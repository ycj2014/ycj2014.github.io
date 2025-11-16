#!/usr/bin/env python3
"""
Script to randomize description positions in comparison CSV files.
For each row, randomly swap description_a and description_b,
and record the position of the original description_b as 'model_position' (A or B).

Usage:
    python randomize_descriptions.py <csv_file_path>
"""

import csv
import random
import sys
import glob
from pathlib import Path


def randomize_csv_file(input_path, seed=None):
    """
    Randomize description positions and add model_position column.
    
    model_position indicates where the original description_b ended up:
    - 'A' means description_b was moved to description_a position (swapped)
    - 'B' means description_b stayed in description_b position (no swap)
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return None
    
    # Set random seed for reproducibility if provided
    if seed is not None:
        random.seed(seed)
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)
    
    # Check if required columns exist
    if 'description_a' not in fieldnames or 'description_b' not in fieldnames:
        print(f"❌ 'description_a' and 'description_b' columns not found in {input_path}")
        return None
    
    # Add model_position column if it doesn't exist
    if 'model_position' not in fieldnames:
        fieldnames.append('model_position')
    
    # Process each row
    swap_count = 0
    for row in rows:
        desc_a = row.get('description_a', '')
        desc_b = row.get('description_b', '')
        
        # Randomly decide whether to swap (50/50 chance)
        should_swap = random.choice([True, False])
        
        if should_swap:
            # Swap the descriptions
            row['description_a'] = desc_b
            row['description_b'] = desc_a
            row['model_position'] = 'A'  # Original desc_b is now in position A
            swap_count += 1
        else:
            # Keep original order
            row['model_position'] = 'B'  # Original desc_b stayed in position B
    
    # Write back to file
    with open(input_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Randomized {input_path}")
    print(f"   Total rows: {len(rows)}")
    print(f"   Swapped: {swap_count} ({swap_count/len(rows)*100:.1f}%)")
    print(f"   Not swapped: {len(rows)-swap_count} ({(len(rows)-swap_count)/len(rows)*100:.1f}%)")
    print(f"   Added 'model_position' column (A = desc_b in position A, B = desc_b in position B)")
    
    return input_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python randomize_descriptions.py <csv_file_path> [--seed SEED]")
        print("\nExamples:")
        print("  python randomize_descriptions.py comparison_input.csv")
        print("  python randomize_descriptions.py path/to/comparison_input.csv")
        print("  python randomize_descriptions.py comparison_*/comparison_input.csv")
        print("  python randomize_descriptions.py comparison_input.csv --seed 42")
        print("\nOptions:")
        print("  --seed SEED    Set random seed for reproducibility")
        sys.exit(1)
    
    # Parse arguments
    seed = None
    file_patterns = []
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--seed' and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])
            i += 2
        else:
            file_patterns.append(sys.argv[i])
            i += 1
    
    if not file_patterns:
        print("❌ No file path provided")
        sys.exit(1)
    
    # Handle glob patterns
    file_paths = []
    for pattern in file_patterns:
        matches = glob.glob(pattern)
        if matches:
            file_paths.extend(matches)
        else:
            # Not a glob pattern, treat as literal path
            file_paths.append(pattern)
    
    if not file_paths:
        print("❌ No files found matching the pattern(s)")
        sys.exit(1)
    
    if seed is not None:
        print(f"Using random seed: {seed}\n")
    
    print(f"Found {len(file_paths)} file(s) to process\n")
    
    success_count = 0
    for csv_path in file_paths:
        print(f"{'='*60}")
        result = randomize_csv_file(csv_path, seed=seed)
        if result is not None:
            success_count += 1
        print()
    
    print(f"{'='*60}")
    print(f"✅ Successfully processed {success_count}/{len(file_paths)} file(s)")


if __name__ == "__main__":
    main()

