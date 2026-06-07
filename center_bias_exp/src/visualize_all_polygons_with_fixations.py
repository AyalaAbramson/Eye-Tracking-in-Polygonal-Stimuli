"""
Visualize all 27 polygons with 2nd fixations and geometric centers.

Creates a comprehensive plot showing:
- Each polygon shape
- All 2nd fixations from all participants
- All 4 geometric centers (COM, BBC, CHC, ICC)
- Screen center for reference
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import json

# Configuration
FIXATIONS_FILE = Path("analysis/second_fixation_partA/second_fixations_with_distances.csv")
GEOMETRY_FILE = Path("manifests/polygon_geometry.csv")
POLYGONS_DIR = Path("data/raw/stimuli/polygons")
OUTPUT_DIR = Path("analysis/polygon_visualizations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Screen parameters
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
SCREEN_CENTER_X = SCREEN_WIDTH / 2
SCREEN_CENTER_Y = SCREEN_HEIGHT / 2

# Display parameters
# Polygons were displayed at 92% of screen height (aperture_scale_factor)
APERTURE_SCALE_FACTOR = int(SCREEN_HEIGHT * 0.92)  # 1987 pixels
# Canonical space is 500x500, centered at origin
# Scaling maps canonical coords to display size
DISPLAY_SCALE = APERTURE_SCALE_FACTOR / 500.0

# Center colors and markers
CENTER_COLORS = {
    'com': '#e74c3c',  # Red
    'bbc': '#3498db',  # Blue
    'chc': '#2ecc71',  # Green
    'icc': '#9b59b6'   # Purple
}

CENTER_LABELS = {
    'com': 'CoM',
    'bbc': 'BBC',
    'chc': 'CHC',
    'icc': 'ICC'
}


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


def plot_polygon_with_fixations(ax, polygon_id, polygon_case, fixations_df, geometry_row):
    """Plot a single polygon with its fixations and centers."""

    # Load polygon vertices
    vertices = load_polygon_vertices(polygon_id, polygon_case)

    if vertices is None:
        ax.text(0.5, 0.5, f'Polygon not found:\n{polygon_case}',
               ha='center', va='center', transform=ax.transAxes)
        ax.set_title(f'{polygon_case} (ID: {polygon_id})')
        return

    # Transform vertices to match experiment display
    # The experiment normalizes polygons so their MAX DIMENSION = aperture_scale_factor (1987px)
    # Step 1: Find current max dimension
    min_xy = vertices.min(axis=0)
    max_xy = vertices.max(axis=0)
    current_max_dim = max(max_xy[0] - min_xy[0], max_xy[1] - min_xy[1])

    # Step 2: Calculate normalize scale (same as experiment)
    normalize_scale = APERTURE_SCALE_FACTOR / current_max_dim if current_max_dim > 0 else 1.0

    # Step 3: Center at origin and scale
    center_xy = (min_xy + max_xy) / 2
    vertices_centered = vertices - center_xy
    vertices_scaled = vertices_centered * normalize_scale

    # Step 4: Flip Y axis (canonical has Y+ up, screen has Y+ down)
    vertices_scaled[:, 1] = -vertices_scaled[:, 1]

    # Step 5: Translate to screen center
    vertices_screen = vertices_scaled + [SCREEN_CENTER_X, SCREEN_CENTER_Y]

    # Plot polygon
    polygon_patch = patches.Polygon(vertices_screen,
                                   fill=False,
                                   edgecolor='black',
                                   linewidth=2,
                                   alpha=0.7)
    ax.add_patch(polygon_patch)

    # Plot screen center (reference)
    ax.plot(SCREEN_CENTER_X, SCREEN_CENTER_Y, 'k+', markersize=15,
           markeredgewidth=2, label='Screen Center', alpha=0.3)

    # Plot geometric centers
    for center_type in ['com', 'bbc', 'chc', 'icc']:
        x_col = f'center_{center_type}_x_canonical_px'
        y_col = f'center_{center_type}_y_canonical_px'

        if x_col in geometry_row and y_col in geometry_row and pd.notna(geometry_row[x_col]):
            # Transform from canonical to screen coordinates (same as vertices)
            # Apply same transformation: center at origin, scale, flip Y, translate to screen center
            center_x_canonical = geometry_row[x_col]
            center_y_canonical = geometry_row[y_col]
            center_x_centered = center_x_canonical - center_xy[0]
            center_y_centered = center_y_canonical - center_xy[1]
            center_x_scaled = center_x_centered * normalize_scale
            center_y_scaled = -(center_y_centered * normalize_scale)  # Flip Y
            center_x = center_x_scaled + SCREEN_CENTER_X
            center_y = center_y_scaled + SCREEN_CENTER_Y

            ax.plot(center_x, center_y,
                   marker='o',
                   markersize=12,
                   markerfacecolor=CENTER_COLORS[center_type],
                   markeredgecolor='white',
                   markeredgewidth=2,
                   label=CENTER_LABELS[center_type],
                   alpha=0.9,
                   zorder=10)

    # Plot fixations
    if len(fixations_df) > 0:
        ax.scatter(fixations_df['x'], fixations_df['y'],
                  c='gray', s=20, alpha=0.4,
                  label=f'2nd Fixations (n={len(fixations_df)})',
                  zorder=5)

    # Set equal aspect ratio and limits
    # Use aperture size (1987px) plus some margin to frame the polygon properly
    margin = 200  # Extra space around the polygon
    half_view = APERTURE_SCALE_FACTOR / 2 + margin
    ax.set_xlim(SCREEN_CENTER_X - half_view, SCREEN_CENTER_X + half_view)
    ax.set_ylim(SCREEN_CENTER_Y - half_view, SCREEN_CENTER_Y + half_view)
    ax.set_aspect('equal')
    ax.invert_yaxis()  # Match screen coordinates (y increases downward)

    # Title and legend
    ax.set_title(f'{polygon_case}\n(ID: {polygon_id}, n={len(fixations_df)} fixations)',
                fontsize=10, fontweight='bold')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')


def main():
    """Generate polygon visualizations."""
    print("="*80)
    print("POLYGON VISUALIZATIONS WITH 2ND FIXATIONS")
    print("="*80)

    # Load data
    print("\nLoading data...")
    fixations_df = pd.read_csv(FIXATIONS_FILE)
    geometry_df = pd.read_csv(GEOMETRY_FILE)
    geometry_df = geometry_df.set_index('polygon_id')

    print(f"Loaded {len(fixations_df)} fixations")
    print(f"Loaded geometry for {len(geometry_df)} polygons")

    # Get unique polygons
    unique_polygons = fixations_df[['polygon_id', 'polygon_case']].drop_duplicates()
    unique_polygons = unique_polygons.sort_values('polygon_id')

    print(f"\nFound {len(unique_polygons)} unique polygons")

    # Create figure with subplots (9 rows x 3 columns = 27 polygons)
    fig, axes = plt.subplots(9, 3, figsize=(24, 54))
    axes = axes.flatten()

    print("\nGenerating plots...")

    for idx, (_, row) in enumerate(unique_polygons.iterrows()):
        polygon_id = row['polygon_id']
        polygon_case = row['polygon_case']

        print(f"  [{idx+1}/{len(unique_polygons)}] {polygon_case} (ID: {polygon_id})")

        # Get fixations for this polygon
        polygon_fixations = fixations_df[fixations_df['polygon_id'] == polygon_id].copy()

        # Get geometry for this polygon
        if polygon_id in geometry_df.index:
            geometry_row = geometry_df.loc[polygon_id]
        else:
            print(f"    WARNING: No geometry found for polygon {polygon_id}")
            geometry_row = pd.Series()

        # Plot
        ax = axes[idx]
        plot_polygon_with_fixations(ax, polygon_id, polygon_case,
                                    polygon_fixations, geometry_row)

    # Remove unused subplots
    for idx in range(len(unique_polygons), len(axes)):
        fig.delaxes(axes[idx])

    # Overall title
    fig.suptitle('All 27 Polygons with 2nd Fixations and Geometric Centers\n' +
                'Gray dots = 2nd fixations from all participants | Colored circles = Geometric centers',
                fontsize=16, fontweight='bold', y=0.995)

    plt.tight_layout(rect=[0, 0, 1, 0.995])

    # Save
    output_file = OUTPUT_DIR / "all_polygons_with_fixations.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {output_file}")

    # Also create individual polygon plots for closer inspection
    print("\nGenerating individual polygon plots...")
    individual_dir = OUTPUT_DIR / "individual_polygons"
    individual_dir.mkdir(exist_ok=True)

    for idx, (_, row) in enumerate(unique_polygons.iterrows()):
        polygon_id = row['polygon_id']
        polygon_case = row['polygon_case']

        polygon_fixations = fixations_df[fixations_df['polygon_id'] == polygon_id].copy()

        if polygon_id in geometry_df.index:
            geometry_row = geometry_df.loc[polygon_id]
        else:
            geometry_row = pd.Series()

        # Create individual figure
        fig_ind, ax_ind = plt.subplots(figsize=(10, 10))
        plot_polygon_with_fixations(ax_ind, polygon_id, polygon_case,
                                    polygon_fixations, geometry_row)

        # Save
        output_file_ind = individual_dir / f"{polygon_case}_id{polygon_id}.png"
        plt.savefig(output_file_ind, dpi=200, bbox_inches='tight')
        plt.close(fig_ind)

    print(f"Saved {len(unique_polygons)} individual plots to: {individual_dir}")

    print("\n" + "="*80)
    print("VISUALIZATION COMPLETE")
    print("="*80)
    print(f"\nGenerated files:")
    print(f"  - all_polygons_with_fixations.png (overview)")
    print(f"  - individual_polygons/*.png (27 individual plots)")


if __name__ == "__main__":
    main()
