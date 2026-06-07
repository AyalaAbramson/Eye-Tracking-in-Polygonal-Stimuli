"""
Recalculate distances to geometric centers using corrected coordinate system.
This script ONLY recalculates distances for already-extracted fixations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

# Configuration
INPUT_FILE = Path("analysis/second_fixation_partA/second_fixations_raw.csv")
OUTPUT_FILE = Path("analysis/second_fixation_partA/second_fixations_with_distances_CORRECTED.csv")
GEOM_FILE = Path("manifests/polygon_geometry.csv")
POLYGONS_DIR = Path("data/raw/stimuli/polygons")

# Screen parameters (matching experiment)
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
SCREEN_CENTER_X = SCREEN_WIDTH / 2
SCREEN_CENTER_Y = SCREEN_HEIGHT / 2
APERTURE_SCALE_FACTOR = int(SCREEN_HEIGHT * 0.92)  # 1987 pixels

# Load geometry
GEOM_DF = pd.read_csv(GEOM_FILE).set_index('polygon_id')


def load_polygon_vertices(polygon_id, polygon_case):
    """Load polygon vertices from JSON file."""
    case_to_filename = {
        'baseline_symmetric': 'baseline_symmetric_consolidated.json',
        'baseline_asymmetric': 'baseline_asymmetric_consolidated.json',
        'baseline_rectangle': 'baseline_rectangle.json',
        'allfar_concave': 'allfar_concave.json',
        'allfar_convex': 'allfar_convex.json',
        'allfar_intermediate': 'allfar_intermediate.json',
        'pair_C1_bbc_vs_chc_icc': 'pair_com_bbc_vs_chc_icc',
        'pair_C2_chc_vs_bbc_icc': 'pair_com_chc_vs_bbc_icc',
        'pair_C3_icc_vs_chc_bbc': 'pair_com_icc_vs_chc_bbc',
    }

    if polygon_case in case_to_filename:
        base_filename = case_to_filename[polygon_case]
        if not base_filename.endswith('.json'):
            replicate_num = str(polygon_id).split('_')[-1]
            json_file = POLYGONS_DIR / f"{base_filename}_{replicate_num}.json"
        else:
            json_file = POLYGONS_DIR / base_filename
    elif polygon_case.startswith('iso_'):
        json_file = POLYGONS_DIR / f"{polygon_id}.json"
    else:
        if polygon_id.startswith('baseline_sym'):
            json_file = POLYGONS_DIR / 'baseline_symmetric_consolidated.json'
        elif polygon_id.startswith('baseline_asym'):
            json_file = POLYGONS_DIR / 'baseline_asymmetric_consolidated.json'
        elif polygon_id.startswith('baseline_rect'):
            json_file = POLYGONS_DIR / 'baseline_rectangle.json'
        else:
            return None

    if json_file.exists():
        with open(json_file, 'r') as f:
            data = json.load(f)
            vertices = data.get('vertices_xy') or data.get('vertices', [])
            if vertices:
                return np.array(vertices)

            # Handle polar coordinate format
            if 'theta' in data and 'area' in data:
                thetas = np.array(data['theta'])
                n = len(thetas)
                area = data.get('area', 550)
                base_r = np.sqrt(area / np.pi) * 1.2
                mean_theta = np.mean(thetas)
                vertices = []
                for i, theta in enumerate(thetas):
                    angle = 2 * np.pi * i / n
                    local_r = base_r * (theta / mean_theta)
                    x = local_r * np.cos(angle)
                    y = local_r * np.sin(angle)
                    vertices.append([x, y])
                return np.array(vertices)

    return None


print("="*80)
print("RECALCULATING DISTANCES WITH CORRECTED COORDINATE SYSTEM")
print("="*80)

# Load raw fixations
print(f"\nLoading: {INPUT_FILE}")
fixations_df = pd.read_csv(INPUT_FILE)
print(f"Loaded {len(fixations_df)} fixations")

# Calculate distances
fixations_with_dist = fixations_df.copy()

print("\nCalculating distances...")
for idx, row in fixations_with_dist.iterrows():
    if idx % 500 == 0:
        print(f"  Processing fixation {idx}/{len(fixations_with_dist)}...")

    polygon_id = row['polygon_id']
    polygon_case = row['polygon_case']
    fix_x = row['x']
    fix_y = row['y']

    if polygon_id not in GEOM_DF.index:
        continue

    geom = GEOM_DF.loc[polygon_id]
    vertices = load_polygon_vertices(polygon_id, polygon_case)

    if vertices is None:
        continue

    # Calculate transformation (same as visualization)
    min_xy = vertices.min(axis=0)
    max_xy = vertices.max(axis=0)
    current_max_dim = max(max_xy[0] - min_xy[0], max_xy[1] - min_xy[1])
    normalize_scale = APERTURE_SCALE_FACTOR / current_max_dim if current_max_dim > 0 else 1.0
    center_xy = (min_xy + max_xy) / 2

    # Calculate distances to each center
    for center_type in ['com', 'bbc', 'chc', 'icc']:
        center_x_canonical = geom[f'center_{center_type}_x_canonical_px']
        center_y_canonical = geom[f'center_{center_type}_y_canonical_px']

        # Transform to screen coordinates
        center_x_centered = center_x_canonical - center_xy[0]
        center_y_centered = center_y_canonical - center_xy[1]
        center_x_scaled = center_x_centered * normalize_scale
        center_y_scaled = -(center_y_centered * normalize_scale)  # Flip Y
        center_x_screen = center_x_scaled + SCREEN_CENTER_X
        center_y_screen = center_y_scaled + SCREEN_CENTER_Y

        # Calculate distance
        dist = np.sqrt((fix_x - center_x_screen)**2 + (fix_y - center_y_screen)**2)

        fixations_with_dist.at[idx, f'dist_to_{center_type}'] = dist
        fixations_with_dist.at[idx, f'{center_type}_x'] = center_x_screen
        fixations_with_dist.at[idx, f'{center_type}_y'] = center_y_screen

    # Find closest center
    distances = {
        'com': fixations_with_dist.at[idx, 'dist_to_com'],
        'bbc': fixations_with_dist.at[idx, 'dist_to_bbc'],
        'chc': fixations_with_dist.at[idx, 'dist_to_chc'],
        'icc': fixations_with_dist.at[idx, 'dist_to_icc']
    }

    closest_center = min(distances, key=distances.get)
    closest_distance = distances[closest_center]

    fixations_with_dist.at[idx, 'closest_center'] = closest_center
    fixations_with_dist.at[idx, 'closest_distance'] = closest_distance

# Save
print(f"\nSaving: {OUTPUT_FILE}")
fixations_with_dist.to_csv(OUTPUT_FILE, index=False)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nMean distances to each center (pixels):")
for center_type in ['com', 'bbc', 'chc', 'icc']:
    dist_col = f'dist_to_{center_type}'
    valid_dist = fixations_with_dist[dist_col].dropna()
    print(f"  {center_type.upper()}: M={valid_dist.mean():.1f}px (SD={valid_dist.std():.1f}px, N={len(valid_dist)})")

print(f"\nClosest center frequencies:")
counts = fixations_with_dist['closest_center'].value_counts()
for center in ['com', 'bbc', 'chc', 'icc']:
    count = counts.get(center, 0)
    pct = count / len(fixations_with_dist) * 100
    print(f"  {center.upper()}: {count} ({pct:.1f}%)")

print("\nDone!")
