"""
Visual inspection tool for all Part A stimuli at experiment scale.

Creates a comprehensive visual overview of all stimuli showing:
- All shapes with their size multipliers
- Masked images at actual experiment scale
- Shape names and sizes labeled

Usage:
    python src/inspect_stimuli_visual.py --part A
    python src/inspect_stimuli_visual.py --part A --save-individual
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from psychopy import visual
from psychopy_utils import prepare_polygon_shape, prepare_masked_image


def create_stimulus_grid(part, manifest_path, output_dir, save_individual=False, screen_size=(3840, 2160)):
    """
    Create a grid visualization of all stimuli.

    Parameters
    ----------
    part : str
        'A' or 'B'
    manifest_path : Path
        Path to stimulus manifest CSV
    output_dir : Path
        Output directory for visualizations
    save_individual : bool
        If True, save individual images for each stimulus
    screen_size : tuple
        Screen resolution (width, height)
    """
    print(f"\n{'='*60}")
    print(f"Creating Visual Inspection for Part {part}")
    print(f"{'='*60}\n")

    # Load manifest
    print(f"Loading manifest: {manifest_path}")
    manifest = pd.read_csv(manifest_path)

    # Filter for this part and image trials only
    manifest_part = manifest[(manifest['part'] == part) & (manifest['trial_type'] == 'image')].copy()
    print(f"Found {len(manifest_part)} image trials for Part {part}")

    # Get unique shapes
    shapes = manifest_part['polygon_json_path'].dropna().unique()
    print(f"Found {len(shapes)} unique shapes")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create PsychoPy window (offscreen)
    print("Creating PsychoPy window...")
    win = visual.Window(
        size=screen_size,
        units='pix',
        fullscr=False,
        color=[0.5, 0.5, 0.5],
        allowGUI=False
    )

    # Aperture scale factor (92% of screen height)
    aperture_scale_factor = int(screen_size[1] * 0.92)

    # Shape categories
    very_compact_shapes = ['iso_chc_01', 'iso_chc_02', 'iso_chc_03',
                           'iso_com_01', 'iso_com_02', 'iso_com_03']
    compact_shapes = ['allfar_convex', 'iso_bbc_02', 'iso_bbc_03',
                      'iso_icc_01', 'iso_icc_02', 'iso_icc_03']

    # Render each shape
    print("\nRendering shapes...")
    shape_data = []

    for shape_path in shapes:
        shape_name = Path(shape_path).stem

        # Determine multiplier
        if shape_name in very_compact_shapes:
            multiplier = 1.03
            category = "Very Compact"
        elif shape_name in compact_shapes:
            multiplier = 1.015
            category = "Compact"
        else:
            multiplier = 1.0
            category = "Standard"

        final_size = int(aperture_scale_factor * multiplier)

        print(f"  {shape_name}: {category} ({multiplier}x) -> {final_size}px")

        try:
            # Prepare polygon shape (empty outline)
            polygon_shape = prepare_polygon_shape(
                win,
                shape_path,
                aperture_scale_factor=aperture_scale_factor
            )

            # Draw and capture
            polygon_shape.draw()
            win.flip()

            # Get pixel data
            win.getMovieFrame(buffer='back')
            img_array = np.array(win.movieFrames[0])
            win.movieFrames = []

            shape_data.append({
                'name': shape_name,
                'category': category,
                'multiplier': multiplier,
                'final_size': final_size,
                'image': img_array
            })

            # Save individual if requested
            if save_individual:
                individual_path = output_dir / f"{shape_name}_outline.png"
                Image.fromarray(img_array).save(individual_path)

        except Exception as e:
            print(f"    ERROR: {e}")
            continue

    win.close()

    # Create comprehensive grid figure
    print("\nCreating grid visualization...")
    n_shapes = len(shape_data)
    n_cols = 4
    n_rows = int(np.ceil(n_shapes / n_cols))

    fig = plt.figure(figsize=(20, 5 * n_rows))
    fig.suptitle(f'Part {part} Stimuli - Visual Inspection\n'
                 f'Screen: {screen_size[0]}x{screen_size[1]}px, Base aperture: {aperture_scale_factor}px',
                 fontsize=16, fontweight='bold')

    for idx, shape in enumerate(shape_data):
        ax = plt.subplot(n_rows, n_cols, idx + 1)
        ax.imshow(shape['image'])
        ax.axis('off')

        # Add title with shape info
        color_map = {'Very Compact': 'red', 'Compact': 'orange', 'Standard': 'green'}
        title_color = color_map.get(shape['category'], 'black')

        ax.set_title(
            f"{shape['name']}\n"
            f"{shape['category']} ({shape['multiplier']}x)\n"
            f"Size: {shape['final_size']}px",
            fontsize=10,
            fontweight='bold',
            color=title_color
        )

    plt.tight_layout()

    # Save grid
    grid_path = output_dir / f"part_{part}_stimulus_grid.png"
    plt.savefig(grid_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved grid visualization: {grid_path}")

    # Create summary figure
    print("Creating summary figure...")
    fig_summary, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: Shape sizes
    categories = [s['category'] for s in shape_data]
    sizes = [s['final_size'] for s in shape_data]
    names = [s['name'] for s in shape_data]

    colors = [color_map.get(c, 'gray') for c in categories]

    ax1.barh(names, sizes, color=colors, alpha=0.7, edgecolor='black')
    ax1.axvline(aperture_scale_factor, color='blue', linestyle='--', linewidth=2, label=f'Base size ({aperture_scale_factor}px)')
    ax1.axvline(screen_size[1], color='red', linestyle='--', linewidth=2, label=f'Screen height ({screen_size[1]}px)')
    ax1.set_xlabel('Size (pixels)', fontsize=12)
    ax1.set_title('Shape Sizes at Experiment Scale', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='x', alpha=0.3)

    # Plot 2: Category distribution
    category_counts = pd.Series(categories).value_counts()
    ax2.pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%',
            colors=[color_map.get(c, 'gray') for c in category_counts.index],
            startangle=90)
    ax2.set_title('Shape Category Distribution', fontsize=14, fontweight='bold')

    plt.tight_layout()
    summary_path = output_dir / f"part_{part}_summary.png"
    plt.savefig(summary_path, dpi=150, bbox_inches='tight')
    print(f"Saved summary figure: {summary_path}")

    # Print summary table
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Shape':<20} {'Category':<15} {'Multiplier':<12} {'Final Size':<12}")
    print("-" * 60)
    for shape in sorted(shape_data, key=lambda x: x['final_size'], reverse=True):
        print(f"{shape['name']:<20} {shape['category']:<15} {shape['multiplier']:<12.3f} {shape['final_size']:<12}px")
    print(f"{'='*60}\n")

    print(f"All visualizations saved to: {output_dir}")
    print(f"\nFiles created:")
    print(f"  - {grid_path.name} (grid of all shapes)")
    print(f"  - {summary_path.name} (size comparison)")
    if save_individual:
        print(f"  - Individual shape files (*_outline.png)")

    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Visual inspection of stimuli at experiment scale')
    parser.add_argument('--part', choices=['A', 'B'], required=True,
                       help='Part to inspect (A or B)')
    parser.add_argument('--save-individual', action='store_true',
                       help='Save individual images for each shape')
    parser.add_argument('--output-dir', type=str,
                       default='outputs/stimulus_inspection',
                       help='Output directory for visualizations')

    args = parser.parse_args()

    # Determine manifest path
    if args.part == 'A':
        manifest_path = Path('manifests/stimulus_manifest_partA.csv')
    else:
        manifest_path = Path('manifests/stimulus_manifest_partB.csv')

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir) / f"part_{args.part}"

    create_stimulus_grid(
        args.part,
        manifest_path,
        output_dir,
        save_individual=args.save_individual
    )


if __name__ == '__main__':
    main()
