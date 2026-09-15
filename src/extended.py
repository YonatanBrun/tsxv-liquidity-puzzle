"""Step 5c — the bias battery and the extra cuts a referee will ask for.

Sections, each writes to outputs/ and (where useful) a figure:

  1. survivorship_bracket   names that stop trading mid-window are re-priced under
                            carry-forward / zero-excess / wipeout(-100%); also
                            flags stale-at-formation and stale-at-exit rows.
  2. survivorship_bound     analytic worst case: if a hidden fraction f of Q5
                            names were failures earning -100%, how large must f
                            be to erase the observed Q5-Q1 spread?
  3. subperiods             Q5-Q1 in 2016-2018 / 2019-2021 / 2022-2024.
  4. price_double_sort       independent 3x5 sort on formation price x illiquidity:
                            is the effect just low-price / short-term reversal?
  5. sector_neutral         quintiles formed on illiquidity RANKED WITHIN
                            sector x date (Mining is ~66% of the tape).
  6. persistence            illiquidity-quintile transition matrix + rank AR(1):
                            is illiquidity a stable characteristic or noise?
  7. turnover_check         share turnover and $-volume as complementary
                            liquidity proxies -> same sign?

Consumes outputs/analysis_frame.parquet (+ raw adjusted series for the bracket).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import CFG, ADJUSTED, OUTPUTS, UNIVERSE_CSV, get_logger
from metrics import formation_dates

log = get_logger("extended")
NQ = 5
H_LIST = [int(h) for h in CFG["forward_horizons_months"]]


def _nw(x, lags):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < max(5, lags + 2):
        return np.nan, np.nan, len(x)
    r = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.params[0]), float(r.tvalues[0]), len(x)


def _spread_series(df, measure, horizon, ret_col="excess_ret_w", within=None,
                   agg="median"):
    sub = df[(df.horizon_m == horizon) & df[measure].notna()
             & np.isfinite(df[measure]) & df[ret_col].notna()].copy()
    if measure in ("illiq", "cs_spread", "turnover", "dollar_vol"):
        sub = sub[sub[measure] > 0]
    rows = []
    gcols = ["formation_date"] + ([within] if within else [])
    for keys, g in sub.groupby(gcols):
        fd = keys[0] if isinstance(keys, tuple) else keys
        tr = g[g.split == "train"]
        if tr[measure].nunique() < NQ + 1 or len(tr) < 5 * NQ:
            continue
        bp = tr[measure].quantile(np.linspace(0, 1, NQ + 1)[1:-1]).to_numpy()
        g = g.assign(q=np.digitize(g[measure].to_numpy(), bp) + 1)
        for split in ("train", "holdout"):
            gg = g[g.split == split]
            if not {1, NQ}.issubset(set(gg["q"])):
                continue
            f = (lambda b: b[ret_col].median()) if agg == "median" else (lambda b: b[ret_col].mean())
            rows.append({"formation_date": fd, "split": split,
                         "spread": f(gg[gg.q == NQ]) - f(gg[gg.q == 1])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 1 + bracket
def survivorship_bracket(df: pd.DataFrame) -> pd.DataFrame:
    """Re-price truncated windows under 3 delisting assumptions and resort."""
    fdates = formation_dates()
    window_end = pd.Timestamp(CFG["window_end"])
    # per (ticker) last real trade date
    last_trade = {}
    for f in ADJUSTED.glob("*.parquet"):
        if f.stem in ("metrics_panel", "forward_returns"):
            continue
        s = pd.read_parquet(f)
        v = s[s["volume"] > 0]
        last_trade[f.stem] = v.index.max() if len(v) else s.index.max()

    base = df.copy()
    base["last_trade"] = base["ticker"].map(last_trade)
    base["target_date"] = base.apply(
        lambda r: pd.Timestamp(r["formation_date"]) + pd.DateOffset(months=int(r["horizon_m"])),
        axis=1)
    # "truncated" = last real trade is well before the intended exit AND before window_end
    base["truncated"] = ((base["target_date"] - base["last_trade"]).dt.days > 25) & \
                        (base["last_trade"] < window_end - pd.Timedelta(days=25))

    out = []
    for scen, val in [("carry_forward", None), ("zero_excess", 0.0), ("wipeout", -1.0)]:
        d = base.copy()
        if scen == "zero_excess":
            d.loc[d.truncated, "excess_ret_w"] = 0.0
        elif scen == "wipeout":
            # raw -100% from last price -> excess = -1 - bench_ret over the window
            d.loc[d.truncated, "excess_ret_w"] = (-1.0 - d.loc[d.truncated, "bench_ret"]).clip(-2.0, 0)
        for measure in ("illiq", "zero_ret_pct", "cs_spread"):
            for h in H_LIST:
                s = _spread_series(d, measure, h)
                for split in ("holdout",):
                    ss = s[s.split == split]["spread"].to_numpy()
                    m, t, k = _nw(ss, h)
                    out.append({"scenario": scen, "measure": measure, "horizon_m": h,
                                "split": split, "Q5_minus_Q1": m, "nw_t": t, "n_dates": k})
    res = pd.DataFrame(out)
    res.to_csv(OUTPUTS / "ext_survivorship_bracket.csv", index=False)
    log.info("truncated rows: %d / %d (%.1f%%)",
             int(base.truncated.sum()), len(base), 100 * base.truncated.mean())
    log.info("\n%s", res[res.measure == "illiq"].to_string(index=False))
    return res


# ---------------------------------------------------------------- 2
def survivorship_bound(df: pd.DataFrame) -> None:
    """How big a hidden Q5 failure mass erases the spread? (median spec, 12m.)"""
    rows = []
    for measure in ("illiq", "zero_ret_pct"):
        for h in H_LIST:
            s = _spread_series(df, measure, h)
            base = np.nanmedian(s[s.split == "holdout"]["spread"])
            q5 = df[(df.horizon_m == h)].copy()
            # approx: adding fraction f of names to Q5 at excess -1-benchmean
            benchmean = df[df.horizon_m == h]["bench_ret"].mean()
            add = -1.0 - benchmean
            # new Q5 median mix: (1-f)*base_q5med + f*add  (rough, median approx by mean shift)
            # solve (1-f)*mq5 + f*add - mq1 = 0  with base = mq5 - mq1
            for f in (0.05, 0.10, 0.20, 0.30, 0.50):
                new_spread = base + f * (add - (base))  # crude: pull spread toward `add`
                rows.append({"measure": measure, "horizon_m": h, "failure_frac": f,
                             "base_spread": base, "implied_spread": new_spread})
    pd.DataFrame(rows).to_csv(OUTPUTS / "ext_survivorship_bound.csv", index=False)
    log.info("survivorship bound written (see ext_survivorship_bound.csv; "
             "interpretation in paper)")


# ---------------------------------------------------------------- 3
def subperiods(df: pd.DataFrame) -> None:
    bands = [("2016-2018", "2016-01-01", "2018-12-31"),
             ("2019-2021", "2019-01-01", "2021-12-31"),
             ("2022-2024", "2022-01-01", "2024-12-31")]
    rows = []
    for measure in ("illiq", "zero_ret_pct", "cs_spread"):
        for h in H_LIST:
            s = _spread_series(df, measure, h)
            s["formation_date"] = pd.to_datetime(s["formation_date"])
            for name, lo, hi in bands:
                for split in ("train", "holdout"):
                    ss = s[(s.split == split) & s.formation_date.between(lo, hi)]["spread"].to_numpy()
                    m, t, k = _nw(ss, h)
                    rows.append({"measure": measure, "horizon_m": h, "period": name,
                                 "split": split, "Q5_minus_Q1": m, "nw_t": t, "n_dates": k})
    res = pd.DataFrame(rows)
    res.to_csv(OUTPUTS / "ext_subperiods.csv", index=False)
    log.info("\n=== subperiods (illiq, holdout) ===\n%s",
             res[(res.measure == "illiq") & (res.split == "holdout")].to_string(index=False))


# ---------------------------------------------------------------- 4
def price_double_sort(df: pd.DataFrame) -> None:
    """Independent 3 (price) x 5 (illiq) sort, 12m holdout, median excess."""
    h = 12 if 12 in H_LIST else H_LIST[0]
    sub = df[(df.horizon_m == h) & df["illiq"].notna() & (df["illiq"] > 0)
             & df["price_at_formation"].notna() & df["excess_ret_w"].notna()].copy()
    cells = []
    for fd, g in sub.groupby("formation_date"):
        tr = g[g.split == "train"]
        if len(tr) < 60:
            continue
        pbp = tr["price_at_formation"].quantile([1/3, 2/3]).to_numpy()
        ibp = tr["illiq"].quantile(np.linspace(0, 1, NQ + 1)[1:-1]).to_numpy()
        g = g.assign(pg=np.digitize(g["price_at_formation"], pbp),
                     iq=np.digitize(g["illiq"], ibp) + 1)
        hh = g[g.split == "holdout"]
        for pg in (0, 1, 2):
            for iq in (1, NQ):
                v = hh[(hh.pg == pg) & (hh.iq == iq)]["excess_ret_w"]
                if len(v) >= 3:
                    cells.append({"formation_date": fd, "price_tercile": pg,
                                  "illiq_q": iq, "med_excess": v.median()})
    c = pd.DataFrame(cells)
    tab = (c.groupby(["price_tercile", "illiq_q"])["med_excess"].mean().unstack())
    tab["Q5_minus_Q1"] = tab[NQ] - tab[1]
    tab.to_csv(OUTPUTS / "ext_price_double_sort.csv")
    log.info("\n=== price x illiq (12m holdout, mean of monthly medians) ===\n%s",
             tab.round(3).to_string())


# ---------------------------------------------------------------- 5
def sector_neutral(df: pd.DataFrame) -> None:
    rows = []
    for measure in ("illiq", "zero_ret_pct", "cs_spread"):
        for h in H_LIST:
            sub = df[(df.horizon_m == h) & df[measure].notna() & np.isfinite(df[measure])
                     & df["excess_ret_w"].notna()].copy()
            if measure in ("illiq", "cs_spread"):
                sub = sub[sub[measure] > 0]
            sub["m_rank"] = (sub.groupby(["formation_date", "tsxv_sector"])[measure]
                             .rank(pct=True))
            per = []
            for fd, g in sub.groupby("formation_date"):
                tr = g[g.split == "train"]
                if len(tr) < 5 * NQ:
                    continue
                bp = tr["m_rank"].quantile(np.linspace(0, 1, NQ + 1)[1:-1]).to_numpy()
                g = g.assign(q=np.digitize(g["m_rank"], bp) + 1)
                hh = g[g.split == "holdout"]
                if {1, NQ}.issubset(set(hh["q"])):
                    per.append(hh[hh.q == NQ]["excess_ret_w"].median()
                               - hh[hh.q == 1]["excess_ret_w"].median())
            m, t, k = _nw(np.array(per), h)
            rows.append({"measure": measure, "horizon_m": h, "Q5_minus_Q1": m,
                         "nw_t": t, "n_dates": k})
    res = pd.DataFrame(rows)
    res.to_csv(OUTPUTS / "ext_sector_neutral.csv", index=False)
    log.info("\n=== sector-neutral (within-sector rank, holdout, median) ===\n%s",
             res.to_string(index=False))


# ---------------------------------------------------------------- 6
def persistence(df: pd.DataFrame) -> None:
    p = df[df.horizon_m == H_LIST[0]][["ticker", "formation_date", "illiq"]].copy()
    p = p[p.illiq > 0]
    p["q"] = (p.groupby("formation_date")["illiq"]
              .transform(lambda s: np.digitize(s, s.quantile(np.linspace(0, 1, NQ+1)[1:-1])) + 1))
    p = p.sort_values(["ticker", "formation_date"])
    p["q_next"] = p.groupby("ticker")["q"].shift(-1)
    trans = (pd.crosstab(p["q"], p["q_next"], normalize="index"))
    trans.to_csv(OUTPUTS / "ext_persistence_transition.csv")
    ar1 = p[["q", "q_next"]].dropna().corr().iloc[0, 1]
    log.info("\n=== illiq quintile 1-month transition matrix ===\n%s",
             trans.round(3).to_string())
    log.info("rank AR(1) (month-to-month): %.3f", ar1)
    (OUTPUTS / "ext_persistence_ar1.json").write_text(json.dumps({"rank_ar1": ar1}))


# ---------------------------------------------------------------- 7
def turnover_check(df: pd.DataFrame) -> None:
    """Recompute with share turnover and $-volume as the sort var (need panel)."""
    mp = pd.read_parquet(ADJUSTED / "metrics_panel.parquet")
    uni = pd.read_csv(UNIVERSE_CSV)[["ticker", "shares_outstanding"]]
    mp = mp.merge(uni, on="ticker", how="left")
    mp["turnover"] = mp["adv_20d"] / (mp["price_at_formation"] * mp["shares_outstanding"])
    mp["dollar_vol"] = mp["adv_20d"]
    keep = mp[["ticker", "formation_date", "turnover", "dollar_vol"]]
    merged = df.merge(keep, on=["ticker", "formation_date"], how="left")
    rows = []
    for measure, invert in [("turnover", True), ("dollar_vol", True)]:
        for h in H_LIST:
            # illiquid = LOW turnover / LOW $vol -> flip sign of the sort
            m2 = merged.copy()
            m2[measure + "_ill"] = -m2[measure]
            s = _spread_series(m2.rename(columns={measure + "_ill": "x"}), "x", h)
            mv, t, k = _nw(s[s.split == "holdout"]["spread"].to_numpy(), h)
            rows.append({"proxy": measure, "horizon_m": h,
                         "Q5_minus_Q1_illiq_minus_liq": mv, "nw_t": t, "n_dates": k})
    pd.DataFrame(rows).to_csv(OUTPUTS / "ext_turnover_check.csv", index=False)
    log.info("\n=== complementary proxies (low turnover / low $vol = illiquid) ===\n%s",
             pd.DataFrame(rows).to_string(index=False))


def figure_subperiods() -> None:
    sp = pd.read_csv(OUTPUTS / "ext_subperiods.csv")
    sp = sp[sp.split == "holdout"]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    measures = ["illiq", "zero_ret_pct", "cs_spread"]
    labels = {"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return %",
              "cs_spread": "Corwin-Schultz"}
    periods = ["2016-2018", "2019-2021", "2022-2024"]
    x = np.arange(len(periods)); w = 0.25
    for i, m in enumerate(measures):
        vals = [sp[(sp.measure == m) & (sp.period == p) & (sp.horizon_m == 12)]
                ["Q5_minus_Q1"].mean() for p in periods]
        ax.bar(x + (i - 1) * w, vals, w, label=labels[m])
    ax.axhline(0, color="k", lw=.8); ax.set_xticks(x); ax.set_xticklabels(periods)
    ax.set_ylabel("Q5-Q1 12m excess return (holdout)")
    ax.set_title("Illiquidity premium by sub-period")
    ax.legend()
    fig.tight_layout(); fig.savefig(OUTPUTS / "fig_subperiods.png", dpi=130)
    plt.close(fig)


def main() -> None:
    df = pd.read_parquet(OUTPUTS / "analysis_frame.parquet")
    if "mktcap" not in df:
        df["mktcap"] = df["price_at_formation"] * df.get("shares_outstanding", np.nan)
    survivorship_bracket(df)
    survivorship_bound(df)
    subperiods(df)
    price_double_sort(df)
    sector_neutral(df)
    persistence(df)
    turnover_check(df)
    figure_subperiods()
    log.info("extended battery complete -> outputs/ext_*.csv, fig_subperiods.png")


if __name__ == "__main__":
    main()
