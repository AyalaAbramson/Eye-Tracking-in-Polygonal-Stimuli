"""
Detailed analysis for Part A: Center bias by polygon and participant.

Main hypothesis: Is there a preferred geometric location across all subjects
defined by polygon type?

Analysis includes:
1. Fixation extraction from EDF files (using existing data or geometry manifest)
2. Center bias metrics by polygon type
3. Individual participant patterns
4. Statistical tests for preferred locations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Set up plotting
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150

# Configuration
PARTICIPANTS = [f"P{i:02d}" for i in range(3, 13)]
PART = "A"
OUTPUT_DIR = Path("analysis/detailed_partA")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load geometry manifest
GEOM_DF = pd.read_csv("manifests/polygon_geometry.csv")
GEOM_DF = GEOM_DF.set_index('polygon_id')


def load_all_trial_data():
    """Load trial data from all participants."""
    print("Loading trial data from all participants...")

    all_trials = []

    for participant_id in PARTICIPANTS:
        participant_dir = Path(f"data/raw/participant_{participant_id}")
        part_dir = participant_dir / f"part_{PART}"

        if not part_dir.exists():
            continue

        # Get most recent session
        sessions = sorted(part_dir.glob("session_*"))
        if not sessions:
            continue

        session_dir = sessions[-1]
        trials_path = session_dir / "logs_trial" / "trials.csv"

        if trials_path.exists():
            df = pd.read_csv(trials_path)
            df['participant_id'] = participant_id
            all_trials.append(df)
            print(f"  {participant_id}: {len(df)} trials")

    if not all_trials:
        return None

    combined = pd.concat(all_trials, ignore_index=True)
    print(f"\nTotal: {len(combined)} trials from {len(all_trials)} participants")

    return combined


def add_geometry_data(trials_df):
    """Add geometry data from manifest to trials."""
    print("\nAdding geometry data from manifest...")

    # Merge with geometry manifest
    trials_with_geom = trials_df.copy()

    # For each trial, look up geometry from manifest
    for idx, row in trials_with_geom.iterrows():
        polygon_id = row['polygon_id']

        if polygon_id in GEOM_DF.index:
            geom_row = GEOM_DF.loc[polygon_id]

            # Add geometric center locations (in canonical coordinates, need to scale/transform)
            # Note: These are from the manifest, which are in canonical 500px space
            # We need to scale to experiment resolution (3840x2160)

            # Center of Mass (COM)
            trials_with_geom.at[idx, 'center_com_x_canonical'] = geom_row['center_com_x_canonical_px']
            trials_with_geom.at[idx, 'center_com_y_canonical'] = geom_row['center_com_y_canonical_px']

            # Bounding Box Center (BBC)
            trials_with_geom.at[idx, 'center_bbc_x_canonical'] = geom_row['center_bbc_x_canonical_px']
            trials_with_geom.at[idx, 'center_bbc_y_canonical'] = geom_row['center_bbc_y_canonical_px']

            # Convex Hull Center (CHC)
            trials_with_geom.at[idx, 'center_chc_x_canonical'] = geom_row['center_chc_x_canonical_px']
            trials_with_geom.at[idx, 'center_chc_y_canonical'] = geom_row['center_chc_y_canonical_px']

            # Inscribed Circle Center (ICC)
            trials_with_geom.at[idx, 'center_icc_x_canonical'] = geom_row['center_icc_x_canonical_px']
            trials_with_geom.at[idx, 'center_icc_y_canonical'] = geom_row['center_icc_y_canonical_px']

    print(f"Added geometry data for trials")

    return trials_with_geom


def analyze_by_polygon(trials_df):
    """Analyze center bias patterns by polygon type."""
    print("\n" + "="*60)
    print("ANALYSIS BY POLYGON TYPE")
    print("="*60)

    # Filter completed trials with valid geometry
    completed = trials_df[~trials_df.get('aborted', False)].copy()

    # Group by polygon_id
    polygon_groups = completed.groupby('polygon_id')

    polygon_stats = []

    for polygon_id, group in polygon_groups:
        n_trials = len(group)
        n_participants = group['participant_id'].nunique()

        # Get center locations from manifest
        if polygon_id in GEOM_DF.index:
            geom = GEOM_DF.loc[polygon_id]

            stats_row = {
                'polygon_id': polygon_id,
                'polygon_case': geom['polygon_case'],
                'n_trials': n_trials,
                'n_participants': n_participants,
                'center_com_x': geom['center_com_x_canonical_px'],
                'center_com_y': geom['center_com_y_canonical_px'],
                'center_bbc_x': geom['center_bbc_x_canonical_px'],
                'center_bbc_y': geom['center_bbc_y_canonical_px'],
                'center_chc_x': geom['center_chc_x_canonical_px'],
                'center_chc_y': geom['center_chc_y_canonical_px'],
                'center_icc_x': geom['center_icc_x_canonical_px'],
                'center_icc_y': geom['center_icc_y_canonical_px'],
            }

            polygon_stats.append(stats_row)

    polygon_df = pd.DataFrame(polygon_stats)

    # Calculate distances from screen center (250, 250 in canonical space)
    screen_center = np.array([250, 250])

    for center_type in ['com', 'bbc', 'chc', 'icc']:
        x_col = f'center_{center_type}_x'
        y_col = f'center_{center_type}_y'

        if x_col in polygon_df.columns:
            centers = polygon_df[[x_col, y_col]].values
            distances = np.linalg.norm(centers - screen_center, axis=1)
            polygon_df[f'dist_{center_type}_from_screen'] = distances

    print(f"\nAnalyzed {len(polygon_df)} unique polygons")
    print(f"\nMean distance from screen center (canonical pixels):")
    for center_type in ['com', 'bbc', 'chc', 'icc']:
        dist_col = f'dist_{center_type}_from_screen'
        if dist_col in polygon_df.columns:
            mean_dist = polygon_df[dist_col].mean()
            std_dist = polygon_df[dist_col].std()
            print(f"  {center_type.upper()}: M={mean_dist:.2f}px (SD={std_dist:.2f}px)")

    # Save
    polygon_df.to_csv(OUTPUT_DIR / "polygon_center_analysis.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'polygon_center_analysis.csv'}")

    return polygon_df


def analyze_by_participant(trials_df):
    """Analyze patterns for each participant."""
    print("\n" + "="*60)
    print("ANALYSIS BY PARTICIPANT")
    print("="*60)

    # Filter completed trials
    completed = trials_df[~trials_df.get('aborted', False)].copy()

    participant_stats = []

    for participant_id in PARTICIPANTS:
        p_trials = completed[completed['participant_id'] == participant_id]

        if len(p_trials) == 0:
            continue

        stats_row = {
            'participant_id': participant_id,
            'n_trials': len(p_trials),
            'n_unique_polygons': p_trials['polygon_id'].nunique(),
            'completion_rate': (~p_trials.get('aborted', False)).mean(),
        }

        participant_stats.append(stats_row)

    participant_df = pd.DataFrame(participant_stats)

    print(f"\nParticipant summary:")
    print(participant_df.to_string(index=False))

    # Save
    participant_df.to_csv(OUTPUT_DIR / "participant_summary.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'participant_summary.csv'}")

    return participant_df


def visualize_polygon_centers(polygon_df):
    """Create visualization of polygon centers."""
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)

    # Create figure with multiple subplots
    fig = plt.figure(figsize=(16, 12))
    gs = plt.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

    # Screen center in canonical space
    screen_center = np.array([250, 250])

    # Color palette for different center types
    colors = {'com': 'red', 'bbc': 'blue', 'chc': 'green', 'icc': 'purple'}

    # Plot 1: All centers overlaid
    ax1 = fig.add_subplot(gs[0, :])
    ax1.set_title('All Geometric Centers (Canonical 500x500 Space)', fontsize=14, fontweight='bold')
    ax1.axhline(y=250, color='gray', linestyle='--', alpha=0.3, label='Screen center')
    ax1.axvline(x=250, color='gray', linestyle='--', alpha=0.3)
    ax1.scatter([250], [250], c='black', s=200, marker='x', linewidths=3, label='Screen center', zorder=10)

    for center_type, color in colors.items():
        x_col = f'center_{center_type}_x'
        y_col = f'center_{center_type}_y'

        if x_col in polygon_df.columns:
            ax1.scatter(polygon_df[x_col], polygon_df[y_col],
                       c=color, alpha=0.6, s=50, label=center_type.upper())

    ax1.set_xlabel('X (canonical pixels)')
    ax1.set_ylabel('Y (canonical pixels)')
    ax1.set_xlim(0, 500)
    ax1.set_ylim(500, 0)  # Flip y-axis to match image coordinates
    ax1.legend(loc='upper right')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)

    # Plots 2-5: Individual center types
    center_types = ['com', 'bbc', 'chc', 'icc']

    for idx, center_type in enumerate(center_types):
        row = 1 + idx // 2
        col = idx % 2
        ax = fig.add_subplot(gs[row, col])

        x_col = f'center_{center_type}_x'
        y_col = f'center_{center_type}_y'

        if x_col in polygon_df.columns:
            # Plot centers
            ax.scatter(polygon_df[x_col], polygon_df[y_col],
                      c=colors[center_type], alpha=0.6, s=80)

            # Screen center
            ax.scatter([250], [250], c='black', s=200, marker='x', linewidths=3, zorder=10)
            ax.axhline(y=250, color='gray', linestyle='--', alpha=0.3)
            ax.axvline(x=250, color='gray', linestyle='--', alpha=0.3)

            # Calculate and show stats
            dist_col = f'dist_{center_type}_from_screen'
            if dist_col in polygon_df.columns:
                mean_dist = polygon_df[dist_col].mean()
                std_dist = polygon_df[dist_col].std()
                ax.text(0.02, 0.98, f'M={mean_dist:.1f}px\nSD={std_dist:.1f}px',
                       transform=ax.transAxes, va='top', ha='left',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_title(f'{center_type.upper()} Centers', fontweight='bold')
        ax.set_xlabel('X (canonical pixels)')
        ax.set_ylabel('Y (canonical pixels)')
        ax.set_xlim(0, 500)
        ax.set_ylim(500, 0)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

    # Plot 6: Distribution of distances
    ax6 = fig.add_subplot(gs[2, 2])

    distances_data = []
    for center_type in center_types:
        dist_col = f'dist_{center_type}_from_screen'
        if dist_col in polygon_df.columns:
            for dist in polygon_df[dist_col]:
                distances_data.append({'Center Type': center_type.upper(), 'Distance (px)': dist})

    if distances_data:
        dist_df = pd.DataFrame(distances_data)
        sns.violinplot(data=dist_df, x='Center Type', y='Distance (px)', ax=ax6)
        ax6.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Screen center')
        ax6.set_title('Distance Distribution', fontweight='bold')
        ax6.set_xlabel('')
        ax6.grid(axis='y', alpha=0.3)

    plt.savefig(OUTPUT_DIR / "polygon_centers_visualization.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'polygon_centers_visualization.png'}")
    plt.close()


def visualize_by_polygon_case(polygon_df):
    """Visualize centers grouped by polygon case."""
    print("\nCreating polygon case visualizations...")

    if 'polygon_case' not in polygon_df.columns:
        print("  Warning: polygon_case column not found")
        return

    # Get unique polygon cases
    cases = polygon_df['polygon_case'].unique()

    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    axes = axes.flatten()

    center_types = ['com', 'bbc', 'chc', 'icc']
    colors_map = {'com': 'red', 'bbc': 'blue', 'chc': 'green', 'icc': 'purple'}

    for ax_idx, center_type in enumerate(center_types):
        ax = axes[ax_idx]

        x_col = f'center_{center_type}_x'
        y_col = f'center_{center_type}_y'

        if x_col in polygon_df.columns:
            # Plot by polygon case
            for case in cases:
                case_data = polygon_df[polygon_df['polygon_case'] == case]
                ax.scatter(case_data[x_col], case_data[y_col],
                          alpha=0.6, s=80, label=case[:20])  # Truncate long labels

            # Screen center
            ax.scatter([250], [250], c='black', s=200, marker='x', linewidths=3, zorder=10)
            ax.axhline(y=250, color='gray', linestyle='--', alpha=0.3)
            ax.axvline(x=250, color='gray', linestyle='--', alpha=0.3)

        ax.set_title(f'{center_type.upper()} Centers by Polygon Case', fontweight='bold')
        ax.set_xlabel('X (canonical pixels)')
        ax.set_ylabel('Y (canonical pixels)')
        ax.set_xlim(0, 500)
        ax.set_ylim(500, 0)
        ax.set_aspect('equal')
        ax.legend(loc='best', fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "centers_by_polygon_case.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'centers_by_polygon_case.png'}")
    plt.close()


def statistical_tests(polygon_df):
    """Run statistical tests for preferred locations."""
    print("\n" + "="*60)
    print("STATISTICAL TESTS")
    print("="*60)

    results = []

    for center_type in ['com', 'bbc', 'chc', 'icc']:
        dist_col = f'dist_{center_type}_from_screen'

        if dist_col in polygon_df.columns:
            distances = polygon_df[dist_col].dropna()

            # One-sample t-test: Is mean distance significantly different from 0?
            t_stat, p_value = stats.ttest_1samp(distances, 0)

            results.append({
                'center_type': center_type.upper(),
                'mean_distance': distances.mean(),
                'std_distance': distances.std(),
                't_statistic': t_stat,
                'p_value': p_value,
                'sig': '***' if p_value < 0.001 else ('**' if p_value < 0.01 else ('*' if p_value < 0.05 else 'ns'))
            })

            print(f"\n{center_type.upper()}:")
            print(f"  Mean distance: {distances.mean():.2f}px (SD={distances.std():.2f})")
            print(f"  t({len(distances)-1}) = {t_stat:.3f}, p = {p_value:.4f} {results[-1]['sig']}")

    # Compare center types (ANOVA)
    print("\n" + "-"*60)
    print("Comparing center types (One-way ANOVA):")

    groups = []
    labels = []
    for center_type in ['com', 'bbc', 'chc', 'icc']:
        dist_col = f'dist_{center_type}_from_screen'
        if dist_col in polygon_df.columns:
            groups.append(polygon_df[dist_col].dropna().values)
            labels.append(center_type.upper())

    if len(groups) >= 2:
        f_stat, p_value = stats.f_oneway(*groups)
        print(f"  F({len(groups)-1}, {sum(len(g) for g in groups) - len(groups)}) = {f_stat:.3f}, p = {p_value:.4f}")

        if p_value < 0.05:
            print("  ==> Significant differences between center types!")
        else:
            print("  ==> No significant differences between center types")

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "statistical_tests.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'statistical_tests.csv'}")

    return results_df


def main():
    """Main analysis pipeline."""
    print("="*60)
    print("DETAILED ANALYSIS: Part A")
    print("Main Hypothesis: Preferred geometric location across subjects")
    print("="*60)

    # Load data
    trials_df = load_all_trial_data()

    if trials_df is None:
        print("ERROR: No data found!")
        return

    # Add geometry data from manifest
    trials_df = add_geometry_data(trials_df)

    # Analyze by polygon
    polygon_df = analyze_by_polygon(trials_df)

    # Analyze by participant
    participant_df = analyze_by_participant(trials_df)

    # Create visualizations
    visualize_polygon_centers(polygon_df)
    visualize_by_polygon_case(polygon_df)

    # Statistical tests
    statistical_tests(polygon_df)

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {OUTPUT_DIR.absolute()}")
    print("\nGenerated files:")
    print("  - polygon_center_analysis.csv")
    print("  - participant_summary.csv")
    print("  - polygon_centers_visualization.png")
    print("  - centers_by_polygon_case.png")
    print("  - statistical_tests.csv")


if __name__ == "__main__":
    main()
