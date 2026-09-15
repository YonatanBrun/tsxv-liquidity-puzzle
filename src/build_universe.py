"""Step 0 — build the study universe, fully programmatically.

  1. Pull the complete TSX Venture issuer directory from tsx.com (public JSON).
     NEX-tier names are already excluded by that endpoint.
  2. Drop non-common / non-operating instruments (CPCs, warrants, units, prefs...).
  3. For every remaining name, hit TMX Money's GraphQL `getQuoteBySymbol` for
     GICS sector + industry + shares outstanding + market cap + last price.
  4. Map GICS -> the 6 TSXV sector buckets.
  5. Optionally draw a sector-stratified subsample (config: sample_size).

Outputs:
  data/universe/tsxv_directory_raw.csv   every directory row + GraphQL fields + drop reason
  data/universe/universe.csv             the cleaned, classified study sample
"""
from __future__ import annotations

import json
import re
import time

import pandas as pd
import requests

from common import (CFG, UNIVERSE_CSV, UNIVERSE_RAW_CSV, get_logger,
                    map_to_tsxv_sector)

log = get_logger("build_universe")

TSXV_DIRECTORY = "https://www.tsx.com/json/company-directory/search/tsxv/%5E"
TMX_GQL = "https://app-money.tmx.com/graphql"
GQL_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Referer": "https://money.tmx.com/",
    "Content-Type": "application/json",
}
GQL_QUERY = """query($sym:String!){
  getQuoteBySymbol(symbol:$sym, locale:"en"){
    symbol name exchangeName exShortName
    sector industry qmdescription
    shareOutStanding totalSharesOutStanding
    MarketCap price prevClose
  }
}"""


def suffix_of(symbol: str) -> str:
    """Return the trailing dotted tag of a symbol ('ABC.WT.A' -> 'WT'), else ''."""
    m = re.match(r"^[A-Z0-9]+\.([A-Z]+)", symbol.upper())
    return m.group(1) if m else ""


def fetch_directory() -> pd.DataFrame:
    log.info("Fetching TSXV issuer directory ...")
    r = requests.get(TSXV_DIRECTORY, timeout=60,
                     headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    r.raise_for_status()
    payload = r.json()
    rows = []
    for entry in payload["results"]:
        instruments = entry.get("instruments") or [{"symbol": entry["symbol"],
                                                    "name": entry["name"]}]
        for ins in instruments:
            rows.append({"symbol": ins["symbol"],
                         "name": ins.get("name", entry["name"])})
    df = pd.DataFrame(rows).drop_duplicates("symbol").reset_index(drop=True)
    log.info("  directory: %d issuers, %d instrument lines",
             len(payload["results"]), len(df))
    return df


def gql_quote(session: requests.Session, symbol: str) -> dict | None:
    try:
        resp = session.post(TMX_GQL, headers=GQL_HEADERS,
                            data=json.dumps({"query": GQL_QUERY,
                                             "variables": {"sym": symbol}}),
                            timeout=20)
        resp.raise_for_status()
        return (resp.json().get("data") or {}).get("getQuoteBySymbol")
    except Exception as e:  # noqa: BLE001 - network best-effort, logged
        log.warning("  GraphQL failed for %s: %s", symbol, e)
        return None


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    pause = float(CFG["tmx_pause_seconds"])
    session = requests.Session()
    recs = []
    n = len(df)
    for i, row in enumerate(df.itertuples(index=False), 1):
        base = row.symbol.split(".")[0]          # GraphQL wants the root symbol
        q = gql_quote(session, base) or {}
        so = q.get("shareOutStanding") or q.get("totalSharesOutStanding")
        recs.append({
            "symbol": row.symbol,
            "name": row.name,
            "gql_symbol": q.get("symbol"),
            "gql_name": q.get("name"),
            "exch": q.get("exShortName"),
            "gics_sector": q.get("sector"),
            "industry": q.get("industry"),
            "qm": q.get("qmdescription"),
            "shares_outstanding": so,
            "market_cap": q.get("MarketCap"),
            "price": q.get("price"),
            "gql_ok": bool(q),
        })
        if i % 100 == 0 or i == n:
            log.info("  GraphQL %d/%d", i, n)
        time.sleep(pause)
    return df.merge(pd.DataFrame(recs).drop(columns=["name"]), on="symbol", how="left")


def classify_and_filter(df: pd.DataFrame) -> pd.DataFrame:
    drop_suffixes = set(CFG["drop_suffixes"])
    want_exch = CFG["require_exchange"]

    df = df.copy()
    df["suffix"] = df["symbol"].map(suffix_of)
    df["tsxv_sector"] = [map_to_tsxv_sector(s, i)
                         for s, i in zip(df["gics_sector"], df["industry"])]

    reason = pd.Series("", index=df.index)
    reason = reason.mask(df["suffix"].isin(drop_suffixes),
                         "suffix:" + df["suffix"])
    reason = reason.mask((reason == "") & (~df["gql_ok"]),
                         "no_graphql_quote")
    reason = reason.mask((reason == "") & df["exch"].notna() & (df["exch"] != want_exch),
                         "exch:" + df["exch"].astype(str))
    reason = reason.mask((reason == "") & df["price"].isna(),
                         "no_price")
    df["drop_reason"] = reason
    df["in_universe"] = reason == ""
    return df


def stratified_subsample(df: pd.DataFrame) -> pd.DataFrame:
    n = CFG["sample_size"]
    if not n:
        return df
    seed = int(CFG["sample_seed"])
    frac = n / len(df)
    out = (df.groupby("tsxv_sector", group_keys=False)
             .apply(lambda g: g.sample(max(1, round(len(g) * frac)), random_state=seed)))
    log.info("Stratified subsample: %d -> %d names", len(df), len(out))
    return out.reset_index(drop=True)


def main() -> None:
    directory = fetch_directory()
    enriched = enrich(directory)
    classified = classify_and_filter(enriched)
    classified.to_csv(UNIVERSE_RAW_CSV, index=False)
    log.info("Wrote %s (%d rows)", UNIVERSE_RAW_CSV, len(classified))

    universe = classified[classified["in_universe"]].copy()
    log.info("Cleaned universe: %d names", len(universe))
    log.info("Sector breakdown:\n%s",
             universe["tsxv_sector"].value_counts().to_string())
    log.info("Dropped, by reason:\n%s",
             classified.loc[~classified["in_universe"], "drop_reason"]
             .str.replace(r":.*", "", regex=True).value_counts().to_string())

    universe = stratified_subsample(universe)

    cols = ["symbol", "name", "tsxv_sector", "gics_sector", "industry", "qm",
            "shares_outstanding", "market_cap", "price"]
    universe[cols].rename(columns={"symbol": "ticker"}).to_csv(UNIVERSE_CSV, index=False)
    log.info("Wrote %s (%d names)", UNIVERSE_CSV, len(universe))


if __name__ == "__main__":
    main()
