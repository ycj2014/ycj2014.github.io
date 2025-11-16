#!/usr/bin/env python3
"""
Script to fix comparison CSV files:
1. Move data from prev_image -> current_image
2. Move data from current_image -> description_a
3. Move data from description_a -> description_b
4. Generate prev_image URL from current_image
"""

import csv
import re
import sys
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


def fix_csv_file(input_path):
    """Fix CSV file column alignment and generate prev_image URLs"""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        return
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Fix each row
    fixed_rows = []
    for row in rows:
        # The data is shifted - fix it:
        # prev_image (has URL) -> current_image
        # current_image (has desc_a) -> description_a  
        # description_a (has desc_b) -> description_b
        
        current_url = row.get('prev_image', '').strip()
        desc_a = row.get('current_image', '').strip()
        desc_b = row.get('description_a', '').strip()
        
        if current_url:  # Only process rows with URLs
            prev_url = get_previous_frame_url(current_url)
            
            fixed_row = {
                'prev_image': prev_url,
                'current_image': current_url,
                'description_a': desc_a,
                'description_b': desc_b
            }
            fixed_rows.append(fixed_row)
    
    # Write fixed CSV
    fieldnames = ['prev_image', 'current_image', 'description_a', 'description_b']
    
    with open(input_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fixed_rows)
    
    print(f"✅ Fixed {input_path}")
    print(f"   Processed {len(fixed_rows)} rows")
    print(f"   Generated prev_image URLs for all rows")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_comparison_csv.py <csv_file> [csv_file2 ...]")
        return
    
    for csv_path in sys.argv[1:]:
        print(f"\n{'='*60}")
        fix_csv_file(csv_path)


if __name__ == "__main__":
    main()

