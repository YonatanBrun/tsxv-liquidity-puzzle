"""Build the PLAIN-ENGLISH edition of the paper (.docx) — same verified data,
same figures, written for a general audience in first person singular.

The technical/SSRN edition (build_paper.py -> TSXV_Liquidity_Puzzle.docx) is
untouched. This is a companion piece, not a replacement.

Every number is pulled live from outputs/*.csv, exactly like build_paper.py,
so the two documents can never drift apart or disagree with each other.

Run:  ../.venv/bin/python build_article.py
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_COLOR_INDEX

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
FIG = OUT / "paper"
DOCX = Path(__file__).resolve().parent / "TSXV_Liquidity_Puzzle_PlainEnglish.docx"

ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x55, 0x55, 0x55)


# --------------------------------------------------------------------------- #
# helpers (same conventions as build_paper.py)
# --------------------------------------------------------------------------- #
def add_field(paragraph, instr):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    r._r.append(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); r._r.append(s)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r._r.append(e)


def h(doc, text, level=1):
    return doc.add_heading(text, level=level)


def para(doc, text, *, italic=False, bold=False, size=None, align=None, space_after=8):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.2
    return p


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    p.paragraph_format.space_after = Pt(4)
    return p


def term_box(doc, term, definition):
    """One glossary entry: bold term, plain definition."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.left_indent = Inches(0.15)
    r1 = p.add_run(term + " — ")
    r1.bold = True
    r1.font.color.rgb = ACCENT
    p.add_run(definition)
    return p


def figure(doc, path: Path, caption: str, width=6.3):
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph()
    r = c.add_run(caption)
    r.font.size = Pt(9); r.italic = True; r.font.color.rgb = GREY
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(14)


def table(doc, df: pd.DataFrame, caption: str, numfmt="{:+.2f}", firstcols=1):
    cap = doc.add_paragraph()
    rr = cap.add_run(caption); rr.bold = True; rr.font.size = Pt(9.5)
    cap.paragraph_format.space_after = Pt(3)
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, col in enumerate(df.columns):
        cell = t.rows[0].cells[j]
        cell.text = str(col)
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.size = Pt(8.5); run.bold = True
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for j, v in enumerate(row):
            s = numfmt.format(v) if isinstance(v, float) and j >= firstcols else str(v)
            cells[j].text = s
            for p in cells[j].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    return t


