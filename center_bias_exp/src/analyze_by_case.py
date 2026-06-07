"""
Analysis of 2nd fixation center bias organized by polygon case type.

Analyzes center preferences separately for:
1. Baseline cases (symmetric, asymmetric, rectangle)
2. All-far spectrum cases (convex, intermediate, concave)
3. Pair separation cases (C1, C2, C3 - each with 3 polygons)
4. Isolated cases (iso_com, iso_bbc, iso_chc, iso_icc - each with 3 polygons)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set up plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 12)

# Input/output paths
INPUT_FILE = Path("analysis/second_fixation_partA/second_fixations_with_distances.csv")
OUTPUT_DIR = Path("analysis/by_case_partA")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define case groupings
CASE_GROUPS = {
    'baseline': {
        'cases': ['baseline_symmetric', 'baseline_asymmetric', 'baseline_rectangle'],
        'description': 'Baseline polygons (control conditions)'
    },
    'allfar_spectrum': {
        'cases': ['allfar_convex', 'allfar_intermediate', 'allfar_concave'],
        'description': 'All-far spectrum (convex -> intermediate -> concave)'
    },
    'pair_C1': {
        'cases': ['pair_C1_bbc_vs_chc_icc'],
        'description': 'Pair separation C1: BBC vs (CHC+ICC)'
    },
    'pair_C2': {
        'cases': ['pair_C2_chc_vs_bbc_icc'],
        'description': 'Pair separation C2: CHC vs (BBC+ICC)'
    },
    'pair_C3': {
        'cases': ['pair_C3_icc_vs_chc_bbc'],
        'description': 'Pair separation C3: ICC vs (CHC+BBC)'
    },
    'isolated_com': {
        'cases': ['iso_com'],
        'description': 'Isolated COM (3 polygons)'
    },
    'isolated_bbc': {
        'cases': ['iso_bbc'],
        'description': 'Isolated BBC (3 polygons)'
    },
    'isolated_chc': {
        'cases': ['iso_chc'],
        'description': 'Isolated CHC (3 polygons)'
    },
    'isolated_icc': {
        'cases': ['iso_icc'],
        'description': 'Isolated ICC (3 polygons)'
    }
}


def load_data():
    """Load the 2nd fixation data with distances."""
    print("="*70)
    print("LOADING DATA")
    print("="*70)

    df = pd.read_csv(INPUT_FILE)
    print(f"\nLoaded {len(df)} 2nd fixations")
    print(f"Participants: {sorted(df['participant_id'].unique())}")
    print(f"Unique polygon cases: {df['polygon_case'].nunique()}")

    return df


def analyze_by_case_group(df):
    """Analyze center preferences for each case group."""
    print("\n" + "="*70)
    print("CENTER PREFERENCE BY CASE GROUP")
    print("="*70)

    results = []

    for group_name, group_info in CASE_GROUPS.items():
        print(f"\n{group_name.upper().replace('_', ' ')}")
        print(f"  {group_info['description']}")
        print("-"*70)

        # Filter data for this case group
        case_mask = df['polygon_case'].isin(group_info['cases'])
        group_df = df[case_mask].copy()

        if len(group_df) == 0:
            print("  No data found!")
            continue

        print(f"  Total fixations: {len(group_df)}")
        print(f"  Participants: {group_df['participant_id'].nunique()}")
        print(f"  Cases included: {', '.join(group_info['cases'])}")

        # Count closest center preferences
        closest_counts = group_df['closest_center'].value_counts()
        print(f"\n  Closest center distribution:")
        for center, count in closest_counts.items():
            pct = count / len(group_df) * 100
            print(f"    {center.upper():3s}: {count:4d} ({pct:5.1f}%)")

        # Mean distances to each center type
        print(f"\n  Mean distance to each center:")
        for center_type in ['com', 'bbc', 'chc', 'icc']:
            col = f'dist_to_{center_type}'
            if col in group_df.columns:
                mean_dist = group_df[col].mean()
                std_dist = group_df[col].std()
                print(f"    {center_type.upper()}: M={mean_dist:6.1f}px (SD={std_dist:6.1f}px)")

        # Statistical test: Are distances to different centers significantly different?
        distances = []
        labels = []
        for center_type in ['com', 'bbc', 'chc', 'icc']:
            col = f'dist_to_{center_type}'
            if col in group_df.columns:
                distances.append(group_df[col].dropna().values)
                labels.append(center_type.upper())

        if len(distances) >= 2:
            f_stat, p_value = stats.f_oneway(*distances)
            print(f"\n  One-way ANOVA (distance to centers):")
            print(f"    F({len(distances)-1}, {sum(len(d) for d in distances) - len(distances)}) = {f_stat:.3f}, p = {p_value:.4f}")
            if p_value < 0.05:
                print(f"    => Significant differences between center distances!")
            else:
                print(f"    => No significant differences")

        # Store results
        for center, count in closest_counts.items():
            results.append({
                'case_group': group_name,
                'description': group_info['description'],
                'closest_center': center,
                'n_fixations': count,
                'percentage': count / len(group_df) * 100,
                'total_fixations': len(group_df)
            })

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "case_group_summary.csv", index=False)
    print(f"\n\nSaved: {OUTPUT_DIR / 'case_group_summary.csv'}")

    return results_df


def analyze_individual_cases(df):
    """Detailed analysis for each individual polygon case."""
    print("\n" + "="*70)
    print("DETAILED ANALYSIS BY INDIVIDUAL CASE")
    print("="*70)

    results = []

    for case in sorted(df['polygon_case'].unique()):
        case_df = df[df['polygon_case'] == case].copy()

        print(f"\n{case}")
        print("-"*70)
        print(f"  Fixations: {len(case_df)}")

        # Closest center distribution
        closest_counts = case_df['closest_center'].value_counts()
        winner = closest_counts.idxmax() if len(closest_counts) > 0 else 'N/A'
        winner_pct = closest_counts.max() / len(case_df) * 100 if len(case_df) > 0 else 0

        print(f"  Winner: {winner.upper()} ({winner_pct:.1f}%)")
        print(f"  Distribution: ", end="")
        dist_str = ", ".join([f"{k.upper()}:{v}" for k, v in closest_counts.items()])
        print(dist_str)

        # Store results
        for center, count in closest_counts.items():
            results.append({
                'polygon_case': case,
                'closest_center': center,
                'n_fixations': count,
                'percentage': count / len(case_df) * 100,
                'total_fixations': len(case_df)
            })

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "individual_case_summary.csv", index=False)
    print(f"\n\nSaved: {OUTPUT_DIR / 'individual_case_summary.csv'}")

    return results_df


def plot_case_group_analysis(df, case_results):
    """Create comprehensive visualizations by case group."""
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)

    # Figure 1: Closest center distribution by case group
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    axes = axes.flatten()

    for idx, (group_name, group_info) in enumerate(CASE_GROUPS.items()):
        ax = axes[idx]

        # Filter data
        case_mask = df['polygon_case'].isin(group_info['cases'])
        group_df = df[case_mask].copy()

        if len(group_df) == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(group_name.replace('_', ' ').title())
            ax.axis('off')
            continue

        # Count closest centers
        closest_counts = group_df['closest_center'].value_counts()

        # Plot bar chart
        colors = {'com': '#e74c3c', 'bbc': '#3498db', 'chc': '#2ecc71', 'icc': '#9b59b6'}
        centers = ['com', 'bbc', 'chc', 'icc']
        counts = [closest_counts.get(c, 0) for c in centers]

        bars = ax.bar(range(len(centers)), counts,
                      color=[colors[c] for c in centers], alpha=0.8, edgecolor='black')

        # Add percentage labels
        for i, (center, count) in enumerate(zip(centers, counts)):
            if count > 0:
                pct = count / len(group_df) * 100
                ax.text(i, count + max(counts)*0.02, f'{pct:.1f}%',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_xticks(range(len(centers)))
        ax.set_xticklabels([c.upper() for c in centers])
        ax.set_ylabel('Number of Fixations')
        ax.set_title(f"{group_name.replace('_', ' ').title()}\n(n={len(group_df)})",
                    fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

    # Remove unused subplots
    for idx in range(len(CASE_GROUPS), len(axes)):
        fig.delaxes(axes[idx])

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "case_group_distribution.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'case_group_distribution.png'}")
    plt.close()

    # Figure 2: Distance distributions by case group
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    axes = axes.flatten()

    for idx, (group_name, group_info) in enumerate(CASE_GROUPS.items()):
        ax = axes[idx]

        # Filter data
        case_mask = df['polygon_case'].isin(group_info['cases'])
        group_df = df[case_mask].copy()

        if len(group_df) == 0:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(group_name.replace('_', ' ').title())
            ax.axis('off')
            continue

        # Prepare distance data
        distance_data = []
        for center_type in ['com', 'bbc', 'chc', 'icc']:
            col = f'dist_to_{center_type}'
            if col in group_df.columns:
                distances = group_df[col].dropna().values
                distance_data.append(distances)
            else:
                distance_data.append(np.array([]))

        # Violin plot
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
        parts = ax.violinplot(distance_data, positions=range(4),
                             showmeans=True, showmedians=True)

        for pc, color in zip(parts['bodies'], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.6)

        ax.set_xticks(range(4))
        ax.set_xticklabels(['COM', 'BBC', 'CHC', 'ICC'])
        ax.set_ylabel('Distance (px)')
        ax.set_title(f"{group_name.replace('_', ' ').title()}",
                    fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

    # Remove unused subplots
    for idx in range(len(CASE_GROUPS), len(axes)):
        fig.delaxes(axes[idx])

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "case_group_distances.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'case_group_distances.png'}")
    plt.close()

    # Figure 3: Summary heatmap
    pivot_data = case_results.pivot_table(
        index='case_group',
        columns='closest_center',
        values='percentage',
        fill_value=0
    )

    # Reorder columns
    center_order = ['com', 'bbc', 'chc', 'icc']
    pivot_data = pivot_data[[c for c in center_order if c in pivot_data.columns]]

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='RdYlGn',
                cbar_kws={'label': 'Percentage (%)'}, ax=ax,
                vmin=0, vmax=100, linewidths=0.5, linecolor='black')

    ax.set_title('Center Preference by Case Group (%)', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Closest Center', fontsize=12, fontweight='bold')
    ax.set_ylabel('Case Group', fontsize=12, fontweight='bold')

    # Improve y-axis labels
    yticklabels = [label.get_text().replace('_', ' ').title() for label in ax.get_yticklabels()]
    ax.set_yticklabels(yticklabels, rotation=0)

    # Improve x-axis labels
    ax.set_xticklabels([label.get_text().upper() for label in ax.get_xticklabels()], rotation=0)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "case_group_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'case_group_heatmap.png'}")
    plt.close()


def generate_summary_report(df, case_results, individual_results):
    """Generate a text summary report."""
    print("\n" + "="*70)
    print("GENERATING SUMMARY REPORT")
    print("="*70)

    report_lines = []
    report_lines.append("="*70)
    report_lines.append("CENTER BIAS ANALYSIS BY POLYGON CASE")
    report_lines.append("="*70)
    report_lines.append(f"\nTotal 2nd fixations analyzed: {len(df)}")
    report_lines.append(f"Participants: {', '.join(sorted(df['participant_id'].unique()))}")
    report_lines.append(f"Unique polygon cases: {df['polygon_case'].nunique()}")

    report_lines.append("\n" + "="*70)
    report_lines.append("KEY FINDINGS BY CASE GROUP")
    report_lines.append("="*70)

    for group_name, group_info in CASE_GROUPS.items():
        case_mask = df['polygon_case'].isin(group_info['cases'])
        group_df = df[case_mask].copy()

        if len(group_df) == 0:
            continue

        report_lines.append(f"\n{group_name.upper().replace('_', ' ')}")
        report_lines.append(f"  Description: {group_info['description']}")
        report_lines.append(f"  Total fixations: {len(group_df)}")

        closest_counts = group_df['closest_center'].value_counts()
        winner = closest_counts.idxmax()
        winner_pct = closest_counts.max() / len(group_df) * 100

        report_lines.append(f"  WINNER: {winner.upper()} ({winner_pct:.1f}%)")
        report_lines.append(f"  Distribution:")
        for center, count in closest_counts.items():
            pct = count / len(group_df) * 100
            report_lines.append(f"    {center.upper():3s}: {count:4d} ({pct:5.1f}%)")

    report_lines.append("\n" + "="*70)
    report_lines.append("INTERPRETATION")
    report_lines.append("="*70)

    # Baseline analysis
    baseline_mask = df['polygon_case'].str.contains('baseline')
    baseline_df = df[baseline_mask]
    if len(baseline_df) > 0:
        baseline_winner = baseline_df['closest_center'].value_counts().idxmax()
        report_lines.append(f"\nBaseline (control): {baseline_winner.upper()} preference")

    # Isolated cases
    report_lines.append(f"\nIsolated cases (testing specific center types):")
    for iso_type in ['com', 'bbc', 'chc', 'icc']:
        iso_mask = df['polygon_case'] == f'iso_{iso_type}'
        iso_df = df[iso_mask]
        if len(iso_df) > 0:
            iso_winner = iso_df['closest_center'].value_counts().idxmax()
            iso_pct = iso_df['closest_center'].value_counts().max() / len(iso_df) * 100
            report_lines.append(f"  iso_{iso_type}: {iso_winner.upper()} preference ({iso_pct:.1f}%)")

    # Pair separation
    report_lines.append(f"\nPair separation cases (competing center types):")
    for pair_type in ['C1', 'C2', 'C3']:
        pair_mask = df['polygon_case'].str.contains(f'pair_{pair_type}')
        pair_df = df[pair_mask]
        if len(pair_df) > 0:
            pair_winner = pair_df['closest_center'].value_counts().idxmax()
            pair_pct = pair_df['closest_center'].value_counts().max() / len(pair_df) * 100
            report_lines.append(f"  pair_{pair_type}: {pair_winner.upper()} preference ({pair_pct:.1f}%)")

    report_lines.append("\n" + "="*70)

    # Write report
    report_text = "\n".join(report_lines)
    with open(OUTPUT_DIR / "summary_report.txt", 'w') as f:
        f.write(report_text)

    print(f"Saved: {OUTPUT_DIR / 'summary_report.txt'}")

    # Print to console
    print("\n" + report_text)


def main():
    """Main analysis pipeline."""
    print("="*70)
    print("CENTER BIAS ANALYSIS BY POLYGON CASE")
    print("="*70)

    # Load data
    df = load_data()

    # Analyze by case group
    case_results = analyze_by_case_group(df)

    # Analyze individual cases
    individual_results = analyze_individual_cases(df)

    # Generate visualizations
    plot_case_group_analysis(df, case_results)

    # Generate summary report
    generate_summary_report(df, case_results, individual_results)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nResults saved to: {OUTPUT_DIR.absolute()}")
    print("\nGenerated files:")
    print("  - case_group_summary.csv")
    print("  - individual_case_summary.csv")
    print("  - case_group_distribution.png")
    print("  - case_group_distances.png")
    print("  - case_group_heatmap.png")
    print("  - summary_report.txt")


if __name__ == "__main__":
    main()
