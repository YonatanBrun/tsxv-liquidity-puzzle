# TSXV Liquidity Discount — results

_Generated 2026-09-08 18:00 UTC_

Direction not assumed in advance: H1 (illiquidity premium, Q5−Q1 > 0) vs H2 (value trap, Q5−Q1 < 0). The holdout column is the test.

## A. Portfolio sort — Q5 (most illiquid) − Q1 (most liquid)

Pooled mean of the per-formation-date equal-weighted excess-return spread; `nw_t` is a Newey-West t-stat (lags = horizon in months).

| measure      |   horizon_m | split   |   n_dates |   mean_Q5_minus_Q1 |    nw_t |   nw_lags |
|:-------------|------------:|:--------|----------:|-------------------:|--------:|----------:|
| illiq        |           6 | train   |       102 |            +0.3445 | +6.8616 |         6 |
| illiq        |           6 | holdout |       102 |            +0.3172 | +9.1926 |         6 |
| illiq        |          12 | train   |        96 |            +0.6533 | +4.9373 |        12 |
| illiq        |          12 | holdout |        96 |            +0.6508 | +5.9427 |        12 |
| illiq        |          24 | train   |        84 |            +0.9571 | +5.4341 |        24 |
| illiq        |          24 | holdout |        84 |            +1.0550 | +5.8320 |        24 |
| zero_ret_pct |           6 | train   |       102 |            +0.2652 | +4.9554 |         6 |
| zero_ret_pct |           6 | holdout |       102 |            +0.2610 | +6.2499 |         6 |
| zero_ret_pct |          12 | train   |        96 |            +0.4321 | +4.4321 |        12 |
| zero_ret_pct |          12 | holdout |        96 |            +0.5335 | +4.3952 |        12 |
| zero_ret_pct |          24 | train   |        84 |            +0.5550 | +4.6302 |        24 |
| zero_ret_pct |          24 | holdout |        84 |            +0.7618 | +4.7640 |        24 |
| cs_spread    |           6 | train   |       102 |            -0.0640 | -2.5305 |         6 |
| cs_spread    |           6 | holdout |       102 |            -0.0306 | -0.5768 |         6 |
| cs_spread    |          12 | train   |        96 |            -0.1492 | -2.0889 |        12 |
| cs_spread    |          12 | holdout |        96 |            +0.0078 | +0.0736 |        12 |
| cs_spread    |          24 | train   |        84 |            -0.1745 | -1.6658 |        24 |
| cs_spread    |          24 | holdout |        84 |            +0.0515 | +0.3429 |        24 |

### Mean excess return by quintile

**Amihud ILLIQ**

| measure   |   horizon_m | split   |   n_dates |      q1 |      q2 |      q3 |      q4 |      q5 |
|:----------|------------:|:--------|----------:|--------:|--------:|--------:|--------:|--------:|
| illiq     |           6 | train   |       102 | -0.0905 | +0.0120 | +0.1075 | +0.1252 | +0.2540 |
| illiq     |           6 | holdout |       102 | -0.0591 | +0.0383 | +0.1144 | +0.1235 | +0.2580 |
| illiq     |          12 | train   |        96 | -0.1713 | -0.0014 | +0.1729 | +0.2366 | +0.4820 |
| illiq     |          12 | holdout |        96 | -0.1077 | +0.1316 | +0.1715 | +0.1880 | +0.5431 |
| illiq     |          24 | train   |        84 | -0.2537 | -0.0170 | +0.2855 | +0.4105 | +0.7034 |
| illiq     |          24 | holdout |        84 | -0.1758 | +0.2011 | +0.2608 | +0.4057 | +0.8793 |

**Zero-return days %**

| measure      |   horizon_m | split   |   n_dates |      q1 |      q2 |      q3 |      q4 |      q5 |
|:-------------|------------:|:--------|----------:|--------:|--------:|--------:|--------:|--------:|
| zero_ret_pct |           6 | train   |       102 | -0.0352 | +0.0212 | +0.0733 | +0.1175 | +0.2300 |
| zero_ret_pct |           6 | holdout |       102 | -0.0248 | +0.0570 | +0.0636 | +0.1451 | +0.2362 |
| zero_ret_pct |          12 | train   |        96 | -0.0563 | +0.0372 | +0.1676 | +0.1920 | +0.3758 |
| zero_ret_pct |          12 | holdout |        96 | -0.0395 | +0.1287 | +0.1126 | +0.2441 | +0.4940 |
| zero_ret_pct |          24 | train   |        84 | -0.0564 | +0.1607 | +0.2534 | +0.2719 | +0.4986 |
| zero_ret_pct |          24 | holdout |        84 | +0.0197 | +0.3135 | +0.1533 | +0.3645 | +0.7815 |

