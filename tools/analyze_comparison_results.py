#!/usr/bin/env python3
"""
Analyze comparison test results.

Given:
  1) A responses CSV exported from Google Sheets / Apps Script with columns:
       ts_server, prolific_pid, study_id, session_id, index, total,
       prev_image, current_image, description_a, description_b,
       model_position, choice, confidence, comments, ua

  2) One or more comparison input CSVs used by the web UIs, each with columns:
       prev_image, current_image, description_a, description_b, model_position

and knowing which model produced the generated description in each dataset
(`model_position` tells you whether the model's description is A or B),
this script:

  * Matches each response row to the corresponding comparison input row
    using (current_image, description_a, description_b)
  * Determines which model (e.g., 'qwen' or 'gpt') authored the chosen
    description
  * Aggregates win / lose / tie counts per model:
       - win  : participant chose the model's description
       - lose : participant chose the other description
       - tie  : participant chose 'Neither' or choice/model_position missing

Usage (with current repo structure):

  python tools/analyze_comparison_results.py

Adjust RESPONSE_PATH and DATASETS if your file names differ.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# ---------- Configuration ----------

# Path to the exported responses CSV (from Google Sheets)
RESPONSE_PATH = Path("Robotic Guide Dog Data - comparison_responses.csv")


@dataclass
class DatasetConfig:
    """Configuration for a single comparison dataset."""

    key: str          # identifier used in stats and debug (e.g., 'qwen_p1')
    model: str        # model name ('qwen', 'gpt', etc.)
    path: Path        # path to comparison_input.csv


# List of datasets to analyze; adjust as needed
DATASETS: List[DatasetConfig] = [
    DatasetConfig("qwen_p1", "qwen", Path("comparison_1_qwen_p1/comparison_input.csv")),
    DatasetConfig("qwen_p2", "qwen", Path("comparison_1_qwen_p2/comparison_input.csv")),
    DatasetConfig("gpt_p1", "gpt", Path("comparison_1_5omini_p1/comparison_input.csv")),
    DatasetConfig("gpt_p2", "gpt", Path("comparison_1_5omini_p2/comparison_input.csv")),
]


def load_comparison_lookup(
    datasets: List[DatasetConfig],
) -> Dict[Tuple[str, str, str], List[Tuple[str, str]]]:
    """
    Build a lookup:
      (current_image, description_a, description_b) -> list of (dataset_key, model_position)
    """
    lookup: Dict[Tuple[str, str, str], List[Tuple[str, str]]] = {}

    for ds in datasets:
        if not ds.path.exists():
            print(f"WARNING: comparison file missing for dataset '{ds.key}': {ds.path}")
            continue

        with ds.path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cur = (row.get("current_image") or "").strip()
                da = (row.get("description_a") or "").strip()
                db = (row.get("description_b") or "").strip()
                if not cur or not da or not db:
                    continue
                key = (cur, da, db)
                mp = (row.get("model_position") or "").strip()
                lookup.setdefault(key, []).append((ds.key, mp))

    total_rows = sum(len(v) for v in lookup.values())
    print(
        f"Loaded {total_rows} comparison rows into lookup "
        f"(may include duplicates across datasets)."
    )
    return lookup


def analyze_results() -> None:
    # Load comparison definitions
    lookup = load_comparison_lookup(DATASETS)

    # Load responses
    if not RESPONSE_PATH.exists():
        raise SystemExit(f"Response file not found: {RESPONSE_PATH}")

    with RESPONSE_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        responses = list(reader)

    print(f"Total responses: {len(responses)}")

    # Initialize stats per model
    stats: Dict[str, Dict[str, int]] = {}
    for ds in DATASETS:
        stats.setdefault(ds.model, {"win": 0, "lose": 0, "tie": 0, "rows": 0})

    unmatched: List[Tuple[str, str, str]] = []
    ambiguous: List[Tuple[Tuple[str, str, str], List[Tuple[str, str]]]] = []

    for r in responses:
        cur = (r.get("current_image") or "").strip()
        da = (r.get("description_a") or "").strip()
        db = (r.get("description_b") or "").strip()
        key = (cur, da, db)

        matches = lookup.get(key)
        if not matches:
            # No matching comparison row found
            unmatched.append(key)
            continue

        if len(matches) > 1:
            # Same pair appears in multiple datasets; record and take first for now
            ambiguous.append((key, matches))

        ds_key, model_pos = matches[0]
        # Map dataset key to model
        model = next((d.model for d in DATASETS if d.key == ds_key), None)
        if model is None:
            continue

        stats[model]["rows"] += 1

        choice = (r.get("choice") or "").strip()
        if choice == "Neither":
            stats[model]["tie"] += 1
        elif choice in ("A", "B") and model_pos in ("A", "B"):
            if choice == model_pos:
                stats[model]["win"] += 1
            else:
                stats[model]["lose"] += 1
        else:
            # Missing or malformed choice/model_position -> treat as tie
            stats[model]["tie"] += 1

    # Print summary
    print("\nModel stats (wins vs the other description, based on human choice):")
    for model, s in stats.items():
        rows = s["rows"] or 1
        print(f"\n{model.upper()}:")
        print(f"  rows:   {s['rows']}")
        print(f"  win:    {s['win']} ({s['win']/rows*100:.1f}%)")
        print(f"  lose:   {s['lose']} ({s['lose']/rows*100:.1f}%)")
        print(f"  tie:    {s['tie']} ({s['tie']/rows*100:.1f}%)")

    if unmatched:
        print(f"\nUnmatched response rows: {len(unmatched)}")
        # Optional: write unmatched keys to a file for inspection
        out = RESPONSE_PATH.with_name(RESPONSE_PATH.stem + "_unmatched_keys.csv")
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["current_image", "description_a", "description_b"])
            for cur, da, db in unmatched:
                w.writerow([cur, da, db])
        print(f"  -> Details written to {out}")

    if ambiguous:
        print(f"Ambiguous matches (same pair in multiple datasets): {len(ambiguous)}")


def main() -> None:
    analyze_results()


if __name__ == "__main__":
    main()


