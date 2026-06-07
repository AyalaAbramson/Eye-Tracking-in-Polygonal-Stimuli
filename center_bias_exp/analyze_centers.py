"""
Analyze which polygon center is closest to the cue position for each trial.
"""
import pandas as pd
import numpy as np

# Load P02 trial data
trials_df = pd.read_csv(r"data/raw/participant_P02/part_A/session_20260115_103203/logs_trial/trials.csv")

# Load polygon geometry
geom_df = pd.read_csv(r"manifests/polygon_geometry.csv")

# Screen center
SCREEN_CENTER_X = 1920
SCREEN_CENTER_Y = 1080

# Aperture scale factor
APERTURE_SCALE = 1987

# Function to convert canonical px to screen px
def canonical_to_screen(cx, cy, scale=APERTURE_SCALE):
    """Convert canonical polygon coordinates to screen coordinates."""
    # Canonical coords are in a normalized space, need to scale and offset
    screen_x = SCREEN_CENTER_X + (cx * scale / 1000)  # Approximate scaling
    screen_y = SCREEN_CENTER_Y + (cy * scale / 1000)
    return screen_x, screen_y

# Merge geometry data with trials
trials_with_geom = trials_df.merge(geom_df, on='polygon_id', how='left', suffixes=('', '_geom'))

# For each trial, compute which center is closest to the cue
results = []

for idx, row in trials_with_geom.iterrows():
    trial_uid = row['trial_uid']
    polygon_id = row['polygon_id']
    polygon_case = row['polygon_case']
    cue_x = row['cue_x_px']
    cue_y = row['cue_y_px']
    cue_pos_id = row['cue_pos_id']
    
    # Get center coordinates (canonical px - relative to screen center at scale)
    # These need to be converted to absolute screen coordinates
    centers = {}
    
    # COM (Center of Mass)
    if pd.notna(row.get('center_com_x_canonical_px')):
        com_x = SCREEN_CENTER_X + row['center_com_x_canonical_px']
        com_y = SCREEN_CENTER_Y + row['center_com_y_canonical_px']
        centers['COM'] = (com_x, com_y)
    
    # BBC (Bounding Box Center)
    if pd.notna(row.get('center_bbc_x_canonical_px')):
        bbc_x = SCREEN_CENTER_X + row['center_bbc_x_canonical_px']
        bbc_y = SCREEN_CENTER_Y + row['center_bbc_y_canonical_px']
        centers['BBC'] = (bbc_x, bbc_y)
    
    # CHC (Convex Hull Centroid)
    if pd.notna(row.get('center_chc_x_canonical_px')):
        chc_x = SCREEN_CENTER_X + row['center_chc_x_canonical_px']
        chc_y = SCREEN_CENTER_Y + row['center_chc_y_canonical_px']
        centers['CHC'] = (chc_x, chc_y)
    
    # ICC (Incircle Center)
    if pd.notna(row.get('center_icc_x_canonical_px')):
        icc_x = SCREEN_CENTER_X + row['center_icc_x_canonical_px']
        icc_y = SCREEN_CENTER_Y + row['center_icc_y_canonical_px']
        centers['ICC'] = (icc_x, icc_y)
    
    # Screen center (always at 1920, 1080)
    centers['SCREEN'] = (SCREEN_CENTER_X, SCREEN_CENTER_Y)
    
    # Calculate distances from cue to each center
    distances = {}
    for center_name, (cx, cy) in centers.items():
        dist = np.sqrt((cue_x - cx)**2 + (cue_y - cy)**2)
        distances[center_name] = dist
    
    # Find closest center
    if distances:
        closest = min(distances, key=distances.get)
        closest_dist = distances[closest]
    else:
        closest = 'N/A'
        closest_dist = np.nan
    
    # Rank centers by distance
    sorted_centers = sorted(distances.items(), key=lambda x: x[1])
    rank_str = ', '.join([f"{name}:{dist:.1f}" for name, dist in sorted_centers[:3]])
    
    results.append({
        'trial_uid': trial_uid,
        'polygon_id': polygon_id,
        'polygon_case': polygon_case,
        'cue_pos_id': cue_pos_id,
        'cue_x': cue_x,
        'cue_y': cue_y,
        'closest_center': closest,
        'closest_dist_px': closest_dist,
        'ranking': rank_str
    })

results_df = pd.DataFrame(results)

# Print results for first 2 blocks (78 trials)
print("=" * 100)
print("P02 - Which center is closest to cue for each trial (Block 1 & 2)")
print("=" * 100)
print(f"{'Trial':<15} {'Polygon':<25} {'Case':<25} {'Cue Pos':<10} {'Closest':<10} {'Dist(px)':<10} {'Top 3 Rankings'}")
print("-" * 100)

for _, row in results_df.iterrows():
    print(f"{row['trial_uid']:<15} {row['polygon_id']:<25} {row['polygon_case']:<25} {row['cue_pos_id']:<10} {row['closest_center']:<10} {row['closest_dist_px']:<10.1f} {row['ranking']}")

# Summary statistics
print("\n" + "=" * 100)
print("Summary: How often is each center type closest to the cue?")
print("=" * 100)
closest_counts = results_df['closest_center'].value_counts()
for center, count in closest_counts.items():
    pct = count / len(results_df) * 100
    print(f"  {center}: {count} trials ({pct:.1f}%)")

# By polygon case
print("\n" + "=" * 100)
print("By polygon case: Which center is usually closest?")
print("=" * 100)
for case in results_df['polygon_case'].unique():
    case_df = results_df[results_df['polygon_case'] == case]
    counts = case_df['closest_center'].value_counts()
    print(f"\n{case}:")
    for center, count in counts.items():
        print(f"  {center}: {count}")