**Corwin-Schultz spread**

| measure   |   horizon_m | split   |   n_dates |      q1 |      q2 |      q3 |      q4 |      q5 |
|:----------|------------:|:--------|----------:|--------:|--------:|--------:|--------:|--------:|
| cs_spread |           6 | train   |       102 | +0.1203 | +0.1074 | +0.0628 | +0.0526 | +0.0564 |
| cs_spread |           6 | holdout |       102 | +0.1389 | +0.1128 | +0.0774 | +0.0434 | +0.1083 |
| cs_spread |          12 | train   |        96 | +0.2380 | +0.1749 | +0.1010 | +0.1032 | +0.0888 |
| cs_spread |          12 | holdout |        96 | +0.2454 | +0.1863 | +0.1637 | +0.1049 | +0.2532 |
| cs_spread |          24 | train   |        84 | +0.3480 | +0.2669 | +0.1646 | +0.1648 | +0.1735 |
| cs_spread |          24 | holdout |        84 | +0.3297 | +0.3578 | +0.3340 | +0.2541 | +0.3812 |

## B. Fama-MacBeth cross-sectional regression

`excess_w ~ illiq_rank + log_mktcap + C(sector)`, one cross-section per formation date, coefficients averaged with Newey-West t (lags = horizon). `b_illiq` is the coefficient on the within-date illiquidity percentile (0..1).

| measure      |   horizon_m | split   |   n_dates |   b_illiq |   t_illiq |   b_size |   t_size |
|:-------------|------------:|:--------|----------:|----------:|----------:|---------:|---------:|
| illiq        |           6 | train   |       102 |   +0.2339 |   +9.5057 |  -0.0475 |  -4.2539 |
| illiq        |           6 | holdout |       102 |   +0.1852 |   +5.7558 |  -0.0437 |  -3.7828 |
| illiq        |          12 | train   |        96 |   +0.4839 |   +5.0197 |  -0.0865 |  -2.1898 |
| illiq        |          12 | holdout |        96 |   +0.3940 |   +7.6683 |  -0.0852 |  -2.6972 |
| illiq        |          24 | train   |        84 |   +0.7111 |   +4.0898 |  -0.1502 |  -2.2324 |
| illiq        |          24 | holdout |        84 |   +0.6363 |   +6.9500 |  -0.1742 |  -2.4872 |
| zero_ret_pct |           6 | train   |       102 |   +0.1342 |   +3.2649 |  -0.0690 |  -6.9022 |
| zero_ret_pct |           6 | holdout |       102 |   +0.1463 |   +2.9398 |  -0.0558 |  -6.1781 |
| zero_ret_pct |          12 | train   |        96 |   +0.1914 |   +3.5720 |  -0.1404 |  -3.9856 |
| zero_ret_pct |          12 | holdout |        96 |   +0.3155 |   +2.6270 |  -0.1118 |  -5.1674 |
| zero_ret_pct |          24 | train   |        84 |   +0.0792 |   +1.2189 |  -0.2496 |  -4.0344 |
| zero_ret_pct |          24 | holdout |        84 |   +0.2020 |   +1.7181 |  -0.2490 |  -4.4362 |
| cs_spread    |           6 | train   |       102 |   -0.0408 |   -1.4736 |  -0.0795 |  -6.3083 |
| cs_spread    |           6 | holdout |       102 |   -0.0072 |   -0.1314 |  -0.0711 |  -6.7174 |
| cs_spread    |          12 | train   |        96 |   -0.0777 |   -1.2719 |  -0.1546 |  -4.0024 |
| cs_spread    |          12 | holdout |        96 |   +0.0955 |   +0.8045 |  -0.1441 |  -4.4478 |
| cs_spread    |          24 | train   |        84 |   -0.0860 |   -1.2847 |  -0.2507 |  -3.9563 |
| cs_spread    |          24 | holdout |        84 |   +0.2086 |   +1.3905 |  -0.2689 |  -4.0053 |

## C. Robustness — is the spread real or a small-price / skew artifact?

Each variant neutralises one suspected artifact channel. HOLDOUT Q5−Q1 shown; `median within quintile` and `price ≥ $0.10` are the decisive ones (an equal-weighted mean of a right-skewed penny-stock distribution mostly measures the fattest right tail).

**Amihud ILLIQ** — HOLDOUT Q5−Q1 (Newey-West t)

