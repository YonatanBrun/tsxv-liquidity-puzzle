"""Step 2 — per-ticker, per-formation-date illiquidity metrics.

Builds a split/dividend-adjusted OHLCV panel from each raw yfinance frame, then
for every month-end formation date computes, over the trailing `trailing_months`:

  illiq        Amihud (2002): mean over days with $vol>0 of |ret| / $vol, x1e6.
               ret from ADJUSTED close; $vol from RAW close x RAW volume
               (actual dollars traded that day).
  zero_ret_pct % of trailing trading days with an exactly unchanged raw close
               (Lesmond-Ogden-Trzcinka no-trade proxy).
  cs_spread    Corwin-Schultz (2012) 2-day high/low effective spread, averaged
               over the window; negative 2-day estimates clamped to 0.

Adjusted OHLC = raw OHLC x (adj_close / close): yfinance only adjusts close, so
we scale the whole bar by the same factor. Within-day ratios (H/L) are
unaffected; the cross-day Corwin-Schultz term is, which is the point — a
consolidation between two days must not register as a real range.

Outputs:
  data/adjusted/<TICKER>.parquet   audited adjusted series + adjustment factor
  data/adjusted/metrics_panel.parquet   long: ticker x formation_date x metrics
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import CFG, RAW, ADJUSTED, UNIVERSE_CSV, get_logger

log = get_logger("metrics")

PANEL_OUT = ADJUSTED / "metrics_panel.parquet"
_CS_K = 3.0 - 2.0 * np.sqrt(2.0)


def formation_dates() -> pd.DatetimeIndex:
    return pd.date_range(CFG["formation_start"], CFG["formation_end"], freq="ME")


def _repair_bad_prints(close: pd.Series) -> pd.Series:
    """Neutralise isolated one-day price spikes that immediately revert.

    TMX's raw series occasionally carries a fat-fingered print (e.g. a 10x tick
    that is gone the next day). A one-day |log move| > 1.6 (~5x) followed by a
    reversal of > 60% of it is treated as bad and linearly interpolated. Genuine
    multi-day moves and real consolidations (which do NOT revert) are untouched.
    """
    c = close.astype(float).copy()
    lr = np.log(c.replace(0, np.nan)).diff()
    bad = (lr.abs() > 1.6) & (lr.shift(-1) * lr < 0) & (lr.shift(-1).abs() > 0.6 * lr.abs())
    if bad.any():
        c[bad.fillna(False)] = np.nan
        c = c.interpolate(limit=2).ffill().bfill()
    return c


def quality_ok(raw: pd.DataFrame) -> tuple[bool, str]:
    """Reject a name whose price series is not a plausible CAD TSXV common."""
    c = raw["close"].dropna()
    if len(c) < 60:
        return False, "too_short"
    if c.median() > 50:
        return False, f"median_price_${c.median():.0f}"      # units / stacked unadjusted splits
    lr = np.log(c.replace(0, np.nan)).diff().abs()
    if (lr > 1.6).sum() > 8:
        return False, "many_extreme_jumps"
    return True, "ok"


def build_adjusted(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw source frame -> adjusted OHLCV + kept raw close/volume for $-volume."""
    df = raw.sort_index().copy()
    df = df[~df.index.duplicated(keep="last")]
    df["close"] = _repair_bad_prints(df["close"])
    if (df["adj_close"] == df["close"]).mean() < 0.99:
        pass  # yfinance-adj present; leave adj_close as delivered
    else:
        df["adj_close"] = df["close"]
    close = df["close"].replace(0, np.nan)
    factor = (df["adj_close"] / close).clip(lower=0)
    factor = factor.ffill().bfill().fillna(1.0)
    out = pd.DataFrame(index=df.index)
    out["adj_open"] = df["open"] * factor
    out["adj_high"] = df["high"] * factor
    out["adj_low"] = df["low"] * factor
    out["adj_close"] = df["adj_close"]
    out["raw_close"] = df["close"]
    out["volume"] = df["volume"].fillna(0)
    out["dollar_volume"] = out["raw_close"] * out["volume"]
    out["adj_factor"] = factor
    out["ret"] = out["adj_close"].pct_change()
    out["splits"] = df.get("splits", 0.0)
    return out


