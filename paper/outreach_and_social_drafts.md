# Publication drafts — LinkedIn, X/Twitter, outreach email

Fill in `[link]` once the paper is posted (SSRN and/or your site). Everything else
is ready to post as-is or lightly edit into your own voice. All numbers pulled
from the verified results — nothing here is rounded differently from the paper.

---

## LinkedIn post

I spent the last several weeks testing a simple question on the TSX Venture Exchange: do stocks that are hard to trade subsequently outperform, or is that just a warning sign in disguise?

I tested 1,127 TSXV companies across 2016–2024, using five different ways of measuring "illiquid" — and locked away 30% of the tickers before looking at a single result, so I couldn't unconsciously tune the answer.

Four measures agreed: the least-liquid fifth of stocks beat the most-liquid fifth by roughly 25–65 percentage points over the following year, on data I never touched while building the method.

One measure — a bid-ask spread estimate — said the opposite.

That disagreement turned out to be the most interesting part. On this exchange, the spread estimator is actually picking up volatility, not trading cost — which means "illiquid" isn't one thing here, it's at least two different things pointing in different directions.

I also did something I don't often see in this kind of write-up: I checked whether any of this could actually be traded. It can't, not as measured. Once you require enough real volume to build a position, turnover costs and portfolio breadth collapse the "portfolio" to 1–3 stocks a month, and every surviving version has a drawdown north of 80%. The academic finding is real. The trading strategy built directly from it isn't — and I think showing that math matters as much as the headline result.

Full paper (plain-English edition, no finance background needed) and the complete reproducible code: [link]

---

## X / Twitter thread

**1/**
Do hard-to-trade stocks actually outperform?

I tested 1,127 TSX Venture Exchange companies over 9 years to find out.

**2/**
I measured "illiquid" five different ways — how often a stock trades, how much, how far its price moves per dollar traded, and its estimated bid-ask spread.

**3/**
Before looking at a single result, I locked away 30% of the companies and only unlocked them once, at the end, to check the pattern actually holds on data I never touched building the method.

**4/**
Four measures agreed: the least-liquid stocks beat the most-liquid ones by ~25–65 points over the following year. Monotonic across every bucket. Held up on the locked-away 30%.

**5/**
One measure — a bid-ask spread estimate — said the opposite.

That's where it got interesting.

**6/**
Turns out that measure is actually tracking volatility on this exchange, not trading cost. "Illiquid" isn't one thing here — it's at least two different things, pointing in different directions.

[attach: the 5-measure comparison chart]

**7/**
The catch: my sample is companies still listed today. Every one that failed or delisted along the way is invisible to the data — and failed companies are usually the most illiquid ones right before they die. That almost certainly inflates the headline number.

**8/**
So I checked: is any of this actually tradable?

No.

Require enough real volume to build a position, and the "portfolio" collapses to 1–3 stocks a month. Turnover costs are brutal. Every version that survives has an 80%+ drawdown.

**9/**
The research finding is real. The trading strategy isn't — and I think showing that math is worth as much as the headline result.

**10/**
Full paper + all code here: [link]

---

## Outreach email/DM template

Subject: TSXV illiquidity study — feedback welcome, especially on survivorship

Hi [Name],

I recently completed an independent empirical study of 1,127 TSX Venture Exchange companies (2016–2024), testing whether trailing illiquidity predicts forward returns. I used five different illiquidity measures with a locked-in, out-of-sample holdout — four measures point one direction, one points the other, which turned out to be the more interesting part of the result.

I'd value your view on the methodology, particularly the survivorship-bias treatment (the sample is necessarily limited to companies still listed today, and I've tried to bound rather than hand-wave the resulting bias) and whether the holdout discipline holds up to scrutiny. I also ran a separate check on whether the effect survives as an actual tradable strategy once realistic costs and turnover are applied — it doesn't, and I think that's worth knowing regardless of what you make of the underlying research finding.

Paper (plain-English edition) and full reproducible code: [link]

No pressure for a long response — even a one-line reaction to where you think this is weakest would be genuinely useful before I post it more publicly.

Thanks,
Yonatan Brunshtein
The Venture Analyst

---

## Notes on using these

- **LinkedIn/X must be posted by you, from your own account** — a post or DM that reads as AI-generated (or is later found to be) undermines exactly the credibility this is trying to build. Use these as a starting draft, then edit until they sound like you.
- **The outreach template is meant to be personalized per recipient** — swap in something specific to their work in the first line if you can (e.g., "I saw your paper on X" or "given your work on microcap liquidity"). A template sent unmodified to 50 people reads as a template.
- Post the LinkedIn piece and the X thread **after**, not before, at least one real person has read the paper (see the step-by-step guide) — a single caught error before the public post is worth more than fast timing.
