#!/usr/bin/env python3
"""
Prepare comparison CSV files for the evaluation UI.

Given an input CSV with columns:
    image_url, original_description, generated_description

This script will:
  1. Remove exact duplicate rows (same image_url + original + generated).
  2. Compute a prev_image URL by decrementing the frame number in image_url.
  3. Randomize whether the model (generated) description is shown as A or B.
  4. Record the model's position in a new column model_position ("A" or "B").
  5. Overwrite the input CSV with columns:
        prev_image,current_image,description_a,description_b,model_position

Usage (in-place):
    python tools/prepare_comparison_csv.py path/to/input.csv
    python tools/prepare_comparison_csv.py path/to/input.csv --seed 42
"""

import csv
import re
import sys
import glob
import random
from pathlib import Path


def get_previous_frame_url(url: str, offset: int = 1) -> str:
    """
    Extract frame number from URL and construct previous frame URL.
    Example: .../000512.jpg -> .../000511.jpg
    """
    if not url:
        return ""

    parts = url.split("/")
    filename = parts[-1]

    # Expect something like 000512.jpg
    match = re.match(r"^(\d+)\.(\w+)$", filename)
    if not match:
        return ""

    frame_num = int(match.group(1))
    ext = match.group(2)
    padding = len(match.group(1))

    prev_frame = frame_num - offset
    if prev_frame < 0:
        return ""

    prev_name = f"{prev_frame:0{padding}d}.{ext}"
    parts[-1] = prev_name
    return "/".join(parts)


def prepare_file(input_path: str, seed=None):
    """
    Transform one source CSV into a comparison-ready CSV.
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return None

    # Optional deterministic randomization
    if seed is not None:
        random.seed(seed)

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    required = {"image_url", "original_description", "generated_description"}
    missing = required.difference(fieldnames)
    if missing:
        print(f"❌ {input_path} is missing required columns: {', '.join(sorted(missing))}")
        return None

    # Remove exact duplicates (same trio)
    seen = set()
    unique_rows = []
    for row in rows:
        key = (
            (row.get("image_url") or "").strip(),
            (row.get("original_description") or "").strip(),
            (row.get("generated_description") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    if not unique_rows:
        print(f"⚠️  No usable rows in {input_path}")
        return None

    # For each image, keep only entries with unique original_description
    filtered_rows = []
    seen_orig_for_img = {}
    for row in unique_rows:
        img = (row.get("image_url") or "").strip()
        orig = (row.get("original_description") or "").strip()
        if not img or not orig:
            # Skip incomplete rows
            continue
        if img not in seen_orig_for_img:
            seen_orig_for_img[img] = set()
        if orig in seen_orig_for_img[img]:
            # Duplicate original description for this image; drop
            continue
        seen_orig_for_img[img].add(orig)
        filtered_rows.append(row)

    if not filtered_rows:
        print(f"⚠️  No rows remained after enforcing unique original_description per image in {input_path}")
        return None

    prepared_rows: list[dict[str, str]] = []

    for row in filtered_rows:
        current = (row.get("image_url") or "").strip()
        orig_desc = (row.get("original_description") or "").strip()
        model_desc = (row.get("generated_description") or "").strip()

        if not current or not orig_desc or not model_desc:
            # Skip incomplete rows
            continue

        prev = get_previous_frame_url(current)

        # Randomize whether the model description is A or B
        if random.choice([True, False]):
            # Model shown as A
            description_a = model_desc
            description_b = orig_desc
            model_position = "A"
        else:
            # Model shown as B
            description_a = orig_desc
            description_b = model_desc
            model_position = "B"

        prepared_rows.append(
            {
                "prev_image": prev,
                "current_image": current,
                "description_a": description_a,
                "description_b": description_b,
                "model_position": model_position,
            }
        )

    if not prepared_rows:
        print(f"⚠️  No rows remained after initial filtering in {input_path}")
        return None

    # Overwrite the original file in place with the prepared format
    output_file = input_file

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "prev_image",
                "current_image",
                "description_a",
                "description_b",
                "model_position",
            ],
        )
        writer.writeheader()
        writer.writerows(prepared_rows)

    print(f"✅ Prepared {input_path} (in place)")
    print(f"   Input rows: {len(rows)}")
    print(f"   After removing exact duplicates: {len(unique_rows)}")
    print(f"   After enforcing unique description_a per image: {len(prepared_rows)}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/prepare_comparison_csv.py <csv_path_or_glob> [--seed SEED]")
        print("\nExamples:")
        print("  python tools/prepare_comparison_csv.py comparison_1_qwen_p1/comparison_input.csv")
        print("  python tools/prepare_comparison_csv.py 'comparison_1_*/comparison_input.csv' --seed 123")
        sys.exit(1)

    seed: int | None = None
    patterns: list[str] = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])
            i += 2
        else:
            patterns.append(arg)
            i += 1

    if not patterns:
        print("❌ No CSV path provided")
        sys.exit(1)

    # Expand globs
    paths: list[str] = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            paths.extend(matches)
        else:
            # treat as literal
            paths.append(pattern)

    if not paths:
        print("❌ No files matched the given pattern(s)")
        sys.exit(1)

    if seed is not None:
        print(f"Using random seed: {seed}\n")

    print(f"Found {len(paths)} file(s) to process\n")

    ok = 0
    for p in paths:
        print("=" * 60)
        if prepare_file(p, seed=seed) is not None:
            ok += 1
        print()

    print("=" * 60)
    print(f"✅ Successfully prepared {ok}/{len(paths)} file(s)")


if __name__ == "__main__":
    main()


