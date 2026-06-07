"""
Analysis of 2nd fixation after stimulus onset - where center bias is strongest.

Main hypothesis: The 2nd fixation after stimulus onset shows bias toward
specific geometric centers (COM, BBC, CHC, or ICC) rather than screen center.

Analysis:
1. Extract 2nd fixation from EDF files for each trial
2. Calculate distance from 2nd fixation to each geometric center
3. Compare which center type is closest to 2nd fixation
4. Visualize spatial distribution by polygon and participant
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import subprocess
import re
import json
import warnings
warnings.filterwarnings('ignore')

# Set up plotting
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150

# Configuration
PARTICIPANTS = [f"P{i:02d}" for i in range(3, 18)]  # P03-P17
PART = "A"
OUTPUT_DIR = Path("analysis/second_fixation_partA")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Screen parameters (matching experiment)
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
SCREEN_CENTER_X = SCREEN_WIDTH / 2
SCREEN_CENTER_Y = SCREEN_HEIGHT / 2
APERTURE_SCALE_FACTOR = int(SCREEN_HEIGHT * 0.92)  # 1987 pixels

# Polygon directory
POLYGONS_DIR = Path("data/raw/stimuli/polygons")

# Load geometry manifest
GEOM_DF = pd.read_csv("manifests/polygon_geometry.csv")
GEOM_DF = GEOM_DF.set_index('polygon_id')


def extract_second_fixation_from_asc(asc_path, trial_uid):
    """
    Extract the 2nd fixation after STIM_ON for a specific trial from ASC file.

    Returns
    -------
    dict or None
        Fixation data: {'eye', 'start_time', 'end_time', 'duration', 'x', 'y', 'pupil'}
    """
    with open(asc_path, 'r') as f:
        lines = f.readlines()

    # Find trial start
    trial_started = False
    stim_on_time = None
    fixations = []

    for line in lines:
        # Look for TRIALID message
        if f"TRIALID {trial_uid}" in line:
            trial_started = True
            fixations = []
            stim_on_time = None
            continue

        if not trial_started:
            continue

        # Look for STIM_ON message
        if "STIM_ON" in line:
            # Extract timestamp from message
            # Format: "MSG	1234567	STIM_ON 123.456"
            parts = line.split()
            if len(parts) >= 3:
                try:
                    stim_on_time = float(parts[1])  # EyeLink timestamp
                except:
                    pass
            continue

        # Look for fixation events AFTER stim_on
        # Format: EFIX L/R start end duration x y pupil
        # Example: EFIX L   1234567  1234789  222  1920  1080  2500
        if line.startswith("EFIX") and stim_on_time is not None:
            parts = line.split()
            if len(parts) >= 8:
                try:
                    eye = parts[1]  # L or R
                    start_time = float(parts[2])
                    end_time = float(parts[3])
                    duration = float(parts[4])
                    x = float(parts[5])
                    y = float(parts[6])
                    pupil = float(parts[7])

                    # Only consider fixations AFTER stimulus onset
                    if start_time >= stim_on_time:
                        fixations.append({
                            'eye': eye,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration,
                            'x': x,
                            'y': y,
                            'pupil': pupil
                        })
                except:
                    pass

        # Check for TRIAL_END to stop
        if "TRIAL_END" in line or "TRIAL_RESULT" in line:
            break

    # Return 2nd fixation (index 1) if it exists
    if len(fixations) >= 2:
        return fixations[1]
    else:
        return None


def convert_edf_to_asc(edf_path):
    """Convert EDF file to ASC format using edf2asc."""
    asc_path = edf_path.with_suffix('.asc')

    if asc_path.exists():
        return asc_path

    print(f"  Converting {edf_path.name} to ASC...")

    try:
        result = subprocess.run(
            ['edf2asc', str(edf_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120
        )

        if asc_path.exists():
            return asc_path
        else:
            print(f"    Warning: ASC file not created")
            return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def extract_all_second_fixations():
    """Extract 2nd fixations for all participants and trials."""
    print("="*60)
    print("EXTRACTING 2ND FIXATIONS FROM EDF FILES")
    print("="*60)

    all_fixations = []

    for participant_id in PARTICIPANTS:
        print(f"\n{participant_id}:")

        participant_dir = Path(f"data/raw/participant_{participant_id}")
        part_dir = participant_dir / f"part_{PART}"

        if not part_dir.exists():
            print(f"  No data found")
            continue

        # Get most recent session
        sessions = sorted(part_dir.glob("session_*"))
        if not sessions:
            continue

        session_dir = sessions[-1]

        # Load trial manifest
        trials_csv = session_dir / "logs_trial" / "trials.csv"
        if not trials_csv.exists():
            print(f"  No trials.csv found")
            continue

        trials_df = pd.read_csv(trials_csv)

        # Get EDF files
        edf_dir = session_dir / "edf"
        edf_files = sorted(edf_dir.glob("*.edf"))

        if not edf_files:
            print(f"  No EDF files found")
            continue

        print(f"  Found {len(edf_files)} EDF files")

        # Process each EDF file
        for edf_path in edf_files:
            # Convert to ASC
            asc_path = convert_edf_to_asc(edf_path)

            if asc_path is None:
                continue

            # Extract 2nd fixations for each trial
            for idx, trial_row in trials_df.iterrows():
                trial_uid = trial_row['trial_uid']

                fixation = extract_second_fixation_from_asc(asc_path, trial_uid)

                if fixation is not None:
                    # Add trial metadata
                    fixation['participant_id'] = participant_id
                    fixation['trial_uid'] = trial_uid
                    fixation['polygon_id'] = trial_row['polygon_id']
                    fixation['polygon_case'] = trial_row.get('polygon_case', '')
                    fixation['trial_type'] = trial_row['trial_type']

                    all_fixations.append(fixation)

        print(f"  Extracted {len([f for f in all_fixations if f['participant_id'] == participant_id])} 2nd fixations")

    if not all_fixations:
        print("\nERROR: No fixations extracted!")
        return None

    fixations_df = pd.DataFrame(all_fixations)

    print(f"\n" + "="*60)
    print(f"TOTAL: {len(fixations_df)} 2nd fixations extracted")
    print(f"Coverage: {len(fixations_df)} / 3207 trials = {len(fixations_df)/3207*100:.1f}%")
    print("="*60)

    # Save raw fixation data
    fixations_df.to_csv(OUTPUT_DIR / "second_fixations_raw.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'second_fixations_raw.csv'}")

    return fixations_df


def load_polygon_vertices(polygon_id, polygon_case):
    """Load polygon vertices from JSON file using polygon_case and polygon_id."""
    # Mapping from polygon_case to JSON filename pattern
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

    # Get the base filename
    if polygon_case in case_to_filename:
        base_filename = case_to_filename[polygon_case]

        # For pairs and iso cases with replicates, append the ID number
        if not base_filename.endswith('.json'):
            # Extract the replicate number from polygon_id (e.g., "pair_C1_01" -> "01")
            replicate_num = str(polygon_id).split('_')[-1]
            json_file = POLYGONS_DIR / f"{base_filename}_{replicate_num}.json"
        else:
            json_file = POLYGONS_DIR / base_filename
    elif polygon_case.startswith('iso_'):
        # iso_* cases: use polygon_id as-is
        json_file = POLYGONS_DIR / f"{polygon_id}.json"
    else:
        # Handle any other case by trying to construct filename from polygon_id
        # For baseline_sym_01, baseline_asym_01, etc.
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
            # Try 'vertices_xy' first (new format), then 'vertices' (legacy format)
            vertices = data.get('vertices_xy') or data.get('vertices', [])
            if vertices:
                return np.array(vertices)

            # Handle polar coordinate format (baseline_symmetric and baseline_asymmetric)
            # This matches the exact conversion used in the experiment (psychopy_utils.py)
            if 'theta' in data and 'area' in data:
                thetas = np.array(data['theta'])
                n = len(thetas)
                area = data.get('area', 550)

                # Calculate base radius from area (matching experiment code)
                base_r = np.sqrt(area / np.pi) * 1.2
                mean_theta = np.mean(thetas)

                # Place vertices at EQUAL angular intervals with VARIABLE radius
                # This creates a radial polygon where theta values control distance from center
                vertices = []
                for i, theta in enumerate(thetas):
                    angle = 2 * np.pi * i / n  # Equal angular spacing
                    local_r = base_r * (theta / mean_theta)  # Variable radius
                    x = local_r * np.cos(angle)
                    y = local_r * np.sin(angle)
                    vertices.append([x, y])

                return np.array(vertices)

    return None


def calculate_distances_to_centers(fixations_df):
    """Calculate distance from 2nd fixation to each geometric center.

    Uses the correct coordinate transformation matching the experiment:
    1. Load polygon vertices
    2. Calculate per-polygon normalization (max dimension -> 1987px)
    3. Center at origin, scale, flip Y, translate to screen center
    4. Calculate distances in properly transformed coordinate space
    """
    print("\n" + "="*60)
    print("CALCULATING DISTANCES TO GEOMETRIC CENTERS")
    print("="*60)

    fixations_with_dist = fixations_df.copy()

    # Add geometric center data
    for idx, row in fixations_with_dist.iterrows():
        polygon_id = row['polygon_id']
        polygon_case = row['polygon_case']
        fix_x = row['x']
        fix_y = row['y']

        if polygon_id not in GEOM_DF.index:
            continue

        geom = GEOM_DF.loc[polygon_id]

        # Load polygon vertices to calculate correct transformation
        vertices = load_polygon_vertices(polygon_id, polygon_case)

        if vertices is None:
            print(f"  Warning: Could not load vertices for polygon {polygon_id} ({polygon_case})")
            continue

        # Calculate the same transformation used in the experiment
        # Step 1: Find current max dimension
        min_xy = vertices.min(axis=0)
        max_xy = vertices.max(axis=0)
        current_max_dim = max(max_xy[0] - min_xy[0], max_xy[1] - min_xy[1])

        # Step 2: Calculate normalize scale (same as experiment)
        normalize_scale = APERTURE_SCALE_FACTOR / current_max_dim if current_max_dim > 0 else 1.0

        # Step 3: Calculate canonical space center (for centering vertices)
        center_xy = (min_xy + max_xy) / 2

        # Calculate distances to each center type
        for center_type in ['com', 'bbc', 'chc', 'icc']:
            center_x_canonical = geom[f'center_{center_type}_x_canonical_px']
            center_y_canonical = geom[f'center_{center_type}_y_canonical_px']

            # Transform center from canonical to screen coordinates
            # (same transformation as vertices: center at origin, scale, flip Y, translate)
            center_x_centered = center_x_canonical - center_xy[0]
            center_y_centered = center_y_canonical - center_xy[1]
            center_x_scaled = center_x_centered * normalize_scale
            center_y_scaled = -(center_y_centered * normalize_scale)  # Flip Y
            center_x_screen = center_x_scaled + SCREEN_CENTER_X
            center_y_screen = center_y_scaled + SCREEN_CENTER_Y

            # Calculate Euclidean distance in screen coordinates
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

    # Summary statistics
    print(f"\nMean distance from 2nd fixation to each center (pixels):")
    for center_type in ['com', 'bbc', 'chc', 'icc']:
        dist_col = f'dist_to_{center_type}'
        if dist_col in fixations_with_dist.columns:
            valid_dist = fixations_with_dist[dist_col].dropna()
            print(f"  {center_type.upper()}: M={valid_dist.mean():.1f}px (SD={valid_dist.std():.1f}px)")

    # Which center is closest most often?
    print(f"\nClosest center to 2nd fixation:")
    if 'closest_center' in fixations_with_dist.columns:
        counts = fixations_with_dist['closest_center'].value_counts()
        for center, count in counts.items():
            pct = count / len(fixations_with_dist) * 100
            print(f"  {center.upper()}: {count} trials ({pct:.1f}%)")

    # Save
    fixations_with_dist.to_csv(OUTPUT_DIR / "second_fixations_with_distances.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'second_fixations_with_distances.csv'}")

    return fixations_with_dist


def visualize_second_fixations(fixations_df):
    """Create comprehensive visualizations of 2nd fixation patterns."""
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)

    # Figure 1: Spatial distribution of 2nd fixations overlaid with centers
    fig, axes = plt.subplots(2, 2, figsize=(16, 16))
    axes = axes.flatten()

    center_types = ['com', 'bbc', 'chc', 'icc']
    colors = {'com': 'red', 'bbc': 'blue', 'chc': 'green', 'icc': 'purple'}

    for idx, center_type in enumerate(center_types):
        ax = axes[idx]

        # Plot all 2nd fixations
        ax.scatter(fixations_df['x'], fixations_df['y'],
                  c='gray', alpha=0.3, s=20, label='2nd fixation')

        # Plot geometric centers for all polygons
        center_x_col = f'{center_type}_x'
        center_y_col = f'{center_type}_y'

        if center_x_col in fixations_df.columns:
            # Get unique centers
            unique_centers = fixations_df[[center_x_col, center_y_col]].drop_duplicates()
            ax.scatter(unique_centers[center_x_col], unique_centers[center_y_col],
                      c=colors[center_type], s=200, marker='X',
                      edgecolors='black', linewidths=2,
                      label=f'{center_type.upper()} center')

        # Screen center for reference
        ax.scatter([1920], [1080], c='black', s=300, marker='+',
                  linewidths=3, label='Screen center')

        ax.set_title(f'2nd Fixation vs {center_type.upper()} Centers',
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
        ax.set_xlim(0, 3840)
        ax.set_ylim(2160, 0)  # Flip y-axis
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "second_fixation_spatial_distribution.png",
                dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'second_fixation_spatial_distribution.png'}")
    plt.close()

    # Figure 2: Distance distributions
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Violin plot of distances
    ax = axes[0]
    distance_data = []
    for center_type in center_types:
        dist_col = f'dist_to_{center_type}'
        if dist_col in fixations_df.columns:
            for dist in fixations_df[dist_col].dropna():
                distance_data.append({'Center Type': center_type.upper(), 'Distance (px)': dist})

    if distance_data:
        dist_df = pd.DataFrame(distance_data)
        sns.violinplot(data=dist_df, x='Center Type', y='Distance (px)', ax=ax)
        ax.set_title('Distance from 2nd Fixation to Each Center', fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

    # Bar plot of closest center
    ax = axes[1]
    if 'closest_center' in fixations_df.columns:
        counts = fixations_df['closest_center'].value_counts()
        counts = counts.reindex(['com', 'bbc', 'chc', 'icc'], fill_value=0)
        colors_list = [colors[c] for c in counts.index]
        ax.bar(range(len(counts)), counts.values, color=colors_list, alpha=0.7)
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels([c.upper() for c in counts.index])
        ax.set_title('Which Center is Closest to 2nd Fixation?', fontweight='bold')
        ax.set_ylabel('Number of Trials')
        ax.grid(axis='y', alpha=0.3)

        # Add percentage labels
        total = counts.sum()
        for i, (center, count) in enumerate(counts.items()):
            pct = count / total * 100
            ax.text(i, count + 5, f'{pct:.1f}%', ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "second_fixation_distance_analysis.png",
                dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'second_fixation_distance_analysis.png'}")
    plt.close()


def statistical_analysis(fixations_df):
    """Run statistical tests on 2nd fixation patterns."""
    print("\n" + "="*60)
    print("STATISTICAL ANALYSIS")
    print("="*60)

    # Test 1: Which center type has smallest mean distance?
    print("\nRepeated measures comparison (paired t-tests):")

    center_types = ['com', 'bbc', 'chc', 'icc']
    results = []

    for center_type in center_types:
        dist_col = f'dist_to_{center_type}'
        if dist_col in fixations_df.columns:
            distances = fixations_df[dist_col].dropna()
            results.append({
                'center_type': center_type.upper(),
                'mean_distance': distances.mean(),
                'std_distance': distances.std(),
                'n': len(distances)
            })

    results_df = pd.DataFrame(results)
    print("\n", results_df.to_string(index=False))

    # Pairwise comparisons
    print("\nPairwise t-tests:")
    for i in range(len(center_types)):
        for j in range(i+1, len(center_types)):
            ct1, ct2 = center_types[i], center_types[j]

            dist1 = fixations_df[f'dist_to_{ct1}'].dropna()
            dist2 = fixations_df[f'dist_to_{ct2}'].dropna()

            # Paired t-test (same trials, different centers)
            common_idx = dist1.index.intersection(dist2.index)
            if len(common_idx) > 0:
                t_stat, p_value = stats.ttest_rel(
                    dist1.loc[common_idx],
                    dist2.loc[common_idx]
                )
                sig = '***' if p_value < 0.001 else ('**' if p_value < 0.01 else ('*' if p_value < 0.05 else 'ns'))
                print(f"  {ct1.upper()} vs {ct2.upper()}: t={t_stat:.3f}, p={p_value:.4f} {sig}")

    # Test 2: Chi-square test on closest center frequencies
    print("\nChi-square test (closest center frequencies):")
    if 'closest_center' in fixations_df.columns:
        observed = fixations_df['closest_center'].value_counts()
        observed = observed.reindex(['com', 'bbc', 'chc', 'icc'], fill_value=0)

        # Expected: equal distribution
        expected = [len(fixations_df) / 4] * 4

        chi2, p_value = stats.chisquare(observed.values, expected)
        print(f"  Chi-square = {chi2:.3f}, p = {p_value:.4f}")

        if p_value < 0.05:
            print("  ==> Significant preference for certain center types!")
        else:
            print("  ==> No significant preference (equal distribution)")

    # Save results
    results_df.to_csv(OUTPUT_DIR / "statistical_results.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'statistical_results.csv'}")


def main():
    """Main analysis pipeline."""
    print("="*60)
    print("ANALYSIS: 2nd Fixation After Stimulus Onset")
    print("Hypothesis: Center bias toward geometric centers")
    print("="*60)

    # Extract 2nd fixations from EDF files
    fixations_df = extract_all_second_fixations()

    if fixations_df is None or len(fixations_df) == 0:
        print("ERROR: No fixation data extracted!")
        return

    # Calculate distances to geometric centers
    fixations_df = calculate_distances_to_centers(fixations_df)

    # Create visualizations
    visualize_second_fixations(fixations_df)

    # Statistical analysis
    statistical_analysis(fixations_df)

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