def corwin_schultz(high: pd.Series, low: pd.Series, clamp_neg: bool) -> float:
    """Mean Corwin-Schultz 2-day spread over a window. NaN if <2 valid pairs."""
    h = np.log(high.to_numpy())
    l = np.log(low.to_numpy())
    ok = np.isfinite(h) & np.isfinite(l) & (high.to_numpy() > 0) & (low.to_numpy() > 0)
    hl = np.where(ok, h - l, np.nan)                      # ln(H/L) per day
    beta = hl[:-1] ** 2 + hl[1:] ** 2                     # sum of two single-day squares
    h2 = np.maximum(h[:-1], h[1:])
    l2 = np.minimum(l[:-1], l[1:])
    gamma = (h2 - l2) ** 2
    pair_ok = ok[:-1] & ok[1:]
    with np.errstate(invalid="ignore"):
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _CS_K - np.sqrt(gamma / _CS_K)
        spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    spread = spread[pair_ok & np.isfinite(spread)]
    if spread.size == 0:
        return np.nan
    if clamp_neg:
        spread = np.where(spread < 0, 0.0, spread)
    return float(np.mean(spread))


def metrics_for_window(win: pd.DataFrame) -> dict:
    scale = float(CFG["amihud_scale"])
    traded = win[win["dollar_volume"] > 0]
    illiq = (np.abs(traded["ret"]) / traded["dollar_volume"]).mean() * scale \
        if len(traded) else np.nan

    raw_close = win["raw_close"]
    unchanged = (raw_close.diff() == 0) & raw_close.notna()
    zero_ret_pct = 100.0 * unchanged.sum() / max(len(win) - 1, 1)

    cs = corwin_schultz(win["adj_high"], win["adj_low"], bool(CFG["cs_clamp_negative"]))

    return {
        "n_days": int(len(win)),
        "n_traded_days": int(len(traded)),
        "illiq": illiq,
        "zero_ret_pct": zero_ret_pct,
        "cs_spread": cs,
        "median_dollar_volume": float(win["dollar_volume"].median()),
        "adv_20d": float(win["dollar_volume"].tail(20).mean()),
    }


def process_ticker(tk: str, fdates: pd.DatetimeIndex, trailing: pd.DateOffset,
                   min_days: int) -> tuple[list[dict], str]:
    path = RAW / f"{tk}.parquet"
    if not path.exists():
        return [], "no_file"
    raw = pd.read_parquet(path)
    ok, why = quality_ok(raw)
    if not ok:
        return [], why
    adj = build_adjusted(raw)
    adj.to_parquet(ADJUSTED / f"{tk}.parquet")

    rows = []
    for fd in fdates:
        win = adj.loc[fd - trailing + pd.Timedelta(days=1): fd]
        if len(win) < min_days:
            continue
        last = win.iloc[-1]
        m = metrics_for_window(win)
        m.update({
            "ticker": tk,
            "formation_date": fd,
            "price_at_formation": float(last["raw_close"]),
            "price_5d_median": float(win["raw_close"].tail(5).median()),
            "flag_sub_nickel": bool(last["raw_close"] < 0.05),
            "flag_thin": m["n_traded_days"] < 0.5 * m["n_days"],
        })
        rows.append(m)
    return rows, "ok"


def main() -> None:
    uni = pd.read_csv(UNIVERSE_CSV)
    fdates = formation_dates()
    trailing = pd.DateOffset(months=int(CFG["trailing_months"]))
    min_days = int(CFG["min_trailing_days"])
    log.info("%d names x %d formation dates (%s .. %s)",
             len(uni), len(fdates), fdates[0].date(), fdates[-1].date())

    all_rows, rejected = [], []
    for i, tk in enumerate(uni["ticker"].astype(str), 1):
        rows, why = process_ticker(tk, fdates, trailing, min_days)
        all_rows.extend(rows)
        if not rows and why not in ("no_file",):
            rejected.append({"ticker": tk, "reason": why})
        if i % 100 == 0 or i == len(uni):
            log.info("  %d/%d names, %d panel rows so far", i, len(uni), len(all_rows))

    rej = pd.DataFrame(rejected)
    if len(rej):
        rej.to_csv(ADJUSTED / "quality_rejects.csv", index=False)
        log.info("quality rejects: %d names\n%s", len(rej),
                 rej["reason"].str.replace(r":.*|\$.*", "", regex=True).value_counts().to_string())

    panel = pd.DataFrame(all_rows)
    panel.to_parquet(PANEL_OUT)
    log.info("wrote %s: %d rows, %d names, %d formation dates",
             PANEL_OUT, len(panel), panel["ticker"].nunique(),
             panel["formation_date"].nunique())
    log.info("coverage per formation date (median names): %.0f",
             panel.groupby("formation_date").size().median())


if __name__ == "__main__":
    main()
