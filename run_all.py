"""Orchestrator. Runs the whole pipeline in order, skipping stages whose output
already exists (unless --force). The holdout split is frozen at stage 3 and is
never touched again.

    python run_all.py                 # full run, resuming from cache
    python run_all.py --from metrics   # re-run metrics onward
    python run_all.py --force          # ignore all caches (does NOT reroll holdout)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STAGES = ["build_universe", "fetch", "holdout", "metrics", "forward_returns",
          "analysis", "robustness", "extended", "report", "paper_figures"]


def run(stage: str, force: bool) -> None:
    print(f"\n{'=' * 70}\n  {stage}\n{'=' * 70}", flush=True)
    cmd = [PY, str(ROOT / "src" / f"{stage}.py")]
    if force and stage == "fetch":
        cmd.append("--force")
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=STAGES, default=STAGES[0])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    for stage in STAGES[STAGES.index(args.start):]:
        run(stage, args.force)
    # the paper itself (needs its own build step; harmless if figures missing)
    try:
        subprocess.run([PY, str(ROOT / "paper" / "build_paper.py")], check=True,
                       cwd=ROOT / "paper")
    except Exception as e:  # noqa: BLE001
        print(f"(paper build skipped: {e})")
    print("\nDONE. See outputs/REPORT.md, outputs/FINDINGS.md, paper/TSXV_Liquidity_Puzzle.docx")


if __name__ == "__main__":
    main()
