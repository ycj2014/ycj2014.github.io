#!/usr/bin/env python3
"""
Script to populate prev_image column in comparison CSV files
by decrementing the frame number from current_image URLs

Usage:
    python generate_prev_images.py <csv_file_path>
    python generate_prev_images.py comparison_input.csv
    python generate_prev_images.py path/to/comparison_input.csv
"""

import csv
import re
import sys
import glob
from pathlib import Path


def get_previous_frame_url(url, offset=1):
    """
    Extract frame number from URL and construct previous frame URL.
    Example: .../000512.jpg -> .../000511.jpg
    """
    if not url:
        return ""
    
    # Extract the filename from the URL
    parts = url.split('/')
    filename = parts[-1]
    
    # Extract frame number and extension (e.g., 000512.jpg)
    match = re.match(r'^(\d+)\.(\w+)$', filename)
    if not match:
        return ""  # Not a valid frame filename
    
    frame_num = int(match.group(1))
    ext = match.group(2)
    padding_length = len(match.group(1))
    
    # Calculate previous frame number
    prev_frame_num = frame_num - offset
    if prev_frame_num < 0:
        return ""
    
    # Reconstruct filename with padded frame number
    prev_frame_name = str(prev_frame_num).zfill(padding_length) + '.' + ext
    
    # Replace the filename in the URL
    parts[-1] = prev_frame_name
    return '/'.join(parts)


def process_csv_file(input_path, in_place=True):
    """Process a CSV file and populate prev_image column"""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return None
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    # Check if required columns exist
    if 'current_image' not in fieldnames:
        print(f"❌ 'current_image' column not found in {input_path}")
        return None
    
    if 'prev_image' not in fieldnames:
        print(f"❌ 'prev_image' column not found in {input_path}")
        return None
    
    # Process each row
    updated_count = 0
    for row in rows:
        current_url = row.get('current_image', '').strip()
        if current_url and not row.get('prev_image', '').strip():
            prev_url = get_previous_frame_url(current_url)
            row['prev_image'] = prev_url
            if prev_url:
                updated_count += 1
    
    if updated_count == 0:
        print(f"⚠️  No rows needed updating in {input_path}")
        return None
    
    # Write back to file (in place or new file)
    if in_place:
        output_file = input_file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Updated {input_path} in place")
        print(f"   Generated prev_image URLs for {updated_count} rows")
    else:
        output_file = input_file.parent / f"{input_file.stem}_with_prev{input_file.suffix}"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Processed {input_path}")
        print(f"   Generated prev_image URLs for {updated_count} rows")
        print(f"   Output: {output_file}")
    
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_prev_images.py <csv_file_path>")
        print("\nExamples:")
        print("  python generate_prev_images.py comparison_input.csv")
        print("  python generate_prev_images.py path/to/comparison_input.csv")
        print("  python generate_prev_images.py comparison_*/comparison_input.csv")
        sys.exit(1)
    
    # Handle glob patterns
    file_paths = []
    for pattern in sys.argv[1:]:
        matches = glob.glob(pattern)
        if matches:
            file_paths.extend(matches)
        else:
            # Not a glob pattern, treat as literal path
            file_paths.append(pattern)
    
    if not file_paths:
        print("❌ No files found matching the pattern(s)")
        sys.exit(1)
    
    print(f"Found {len(file_paths)} file(s) to process\n")
    
    success_count = 0
    for csv_path in file_paths:
        print(f"{'='*60}")
        result = process_csv_file(csv_path, in_place=True)
        if result is not None:
            success_count += 1
        print()
    
    print(f"{'='*60}")
    print(f"✅ Successfully processed {success_count}/{len(file_paths)} file(s)")


if __name__ == "__main__":
    main()

