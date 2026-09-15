"""Shared config, paths, logging, and the GICS -> TSXV sector map.

Every script imports from here so there is exactly one definition of each knob.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


CFG = load_config()

# --- canonical paths --------------------------------------------------------
DATA        = ROOT / "data"
RAW         = DATA / "raw"           # untouched per-ticker source pulls (parquet)
ADJUSTED    = DATA / "adjusted"      # split-adjusted OHLCV panel + adjustment log
BENCHMARK   = DATA / "benchmark"
UNIVERSE    = DATA / "universe"
OUTPUTS     = ROOT / "outputs"
LOGS        = ROOT / "logs"
for _p in (RAW, ADJUSTED, BENCHMARK, UNIVERSE, OUTPUTS, LOGS):
    _p.mkdir(parents=True, exist_ok=True)

UNIVERSE_CSV = UNIVERSE / "universe.csv"          # the cleaned, classified sample
UNIVERSE_RAW_CSV = UNIVERSE / "tsxv_directory_raw.csv"  # every directory row + GraphQL fields


def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
                                     datefmt="%H:%M:%S"))
    log.addHandler(h)
    fh = logging.FileHandler(LOGS / f"{name}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
    log.addHandler(fh)
    return log


# --- sector mapping -------------------------------------------------------------
# TMX Money GraphQL returns GICS-style sector + a finer "industry" string.
# The study needs TSXV's own 6 buckets. Mapping is industry-first, sector-second.
TSXV_SECTORS = [
    "Mining", "Oil & Gas", "Technology", "Life Sciences",
    "CleanTech", "Diversified Industries",
]

_INDUSTRY_KEYWORDS = [
    ("Mining",          ["mining", "metals", "minerals", "gold", "silver", "copper",
                          "precious metals", "diversified metals"]),
    ("Oil & Gas",       ["oil & gas", "oil and gas", "oil & gas exploration",
                          "integrated oil", "oil & gas storage", "coal"]),
    ("CleanTech",       ["renewable", "solar", "wind", "clean", "hydrogen",
                          "fuel cell", "battery", "energy storage",
                          "other energy sources"]),
    ("Life Sciences",   ["biotech", "pharmaceutical", "life sciences", "health care",
                          "healthcare", "medical", "drug", "therapeutics", "diagnostics"]),
    ("Technology",      ["software", "it services", "hardware", "semiconductor",
                          "internet", "technology", "electronic", "communications equipment"]),
]

_SECTOR_FALLBACK = {
    "materials":              "Mining",     # TSXV Materials is ~all mining; refined by industry above
    "energy":                 "Oil & Gas",
    "health care":            "Life Sciences",
    "healthcare":             "Life Sciences",
    "information technology": "Technology",
    "technology":             "Technology",
    "communication services": "Technology",
}


def map_to_tsxv_sector(gics_sector: str | None, industry: str | None) -> str:
    """Best-effort classification into one of the 6 TSXV buckets.

    Everything that is not clearly Mining / Oil&Gas / Tech / Life-Sci / CleanTech
    lands in Diversified Industries, matching how TMX itself treats the long tail.
    """
    ind = (industry or "").strip().lower()
    sec = (gics_sector or "").strip().lower()

    for bucket, kws in _INDUSTRY_KEYWORDS:
        if any(kw in ind for kw in kws):
            return bucket

    # Chemicals / construction materials sit in GICS "Materials" but are NOT mining.
    if sec == "materials" and ind and ("chemical" in ind or "construction" in ind
                                       or "paper" in ind or "packaging" in ind
                                       or "forest" in ind):
        return "Diversified Industries"

    if sec in _SECTOR_FALLBACK:
        return _SECTOR_FALLBACK[sec]

    return "Diversified Industries"


def yahoo_symbol(tsxv_ticker: str) -> str:
    """`ABC` -> `ABC.V`; `ABC.A` (dual class) -> `ABC-A.V`."""
    t = tsxv_ticker.strip().upper()
    return t.replace(".", "-") + ".V"
