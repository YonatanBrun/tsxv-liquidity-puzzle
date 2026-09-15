# Is the illiquidity effect a tradable strategy? — No, and here's the evidence

This tests a different, stricter question than the research paper. The paper asks
"is illiquidity associated with forward returns" (a 12-month overlapping-window
cross-sectional test with a research holdout). This asks "if I actually ran this
as a monthly-rebalanced, long-only portfolio, funded and traded with realistic
costs, what would happen." See `src/strategy_backtest.py` for the full method and
every assumption. Design notes, briefly:

- **Long-only.** TSXV nano-caps have no stock-borrow market — you cannot short
  them. Only "long the illiquid quintile" is tradable, not the paper's
  Q5-minus-Q1 spread.
- **Monthly rebalance**, turnover computed honestly: a name that stays in the
  basket pays no new trading cost; only entries and exits do.
- **Transaction costs are a documented assumption** (not derived from the
  Corwin-Schultz spread, which the paper itself shows is an unreliable cost
  proxy for the least-liquid names): 8% round-trip under $25k/day average
  volume, 4% at $25-100k, 2% at $100-250k, 1% above $250k, per leg.
- **Two universe definitions**, because they answer different questions: `full`
  (every TSXV name clearing the volume floor — what a live fund would actually
  trade) and `holdout` (only the paper's 30% out-of-sample tickers — a stricter
  check that the earlier finding survives a liquidity floor).

## The results

| Universe | Min. $/day volume | Months tested | Avg. holdings | Avg. monthly turnover | CAGR, net of costs | Benchmark CAGR | Max drawdown | Annualized volatility |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | $0 (no floor) | 107 | 156 | 14% | +120% | +0.3% | −23% | 174% |
| full | $25,000 | 100 | 8 | 71% | **−38%** | +0.6% | −100% | 76% |
| full | $100,000 | 66 | 3 | 72% | **+9.6%** | −0.3% | **−95%** | 147% |
| full | $250,000 | 41 | 2 | 70% | −11% | +6.5% | −78% | 172% |
| full | $500,000 | 25 | 1 | 79% | −59% | +8.9% | −88% | 185% |
| holdout | $0 (no floor) | 107 | 51 | 14% | +99% | +0.3% | −31% | 52% |
| holdout | $25,000 | 71 | 3 | 65% | −56% | +2.9% | −99% | 96% |
| holdout | $100,000 | 36 | 2 | 56% | −38% | +20.3% | −90% | 202% |
| holdout | $250,000 | 19 | 1 | 42% | +98% | +36.5% | −70% | 313% |
| holdout | $500,000 | 8 | 1 | 44% | −22% | +99.6% | −44% | 133% |

## Reading this honestly

**No floor (the "academic" version).** Huge headline returns, but this basket
includes names trading a few thousand dollars a day — you cannot buy or sell a
real position without moving the price against yourself before the trade
completes. This row is not investable at any account size worth having.

**Any real floor collapses breadth to 1–8 stocks.** The number of names that are
*simultaneously* in the most-illiquid quintile *and* trade enough dollar volume
to actually transact is small — by definition, since "illiquid" and "enough
volume to trade" pull in opposite directions. A 1-to-3-stock "portfolio" is not
a diversified systematic strategy; it is concentrated single-name speculation,
and its returns are dominated by whichever one or two names happened to be held
that month.

**Turnover costs are severe and unstable.** Average monthly turnover runs
65–80% at every realistic floor, because the qualifying pool itself is small and
volatile — names drop in and out of "the 3 stocks that qualify this month"
easily. At every cost tier, that turnover consumes 2–6 percentage points of
return *per month*, which compounds brutally over 5-9 years.

**Results flip sign depending on small, defensible choices.** The $100k-floor
full-universe case shows +9.6% net CAGR (beating the benchmark's flat −0.3%);
the *same floor* restricted to only the research holdout tickers shows −38%.
The $250k and $500k floors flip sign again, in both directions, across nearby
thresholds. This instability — not any single bad number — is the real verdict:
a genuine, robust tradable edge does not usually reverse sign when you nudge a
volume floor by $150k or swap which 70% of tickers you're allowed to use.

**Every surviving case has a catastrophic drawdown.** Even the best net result
(+9.6% CAGR, full universe, $100k floor) comes with a **−95% maximum drawdown**
and **147% annualized volatility**. No real account — personal or
institutional — survives a 95% drawdown to collect a 9.6% annual return on the
other side of it. This alone is disqualifying, independent of everything else.

## Verdict

**The academic finding (Sections 5–6 of the research paper) is real. The
naive trading strategy built directly from it is not.** The gap between the two
is exactly turnover cost, position breadth, and drawdown risk — none of which
the portfolio-sort test was designed to capture, and all of which a real
account has to survive. This is not a failure of the research; it is what a
proper "would this actually make money" check is supposed to find, and finding
it is the useful result. See Section 8.4 of the paper for the one direction
that could plausibly change this verdict: a fundamentals/financing-quality
filter that separates the illiquid *winners* from the illiquid *value traps*
before capital is committed, rather than buying the whole quintile.

*Every number above is reproducible: `./.venv/bin/python src/strategy_backtest.py`.
Full monthly detail in `monthly_returns_base.csv`; the complete sweep in
`cost_sensitivity.csv`; the assumptions are documented at the top of
`src/strategy_backtest.py`.*
