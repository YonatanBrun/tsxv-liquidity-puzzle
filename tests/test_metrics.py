"""Known-input checks for each estimator. Run: python -m pytest tests/ -q
(or: python tests/test_metrics.py)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from metrics import build_adjusted, corwin_schultz, metrics_for_window  # noqa: E402


def _raw(dates, o, h, l, c, v, adj=None, splits=None):
    return pd.DataFrame(
        {"open": o, "high": h, "low": l, "close": c,
         "adj_close": adj if adj is not None else c,
         "volume": v,
         "dividends": np.zeros(len(c)),
         "splits": splits if splits is not None else np.zeros(len(c))},
        index=pd.DatetimeIndex(dates, name="date"))


def test_amihud_hand_value():
    # 3 days, returns from adj close: day2 +0.10, day3 -0.0909...
    dates = pd.bdate_range("2020-01-01", periods=3)
    raw = _raw(dates, [10, 11, 10], [10, 11, 10], [10, 11, 10],
              c=[10.0, 11.0, 10.0], v=[1000, 1000, 1000])
    adj = build_adjusted(raw)
    m = metrics_for_window(adj)
    # day1 ret is NaN (pct_change), excluded. day2: |0.1|/(11*1000). day3: |−1/11|/(10*1000)
    expected = np.mean([abs(0.1) / (11 * 1000),
                        abs(-1 / 11) / (10 * 1000)]) * 1e6
    assert abs(m["illiq"] - expected) < 1e-9, (m["illiq"], expected)


def test_zero_return_days():
    dates = pd.bdate_range("2020-01-01", periods=5)
    raw = _raw(dates, [1] * 5, [1] * 5, [1] * 5,
              c=[10.0, 10.0, 10.5, 10.5, 10.5], v=[100] * 5)
    m = metrics_for_window(build_adjusted(raw))
    # diffs: [nan, 0, +0.5, 0, 0] -> 3 unchanged out of 4 comparable days = 75%
    assert abs(m["zero_ret_pct"] - 75.0) < 1e-9, m["zero_ret_pct"]


def test_corwin_schultz_zero_when_no_intraday_range():
    # high == low every day => ln(H/L)=0 => alpha=0 => spread=0 exactly
    n = 30
    px = pd.Series(np.full(n, 10.0))
    s = corwin_schultz(px, px.copy(), clamp_neg=True)
    assert abs(s) < 1e-12, s


def test_corwin_schultz_recovers_known_spread_order():
    # a persistent wide H/L range implies a large effective spread in the CS model;
    # a narrow range implies a small one. Check ordering + rough magnitude.
    n = 40
    wide = corwin_schultz(pd.Series(np.full(n, 10.0)), pd.Series(np.full(n, 9.0)), True)
    narrow = corwin_schultz(pd.Series(np.full(n, 10.0)), pd.Series(np.full(n, 9.9)), True)
    assert narrow < wide, (narrow, wide)
    assert 0.0 < narrow < 0.03, narrow


def test_corwin_schultz_positive_with_wider_range():
    rng = np.random.default_rng(0)
    mid = 10 + np.cumsum(rng.normal(0, 0.1, 40))
    high = pd.Series(mid * 1.03)
    low = pd.Series(mid * 0.97)
    s = corwin_schultz(high, low, clamp_neg=True)
    assert 0.0 <= s < 0.2, s


def test_split_adjustment_removes_fake_return():
    # 5:1 consolidation between day2 and day3: raw close 2 -> 10, adj close continuous
    dates = pd.bdate_range("2020-01-01", periods=4)
    raw = _raw(dates,
              o=[2, 2, 10, 10], h=[2, 2, 10, 10], l=[2, 2, 10, 10],
              c=[2.0, 2.0, 10.0, 10.0],
              adj=[2.0, 2.0, 2.0, 2.0],           # economically flat
              v=[100, 100, 100, 100],
              splits=[0, 0, 0.2, 0])
    adj = build_adjusted(raw)
    assert adj["ret"].abs().max() < 1e-9, adj["ret"].tolist()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"\n{len(fns)} passed")
