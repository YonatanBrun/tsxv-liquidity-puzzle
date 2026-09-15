"""Step 1 — fetch and cache clean daily history for every universe name.

Primary source: TMX Money GraphQL `getTimeSeriesData` (same provider as the
universe / sector / shares-outstanding pull). It returns daily OHLCV for every
TSXV name and for the S&P/TSX Venture Composite (TMX symbol `JX`; Yahoo's
`^SPCDNX`). It showed no rate limiting across ~1,500 calls and its series is
consolidation-consistent (spot-checked across a known 5:1 rollback — no fake
jump), i.e. effectively split-adjusted.

Optional supplement: if yfinance is reachable, its `adj_close` + `splits` for a
name are stored alongside, and metrics.py will prefer the yfinance-derived
adjustment factor when present. yfinance being blocked (common) does not stop
the run.

Nothing is silently dropped: per-name outcome is logged to
data/raw/_fetch_report.csv, and any large overnight jump that reverts (possible
unadjusted consolidation) is counted in the `n_jump_flags` column for QA.

  data/raw/<TICKER>.parquet        date, open, high, low, close, volume,
                                   adj_close (== close unless yfinance filled it),
                                   splits, source
  data/benchmark/spcdnx.parquet    the Venture Composite
  data/raw/_fetch_report.csv
"""
from __future__ import annotations

import argparse
import io
import json
import time
from contextlib import redirect_stderr

import numpy as np
import pandas as pd
import requests

from common import CFG, RAW, BENCHMARK, UNIVERSE_CSV, get_logger, yahoo_symbol

log = get_logger("fetch")

TMX_GQL = "https://app-money.tmx.com/graphql"
GQL_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Referer": "https://money.tmx.com/",
    "Content-Type": "application/json",
}
TS_QUERY = """query($sym:String!,$start:String!,$end:String!){
  getTimeSeriesData(symbol:$sym, freq:"day", start:$start, end:$end){
    dateTime open high low close volume
  }
}"""

BENCH_PARQUET = BENCHMARK / "spcdnx.parquet"
FETCH_REPORT = RAW / "_fetch_report.csv"
BENCH_TMX_SYMBOL = "JX"


