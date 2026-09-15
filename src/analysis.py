"""Step 5 — the actual test. Portfolio sort + Fama-MacBeth, train then holdout.

For each illiquidity measure (illiq, zero_ret_pct, cs_spread) and each forward
horizon (6, 12, 24 months):

  A. Portfolio sort
     - quintile breakpoints computed at each formation date from TRAIN names only
     - every name (train and holdout) bucketed with those TRAIN breakpoints
     - equal-weighted mean forward EXCESS return per quintile per date
     - Q5 (most illiquid) - Q1 (most liquid) spread per date
     - pooled mean of that spread, Newey-West t (lags = horizon in months)
     - reported separately for split == train and split == holdout

  B. Fama-MacBeth cross-sectional regression
        excess_w ~ illiq_rank + log_mktcap + C(sector)
     - illiq_rank = within-date percentile of the measure (0..1); levels are far
       too skewed to enter raw
     - one cross-sectional OLS per formation date; coefficients averaged over
       dates; Newey-West t on the coefficient series (lags = horizon in months)
     - fit on TRAIN, then independently on HOLDOUT; sign agreement is the check

Nothing here is tuned. There are no free thresholds. Quintile count (5) and the
rank transform are fixed in advance by this file and the config.

Outputs (outputs/):
  analysis_frame.parquet     the merged row-per-(ticker,date,horizon) table
  quintile_returns.csv       mean excess return per quintile, measure, horizon, split
  spread_summary.csv         Q5-Q1 pooled mean + NW t, per measure/horizon/split
  fama_macbeth.csv           b1 mean + NW t, per measure/horizon/split
  results.json               everything above, machine-readable, + run metadata
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from common import CFG, ADJUSTED, OUTPUTS, UNIVERSE_CSV, get_logger
from holdout import load_split

log = get_logger("analysis")

MEASURES = ["illiq", "zero_ret_pct", "cs_spread"]
N_QUANTILES = 5


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def build_frame() -> pd.DataFrame:
    metrics = pd.read_parquet(ADJUSTED / "metrics_panel.parquet")
    fwd = pd.read_parquet(ADJUSTED / "forward_returns.parquet")
    uni = pd.read_csv(UNIVERSE_CSV).rename(columns={"ticker": "ticker"})
    split = load_split()
    member = {t: "train" for t in split["train"]}
    member.update({t: "holdout" for t in split["holdout"]})

    df = fwd.merge(metrics, on=["ticker", "formation_date"], how="inner")
    df = df.merge(uni[["ticker", "tsxv_sector", "shares_outstanding"]],
                  on="ticker", how="left")
    df["split"] = df["ticker"].map(member)
    df = df[df["split"].isin(["train", "holdout"])].copy()

    df["mktcap"] = df["price_at_formation"] * df["shares_outstanding"]
    df["log_mktcap"] = np.log(df["mktcap"].where(df["mktcap"] > 0))
    df["log_price"] = np.log(df["price_at_formation"].where(df["price_at_formation"] > 0))

    # exclude non-positive / missing illiquidity values per measure at use time
    log.info("analysis frame: %d rows, %d names, horizons %s, splits %s",
             len(df), df["ticker"].nunique(),
             sorted(df["horizon_m"].unique()), df["split"].value_counts().to_dict())
    return df


# --------------------------------------------------------------------------- #
# A. portfolio sort
# --------------------------------------------------------------------------- #
def _breakpoints(s: pd.Series) -> np.ndarray:
    qs = np.linspace(0, 1, N_QUANTILES + 1)[1:-1]
    return s.quantile(qs).to_numpy()


def portfolio_sort(df: pd.DataFrame, measure: str, horizon: int):
    sub = df[(df["horizon_m"] == horizon) & df[measure].notna()
             & np.isfinite(df[measure])].copy()
    # measure must be strictly usable; ILLIQ/cs must be > 0, zero_ret_pct can be 0
    if measure in ("illiq", "cs_spread"):
        sub = sub[sub[measure] > 0]

    per_date = []
    for fd, g in sub.groupby("formation_date"):
        train = g[g["split"] == "train"]
        if train[measure].nunique() < N_QUANTILES + 1 or len(train) < 5 * N_QUANTILES:
            continue
        bp = _breakpoints(train[measure])
        q = np.digitize(g[measure].to_numpy(), bp)          # 0..N_QUANTILES-1
        g = g.assign(quintile=q + 1)
        for split in ("train", "holdout"):
            gg = g[g["split"] == split]
            if gg.empty:
                continue
            means = gg.groupby("quintile")["excess_ret_w"].mean()
            if {1, N_QUANTILES}.issubset(means.index):
                per_date.append({
                    "formation_date": fd, "split": split,
                    **{f"q{k}": means.get(k, np.nan) for k in range(1, N_QUANTILES + 1)},
                    "spread": means[N_QUANTILES] - means[1],
                    "n": len(gg),
                })
    return pd.DataFrame(per_date)


def nw_mean_t(x: np.ndarray, lags: int):
    """Pooled mean of a time series with a Newey-West t-stat on the constant."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < max(5, lags + 2):
        return np.nan, np.nan, len(x)
    res = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC",
                                         cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0]), len(x)


