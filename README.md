# The TSXV Liquidity Puzzle

**Does a TSX Venture Exchange stock's trailing illiquidity predict its forward return? Yes — but the sign depends entirely on how you measure "illiquid."**

An independent empirical study of 1,127 TSX Venture Exchange (TSXV) common stocks, January 2016 – December 2024. Every research decision — the universe, the illiquidity measures, the time horizons, a 30% ticker holdout — was fixed *before* any result was computed. Full write-ups, all figures, and the complete reproducible pipeline are in this repository.

**Read this first:** [`paper/TSXV_Liquidity_Puzzle_PlainEnglish.docx`](paper/TSXV_Liquidity_Puzzle_PlainEnglish.docx) — the plain-language edition, no finance background assumed, glossary included.
For the formal version with statistical notation: [`paper/TSXV_Liquidity_Puzzle.docx`](paper/TSXV_Liquidity_Puzzle.docx).

---

## The finding, in one paragraph

Four different ways of measuring "how illiquid is this stock" — the Amihud (2002) price-impact ratio, the share of no-trade days, share turnover, and dollar volume — all say the same thing: the least-liquid fifth of TSXV stocks beat the most-liquid fifth by roughly **26–43 percentage points** over the following 12 months (median-based, out-of-sample, statistically significant, holds up across a full robustness battery). A fifth measure, the Corwin–Schultz (2012) bid-ask spread estimator, says the *opposite* — wide-spread names underperform. The two families of measures disagree because, on this exchange, the spread estimator is negatively correlated with the activity measures and behaves more like a volatility proxy than a trading-cost proxy. The activity-based effect is real and replicates on data untouched while building the method, but it is inflated by survivorship bias (the sample is companies still listed in 2026), concentrated in speculative booms, and — see [`outputs/strategy/`](outputs/strategy/) — **does not survive as an actual tradable strategy** once realistic transaction costs and portfolio breadth are imposed. This is a research finding about how returns are distributed across the liquidity spectrum on a microcap exchange, not a trading system.

## Repository structure

```
tsxv-liquidity-study/
├── paper/
│   ├── TSXV_Liquidity_Puzzle.docx              formal/technical edition
│   ├── TSXV_Liquidity_Puzzle_PlainEnglish.docx plain-language edition (start here)
│   ├── build_paper.py                          generates the technical docx from outputs/
│   └── build_article.py                        generates the plain-English docx from outputs/
├── config.yaml            every locked parameter — window, horizons, winsorization, holdout seed
├── src/
│   ├── build_universe.py  Stage 0 — TSXV issuer directory -> cleaned, sector-tagged universe
│   ├── fetch.py            Stage 1 — daily OHLCV + benchmark, cached, resumable
│   ├── metrics.py          Stage 2 — Amihud / zero-return / Corwin-Schultz per name per month
│   ├── holdout.py          Stage 3 — the 70/30 ticker split, written ONCE, never re-rolled
│   ├── forward_returns.py  Stage 4 — 6/12/24m excess returns, winsorized, look-ahead safe
│   ├── analysis.py         Stage 5 — portfolio sorts + Fama-MacBeth, train vs. holdout
│   ├── robustness.py       Stage 5b — the stress-test battery
│   ├── extended.py         Stage 5c — survivorship bracket, sub-periods, double-sort, persistence
│   ├── strategy_backtest.py  is this actually tradable? cost- and turnover-aware simulation
│   ├── report.py / paper_figures.py   figures and markdown summaries
│   └── common.py           shared config, paths, sector mapping
├── outputs/                every result table, figure, and the FINDINGS.md summary
├── tests/                  unit tests for the illiquidity estimators (known-input checks)
└── run_all.py              runs every stage in order, end to end
```

## Reproducing this

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python run_all.py              # full pipeline, resumes from cache
./.venv/bin/python -m pytest tests/ -q     # estimator unit tests
./.venv/bin/python src/strategy_backtest.py  # the tradability check
cd paper && ../.venv/bin/python build_paper.py && ../.venv/bin/python build_article.py
```

Every parameter — the sample window, the illiquidity formulas, the holdout seed, the winsorization rule — lives in [`config.yaml`](config.yaml). Nothing downstream is hard-coded. Re-running from cached inputs reproduces every number in both papers exactly; both `build_*.py` scripts pull their numbers live from `outputs/*.csv`, so the papers can never drift from the code that produced them.

**On the data**: this repository does **not** redistribute the raw TMX Money price/reference data (see [Data access](#data-access) below) — only the derived, aggregated results. `src/fetch.py` and `src/build_universe.py` document exactly which public endpoints were used and how to re-pull the same data yourself.

## Data access

- **Universe & sector data**: TMX's public TSX Venture issuer directory and TMX Money's public GraphQL service (`getQuoteBySymbol`, `getTimeSeriesData`) — no API key, no paid subscription. Endpoints and query shapes are in `src/build_universe.py` and `src/fetch.py`.
- **Benchmark**: S&P/TSX Venture Composite, TMX symbol `JX`, same service.
- Re-pulling from scratch (`run_all.py` from stage 0) takes roughly 20–30 minutes and reconstructs the full dataset from public sources.

## What's in `outputs/`

| File | What it is |
|---|---|
| `FINDINGS.md` | one-page plain summary of the whole study |
| `spread_summary.csv` | headline Q5−Q1 portfolio-sort results, train vs. holdout |
| `fama_macbeth.csv` | cross-sectional regression coefficients (illiquidity + size + sector) |
| `robustness.csv` | every alternative specification tested |
| `ext_*.csv` | survivorship bracket, sub-periods, price double-sort, sector-neutral, persistence, turnover checks |
| `strategy/` | the cost- and turnover-aware tradability test — read this before treating anything above as a strategy |
| `REPORT.md` | full result tables in one document |

## Limitations (see the papers for the full discussion)

- **Survivorship bias, unresolved.** The universe is TSXV names still listed as of the data pull; every company that failed or delisted 2016–2024 is absent, and no free point-in-time constituent list exists. The direction of the bias is known (it inflates the activity-based finding); the magnitude is bounded, not eliminated.
- **Company size is approximated** using current shares outstanding applied to all historical dates (historical share counts for TSXV names aren't freely available). Results are checked against price alone as an alternative size proxy.
- **One exchange, one period.** No claim of generalization beyond TSXV, 2016–2024.
- **Not a trading strategy**, and the repository includes the evidence for why: see `outputs/strategy/`.

## Citation

If you reference this work:

> [Author name]. "The TSX Venture Liquidity Puzzle: When Illiquidity Pays and When It Doesn't." Working paper, September 2026.

## AI disclosure

Claude (Anthropic) assisted with the data-collection and analysis code, statistical structure, figure generation, and drafting of both paper editions. All research decisions — what to measure, how to define it, the interpretation of results, and the framing of the contribution — are the author's, who is responsible for the content in full.

## License

Code in this repository is provided as-is for research transparency and reproducibility. No warranty. This is not investment advice, and nothing in this repository or the accompanying papers constitutes a recommendation to buy or sell any security.
