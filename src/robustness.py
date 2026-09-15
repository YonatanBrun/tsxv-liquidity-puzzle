"""Step 5b — is the Amihud/zero-return quintile spread a real premium, or a
small-price / skewness artifact?

The primary spec (analysis.py) uses the equal-weighted MEAN forward excess
return per quintile. For TSXV sub-penny names that distribution is violently
right-skewed (median 24m excess return is negative while the mean is positive),
so an equal-weighted mean mostly measures which quintile has the fattest right
tail — and the lowest-priced quintile always does. That is mechanical, not
investable.

This module recomputes the Q5-Q1 spread under variants that each neutralise one
suspected artifact channel, and reports them side by side:

  agg        mean  -> median of within-quintile excess returns (skew-robust)
  weight     equalweight -> valueweight by formation market cap (tiny-name-robust)
  retmeasure excess_ret_w -> excess_ret_avg3_w (3-day avg prices: kills bid-ask bounce)
  pricecut   all -> price_at_formation >= $0.10 at formation
  winsor     1/99 -> also clip at [-0.9, +2.0]

If the spread collapses toward zero under median / value-weight / avg3 / price
cut, the headline is an artifact. If it survives all of them, it is a finding.

  outputs/robustness.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import CFG, OUTPUTS, get_logger

log = get_logger("robustness")
NQ = 5
MEASURES = ["illiq", "zero_ret_pct", "cs_spread"]


def _nw(x: np.ndarray, lags: int):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < max(5, lags + 2):
        return np.nan, np.nan, len(x)
    r = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.params[0]), float(r.tvalues[0]), len(x)


def _quintile_spread_series(df, measure, horizon, *, ret_col, agg, weight,
                            price_min, extra_winsor):
    sub = df[(df["horizon_m"] == horizon) & df[measure].notna()
             & np.isfinite(df[measure]) & df[ret_col].notna()].copy()
    if measure in ("illiq", "cs_spread"):
        sub = sub[sub[measure] > 0]
    if price_min:
        sub = sub[sub["price_at_formation"] >= price_min]
    if extra_winsor:
        sub[ret_col] = sub[ret_col].clip(-0.9, 2.0)

    out = []
    for fd, g in sub.groupby("formation_date"):
        tr = g[g["split"] == "train"]
        if tr[measure].nunique() < NQ + 1 or len(tr) < 5 * NQ:
            continue
        bp = tr[measure].quantile(np.linspace(0, 1, NQ + 1)[1:-1]).to_numpy()
        g = g.assign(q=np.digitize(g[measure].to_numpy(), bp) + 1)
        for split in ("train", "holdout"):
            gg = g[g["split"] == split]
            if not {1, NQ}.issubset(set(gg["q"])):
                continue

            def _agg(block):
                if weight == "value" and block["mktcap"].sum() > 0:
                    w = block["mktcap"].clip(lower=0)
                    return np.average(block[ret_col], weights=w)
                return (block[ret_col].median() if agg == "median"
                        else block[ret_col].mean())

            q1 = _agg(gg[gg["q"] == 1])
            q5 = _agg(gg[gg["q"] == NQ])
            out.append({"formation_date": fd, "split": split, "spread": q5 - q1})
    return pd.DataFrame(out)


def main() -> None:
    df = pd.read_parquet(OUTPUTS / "analysis_frame.parquet")
    if "mktcap" not in df:
        df["mktcap"] = df["price_at_formation"] * df.get("shares_outstanding", np.nan)
    horizons = [int(h) for h in CFG["forward_horizons_months"]]

    VARIANTS = [
        dict(name="primary (mean, EW, pt-to-pt)", ret_col="excess_ret_w",
             agg="mean", weight="equal", price_min=None, extra_winsor=False),
        dict(name="median within quintile", ret_col="excess_ret_w",
             agg="median", weight="equal", price_min=None, extra_winsor=False),
        dict(name="value-weighted", ret_col="excess_ret_w",
             agg="mean", weight="value", price_min=None, extra_winsor=False),
        dict(name="3-day avg prices", ret_col="excess_ret_avg3_w",
             agg="mean", weight="equal", price_min=None, extra_winsor=False),
        dict(name="price >= $0.10", ret_col="excess_ret_w",
             agg="mean", weight="equal", price_min=0.10, extra_winsor=False),
        dict(name="tight winsor [-0.9,2.0]", ret_col="excess_ret_w",
             agg="mean", weight="equal", price_min=None, extra_winsor=True),
        dict(name="median + price>=$0.10", ret_col="excess_ret_w",
             agg="median", weight="equal", price_min=0.10, extra_winsor=False),
    ]

    rows = []
    for measure in MEASURES:
        for h in horizons:
            lags = h if CFG["newey_west_lags"] is None else int(CFG["newey_west_lags"])
            for v in VARIANTS:
                s = _quintile_spread_series(
                    df, measure, h, ret_col=v["ret_col"], agg=v["agg"],
                    weight=v["weight"], price_min=v["price_min"],
                    extra_winsor=v["extra_winsor"])
                for split in ("train", "holdout"):
                    ss = s[s["split"] == split]["spread"].to_numpy()
                    mean, t, k = _nw(ss, lags)
                    rows.append({"measure": measure, "horizon_m": h, "variant": v["name"],
                                 "split": split, "n_dates": k,
                                 "Q5_minus_Q1": mean, "nw_t": t})

    res = pd.DataFrame(rows)
    res.to_csv(OUTPUTS / "robustness.csv", index=False)

    for measure in MEASURES:
        piv = (res[(res.measure == measure) & (res.split == "holdout")]
               .pivot(index="variant", columns="horizon_m", values="Q5_minus_Q1")
               .reindex([v["name"] for v in VARIANTS]))
        tpiv = (res[(res.measure == measure) & (res.split == "holdout")]
                .pivot(index="variant", columns="horizon_m", values="nw_t")
                .reindex([v["name"] for v in VARIANTS]))
        log.info("\n=== %s : HOLDOUT Q5-Q1 by variant (value | NW t) ===", measure)
        for var in piv.index:
            cells = "  ".join(f"{h}m {piv.loc[var, h]:+.3f} (t={tpiv.loc[var, h]:+.2f})"
                              for h in horizons)
            log.info("  %-28s %s", var, cells)


if __name__ == "__main__":
    main()
