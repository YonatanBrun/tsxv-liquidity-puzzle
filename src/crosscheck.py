"""Independent price cross-check: Alpha Vantage TIME_SERIES_DAILY vs yfinance.

Free-tier Alpha Vantage throttles hard (~25 req/day), so this pulls a small
random sample of universe names and reports, per name, the correlation of daily
returns and the median absolute close difference between the two sources over the
overlapping dates. It is evidence that the yfinance series is not idiosyncratic,
not a second full dataset.

Set ALPHAVANTAGE_API_KEY in the environment. Without it, the script explains how
the equivalent check was run manually via the Alpha Vantage MCP and exits 0.

  outputs/crosscheck_alphavantage.csv
"""
from __future__ import annotations

import io
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

from common import CFG, RAW, OUTPUTS, UNIVERSE_CSV, get_logger

log = get_logger("crosscheck")
AV_URL = "https://www.alphavantage.co/query"


def av_daily(symbol: str, key: str) -> pd.DataFrame:
    r = requests.get(AV_URL, timeout=30, params={
        "function": "TIME_SERIES_DAILY", "symbol": symbol,
        "outputsize": "full", "datatype": "csv", "apikey": key})
    r.raise_for_status()
    if "timestamp" not in r.text[:200]:
        raise RuntimeError(r.text[:200])
    df = pd.read_csv(io.StringIO(r.text), parse_dates=["timestamp"])
    return df.set_index("timestamp").sort_index()


def main() -> None:
    key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key:
        log.warning(
            "No ALPHAVANTAGE_API_KEY set. The cross-check was run manually via the "
            "Alpha Vantage MCP during development (see README). Skipping automated "
            "re-run.")
        sys.exit(0)

    uni = pd.read_csv(UNIVERSE_CSV)
    n = int(CFG["crosscheck_sample_n"])
    sample = uni.sample(min(n, len(uni)), random_state=int(CFG["sample_seed"]))

    rows = []
    for tk in sample["ticker"].astype(str):
        raw_path = RAW / f"{tk}.parquet"
        if not raw_path.exists():
            continue
        yf_df = pd.read_parquet(raw_path)
        for av_sym in (f"{tk}.V", f"{tk}.TRV"):
            try:
                av = av_daily(av_sym, key)
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                av = None
            time.sleep(15)
        if av is None:
            rows.append({"ticker": tk, "status": f"av_fail:{last_err}"[:60]})
            continue
        idx = yf_df.index.intersection(av.index)
        if len(idx) < 60:
            rows.append({"ticker": tk, "status": "little_overlap", "n": len(idx)})
            continue
        a = av.loc[idx, "close"]
        y = yf_df.loc[idx, "close"]
        ret_corr = np.corrcoef(a.pct_change().dropna(),
                               y.pct_change().reindex(a.index).dropna())[0, 1]
        rows.append({"ticker": tk, "status": "ok", "n": len(idx),
                     "ret_corr": round(float(ret_corr), 4),
                     "median_abs_close_diff": round(float((a - y).abs().median()), 4),
                     "median_close": round(float(y.median()), 4)})
        log.info("  %s: corr=%.4f  n=%d", tk, ret_corr, len(idx))
        time.sleep(15)

    out = pd.DataFrame(rows)
    out.to_csv(OUTPUTS / "crosscheck_alphavantage.csv", index=False)
    ok = out[out["status"] == "ok"]
    if not ok.empty:
        log.info("cross-check: %d names, median return-corr %.4f",
                 len(ok), ok["ret_corr"].median())


if __name__ == "__main__":
    main()
