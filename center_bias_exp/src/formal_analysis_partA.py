"""
Formal analysis of Part A data following the preregistered analysis plan.

Based on: "Analysis Plan - CB experiment 2.md"

Participants: P03-P14 (12 participants)

Primary analyses:
1. Distance-based metrics: mean distance from Fixation 2 to each center type
2. Winner probability: frequency each center is closest
3. Robustness across case types (baseline, all-far, pair, isolated)
4. Replicate consistency within each case type
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from itertools import combinations

# Set up plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 12)

# Configuration
PARTICIPANTS = [f"P{i:02d}" for i in range(3, 13)]  # P03-P12 (will update to P14 later)
INPUT_FILE = Path("analysis/second_fixation_partA/second_fixations_with_distances.csv")
OUTPUT_DIR = Path("analysis/formal_partA")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Center types
CENTER_TYPES = ['com', 'bbc', 'chc', 'icc']
CENTER_LABELS = {'com': 'CoM', 'bbc': 'BBC', 'chc': 'CHC', 'icc': 'ICC'}

# Case type groupings (per analysis plan)
CASE_GROUPS = {
    'baseline': ['baseline_symmetric', 'baseline_asymmetric', 'baseline_rectangle'],
    'allfar': ['allfar_convex', 'allfar_intermediate', 'allfar_concave'],
    'pair': ['pair_C1_bbc_vs_chc_icc', 'pair_C2_chc_vs_bbc_icc', 'pair_C3_icc_vs_chc_bbc'],
    'isolated': ['iso_com', 'iso_bbc', 'iso_chc', 'iso_icc']
}


def load_and_prepare_data():
    """Load 2nd fixation data and prepare for analysis."""
    print("="*80)
    print("FORMAL ANALYSIS - PART A (Following Preregistered Plan)")
    print("="*80)

    # Check if we need to regenerate data with P13-P14
    if not INPUT_FILE.exists():
        print(f"\nERROR: Input file not found: {INPUT_FILE}")
        print("Please run analyze_second_fixation.py first to extract fixation data.")
        return None

    df = pd.read_csv(INPUT_FILE)

    # Filter to include only P03-P14
    df = df[df['participant_id'].isin(PARTICIPANTS)].copy()

    print(f"\nData loaded: {len(df)} fixations")
    print(f"Participants: {sorted(df['participant_id'].unique())}")
    print(f"Expected: {PARTICIPANTS}")

    missing_participants = set(PARTICIPANTS) - set(df['participant_id'].unique())
    if missing_participants:
        print(f"\nWARNING: Missing participants: {sorted(missing_participants)}")
        print("Please ensure all participants have completed Part A and run analyze_second_fixation.py")

    # Add case_type grouping column
    def get_case_type(polygon_case):
        for case_type, cases in CASE_GROUPS.items():
            if polygon_case in cases:
                return case_type
        return 'unknown'

    df['case_type'] = df['polygon_case'].apply(get_case_type)

    # Calculate winner margin (distance between 2nd best and best)
    distances_cols = [f'dist_to_{c}' for c in CENTER_TYPES]

    def calc_winner_margin(row):
        distances = [row[f'dist_to_{c}'] for c in CENTER_TYPES]
        sorted_dists = sorted(distances)
        return sorted_dists[1] - sorted_dists[0]  # 2nd - 1st

    df['winner_margin'] = df.apply(calc_winner_margin, axis=1)

    print(f"\nCase type distribution:")
    for case_type in ['baseline', 'allfar', 'pair', 'isolated']:
        count = (df['case_type'] == case_type).sum()
        print(f"  {case_type:10s}: {count:4d} trials")

    return df


def section_1_data_quality(df):
    """Section 1: Data quality and trial inclusion."""
    print("\n" + "="*80)
    print("1. DATA QUALITY AND TRIAL INCLUSION")
    print("="*80)

    # Per participant summary
    participant_summary = []
    for pid in sorted(df['participant_id'].unique()):
        pid_df = df[df['participant_id'] == pid]
        participant_summary.append({
            'participant_id': pid,
            'n_valid_trials': len(pid_df),
            'n_baseline': (pid_df['case_type'] == 'baseline').sum(),
            'n_allfar': (pid_df['case_type'] == 'allfar').sum(),
            'n_pair': (pid_df['case_type'] == 'pair').sum(),
            'n_isolated': (pid_df['case_type'] == 'isolated').sum()
        })

    summary_df = pd.DataFrame(participant_summary)
    summary_df.to_csv(OUTPUT_DIR / "data_quality.csv", index=False)

    print(f"\nValid trials with Fixation 2: {len(df)}")
    print(f"\nPer-participant summary:")
    print(summary_df.to_string(index=False))

    return summary_df


def section_2_primary_endpoint_distances(df):
    """Section 2: Primary endpoint - distance-based analysis."""
    print("\n" + "="*80)
    print("2. PRIMARY ENDPOINT: DISTANCE-BASED ANALYSIS")
    print("="*80)

    # Overall mean distances
    print("\n2.1 OVERALL MEAN DISTANCES (degrees)")
    print("-"*80)

    distance_summary = []
    for center in CENTER_TYPES:
        dist_col = f'dist_to_{center}'
        distances = df[dist_col].dropna()

        mean_dist = distances.mean()
        std_dist = distances.std()
        sem_dist = distances.sem()
        ci_lower = mean_dist - 1.96 * sem_dist
        ci_upper = mean_dist + 1.96 * sem_dist

        distance_summary.append({
            'center': CENTER_LABELS[center],
            'mean_distance_px': mean_dist,
            'std_distance_px': std_dist,
            'sem_distance_px': sem_dist,
            'ci_lower_px': ci_lower,
            'ci_upper_px': ci_upper,
            'n_trials': len(distances)
        })

        print(f"  {CENTER_LABELS[center]:4s}: M = {mean_dist:6.1f}px, "
              f"SD = {std_dist:6.1f}px, 95% CI [{ci_lower:6.1f}, {ci_upper:6.1f}]")

    distance_df = pd.DataFrame(distance_summary)
    distance_df.to_csv(OUTPUT_DIR / "overall_distances.csv", index=False)

    # One-way ANOVA: Are distances significantly different across centers?
    print("\n2.2 OMNIBUS TEST: One-way ANOVA on distances")
    print("-"*80)

    distance_groups = [df[f'dist_to_{c}'].dropna().values for c in CENTER_TYPES]
    f_stat, p_value = stats.f_oneway(*distance_groups)

    print(f"  F({len(CENTER_TYPES)-1}, {sum(len(g) for g in distance_groups) - len(CENTER_TYPES)}) = {f_stat:.3f}")
    print(f"  p = {p_value:.6f}")

    if p_value < 0.05:
        print("  => Significant differences in mean distance across centers (p < 0.05)")
    else:
        print("  => No significant differences in mean distance across centers (p >= 0.05)")

    # Pairwise comparisons with Holm-Bonferroni correction
    print("\n2.3 PAIRWISE COMPARISONS (Holm-Bonferroni corrected)")
    print("-"*80)

    pairwise_results = []
    p_values = []

    for c1, c2 in combinations(CENTER_TYPES, 2):
        dist1 = df[f'dist_to_{c1}'].dropna().values
        dist2 = df[f'dist_to_{c2}'].dropna().values

        t_stat, p_val = stats.ttest_rel(dist1, dist2)
        mean_diff = dist1.mean() - dist2.mean()

        pairwise_results.append({
            'comparison': f'{CENTER_LABELS[c1]} vs {CENTER_LABELS[c2]}',
            'mean_diff_px': mean_diff,
            't_statistic': t_stat,
            'p_value_uncorrected': p_val
        })
        p_values.append(p_val)

    # Holm-Bonferroni correction
    sorted_indices = np.argsort(p_values)
    n_tests = len(p_values)

    for idx in sorted_indices:
        rank = np.where(sorted_indices == idx)[0][0] + 1
        corrected_alpha = 0.05 / (n_tests - rank + 1)
        pairwise_results[idx]['corrected_alpha'] = corrected_alpha
        pairwise_results[idx]['significant_holm'] = p_values[idx] < corrected_alpha

    pairwise_df = pd.DataFrame(pairwise_results)
    pairwise_df.to_csv(OUTPUT_DIR / "pairwise_comparisons.csv", index=False)

    print("\n" + pairwise_df.to_string(index=False))

    # Identify winner
    winner_center = distance_df.loc[distance_df['mean_distance_px'].idxmin(), 'center']
    print(f"\n  => PRIMARY WINNER: {winner_center} (lowest mean distance)")

    return distance_df, pairwise_df, winner_center


def section_3_winner_probability(df):
    """Section 3: Winner probability (categorical endpoint)."""
    print("\n" + "="*80)
    print("3. WINNER PROBABILITY (CATEGORICAL ENDPOINT)")
    print("="*80)

    # Overall winner distribution
    print("\n3.1 OVERALL WINNER DISTRIBUTION")
    print("-"*80)

    winner_counts = df['closest_center'].value_counts()
    total_trials = len(df)

    winner_summary = []
    for center in CENTER_TYPES:
        count = winner_counts.get(center, 0)
        prob = count / total_trials

        # Binomial confidence interval (Wilson score)
        from scipy.stats import binom
        ci_lower, ci_upper = binom.interval(0.95, total_trials, prob)
        ci_lower_prob = ci_lower / total_trials
        ci_upper_prob = ci_upper / total_trials

        winner_summary.append({
            'center': CENTER_LABELS[center],
            'n_wins': count,
            'win_probability': prob,
            'ci_lower': ci_lower_prob,
            'ci_upper': ci_upper_prob
        })

        print(f"  {CENTER_LABELS[center]:4s}: {count:4d} wins ({prob*100:5.1f}%), "
              f"95% CI [{ci_lower_prob*100:5.1f}%, {ci_upper_prob*100:5.1f}%]")

    winner_df = pd.DataFrame(winner_summary)
    winner_df.to_csv(OUTPUT_DIR / "winner_probabilities.csv", index=False)

    # Chi-square test: Are win probabilities significantly different?
    print("\n3.2 CHI-SQUARE TEST: Equal win probabilities?")
    print("-"*80)

    observed = [winner_counts.get(c, 0) for c in CENTER_TYPES]
    chi2_stat, chi2_p = stats.chisquare(observed)

    print(f"  Chi-square statistic = {chi2_stat:.3f}")
    print(f"  p = {chi2_p:.6f}")

    if chi2_p < 0.05:
        print("  => Win probabilities are significantly different (p < 0.05)")
    else:
        print("  => Win probabilities are not significantly different (p >= 0.05)")

    categorical_winner = winner_df.loc[winner_df['win_probability'].idxmax(), 'center']
    print(f"\n  => CATEGORICAL WINNER: {categorical_winner} (highest win probability)")

    return winner_df, categorical_winner


def section_4_robustness_case_types(df):
    """Section 4: Robustness across case types."""
    print("\n" + "="*80)
    print("4. ROBUSTNESS ACROSS CASE TYPES")
    print("="*80)

    case_results = []

    for case_type in ['baseline', 'allfar', 'pair', 'isolated']:
        case_df = df[df['case_type'] == case_type].copy()

        if len(case_df) == 0:
            continue

        print(f"\n4.{list(['baseline', 'allfar', 'pair', 'isolated']).index(case_type) + 1} CASE TYPE: {case_type.upper()}")
        print("-"*80)
        print(f"  N trials = {len(case_df)}")

        # Winner distribution
        winner_counts = case_df['closest_center'].value_counts()
        winner = winner_counts.idxmax()
        winner_pct = winner_counts.max() / len(case_df) * 100

        print(f"  Winner: {CENTER_LABELS[winner]} ({winner_pct:.1f}%)")
        print(f"  Distribution:")
        for center in CENTER_TYPES:
            count = winner_counts.get(center, 0)
            pct = count / len(case_df) * 100
            print(f"    {CENTER_LABELS[center]:4s}: {count:4d} ({pct:5.1f}%)")

        # Mean distances
        print(f"  Mean distances:")
        for center in CENTER_TYPES:
            mean_dist = case_df[f'dist_to_{center}'].mean()
            std_dist = case_df[f'dist_to_{center}'].std()
            print(f"    {CENTER_LABELS[center]:4s}: M = {mean_dist:6.1f}px (SD = {std_dist:6.1f}px)")

        # Store results
        for center in CENTER_TYPES:
            case_results.append({
                'case_type': case_type,
                'center': CENTER_LABELS[center],
                'mean_distance_px': case_df[f'dist_to_{center}'].mean(),
                'n_wins': winner_counts.get(center, 0),
                'win_probability': winner_counts.get(center, 0) / len(case_df)
            })

    case_results_df = pd.DataFrame(case_results)
    case_results_df.to_csv(OUTPUT_DIR / "robustness_case_types.csv", index=False)

    print("\n4.5 SUMMARY: Winner consistency across case types")
    print("-"*80)

    for case_type in ['baseline', 'allfar', 'pair', 'isolated']:
        case_subset = case_results_df[case_results_df['case_type'] == case_type]
        if len(case_subset) > 0:
            winner_row = case_subset.loc[case_subset['win_probability'].idxmax()]
            print(f"  {case_type:10s}: {winner_row['center']} ({winner_row['win_probability']*100:.1f}%)")

    return case_results_df


def section_5_replicate_consistency(df):
    """Section 5: Replicate consistency within case types."""
    print("\n" + "="*80)
    print("5. REPLICATE CONSISTENCY (Shape-Specific Artifact Control)")
    print("="*80)

    replicate_results = []

    # Group by polygon_case (each has 3 replicates except baselines)
    for polygon_case in sorted(df['polygon_case'].unique()):
        case_df = df[df['polygon_case'] == polygon_case].copy()

        if len(case_df) == 0:
            continue

        winner_counts = case_df['closest_center'].value_counts()
        winner = winner_counts.idxmax() if len(winner_counts) > 0 else 'N/A'
        winner_pct = winner_counts.max() / len(case_df) * 100 if len(case_df) > 0 else 0

        replicate_results.append({
            'polygon_case': polygon_case,
            'n_trials': len(case_df),
            'winner': CENTER_LABELS.get(winner, winner),
            'winner_percentage': winner_pct,
            'n_com': winner_counts.get('com', 0),
            'n_bbc': winner_counts.get('bbc', 0),
            'n_chc': winner_counts.get('chc', 0),
            'n_icc': winner_counts.get('icc', 0)
        })

    replicate_df = pd.DataFrame(replicate_results)
    replicate_df.to_csv(OUTPUT_DIR / "replicate_consistency.csv", index=False)

    print("\n" + replicate_df.to_string(index=False))

    return replicate_df


def generate_summary_report(distance_df, winner_df, case_results_df, replicate_df,
                           primary_winner, categorical_winner):
    """Generate comprehensive summary report."""
    print("\n" + "="*80)
    print("SUMMARY AND CONCLUSIONS")
    print("="*80)

    lines = []
    lines.append("="*80)
    lines.append("FORMAL ANALYSIS - PART A RESULTS")
    lines.append("="*80)
    lines.append("")
    lines.append(f"Participants: P03-P14 (12 participants)")
    lines.append(f"Analysis follows: 'Analysis Plan - CB experiment 2.md'")
    lines.append("")

    lines.append("PRIMARY RESULTS")
    lines.append("-"*80)
    lines.append(f"Distance-based winner: {primary_winner}")
    lines.append(f"Categorical winner:    {categorical_winner}")
    lines.append("")

    lines.append("Overall win probabilities:")
    for _, row in winner_df.iterrows():
        lines.append(f"  {row['center']:4s}: {row['win_probability']*100:5.1f}% "
                    f"({row['n_wins']} wins)")
    lines.append("")

    lines.append("Overall mean distances:")
    for _, row in distance_df.iterrows():
        lines.append(f"  {row['center']:4s}: M = {row['mean_distance_px']:6.1f}px "
                    f"(95% CI [{row['ci_lower_px']:6.1f}, {row['ci_upper_px']:6.1f}])")
    lines.append("")

    lines.append("ROBUSTNESS ACROSS CASE TYPES")
    lines.append("-"*80)
    for case_type in ['baseline', 'allfar', 'pair', 'isolated']:
        case_subset = case_results_df[case_results_df['case_type'] == case_type]
        if len(case_subset) > 0:
            winner_row = case_subset.loc[case_subset['win_probability'].idxmax()]
            lines.append(f"  {case_type.capitalize():10s}: {winner_row['center']} wins "
                        f"({winner_row['win_probability']*100:.1f}%)")
    lines.append("")

    lines.append("="*80)

    report_text = "\n".join(lines)

    with open(OUTPUT_DIR / "summary_report.txt", 'w') as f:
        f.write(report_text)

    print("\n" + report_text)

    print(f"\nAll results saved to: {OUTPUT_DIR.absolute()}")


def main():
    """Main analysis pipeline following formal analysis plan."""

    # Load data
    df = load_and_prepare_data()
    if df is None:
        return

    # Section 1: Data quality
    quality_df = section_1_data_quality(df)

    # Section 2: Distance-based primary endpoint
    distance_df, pairwise_df, primary_winner = section_2_primary_endpoint_distances(df)

    # Section 3: Winner probability categorical endpoint
    winner_df, categorical_winner = section_3_winner_probability(df)

    # Section 4: Robustness across case types
    case_results_df = section_4_robustness_case_types(df)

    # Section 5: Replicate consistency
    replicate_df = section_5_replicate_consistency(df)

    # Generate summary report
    generate_summary_report(distance_df, winner_df, case_results_df, replicate_df,
                           primary_winner, categorical_winner)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print("  - data_quality.csv")
    print("  - overall_distances.csv")
    print("  - pairwise_comparisons.csv")
    print("  - winner_probabilities.csv")
    print("  - robustness_case_types.csv")
    print("  - replicate_consistency.csv")
    print("  - summary_report.txt")


if __name__ == "__main__":
    main()