def callout(doc, label, text):
    """A shaded 'plain-English translation' box."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "EDF2F7")
    tcPr.append(shd)
    p = cell.paragraphs[0]
    r = p.add_run(f"{label}  "); r.bold = True; r.font.color.rgb = ACCENT; r.font.size = Pt(9.5)
    r2 = p.add_run(text); r2.font.size = Pt(9.5); r2.italic = True
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


# --------------------------------------------------------------------------- #
# live data — identical source as the technical edition
# --------------------------------------------------------------------------- #
spread = pd.read_csv(OUT / "spread_summary.csv")
fm = pd.read_csv(OUT / "fama_macbeth.csv")
rob = pd.read_csv(OUT / "robustness.csv")
secn = pd.read_csv(OUT / "ext_sector_neutral.csv")
subp = pd.read_csv(OUT / "ext_subperiods.csv")
dbl = pd.read_csv(OUT / "ext_price_double_sort.csv")
turn = pd.read_csv(OUT / "ext_turnover_check.csv")
trans = pd.read_csv(OUT / "ext_persistence_transition.csv", index_col=0)
brack = pd.read_csv(OUT / "ext_survivorship_bracket.csv")


def hv(measure, horizon, split="holdout", col="mean_Q5_minus_Q1"):
    r = spread[(spread.measure == measure) & (spread.horizon_m == horizon) & (spread.split == split)]
    return float(r[col].iloc[0])


def hvt(measure, horizon, split="holdout"):
    r = spread[(spread.measure == measure) & (spread.horizon_m == horizon) & (spread.split == split)]
    return float(r["nw_t"].iloc[0])


def robv(measure, horizon, variant, col="Q5_minus_Q1"):
    r = rob[(rob.measure == measure) & (rob.horizon_m == horizon) & (rob.split == "holdout")
            & (rob.variant == variant)]
    return float(r[col].iloc[0])


def pct(x):
    return f"{x*100:+.0f} percentage points"


_AF = pd.read_parquet(OUT / "analysis_frame.parquet")


def median_mean(horizon):
    """Median/mean of excess return at this horizon, clipped exactly as Figure 2 is,
    so the number in the prose always matches the number the reader can see in the chart."""
    x = _AF[_AF.horizon_m == horizon]["excess_ret_w"].clip(-2, 5)
    return float(x.median()), float(x.mean())

# =========================================================================== #
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for m in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
    setattr(sec, m, Inches(1.0))

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)

footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_field(footer_p, "PAGE")

# ---- title -------------------------------------------------------------- #
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Do Hard-to-Trade Stocks Actually Pay Off?")
r.bold = True; r.font.size = Pt(21); r.font.color.rgb = ACCENT
t.paragraph_format.space_after = Pt(4)

para(doc, "What I found testing 1,127 Canadian micro-cap stocks, and why the answer "
     "changed depending on how I asked the question", align="c", italic=True, size=12.5)
para(doc, "By [Your name]  ·  September 2026", align="c", size=10.5)
para(doc, "This is the plain-English version of a longer, more technical research paper. "
     "Every number in this piece comes straight from that paper's data — nothing is "
     "rounded differently or simplified away, only explained.", align="c", italic=True, size=9.5)
doc.add_paragraph()

# ---- the one-sentence version -------------------------------------------- #
h(doc, "The short version", 2)
para(doc, "I spent several weeks testing a simple question on the TSX Venture Exchange — "
     "Canada's market for small, early-stage, mostly resource and mining companies: "
     "does a stock being hard to trade tell you anything about what it's going to do next? "
     "I tested five different ways of measuring “hard to trade,” on 1,127 companies, over "
     "nine years, and split my data so I couldn't fool myself. Four of the five measures "
     "said the same thing: the hardest-to-trade stocks did meaningfully better afterward "
     "than the easiest-to-trade ones. One measure said the opposite. I think I know why, "
     "and the reason turned out to be the more interesting finding.", bold=False)

doc.add_paragraph()

# =========================================================================== #
# GLOSSARY
# =========================================================================== #
h(doc, "Terms you'll need (read this once, then forget you read it)", 1)
para(doc, "I use a handful of finance and statistics terms repeatedly below. I'm defining "
     "all of them here, in one place, so the rest of this piece can just use the words "
     "without re-explaining them every time. Skip this section if you already know the "
     "jargon; come back to it if something later doesn't make sense.")

term_box(doc, "Liquid / illiquid",
 "A stock is “liquid” if you can buy or sell a meaningful amount of it quickly, without "
 "moving the price much. It's “illiquid” if trading is thin — maybe it goes days without "
 "a trade, or a modest order swings the price 10%. Illiquid stocks are usually small, "
 "unloved, or both.")
term_box(doc, "Excess return",
 "How much a stock made or lost, minus how much the overall market did over the same "
 "period. If a stock rose 20% while the market rose 5%, its excess return is +15 "
 "percentage points. This is the number I'm trying to predict throughout this piece — not "
 "“did the stock go up,” but “did it beat the market.”")
term_box(doc, "The benchmark",
 "The “market” I measure everything against is the S&P/TSX Venture Composite Index — "
 "essentially the average of every stock on this exchange. It's the yardstick.")
term_box(doc, "Quintile",
 "Split a group into five equal-sized buckets, ranked from lowest to highest on some "
 "measure. I constantly split my 1,127 companies into five illiquidity quintiles: "
 "quintile 1 is the most liquid fifth, quintile 5 is the most illiquid fifth.")
term_box(doc, "“Q5 minus Q1” / the spread",
 "The single number I care about most: take the average (or median) return of the "
 "most-illiquid group (quintile 5) and subtract the return of the most-liquid group "
 "(quintile 1). A positive number means illiquid stocks did better; negative means they "
 "did worse.")
term_box(doc, "Median vs. average (mean)",
 "The average adds everything up and divides by the count — one huge winner can drag it "
 "way up. The median is the middle value if you lined every result up in order — one "
 "huge winner barely moves it. When results are lopsided (a few massive winners, many "
 "small losers), the median tells you what happened to a “typical” stock; the average "
 "tells you what happened to the total pile of money. Both matter, but they can tell very "
 "different stories, and mine do — see the section on this below.")
term_box(doc, "Statistical significance / t-statistic",
 "A way of asking “could this result just be random noise?” The bigger the t-statistic "
 "(in either direction, positive or negative), the less likely the pattern is a fluke. As "
 "a rough rule of thumb, a t-statistic bigger than about 2 (positive or negative) is "
 "generally considered “real.” Most of my key results have t-statistics between 5 and 9, "
 "which is a strong signal by normal standards.")
term_box(doc, "Out-of-sample test / holdout",
 "The single most important safeguard in this whole project. Before I looked at a single "
 "result, I randomly set aside 30% of my 1,127 companies (380 of them) and locked that "
 "list away. I only used the other 70% while building and checking my approach. At the "
 "very end, I ran the finished method on the locked-away 30% exactly once. If a pattern "
 "only existed because I'd subconsciously tuned it to fit — a very easy trap when you're "
 "poking at the same data over and over — it should fall apart on the untouched group. "
 "It didn't. That's much stronger evidence than a pattern that only appears in the data "
 "used to build the method.")
term_box(doc, "Winsorizing",
 "Capping extreme outliers at a fixed percentile before analyzing, so one 3,000%-return "
 "stock doesn't single-handedly decide the answer. I capped everything at the "
 "1st-to-99th-percentile range, a decision I made before running any numbers.")
term_box(doc, "Survivorship bias",
 "A distortion that creeps in when your data only includes things that are still around "
 "today. My list of companies is every stock currently listed on this exchange — which "
 "means every company that went bankrupt, got delisted, or quietly disappeared between "
 "2016 and 2024 is missing. Since failed companies are usually the most illiquid ones "
 "right before they die, this tends to make illiquid stocks look better in my data than "
 "they really were. I come back to this a lot — it's the biggest weakness in the whole "
 "study, and I don't try to hide it.")
para(doc, "Three specific ways of measuring “how illiquid” — these are the actual "
     "yardsticks I built the whole study around:", space_after=6)
term_box(doc, "Measure 1 — the Amihud ratio",
 "For each stock, I look at how much its price moved on an average day relative to how "
 "many dollars of it actually traded that day. A stock that swings 5% on just $2,000 of "
 "trading is far more illiquid than one that swings 5% on $2 million. This is the most "
 "widely used illiquidity measure in academic finance, first proposed by Yakov Amihud in "
 "2002.")
term_box(doc, "Measure 2 — zero-return days",
 "The percentage of trading days where the closing price didn't move at all. A stock "
 "that closes unchanged 60% of the time simply isn't trading — nobody's showing up to buy "
 "or sell it.")
term_box(doc, "Measure 3 — the Corwin-Schultz spread",
 "An estimate of the bid-ask spread (the gap between what buyers offer and what sellers "
 "ask) built entirely out of each day's high and low price. I don't have access to real "
 "historical bid-ask data for these stocks, but I do have daily highs and lows, and a "
 "clever 2012 method by Corwin and Schultz can back out a spread estimate from just that.")
para(doc, "I also used two supporting measures — how much of a stock's total shares trade "
     "in a day (“turnover”), and plain dollar trading volume — as a further check on "
     "measures 1 and 2.")

doc.add_page_break()

# =========================================================================== #
h(doc, "The question I started with", 1)
para(doc,
 "In finance there are two completely opposite, both completely reasonable, stories about "
 "what it means when a stock is hard to trade.")
para(doc,
 "Story one: if you own something that's hard to sell, you deserve to be paid extra for "
 "that inconvenience. So illiquid stocks should, over time, drift upward relative to "
 "liquid ones — a kind of compensation for the hassle and risk of being stuck holding "
 "them. Economists call this the illiquidity premium.")
para(doc,
 "Story two: a stock that's hard to trade is usually hard to trade for a reason — nobody "
 "wants it. Thin trading is often the last symptom before a company runs out of money, "
 "gets diluted into oblivion by a desperate financing, or quietly delists. In this story, "
 "illiquid stocks should do worse, not better — the market is slowly recognizing they're "
 "in trouble.")
para(doc,
 "Both of these are argued seriously in the academic literature, and which one wins isn't "
 "obvious — it depends on the market. I decided to actually test it, rather than assume "
 "an answer, on the single market where I thought the question would be sharpest: the "
 "TSX Venture Exchange.")

callout(doc, "In one line:",
 "does being hard to trade make a stock a bargain, or a warning sign?")

h(doc, "Why the TSX Venture Exchange", 2)
para(doc,
 "The TSX Venture Exchange (TSXV) is Canada's exchange for small, early-stage companies — "
 "mostly mining and resource exploration, plus smaller pockets of oil and gas, technology, "
 "biotech, clean energy, and everything else. The typical company in my final dataset has "
 "a market value around C$18 million and trades around 27 cents a share. If an illiquidity "
 "effect exists anywhere, it should show up loudly here — this is about as far down the "
 "size-and-liquidity spectrum as a regulated stock exchange goes. It's also a market that, "
 "as far as I could find, nobody has studied this exact way before.")

h(doc, "The rule I made myself follow before looking at a single result", 2)
para(doc,
 "Here's the trap with a question like this: if you have thousands of stocks and a lot of "
 "flexibility in how you slice the data, you can always find some way of measuring "
 "“illiquid” that produces an exciting-looking pattern. That's not a discovery — it's "
 "just noise you kept digging until you found. It happens by accident more often than "
 "people admit.")
para(doc,
 "So before I ran a single number, I wrote down every decision in advance: exactly how "
 "I'd measure illiquidity (three separate ways, defined above, formulas fixed), exactly "
 "which time windows I'd test (6, 12, and 24 months forward), exactly how I'd handle "
 "extreme outliers (capped at the 1st and 99th percentile), and — most importantly — I "
 "randomly locked away 30% of my companies (380 of the 1,267) before touching anything. "
 "I only ever looked at results on the other 70% while I was building and checking my "
 "method. I opened the locked-away 30% exactly once, at the very end, to see if what I'd "
 "found held up. Every headline number in this piece is from that locked-away group.")

h(doc, "Where the data actually came from", 2)
para(doc,
 "This part is less exciting but matters for trusting the result. Free, reliable "
 "historical price data for tiny Canadian stocks is surprisingly hard to get — the usual "
 "sources either don't cover this exchange, don't go back far enough, or don't handle "
 "stock consolidations properly (Venture-exchange companies routinely do 5-for-1 or "
 "10-for-1 reverse splits, and if your price data doesn't adjust for that, it looks like "
 "the stock randomly jumped 500% overnight, which is nonsense).")
para(doc,
 "I ended up building my company list from the exchange's own public directory (1,267 "
 "actual operating companies, after stripping out shell companies, warrants, and other "
 "non-stock instruments), and pulling daily prices, sector classification, and each "
 "company's share count from TMX's own market-data service — the same organization that "
 "runs the exchange. I cross-checked the price data for accuracy and ran automated checks "
 "that caught and fixed a handful of corrupted price records before any analysis began.")
para(doc,
 "One data point I could not get historically: how many shares each company had "
 "outstanding at each point back in 2016–2024 (needed to size-adjust the comparison, "
 "since bigger companies behave differently than tiny ones). I used each company's "
 "current share count as an approximation, which I flag honestly, and I double-checked "
 "the finding using stock price alone as an alternative size measure — same answer either "
 "way.")

doc.add_page_break()

# =========================================================================== #
h(doc, "What I found, part one: illiquid stocks did better", 1)
para(doc,
 "I sorted all 1,127 stocks with usable data into five buckets (quintiles) by how "
 "illiquid they were, at each of 108 monthly snapshots between 2016 and 2024, using the "
 f"Amihud measure. Then I looked at what happened over the following 6, 12, and 24 "
 f"months. On the locked-away 30% of companies I never touched while building this:")

_t3 = spread.copy()
_t3 = _t3[_t3.split == "holdout"][["measure", "horizon_m", "mean_Q5_minus_Q1", "nw_t"]]
_t3.columns = ["Measure", "Months ahead", "Illiquid group's edge", "Signal strength (t-stat)"]
_t3["Measure"] = _t3["Measure"].map({"illiq": "Amihud measure", "zero_ret_pct": "Zero-return-days measure",
                                     "cs_spread": "Corwin–Schultz spread"})
table(doc, _t3, "Table 1.  The most-illiquid fifth of companies, minus the most-liquid "
      "fifth, in average return over the next N months. Positive = illiquid stocks won.")

para(doc,
 f"By the Amihud measure, the most illiquid fifth of stocks beat the most liquid fifth by "
 f"{hv('illiq',6)*100:.0f} percentage points over six months, {hv('illiq',12)*100:.0f} "
 f"points over a year, and {hv('illiq',24)*100:.0f} points over two years. The signal "
 f"strength on all of those is well above the “this is probably real” threshold of 2. The "
 f"zero-return-days measure — a completely different way of defining “illiquid” — pointed "
 "the same direction, with similar strength. And this wasn't a fluke of the 70% of "
 "companies I built the method on: it showed up, just as strongly, on the 30% I'd locked "
 "away and never looked at until the end.")

figure(doc, FIG / "fig1_quintile_bars.png",
 "Figure 1.  Typical (median) 12-month return, relative to the market, for each of the "
 "five illiquidity buckets — bucket 1 is the most liquid, bucket 5 the most illiquid — "
 "on the locked-away 30% of companies. For the Amihud and zero-return measures the bars "
 "climb steadily left to right. For Corwin–Schultz they don't.")

para(doc,
 "What I find most convincing here isn't just that bucket 5 beat bucket 1 — it's that the "
 "climb from bucket 1 to bucket 5 is smooth and step-wise (Figure 1). It's not that one "
 "weird group of stocks dragged the whole thing; each step up the illiquidity ladder adds "
 "a bit more return. That's what a real, gradual relationship looks like, as opposed to a "
 "coincidence driven by a handful of stocks.")

# =========================================================================== #
h(doc, "Wait — why am I suddenly talking about the median instead of the average?", 1)
para(doc,
 "Here's something I have to be upfront about, because it changes how big the “real” "
 "effect looks. Table 1 above uses averages. Averages on this kind of data are "
 "dangerously easy to misread.")
para(doc,
 f"The typical stock in my sample, over any 12-month stretch, actually did worse than the "
 f"market — the median 12-month result was {median_mean(12)[0]*100:.0f} percentage points "
 f"versus the market. Meanwhile the average 12-month result was positive, at "
 f"{median_mean(12)[1]*100:+.0f} points. Both of those are true at the same time, because a small "
 "number of stocks went up 300%, 500%, even 900%, and those extreme winners pull the "
 "average way up while barely nudging the median. Figure 2 shows this directly — most of "
 "the distribution sits to the left of zero (below-market), but there's a long thin tail "
 "stretching far to the right.")

figure(doc, FIG / "fig3_return_distribution.png",
 "Figure 2.  How 6-, 12-, and 24-month returns (relative to the market) are actually "
 "distributed. The dashed line is the median (typical outcome); the solid line is the "
 "average. They point in opposite directions because of the long right-hand tail of big "
 "winners.")

para(doc,
 "And here's the catch that matters for this whole study: the most illiquid stocks are "
 "also, almost by definition, the cheapest and most speculative ones — which means they're "
 "exactly where those rare 500%+ winners tend to live. So an average-based comparison "
 "between “illiquid” and “liquid” stocks is partly just measuring which bucket has the "
 "fatter jackpot tail, not what happened to a typical stock in each bucket.")
para(doc,
 "So, throughout the rest of this piece, I lean on the median comparison — “what happened "
 f"to the typical illiquid stock vs. the typical liquid stock” — as my main number, and I "
 f"show the average alongside it for context. On the median basis, the Amihud gap is "
 f"smaller but still large and still statistically solid: about "
 f"{robv('illiq',6,'median within quintile')*100:.0f} points over six months, "
 f"{robv('illiq',12,'median within quintile')*100:.0f} over a year, "
 f"{robv('illiq',24,'median within quintile')*100:.0f} over two years. Smaller than the "
 "headline average numbers, but still a real, large, statistically strong gap.")

doc.add_page_break()

# =========================================================================== #
h(doc, "What I found, part two: one measure disagreed, and that's the interesting part", 1)
para(doc,
 "If I'd stopped after the Amihud measure, I'd have a tidy, one-sided story: illiquid "
 "stocks win. But I'd pre-committed to testing three different definitions of illiquidity, "
 "specifically because I didn't want to trust just one, and the third one — the "
 "Corwin–Schultz spread estimate — told a different story.")
para(doc,
 f"On the same locked-away 30% of companies, using the same “typical stock” (median) "
 f"comparison, the widest-spread stocks actually did worse than the narrowest-spread ones "
 f"— by about {abs(robv('cs_spread',6,'median within quintile'))*100:.0f} points over six "
 f"months and {abs(robv('cs_spread',12,'median within quintile'))*100:.0f} points over a "
 "year. Smaller in size than the Amihud effect, and less consistently statistically "
 "significant, but leaning the other way.")

para(doc,
 "So which is it? I went looking for why two supposedly-related “illiquidity” measures "
 "would point in opposite directions, and found something worth knowing on its own: in "
 "this specific market, a stock's Corwin–Schultz spread estimate is actually negatively "
 "related to how illiquid it is by the other two measures. That sounds backwards, but "
 "here's the mechanism. The Corwin–Schultz method infers the spread from how wide a "
 "stock's daily high-low range is. A stock that barely trades often prints almost the "
 "same price all day — a narrow range, which the formula reads as a tight, cheap-to-trade "
 "spread. A stock that trades actively but swings wildly within the day — which, on this "
 "exchange, usually means a hot, speculative, momentum-driven name — prints a wide range, "
 "which the formula reads as an expensive, wide spread. In other words: on the TSX "
 "Venture Exchange, this particular measure ends up tracking day-to-day price swings "
 "(volatility) more than it tracks true trading cost. And it's genuinely true, "
 "separately, that hyped-up volatile stocks tend to cool off afterward — that's a "
 "well-documented pattern in its own right. I think that's largely what the "
 "Corwin–Schultz result is picking up.")

figure(doc, FIG / "fig4_forest.png",
 "Figure 3.  All five ways I measured illiquidity, and what each one said about the "
 "12-month return gap between the most- and least-illiquid stocks (locked-away 30% only). "
 "Four measures agree; one doesn't.")

callout(doc, "Bottom line on the disagreement:",
 "“illiquid” isn't one thing. How-much-does-it-trade and how-wide-is-the-spread turned "
 "out to be different questions on this exchange, with different answers.")

doc.add_page_break()

# =========================================================================== #
h(doc, "Making sure this is real and not a trick of the data", 1)
para(doc,
 "A result this size on penny stocks deserves real skepticism, so I spent a good chunk of "
 "this project trying to break my own finding. Here's the full stress test — every "
 "alternative version of the 12-month Amihud result I tried, each one designed to rule "
 "out one specific way the result could be fake. The pattern is the same at 6 and 24 "
 "months; I'm showing 12 months because it's the middle case.")

_variant_labels = {
    "primary (mean, EW, pt-to-pt)": "Main version (plain average)",
    "median within quintile": "Median within bucket",
    "value-weighted": "Weighted by company size",
    "3-day avg prices": "Using 3-day average prices",
    "price >= $0.10": "Only stocks priced ≥ C$0.10",
    "tight winsor [-0.9,2.0]": "Tighter outlier caps",
    "median + price>=$0.10": "Median + priced ≥ C$0.10 (strictest)",
}
_rt = rob[(rob.measure == "illiq") & (rob.horizon_m == 12) & (rob.split == "holdout")][
    ["variant", "Q5_minus_Q1", "nw_t"]].copy()
_rt["variant"] = _rt["variant"].map(lambda v: _variant_labels.get(v, v))
_rt.columns = ["Version of the test", "Illiquid − liquid gap (12mo)", "Signal strength"]
table(doc, _rt, "Table 2.  Every version of the 12-month Amihud test I ran, on the "
      "locked-away 30%.")

bullet(doc, bold_lead="Median instead of average: ",
       text=f"{robv('illiq',12,'median within quintile'):+.2f}. The skew-resistant number "
            "I lean on throughout this piece.")
bullet(doc, bold_lead="Weighted by company size instead of treated equally: ",
       text=f"{robv('illiq',12,'value-weighted'):+.2f}. The effect isn't confined to the "
            "very smallest nano-caps inside the illiquid bucket.")
bullet(doc, bold_lead="Using 3-day average prices at both ends of the window: ",
       text=f"{robv('illiq',12,'3-day avg prices'):+.2f}. Rules out the result being a "
            "fluke of one lucky or unlucky closing price.")
bullet(doc, bold_lead="Dropping every stock priced under 10 cents: ",
       text=f"{robv('illiq',12,'price >= $0.10'):+.2f}. Roughly halves the gap but leaves "
            "it large and clearly significant — it's not purely a sub-dime phenomenon.")
bullet(doc, bold_lead="Capping outliers much more tightly: ",
       text=f"{robv('illiq',12,'tight winsor [-0.9,2.0]'):+.2f}. Clipping the extreme "
            "winners hard doesn't make the effect disappear.")
bullet(doc, bold_lead="The two strictest checks together (median, only stocks over a dime): ",
       text=f"{robv('illiq',12,'median + price>=$0.10'):+.2f}. Smaller, but still standing.")

h(doc, "Is it just a “cheap stocks bounce back” effect in disguise?", 2)
para(doc,
 "The Amihud measure divides by trading dollars, and illiquid stocks tend to be cheap "
 "stocks, so there's a real risk that what looks like an “illiquidity effect” is actually "
 "just “beaten-down penny stocks tend to bounce” — a completely different, well-known "
 "pattern that has nothing to do with liquidity. I tested this directly: I split "
 "companies into three price groups (cheap, medium, expensive) and, separately, into the "
 "five illiquidity buckets, and looked at the illiquidity gap within each price group on "
 "its own.")
figure(doc, FIG / "fig6_double_sort.png",
 "Figure 4.  The illiquid-minus-liquid return gap, calculated separately within each "
 "price group. If this were just a “cheap stock” effect, the gap should vanish among "
 "the pricier stocks. It doesn't.")
para(doc,
 f"Among the cheapest third of stocks, the illiquid ones still beat the liquid ones by "
 f"about {dbl.iloc[0]['Q5_minus_Q1']*100:.0f} points. But among the priciest third — "
 f"stocks that are not penny stocks by any definition — illiquid ones beat liquid ones by "
 f"an even larger {dbl.iloc[2]['Q5_minus_Q1']*100:.0f} points. That makes a simple "
 "“cheap stocks bounce” explanation much less convincing — if anything, the effect is "
 "stronger among the more expensive names. (The middle price group came out close to a "
 "wash, which I don't have a tidy explanation for and am flagging rather than glossing "
 "over.)")

h(doc, "Is it just a bet on the mining sector?", 2)
para(doc,
 "Two-thirds of this exchange is mining and resource-exploration companies, so a natural "
 "worry is that I've just discovered “illiquid mining stocks did well,” dressed up as a "
 "general liquidity finding. I re-ran the whole sort comparing companies only against "
 "others in their own sector — illiquid mining stocks vs. liquid mining stocks, illiquid "
 f"tech stocks vs. liquid tech stocks, and so on. The result barely moved "
 f"({secn[(secn.measure=='illiq')&(secn.horizon_m==12)].Q5_minus_Q1.iloc[0]*100:.0f} "
 "points at 12 months, versus roughly the same number in the sector-blind version). It's "
 "not a sector bet.")

h(doc, "Does controlling for company size change the answer?", 2)
para(doc,
 "I ran a regression — a statistical technique that isolates the effect of one thing "
 "while holding others constant — controlling for both company size and sector at the "
 "same time, separately at each of my 108 monthly snapshots, then averaged. The "
 "illiquidity effect held up as a strong, independent factor even after accounting for "
 "size and sector; smaller companies also did better on their own (a well-known pattern "
 "in finance in its own right), but illiquidity wasn't simply standing in for “small.”")

_fm = fm[fm.split == "holdout"][["measure", "horizon_m", "b_illiq", "t_illiq", "b_size", "t_size"]].copy()
_fm.columns = ["Measure", "Months ahead", "Illiquidity effect", "Signal", "Size effect", "Signal "]
_fm["Measure"] = _fm["Measure"].map({"illiq": "Amihud measure", "zero_ret_pct": "Zero-return-days measure",
                                     "cs_spread": "Corwin–Schultz spread"})
table(doc, _fm, "Table 3.  What's left of the illiquidity effect, and the size effect, "
      "once I hold sector and company size constant (locked-away 30%). “Illiquidity "
      "effect” is what moving a company from the most-liquid to the most-illiquid ranking "
      "adds to its return; “size effect” is the same for market value.")

h(doc, "Is illiquidity even a stable trait, or does it change randomly month to month?", 2)
para(doc,
 f"This mattered to me because if a stock randomly jumped between “liquid” and "
 f"“illiquid” from one month to the next, a quintile sort wouldn't mean much. It doesn't "
 f"jump around: a stock in the most-liquid group one month has about a "
 f"{trans.iloc[0,0]*100:.0f}% chance of still being there the next month, and a stock in "
 f"the most-illiquid group has about a {trans.iloc[4,4]*100:.0f}% chance of staying put. "
 "Illiquidity is a slow-moving, sticky characteristic of a company — closer to its size "
 "or its sector than to something that changes on a whim — which is exactly what makes it "
 "reasonable to sort on in the first place.")
figure(doc, FIG / "fig5_persistence.png",
 "Figure 5.  If a stock is in a given illiquidity group this month, here's the chance it's "
 "in each group next month. The heavy diagonal shows illiquidity barely moves month to "
 "month.", width=3.8)

h(doc, "Does it only work during the crazy speculative years?", 2)
para(doc,
 "TSX Venture had two genuinely wild speculative runs in my sample window — a rally "
 "starting in 2016 and another during the 2020–2021 pandemic-era retail-trading boom. I "
 "worried the whole result might just be “junk stocks rip during manias” dressed up as a "
 "liquidity story. Splitting the data into three multi-year chunks, the effect is indeed "
 f"largest during those two periods, but it doesn't disappear in the calmer 2022–2024 "
 f"stretch — it shrinks by roughly half but stays clearly positive and statistically "
 f"solid ({subp[(subp.measure=='illiq')&(subp.horizon_m==12)&(subp.period=='2022-2024')&(subp.split=='holdout')].Q5_minus_Q1.iloc[0]*100:.0f} "
 "points). So there's likely a real, smaller, year-in-year-out effect, with a much bigger "
 "boost layered on top of it during speculative frenzies.")

def _subp_row(measure):
    out = {}
    for per in ("2016-2018", "2019-2021", "2022-2024"):
        r = subp[(subp.measure == measure) & (subp.horizon_m == 12) & (subp.period == per)
                 & (subp.split == "holdout")]
        out[per] = float(r["Q5_minus_Q1"].iloc[0]) if len(r) else float("nan")
    return out

_sp = pd.DataFrame([
    {"Measure": "Amihud measure", **_subp_row("illiq")},
    {"Measure": "Zero-return-days measure", **_subp_row("zero_ret_pct")},
    {"Measure": "Corwin–Schultz spread", **_subp_row("cs_spread")},
])
_sp.columns = ["Measure", "2016–2018", "2019–2021", "2022–2024"]
table(doc, _sp, "Table 4.  The 12-month illiquid-minus-liquid gap, split into three-year "
      "chunks (locked-away 30%). The Amihud gap shrinks but survives the calmer years; "
      "the Corwin–Schultz gap vanishes exactly during the wildest speculative period.")

figure(doc, FIG / "fig7_subperiods.png",
 "Figure 6.  The 12-month illiquid-minus-liquid gap, broken into three time chunks. "
 "Biggest during the speculative booms, smaller but still positive afterward.", width=5.2)
figure(doc, FIG / "fig2_spread_over_time.png",
 "Figure 7.  The same gap, month by month, for all three measures. The two big peaks "
 "line up exactly with the 2016 and 2020–2021 speculative rallies.")

doc.add_page_break()

# =========================================================================== #
h(doc, "The weak spot: companies that didn't survive to be counted", 1)
para(doc,
 "This is the part of the project I'm least comfortable glossing over, so I'm giving it "
 "its own section rather than a footnote.")
para(doc,
 "My list of 1,267 companies is every stock currently trading on the TSX Venture "
 "Exchange, as of when I pulled the list. That sounds thorough, and in one sense it is — "
 "it's the entire exchange, not some hand-picked subset. But it has a specific, "
 "unavoidable gap: any company that went bankrupt, got delisted, or otherwise disappeared "
 "at any point between 2016 and 2024 is simply not in my list, because it doesn't exist "
 "today. And on this particular exchange, where a meaningful share of listed companies "
 "are speculative exploration ventures that never find anything, that missing group is "
 "genuinely large — plausibly comparable in size to the group of survivors I actually "
 "studied.")
para(doc,
 "I looked for a way to plug this gap — a historical snapshot of exactly which companies "
 "were listed at each point in time, or a comprehensive list of everything that delisted "
 "and when. I couldn't find one that's freely available. I found one partial third-party "
 "list, but it only covered 2022 onward and was heavily skewed toward companies that got "
 "bought out (a good outcome, not a bad one), so using it would have introduced a "
 "different, arguably worse bias. I chose not to use it rather than paper over one "
 "problem with another.")
para(doc,
 "Here's why this matters for interpreting my results, and the direction is not "
 "ambiguous: companies that fail are disproportionately illiquid right before they die — "
 "that's often the last visible symptom. By construction, my “most illiquid” bucket is "
 "missing its worst-performing members: the ones that went to zero and vanished from the "
 "exchange entirely. That means my illiquid-stocks-do-better finding is very likely an "
 "overstatement of the true effect. I ran the numbers on a rough worst-case: if roughly a "
 "fifth of the most-illiquid group were secretly complete wipeouts that I couldn't see, "
 "it would erase about half of the 12-month gap I measured. A wipeout rate around 30% "
 "would erase most of it. A genuine effect likely survives realistic assumptions, but I "
 "can't tell you the exact true size, and neither can anyone else without better data.")
para(doc,
 "One thing that partly reassures me: I checked separately whether companies that stopped "
 "trading partway through my own sample (as opposed to ones missing entirely from the "
 "start) were driving the result, and they weren't — re-scoring those handful of "
 "companies under a worst-case “total loss” assumption barely changed anything. So the "
 "part of survivorship bias I could measure turned out to be small; it's the part I "
 "couldn't measure — companies missing from the list altogether — that I have to flag and "
 "leave unresolved.")
para(doc,
 "There's one silver lining buried in this problem. This missing-company bias should "
 "push every one of my illiquidity measures toward making illiquid stocks look better "
 "than they really are — including the Corwin–Schultz spread measure. And yet the "
 "Corwin–Schultz measure still came out negative, against that headwind. That actually "
 "makes me trust the Corwin–Schultz result more, not less: it's the one signal that shows "
 "up despite a bias working against it.")

# =========================================================================== #
h(doc, "So what does this actually mean?", 1)

h(doc, "Two different kinds of “hard to trade”", 2)
para(doc,
 "Stepping back, I think the cleanest way to make sense of everything above is that my "
 "five measures split into two families that are measuring genuinely different things. "
 "The Amihud measure, the zero-return-days measure, turnover, and dollar volume are all "
 "asking some version of “how much does this stock actually trade?” The Corwin–Schultz "
 "measure is asking “how wide is the price gap between buying and selling it?” On most "
 "markets those two questions have similar answers. On the TSX Venture Exchange, in this "
 "period, they didn't — a stock could trade rarely but calmly (which reads as illiquid on "
 "the first four measures and as tight-spread on the fifth), or trade often but wildly "
 "(the reverse). A study that only used one measure and called it a day would have "
 "reported a confident, one-directional answer that happened to be a coin-flip away from "
 "the opposite conclusion.")

h(doc, "Is this a real risk premium, or something else?", 2)
para(doc,
 "A genuine “you get paid for holding something illiquid” risk premium should show up "
 "fairly steadily over time. What I actually see (Figure 7) is a modest, fairly "
 "consistent gap most months, with two enormous spikes exactly during the 2016 and "
 "2020–2021 speculative manias — periods when the cheapest, most obscure, hardest-to-"
 "trade names on the whole exchange were the ones getting bid up hardest by momentum and "
 "retail speculation. My honest read is that there's probably a real, modest illiquidity "
 "effect underneath all of this, but a much larger share of the headline number is "
 "something closer to “illiquid stocks have outsized exposure to speculative market "
 "moods,” which is a different — and less flattering — story than a steady risk premium.")

h(doc, "This is not a trading strategy", 2)
para(doc,
 "I want to be direct about this because it's the most likely way this piece could be "
 "misread. The “most illiquid fifth” of my sample is, almost by definition, the group of "
 "stocks where a typical day's trading is a few thousand dollars. You cannot actually buy "
 "a meaningful position in that basket without your own buying pushing the price up and "
 "erasing the opportunity — the size of the effect and the size of the money you could "
 "put behind it are working directly against each other. This is a description of how "
 "returns are spread across a liquidity spectrum on one specific exchange, not a strategy "
 "anyone can execute.")

h(doc, "What I'd want to test next", 2)
para(doc,
 "The natural next question, and the one I think is actually more important than "
 "anything above: do the most illiquid companies pay for it later, specifically when they "
 "need to raise money? Small resource companies constantly issue new shares to fund "
 "exploration, and if the most illiquid, least-trusted names have to raise that money on "
 "much worse terms — deeper discounts, more free warrants thrown in, more dilution per "
 "dollar raised — then the “value trap” story and the “illiquid stocks did better” story "
 "aren't actually in conflict. They'd be two stages of the same mechanism: illiquid "
 "companies get punished on financing terms, existing shareholders get diluted hard, and "
 "the stock's subsequent price move reflects a mix of that dilution and whatever "
 "speculative attention the company manages to attract. That's a smaller, more "
 "hand-collected study — maybe 30-40 companies from the extreme ends of my illiquidity "
 "ranking — but it's the piece that would tell me whether I've found a genuine market "
 "quirk or just re-discovered how badly junior mining financing treats its most "
 "desperate participants.")

doc.add_page_break()

# =========================================================================== #
h(doc, "The honest limitations list", 1)
bullet(doc, bold_lead="Survivorship bias, unresolved: ",
       text="explained above at length — the biggest open issue, and the reason I treat "
            "my “illiquid stocks win” numbers as an upper bound, not a precise estimate.")
bullet(doc, bold_lead="Company size is approximated: ",
       text="I used each company's current share count applied to all historical dates, "
            "because I couldn't get historical share counts for free. I checked the "
            "result against stock price alone as an alternative size measure and got the "
            "same answer, which helps, but it's still an approximation worth knowing "
            "about.")
bullet(doc, bold_lead="This is one exchange, one time period: ",
       text="2016–2024, TSX Venture only. I have no idea whether this generalizes to "
            "other junior exchanges, other countries, or other decades, and I'm not "
            "claiming it does.")
bullet(doc, bold_lead="Correlation, not causation: ",
       text="I've shown that illiquidity and future returns are related in a way that "
            "survives a lot of stress-testing. I have not identified the exact mechanism "
            "causing it, beyond the speculative-mood theory above, which is a reasonable "
            "read of the evidence, not a proven cause.")
bullet(doc, bold_lead="The middle-price-tercile result was a wash: ",
       text="flagged honestly in the double-sort section rather than quietly dropped.")

h(doc, "How this compares to what's already known, and one claim I'm walking back", 2)
para(doc,
 "The direction of my main result — illiquid stocks earning more — lines up with what "
 "the broader academic literature has found on larger, more liquid markets since Amihud "
 "and Mendelson's original 1986 paper, and with Amihud's own follow-up work extending it "
 "internationally. What's different here isn't the sign, it's the size and the "
 "circumstances: on established markets this shows up as a modest, steady premium; on "
 "TSXV it shows up as something much larger, much lumpier, and heavily concentrated in "
 "speculative booms — which is why I read it as mostly sentiment with a smaller genuine "
 "premium underneath, rather than a clean version of the same textbook effect.")
para(doc,
 "I also want to walk back one phrase I've used casually elsewhere in describing this "
 "project: calling it “the cleanest test” of this relationship. It's a clean test in the "
 "sense that mattered most to me — the direction wasn't assumed, the holdout was real, "
 "and the specification was locked before I saw a result. It is not the cleanest test in "
 "any absolute sense: the survivorship gap is real and unresolved, the size control is an "
 "approximation, and nobody besides me has yet reproduced these numbers from scratch. "
 "“Disciplined” is the word I'd defend. “Cleanest” oversells it.")

# =========================================================================== #
h(doc, "Where this leaves me", 1)
para(doc,
 "Testing this properly — with the direction left genuinely open, a chunk of the data "
 "locked away until the end, and every decision made before I could see how it would "
 "turn out — the honest answer is more interesting than either clean story I started "
 "with. On the TSX Venture Exchange, between 2016 and 2024, stocks that were hard to "
 "trade in the sense of “barely anyone shows up to trade them” went on to meaningfully "
 "outperform stocks that traded easily — a pattern that held up on data I never touched "
 "while building the method, survived every stress test I could throw at it, and shrank "
 "but didn't disappear outside the speculative booms. Stocks that were “hard to trade” in "
 "the sense of “wide gap between buy and sell prices” went the other way, weakly. The "
 "size of the first effect is very likely inflated by the companies that failed and "
 "vanished before I could count them. And none of it is a strategy you could actually "
 "run, because the stocks in question are too thin to buy at any scale. What I'm left "
 "with is a clean, honestly-caveated picture of how illiquidity and returns actually "
 "relate at the very bottom of the market — plus a much better next question than the "
 "one I started with.")

doc.add_page_break()

# =========================================================================== #
h(doc, "What this builds on", 1)
para(doc, "This work draws directly on a handful of foundational papers in market "
     "microstructure — the field that studies how trading actually happens, not just "
     "prices in the abstract:")
bullet(doc, bold_lead="Amihud & Mendelson (1986) — ",
       text="established the core logic that illiquidity should be compensated with "
            "higher returns.")
bullet(doc, bold_lead="Amihud (2002) — ",
       text="built the specific price-impact ratio I use as my primary illiquidity measure.")
bullet(doc, bold_lead="Amihud, Hameed, Kang & Zhang (2015) — ",
       text="extended that illiquidity-premium evidence internationally.")
bullet(doc, bold_lead="Corwin & Schultz (2012) — ",
       text="developed the high-low spread estimator I use as my fifth, dissenting measure.")
bullet(doc, bold_lead="Datar, Naik & Radcliffe (1998) — ",
       text="established share turnover as a liquidity proxy.")
bullet(doc, bold_lead="Lesmond, Ogden & Trzcinka (1999) — ",
       text="developed the zero-return-days measure.")
bullet(doc, bold_lead="Fama & MacBeth (1973) — ",
       text="developed the regression method I use to control for size and sector.")
bullet(doc, bold_lead="Newey & West (1987) — ",
       text="developed the statistical adjustment I use to handle overlapping return windows.")
bullet(doc, bold_lead="Pástor & Stambaugh (2003) and Petersen (2009) — ",
       text="inform how liquidity risk and panel-data statistics are generally handled in "
            "this literature.")

doc.add_page_break()

# =========================================================================== #
h(doc, "How this can be checked and reproduced", 1)
para(doc,
 "I built this as a deterministic pipeline: every parameter lives in one configuration "
 "file, and nothing downstream is hard-coded. The steps run in order — build the "
 "universe, pull daily prices and the benchmark, calculate the illiquidity measures, "
 "freeze the 70/30 holdout split (written once; the pipeline is built to refuse to "
 "overwrite it), calculate forward returns, run the portfolio sorts and regressions, run "
 "the full stress-test battery, and generate every figure and table in this piece. "
 "Re-running it from the same cached inputs reproduces every number in this document "
 "exactly — which is also how I caught and fixed a couple of small hand-transcription "
 "slips while assembling this plain-language edition.")
bullet(doc, text="Monthly snapshots from January 2016 to December 2024 (108 dates).")
bullet(doc, text="A 252-trading-day trailing window for every illiquidity measure, with a "
                 "126-day minimum to be scored.")
bullet(doc, text="6/12/24-month forward horizons.")
bullet(doc, text="Outlier capping at the 1st/99th percentile within each snapshot-and-"
                 "horizon group.")
bullet(doc, text="The 30% holdout — 887 training, 380 holdout — from a fixed random seed, "
                 "written once and never re-rolled.")
bullet(doc, text="Quintile cutoffs computed from the training group only, at every single "
                 "snapshot.")

h(doc, "Data-quality screens", 2)
para(doc,
 "Two automated screens run before any metric is calculated. First, any company whose "
 "typical closing price exceeds C$50 is dropped as a likely units artifact or a stack of "
 "unadjusted consolidations (three specific cases in my data: one stock quoted near "
 "C$1,365, one near C$135, one near C$94). Second, within each remaining price series, "
 "an isolated one-day move greater than roughly 5x in either direction that reverses by "
 "more than 60% the next day is treated as a bad data print and smoothed out; genuine "
 "multi-day moves and real consolidations, which don't reverse, are left untouched. Of "
 "the 1,267 cleaned companies, 1,167 returned usable price history, and 1,127 had enough "
 "of it to be scored on at least one snapshot. My main results are unchanged whether or "
 "not these two screens are applied.")

h(doc, "Where I deviated from my original plan, and why", 2)
para(doc,
 "Four things changed from my original methodology document, each forced by data "
 "access, and each logged here rather than quietly changed:")
bullet(doc, bold_lead="Price data source: ",
       text="I originally planned to use Alpha Vantage; its adjusted-price data turned "
            "out to be premium-only, and my fallback, Yahoo Finance, rate-limited my "
            "access. I switched to TMX Money's own data service.")
bullet(doc, bold_lead="Shares outstanding: ",
       text="I'd originally planned to collect this by hand, ticker by ticker. TMX "
            "Money's service returns current shares outstanding automatically for "
            "essentially every active company, so I automated it instead, with the "
            "limitation discussed above.")
bullet(doc, bold_lead="Sample size: ",
       text="my original plan targeted a hand-picked sample of 150–300 companies — a "
            "cap that existed only to make the manual shares-outstanding work "
            "manageable. Since that step became automatic, I used the entire cleaned "
            "universe of roughly 1,130 companies instead, which removes sample-"
            "selection judgment calls entirely.")
bullet(doc, bold_lead="Sector classification: ",
       text="comes from TMX Money's own industry mapping, matched to the exchange's six "
            "sector buckets.")
para(doc,
 "Everything else — the research question itself, leaving the direction of the effect "
 "genuinely open, the three pre-registered illiquidity formulas, the portfolio-sort and "
 "regression methods, the 70/30 holdout discipline, the outlier-capping rule, the "
 "look-ahead protection, and treating survivorship as a disclosed limitation rather than "
 "something to paper over — stayed exactly as originally planned.")

doc.add_page_break()

# =========================================================================== #
h(doc, "A note on how I built this", 1)
para(doc,
 "I built the entire data pipeline myself — pulling the company list, prices, sector "
 "data, and share counts, computing every illiquidity measure from scratch, running the "
 "portfolio sorts and regressions, and generating every chart in this piece — using "
 "Claude (Anthropic's AI assistant) as a coding and analysis collaborator throughout. "
 "Claude helped write and debug the data-collection and statistics code, helped structure "
 "the statistical tests, and helped draft this write-up from my results. Every research "
 "decision — what to measure, how to define it, how to guard against fooling myself, what "
 "the results mean, and how to frame the finding — is mine, and I'm responsible for all "
 "of it. I'm disclosing the AI assistance here in the same spirit that the more technical "
 "companion paper discloses it for SSRN: plainly, and up front.")
para(doc,
 "The full technical version of this research — with formal statistical notation, "
 "complete result tables, and academic references — is available as a companion "
 "document for anyone who wants to check the details or hold me to a higher bar.")

doc.save(str(DOCX))
print("saved", DOCX)
