# TSXV Liquidity Puzzle — findings (v2, run 2026-09-08)

Full write-up: **`paper/Do Hard to Trade Stocks Actually Pay Off? - Yonatan Brunshtein.docx`**.
This file is the executive summary.

## Setup

- Universe: **1,267** cleaned TSXV common shares (full exchange directory, NEX excluded,
  CPCs/warrants/units/prefs removed); **1,127** scored after price-history + QA screens.
- Prices: TMX Money GraphQL daily OHLCV (Alpha Vantage adjusted feed is paywalled; Yahoo
  IP-blocked mid-collection). Benchmark: S&P/TSX Venture Composite (TMX `JX` / Yahoo `^SPCDNX`).
- Monthly formation Jan-2016 → Dec-2024 (108 dates), trailing 12-mo illiquidity, forward
  6/12/24-mo excess return, winsorized 1/99 within each cross-section.
- **70/30 ticker holdout frozen before any result** (887 train / 380 holdout, seed 424242).
  All numbers below are holdout.

## Bottom line

**The sign of the illiquidity–return relation depends on which measure you use.**

| Proxy | Family | Q5−Q1 12-mo (median spec) | NW t | Verdict |
|---|---|---|---|---|
| Amihud ILLIQ | price impact | **+0.43** | 6.6 | H1 (illiquid outperforms) |
| Zero-return days % | no-trade freq | **+0.34** | 4.8 | H1 |
| Low share turnover | activity | **+0.21** | 6.0 | H1 |
| Low dollar volume | activity | **+0.44** | 6.9 | H1 |
| Corwin–Schultz spread | quoted cost | **−0.12** | −1.8 | weak H2 (wide-spread underperforms) |

Four activity measures say illiquidity is rewarded; the spread estimator says the opposite.
They disagree because on TSXV the Corwin–Schultz estimate is **negatively** rank-correlated
with the activity measures (−0.36 with Amihud) — it behaves like a volatility proxy here,
not a trading-cost proxy.

## The H1 result (Amihud / zero-return) survives everything

| Cut | Amihud Q5−Q1 12-mo (holdout) |
|---|---|
| Equal-weighted mean (spec'd) | +0.65 |
| **Median within quintile** (skew-robust, primary) | **+0.43** |
| Value-weighted | +0.54 |
| 3-day average prices (bounce control) | +0.63 |
| Price ≥ C$0.10 (drop sub-dime tail) | +0.32 |
| Median + price ≥ C$0.10 (most conservative) | +0.26 |
| Sector-neutral (rank within sector×date) | +0.41 |
| Fama–MacBeth b(illiq pct), size + sector controlled | +0.39 (t 7.7) |

- **Monotonic** across all 5 quintiles (Fig 1), not an extreme-bucket jump.
- **Replicates** on the untouched 30% at every horizon (t 5.8–9.2).
- **Price double-sort**: within the low-price tercile Q5−Q1 = +0.36; within the high-price
  tercile = +0.62. The effect is present — stronger — among higher-priced names, so it is
  *not* a low-price/reversal artifact. (Mid tercile ≈ 0, unexplained, flagged.)
- **Persistent**: illiquidity-quintile 1-month transition is 95% diagonal, rank AR(1) = 0.98.
- **Sub-periods** (12-mo): 2016–18 +0.50, 2019–21 +0.52, 2022–24 **+0.21** — shrinks ~55%
  after the booms but stays positive and significant (t 5.4).

## Why the magnitudes are not investable

- 12-mo excess return: **median −0.13, mean +0.10**. The distribution is violently
  right-skewed; equal-weighted means track the fat right tail (Fig 3). Median spec used as
  primary for this reason.
- Q5 = the least-tradable quarter of the least-tradable exchange in North America; median
  Q5 name trades a few thousand $/day. Buying the basket moves it.
- Time profile looks like episodic beta to speculative sentiment (huge in 2016 & 2020–21
  manias), not a steady risk premium.

## Survivorship — bounded, not fixed

- **In-sample attrition is negligible**: only 0.4% of rows are truncated; re-pricing them at
  −100% moves the Amihud 12-mo spread from +0.434 to +0.432.
- **The real exposure is external**: the universe is names still listed in 2026; every junior
  that failed/delisted 2016–2024 is absent, and on TSXV that is a large number. No free
  point-in-time constituent list or comprehensive delisted feed exists.
- **Direction is known**: failed juniors are disproportionately illiquid with steeply
  negative returns → excluding them inflates the Q5 return and the H1 spread. The H1 numbers
  are an **upper bound**. Rough bound: a hidden 20% of Q5 at −100% erases ~half the 12-mo
  spread; ~30% erases most of it.
- **The CS H2 lean runs against this bias** — survivorship pushes every measure toward H1,
  yet CS resists — which is why the divergence is the more informative result.

## Reproduce

`./.venv/bin/python run_all.py` — deterministic pipeline, resumes from cache. Stages:
build_universe → fetch → holdout → metrics → forward_returns → analysis → robustness →
extended → report → paper_figures.