# --------------------------------------------------------------------------- #
# TMX GraphQL daily series
# --------------------------------------------------------------------------- #
def tmx_daily(session: requests.Session, symbol: str,
              start: str, end: str, retries: int = 3) -> pd.DataFrame:
    payload = {"query": TS_QUERY,
               "variables": {"sym": symbol, "start": start, "end": end}}
    for attempt in range(retries):
        try:
            r = session.post(TMX_GQL, headers=GQL_HEADERS,
                             data=json.dumps(payload), timeout=30)
            r.raise_for_status()
            data = (r.json().get("data") or {}).get("getTimeSeriesData")
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["dateTime"], utc=True).dt.tz_localize(None).dt.normalize()
            df = (df.drop(columns=["dateTime"])
                    .set_index("date").sort_index())
            for c in ("open", "high", "low", "close", "volume"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df[~df.index.duplicated(keep="last")]
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return pd.DataFrame()


# --------------------------------------------------------------------------- #
# optional yfinance supplement (adj_close + splits only)
# --------------------------------------------------------------------------- #
_YF_STATE = {"ok": True, "consecutive_fail": 0}


def yf_supplement(symbol: str) -> pd.DataFrame:
    """Return a frame with adj_close + splits, or empty. Never raises.

    After 15 consecutive misses (Yahoo IP-blocking is common) the supplement
    switches itself off for the rest of the run so it stops wasting time.
    """
    if not _YF_STATE["ok"]:
        return pd.DataFrame()
    try:
        import yfinance as yf
        with redirect_stderr(io.StringIO()):
            d = yf.download(symbol, start=CFG["data_start"], end=CFG["window_end"],
                            auto_adjust=False, actions=True, progress=False,
                            threads=False)
        if d is None or len(d) == 0:
            _YF_STATE["consecutive_fail"] += 1
            if _YF_STATE["consecutive_fail"] >= 15:
                _YF_STATE["ok"] = False
                log.warning("yfinance supplement disabled after 15 consecutive "
                            "misses (Yahoo likely blocking); continuing on TMX only")
            return pd.DataFrame()
        _YF_STATE["consecutive_fail"] = 0
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        out = pd.DataFrame(index=d.index.tz_localize(None).normalize())
        out["adj_close"] = pd.to_numeric(d.get("Adj Close"), errors="coerce")
        out["splits"] = pd.to_numeric(d.get("Stock Splits", 0.0), errors="coerce").fillna(0.0)
        return out
    except Exception:  # noqa: BLE001
        _YF_STATE["consecutive_fail"] += 1
        if _YF_STATE["consecutive_fail"] >= 15:
            _YF_STATE["ok"] = False
        return pd.DataFrame()


def _jump_flags(close: pd.Series) -> int:
    lr = np.log(close.replace(0, np.nan)).diff()
    big = lr.abs() > 0.5
    reverts = big & (lr * lr.shift(-1) < 0) & (lr.shift(-1).abs() > 0.3)
    return int(reverts.sum())


# --------------------------------------------------------------------------- #
def fetch_benchmark(session: requests.Session, force: bool = False) -> None:
    if BENCH_PARQUET.exists() and not force:
        log.info("benchmark cached (%s)", BENCH_PARQUET.name)
        return
    df = tmx_daily(session, BENCH_TMX_SYMBOL, CFG["data_start"], CFG["window_end"])
    if df.empty:
        log.error("benchmark %s returned nothing from TMX - cannot proceed",
                  BENCH_TMX_SYMBOL)
        raise SystemExit(1)
    df["adj_close"] = df["close"]
    df["splits"] = 0.0
    df["source"] = "tmx"
    df.to_parquet(BENCH_PARQUET)
    log.info("benchmark (TMX %s): %d rows %s -> %s", BENCH_TMX_SYMBOL, len(df),
             df.index.min().date(), df.index.max().date())


def fetch_universe(session: requests.Session, force: bool = False,
                   with_yf: bool = True) -> None:
    uni = pd.read_csv(UNIVERSE_CSV)
    pause = float(CFG["tmx_pause_seconds"])
    start, end = CFG["data_start"], CFG["window_end"]
    report = []
    n = len(uni)
    yf_hits = 0
    for i, tk in enumerate(uni["ticker"].astype(str), 1):
        out = RAW / f"{tk}.parquet"
        if out.exists() and not force:
            report.append({"ticker": tk, "status": "cached"})
            continue
        base = tk.split(".")[0]
        try:
            df = tmx_daily(session, base, start, end)
        except Exception as e:  # noqa: BLE001
            log.warning("  %s: TMX ERROR %s", tk, e)
            report.append({"ticker": tk, "status": f"tmx_error:{e}"[:80]})
            time.sleep(pause)
            continue
        if df.empty:
            report.append({"ticker": tk, "status": "empty"})
            time.sleep(pause)
            continue

        df["adj_close"] = df["close"]
        df["splits"] = 0.0
        df["source"] = "tmx"
        if with_yf:
            sup = yf_supplement(yahoo_symbol(tk))
            if not sup.empty:
                yf_hits += 1
                df = df.join(sup[["adj_close"]].rename(columns={"adj_close": "yf_adj"}),
                             how="left")
                # scale yf adj onto the TMX close level, use where available
                ratio = (df["yf_adj"] / df["close"]).median(skipna=True)
                if np.isfinite(ratio) and ratio > 0:
                    df["adj_close"] = (df["yf_adj"] / ratio).fillna(df["close"])
                df["splits"] = sup["splits"].reindex(df.index).fillna(0.0)
                df["source"] = "tmx+yf_adj"
                df = df.drop(columns=["yf_adj"])

        df.to_parquet(out)
        report.append({"ticker": tk, "status": "ok", "rows": len(df),
                       "start": df.index.min().date(), "end": df.index.max().date(),
                       "source": df["source"].iloc[0],
                       "n_splits": int((df["splits"] != 0).sum()),
                       "n_jump_flags": _jump_flags(df["close"])})
        if i % 50 == 0 or i == n:
            ok = sum(1 for r in report if r["status"] in ("ok", "cached"))
            log.info("  %d/%d  (%d usable, %d yf-adj)", i, n, ok, yf_hits)
        time.sleep(pause)

    rep = pd.DataFrame(report)
    rep.to_csv(FETCH_REPORT, index=False)
    log.info("fetch report -> %s", FETCH_REPORT)
    log.info("status counts:\n%s",
             rep["status"].str.replace(r":.*", "", regex=True).value_counts().to_string())
    if "n_jump_flags" in rep:
        log.info("names with >=1 unadjusted-jump QA flag: %d",
                 int((rep["n_jump_flags"].fillna(0) > 0).sum()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--benchmark-only", action="store_true")
    ap.add_argument("--no-yf", action="store_true", help="skip the yfinance adj-close supplement")
    args = ap.parse_args()

    session = requests.Session()
    fetch_benchmark(session, force=args.force)
    if not args.benchmark_only:
        fetch_universe(session, force=args.force, with_yf=not args.no_yf)


if __name__ == "__main__":
    main()
