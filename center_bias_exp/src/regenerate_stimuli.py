"""
Regenerate all masked image stimuli with updated size multipliers.

This script pre-renders all masked images using the current size settings
(3% boost for very compact shapes, 1.5% boost for compact shapes).

This allows you to:
1. Verify that stimuli look correct before running the experiment
2. Speed up experiment runtime (pre-rendered images load faster)

Usage:
    python src/regenerate_stimuli.py --part A
    python src/regenerate_stimuli.py --part B
    python src/regenerate_stimuli.py --all  # Both parts
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from PIL import Image
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from psychopy import visual
from psychopy_utils import prepare_polygon_shape, prepare_masked_image


def regenerate_stimuli(part, manifest_path, output_dir, screen_size=(3840, 2160)):
    """
    Regenerate all stimuli for a given part.

    Parameters
    ----------
    part : str
        'A' or 'B'
    manifest_path : Path
        Path to stimulus manifest CSV
    output_dir : Path
        Output directory for rendered stimuli
    screen_size : tuple
        Screen resolution (width, height)
    """
    print(f"\n{'='*60}")
    print(f"Regenerating Part {part} Stimuli")
    print(f"{'='*60}\n")

    # Load manifest
    print(f"Loading manifest: {manifest_path}")
    manifest = pd.read_csv(manifest_path)

    # Filter for this part
    manifest_part = manifest[manifest['part'] == part].copy()
    print(f"Found {len(manifest_part)} trials for Part {part}")

    # Get unique image+polygon combinations
    stim_combos = manifest_part[['trial_type', 'image_path', 'polygon_json_path']].drop_duplicates()
    print(f"Found {len(stim_combos)} unique stimulus combinations")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary PsychoPy window (offscreen for rendering)
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
    print(f"Aperture scale factor: {aperture_scale_factor}px")

    # Regenerate each stimulus
    print("\nRegenerating stimuli...")
    success_count = 0
    error_count = 0

    for idx, row in tqdm(stim_combos.iterrows(), total=len(stim_combos), desc="Rendering"):
        trial_type = row['trial_type']
        image_path = row['image_path']
        polygon_json_path = row['polygon_json_path']

        # Skip non-image trials
        if trial_type != 'image' or pd.isna(image_path) or pd.isna(polygon_json_path):
            continue

        try:
            # Extract shape name for output filename
            shape_name = Path(polygon_json_path).stem
            image_name = Path(image_path).stem

            # Create output filename
            output_filename = f"{image_name}_{shape_name}.png"
            output_path = output_dir / output_filename

            # Skip if already exists
            if output_path.exists():
                continue

            # Prepare polygon shape
            polygon_shape = prepare_polygon_shape(
                win,
                polygon_json_path,
                aperture_scale_factor=aperture_scale_factor
            )

            # Prepare masked image
            masked_image = prepare_masked_image(
                win,
                image_path,
                polygon_shape,
                shape_name=shape_name,
                position=(0, 0)
            )

            # Draw and capture
            masked_image.draw()
            win.flip()

            # Get the pixel data
            win.getMovieFrame(buffer='back')
            img_array = np.array(win.movieFrames[0])
            img_pil = Image.fromarray(img_array)

            # Save
            img_pil.save(output_path, 'PNG')

            # Clear movie frames
            win.movieFrames = []

            success_count += 1

        except Exception as e:
            print(f"\nError rendering {image_name}_{shape_name}: {e}")
            error_count += 1
            continue

    # Cleanup
    win.close()

    print(f"\n{'='*60}")
    print(f"Regeneration Complete")
    print(f"{'='*60}")
    print(f"Successfully rendered: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Regenerate masked image stimuli')
    parser.add_argument('--part', choices=['A', 'B'], help='Part to regenerate (A or B)')
    parser.add_argument('--all', action='store_true', help='Regenerate both parts')
    parser.add_argument('--manifest', type=str,
                       default='manifests/stimulus_manifest_partA.csv',
                       help='Path to stimulus manifest')
    parser.add_argument('--output-dir', type=str,
                       default='outputs/rendered_stimuli',
                       help='Output directory for rendered stimuli')

    args = parser.parse_args()

    if not args.part and not args.all:
        print("ERROR: Must specify --part A, --part B, or --all")
        sys.exit(1)

    output_dir = Path(args.output_dir)

    if args.all:
        parts = ['A', 'B']
    else:
        parts = [args.part]

    for part in parts:
        # Determine manifest path
        if part == 'A':
            manifest_path = Path('manifests/stimulus_manifest_partA.csv')
        else:
            manifest_path = Path('manifests/stimulus_manifest_partB.csv')

        if not manifest_path.exists():
            print(f"ERROR: Manifest not found: {manifest_path}")
            continue

        # Create part-specific output directory
        part_output_dir = output_dir / f"part_{part}"

        regenerate_stimuli(part, manifest_path, part_output_dir)


if __name__ == '__main__':
    main()
