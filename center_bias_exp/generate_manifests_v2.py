#!/usr/bin/env python3
"""
Generate stimulus and memory manifests for center_bias_exp.

This script creates manifests using only the 6 available CAT2000 categories:
- Fractal, Object, OutdoorNatural, Random, Satelite, Sketch

Design (from experiment2_spec.md):
- 2 parts (A/B) × 9 mini-blocks × 39 trials = 702 total trials
- Each block: 36 image trials + 3 empty trials
- Each polygon (27 total) per part:
  - 12 image trials (2 images from each of 6 categories)
  - 1 empty trial (27 empty trials distributed across 9 blocks = 3 per block)
- Total image trials per part: 27 × 12 = 324
- Total empty trials per part: 27 × 1 = 27
- Total trials per part: 351 ✓

Image allocation:
- Need: 324 × 2 parts = 648 images
- Have: 6 categories × 100 = 600 images
- Solution: Use all 600 unique + repeat 48 images in Part B
"""

import os
import random
import pandas as pd
from pathlib import Path


# Configuration
CATEGORIES = ['Fractal', 'Object', 'OutdoorNatural', 'Random', 'Satelite', 'Sketch']
IMAGES_PER_CATEGORY = 100
IMAGES_PER_POLYGON_PER_CATEGORY = 2  # 2 images from each category for each polygon
POLYGONS_COUNT = 27
BLOCKS_PER_PART = 9
TRIALS_PER_BLOCK = 39
IMAGE_TRIALS_PER_BLOCK = 36
EMPTY_TRIALS_PER_BLOCK = 3

# Screen configuration (from experiment_config.yaml)
SCREEN_WIDTH_PX = 3840
SCREEN_HEIGHT_PX = 2160

# Cue grid positions (3x3 grid, EyeLink coordinates - top-left origin)
CUE_POSITIONS = {
    'grid_11': (960, 540),    # Top-left
    'grid_12': (1920, 540),   # Top-center
    'grid_13': (2880, 540),   # Top-right
    'grid_21': (960, 1080),   # Middle-left
    'grid_22': (1920, 1080),  # Center
    'grid_23': (2880, 1080),  # Middle-right
    'grid_31': (960, 1620),   # Bottom-left
    'grid_32': (1920, 1620),  # Bottom-center
    'grid_33': (2880, 1620),  # Bottom-right
}

# Polygon definitions (from polygon_geometry.csv)
POLYGONS = [
    # Allfar polygons (3)
    {'id': 'allfar_concave_01', 'case': 'allfar_concave', 'json': 'allfar_concave.json'},
    {'id': 'allfar_convex_01', 'case': 'allfar_convex', 'json': 'allfar_convex.json'},
    {'id': 'allfar_intermediate_01', 'case': 'allfar_intermediate', 'json': 'allfar_intermediate.json'},
    # Baseline polygons (3)
    {'id': 'baseline_rect_01', 'case': 'baseline_rectangle', 'json': 'baseline_rectangle.json'},
    {'id': 'baseline_sym_01', 'case': 'baseline_symmetric', 'json': 'baseline_symmetric_consolidated.json'},
    {'id': 'baseline_asym_01', 'case': 'baseline_asymmetric', 'json': 'baseline_asymmetric_consolidated.json'},
    # Iso-COM polygons (3)
    {'id': 'iso_com_01', 'case': 'iso_com', 'json': 'iso_com_01.json'},
    {'id': 'iso_com_02', 'case': 'iso_com', 'json': 'iso_com_02.json'},
    {'id': 'iso_com_03', 'case': 'iso_com', 'json': 'iso_com_03.json'},
    # Iso-CHC polygons (3)
    {'id': 'iso_chc_01', 'case': 'iso_chc', 'json': 'iso_chc_01.json'},
    {'id': 'iso_chc_02', 'case': 'iso_chc', 'json': 'iso_chc_02.json'},
    {'id': 'iso_chc_03', 'case': 'iso_chc', 'json': 'iso_chc_03.json'},
    # Iso-BBC polygons (3)
    {'id': 'iso_bbc_01', 'case': 'iso_bbc', 'json': 'iso_bbc_01.json'},
    {'id': 'iso_bbc_02', 'case': 'iso_bbc', 'json': 'iso_bbc_02.json'},
    {'id': 'iso_bbc_03', 'case': 'iso_bbc', 'json': 'iso_bbc_03.json'},
    # Iso-ICC polygons (3)
    {'id': 'iso_icc_01', 'case': 'iso_icc', 'json': 'iso_icc_01.json'},
    {'id': 'iso_icc_02', 'case': 'iso_icc', 'json': 'iso_icc_02.json'},
    {'id': 'iso_icc_03', 'case': 'iso_icc', 'json': 'iso_icc_03.json'},
    # Pair C1: BBC vs CHC+ICC (3)
    {'id': 'pair_C1_01', 'case': 'pair_C1_bbc_vs_chc_icc', 'json': 'pair_com_bbc_vs_chc_icc_01.json'},
    {'id': 'pair_C1_02', 'case': 'pair_C1_bbc_vs_chc_icc', 'json': 'pair_com_bbc_vs_chc_icc_02.json'},
    {'id': 'pair_C1_03', 'case': 'pair_C1_bbc_vs_chc_icc', 'json': 'pair_com_bbc_vs_chc_icc_03.json'},
    # Pair C2: CHC vs BBC+ICC (3)
    {'id': 'pair_C2_01', 'case': 'pair_C2_chc_vs_bbc_icc', 'json': 'pair_com_chc_vs_bbc_icc_01.json'},
    {'id': 'pair_C2_02', 'case': 'pair_C2_chc_vs_bbc_icc', 'json': 'pair_com_chc_vs_bbc_icc_02.json'},
    {'id': 'pair_C2_03', 'case': 'pair_C2_chc_vs_bbc_icc', 'json': 'pair_com_chc_vs_bbc_icc_03.json'},
    # Pair C3: ICC vs CHC+BBC (3)
    {'id': 'pair_C3_01', 'case': 'pair_C3_icc_vs_chc_bbc', 'json': 'pair_com_icc_vs_chc_bbc_01.json'},
    {'id': 'pair_C3_02', 'case': 'pair_C3_icc_vs_chc_bbc', 'json': 'pair_com_icc_vs_chc_bbc_02.json'},
    {'id': 'pair_C3_03', 'case': 'pair_C3_icc_vs_chc_bbc', 'json': 'pair_com_icc_vs_chc_bbc_03.json'},
]


