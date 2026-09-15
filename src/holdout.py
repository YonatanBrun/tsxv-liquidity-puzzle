"""Step 3 — the 70/30 ticker holdout split. Written ONCE, then frozen.

This runs before any metric is looked at. It records which tickers are TRAIN
and which are HOLDOUT, plus the config hash and universe hash it was built
against. If the lock file already exists it is NOT regenerated — the whole
point is that the split cannot be re-rolled after seeing a result.

  data/holdout.json   {seed, fraction, created_utc, universe_sha, train:[...], holdout:[...]}
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from common import CFG, ROOT, UNIVERSE_CSV, get_logger

log = get_logger("holdout")
LOCK = ROOT / CFG["holdout_lock_file"]


def _sha(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def load_split() -> dict:
    """Return the frozen split, creating it on first call only."""
    if LOCK.exists():
        split = json.loads(LOCK.read_text())
        cur = _sha(UNIVERSE_CSV)
        if split.get("universe_sha") != cur:
            log.warning("universe.csv changed since holdout was frozen "
                        "(%s -> %s). The frozen split is being kept; new names "
                        "are NEITHER train nor holdout until you delete %s "
                        "deliberately.", split.get("universe_sha"), cur, LOCK.name)
        return split

    tickers = sorted(pd.read_csv(UNIVERSE_CSV)["ticker"].astype(str).tolist())
    rng = np.random.default_rng(int(CFG["holdout_seed"]))
    idx = rng.permutation(len(tickers))
    n_hold = int(round(len(tickers) * float(CFG["holdout_fraction"])))
    hold = sorted(tickers[i] for i in idx[:n_hold])
    train = sorted(tickers[i] for i in idx[n_hold:])

    split = {
        "seed": int(CFG["holdout_seed"]),
        "fraction": float(CFG["holdout_fraction"]),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universe_sha": _sha(UNIVERSE_CSV),
        "n_total": len(tickers),
        "n_train": len(train),
        "n_holdout": len(hold),
        "train": train,
        "holdout": hold,
    }
    LOCK.write_text(json.dumps(split, indent=2))
    log.info("FROZE holdout split -> %s  (train=%d, holdout=%d)",
             LOCK, len(train), len(hold))
    return split


def tag_frame(df: pd.DataFrame, ticker_col: str = "ticker") -> pd.DataFrame:
    split = load_split()
    membership = {t: "train" for t in split["train"]}
    membership.update({t: "holdout" for t in split["holdout"]})
    out = df.copy()
    out["split"] = out[ticker_col].astype(str).map(membership)
    return out


if __name__ == "__main__":
    s = load_split()
    print(json.dumps({k: v for k, v in s.items() if k not in ("train", "holdout")},
                     indent=2))
