"""
Fixation Extraction Pipeline for Center Bias Experiment

This script extracts fixations from EyeLink .asc files and matches them to trials
from the stimulus manifest. It computes:
- Fixation 1, 2, 3, 4 after stimulus onset
- Distance from each fixation to all 4 geometric centers
- Winner label (closest center) for each fixation
- Temporal metrics (onset latency, duration)

Usage:
    python src/extract_fixations.py --participant P01 --part A
    python src/extract_fixations.py --session path/to/session --output results.csv

Output:
    - fixations.csv: One row per fixation per trial
    - fixations_summary.csv: One row per trial with Fix1-4 data
    - quality_report.txt: Data quality metrics

Author: Eye Tracking Lab
Date: 2026-01-17
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np


class Fixation(object):
    """Represents a single fixation event from EyeLink."""
    def __init__(self, eye, start_time, end_time, duration, x, y, pupil_size):
        self.eye = eye  # 'L' or 'R'
        self.start_time = start_time  # ms
        self.end_time = end_time  # ms
        self.duration = duration  # ms
        self.x = x  # pixels
        self.y = y  # pixels
        self.pupil_size = pupil_size  # arbitrary units


class Trial(object):
    """Represents a single trial with extracted fixations."""
    def __init__(self, trial_uid, stim_on_time, stim_off_time, fixations,
                 center_com_x=None, center_com_y=None,
                 center_chc_x=None, center_chc_y=None,
                 center_bbc_x=None, center_bbc_y=None,
                 center_icc_x=None, center_icc_y=None):
        self.trial_uid = trial_uid
        self.stim_on_time = stim_on_time  # ms from ASC file
        self.stim_off_time = stim_off_time  # ms from ASC file
        self.fixations = fixations  # List of Fixation objects

        # Center positions (from trial manifest)
        self.center_com_x = center_com_x
        self.center_com_y = center_com_y
        self.center_chc_x = center_chc_x
        self.center_chc_y = center_chc_y
        self.center_bbc_x = center_bbc_x
        self.center_bbc_y = center_bbc_y
        self.center_icc_x = center_icc_x
        self.center_icc_y = center_icc_y


def parse_asc_file(asc_path) :
    """
    Parse EyeLink .asc file and extract fixations per trial.

    Parameters
    ----------
    asc_path 
        Path to .asc file

    Returns
    -------
    dict
        Dictionary mapping trial_uid to Trial objects with fixations
    """
    trials = {}
    current_trial_uid = None
    current_stim_on = None
    current_stim_off = None
    current_fixations = []

    print(f"Parsing ASC file: {asc_path}")

    with open(asc_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()

            # Extract trial ID from TRIALID message
            if line.startswith('MSG') and 'TRIALID' in line:
                # MSG 12345678 TRIALID A_MB01_T001
                match = re.search(r'TRIALID\s+(\S+)', line)
                if match:
                    # Save previous trial if exists
                    if current_trial_uid and current_stim_on:
                        trials[current_trial_uid] = Trial(
                            trial_uid=current_trial_uid,
                            stim_on_time=current_stim_on,
                            stim_off_time=current_stim_off,
                            fixations=current_fixations,
                            # Centers will be filled from manifest later
                            center_com_x=0, center_com_y=0,
                            center_chc_x=0, center_chc_y=0,
                            center_bbc_x=0, center_bbc_y=0,
                            center_icc_x=0, center_icc_y=0
                        )

                    # Start new trial
                    current_trial_uid = match.group(1)
                    current_stim_on = None
                    current_stim_off = None
                    current_fixations = []

            # Extract STIM_ON timestamp
            elif line.startswith('MSG') and 'STIM_ON' in line:
                # MSG 12345678 STIM_ON 123.456
                match = re.search(r'MSG\s+(\d+)\s+STIM_ON', line)
                if match:
                    current_stim_on = float(match.group(1))

            # Extract STIM_OFF timestamp
            elif line.startswith('MSG') and 'STIM_OFF' in line:
                match = re.search(r'MSG\s+(\d+)\s+STIM_OFF', line)
                if match:
                    current_stim_off = float(match.group(1))

            # Extract fixation events
            # Format: EFIX L   12345678  12345778   100  960.5  540.2  1234
            # EFIX <eye> <start> <end> <duration> <x> <y> <pupil>
            elif line.startswith('EFIX'):
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        fix = Fixation(
                            eye=parts[1],
                            start_time=float(parts[2]),
                            end_time=float(parts[3]),
                            duration=float(parts[4]),
                            x=float(parts[5]),
                            y=float(parts[6]),
                            pupil_size=float(parts[7]) if len(parts) > 7 else 0.0
                        )

                        # Only keep fixations within current trial's stimulus epoch
                        if current_stim_on and current_stim_off:
                            if current_stim_on <= fix.start_time <= current_stim_off:
                                current_fixations.append(fix)

                    except (ValueError, IndexError) as e:
                        # Skip malformed fixation lines
                        continue

        # Save last trial
        if current_trial_uid and current_stim_on:
            trials[current_trial_uid] = Trial(
                trial_uid=current_trial_uid,
                stim_on_time=current_stim_on,
                stim_off_time=current_stim_off,
                fixations=current_fixations,
                center_com_x=0, center_com_y=0,
                center_chc_x=0, center_chc_y=0,
                center_bbc_x=0, center_bbc_y=0,
                center_icc_x=0, center_icc_y=0
            )

    print(f"  Found {len(trials)} trials with {sum(len(t.fixations) for t in trials.values())} fixations")
    return trials


def merge_trial_metadata(
    trials: Dict[str, Trial],
    trial_manifest_csv
) :
    """
    Merge center positions from trial manifest into Trial objects.

    Parameters
    ----------
    trials : dict
        Dictionary of Trial objects from ASC parsing
    trial_manifest_csv 
        Path to trials.csv with center coordinates

    Returns
    -------
    dict
        Updated trials with center positions filled
    """
    print(f"Loading trial manifest: {trial_manifest_csv}")
    df = pd.read_csv(trial_manifest_csv)

    for idx, row in df.iterrows():
        trial_uid = row['trial_uid']
        if trial_uid in trials:
            # Fill in center positions
            trials[trial_uid].center_com_x = row.get('center_mass_x_px', 0)
            trials[trial_uid].center_com_y = row.get('center_mass_y_px', 0)
            trials[trial_uid].center_chc_x = row.get('center_hull_x_px', 0)
            trials[trial_uid].center_chc_y = row.get('center_hull_y_px', 0)
            trials[trial_uid].center_bbc_x = row.get('center_bbc_x_px', 0)
            trials[trial_uid].center_bbc_y = row.get('center_bbc_y_px', 0)
            trials[trial_uid].center_icc_x = row.get('center_icc_x_px', 0)
            trials[trial_uid].center_icc_y = row.get('center_icc_y_px', 0)

    print(f"  Merged metadata for {len(trials)} trials")
    return trials


def compute_distances(fix_x: float, fix_y: float, trial: Trial) :
    """
    Compute Euclidean distance from fixation to all 4 centers.

    Parameters
    ----------
    fix_x : float
        Fixation x coordinate (pixels)
    fix_y : float
        Fixation y coordinate (pixels)
    trial : Trial
        Trial object with center positions

    Returns
    -------
    dict
        Distances to each center: {'com': d1, 'chc': d2, 'bbc': d3, 'icc': d4}
    """
    distances = {}

    # Center of Mass
    dx = fix_x - trial.center_com_x
    dy = fix_y - trial.center_com_y
    distances['com'] = np.sqrt(dx**2 + dy**2)

    # Convex Hull Center
    dx = fix_x - trial.center_chc_x
    dy = fix_y - trial.center_chc_y
    distances['chc'] = np.sqrt(dx**2 + dy**2)

    # Bounding Box Center
    dx = fix_x - trial.center_bbc_x
    dy = fix_y - trial.center_bbc_y
    distances['bbc'] = np.sqrt(dx**2 + dy**2)

    # Inscribed Circle Center
    dx = fix_x - trial.center_icc_x
    dy = fix_y - trial.center_icc_y
    distances['icc'] = np.sqrt(dx**2 + dy**2)

    return distances


def identify_winner(distances: Dict[str, float]) :
    """
    Identify the closest center and compute margin.

    Parameters
    ----------
    distances : dict
        Distances to each center

    Returns
    -------
    tuple
        (winner_label, margin) where margin = 2nd_best - best
    """
    sorted_centers = sorted(distances.items(), key=lambda x: x[1])
    winner = sorted_centers[0][0]
    best_dist = sorted_centers[0][1]
    second_best_dist = sorted_centers[1][1] if len(sorted_centers) > 1 else best_dist
    margin = second_best_dist - best_dist

    return winner, margin


def extract_fixations_for_trial(trial: Trial) -> pd.DataFrame:
    """
    Extract first 4 fixations after stimulus onset for a trial.

    Returns DataFrame with one row per fixation (up to 4 rows).
    """
    rows = []

    for fix_num, fix in enumerate(trial.fixations[:4], start=1):
        # Compute onset latency relative to STIM_ON
        onset_latency_ms = fix.start_time - trial.stim_on_time

        # Compute distances to all centers
        distances = compute_distances(fix.x, fix.y, trial)

        # Identify winner
        winner, margin = identify_winner(distances)

        row = {
            'trial_uid': trial.trial_uid,
            'fixation_number': fix_num,
            'eye': fix.eye,
            'onset_latency_ms': onset_latency_ms,
            'duration_ms': fix.duration,
            'x_px': fix.x,
            'y_px': fix.y,
            'pupil_size': fix.pupil_size,

            # Distances to each center (pixels)
            'dist_com_px': distances['com'],
            'dist_chc_px': distances['chc'],
            'dist_bbc_px': distances['bbc'],
            'dist_icc_px': distances['icc'],

            # Winner
            'winner': winner,
            'winner_margin_px': margin,

            # Center positions for reference
            'center_com_x_px': trial.center_com_x,
            'center_com_y_px': trial.center_com_y,
            'center_chc_x_px': trial.center_chc_x,
            'center_chc_y_px': trial.center_chc_y,
            'center_bbc_x_px': trial.center_bbc_x,
            'center_bbc_y_px': trial.center_bbc_y,
            'center_icc_x_px': trial.center_icc_x,
            'center_icc_y_px': trial.center_icc_y,
        }

        rows.append(row)

    return pd.DataFrame(rows)


def create_summary_row(trial: Trial, fixations_df: pd.DataFrame) :
    """
    Create a summary row for a trial with Fix1-4 data in wide format.

    Returns one row with columns: trial_uid, fix1_winner, fix1_dist_com, ..., fix4_...
    """
    row = {'trial_uid': trial.trial_uid}

    for fix_num in range(1, 5):
        fix_data = fixations_df[fixations_df['fixation_number'] == fix_num]

        if len(fix_data) > 0:
            fix = fix_data.iloc[0]
            row[f'fix{fix_num}_exists'] = True
            row[f'fix{fix_num}_onset_latency_ms'] = fix['onset_latency_ms']
            row[f'fix{fix_num}_duration_ms'] = fix['duration_ms']
            row[f'fix{fix_num}_x_px'] = fix['x_px']
            row[f'fix{fix_num}_y_px'] = fix['y_px']
            row[f'fix{fix_num}_winner'] = fix['winner']
            row[f'fix{fix_num}_winner_margin_px'] = fix['winner_margin_px']
            row[f'fix{fix_num}_dist_com_px'] = fix['dist_com_px']
            row[f'fix{fix_num}_dist_chc_px'] = fix['dist_chc_px']
            row[f'fix{fix_num}_dist_bbc_px'] = fix['dist_bbc_px']
            row[f'fix{fix_num}_dist_icc_px'] = fix['dist_icc_px']
        else:
            row[f'fix{fix_num}_exists'] = False
            row[f'fix{fix_num}_onset_latency_ms'] = np.nan
            row[f'fix{fix_num}_duration_ms'] = np.nan
            row[f'fix{fix_num}_x_px'] = np.nan
            row[f'fix{fix_num}_y_px'] = np.nan
            row[f'fix{fix_num}_winner'] = None
            row[f'fix{fix_num}_winner_margin_px'] = np.nan
            row[f'fix{fix_num}_dist_com_px'] = np.nan
            row[f'fix{fix_num}_dist_chc_px'] = np.nan
            row[f'fix{fix_num}_dist_bbc_px'] = np.nan
            row[f'fix{fix_num}_dist_icc_px'] = np.nan

    return row


def generate_quality_report(
    trials: Dict[str, Trial],
    fixations_df: pd.DataFrame,
    output_path
):
    """
    Generate data quality report.
    """
    total_trials = len(trials)
    trials_with_fix2 = fixations_df[fixations_df['fixation_number'] == 2]['trial_uid'].nunique()

    report = f"""