def get_available_images(base_path: str) -> dict:
    """
    Scan CAT2000 folders and return available images per category.
    
    Returns dict: {category: [list of image filenames]}
    """
    images = {}
    cat2000_path = Path(base_path) / 'data' / 'raw' / 'stimuli' / 'CAT2000'
    
    for category in CATEGORIES:
        cat_path = cat2000_path / category
        if cat_path.exists():
            # Get all jpg files (actual naming: 001.jpg, 003.jpg, etc.)
            img_files = sorted([f.name for f in cat_path.glob('*.jpg') if not f.name.startswith('._')])
            images[category] = img_files
            print(f"  {category}: {len(img_files)} images")
        else:
            print(f"  WARNING: {category} folder not found!")
            images[category] = []
    
    return images


def allocate_images_to_polygons(available_images: dict, seed: int = 42) -> tuple:
    """
    Allocate images to polygons ensuring:
    - Each polygon gets exactly 2 images from each category (12 total) per part
    - Images are unique within each part where possible
    - Part B may reuse some images from Part A if not enough available
    
    Design:
    - Part A: 27 polygons × 6 categories × 2 images = 324 images (use first 54 from each cat)
    - Part B: 27 polygons × 6 categories × 2 images = 324 images (use remaining 46 + repeat 8)
    
    Returns (part_a_allocation, part_b_allocation)
    Each allocation is dict: {polygon_id: {category: [img1, img2]}}
    """
    random.seed(seed)
    
    # Shuffle images within each category
    shuffled = {}
    for cat, imgs in available_images.items():
        shuffled[cat] = imgs.copy()
        random.shuffle(shuffled[cat])
    
    # Images needed per category per part: 27 polygons × 2 = 54
    images_per_cat_per_part = POLYGONS_COUNT * IMAGES_PER_POLYGON_PER_CATEGORY
    print(f"\n  Images needed per category per part: {images_per_cat_per_part}")
    print(f"  Total images needed per part: {images_per_cat_per_part * len(CATEGORIES)}")
    
    # Allocate to Part A (first 54 images from each category)
    part_a = {}
    image_idx = {cat: 0 for cat in CATEGORIES}
    
    for polygon in POLYGONS:
        pid = polygon['id']
        part_a[pid] = {}
        for cat in CATEGORIES:
            imgs = shuffled[cat]
            idx = image_idx[cat]
            part_a[pid][cat] = [imgs[idx], imgs[idx + 1]]
            image_idx[cat] += 2
    
    print(f"  Part A allocated. Index position per category: {list(image_idx.values())[0]}")
    
    # Allocate to Part B
    # Use remaining images (46 per category), then wrap around for the extra 8
    part_b = {}
    
    for polygon in POLYGONS:
        pid = polygon['id']
        part_b[pid] = {}
        for cat in CATEGORIES:
            imgs = shuffled[cat]
            idx = image_idx[cat]
            # Get two images, wrapping around if needed
            img1_idx = idx % len(imgs)
            img2_idx = (idx + 1) % len(imgs)
            part_b[pid][cat] = [imgs[img1_idx], imgs[img2_idx]]
            image_idx[cat] += 2
    
    print(f"  Part B allocated. Final index per category: {list(image_idx.values())[0]}")
    
    return part_a, part_b


