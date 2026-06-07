#!/usr/bin/env python3
"""
Generate polygon_geometry.csv from polygon JSON files.

Extracts center coordinates (COM, BBC, CHC, ICC) from each polygon JSON
and creates the geometry manifest required by config_loader.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def extract_centers_from_json(json_path: Path) -> Dict[str, Any]:
    """Extract center coordinates from polygon JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    centers = data.get('centers', {})
    
    # Extract center coordinates (canonical coordinates, centered at origin)
    center_data = {}
    
    for center_type in ['COM', 'BBC', 'CHC', 'ICC']:
        if center_type in centers:
            coords = centers[center_type]
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                # Store as px (will be transformed to screen coords by geometry_utils)
                center_data[f'center_{center_type.lower()}_x_canonical_px'] = coords[0]
                center_data[f'center_{center_type.lower()}_y_canonical_px'] = coords[1]
    
    return center_data


def main():
    """Generate polygon_geometry.csv from all polygon JSON files."""
    
    # Polygon directory
    polygon_dir = Path("data/raw/stimuli/polygons")
    
    if not polygon_dir.exists():
        print(f"Error: Polygon directory not found: {polygon_dir}")
        return 1
    
    # Load polygon mapping
    mapping_file = Path("docs/polygon_mapping.csv")
    if not mapping_file.exists():
        print(f"Error: Polygon mapping not found: {mapping_file}")
        return 1
    
    mapping_df = pd.read_csv(mapping_file)
    
    print("=" * 70)
    print("Generating polygon_geometry.csv")
    print("=" * 70)
    print(f"Polygon directory: {polygon_dir}")
    print(f"Number of polygons: {len(mapping_df)}")
    print()
    
    # Extract geometry for each polygon
    geometry_rows = []
    
    for _, row in mapping_df.iterrows():
        polygon_id = row['polygon_id']
        json_filename = row['json_filename']
        json_path = polygon_dir / json_filename
        
        if not json_path.exists():
            print(f"Warning: JSON file not found: {json_path}")
            continue
        
        try:
            centers = extract_centers_from_json(json_path)
            
            geometry_row = {
                'polygon_id': polygon_id,
                'polygon_case': row['polygon_case'],
                'json_filename': json_filename,
            }
            geometry_row.update(centers)
            
            geometry_rows.append(geometry_row)
            print(f"✓ {polygon_id}: {len(centers)//2} centers extracted")
            
        except Exception as e:
            print(f"✗ Error processing {json_path}: {e}")
    
    # Create DataFrame
    geometry_df = pd.DataFrame(geometry_rows)
    
    # Set polygon_id as index
    geometry_df = geometry_df.set_index('polygon_id')
    
    # Save to CSV
    output_path = Path("manifests/polygon_geometry.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_df.to_csv(output_path)
    
    print()
    print("=" * 70)
    print(f"✓ Geometry manifest saved: {output_path}")
    print(f"  - Polygons: {len(geometry_df)}")
    print(f"  - Columns: {list(geometry_df.columns)}")
    print()
    
    # Show sample
    print("Sample (first 3 polygons):")
    print("-" * 70)
    print(geometry_df.head(3).to_string())
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
