"""
Partial analysis script for participants P03-P12 (Part A only).

Analyzes:
1. Data quality metrics (calibration, drift correction, trial completion)
2. Fixation patterns (spatial distribution, center bias)
3. Geometric center biases (mass, hull, bbc, icc vs screen center)
4. Descriptive statistics across participants
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set up plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

# Participants to analyze
PARTICIPANTS = [f"P{i:02d}" for i in range(3, 13)]  # P03-P12
PART = "A"

# Output directory
OUTPUT_DIR = Path("analysis/partial_partA")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_participant_data(participant_id, part):
    """Load all CSV logs for a participant's session."""
    # Find the most recent session
    participant_dir = Path(f"data/raw/participant_{participant_id}")
    part_dir = participant_dir / f"part_{part}"

    if not part_dir.exists():
        return None

    # Get most recent session
    sessions = sorted(part_dir.glob("session_*"))
    if not sessions:
        return None

    session_dir = sessions[-1]  # Most recent

    # Load CSV files
    trials_path = session_dir / "logs_trial" / "trials.csv"
    blocks_path = session_dir / "logs_block" / "blocks.csv"
    memory_path = session_dir / "logs_memory" / "memory.csv"

    data = {}

    if trials_path.exists():
        data['trials'] = pd.read_csv(trials_path)

    if blocks_path.exists():
        data['blocks'] = pd.read_csv(blocks_path)

    if memory_path.exists():
        data['memory'] = pd.read_csv(memory_path)

    data['session_dir'] = session_dir

    return data if data else None


def analyze_data_quality(all_data):
    """Analyze data quality metrics across participants."""
    print("\n" + "="*60)
    print("DATA QUALITY ANALYSIS")
    print("="*60)

    quality_metrics = []

    for participant_id, data in all_data.items():
        if not data or 'trials' not in data or 'blocks' not in data:
            continue

        trials = data['trials']
        blocks = data['blocks']

        # Trial-level metrics
        n_trials_total = len(trials)
        n_trials_completed = (~trials.get('aborted', False)).sum()
        n_trials_aborted = trials.get('aborted', False).sum()

        # Fixation metrics
        fixation_achieved = trials.get('fixation_achieved', True)
        n_fixation_success = fixation_achieved.sum()
        n_fixation_failed = (~fixation_achieved).sum()

        # Block-level metrics
        calibration_errors = blocks['calibration_error_deg'].dropna()
        validation_errors = blocks['validation_error_avg_deg'].dropna()
        validation_max_errors = blocks['validation_error_max_deg'].dropna()

        # Memory task
        if 'memory' in data:
            memory = data['memory']
            memory_accuracy = memory['correct'].mean() if len(memory) > 0 else np.nan
        else:
            memory_accuracy = np.nan

        metrics = {
            'participant_id': participant_id,
            'n_trials_total': n_trials_total,
            'n_trials_completed': n_trials_completed,
            'n_trials_aborted': n_trials_aborted,
            'completion_rate': n_trials_completed / n_trials_total if n_trials_total > 0 else 0,
            'n_fixation_success': n_fixation_success,
            'n_fixation_failed': n_fixation_failed,
            'fixation_success_rate': n_fixation_success / n_trials_total if n_trials_total > 0 else 0,
            'calibration_error_mean': calibration_errors.mean(),
            'calibration_error_std': calibration_errors.std(),
            'validation_error_mean': validation_errors.mean(),
            'validation_error_std': validation_errors.std(),
            'validation_max_error_mean': validation_max_errors.mean(),
            'validation_max_error_std': validation_max_errors.std(),
            'memory_accuracy': memory_accuracy,
        }

        quality_metrics.append(metrics)

    quality_df = pd.DataFrame(quality_metrics)

    # Print summary
    print(f"\nParticipants analyzed: {len(quality_df)}")
    print(f"\nTrial Completion:")
    print(f"  Total trials: {quality_df['n_trials_total'].sum()}")
    print(f"  Completed: {quality_df['n_trials_completed'].sum()}")
    print(f"  Aborted: {quality_df['n_trials_aborted'].sum()}")
    print(f"  Mean completion rate: {quality_df['completion_rate'].mean():.2%}")

    print(f"\nFixation Success:")
    print(f"  Mean success rate: {quality_df['fixation_success_rate'].mean():.2%}")
    print(f"  Range: {quality_df['fixation_success_rate'].min():.2%} - {quality_df['fixation_success_rate'].max():.2%}")

    print(f"\nCalibration Quality:")
    print(f"  Mean error: {quality_df['calibration_error_mean'].mean():.3f}° (SD: {quality_df['calibration_error_mean'].std():.3f}°)")
    print(f"  Validation mean: {quality_df['validation_error_mean'].mean():.3f}° (SD: {quality_df['validation_error_mean'].std():.3f}°)")
    print(f"  Validation max: {quality_df['validation_max_error_mean'].mean():.3f}° (SD: {quality_df['validation_max_error_mean'].std():.3f}°)")

    print(f"\nMemory Task:")
    print(f"  Mean accuracy: {quality_df['memory_accuracy'].mean():.2%}")

    # Save to CSV
    quality_df.to_csv(OUTPUT_DIR / "data_quality_summary.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'data_quality_summary.csv'}")

    return quality_df


