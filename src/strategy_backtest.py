"""Strategy backtest — does the illiquidity effect survive as an actual tradable
monthly-rebalanced portfolio, with realistic turnover and transaction costs?

This is deliberately a DIFFERENT, stricter test than the research paper's portfolio
sort. The paper asks "is illiquidity associated with forward returns" (a 12-month
overlapping-window cross-sectional test). This asks "if I actually ran this as a
monthly long-only portfolio, funded, traded, and taxed by realistic costs, what
would my equity curve look like." The two can legitimately give different answers.

Design choices, stated up front because they materially affect the result:

  - LONG-ONLY. TSXV nano-caps have no stock-borrow market; you cannot short them.
    So "Q5 minus Q1" (the paper's headline number) is not a tradable strategy —
    only "long Q5" is. This backtest holds Q5 (most illiquid, subject to a
    liquidity floor) and compares it to just holding the benchmark index.
  - Monthly holding period (not 6/12/24mo), because that's the natural cadence
    of a monthly-rebalanced portfolio and it lets turnover be computed honestly:
    a name that stays in the basket from one month to the next is NOT re-traded,
    so it pays no incremental cost that month. Only entries and exits pay costs.
  - Universe/breakpoints: quintile breakpoints are computed from the TRAIN
    tickers only (as in the paper); the simulated portfolio only ever holds
    HOLDOUT tickers, so this remains an out-of-sample simulation, not a fit.
  - Transaction costs are a DOCUMENTED ASSUMPTION, not derived from Corwin-Schultz
    (the paper shows CS is an unreliable cost proxy for exactly the least-liquid
    names). Tiered by 20-day average dollar volume, round-trip (entry+exit charged
    once each, i.e. this multiplier is applied once per trade leg):
        ADV <  $25k/day   -> 8.0% per leg  (very thin, real impact is severe)
        ADV $25k-$100k    -> 4.0% per leg
        ADV $100k-$250k   -> 2.0% per leg
        ADV >= $250k      -> 1.0% per leg
    These are estimates from general microcap-market experience, not TSXV-specific
    fills. Treat every number downstream as sensitive to this assumption and check
    the sensitivity table this script also produces.
  - Position sizing cap: no single name may exceed `max_pct_of_adv` of its own
    20-day dollar volume (default 5%), which caps how much capital the strategy
    could actually deploy before the ADV floor stops mattering. This is reported,
    not enforced on the return (the portfolio is equal-weighted per name; the cap
    tells you the capacity ceiling, not a return adjustment).

Outputs: outputs/strategy/backtest_summary.csv, equity_curve.png, cost_sensitivity.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import ADJUSTED, OUTPUTS, UNIVERSE_CSV, get_logger
from holdout import load_split
from metrics import formation_dates

log = get_logger("strategy_backtest")
SDIR = OUTPUTS / "strategy"
SDIR.mkdir(exist_ok=True)

N_Q = 5
COST_TIERS = [(25_000, 0.080), (100_000, 0.040), (250_000, 0.020), (np.inf, 0.010)]
MAX_PCT_OF_ADV = 0.05


def cost_for_adv(adv: float) -> float:
    for cap, cost in COST_TIERS:
        if adv < cap:
            return cost
    return COST_TIERS[-1][1]


def one_month_fwd_returns(tickers, fdates) -> pd.DataFrame:
    """1-month forward adjusted-close return per ticker per formation date."""
    rows = []
    for tk in tickers:
        f = ADJUSTED / f"{tk}.parquet"
        if not f.exists():
            continue
        px = pd.read_parquet(f)["adj_close"].sort_index().dropna()
        if px.empty:
            continue
        for fd in fdates:
            p0s = px.loc[:fd]
            if p0s.empty:
                continue
            p0 = p0s.iloc[-1]
            target = fd + pd.DateOffset(months=1)
            p1s = px.loc[:target]
            if p1s.empty or (target - p1s.index[-1]).days > 20:
                continue
            p1 = p1s.iloc[-1]
            if p0 <= 0:
                continue
            rows.append({"ticker": tk, "formation_date": fd, "ret_1m": p1 / p0 - 1.0})
    return pd.DataFrame(rows)


def bench_1m_returns(fdates) -> pd.Series:
    bx = pd.read_parquet(OUTPUTS.parent / "data" / "benchmark" / "spcdnx.parquet")["adj_close"].sort_index()
    out = {}
    for fd in fdates:
        p0s = bx.loc[:fd]; target = fd + pd.DateOffset(months=1); p1s = bx.loc[:target]
        if p0s.empty or p1s.empty:
            continue
        out[fd] = p1s.iloc[-1] / p0s.iloc[-1] - 1.0
    return pd.Series(out)


def run(adv_floor: float, cost_tiers=COST_TIERS, universe: str = "holdout") -> dict:
    """universe='holdout' keeps the paper's out-of-sample discipline (breakpoints
    from train, basket from holdout only, roughly a 380-name pool). universe='full'
    is what a live strategy would actually do: breakpoints AND basket from every
    name that clears the ADV floor, no holdout restriction. Both are reported
    because they answer different questions: 'full' answers how this would
    perform as an actual fund; 'holdout' answers whether the earlier finding is
    still out-of-sample once a liquidity floor is applied."""
    mp = pd.read_parquet(ADJUSTED / "metrics_panel.parquet")
    split = load_split()
    member = {t: "train" for t in split["train"]}
    member.update({t: "holdout" for t in split["holdout"]})
    mp["split"] = mp["ticker"].map(member)
    mp = mp[mp["split"].isin(["train", "holdout"]) & (mp["illiq"] > 0)]

    fdates = formation_dates()
    all_tickers = mp["ticker"].unique().tolist()
    fwd = one_month_fwd_returns(all_tickers, fdates)
    mp = mp.merge(fwd, on=["ticker", "formation_date"], how="inner")
    bench = bench_1m_returns(fdates)

    prev_basket = set()
    monthly = []
    for fd, g in mp.groupby("formation_date"):
        if universe == "holdout":
            tr = g[g.split == "train"]
            if tr["illiq"].nunique() < N_Q + 1 or len(tr) < 5 * N_Q:
                continue
            bp = tr["illiq"].quantile(np.linspace(0, 1, N_Q + 1)[1:-1]).to_numpy()
            g = g.assign(q=np.digitize(g["illiq"].to_numpy(), bp) + 1)
            hh = g[(g.split == "holdout") & (g.q == N_Q) & (g.adv_20d >= adv_floor)]
        else:  # 'full' -- breakpoints and basket both from the whole cross-section
            if g["illiq"].nunique() < N_Q + 1 or len(g) < 5 * N_Q:
                continue
            bp = g["illiq"].quantile(np.linspace(0, 1, N_Q + 1)[1:-1]).to_numpy()
            g = g.assign(q=np.digitize(g["illiq"].to_numpy(), bp) + 1)
            hh = g[(g.q == N_Q) & (g.adv_20d >= adv_floor)]
        if hh.empty:
            continue
        basket = set(hh["ticker"])
        gross_ret = hh["ret_1m"].mean()          # equal-weighted

        entries = basket - prev_basket
        exits = prev_basket & (set(mp[mp.formation_date == fd]["ticker"]) - basket) \
            if prev_basket else set()
        # cost: entries pay their own tier's cost; exits pay the tier cost of the
        # position being closed (approximated with the current period's ADV for
        # names still in mp this period, else the tiered default 8%)
        adv_map = dict(zip(hh["ticker"], hh["adv_20d"]))
        turn_cost = 0.0
        n_trades = 0
        if entries:
            for tkr in entries:
                turn_cost += (1 / max(len(basket), 1)) * cost_for_adv(adv_map.get(tkr, 0))
                n_trades += 1
        if exits:
            exit_adv = mp[(mp.formation_date == fd) & (mp.ticker.isin(exits))] \
                .set_index("ticker")["adv_20d"].to_dict()
            for tkr in exits:
                turn_cost += (1 / max(len(prev_basket), 1)) * cost_for_adv(exit_adv.get(tkr, 0))
                n_trades += 1

        net_ret = gross_ret - turn_cost
        monthly.append({
            "formation_date": fd, "n_holdings": len(basket),
            "gross_ret": gross_ret, "turnover_cost": turn_cost, "net_ret": net_ret,
            "n_trades": n_trades, "bench_ret": bench.get(fd, np.nan),
            "turnover_frac": (len(entries) + len(exits)) / max(len(basket | prev_basket), 1),
        })
        prev_basket = basket

    m = pd.DataFrame(monthly).dropna(subset=["bench_ret"])
    if m.empty:
        return {"adv_floor": adv_floor, "n_months": 0}, m

    m["equity_net"] = (1 + m["net_ret"]).cumprod()
    m["equity_gross"] = (1 + m["gross_ret"]).cumprod()
    m["equity_bench"] = (1 + m["bench_ret"]).cumprod()

    def cagr(eq, n):
        yrs = n / 12
        return eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 and eq.iloc[-1] > 0 else np.nan

    def maxdd(eq):
        peak = eq.cummax()
        return float(((eq - peak) / peak).min())

    n = len(m)
    out = {
        "adv_floor": adv_floor,
        "n_months": n,
        "avg_holdings": float(m["n_holdings"].mean()),
        "avg_monthly_turnover_frac": float(m["turnover_frac"].mean()),
        "avg_monthly_cost_drag": float(m["turnover_cost"].mean()),
        "cagr_gross": cagr(m["equity_gross"], n),
        "cagr_net": cagr(m["equity_net"], n),
        "cagr_benchmark": cagr(m["equity_bench"], n),
        "maxdd_net": maxdd(m["equity_net"]),
        "maxdd_bench": maxdd(m["equity_bench"]),
        "vol_ann_net": float(m["net_ret"].std() * np.sqrt(12)),
        "sharpe_like_net": float(m["net_ret"].mean() / m["net_ret"].std() * np.sqrt(12))
                           if m["net_ret"].std() > 0 else np.nan,
        "final_equity_net": float(m["equity_net"].iloc[-1]),
        "final_equity_gross": float(m["equity_gross"].iloc[-1]),
        "final_equity_bench": float(m["equity_bench"].iloc[-1]),
    }
    return out, m


def _summary_only(adv_floor: float, universe: str = "holdout") -> dict:
    s, _ = run(adv_floor, universe=universe)
    s["universe"] = universe
    return s


def main() -> None:
    log.info("Running base case: ADV floor $100,000/day, FULL universe (live-strategy realism)")
    base_summary, base_monthly = run(100_000, universe="full")
    base_monthly.to_csv(SDIR / "monthly_returns_base.csv", index=False)

    log.info("Sensitivity: ADV floor sweep, both universe definitions")
    rows = []
    for universe in ("full", "holdout"):
        for floor in (0, 25_000, 100_000, 250_000, 500_000):
            rows.append(_summary_only(floor, universe=universe))
    sens = pd.DataFrame(rows)
    sens.to_csv(SDIR / "cost_sensitivity.csv", index=False)
    log.info("\n%s", sens[["universe", "adv_floor", "n_months", "avg_holdings",
                           "avg_monthly_turnover_frac", "cagr_net", "cagr_benchmark",
                           "maxdd_net", "sharpe_like_net"]].to_string(index=False))

    # equity curve figure for the base case
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(pd.to_datetime(base_monthly.formation_date), base_monthly.equity_net,
            label="Strategy, net of estimated costs", color="#2E5A87", lw=1.8)
    ax.plot(pd.to_datetime(base_monthly.formation_date), base_monthly.equity_gross,
            label="Strategy, gross (no costs)", color="#3B7A57", lw=1.2, ls="--")
    ax.plot(pd.to_datetime(base_monthly.formation_date), base_monthly.equity_bench,
            label="Just holding the benchmark", color="#888888", lw=1.4)
    ax.set_yscale("log")
    ax.set_title("Long-only illiquid-quintile portfolio vs. benchmark\n"
                 "(monthly rebalance, ADV ≥ $100k/day, all qualifying TSXV names, "
                 "tiered cost assumption)")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(SDIR / "equity_curve.png", dpi=140)
    plt.close(fig)

    pd.DataFrame([base_summary]).to_csv(SDIR / "backtest_summary.csv", index=False)
    log.info("\n=== base case ($100k ADV floor) ===\n%s",
             pd.Series(base_summary).to_string())
    log.info("wrote outputs to %s", SDIR)


if __name__ == "__main__":
    main()
