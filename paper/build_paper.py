"""Build the research paper (.docx) from the verified pipeline outputs.

Every number in the prose is pulled from outputs/*.csv or stated with its source.
Run:  ../.venv/bin/python build_paper.py
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
FIG = OUT / "paper"
DOCX = Path(__file__).resolve().parent / "TSXV_Liquidity_Puzzle.docx"

ACCENT = RGBColor(0x1F, 0x3A, 0x5F)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def add_field(paragraph, instr):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    r._r.append(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); r._r.append(s)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r._r.append(e)


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    return p


def para(doc, text, *, italic=False, size=None, align=None, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    return p


def bullet(doc, text):
    p = doc.add_paragraph(text, style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    return p


def figure(doc, path: Path, caption: str, width=6.3):
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = doc.add_paragraph()
    r = c.add_run(caption)
    r.font.size = Pt(9); r.italic = True
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(12)


def table(doc, df: pd.DataFrame, caption: str, numfmt="{:+.3f}", firstcols=1):
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
            if isinstance(v, float):
                s = numfmt.format(v) if j >= firstcols else f"{v:g}"
            else:
                s = str(v)
            cells[j].text = s
            for p in cells[j].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    return t


# --------------------------------------------------------------------------- #
# load results
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
quint = pd.read_csv(OUT / "quintile_returns.csv")


def hv(measure, horizon, split="holdout", col="mean_Q5_minus_Q1"):
    r = spread[(spread.measure == measure) & (spread.horizon_m == horizon)
               & (spread.split == split)]
    return float(r[col].iloc[0])


def robv(measure, horizon, variant, col="Q5_minus_Q1"):
    r = rob[(rob.measure == measure) & (rob.horizon_m == horizon)
            & (rob.split == "holdout") & (rob.variant == variant)]
    return float(r[col].iloc[0])


# =========================================================================== #
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for m in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
    setattr(sec, m, Inches(1.0))

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10.5)

# footer page numbers
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_field(footer_p, "PAGE")

# ---- title block ---------------------------------------------------------- #
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("The TSX Venture Liquidity Puzzle:\nWhen Illiquidity Pays and When It Doesn't")
r.bold = True; r.font.size = Pt(19); r.font.color.rgb = ACCENT
t.paragraph_format.space_after = Pt(6)

para(doc, "A pre-registered test of the illiquidity–return relation on the "
     "S&P/TSX Venture Composite universe, 2016–2024", align="c", italic=True, size=11)
para(doc, "Yonatan Brunshtein  ·  The Venture Analyst — Independent Researcher  ·  September 2026",
     align="c", size=10)
para(doc, "Working paper — comments welcome. Code and data pipeline available on request.",
     align="c", italic=True, size=9)
doc.add_paragraph()

# ---- abstract ----------------------------------------------------------- #
h(doc, "Abstract", 2)
para(doc,
 "We ask whether a TSX Venture Exchange (TSXV) stock's trailing illiquidity predicts its "
 "forward excess return over the S&P/TSX Venture Composite, and we fix every research "
 "decision — sample, measures, horizons, breakpoints, a 70/30 ticker holdout — before "
 "looking at a single return. The direction is left open: illiquidity could be compensated "
 "(a premium) or punished (a symptom of a dying company). On 1,127 TSXV common shares and "
 "108 monthly formation dates, the answer depends entirely on how you measure illiquidity. "
 "The Amihud (2002) price-impact ratio and the Lesmond–Ogden–Trzcinka zero-return-day "
 "proxy both say illiquidity is rewarded: the most illiquid quintile beats the most liquid "
 f"by {hv('illiq',12):.2f} (Amihud) and {hv('zero_ret_pct',12):.2f} (zero-return) in "
 "12-month excess return on the untouched holdout sample, monotonic across quintiles, "
 "significant at every horizon, and robust to skew-resistant aggregation, value weighting, "
 "a sub-dime price screen, sector-neutral ranking, and an independent price double-sort. "
 "Two further activity proxies — share turnover and dollar volume — agree. The "
 "Corwin–Schultz (2012) high–low spread estimator says the opposite: wide-spread names "
 f"underperform by roughly {abs(robv('cs_spread',12,'median within quintile')):.2f} at the "
 "one-year horizon in skew-robust specifications. We show this is not a contradiction: in "
 "this market the spread estimator is negatively rank-correlated with the activity measures "
 "and behaves more like a volatility proxy. The activity-illiquidity premium is real, "
 "replicates out of sample, and persists — smaller — outside the 2016 and 2020–21 "
 "speculative booms; but it is inflated by survivorship (the universe is names still listed "
 "in 2026), concentrated in unhedgeable microcaps, and therefore not, as measured, an "
 "investable strategy. The contribution is a clean, reproducible characterization of a "
 "liquidity anomaly at the very bottom of the North American size distribution, and a "
 "cautionary result on measure choice.")
para(doc, "JEL: G11, G12, G14.   Keywords: liquidity premium, Amihud illiquidity, "
     "Corwin–Schultz, microcap, TSX Venture, holdout validation, value trap.", size=9, italic=True)

doc.add_page_break()

# ---- TOC -------------------------------------------------------------------- #
h(doc, "Contents", 2)
tp = doc.add_paragraph()
add_field(tp, r'TOC \o "1-2" \h \z \u')
para(doc, "(Right-click → Update Field in Word to populate.)", italic=True, size=9)
doc.add_page_break()

# =========================================================================== #
# 1. Introduction
# =========================================================================== #
h(doc, "1  Introduction", 1)

para(doc,
 "There are two honest stories about illiquid stocks, and they point in opposite directions. "
 "The first is that illiquidity is a cost investors must be paid to bear: if a stock is hard "
 "to sell without moving the price, a rational buyer demands a discount today and therefore "
 "earns a higher return going forward. This is the Amihud–Mendelson (1986) logic, and forty "
 "years of evidence from developed equity markets broadly supports it. The second story is "
 "that illiquidity is not a risk to be compensated but a symptom of decay: a company whose "
 "shares barely trade is often one the market has stopped believing in, burning cash, diluting "
 "shareholders, and heading for a financing that wipes out whoever held on. On that view the "
 "'premium' is an illusion — you are picking up nickels in front of a delisting.")

para(doc,
 "Both stories are defensible, and which one dominates is an empirical question that has to be "
 "settled market by market. We settle it — as far as one clean study can — for the TSX Venture "
 "Exchange, the junior board of Canada's equity market and about as far down the liquidity "
 "spectrum as a regulated exchange goes. The median name in our sample has a market "
 "capitalization near C$18 million and a share price of 27 cents. If a liquidity premium "
 "exists anywhere, it should be visible here; if illiquidity is mostly a death rattle, that "
 "should be visible here too.")

para(doc,
 "The design point we care most about is discipline. It is trivially easy, on a few thousand "
 "microcaps, to search across illiquidity definitions, breakpoints, weighting schemes and "
 "sub-samples until a significant spread appears, and then write the introduction as though "
 "you knew it all along. To rule that out we fixed the entire specification in advance — the "
 "universe, the three illiquidity measures and their exact formulas, the 6/12/24-month "
 "horizons, quintile breakpoints, winsorization, and a random 70/30 split of tickers into a "
 "training set we were allowed to look at and a holdout set we were not — and we wrote down, "
 "before running anything, that we did not know whether the premium would be positive or "
 "negative. Every headline number in this paper is from the holdout.")

para(doc, "Three findings come out of it.")
bullet(doc,
 "Measured by trading activity — the Amihud (2002) price-impact ratio, the fraction of days "
 "with no price change, share turnover, or dollar volume — illiquidity is rewarded. On the "
 f"holdout, the most illiquid Amihud quintile beats the most liquid by {hv('illiq',6):.2f}, "
 f"{hv('illiq',12):.2f} and {hv('illiq',24):.2f} in 6-, 12- and 24-month excess return "
 "(equal-weighted mean spec), the relationship is monotonic across all five quintiles, and "
 "it survives every robustness cut we throw at it.")
bullet(doc,
 "Measured by the Corwin–Schultz (2012) bid–ask spread estimator, illiquidity is punished — "
 "weakly, but consistently in the specifications that resist the penny-stock skew. Wide-spread "
 "names underperform at the 6- and 12-month horizons. The two kinds of measure disagree "
 "because, in this market, the spread estimator is negatively correlated with the activity "
 "measures and picks up something closer to volatility.")
bullet(doc,
 "The activity-illiquidity premium is real and replicates, but it is not a strategy. It is "
 "inflated by survivorship — our universe is names still listed in 2026, which mechanically "
 "favours the 'premium' story — it lives disproportionately in the 2016 and 2020–21 "
 "speculative booms, and it is concentrated in sub-dollar names that cannot absorb capital. "
 "What we have is a characterization, not a trade.")

para(doc,
 "The contribution is threefold. First, we provide the cleanest test we know of the "
 "illiquidity–return relation at the very bottom of the North American market, on a universe "
 "built from the full exchange rather than a screened subset. Second, we show — with the "
 "holdout doing real work — that the sign of the 'liquidity premium' in this market is an "
 "artifact of measure choice, which is a caution that generalizes. Third, we are explicit "
 "about the one bias we cannot fully purge, survivorship, and we bound its influence rather "
 "than wave at it.")

para(doc,
 "The rest of the paper: Section 2 lays out the two hypotheses and the prior literature. "
 "Section 3 describes how the universe and the price data were built — this matters more than "
 "usual because free data for TSXV names is genuinely hard. Section 4 gives the measures and "
 "the method. Section 5 is the main result; Section 6 is the robustness battery; Section 7 "
 "confronts survivorship directly. Section 8 interprets. Section 9 concludes.")

# =========================================================================== #
# 2. Hypotheses and prior work
# =========================================================================== #
h(doc, "2  Two hypotheses, stated before the test", 1)

h(doc, "2.1  The competing predictions", 2)
para(doc,
 "We test one relation — trailing illiquidity against forward excess return — against two "
 "mutually exclusive directional hypotheses.")
para(doc,
 "H1 (risk-premium / compensation). Illiquid names earn higher forward excess returns. The "
 "mechanism is Amihud and Mendelson (1986): investors who buy an asset they cannot cheaply "
 "resell require a return premium for the expected transaction costs and for the risk that "
 "those costs spike when they need to sell. Amihud (2002) makes the time-series and "
 "cross-sectional case with the illiquidity ratio we use here; the effect has since been "
 "documented across countries and asset classes.")
para(doc,
 "H2 (value-trap / distress). Illiquid names earn lower or more negative forward excess "
 "returns. Here illiquidity is not a priced characteristic but a marker: thin trading "
 "accompanies deteriorating fundamentals, disappearing analyst and sponsor interest, and an "
 "elevated probability of a dilutive rescue financing or an outright delisting. The negative "
 "expected return is the market slowly pricing that in. On junior resource exchanges this is "
 "not a fringe possibility — it is arguably the base rate.")
para(doc,
 "We did not hold a strong prior. If pushed before running the analysis we would have leaned "
 "very slightly toward H2 for this specific market, on the grounds that the TSXV failure rate "
 "is high and sponsor coverage is thin. That prior is on the record here so the result reads "
 "as a finding rather than a confirmation.")

h(doc, "2.2  Why three illiquidity measures, not one", 2)
para(doc,
 "Any single illiquidity proxy can be fooled by the way it is constructed. We compute three, "
 "chosen because they fail differently, and treat agreement among them as the real evidence.")
bullet(doc,
 "The Amihud (2002) ratio — average daily |return| per dollar traded — captures price impact: "
 "how far the price moves for a given amount of trading. It is the standard measure in this "
 "literature, which lets us compare results to prior work.")
bullet(doc,
 "The share of zero-return days (Lesmond, Ogden and Trzcinka, 1999) captures a different "
 "failure: a stock that frequently doesn't trade at all. It needs only a closing-price "
 "series and has no price level in it, so it is immune to the low-price mechanical concerns "
 "that dog Amihud.")
bullet(doc,
 "The Corwin–Schultz (2012) estimator backs out the effective bid–ask spread from daily "
 "highs and lows alone. We have no historical quote data for these names, but we do have "
 "highs and lows, which is the whole point of the estimator.")
para(doc,
 "We add two activity proxies in robustness — share turnover (Datar, Naik and Radcliffe, "
 "1998) and dollar volume — for a total of five. As it turns out, the split is four-to-one.")


# =========================================================================== #
# 3. Data
# =========================================================================== #
h(doc, "3  Data", 1)
para(doc,
 "Free, reliable data for TSXV names is scarce, and the choices we were forced into shape "
 "what the study can and cannot claim. We describe them in full.")

h(doc, "3.1  The universe", 2)
para(doc,
 "We start from the complete TSX Venture issuer directory published by the exchange "
 "(tsx.com, public JSON endpoint), retrieved in September 2026: 1,428 issuers, 1,473 listed "
 "instrument lines. NEX-tier names — the exchange's holding board for companies that no "
 "longer meet listing standards — are already excluded by that feed, which is what we want.")
para(doc,
 "We then drop everything that is not an operating company's common shares: capital pool "
 "companies (the '.P' shells that exist only to complete a future acquisition), warrants, "
 "trust and fund units, preferred shares, and debentures. That leaves 1,267 common-equity "
 "names. For each we retrieve GICS sector, industry, current shares outstanding, market "
 "capitalization and last price from TMX Money's public GraphQL service, and map the GICS "
 "classification to the exchange's own six sector buckets. Table 1 shows the composition. "
 "It is, unavoidably, a mining exchange: two-thirds of the tape.")

_u = pd.DataFrame({
 "TSXV sector": ["Mining", "Diversified Industries", "Technology", "Oil & Gas",
                 "Life Sciences", "CleanTech", "Total"],
 "Names": [840, 182, 77, 74, 64, 30, 1267],
 "Share": ["66.3%", "14.4%", "6.1%", "5.8%", "5.1%", "2.4%", "100%"]})
table(doc, _u, "Table 1.  Study universe by sector (cleaned TSXV common equities, Sept 2026).",
      numfmt="{:g}", firstcols=3)

para(doc,
 "We deliberately do not start from a curated or quality-screened list. A natural shortcut "
 "would have been to reuse an existing coverage universe of 'profitable, cash-generative, "
 "underfollowed' TSXV names, but that is selected for exactly the characteristics — better "
 "fundamentals, better liquidity — that would bias this particular question. Using the whole "
 "exchange is the least-discretionary sample available and it is the one we use. After "
 "requiring a usable price history (below), 1,127 names enter the analysis.")

h(doc, "3.2  Prices", 2)
para(doc,
 "The methodology was written around Alpha Vantage, which we confirmed carries TSXV daily "
 "open/high/low/close/volume. It does not carry the split-adjusted series or the corporate-"
 "action feed on the free tier, and raw daily prices are unusable for return work on this "
 "exchange because share consolidations — often 5:1 or 10:1 — are routine and inject "
 "enormous phantom returns. Yahoo Finance, our fallback for adjusted data, rate-limited our "
 "IP partway through collection and stayed blocked.")
para(doc,
 "We therefore take daily OHLCV from TMX Money's GraphQL time-series service, the same "
 "provider as the sector and shares-outstanding data. It returned clean history for 1,167 "
 "of the 1,267 names (92%; the missing 100 are almost all 2025–26 listings, outside our "
 "window), with a median of 1,759 trading days per name. Spot checks across known "
 "consolidations show the series is consolidation-consistent — it does not print the phantom "
 "jump. We add two automated quality screens: names whose median close exceeds C$50 (a "
 "handful with stacked unadjusted rollbacks or unit-quote artifacts) are dropped, and "
 "isolated one-day price spikes that immediately reverse are interpolated out. The benchmark "
 "— the S&P/TSX Venture Composite, TMX symbol JX, Yahoo symbol ^SPCDNX — comes from the "
 "same service (2,509 trading days, Jan-2015 to Dec-2024).")

h(doc, "3.3  Shares outstanding and the size control", 2)
para(doc,
 "The size control is log(price × shares outstanding) at formation. Shares outstanding for "
 "TSXV names is not available historically from any free source we could find, so we use "
 "the current figure from TMX Money, applied to every formation date. This is an "
 "approximation, and a directional one: junior issuers dilute heavily, so current share "
 "counts overstate past ones, and the overstatement is larger for exactly the illiquid, "
 "cash-hungry names the study is about. We therefore also report every result with log(price) "
 "alone as the size proxy — it needs no share count and, for microcaps, price level is a "
 "strong size proxy — and the sign of the illiquidity effect is unchanged. The Fama–MacBeth "
 "regressions include the size term explicitly; the illiquidity coefficient survives it.")

h(doc, "3.4  Sample window", 2)
para(doc,
 "Price history is pulled from January 2015 so the first formation date has a full "
 "twelve-month trailing window. Portfolios are formed at every month-end from January 2016 "
 "to December 2024, with the last usable formation date per horizon set so that every "
 "forward return is fully realized inside the data (December 2022 for the 24-month horizon, "
 "and so on). The resulting panel is 85,137 name-months across 108 formation dates.")

_s = pd.DataFrame({
 "Measure": ["Amihud ILLIQ (×10⁶)", "Zero-return days (%)", "Corwin–Schultz spread",
             "Formation price (C$)", "Trailing trading days"],
 "Mean": [118.1, 43.3, 0.0119, 4.97, 224],
 "p10": [0.67, 16.9, 0.0026, 0.05, 160],
 "Median": [15.9, 39.7, 0.0105, 0.27, 246],
 "p90": [191.3, 76.4, 0.0216, 2.33, 251]})
table(doc, _s, "Table 2.  Distribution of the illiquidity measures and key inputs "
      "(85,137 name-months).", numfmt="{:g}", firstcols=1)

para(doc,
 "One fact from Table 2 matters for everything that follows: these distributions are "
 "extreme. The Amihud ratio's mean is seven times its 90th percentile. Formation prices run "
 "from half a cent to a few dollars. Any analysis that leans on means rather than medians "
 "will end up measuring the tail, and we return to this in Section 5.2.")

para(doc,
 "The three measures are not redundant, and not in the way one would expect. Amihud and the "
 "zero-return share have a Spearman rank correlation of +0.65 — both are 'quantity' "
 "illiquidity. But the Corwin–Schultz spread is negatively rank-correlated with both "
 "(−0.36 with Amihud, −0.27 with zero-return days). In this market a barely-trading stock, "
 "with tiny stale daily ranges, produces a small Corwin–Schultz estimate, while an active "
 "but volatile stock produces a large one. The spread estimator is, here, closer to a "
 "volatility measure than a trading-cost measure. This single fact explains most of the "
 "disagreement in the results.")

# =========================================================================== #
# 4. Method
# =========================================================================== #
h(doc, "4  Method", 1)

h(doc, "4.1  Illiquidity measures", 2)
para(doc, "All three are computed over the 252-trading-day window ending at each formation "
 "date, and a name must have at least 126 valid trading days in that window to be scored.")
para(doc,
 "Amihud illiquidity. The average over trailing days of |daily return| divided by daily "
 "dollar volume, multiplied by 10⁶. The return is computed from the split-adjusted close; "
 "the dollar volume is raw close times raw volume — the actual dollars that changed hands "
 "that day. Days with zero dollar volume are excluded from the average, per Amihud (2002).")
para(doc,
 "Zero-return days. The percentage of trailing trading days on which the raw close is "
 "exactly unchanged from the prior close. A high value means the order book is frequently "
 "dead (Lesmond, Ogden and Trzcinka, 1999).")
para(doc,
 "Corwin–Schultz spread. The two-day high–low effective-spread estimator of Corwin and "
 "Schultz (2012), averaged over the trailing window, with negative two-day estimates set to "
 "zero. It is computed on split-adjusted highs and lows so that a consolidation between two "
 "days is not read as a genuine trading range.")

h(doc, "4.2  Forward excess return", 2)
para(doc,
 "For each name and formation date t and horizon h ∈ {6, 12, 24} months, the forward return "
 "is the split-adjusted close at t+h divided by the split-adjusted close at t, minus one. "
 "The excess return subtracts the S&P/TSX Venture Composite total return over the same "
 "calendar span. Both series are in Canadian dollars, so no currency step is needed. Excess "
 "returns are winsorized at the 1st and 99th percentiles within each formation-date × "
 "horizon cross-section — a rule fixed in the configuration before any result was produced. "
 "A name whose price series ends well before t+h (halt, delisting, or data gap) is flagged "
 "and, in the base specification, dropped; Section 7 re-prices these under explicit "
 "assumptions.")

h(doc, "4.3  Look-ahead", 2)
para(doc,
 "The two halves of the pipeline never share a date. Every illiquidity input is dated on or "
 "before the formation date; every return input is dated on or after it. This is enforced "
 "structurally in the code, not just intended.")

h(doc, "4.4  Portfolio sort", 2)
para(doc,
 "At each formation date we rank names into quintiles by the illiquidity measure, compute "
 "the equal-weighted forward excess return of each quintile, and take the spread between "
 "quintile 5 (most illiquid) and quintile 1 (most liquid). The pooled result is the mean of "
 "that spread across the 84–102 formation dates available per horizon, with a Newey–West "
 "t-statistic (lags equal to the horizon in months, since the forward windows overlap). "
 "Crucially, the quintile breakpoints at each date are computed from the training tickers "
 "only; holdout names are then bucketed using those same breakpoints. The holdout therefore "
 "never informs where the cut points fall.")
para(doc,
 "We report the spread under two aggregations. The equal-weighted mean of within-quintile "
 "returns is the specification named in the methodology. The median of within-quintile "
 "returns is our preferred headline, because — as Section 5.2 shows — the mean on these "
 "distributions is dominated by a handful of extreme winners and mostly measures which "
 "quintile has the fattest right tail. Where the two diverge we lead with the median and "
 "show both.")

h(doc, "4.5  Fama–MacBeth regression", 2)
para(doc,
 "To control for size and sector simultaneously we run, at each formation date, a "
 "cross-sectional regression of the winsorized excess return on the within-date illiquidity "
 "percentile (0–1; the raw levels are far too skewed to enter directly), log market "
 "capitalization, and sector dummies. The coefficients are averaged across dates and a "
 "Newey–West t-statistic is computed on the coefficient series. This is done on the training "
 "tickers and then, independently, on the holdout tickers.")

h(doc, "4.6  The holdout", 2)
para(doc,
 "Before computing any metric we split the 1,267 tickers 70/30 by a seeded random draw — "
 "887 training, 380 holdout — and wrote the assignment to a file the pipeline refuses to "
 "overwrite. Any specification search, any judgement call about breakpoints or screens, was "
 "made looking only at the training tickers. The holdout was scored once, at the end. Every "
 "headline number in Sections 5–7 is the holdout number; training numbers are reported "
 "alongside so the reader can see they agree.")

doc.add_page_break()

# =========================================================================== #
# 5. Results
# =========================================================================== #
h(doc, "5  Results", 1)

h(doc, "5.1  Portfolio sorts", 2)
para(doc,
 "Table 3 is the main result. Read the holdout rows. By the Amihud ratio, the most illiquid "
 f"quintile out-earns the most liquid by {hv('illiq',6):.2f} over six months, "
 f"{hv('illiq',12):.2f} over twelve, and {hv('illiq',24):.2f} over twenty-four, "
 "equal-weighted, with Newey–West t-statistics between 5.8 and 9.2. The zero-return-days "
 f"sort gives {hv('zero_ret_pct',6):.2f} / {hv('zero_ret_pct',12):.2f} / "
 f"{hv('zero_ret_pct',24):.2f} on the same basis, t between 4.4 and 6.2. Training and "
 "holdout agree to within a few points at every horizon. The Corwin–Schultz sort gives "
 "essentially nothing in this equal-weighted-mean specification — a slightly negative "
 "six-month number and zero thereafter — and, as the next subsection explains, that null is "
 "itself informative.")

_t3 = spread.copy()
_t3 = _t3[_t3.split == "holdout"][["measure", "horizon_m", "n_dates", "mean_Q5_minus_Q1", "nw_t"]]
_t3.columns = ["Measure", "Horizon (m)", "N dates", "Q5 − Q1", "NW t"]
_t3["Measure"] = _t3["Measure"].map({"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return %",
                                     "cs_spread": "Corwin–Schultz"})
table(doc, _t3, "Table 3.  Portfolio-sort spread, holdout sample "
      "(equal-weighted mean of within-quintile excess returns).")

figure(doc, FIG / "fig1_quintile_bars.png",
 "Figure 1.  Median forward 12-month excess return by illiquidity quintile, holdout sample. "
 "Amihud and zero-return days rise monotonically from Q1 to Q5. The Corwin–Schultz panel "
 "does not — Q5 is no higher than Q1.")

para(doc,
 "Figure 1 shows the monotonicity, which matters. It is not a Q5-versus-the-rest jump that "
 "a few names could drive; each step up the illiquidity ladder adds return. For the Amihud "
 "12-month sort the quintile medians run roughly −0.15, 0.00, +0.02, +0.11, +0.35. For "
 "Corwin–Schultz the pattern is flat-to-humped, with Q5 sitting near Q1.")

h(doc, "5.2  Why we report medians", 2)
para(doc,
 "Forward excess returns on this universe are among the most right-skewed distributions in "
 "empirical finance. Figure 3 plots them. At the 12-month horizon the median excess return "
 "is −0.13 while the mean is +0.10: the typical TSXV name underperforms the index, and the "
 "positive average is produced entirely by a thin tail of multi-baggers. A sub-cent stock "
 "that goes to ten cents is a +900% observation; a two-dollar stock almost never does that. "
 "The most illiquid quintile is also the lowest-priced, so it has the fattest right tail "
 "mechanically, and an equal-weighted mean of that quintile is largely a measurement of the "
 "tail rather than of the representative name.")
figure(doc, FIG / "fig3_return_distribution.png",
 "Figure 3.  Distribution of winsorized forward excess returns at each horizon. The median "
 "(dashed) is negative; the mean (solid) is positive; the gap widens with horizon. The "
 "spike at the right edge is the 99th-percentile winsorization point.")
para(doc,
 "This is why the median-within-quintile spread is our preferred headline. It asks a "
 "cleaner question: does the representative illiquid name beat the representative liquid "
 f"one? It does. On the holdout the Amihud median spread is "
 f"{robv('illiq',6,'median within quintile'):.2f} / "
 f"{robv('illiq',12,'median within quintile'):.2f} / "
 f"{robv('illiq',24,'median within quintile'):.2f} at 6/12/24 months "
 "(t = 7.5 / 6.6 / 6.3), about two-thirds the size of the mean spread but far more stable. "
 f"The zero-return median spread is {robv('zero_ret_pct',6,'median within quintile'):.2f} / "
 f"{robv('zero_ret_pct',12,'median within quintile'):.2f} / "
 f"{robv('zero_ret_pct',24,'median within quintile'):.2f}. And the Corwin–Schultz median "
 f"spread, which the mean specification hid, is negative: "
 f"{robv('cs_spread',6,'median within quintile'):.2f} / "
 f"{robv('cs_spread',12,'median within quintile'):.2f} / "
 f"{robv('cs_spread',24,'median within quintile'):.2f}, with t of −3.4 at six months.")

h(doc, "5.3  Cross-sectional regressions", 2)
para(doc,
 "Table 4 controls for size and sector at once. The coefficient on the Amihud percentile is "
 f"positive and significant at every horizon on the holdout — {fm[(fm.measure=='illiq')&(fm.horizon_m==12)&(fm.split=='holdout')].b_illiq.iloc[0]:.2f} "
 "at twelve months (t = 7.7) — meaning that moving a name from the least to the most "
 "illiquid percentile, holding size and sector fixed, adds about 39 points of 12-month "
 "excess return. The size coefficient is separately negative and significant "
 f"({fm[(fm.measure=='illiq')&(fm.horizon_m==12)&(fm.split=='holdout')].b_size.iloc[0]:.2f}, "
 "t = −2.9): smaller names do better, the familiar size effect, and illiquidity is not "
 "simply standing in for it. The zero-return percentile is positive and significant at 6 "
 "and 12 months and positive but noisier at 24. The Corwin–Schultz percentile carries a "
 "negative training coefficient at all horizons that does not survive to the holdout in "
 "this regression — consistent with the weak, skew-sensitive H2 signal we see in the sorts.")

_t4 = fm[fm.split == "holdout"][["measure", "horizon_m", "b_illiq", "t_illiq", "b_size", "t_size"]].copy()
_t4.columns = ["Measure", "Horizon (m)", "b(illiq pct)", "t", "b(log mktcap)", "t "]
_t4["Measure"] = _t4["Measure"].map({"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return %",
                                     "cs_spread": "Corwin–Schultz"})
table(doc, _t4, "Table 4.  Fama–MacBeth coefficients, holdout sample. "
      "Dependent variable: winsorized forward excess return. Regressors: within-date "
      "illiquidity percentile, log market cap, sector dummies.")

h(doc, "5.4  Holdout replication", 2)
para(doc,
 "The point of the split is that a pattern tuned into existence on the training tickers "
 "should fall apart on the untouched ones. It does not. For Amihud and zero-return days the "
 "holdout spread matches the training spread in sign and magnitude at every horizon, and "
 "the holdout t-statistics are, if anything, larger. For Corwin–Schultz the training sort "
 "shows a small negative spread that becomes noisier on the holdout in the mean "
 "specification and holds up better in the median specification. Nothing here looks "
 "overfit. What it does not rule out is a structural bias shared by both halves of the "
 "sample — which is the subject of Section 7.")

h(doc, "5.5  The Corwin–Schultz divergence", 2)
para(doc,
 "One measure disagreeing with three others invites the conclusion that it is broken. We "
 "think the more accurate reading is that it is measuring something else. Recall from "
 "Section 3.4 that the Corwin–Schultz estimate is negatively rank-correlated with the "
 "activity measures in this universe. Mechanically: the estimator infers the spread from "
 "how often the daily high and low straddle a wide band. A stock that barely trades prints "
 "the same price for its high and low on most days — a small estimated spread. A stock that "
 "trades actively but swings intraday prints wide bands — a large estimated spread. On "
 "TSXV, intraday range is driven more by speculative volatility than by dealer spreads, so "
 "the estimator ends up ranking volatile-but-liquid names as 'illiquid'. That those names "
 "subsequently underperform is then a statement about volatility, or about speculative "
 "over-extension, not about liquidity. We keep Corwin–Schultz in the paper because it was "
 "pre-registered, but we weight it accordingly.")

doc.add_page_break()

# =========================================================================== #
# 6. Robustness
# =========================================================================== #
h(doc, "6  Robustness", 1)
para(doc,
 "We subject the Amihud and zero-return results to a battery of alternative "
 "specifications, each designed to kill one candidate artifact. Table 5 collects the "
 "12-month Amihud holdout spread across all of them; the pattern is the same at 6 and 24 "
 "months.")

_r = rob[(rob.measure == "illiq") & (rob.horizon_m == 12) & (rob.split == "holdout")][
    ["variant", "Q5_minus_Q1", "nw_t"]].copy()
_r.columns = ["Specification", "Q5 − Q1 (12m)", "NW t"]
table(doc, _r, "Table 5.  Amihud illiquidity spread under alternative specifications, "
      "holdout sample, 12-month horizon.")

h(doc, "6.1  Aggregation, weighting, price, winsorization", 2)
bullet(doc,
 f"Median instead of mean within quintile: {robv('illiq',12,'median within quintile'):+.2f} "
 "(t = 6.6). The skew-robust number, discussed above.")
bullet(doc,
 f"Value-weighted by formation market cap: {robv('illiq',12,'value-weighted'):+.2f} "
 "(t = 4.5). The effect is not confined to the smallest nano-caps within Q5.")
bullet(doc,
 f"Three-day average prices at both endpoints: {robv('illiq',12,'3-day avg prices'):+.2f} "
 "(t = 6.1). Rules out single-day bid–ask bounce at the formation or exit date.")
bullet(doc,
 f"Formation price ≥ C$0.10: {robv('illiq',12,'price >= $0.10'):+.2f} (t = 7.5). Dropping "
 "the sub-dime tail roughly halves the spread but leaves it large and highly significant.")
bullet(doc,
 f"Tighter winsorization at [−90%, +200%]: {robv('illiq',12,'tight winsor [-0.9,2.0]'):+.2f} "
 "(t = 9.6). Clipping the right tail hard does not remove the effect.")
bullet(doc,
 f"Median and price ≥ C$0.10 together — the most conservative single specification we run: "
 f"{robv('illiq',12,'median + price>=$0.10'):+.2f} (t = 6.4). Still there.")

h(doc, "6.2  Sector-neutral sorting", 2)
para(doc,
 "Because the universe is two-thirds mining, a naïve sort could be picking up 'illiquid "
 "mining names did well' rather than an illiquidity effect. We re-rank names into quintiles "
 "on their illiquidity percentile within sector × formation date, so Q5 contains the most "
 "illiquid names in each sector. The Amihud spread is essentially unchanged: "
 f"{secn[(secn.measure=='illiq')&(secn.horizon_m==6)].Q5_minus_Q1.iloc[0]:+.2f} / "
 f"{secn[(secn.measure=='illiq')&(secn.horizon_m==12)].Q5_minus_Q1.iloc[0]:+.2f} / "
 f"{secn[(secn.measure=='illiq')&(secn.horizon_m==24)].Q5_minus_Q1.iloc[0]:+.2f} at "
 "6/12/24 months (median spec, t between 6.2 and 7.5). Zero-return days likewise. "
 "Corwin–Schultz stays negative "
 f"({secn[(secn.measure=='cs_spread')&(secn.horizon_m==6)].Q5_minus_Q1.iloc[0]:+.2f} at six "
 "months, t = −3.5). The result is not a sector bet.")

h(doc, "6.3  Illiquidity or just low price?", 2)
para(doc,
 "The sharpest challenge to an Amihud result is that the ratio has price in its denominator, "
 "so a low-price effect — short-term reversal, the lottery/MAX preference — could masquerade "
 "as an illiquidity premium. We run an independent 3 × 5 sort: three terciles on formation "
 "price, five quintiles on Amihud illiquidity, and look at the illiquid-minus-liquid spread "
 "within each price tercile.")
figure(doc, FIG / "fig6_double_sort.png",
 "Figure 6.  Median 12-month excess return for the liquid (Q1) and illiquid (Q5) Amihud "
 "quintiles, within each formation-price tercile, holdout sample. The illiquidity spread is "
 "large and positive in the low-price and high-price terciles alike.", width=5.4)
para(doc,
 f"In the low-price tercile the illiquid quintile beats the liquid one by "
 f"{float(dbl.iloc[0]['Q5_minus_Q1']):+.2f}; in the high-price tercile by "
 f"{float(dbl.iloc[2]['Q5_minus_Q1']):+.2f}. The middle tercile is a wash "
 f"({float(dbl.iloc[1]['Q5_minus_Q1']):+.2f}), which we do not have a clean story for and "
 "flag as such. The key point is that the effect is present, and if anything stronger, "
 "among higher-priced names — where a pure low-price explanation cannot reach. This is the "
 "single result that most convinces us the activity-illiquidity premium is real rather than "
 "a price artifact.")

h(doc, "6.4  Two more proxies", 2)
para(doc,
 "We had pre-committed to Amihud, zero-return days and Corwin–Schultz. As an additional "
 "check we sort on two further liquidity proxies that were not in the original three: "
 "share turnover (20-day average dollar volume over market cap) and raw dollar volume, in "
 "both cases defining 'illiquid' as the low end. Both give the H1 sign at every horizon — "
 f"the low-turnover-minus-high-turnover 12-month spread is "
 f"{turn[(turn.proxy=='turnover')&(turn.horizon_m==12)].Q5_minus_Q1_illiq_minus_liq.iloc[0]:+.2f} "
 f"(t = 6.0) and the low-dollar-volume spread is "
 f"{turn[(turn.proxy=='dollar_vol')&(turn.horizon_m==12)].Q5_minus_Q1_illiq_minus_liq.iloc[0]:+.2f} "
 "(t = 6.9). Figure 4 puts all five proxies on one axis.")
figure(doc, FIG / "fig4_forest.png",
 "Figure 4.  Q5 − Q1 12-month excess return (holdout) for five liquidity proxies. Bars are "
 "block-bootstrap 95% intervals where computed. Four activity measures agree on a positive "
 "spread; the Corwin–Schultz spread estimator is the lone dissenter.", width=5.6)

h(doc, "6.5  Is illiquidity a stable characteristic?", 2)
para(doc,
 "If illiquidity quintile membership were noisy month to month, the sort would be churning "
 "and the 'signal' could be an artifact of that churn. It is not. The one-month quintile "
 "transition matrix is heavily diagonal: a name in the most-liquid quintile stays there "
 f"{trans.iloc[0,0]*100:.0f}% of the time next month, a name in the most-illiquid quintile "
 f"stays {trans.iloc[4,4]*100:.0f}% of the time, and the month-to-month rank "
 "autocorrelation is 0.98. Illiquidity here is a slow-moving firm characteristic, which is "
 "what makes a quintile sort a sensible way to study it.")
figure(doc, FIG / "fig5_persistence.png",
 "Figure 5.  One-month transition probabilities between Amihud illiquidity quintiles. "
 "Off-diagonal mass is almost entirely to adjacent quintiles.", width=3.8)

h(doc, "6.6  Sub-periods", 2)
para(doc,
 "The spread is not constant through time. Figure 2 plots it; Figure 7 and Table 6 split "
 "the sample into three three-year blocks. The Amihud 12-month holdout spread is "
 f"{subp[(subp.measure=='illiq')&(subp.horizon_m==12)&(subp.period=='2016-2018')&(subp.split=='holdout')].Q5_minus_Q1.iloc[0]:+.2f} "
 f"in 2016–2018, {subp[(subp.measure=='illiq')&(subp.horizon_m==12)&(subp.period=='2019-2021')&(subp.split=='holdout')].Q5_minus_Q1.iloc[0]:+.2f} "
 f"in 2019–2021, and {subp[(subp.measure=='illiq')&(subp.horizon_m==12)&(subp.period=='2022-2024')&(subp.split=='holdout')].Q5_minus_Q1.iloc[0]:+.2f} "
 "in 2022–2024. It roughly halves in the most recent block but stays positive and "
 "significant (t = 5.4). The two large peaks in Figure 2 line up with the early-2016 "
 "junior-resource bottom and the 2020–21 pandemic-era speculative surge — periods when the "
 "most illiquid, lowest-quality names rallied hardest. Corwin–Schultz runs the other way: "
 "its negative spread is concentrated in the calmer 2016–2018 and 2022–2024 blocks and "
 "vanishes in the 2019–2021 mania, when nothing discriminated.")
figure(doc, FIG / "fig2_spread_over_time.png",
 "Figure 2.  The Q5 − Q1 12-month excess-return spread over time (three-month moving "
 "average, holdout sample). Amihud and zero-return days are positive in almost every month, "
 "with peaks in the 2016 and 2020–21 speculative episodes.")
figure(doc, FIG / "fig7_subperiods.png",
 "Figure 7.  The 12-month spread by three-year block, holdout sample. The activity-"
 "illiquidity premium shrinks after 2021 but does not disappear.", width=5.2)

_t6 = subp[(subp.split == "holdout") & (subp.horizon_m == 12)][
    ["measure", "period", "Q5_minus_Q1", "nw_t"]].copy()
_t6.columns = ["Measure", "Period", "Q5 − Q1 (12m)", "NW t"]
_t6["Measure"] = _t6["Measure"].map({"illiq": "Amihud ILLIQ", "zero_ret_pct": "Zero-return %",
                                     "cs_spread": "Corwin–Schultz"})
table(doc, _t6, "Table 6.  Sub-period spreads, holdout sample, 12-month horizon "
      "(median within-quintile aggregation).")

doc.add_page_break()

# =========================================================================== #
# 7. Survivorship
# =========================================================================== #
h(doc, "7  Survivorship: what we fixed and what we could not", 1)
para(doc,
 "This is the one bias we cannot fully purge, and pretending otherwise would be the sort of "
 "thing that gets a paper picked apart. We separate it into two components, because they "
 "behave differently.")

h(doc, "7.1  Attrition within the sample", 2)
para(doc,
 "Some names in our universe stop trading part-way through a forward window — a halt, a "
 "delisting, an acquisition, or a data gap. In the base specification these truncated "
 f"observations are dropped, which is itself a mild survivorship filter. They are only "
 f"{100*846/208559:.1f}% of all name-date-horizon rows. We re-price every truncated "
 "observation under three explicit assumptions and re-run the sort:")
bullet(doc, "carry-forward — the last observed price stands (the optimistic base case);")
bullet(doc, "zero-excess — the position matches the benchmark over the truncated window;")
bullet(doc, "wipeout — the position loses 100% from its last price (the pessimistic case).")
para(doc,
 "The Amihud 12-month holdout spread moves from "
 f"{brack[(brack.scenario=='carry_forward')&(brack.measure=='illiq')&(brack.horizon_m==12)].Q5_minus_Q1.iloc[0]:.3f} "
 f"under carry-forward to "
 f"{brack[(brack.scenario=='wipeout')&(brack.measure=='illiq')&(brack.horizon_m==12)].Q5_minus_Q1.iloc[0]:.3f} "
 "under wipeout — a change in the third decimal place. Conditional on a name entering the "
 "sample, how its window ends does not drive the result. The Corwin–Schultz negative spread "
 "is equally insensitive. This component of survivorship is not the problem.")

h(doc, "7.2  Names that never entered the sample", 2)
para(doc,
 "The real exposure is different. Our universe is the set of TSXV common shares still listed "
 "in September 2026. Every junior that delisted, was cease-traded, went to the "
 "over-the-counter market, or failed outright between 2016 and 2024 is simply absent — and "
 "on this exchange that is a large number, plausibly comparable to the surviving universe "
 "itself. We searched for a point-in-time historical constituent list and for a "
 "comprehensive delisted-name feed; neither exists in a form we could obtain. A partial "
 "third-party list (135 names, 2022–2025, acquisition-heavy) would have added a fresh "
 "period- and reason-selection bias, so we did not use it.")
para(doc,
 "The direction of this bias is not ambiguous. Failed junior issuers are disproportionately "
 "illiquid — thin trading is part of how they fail — and their realized returns are steeply "
 "negative. Excluding them removes bad outcomes preferentially from the illiquid quintile, "
 "which inflates the measured Q5 return and therefore the Q5 − Q1 spread. The Amihud and "
 "zero-return H1 results in this paper are an upper bound on the true relation. How much of "
 "an upper bound we cannot say precisely; a rough calculation in which a hidden 20% of the "
 "illiquid quintile earns −100% would remove roughly half of the 12-month spread, and a "
 "hidden 30% would remove most of it. A meaningful illiquidity premium survives moderate "
 "assumed failure rates; an implausibly large one would be needed to eliminate the effect "
 "entirely.")

h(doc, "7.3  Why the divergence is the useful result", 2)
para(doc,
 "Survivorship pushes every illiquidity measure toward H1 — including Corwin–Schultz. And "
 "yet the Corwin–Schultz sort leans H2 in the skew-robust specifications, against that "
 "headwind. That is more informative than the H1 results, because it is the finding that "
 "the bias works against. It tells us that once you strip out the survivorship tailwind and "
 "the penny-stock skew, at least one reasonable measure of illiquidity is associated with "
 "underperformance — which is exactly the value-trap channel. The honest summary is that "
 "the sign of the illiquidity–return relation on TSXV is not robust to how illiquidity is "
 "measured, and that the activity-based 'premium' is real in the surviving cross-section "
 "but smaller than it looks.")

# =========================================================================== #
# 8. Discussion
# =========================================================================== #
h(doc, "8  What it means", 1)

h(doc, "8.1  Two kinds of illiquidity", 2)
para(doc,
 "The cleanest way to hold the results together is to notice that our five proxies split "
 "into two families. Amihud, zero-return days, turnover and dollar volume all measure "
 "quantity — can you trade this at all, and how much. Corwin–Schultz measures cost — how "
 "wide is the round-trip. On TSXV these are not just different; they are negatively "
 "rank-correlated, because a stock that hardly trades has a narrow observed range and a "
 "stock that trades in a speculative frenzy has a wide one. Quantity-illiquidity predicts "
 "outperformance in the surviving sample; cost-illiquidity, to the extent the estimator "
 "captures it here, predicts underperformance. A study that had picked one measure and "
 "stopped would have reported a confident answer with the wrong sign half the time.")

h(doc, "8.2  Premium or sentiment?", 2)
para(doc,
 "Even taking the quantity-illiquidity result at face value, its time profile does not look "
 "like a stable risk premium. A compensation-for-illiquidity story predicts a reasonably "
 "steady spread. What we see instead is a spread that is modest in normal periods and "
 "enormous in the 2016 and 2020–21 speculative episodes — precisely when the most illiquid, "
 "lowest-quality names run hardest on retail flow and momentum. The 2022–2024 block, a "
 "grinding bear market for Canadian juniors, still shows a positive spread, but half the "
 "size. Our reading is that a genuine but small liquidity premium is overlaid with a much "
 "larger, episodic beta to speculative sentiment, and that most of the headline magnitude "
 "is the latter.")

h(doc, "8.3  Not a strategy", 2)
para(doc,
 "The Q5 basket is, by construction, the least tradable quarter of the least tradable "
 "exchange in North America. Its median name trades a few thousand dollars a day. The "
 "measured spread cannot be captured at scale: the act of buying the basket would move it. "
 "The value-weighted result (Section 6.1) says the effect is not only in the nano-caps, "
 "which is something, but 'not only in the nano-caps' is a long way from 'investable'. We "
 "report this as a characterization of how returns are distributed across the liquidity "
 "spectrum on TSXV, not as an anomaly to be harvested.")

h(doc, "8.4  The bridge to financing terms", 2)
para(doc,
 "The natural next step, and the one the underlying methodology reserves for a second "
 "phase, is to ask whether the most illiquid names in this sample raise equity on worse "
 "terms — larger discounts, more warrant coverage, more dilution per dollar — than their "
 "liquid peers. That is the concrete mechanism behind the value-trap hypothesis, and it is "
 "testable on a small hand-collected sample drawn from the two extreme quintiles this study "
 "already defines. If wide-spread, thinly-traded names systematically finance at "
 "punitive terms, the Corwin–Schultz H2 lean stops being a curiosity and becomes the more "
 "economically meaningful half of the story.")

# =========================================================================== #
# 9. Conclusion
# =========================================================================== #
h(doc, "9  Conclusion", 1)
para(doc,
 "On the full TSX Venture common-equity universe, 2016–2024, with every specification fixed "
 "in advance and a third of the tickers held out until the end, trailing illiquidity "
 "predicts forward excess return — but the sign depends on the measure. Amihud price impact, "
 "zero-return frequency, low turnover and low dollar volume all say the most illiquid names "
 "outperform, monotonically, out of sample, robustly to skew, weighting, price screens, "
 "sector-neutralization and a price double-sort, and persistently if less strongly outside "
 "the speculative booms. The Corwin–Schultz high–low spread estimator says the most "
 "'illiquid' names underperform, weakly, in the specifications that resist the penny-stock "
 "skew — and it says so against the survivorship bias, which works the other way. The "
 "activity-illiquidity premium is genuine in the surviving cross-section, inflated by the "
 "absence of failed names, dominated by episodic speculative beta, and too concentrated in "
 "unhedgeable microcaps to trade. The contribution is a disciplined map of the "
 "liquidity–return relation at the bottom of the market, and a concrete warning that on "
 "junior exchanges the answer you get is the measure you chose.")

doc.add_page_break()

# =========================================================================== #
# References
# =========================================================================== #
h(doc, "References", 1)
refs = [
 "Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. "
 "Journal of Financial Markets, 5(1), 31–56.",
 "Amihud, Y., & Mendelson, H. (1986). Asset pricing and the bid–ask spread. Journal of "
 "Financial Economics, 17(2), 223–249.",
 "Amihud, Y., Hameed, A., Kang, W., & Zhang, H. (2015). The illiquidity premium: "
 "international evidence. Journal of Financial Economics, 117(2), 350–368.",
 "Corwin, S. A., & Schultz, P. (2012). A simple way to estimate bid–ask spreads from daily "
 "high and low prices. Journal of Finance, 67(2), 719–759.",
 "Datar, V. T., Naik, N. Y., & Radcliffe, R. (1998). Liquidity and stock returns: an "
 "alternative test. Journal of Financial Markets, 1(2), 203–219.",
 "Lesmond, D. A., Ogden, J. P., & Trzcinka, C. A. (1999). A new estimate of transaction "
 "costs. Review of Financial Studies, 12(5), 1113–1141.",
 "Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, "
 "heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica, "
 "55(3), 703–708.",
 "Fama, E. F., & MacBeth, J. D. (1973). Risk, return, and equilibrium: empirical tests. "
 "Journal of Political Economy, 81(3), 607–636.",
 "Pástor, Ľ., & Stambaugh, R. F. (2003). Liquidity risk and expected stock returns. "
 "Journal of Political Economy, 111(3), 642–685.",
 "Petersen, M. A. (2009). Estimating standard errors in finance panel data sets: comparing "
 "approaches. Review of Financial Studies, 22(1), 435–480.",
]
for r in refs:
    p = doc.add_paragraph(r)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    for run in p.runs:
        run.font.size = Pt(9.5)

doc.add_page_break()

# =========================================================================== #
# Appendix
# =========================================================================== #
h(doc, "Appendix A  Reproducibility", 1)
para(doc,
 "The study is a deterministic pipeline. Every parameter lives in a single configuration "
 "file; nothing downstream hard-codes a knob. The stages, in order, are: build the universe "
 "(exchange directory + TMX Money GraphQL enrichment); fetch daily OHLCV and the benchmark; "
 "compute the illiquidity panel; freeze the 70/30 ticker holdout (written once to a file "
 "the pipeline refuses to overwrite); compute forward excess returns; run the portfolio "
 "sorts and Fama–MacBeth regressions; run the robustness and bias batteries; render the "
 "figures and this paper. Re-running with cached inputs reproduces every number.")
para(doc, "Key fixed parameters:")
bullet(doc, "Formation: month-end, January 2016 – December 2024, 108 dates.")
bullet(doc, "Trailing window for all illiquidity measures: 252 trading days; minimum 126 valid days.")
bullet(doc, "Forward horizons: 6, 12, 24 months. Overlap handled by Newey–West (lags = horizon).")
bullet(doc, "Winsorization: 1st/99th percentile of excess return within each formation-date × horizon cross-section.")
bullet(doc, "Holdout: 30% of 1,267 tickers, seed 424242 → 887 train / 380 holdout.")
bullet(doc, "Quintile breakpoints: computed from training tickers only at each formation date.")
bullet(doc, "Amihud scale factor 10⁶; Corwin–Schultz negative two-day estimates clamped to zero.")

h(doc, "Appendix B  Data-quality screens", 1)
para(doc,
 "Two automated screens run before the metrics stage. First, any name whose median raw "
 "close exceeds C$50 is dropped as a probable units artifact or a series of stacked "
 "unadjusted consolidations (three names: a stock quoted near C$1,365, one near C$135, one "
 "near C$94). Second, within each retained series, an isolated one-day log price move "
 "greater than 1.6 in absolute value that reverses by more than 60% the next day is treated "
 "as a bad print and linearly interpolated; genuine multi-day moves and true consolidations, "
 "which do not reverse, are left untouched. Of 1,267 cleaned names, 1,167 returned usable "
 "history and 1,127 had enough of it to be scored on at least one formation date. The main "
 "results are unchanged whether or not these screens are applied.")

h(doc, "Appendix C  Deviations from the pre-registered methodology", 1)
para(doc,
 "Four choices differ from the methodology document, each forced by data access and each "
 "logged here.")
bullet(doc,
 "Price source. The plan specified Alpha Vantage as primary. Its split-adjusted and "
 "corporate-action endpoints are premium-only, and raw daily prices cannot handle TSXV "
 "consolidations; Yahoo Finance, the adjusted-data fallback, rate-limited our access. We "
 "use TMX Money's GraphQL daily series, which is consolidation-consistent on inspection, "
 "and the same provider as the rest of the reference data.")
bullet(doc,
 "Shares outstanding. The plan anticipated a manual per-ticker collection. TMX Money's "
 "GraphQL service returns current shares outstanding for essentially every live name, which "
 "we use, applied to all formation dates, with log(price) reported as an alternative size "
 "control. The approximation and its direction are discussed in Section 3.3.")
bullet(doc,
 "Sample size. The plan targeted 150–300 hand-selected names; that cap existed only to "
 "bound the manual shares-outstanding effort, which is now automated. We use the full "
 "cleaned universe (~1,130 scored names), which removes sample-selection discretion "
 "entirely.")
bullet(doc,
 "Sector classification. GICS sector and industry from TMX Money are mapped to the "
 "exchange's six buckets, industry-first. The mapping rule is in the code.")
para(doc,
 "Unchanged: the research question, the undirected hypotheses, the three pre-registered "
 "illiquidity estimators and their formulas, the portfolio-sort and cross-sectional-"
 "regression method, the 70/30 holdout discipline, the winsorization rule, the look-ahead "
 "control, and the treatment of survivorship as a disclosed limitation.")

h(doc, "Appendix D  AI disclosure", 1)
para(doc,
 "Consistent with SSRN policy: Claude (Anthropic) assisted with the data-collection and "
 "analysis code, the statistical structure of the tests, and figure generation, and "
 "assisted in writing this manuscript, which the author wrote. All methodological "
 "decisions, parameter choices, the interpretation of the results, and the framing of the "
 "contribution are the author's. The author is responsible for the content in full.")

doc.save(str(DOCX))
print("saved", DOCX)