=============================================================================
FIXATION EXTRACTION QUALITY REPORT
Generated: {datetime.now().isoformat()}
=============================================================================

TRIAL SUMMARY
-------------
Total trials processed: {total_trials}
Trials with Fixation 2: {trials_with_fix2} ({trials_with_fix2/total_trials*100:.1f}%)
Trials missing Fixation 2: {total_trials - trials_with_fix2} ({(total_trials - trials_with_fix2)/total_trials*100:.1f}%)

FIXATION COUNTS
---------------
"""

    for fix_num in range(1, 5):
        count = len(fixations_df[fixations_df['fixation_number'] == fix_num])
        report += f"Fixation {fix_num}: {count} ({count/total_trials*100:.1f}% of trials)\n"

    report += f"""
FIXATION 2 ANALYSIS (Primary DV)
---------------------------------
"""

    fix2 = fixations_df[fixations_df['fixation_number'] == 2]
    if len(fix2) > 0:
        report += f"Mean onset latency: {fix2['onset_latency_ms'].mean():.1f} ms (SD={fix2['onset_latency_ms'].std():.1f})\n"
        report += f"Mean duration: {fix2['duration_ms'].mean():.1f} ms (SD={fix2['duration_ms'].std():.1f})\n"
        report += f"\nWinner distribution (Fix2):\n"

        winner_counts = fix2['winner'].value_counts()
        for center, count in winner_counts.items():
            report += f"  {center.upper()}: {count} ({count/len(fix2)*100:.1f}%)\n"

        report += f"\nMean distances to centers (Fix2):\n"
        for center in ['com', 'chc', 'bbc', 'icc']:
            mean_dist = fix2[f'dist_{center}_px'].mean()
            report += f"  {center.upper()}: {mean_dist:.1f} px\n"

    report += "\n=============================================================================\n"

    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\nQuality report saved to: {output_path}")
    print(report)


def main():
    parser = argparse.ArgumentParser(
        description='Extract fixations from EyeLink ASC files for center bias analysis'
    )
    parser.add_argument(
        '--asc',
        type=str,
        help='Path to .asc file (e.g., data/raw/participant_P01/part_A/session_*/edf/*.asc)'
    )
    parser.add_argument(
        '--trial-csv',
        type=str,
        help='Path to trials.csv with trial metadata and center positions'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/fixations',
        help='Output directory for fixation data (default: outputs/fixations)'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.asc or not args.trial_csv:
        print("ERROR: Both --asc and --trial-csv are required")
        parser.print_help()
        sys.exit(1)

    asc_path = Path(args.asc)
    trial_csv_path = Path(args.trial_csv)
    output_dir = Path(args.output_dir)

    if not asc_path.exists():
        print(f"ERROR: ASC file not found: {asc_path}")
        sys.exit(1)

    if not trial_csv_path.exists():
        print(f"ERROR: Trial CSV not found: {trial_csv_path}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract session ID from path for output naming
    session_id = asc_path.parent.parent.name  # e.g., session_20260115_103203

    print(f"\n{'='*80}")
    print(f"FIXATION EXTRACTION PIPELINE")
    print(f"{'='*80}\n")

    # Step 1: Parse ASC file
    trials = parse_asc_file(asc_path)

    # Step 2: Merge trial metadata (center positions)
    trials = merge_trial_metadata(trials, trial_csv_path)

    # Step 3: Extract fixations for each trial
    all_fixations = []
    all_summaries = []

    for trial_uid, trial in trials.items():
        # Extract fixations 1-4 (long format)
        fix_df = extract_fixations_for_trial(trial)
        all_fixations.append(fix_df)

        # Create summary row (wide format)
        summary = create_summary_row(trial, fix_df)
        all_summaries.append(summary)

    # Combine all trials
    fixations_long = pd.concat(all_fixations, ignore_index=True)
    fixations_summary = pd.DataFrame(all_summaries)

    # Step 4: Save outputs
    fixations_long_path = output_dir / f'{session_id}_fixations.csv'
    fixations_summary_path = output_dir / f'{session_id}_fixations_summary.csv'
    quality_report_path = output_dir / f'{session_id}_quality_report.txt'

    fixations_long.to_csv(fixations_long_path, index=False)
    fixations_summary.to_csv(fixations_summary_path, index=False)

    print(f"\nOutputs saved:")
    print(f"  Long format (one row per fixation): {fixations_long_path}")
    print(f"  Summary format (one row per trial):  {fixations_summary_path}")

    # Step 5: Generate quality report
    generate_quality_report(trials, fixations_long, quality_report_path)

    print(f"\n{'='*80}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