# --------------------------------------------------------------------------- #
# B. Fama-MacBeth
# --------------------------------------------------------------------------- #
def fama_macbeth(df: pd.DataFrame, measure: str, horizon: int, split: str,
                 size_var: str = "log_mktcap"):
    sub = df[(df["horizon_m"] == horizon) & (df["split"] == split)
             & df[measure].notna() & np.isfinite(df[measure])
             & df[size_var].notna()].copy()
    if measure in ("illiq", "cs_spread"):
        sub = sub[sub[measure] > 0]

    coefs = []
    for fd, g in sub.groupby("formation_date"):
        if len(g) < 30 or g["tsxv_sector"].nunique() < 1:
            continue
        g = g.assign(illiq_rank=g[measure].rank(pct=True))
        rhs = ["illiq_rank", size_var]
        formula = f"excess_ret_w ~ illiq_rank + {size_var}"
        if CFG["sector_dummies"] and g["tsxv_sector"].nunique() > 1:
            formula += " + C(tsxv_sector)"
        try:
            r = smf.ols(formula, data=g).fit()
        except Exception:  # noqa: BLE001
            continue
        coefs.append({"formation_date": fd, "b_illiq": r.params.get("illiq_rank", np.nan),
                      "b_size": r.params.get(size_var, np.nan), "n": len(g)})
    cdf = pd.DataFrame(coefs)
    if cdf.empty:
        return {"measure": measure, "horizon_m": horizon, "split": split,
                "n_dates": 0, "b_illiq": np.nan, "t_illiq": np.nan}
    lags = horizon if CFG["newey_west_lags"] is None else int(CFG["newey_west_lags"])
    b, t, k = nw_mean_t(cdf["b_illiq"].to_numpy(), lags)
    bs, ts, _ = nw_mean_t(cdf["b_size"].to_numpy(), lags)
    return {"measure": measure, "horizon_m": horizon, "split": split,
            "n_dates": int(k), "b_illiq": b, "t_illiq": t,
            "b_size": bs, "t_size": ts,
            "mean_n_per_date": float(cdf["n"].mean())}


# --------------------------------------------------------------------------- #
def main() -> None:
    df = build_frame()
    df.to_parquet(OUTPUTS / "analysis_frame.parquet")
    horizons = [int(h) for h in CFG["forward_horizons_months"]]

    quint_rows, spread_rows, fm_rows = [], [], []
    for measure in MEASURES:
        for h in horizons:
            ps = portfolio_sort(df, measure, h)
            for split in ("train", "holdout"):
                s = ps[ps["split"] == split]
                if s.empty:
                    continue
                qcols = [f"q{k}" for k in range(1, N_QUANTILES + 1)]
                quint_rows.append({"measure": measure, "horizon_m": h, "split": split,
                                   "n_dates": len(s),
                                   **{c: float(s[c].mean()) for c in qcols}})
                lags = h if CFG["newey_west_lags"] is None else int(CFG["newey_west_lags"])
                mean_spread, tstat, k = nw_mean_t(s["spread"].to_numpy(), lags)
                spread_rows.append({"measure": measure, "horizon_m": h, "split": split,
                                    "n_dates": k, "mean_Q5_minus_Q1": mean_spread,
                                    "nw_t": tstat, "nw_lags": lags})
                fm_rows.append(fama_macbeth(df, measure, h, split))

    quint = pd.DataFrame(quint_rows)
    spread = pd.DataFrame(spread_rows)
    fm = pd.DataFrame(fm_rows)
    quint.to_csv(OUTPUTS / "quintile_returns.csv", index=False)
    spread.to_csv(OUTPUTS / "spread_summary.csv", index=False)
    fm.to_csv(OUTPUTS / "fama_macbeth.csv", index=False)

    results = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": CFG,
        "n_names": int(df["ticker"].nunique()),
        "n_formation_dates": int(df["formation_date"].nunique()),
        "quintile_returns": quint.to_dict("records"),
        "spread_summary": spread.to_dict("records"),
        "fama_macbeth": fm.to_dict("records"),
    }
    (OUTPUTS / "results.json").write_text(json.dumps(results, indent=2, default=str))

    log.info("\n=== Q5-Q1 spread (pooled mean, NW t) ===\n%s",
             spread.to_string(index=False))
    log.info("\n=== Fama-MacBeth b(illiq_rank) ===\n%s",
             fm[["measure", "horizon_m", "split", "n_dates", "b_illiq", "t_illiq"]]
             .to_string(index=False))
    _verdict(spread, fm)


def _verdict(spread: pd.DataFrame, fm: pd.DataFrame) -> None:
    """Plain-language read of train-vs-holdout agreement. Not a p-hack; just a summary."""
    lines = []
    for measure in MEASURES:
        for h in [int(x) for x in CFG["forward_horizons_months"]]:
            tr = spread[(spread.measure == measure) & (spread.horizon_m == h)
                        & (spread.split == "train")]
            ho = spread[(spread.measure == measure) & (spread.horizon_m == h)
                        & (spread.split == "holdout")]
            if tr.empty or ho.empty:
                continue
            st, sh = tr.iloc[0]["mean_Q5_minus_Q1"], ho.iloc[0]["mean_Q5_minus_Q1"]
            tt, th = tr.iloc[0]["nw_t"], ho.iloc[0]["nw_t"]
            agree = np.sign(st) == np.sign(sh)
            hold_sig = abs(th) >= 1.96
            lines.append(f"  {measure:<13} {h:>2}m  train Q5-Q1={st:+.3f} (t={tt:+.2f})"
                         f"  holdout={sh:+.3f} (t={th:+.2f})  "
                         f"{'REPLICATES' if agree and hold_sig else 'sign-agrees' if agree else 'DOES NOT replicate'}")
    log.info("\n=== holdout replication read ===\n%s", "\n".join(lines))


if __name__ == "__main__":
    main()
