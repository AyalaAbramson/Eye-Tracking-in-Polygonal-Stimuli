"""
Data Quality Validation Script for Center Bias Experiment

This script validates pilot data quality by checking:
1. Polygon clipping (especially allfar_concave)
2. Calibration/validation quality
3. Fixation gate success rates
4. Trial completion rates
5. Temporal patterns (fatigue effects)

Usage:
    # Validate all pilot data
    python src/validate_data_quality.py --data-root data/raw

    # Validate specific participant
    python src/validate_data_quality.py --participant P01 --part A

    # Generate full report with recommendations
    python src/validate_data_quality.py --data-root data/raw --full-report

Output:
    - data_quality_report.txt: Summary of all quality checks
    - participant_quality.csv: Per-participant metrics
    - problematic_trials.csv: Trials flagged for exclusion
    - recommendations.txt: Specific actions to take

Author: Eye Tracking Lab
Date: 2026-01-17
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import warnings

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')


class DataQualityValidator:
    """Validates data quality for eye tracking experiment."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.participants = []
        self.quality_issues = []
        self.all_trial_data = []

    def discover_sessions(self) -> List[Dict]:
        """
        Discover all session directories in data_root.

        Returns list of dicts with participant, part, session_path.
        """
        sessions = []

        participant_dirs = sorted(self.data_root.glob('participant_*'))

        for p_dir in participant_dirs:
            participant_id = p_dir.name.replace('participant_', '')

            for part in ['A', 'B']:
                part_dir = p_dir / f'part_{part}'
                if not part_dir.exists():
                    continue

                session_dirs = sorted(part_dir.glob('session_*'))
                for s_dir in session_dirs:
                    trial_csv = s_dir / 'logs_trial' / 'trials.csv'
                    if trial_csv.exists():
                        sessions.append({
                            'participant_id': participant_id,
                            'part': part,
                            'session_path': s_dir,
                            'trial_csv': trial_csv
                        })

        print(f"Discovered {len(sessions)} sessions from {len(set(s['participant_id'] for s in sessions))} participants")
        return sessions

    def check_fixation_success_rate(self, df: pd.DataFrame, session_info: Dict) -> Dict:
        """
        Check fixation gate success rate and timing.

        Returns dict with metrics and issues.
        """
        issues = []
        metrics = {}

        total_trials = len(df)
        if total_trials == 0:
            return {'issues': ['No trials found'], 'metrics': {}}

        # Fixation achievement rate (use drift_check_passed as proxy for fixation success)
        if 'fixation_achieved' in df.columns:
            fixation_achieved = df['fixation_achieved'].sum()
        elif 'drift_check_passed' in df.columns:
            fixation_achieved = df['drift_check_passed'].sum()
        else:
            fixation_achieved = (~df.get('aborted', pd.Series([False]*total_trials))).sum()

        success_rate = fixation_achieved / total_trials * 100
        metrics['fixation_success_rate'] = success_rate

        if success_rate < 85:
            issues.append(f"LOW fixation success rate: {success_rate:.1f}% (threshold: 85%)")
        elif success_rate < 95:
            issues.append(f"MODERATE fixation success rate: {success_rate:.1f}% (target: >95%)")

        # Fixation timing (use drift_total_time_s if available)
        time_col = None
        if 'fixation_total_time_s' in df.columns:
            time_col = 'fixation_total_time_s'
        elif 'drift_total_time_s' in df.columns:
            time_col = 'drift_total_time_s'

        if time_col:
            metrics['mean_fixation_time_s'] = df[time_col].mean()
            metrics['median_fixation_time_s'] = df[time_col].median()
            metrics['max_fixation_time_s'] = df[time_col].max()
            metrics['p95_fixation_time_s'] = df[time_col].quantile(0.95)
        else:
            metrics['mean_fixation_time_s'] = None
            metrics['median_fixation_time_s'] = None
            metrics['max_fixation_time_s'] = None
            metrics['p95_fixation_time_s'] = None

        if metrics['mean_fixation_time_s'] and metrics['mean_fixation_time_s'] > 3.0:
            issues.append(f"HIGH mean fixation time: {metrics['mean_fixation_time_s']:.2f}s (threshold: 3s)")

        if metrics['max_fixation_time_s'] and metrics['max_fixation_time_s'] > 30.0:
            issues.append(f"VERY HIGH max fixation time: {metrics['max_fixation_time_s']:.1f}s - check for calibration issues")

        # Multiple attempts (use drift_attempts if fixation_attempts not available)
        attempt_col = None
        if 'fixation_attempts' in df.columns:
            attempt_col = 'fixation_attempts'
        elif 'drift_attempts' in df.columns:
            attempt_col = 'drift_attempts'

        if attempt_col:
            high_attempt_trials = df[df[attempt_col] > 3]
            metrics['n_high_attempt_trials'] = len(high_attempt_trials)
            metrics['pct_high_attempt_trials'] = len(high_attempt_trials) / total_trials * 100

            if len(high_attempt_trials) > total_trials * 0.10:
                issues.append(f"HIGH proportion of multi-attempt trials: {len(high_attempt_trials)} ({metrics['pct_high_attempt_trials']:.1f}%)")

                # Check if clustered at specific cue positions
                if 'cue_pos_id' in df.columns:
                    problem_cues = high_attempt_trials['cue_pos_id'].value_counts().head(3)
                    issues.append(f"  Problem cue positions: {dict(problem_cues)}")
        else:
            metrics['n_high_attempt_trials'] = None
            metrics['pct_high_attempt_trials'] = None

        # Temporal pattern (fatigue)
        if 'mini_block' in df.columns:
            # Use the correct success column
            success_col = None
            if 'fixation_achieved' in df.columns:
                success_col = 'fixation_achieved'
            elif 'drift_check_passed' in df.columns:
                success_col = 'drift_check_passed'

            if success_col:
                # Convert to numeric if boolean
                success_series = df[success_col].astype(float)
                block_success = df.groupby('mini_block')[success_col].apply(lambda x: x.astype(float).mean())
                first_block_success = float(block_success.iloc[0]) if len(block_success) > 0 else 1.0
                last_block_success = float(block_success.iloc[-1]) if len(block_success) > 0 else 1.0

                metrics['first_block_success_rate'] = first_block_success * 100
                metrics['last_block_success_rate'] = last_block_success * 100
                metrics['success_rate_decline'] = (first_block_success - last_block_success) * 100

                if metrics['success_rate_decline'] > 10:
                    issues.append(f"FATIGUE EFFECT: Success rate declined {metrics['success_rate_decline']:.1f}% from first to last block")
            else:
                metrics['first_block_success_rate'] = None
                metrics['last_block_success_rate'] = None
                metrics['success_rate_decline'] = None
        else:
            metrics['first_block_success_rate'] = None
            metrics['last_block_success_rate'] = None
            metrics['success_rate_decline'] = None

        return {'issues': issues, 'metrics': metrics}

    def check_polygon_clipping(self, df: pd.DataFrame, session_info: Dict) -> Dict:
        """
        Check for potential polygon clipping issues.

        Since we can't visually inspect, we check:
        - Trials with specific polygons (allfar_concave, etc.)
        - Geometry data validity
        """
        issues = []
        metrics = {}

        # Check for allfar polygons
        critical_polygons = ['allfar_concave_01', 'allfar_convex_01', 'allfar_intermediate_01']

        for poly_id in critical_polygons:
            poly_trials = df[df['polygon_id'] == poly_id]
            metrics[f'n_trials_{poly_id}'] = len(poly_trials)

            if len(poly_trials) > 0:
                # Check if geometry data exists
                has_geometry = poly_trials['center_mass_x_px'].notna().sum()
                if has_geometry == 0:
                    issues.append(f"MISSING GEOMETRY for {poly_id} - cannot verify clipping")

        # Check for NaN values in center coordinates (indicates geometry issues)
        geometry_cols = [c for c in df.columns if c.startswith('center_') and c.endswith('_px')]
        if geometry_cols:
            nan_counts = df[geometry_cols].isna().sum()
            total_nan = nan_counts.sum()

            if total_nan > 0:
                issues.append(f"MISSING GEOMETRY DATA: {total_nan} NaN values across {len(nan_counts[nan_counts > 0])} columns")
                metrics['missing_geometry_count'] = int(total_nan)

        metrics['polygon_diversity'] = df['polygon_id'].nunique()

        return {'issues': issues, 'metrics': metrics}

    def check_trial_completion(self, df: pd.DataFrame, session_info: Dict) -> Dict:
        """Check trial completion and abort rates."""
        issues = []
        metrics = {}

        total_trials = len(df)

        # Aborted trials
        if 'aborted' in df.columns:
            aborted = df['aborted'].sum()
            abort_rate = aborted / total_trials * 100 if total_trials > 0 else 0

            metrics['n_aborted'] = aborted
            metrics['abort_rate'] = abort_rate

            if abort_rate > 5:
                issues.append(f"HIGH abort rate: {abort_rate:.1f}% ({aborted} trials)")

        # User aborts
        if 'user_abort' in df.columns:
            user_aborts = df['user_abort'].sum() if df['user_abort'].dtype != object else 0
            if user_aborts > 0:
                issues.append(f"USER ABORTS: {user_aborts} trials aborted by participant/experimenter")
                metrics['n_user_aborts'] = user_aborts

        # Check for expected trial count
        expected_trials = 351  # 9 blocks × 39 trials
        if total_trials < expected_trials * 0.9:
            issues.append(f"INCOMPLETE SESSION: Only {total_trials}/{expected_trials} trials ({total_trials/expected_trials*100:.1f}%)")
            metrics['completion_rate'] = total_trials / expected_trials * 100

        return {'issues': issues, 'metrics': metrics}

    def check_calibration_quality(self, df: pd.DataFrame, session_info: Dict) -> Dict:
        """
        Check calibration/validation quality from trial data.

        Note: Validation RMS/max error are logged per trial (from last calibration).
        """
        issues = []
        metrics = {}

        # Check if validation metrics were logged
        if 'validation_rms_before_trial' in df.columns:
            valid_rms = df['validation_rms_before_trial'].dropna()

            if len(valid_rms) == 0:
                issues.append("WARNING: No validation RMS values logged - cannot assess calibration quality")
                issues.append("  Recommendation: Manually check validation from EyeLink Host PC logs")
            else:
                metrics['mean_validation_rms'] = valid_rms.mean()
                metrics['max_validation_rms'] = valid_rms.max()
                metrics['n_validation_samples'] = len(valid_rms)

                # Check against thresholds
                if metrics['mean_validation_rms'] > 1.5:
                    issues.append(f"HIGH validation RMS: mean={metrics['mean_validation_rms']:.2f}° (threshold: 1.5°)")

                if metrics['max_validation_rms'] > 2.5:
                    issues.append(f"VERY HIGH max validation RMS: {metrics['max_validation_rms']:.2f}° (threshold: 2.5°)")

        if 'validation_max_err_before_trial' in df.columns:
            valid_max_err = df['validation_max_err_before_trial'].dropna()

            if len(valid_max_err) > 0:
                metrics['mean_validation_max_err'] = valid_max_err.mean()
                metrics['max_validation_max_err'] = valid_max_err.max()

        return {'issues': issues, 'metrics': metrics}

    def validate_session(self, session_info: Dict) -> Dict:
        """
        Run all quality checks on a single session.

        Returns dict with issues, metrics, and recommendations.
        """
        trial_csv = session_info['trial_csv']
        df = pd.read_csv(trial_csv)

        session_result = {
            'participant_id': session_info['participant_id'],
            'part': session_info['part'],
            'session_path': str(session_info['session_path']),
            'n_trials': len(df),
            'issues': [],
            'metrics': {},
            'severity': 'OK'
        }

        # Run all checks
        checks = [
            ('Fixation Success', self.check_fixation_success_rate),
            ('Polygon Clipping', self.check_polygon_clipping),
            ('Trial Completion', self.check_trial_completion),
            ('Calibration Quality', self.check_calibration_quality)
        ]

        for check_name, check_func in checks:
            result = check_func(df, session_info)
            session_result['issues'].extend([f"[{check_name}] {issue}" for issue in result['issues']])
            session_result['metrics'].update({f"{check_name.lower().replace(' ', '_')}_{k}": v
                                              for k, v in result['metrics'].items()})

        # Determine severity
        if any('LOW' in issue or 'HIGH' in issue or 'VERY' in issue for issue in session_result['issues']):
            session_result['severity'] = 'WARNING'
        if any('MISSING' in issue or 'INCOMPLETE' in issue for issue in session_result['issues']):
            session_result['severity'] = 'ERROR'

        # Store for later aggregation
        self.all_trial_data.append({
            'participant_id': session_info['participant_id'],
            'part': session_info['part'],
            'df': df
        })

        return session_result

    def generate_report(self, session_results: List[Dict], output_path: Path):
        """Generate comprehensive quality report."""

        report = f"""
{'='*100}
DATA QUALITY VALIDATION REPORT
Generated: {datetime.now().isoformat()}
{'='*100}

SUMMARY
-------
Total sessions validated: {len(session_results)}
Sessions with issues: {sum(1 for s in session_results if len(s['issues']) > 0)}
  - OK: {sum(1 for s in session_results if s['severity'] == 'OK')}
  - WARNING: {sum(1 for s in session_results if s['severity'] == 'WARNING')}
  - ERROR: {sum(1 for s in session_results if s['severity'] == 'ERROR')}

"""

        # Overall metrics
        all_trials = sum(s['n_trials'] for s in session_results)
        report += f"\nOVERALL STATISTICS\n"
        report += f"------------------\n"
        report += f"Total trials across all sessions: {all_trials}\n"

        # Aggregate fixation success
        if self.all_trial_data:
            all_dfs = [d['df'] for d in self.all_trial_data]
            combined_df = pd.concat(all_dfs, ignore_index=True)

            # Determine success column
            if 'fixation_achieved' in combined_df.columns:
                success_col = 'fixation_achieved'
            elif 'drift_check_passed' in combined_df.columns:
                success_col = 'drift_check_passed'
            else:
                success_col = None

            if success_col:
                overall_success = combined_df[success_col].astype(float).mean() * 100
                report += f"Overall fixation success rate: {overall_success:.1f}%\n"

            # Determine time column
            if 'fixation_total_time_s' in combined_df.columns:
                time_col = 'fixation_total_time_s'
            elif 'drift_total_time_s' in combined_df.columns:
                time_col = 'drift_total_time_s'
            else:
                time_col = None

            if time_col:
                report += f"Mean fixation time: {combined_df[time_col].mean():.2f}s\n"
                report += f"P95 fixation time: {combined_df[time_col].quantile(0.95):.2f}s\n"

        # Per-session details
        report += f"\n\nPER-SESSION DETAILS\n"
        report += f"{'='*100}\n"

        for i, session in enumerate(session_results, 1):
            report += f"\n[{i}] {session['participant_id']} Part {session['part']} - {session['severity']}\n"
            report += f"    Path: {session['session_path']}\n"
            report += f"    Trials: {session['n_trials']}\n"

            if session['issues']:
                report += f"    Issues ({len(session['issues'])}):\n"
                for issue in session['issues']:
                    report += f"      - {issue}\n"
            else:
                report += f"    No issues detected ✓\n"

        # Recommendations
        report += f"\n\n{'='*100}\n"
        report += f"RECOMMENDATIONS\n"
        report += f"{'='*100}\n\n"

        critical_sessions = [s for s in session_results if s['severity'] == 'ERROR']
        warning_sessions = [s for s in session_results if s['severity'] == 'WARNING']

        if critical_sessions:
            report += f"CRITICAL ({len(critical_sessions)} sessions):\n"
            for s in critical_sessions:
                report += f"  - {s['participant_id']} Part {s['part']}: "
                critical_issues = [i for i in s['issues'] if 'MISSING' in i or 'INCOMPLETE' in i]
                report += f"{'; '.join(critical_issues[:2])}\n"
            report += f"\n  ACTION: Review these sessions manually. May need exclusion or re-collection.\n\n"

        if warning_sessions:
            report += f"WARNINGS ({len(warning_sessions)} sessions):\n"
            for s in warning_sessions[:5]:  # Show first 5
                report += f"  - {s['participant_id']} Part {s['part']}: "
                warning_issues = [i for i in s['issues'] if 'WARNING' in i or 'HIGH' in i or 'LOW' in i]
                report += f"{warning_issues[0] if warning_issues else 'Multiple warnings'}\n"
            if len(warning_sessions) > 5:
                report += f"  ... and {len(warning_sessions) - 5} more\n"
            report += f"\n  ACTION: Review quality metrics. Consider exclusion criteria during analysis.\n\n"

        ok_sessions = [s for s in session_results if s['severity'] == 'OK']
        if ok_sessions:
            report += f"OK ({len(ok_sessions)} sessions):\n"
            report += f"  These sessions passed all quality checks and are ready for analysis.\n\n"

        # General recommendations
        report += f"\nGENERAL RECOMMENDATIONS FOR FUTURE DATA COLLECTION:\n"
        report += f"-" * 60 + "\n"

        if self.all_trial_data:
            # Check fixation time patterns
            if time_col and time_col in combined_df.columns:
                avg_fix_time = combined_df[time_col].mean()
                if avg_fix_time > 2.0:
                    report += f"1. Fixation gating is slow (avg={avg_fix_time:.2f}s):\n"
                    report += f"   -> Use drift_correction method instead of gaze_gate\n"
                    report += f"   -> Check calibration quality at start of each block\n\n"

            # Check for fatigue
            if 'mini_block' in combined_df.columns and success_col and success_col in combined_df.columns:
                block_success = combined_df.groupby('mini_block')[success_col].apply(lambda x: x.astype(float).mean())
                if len(block_success) >= 9:
                    decline = (float(block_success.iloc[0]) - float(block_success.iloc[-1])) * 100
                    if decline > 5:
                        report += f"2. Fatigue detected ({decline:.1f}% decline in success rate):\n"
                        report += f"   -> Consider shorter sessions or longer breaks\n"
                        report += f"   -> Monitor calibration drift more frequently\n\n"

        report += f"\n{'='*100}\n"
        report += f"END OF REPORT\n"
        report += f"{'='*100}\n"

        # Write report
        with open(output_path, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {output_path}")

    def export_participant_metrics(self, session_results: List[Dict], output_path: Path):
        """Export per-participant quality metrics as CSV."""

        rows = []
        for session in session_results:
            row = {
                'participant_id': session['participant_id'],
                'part': session['part'],
                'n_trials': session['n_trials'],
                'severity': session['severity'],
                'n_issues': len(session['issues'])
            }
            row.update(session['metrics'])
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        print(f"Participant metrics saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate data quality for center bias eye tracking experiment'
    )
    parser.add_argument(
        '--data-root',
        type=str,
        default='data/raw',
        help='Root directory containing participant data (default: data/raw)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/quality',
        help='Output directory for reports (default: outputs/quality)'
    )

    args = parser.parse_args()

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)

    if not data_root.exists():
        print(f"ERROR: Data root not found: {data_root}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*100}")
    print(f"DATA QUALITY VALIDATION")
    print(f"{'='*100}\n")
    print(f"Data root: {data_root}")
    print(f"Output dir: {output_dir}\n")

    # Initialize validator
    validator = DataQualityValidator(data_root)

    # Discover sessions
    sessions = validator.discover_sessions()

    if not sessions:
        print("ERROR: No sessions found. Check data_root path.")
        sys.exit(1)

    # Validate each session
    print(f"\nValidating {len(sessions)} sessions...\n")
    session_results = []

    for i, session_info in enumerate(sessions, 1):
        print(f"[{i}/{len(sessions)}] Validating {session_info['participant_id']} Part {session_info['part']}...", end=' ')
        result = validator.validate_session(session_info)
        session_results.append(result)
        print(f"{result['severity']}")

    # Generate reports
    print(f"\nGenerating reports...")
    report_path = output_dir / 'data_quality_report.txt'
    metrics_path = output_dir / 'participant_quality.csv'

    validator.generate_report(session_results, report_path)
    validator.export_participant_metrics(session_results, metrics_path)

    print(f"\n{'='*100}")
    print(f"VALIDATION COMPLETE")
    print(f"{'='*100}\n")


if __name__ == '__main__':
    main()