def create_image_path(category: str, filename: str) -> str:
    """Create the full relative path to an image file."""
    return f"data/raw/stimuli/CAT2000/{category}/{filename}"


def create_polygon_json_path(json_filename: str) -> str:
    """Create the full relative path to a polygon JSON file."""
    return f"data/raw/stimuli/polygons/{json_filename}"


def generate_stimulus_manifest(
    part: str,
    image_allocation: dict,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate stimulus manifest for one part (A or B).
    
    Structure: 9 blocks × 39 trials = 351 trials
    Each block: 36 image trials + 3 empty trials
    
    Each polygon appears:
    - 12 times with images (2 per category × 6 categories)
    - 1 time empty
    - Total: 13 appearances per polygon per part
    """
    random.seed(seed)
    
    # Create list of all image trials (324 total)
    # Each polygon gets 12 image trials (2 per category)
    image_trials = []
    
    for polygon in POLYGONS:
        pid = polygon['id']
        pcase = polygon['case']
        pjson = polygon['json']
        
        for cat in CATEGORIES:
            for img_file in image_allocation[pid][cat]:
                image_id = f"{part}_{cat}_{img_file.replace('.jpg', '')}"
                image_trials.append({
                    'polygon_id': pid,
                    'polygon_case': pcase,
                    'polygon_json_path': create_polygon_json_path(pjson),
                    'trial_type': 'image',
                    'image_id': image_id,
                    'image_path': create_image_path(cat, img_file),
                    'category': cat,
                })
    
    print(f"  Created {len(image_trials)} image trials")
    
    # Create list of empty trials (27 total - one per polygon)
    empty_trials = []
    for polygon in POLYGONS:
        empty_trials.append({
            'polygon_id': polygon['id'],
            'polygon_case': polygon['case'],
            'polygon_json_path': create_polygon_json_path(polygon['json']),
            'trial_type': 'empty',
            'image_id': None,
            'image_path': None,
            'category': None,
        })
    
    print(f"  Created {len(empty_trials)} empty trials")
    
    # Shuffle both lists
    random.shuffle(image_trials)
    random.shuffle(empty_trials)
    
    # Distribute into 9 blocks
    # Each block: 36 image trials + 3 empty trials = 39 total
    all_trials = []
    cue_pos_list = list(CUE_POSITIONS.keys())
    trial_counter = 0
    
    for block in range(1, BLOCKS_PER_PART + 1):
        # Get 36 image trials for this block
        start_img = (block - 1) * IMAGE_TRIALS_PER_BLOCK
        end_img = block * IMAGE_TRIALS_PER_BLOCK
        block_image_trials = image_trials[start_img:end_img]
        
        # Get 3 empty trials for this block
        start_empty = (block - 1) * EMPTY_TRIALS_PER_BLOCK
        end_empty = block * EMPTY_TRIALS_PER_BLOCK
        block_empty_trials = empty_trials[start_empty:end_empty]
        
        # Combine and shuffle within block
        block_trials = block_image_trials + block_empty_trials
        random.shuffle(block_trials)
        
        # Assign trial numbers and cue positions
        for trial_in_block, trial_data in enumerate(block_trials, 1):
            trial_counter += 1
            
            # Select cue position (cycle through all 9 positions)
            cue_pos_id = cue_pos_list[(trial_counter - 1) % len(cue_pos_list)]
            cue_x, cue_y = CUE_POSITIONS[cue_pos_id]
            
            trial_uid = f"{part}_MB{block:02d}_T{trial_counter:03d}"
            
            trial = {
                'part': part,
                'mini_block': block,
                'trial_in_block': trial_in_block,
                'trial_uid': trial_uid,
                'trial_type': trial_data['trial_type'],
                'polygon_id': trial_data['polygon_id'],
                'polygon_case': trial_data['polygon_case'],
                'polygon_json_path': trial_data['polygon_json_path'],
                'cue_pos_id': cue_pos_id,
                'cue_x_px': cue_x,
                'cue_y_px': cue_y,
                'stimulus_duration_s': 4.0,
                'iti_s': 0.5,
                'max_drift_time_s': 10.0,
                'drift_retry_limit': 1,
                'aperture_scale_factor': 1987,  # Target size in pixels (92% of 2160px screen height)
                'image_id': trial_data['image_id'],
                'image_path': trial_data['image_path'],
                'category': trial_data['category'],
                'bias_level': None,  # Can be computed later if needed
            }
            all_trials.append(trial)
    
    return pd.DataFrame(all_trials)


def generate_memory_manifest(
    part: str,
    stimulus_df: pd.DataFrame,
    other_part_images: set,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate memory manifest for one part.
    
    9 blocks, each with 1 memory probe.
    Mix of old (from trials in THIS part) and new (from OTHER part - not seen in this part)
    """
    random.seed(seed + 100)  # Different seed for memory selection
    
    # Get images that were shown in this part's trials
    shown_df = stimulus_df[stimulus_df['image_path'].notna()][['image_id', 'image_path', 'category']]
    shown_list = shown_df.values.tolist()
    this_part_images = set(stimulus_df[stimulus_df['image_path'].notna()]['image_path'])
    random.shuffle(shown_list)
    
    # Select 5 "old" probes (images that were shown in this part)
    n_old = 5
    old_probes = shown_list[:n_old]
    
    # Select 4 "new" probes - images from the OTHER part that weren't shown in this part
    # These are truly "new" from the participant's perspective for this part
    n_new = 4
    new_images = list(other_part_images - this_part_images)
    random.shuffle(new_images)
    
    new_probes = []
    for img_path in new_images[:n_new]:
        # Extract category and filename from path
        parts = img_path.split('/')
        cat = parts[-2]  # Category is second to last
        filename = parts[-1]
        new_probes.append({
            'image_id': f"{part}_MEM_{cat}_{filename.replace('.jpg', '')}",
            'image_path': img_path,
            'category': cat,
        })
    
    # Combine probes
    memory_trials = []
    
    # Add old probes
    for img_id, img_path, cat in old_probes:
        memory_trials.append({
            'probe_image_id': img_id,
            'probe_image_path': img_path,
            'is_old': True,
        })
    
    # Add new probes
    for probe in new_probes:
        memory_trials.append({
            'probe_image_id': probe['image_id'],
            'probe_image_path': probe['image_path'],
            'is_old': False,
        })
    
    # Shuffle and assign to blocks
    random.shuffle(memory_trials)
    
    rows = []
    for block, probe in enumerate(memory_trials, 1):
        rows.append({
            'part': part,
            'mini_block': block,
            'probe_image_id': probe['probe_image_id'],
            'probe_image_path': probe['probe_image_path'],
            'probe_duration_s': 3.0,
            'is_old': probe['is_old'],
        })
    
    return pd.DataFrame(rows)


def verify_manifest(df: pd.DataFrame, part: str) -> bool:
    """Verify manifest meets experiment requirements."""
    print(f"\n  Verifying Part {part} manifest...")
    
    errors = []
    
    # Check total trials
    if len(df) != 351:
        errors.append(f"Expected 351 trials, got {len(df)}")
    
    # Check blocks
    for block in range(1, 10):
        block_df = df[df['mini_block'] == block]
        if len(block_df) != 39:
            errors.append(f"Block {block}: expected 39 trials, got {len(block_df)}")
        
        image_count = len(block_df[block_df['trial_type'] == 'image'])
        empty_count = len(block_df[block_df['trial_type'] == 'empty'])
        
        if image_count != 36:
            errors.append(f"Block {block}: expected 36 image trials, got {image_count}")
        if empty_count != 3:
            errors.append(f"Block {block}: expected 3 empty trials, got {empty_count}")
    
    # Check each polygon appears with images from each category
    for polygon in POLYGONS:
        pid = polygon['id']
        poly_df = df[df['polygon_id'] == pid]
        
        # Check image trials per category
        for cat in CATEGORIES:
            cat_count = len(poly_df[(poly_df['category'] == cat) & (poly_df['trial_type'] == 'image')])
            if cat_count != 2:
                errors.append(f"Polygon {pid}, category {cat}: expected 2 image trials, got {cat_count}")
        
        # Check empty trials
        empty_count = len(poly_df[poly_df['trial_type'] == 'empty'])
        if empty_count < 1:
            errors.append(f"Polygon {pid}: expected at least 1 empty trial, got {empty_count}")
    
    if errors:
        print(f"  ❌ Verification FAILED with {len(errors)} errors:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"     - {err}")
        if len(errors) > 10:
            print(f"     ... and {len(errors) - 10} more errors")
        return False
    else:
        print(f"  ✓ Verification PASSED")
        return True


def main():
    """Generate all manifests."""
    print("=" * 60)
    print("Generating Experiment Manifests")
    print("=" * 60)
    
    base_path = Path(__file__).parent
    
    # Get available images
    print("\nScanning available images...")
    available_images = get_available_images(base_path)
    
    # Verify we have enough images
    total_images = sum(len(imgs) for imgs in available_images.values())
    images_needed_per_part = POLYGONS_COUNT * IMAGES_PER_POLYGON_PER_CATEGORY * len(CATEGORIES)
    
    print(f"\nTotal images available: {total_images}")
    print(f"Images needed per part: {images_needed_per_part}")
    print(f"Images needed total: {images_needed_per_part * 2}")
    
    if total_images < images_needed_per_part:
        print("ERROR: Not enough images even for one part!")
        return
    
    # Allocate images to polygons
    print("\nAllocating images to polygons...")
    part_a_alloc, part_b_alloc = allocate_images_to_polygons(available_images)
    
    # Track all used images (for memory probe selection)
    all_used_images = set()
    for alloc in [part_a_alloc, part_b_alloc]:
        for pid, cats in alloc.items():
            for cat, imgs in cats.items():
                for img in imgs:
                    all_used_images.add(create_image_path(cat, img))
    
    print(f"\nTotal images allocated (may include repeats): {len(all_used_images)}")
    
    # Generate stimulus manifests
    print("\nGenerating stimulus manifests...")
    print("  Part A:")
    stim_a = generate_stimulus_manifest('A', part_a_alloc, seed=42)
    print("  Part B:")
    stim_b = generate_stimulus_manifest('B', part_b_alloc, seed=43)
    
    # Verify manifests
    verify_manifest(stim_a, 'A')
    verify_manifest(stim_b, 'B')
    
    # Generate memory manifests
    # Get image sets for each part
    part_a_images = set(stim_a[stim_a['image_path'].notna()]['image_path'])
    part_b_images = set(stim_b[stim_b['image_path'].notna()]['image_path'])
    
    print("\nGenerating memory manifests...")
    mem_a = generate_memory_manifest('A', stim_a, part_b_images, seed=42)
    mem_b = generate_memory_manifest('B', stim_b, part_a_images, seed=43)
    
    print(f"  Part A: {len(mem_a)} probes ({sum(mem_a['is_old'])} old, {sum(~mem_a['is_old'])} new)")
    print(f"  Part B: {len(mem_b)} probes ({sum(mem_b['is_old'])} old, {sum(~mem_b['is_old'])} new)")
    
    # Save manifests
    manifest_dir = base_path / 'manifests'
    manifest_dir.mkdir(exist_ok=True)
    
    print("\nSaving manifests...")
    stim_a.to_csv(manifest_dir / 'stimulus_manifest_partA.csv', index=False)
    stim_b.to_csv(manifest_dir / 'stimulus_manifest_partB.csv', index=False)
    mem_a.to_csv(manifest_dir / 'memory_manifest_partA.csv', index=False)
    mem_b.to_csv(manifest_dir / 'memory_manifest_partB.csv', index=False)
    
    # Also save combined manifests
    stim_combined = pd.concat([stim_a, stim_b], ignore_index=True)
    mem_combined = pd.concat([mem_a, mem_b], ignore_index=True)
    stim_combined.to_csv(manifest_dir / 'stimulus_manifest.csv', index=False)
    mem_combined.to_csv(manifest_dir / 'memory_manifest.csv', index=False)
    
    print(f"\nManifests saved to {manifest_dir}/")
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    
    for part, df in [('A', stim_a), ('B', stim_b)]:
        print(f"\nPart {part}:")
        print(f"  Total trials: {len(df)}")
        print(f"  Image trials: {len(df[df['trial_type'] == 'image'])}")
        print(f"  Empty trials: {len(df[df['trial_type'] == 'empty'])}")
        print(f"  Unique polygons: {df['polygon_id'].nunique()}")
        print(f"  Blocks: {df['mini_block'].nunique()}")
        print(f"  Trials per block: {df.groupby('mini_block').size().unique()}")
        
        cat_counts = df[df['category'].notna()]['category'].value_counts()
        print(f"  Trials per category: {dict(cat_counts)}")
    
    # Check for image repeats between parts
    overlap = part_a_images & part_b_images
    
    print(f"\n  Part A unique images: {len(part_a_images)}")
    print(f"  Part B unique images: {len(part_b_images)}")
    print(f"  Images shared between parts: {len(overlap)}")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
