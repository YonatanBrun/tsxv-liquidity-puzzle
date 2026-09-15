"""Step 4 — forward excess returns, the dependent variable.

For each (ticker, formation_date, horizon in {6,12,24} months):

  fwd_ret    adj_close(fd + h) / adj_close(fd) - 1     [total return, split/div adj]
  bench_ret  same ratio on ^SPCDNX over the same calendar span
  excess     fwd_ret - bench_ret
  excess_w   excess winsorized at [1, 99] pct WITHIN each (formation_date, horizon)
             cross-section  (decided before seeing results; see config)

Look-ahead: every input here is dated on or after the formation date, and every
illiquidity input (metrics.py) is dated strictly before it. The two never touch.

A name whose adjusted series ends well before fd+h (halt / delist / data gap)
gets a NaN forward return and is flagged `tail_ends_early`. v1 drops these and
discloses the resulting survivorship exposure; a robustness pass can instead
assign -100%.

  data/adjusted/forward_returns.parquet
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import CFG, ADJUSTED, BENCHMARK, get_logger
from metrics import formation_dates

log = get_logger("forward_returns")

OUT = ADJUSTED / "forward_returns.parquet"
BENCH_PARQUET = BENCHMARK / "spcdnx.parquet"


def _asof_price(s: pd.Series, when: pd.Timestamp) -> tuple[float, pd.Timestamp]:
    """Last non-NaN value at/before `when`; returns (nan, NaT) if none."""
    s = s.dropna().loc[:when]
    if s.empty:
        return np.nan, pd.NaT
    return float(s.iloc[-1]), s.index[-1]


def _asof_avg(s: pd.Series, when: pd.Timestamp, k: int = 3) -> float:
    """Mean of the last k valid closes at/before `when` (microstructure-noise damped)."""
    s = s.dropna().loc[:when]
    return float(s.iloc[-k:].mean()) if len(s) else np.nan


def _ret(s: pd.Series, fd: pd.Timestamp, h: int, tol_days: int = 20):
    """(fwd_ret, tail_ends_early) or None if either endpoint is missing."""
    p0, _ = _asof_price(s, fd)
    target = fd + pd.DateOffset(months=h)
    p1, d1 = _asof_price(s, target)
    if not np.isfinite(p0) or not np.isfinite(p1) or p0 <= 0:
        return None
    early = (target - d1).days > tol_days       # nearest price is stale -> series ended
    return p1 / p0 - 1.0, early


def main() -> None:
    bench = pd.read_parquet(BENCH_PARQUET)["adj_close"].sort_index()
    fdates = formation_dates()
    horizons = [int(h) for h in CFG["forward_horizons_months"]]
    wlo, whi = CFG["winsorize_pct"]
    window_end = pd.Timestamp(CFG["window_end"])

    files = sorted(ADJUSTED.glob("*.parquet"))
    files = [f for f in files if f.stem not in ("metrics_panel", "forward_returns")]
    log.info("%d adjusted series x %d formation dates x %d horizons",
             len(files), len(fdates), len(horizons))

    rows = []
    for i, f in enumerate(files, 1):
        tk = f.stem
        px = pd.read_parquet(f)["adj_close"].sort_index()
        for fd in fdates:
            for h in horizons:
                if fd + pd.DateOffset(months=h) > window_end + pd.Timedelta(days=5):
                    continue                        # forward window not fully realized
                r = _ret(px, fd, h)
                if r is None:
                    continue
                fret, early = r
                tgt = fd + pd.DateOffset(months=h)
                b0, b1 = _asof_price(bench, fd)[0], _asof_price(bench, tgt)[0]
                bret = (b1 / b0 - 1.0) if np.isfinite(b0) and np.isfinite(b1) and b0 > 0 \
                    else np.nan
                if not np.isfinite(fret) or not np.isfinite(bret):
                    continue
                a0, a1 = _asof_avg(px, fd), _asof_avg(px, tgt)
                ba0, ba1 = _asof_avg(bench, fd), _asof_avg(bench, tgt)
                fret_avg = (a1 / a0 - 1.0) if np.isfinite(a0) and a0 > 0 else np.nan
                bret_avg = (ba1 / ba0 - 1.0) if np.isfinite(ba0) and ba0 > 0 else np.nan
                rows.append({"ticker": tk, "formation_date": fd, "horizon_m": h,
                             "fwd_ret": fret, "bench_ret": bret,
                             "excess_ret": fret - bret,
                             "excess_ret_avg3": fret_avg - bret_avg,
                             "tail_ends_early": early})
        if i % 100 == 0 or i == len(files):
            log.info("  %d/%d", i, len(files))

    df = pd.DataFrame(rows)
    # winsorize excess within each (formation_date, horizon) cross-section
    def _w(g):
        lo, hi = g["excess_ret"].quantile([wlo, whi])
        g["excess_ret_w"] = g["excess_ret"].clip(lo, hi)
        lo2, hi2 = g["excess_ret_avg3"].quantile([wlo, whi])
        g["excess_ret_avg3_w"] = g["excess_ret_avg3"].clip(lo2, hi2)
        return g
    df = df.groupby(["formation_date", "horizon_m"], group_keys=False).apply(_w)

    df.to_parquet(OUT)
    log.info("wrote %s: %d rows", OUT, len(df))
    log.info("rows per horizon:\n%s", df.groupby("horizon_m").size().to_string())
    log.info("tail_ends_early share: %.1f%%", 100 * df["tail_ends_early"].mean())


if __name__ == "__main__":
    main()