| variant                      | 6                | 12              | 24              |
|:-----------------------------|:-----------------|:----------------|:----------------|
| 3-day avg prices             | +0.305 (t=+9.4)  | +0.635 (t=+6.1) | +1.039 (t=+5.9) |
| median + price>=$0.10        | +0.150 (t=+6.5)  | +0.263 (t=+6.4) | +0.410 (t=+7.9) |
| median within quintile       | +0.238 (t=+7.5)  | +0.434 (t=+6.6) | +0.673 (t=+6.3) |
| price >= $0.10               | +0.184 (t=+6.9)  | +0.321 (t=+7.5) | +0.626 (t=+6.7) |
| primary (mean, EW, pt-to-pt) | +0.317 (t=+9.2)  | +0.651 (t=+5.9) | +1.055 (t=+5.8) |
| tight winsor [-0.9,2.0]      | +0.271 (t=+11.0) | +0.454 (t=+9.6) | +0.664 (t=+8.4) |
| value-weighted               | +0.275 (t=+4.8)  | +0.537 (t=+4.5) | +0.889 (t=+5.3) |

**Zero-return days %** — HOLDOUT Q5−Q1 (Newey-West t)

| variant                      | 6               | 12              | 24              |
|:-----------------------------|:----------------|:----------------|:----------------|
| 3-day avg prices             | +0.255 (t=+6.2) | +0.515 (t=+4.5) | +0.742 (t=+4.8) |
| median + price>=$0.10        | +0.117 (t=+5.6) | +0.237 (t=+4.2) | +0.237 (t=+7.7) |
| median within quintile       | +0.179 (t=+6.3) | +0.338 (t=+4.8) | +0.407 (t=+6.6) |
| price >= $0.10               | +0.166 (t=+5.8) | +0.313 (t=+4.8) | +0.320 (t=+5.2) |
| primary (mean, EW, pt-to-pt) | +0.261 (t=+6.2) | +0.533 (t=+4.4) | +0.762 (t=+4.8) |
| tight winsor [-0.9,2.0]      | +0.211 (t=+7.8) | +0.345 (t=+6.9) | +0.423 (t=+7.5) |
| value-weighted               | +0.158 (t=+3.1) | +0.357 (t=+2.6) | +0.506 (t=+1.9) |

**Corwin-Schultz spread** — HOLDOUT Q5−Q1 (Newey-West t)

| variant                      | 6               | 12              | 24              |
|:-----------------------------|:----------------|:----------------|:----------------|
| 3-day avg prices             | -0.026 (t=-0.5) | +0.010 (t=+0.1) | +0.055 (t=+0.4) |
| median + price>=$0.10        | -0.124 (t=-4.6) | -0.149 (t=-2.8) | -0.233 (t=-3.1) |
| median within quintile       | -0.103 (t=-3.4) | -0.118 (t=-1.8) | -0.168 (t=-1.6) |
| price >= $0.10               | -0.037 (t=-0.9) | -0.028 (t=-0.3) | -0.047 (t=-0.3) |
| primary (mean, EW, pt-to-pt) | -0.031 (t=-0.6) | +0.008 (t=+0.1) | +0.051 (t=+0.3) |
| tight winsor [-0.9,2.0]      | -0.055 (t=-1.6) | -0.069 (t=-1.3) | -0.095 (t=-1.2) |
| value-weighted               | -0.148 (t=-2.4) | -0.122 (t=-1.0) | -0.219 (t=-1.5) |

## Holdout replication (primary spec)

- Amihud ILLIQ 6m: train +0.344 / holdout +0.317 (t=+9.19) — **replicates** (same sign, holdout |t|≥1.96)
- Amihud ILLIQ 12m: train +0.653 / holdout +0.651 (t=+5.94) — **replicates** (same sign, holdout |t|≥1.96)
- Amihud ILLIQ 24m: train +0.957 / holdout +1.055 (t=+5.83) — **replicates** (same sign, holdout |t|≥1.96)
- Zero-return days % 6m: train +0.265 / holdout +0.261 (t=+6.25) — **replicates** (same sign, holdout |t|≥1.96)
- Zero-return days % 12m: train +0.432 / holdout +0.533 (t=+4.40) — **replicates** (same sign, holdout |t|≥1.96)
- Zero-return days % 24m: train +0.555 / holdout +0.762 (t=+4.76) — **replicates** (same sign, holdout |t|≥1.96)
- Corwin-Schultz spread 6m: train -0.064 / holdout -0.031 (t=-0.58) — sign agrees, holdout not significant
- Corwin-Schultz spread 12m: train -0.149 / holdout +0.008 (t=+0.07) — **does not replicate** (sign flips)
- Corwin-Schultz spread 24m: train -0.174 / holdout +0.051 (t=+0.34) — **does not replicate** (sign flips)
