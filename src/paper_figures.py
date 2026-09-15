"""Publication figures for the paper. Writes outputs/paper/fig_*.png."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import CFG, OUTPUTS, get_logger
from analysis import build_frame, MEASURES, N_QUANTILES

NQ = N_QUANTILES


def median_quintiles(df, measure, horizon, split="holdout"):
    """Per-formation-date, median within-quintile excess return; TRAIN breakpoints.

    Matches the paper's primary specification (skew-robust). Returns a frame with
    one row per formation date: q1..q5 medians and the Q5-Q1 spread.
    """
    sub = df[(df.horizon_m == horizon) & df[measure].notna() & np.isfinite(df[measure])
             & df["excess_ret_w"].notna()].copy()
    if measure in ("illiq", "cs_spread"):
        sub = sub[sub[measure] > 0]
    rows = []
    for fd, g in sub.groupby("formation_date"):
        tr = g[g.split == "train"]
        if tr[measure].nunique() < NQ + 1 or len(tr) < 5 * NQ:
            continue
        bp = tr[measure].quantile(np.linspace(0, 1, NQ + 1)[1:-1]).to_numpy()
        g = g.assign(q=np.digitize(g[measure].to_numpy(), bp) + 1)
        gg = g[g.split == split]
        if not {1, NQ}.issubset(set(gg["q"])):
            continue
        med = gg.groupby("q")["excess_ret_w"].median()
        rows.append({"formation_date": fd,
                     **{f"q{k}": med.get(k, np.nan) for k in range(1, NQ + 1)},
                     "spread": med.get(NQ, np.nan) - med.get(1, np.nan)})
    return pd.DataFrame(rows)

log = get_logger("paper_figures")
PDIR = OUTPUTS / "paper"
PDIR.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white"})
LAB = {"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return days %",
       "cs_spread": "Corwin–Schultz spread"}
BLUE, RED, GREEN = "#2E5A87", "#B0413E", "#3B7A57"


def fig_quintile_bars(df):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, m in zip(axes, MEASURES):
        mq = median_quintiles(df, m, 12)
        qc = [f"q{k}" for k in range(1, N_QUANTILES + 1)]
        vals = [mq[q].mean() for q in qc]
        ax.bar(range(1, 6), vals, color=[BLUE]*4 + [RED])
        ax.axhline(0, color="k", lw=.7)
        ax.set_title(LAB[m], fontsize=10)
        ax.set_xlabel("illiquidity quintile (1=liquid, 5=illiquid)")
    axes[0].set_ylabel("median 12-mo excess return")
    fig.suptitle("Figure 1.  Forward excess return by illiquidity quintile (holdout sample)",
                 fontsize=11, y=1.05)
    fig.tight_layout()
    fig.savefig(PDIR / "fig1_quintile_bars.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_spread_over_time(df):
    fig, ax = plt.subplots(figsize=(10, 4))
    for m, c in zip(MEASURES, (BLUE, GREEN, RED)):
        mq = median_quintiles(df, m, 12).sort_values("formation_date")
        ax.plot(pd.to_datetime(mq.formation_date),
                mq["spread"].rolling(3, min_periods=1).mean(), label=LAB[m], color=c, lw=1.5)
    ax.axhline(0, color="k", lw=.8)
    ax.set_ylabel("Q5 − Q1  (12-mo excess return, 3-mo MA)")
    ax.set_title("Figure 2.  The illiquidity spread over time (holdout sample)", fontsize=11)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PDIR / "fig2_spread_over_time.png", dpi=150)
    plt.close(fig)


def fig_return_distribution(df):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True)
    for ax, h in zip(axes, [6, 12, 24]):
        x = df[df.horizon_m == h]["excess_ret_w"].clip(-2, 5)
        ax.hist(x, bins=80, color=BLUE, alpha=.8)
        ax.axvline(x.mean(), color=RED, lw=1.6, label=f"mean {x.mean():+.2f}")
        ax.axvline(x.median(), color="k", lw=1.6, ls="--", label=f"median {x.median():+.2f}")
        ax.set_title(f"{h}-month horizon", fontsize=10)
        ax.set_xlabel("excess return (winsorized)")
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_ylabel("frequency")
    fig.suptitle("Figure 3.  Forward excess returns are heavily right-skewed — "
                 "mean ≠ median", fontsize=11, y=1.04)
    fig.tight_layout()
    fig.savefig(PDIR / "fig3_return_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _block_bootstrap_ci(series, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    s = np.asarray(series, float); s = s[np.isfinite(s)]
    if len(s) < 10:
        return np.nan, np.nan, np.nan
    means = [rng.choice(s, len(s), replace=True).mean() for _ in range(n)]
    return float(np.mean(s)), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def fig_forest(df):
    rows = []
    for m in MEASURES:
        s = median_quintiles(df, m, 12)["spread"]
        mean, lo, hi = _block_bootstrap_ci(s)
        rows.append((LAB[m], mean, lo, hi))
    # turnover + dollar-vol from ext file
    ext = pd.read_csv(OUTPUTS / "ext_turnover_check.csv")
    for _, r in ext[ext.horizon_m == 12].iterrows():
        nm = {"turnover": "Low share turnover", "dollar_vol": "Low dollar volume"}[r["proxy"]]
        rows.append((nm, r["Q5_minus_Q1_illiq_minus_liq"], np.nan, np.nan))
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for i, (nm, mn, lo, hi) in enumerate(rows):
        col = RED if mn < 0 else BLUE
        if np.isfinite(lo):
            ax.plot([lo, hi], [i, i], color=col, lw=2)
        ax.plot(mn, i, "o", color=col, ms=7)
        ax.text(mn, i + .18, f"{mn:+.2f}", ha="center", fontsize=8)
    ax.axvline(0, color="k", lw=.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel("Q5 − Q1  (12-mo excess return, holdout; bars = block-bootstrap 95% CI)")
    ax.set_title("Figure 4.  Five liquidity proxies, one disagreement", fontsize=11)
    fig.tight_layout()
    fig.savefig(PDIR / "fig4_forest.png", dpi=150)
    plt.close(fig)


def fig_persistence():
    t = pd.read_csv(OUTPUTS / "ext_persistence_transition.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(4.6, 4))
    im = ax.imshow(t.values, cmap="Blues", vmin=0, vmax=1)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{t.values[i, j]:.2f}", ha="center", va="center",
                    color="white" if t.values[i, j] > .5 else "black", fontsize=9)
    ax.set_xticks(range(5)); ax.set_xticklabels(range(1, 6))
    ax.set_yticks(range(5)); ax.set_yticklabels(range(1, 6))
    ax.set_xlabel("quintile next month"); ax.set_ylabel("quintile this month")
    ax.set_title("Figure 5.  Illiquidity-quintile\n1-month transition probabilities", fontsize=10)
    fig.colorbar(im, fraction=.046)
    fig.tight_layout()
    fig.savefig(PDIR / "fig5_persistence.png", dpi=150)
    plt.close(fig)


def fig_double_sort():
    d = pd.read_csv(OUTPUTS / "ext_price_double_sort.csv")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    labs = ["low price", "mid price", "high price"]
    x = np.arange(3); w = .35
    ax.bar(x - w/2, d["1"], w, label="Q1 (liquid)", color=BLUE)
    ax.bar(x + w/2, d["5"], w, label="Q5 (illiquid)", color=RED)
    for i, v in enumerate(d["Q5_minus_Q1"]):
        ax.text(i, max(d["1"][i], d["5"][i]) + .03, f"Δ={v:+.2f}", ha="center", fontsize=9)
    ax.axhline(0, color="k", lw=.7)
    ax.margins(y=0.18)
    ax.set_xticks(x); ax.set_xticklabels(labs)
    ax.set_ylabel("median 12-mo excess return (holdout)")
    ax.set_title("Figure 6.  Illiquidity effect within price terciles "
                 "(independent 3×5 sort)", fontsize=10)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PDIR / "fig6_double_sort.png", dpi=150)
    plt.close(fig)


def fig_subperiods():
    sp = pd.read_csv(OUTPUTS / "ext_subperiods.csv")
    sp = sp[(sp.split == "holdout") & (sp.horizon_m == 12)]
    periods = ["2016-2018", "2019-2021", "2022-2024"]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = np.arange(3); w = .25
    for i, (m, c) in enumerate(zip(MEASURES, (BLUE, GREEN, RED))):
        vals = [sp[(sp.measure == m) & (sp.period == p)]["Q5_minus_Q1"].mean() for p in periods]
        ax.bar(x + (i-1)*w, vals, w, label=LAB[m], color=c)
    ax.axhline(0, color="k", lw=.7)
    ax.set_xticks(x); ax.set_xticklabels(periods)
    ax.set_ylabel("Q5 − Q1  (12-mo excess return, holdout)")
    ax.set_title("Figure 7.  The spread by sub-period", fontsize=11)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PDIR / "fig7_subperiods.png", dpi=150)
    plt.close(fig)


def main():
    df = build_frame()
    fig_quintile_bars(df)
    fig_spread_over_time(df)
    fig_return_distribution(df)
    fig_forest(df)
    fig_persistence()
    fig_double_sort()
    fig_subperiods()
    log.info("wrote paper figures -> %s", PDIR)


if __name__ == "__main__":
    main()