def analyze_spatial_distribution(all_data):
    """Analyze fixation spatial distributions and center bias."""
    print("\n" + "="*60)
    print("SPATIAL DISTRIBUTION ANALYSIS")
    print("="*60)

    # Collect all trial data
    all_trials = []

    for participant_id, data in all_data.items():
        if not data or 'trials' not in data:
            continue

        trials = data['trials'].copy()
        trials['participant_id'] = participant_id
        all_trials.append(trials)

    if not all_trials:
        print("No trial data found!")
        return None

    combined_trials = pd.concat(all_trials, ignore_index=True)

    # Filter completed trials only
    completed = combined_trials[~combined_trials.get('aborted', False)].copy()

    print(f"\nAnalyzing {len(completed)} completed trials from {len(PARTICIPANTS)} participants")

    # Use the pre-computed distance columns from the trial logs
    center_types = ['mass', 'hull', 'bbc', 'icc']

    # Summary statistics
    print(f"\nDistance from screen center (degrees):")
    for center_type in center_types:
        deg_col = f'dist_center_{center_type}_to_screen_deg'
        if deg_col in completed.columns:
            # Filter out NaN values (empty polygon trials)
            valid_distances = completed[deg_col].dropna()
            if len(valid_distances) > 0:
                mean_dist = valid_distances.mean()
                std_dist = valid_distances.std()
                median_dist = valid_distances.median()
                print(f"  {center_type.upper():4s}: M={mean_dist:.2f}° (SD={std_dist:.2f}°, Mdn={median_dist:.2f}°)")
            else:
                print(f"  {center_type.upper():4s}: No valid data")

    # Save summary
    summary_stats = []
    for center_type in center_types:
        deg_col = f'dist_center_{center_type}_to_screen_deg'
        if deg_col in completed.columns:
            valid_distances = completed[deg_col].dropna()
            if len(valid_distances) > 0:
                summary_stats.append({
                    'center_type': center_type,
                    'n_valid_trials': len(valid_distances),
                    'mean_distance_deg': valid_distances.mean(),
                    'std_distance_deg': valid_distances.std(),
                    'median_distance_deg': valid_distances.median(),
                    'q25_distance_deg': valid_distances.quantile(0.25),
                    'q75_distance_deg': valid_distances.quantile(0.75),
                })

    summary_df = pd.DataFrame(summary_stats)
    summary_df.to_csv(OUTPUT_DIR / "spatial_distribution_summary.csv", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'spatial_distribution_summary.csv'}")

    return completed


def plot_data_quality(quality_df):
    """Create visualizations for data quality metrics."""
    print("\n" + "="*60)
    print("GENERATING PLOTS")
    print("="*60)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Completion rate
    ax = axes[0, 0]
    ax.bar(quality_df['participant_id'], quality_df['completion_rate'])
    ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='100%')
    ax.set_xlabel('Participant')
    ax.set_ylabel('Completion Rate')
    ax.set_title('Trial Completion Rate by Participant')
    ax.set_ylim([0.9, 1.01])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # 2. Calibration error
    ax = axes[0, 1]
    ax.bar(quality_df['participant_id'], quality_df['calibration_error_mean'],
           yerr=quality_df['calibration_error_std'], capsize=5)
    ax.axhline(y=0.5, color='g', linestyle='--', alpha=0.5, label='Excellent (<0.5°)')
    ax.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='Good (<1.0°)')
    ax.set_xlabel('Participant')
    ax.set_ylabel('Calibration Error (degrees)')
    ax.set_title('Calibration Error by Participant')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # 3. Validation error
    ax = axes[1, 0]
    ax.bar(quality_df['participant_id'], quality_df['validation_error_mean'],
           yerr=quality_df['validation_error_std'], capsize=5)
    ax.axhline(y=0.5, color='g', linestyle='--', alpha=0.5, label='Excellent (<0.5°)')
    ax.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='Good (<1.0°)')
    ax.set_xlabel('Participant')
    ax.set_ylabel('Validation Error (degrees)')
    ax.set_title('Validation Error by Participant')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # 4. Memory accuracy
    ax = axes[1, 1]
    ax.bar(quality_df['participant_id'], quality_df['memory_accuracy'])
    ax.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Chance (50%)')
    ax.set_xlabel('Participant')
    ax.set_ylabel('Memory Accuracy')
    ax.set_title('Memory Task Accuracy by Participant')
    ax.set_ylim([0, 1])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "data_quality_plots.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'data_quality_plots.png'}")
    plt.close()


def main():
    """Main analysis pipeline."""
    print("="*60)
    print("PARTIAL ANALYSIS: Part A (P03-P12)")
    print("="*60)

    # Load data for all participants
    print("\nLoading participant data...")
    all_data = {}

    for participant_id in PARTICIPANTS:
        print(f"  Loading {participant_id}...", end=" ")
        data = load_participant_data(participant_id, PART)
        if data:
            all_data[participant_id] = data
            print("OK")
        else:
            print("MISSING")

    print(f"\nLoaded data for {len(all_data)}/{len(PARTICIPANTS)} participants")

    if not all_data:
        print("ERROR: No data found!")
        return

    # Run analyses
    quality_df = analyze_data_quality(all_data)
    completed_trials = analyze_spatial_distribution(all_data)

    # Generate plots
    if quality_df is not None:
        plot_data_quality(quality_df)

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {OUTPUT_DIR.absolute()}")
    print("\nGenerated files:")
    print("  - data_quality_summary.csv")
    print("  - spatial_distribution_summary.csv")
    print("  - data_quality_plots.png")


if __name__ == "__main__":
    main()
