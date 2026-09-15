"""Step 6 — human-readable outputs.

  outputs/REPORT.md                 quintile tables + spread + Fama-MacBeth, train vs holdout
  outputs/fig_quintile_spread.png   Q5-Q1 spread over formation dates (per measure, 12m)
  outputs/fig_quintile_bars.png     mean excess return by quintile (per measure/horizon)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import CFG, OUTPUTS, get_logger
from analysis import MEASURES, N_QUANTILES, build_frame, portfolio_sort

log = get_logger("report")

PRETTY = {"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return days %",
          "cs_spread": "Corwin-Schultz spread"}


def _md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt="+.4f")


def write_markdown() -> None:
    spread = pd.read_csv(OUTPUTS / "spread_summary.csv")
    quint = pd.read_csv(OUTPUTS / "quintile_returns.csv")
    fm = pd.read_csv(OUTPUTS / "fama_macbeth.csv")

    lines = ["# TSXV Liquidity Discount — results", "",
             f"_Generated {pd.Timestamp.utcnow():%Y-%m-%d %H:%M UTC}_", "",
             "Direction not assumed in advance: H1 (illiquidity premium, Q5−Q1 > 0) "
             "vs H2 (value trap, Q5−Q1 < 0). The holdout column is the test.", "",
             "## A. Portfolio sort — Q5 (most illiquid) − Q1 (most liquid)", "",
             "Pooled mean of the per-formation-date equal-weighted excess-return spread; "
             "`nw_t` is a Newey-West t-stat (lags = horizon in months).", "",
             _md_table(spread), "",
             "### Mean excess return by quintile", ""]
    for measure in MEASURES:
        sub = quint[quint["measure"] == measure]
        if sub.empty:
            continue
        lines += [f"**{PRETTY[measure]}**", "", _md_table(sub), ""]

    lines += ["## B. Fama-MacBeth cross-sectional regression", "",
              "`excess_w ~ illiq_rank + log_mktcap + C(sector)`, one cross-section per "
              "formation date, coefficients averaged with Newey-West t "
              "(lags = horizon). `b_illiq` is the coefficient on the within-date "
              "illiquidity percentile (0..1).", "",
              _md_table(fm[["measure", "horizon_m", "split", "n_dates",
                            "b_illiq", "t_illiq", "b_size", "t_size"]]), ""]

    # robustness battery
    rb_path = OUTPUTS / "robustness.csv"
    if rb_path.exists():
        rb = pd.read_csv(rb_path)
        lines += ["## C. Robustness — is the spread real or a small-price / skew artifact?", "",
                  "Each variant neutralises one suspected artifact channel. HOLDOUT "
                  "Q5−Q1 shown; `median within quintile` and `price ≥ $0.10` are the "
                  "decisive ones (an equal-weighted mean of a right-skewed penny-stock "
                  "distribution mostly measures the fattest right tail).", ""]
        for measure in MEASURES:
            piv = (rb[(rb.measure == measure) & (rb.split == "holdout")]
                   .pivot(index="variant", columns="horizon_m", values="Q5_minus_Q1"))
            tp = (rb[(rb.measure == measure) & (rb.split == "holdout")]
                  .pivot(index="variant", columns="horizon_m", values="nw_t"))
            tbl = piv.copy()
            for c in piv.columns:
                tbl[c] = [f"{piv.loc[i, c]:+.3f} (t={tp.loc[i, c]:+.1f})" for i in piv.index]
            lines += [f"**{PRETTY[measure]}** — HOLDOUT Q5−Q1 (Newey-West t)", "",
                      tbl.reset_index().to_markdown(index=False), ""]

    # replication read
    lines += ["## Holdout replication (primary spec)", ""]
    for measure in MEASURES:
        for h in [int(x) for x in CFG["forward_horizons_months"]]:
            tr = spread[(spread.measure == measure) & (spread.horizon_m == h)
                        & (spread.split == "train")]
            ho = spread[(spread.measure == measure) & (spread.horizon_m == h)
                        & (spread.split == "holdout")]
            if tr.empty or ho.empty:
                continue
            st, sh = tr.iloc[0]["mean_Q5_minus_Q1"], ho.iloc[0]["mean_Q5_minus_Q1"]
            th = ho.iloc[0]["nw_t"]
            agree = np.sign(st) == np.sign(sh)
            verdict = ("**replicates** (same sign, holdout |t|≥1.96)"
                       if agree and abs(th) >= 1.96
                       else "sign agrees, holdout not significant" if agree
                       else "**does not replicate** (sign flips)")
            lines.append(f"- {PRETTY[measure]} {h}m: train {st:+.3f} / "
                         f"holdout {sh:+.3f} (t={th:+.2f}) — {verdict}")
    lines.append("")

    (OUTPUTS / "REPORT.md").write_text("\n".join(lines))
    log.info("wrote %s", OUTPUTS / "REPORT.md")


def make_figures() -> None:
    df = build_frame()
    horizons = [int(h) for h in CFG["forward_horizons_months"]]

    # --- spread over time, 12m horizon (or first available) --------------------
    h_show = 12 if 12 in horizons else horizons[0]
    fig, ax = plt.subplots(figsize=(11, 5))
    for measure in MEASURES:
        ps = portfolio_sort(df, measure, h_show)
        s = (ps[ps["split"] == "holdout"] if not ps[ps["split"] == "holdout"].empty
             else ps[ps["split"] == "train"])
        if s.empty:
            continue
        s = s.sort_values("formation_date")
        ax.plot(pd.to_datetime(s["formation_date"]),
                s["spread"].rolling(3, min_periods=1).mean(),
                label=f"{PRETTY[measure]}", lw=1.6)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title(f"Q5−Q1 forward {h_show}-month excess return over time "
                 f"(3-formation moving average)")
    ax.set_ylabel("Q5 − Q1 excess return")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUTS / "fig_quintile_spread.png", dpi=130)
    plt.close(fig)

    # --- quintile bar charts -------------------------------------------------
    fig, axes = plt.subplots(len(MEASURES), len(horizons),
                             figsize=(4 * len(horizons), 3 * len(MEASURES)),
                             squeeze=False)
    for r, measure in enumerate(MEASURES):
        for c, h in enumerate(horizons):
            ax = axes[r][c]
            ps = portfolio_sort(df, measure, h)
            s = ps[ps["split"] == "holdout"]
            s = s if not s.empty else ps[ps["split"] == "train"]
            if s.empty:
                ax.set_visible(False)
                continue
            qcols = [f"q{k}" for k in range(1, N_QUANTILES + 1)]
            ax.bar(range(1, N_QUANTILES + 1), [s[q].mean() for q in qcols],
                   color="#4C72B0")
            ax.axhline(0, color="k", lw=0.8)
            ax.set_title(f"{PRETTY[measure]} · {h}m", fontsize=9)
            ax.set_xticks(range(1, N_QUANTILES + 1))
    fig.suptitle("Mean forward excess return by illiquidity quintile "
                 "(Q1 = most liquid, Q5 = most illiquid)")
    fig.tight_layout()
    fig.savefig(OUTPUTS / "fig_quintile_bars.png", dpi=130)
    plt.close(fig)
    log.info("wrote figures to %s", OUTPUTS)


def main() -> None:
    write_markdown()
    make_figures()


if __name__ == "__main__":
    main()
