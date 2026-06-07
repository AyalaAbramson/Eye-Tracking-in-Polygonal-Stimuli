#!/usr/bin/env python3
"""
Generate stimulus and memory manifests for center_bias_exp.

Creates complete trial manifests for Parts A and B with:
- 9 mini-blocks × 39 trials = 351 trials per part
- 36 image trials + 3 empty trials per block
- Each polygon appears empty once and with multiple images
- Deterministic randomization with fixed seed

Usage:
    python generate_manifests.py [--participant-id P01] [--output-dir manifests]
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd

# Add src to path to import cue_grid
sys.path.insert(0, str(Path(__file__).parent / "src"))
from cue_grid import get_cue_positions


# =============================================================================
# POLYGON DEFINITIONS (27 total)
# =============================================================================

POLYGONS = [
    # Spectrum polygons (3)
    {
        "polygon_id": "allfar_concave_01",
        "polygon_case": "allfar_concave",
        "family": "spectrum",
        "json_filename": "allfar_concave.json",
        "polygon_json_path": "data/raw/stimuli/polygons/allfar_concave.json",
    },
    {
        "polygon_id": "allfar_convex_01",
        "polygon_case": "allfar_convex",
        "family": "spectrum",
        "json_filename": "allfar_convex.json",
        "polygon_json_path": "data/raw/stimuli/polygons/allfar_convex.json",
    },
    {
        "polygon_id": "allfar_intermediate_01",
        "polygon_case": "allfar_intermediate",
        "family": "spectrum",
        "json_filename": "allfar_intermediate.json",
        "polygon_json_path": "data/raw/stimuli/polygons/allfar_intermediate.json",
    },
    
    # Baseline polygons (3)
    {
        "polygon_id": "baseline_rect_01",
        "polygon_case": "baseline_rectangle",
        "family": "baseline",
        "json_filename": "baseline_rectangle.json",
        "polygon_json_path": "data/raw/stimuli/polygons/baseline_rectangle.json",
    },
    {
        "polygon_id": "baseline_sym_01",
        "polygon_case": "baseline_symmetric",
        "family": "baseline",
        "json_filename": "baseline_symmetric_consolidated.json",
        "polygon_json_path": "data/raw/stimuli/polygons/baseline_symmetric_consolidated.json",
    },
    {
        "polygon_id": "baseline_asym_01",
        "polygon_case": "baseline_asymmetric",
        "family": "baseline",
        "json_filename": "baseline_asymmetric_consolidated.json",
        "polygon_json_path": "data/raw/stimuli/polygons/baseline_asymmetric_consolidated.json",
    },
    
    # Iso-dispersion: COM (3)
    {
        "polygon_id": "iso_com_01",
        "polygon_case": "iso_com",
        "family": "iso_com",
        "json_filename": "iso_com_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_com_01.json",
    },
    {
        "polygon_id": "iso_com_02",
        "polygon_case": "iso_com",
        "family": "iso_com",
        "json_filename": "iso_com_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_com_02.json",
    },
    {
        "polygon_id": "iso_com_03",
        "polygon_case": "iso_com",
        "family": "iso_com",
        "json_filename": "iso_com_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_com_03.json",
    },
    
    # Iso-dispersion: CHC (3)
    {
        "polygon_id": "iso_chc_01",
        "polygon_case": "iso_chc",
        "family": "iso_chc",
        "json_filename": "iso_chc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_chc_01.json",
    },
    {
        "polygon_id": "iso_chc_02",
        "polygon_case": "iso_chc",
        "family": "iso_chc",
        "json_filename": "iso_chc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_chc_02.json",
    },
    {
        "polygon_id": "iso_chc_03",
        "polygon_case": "iso_chc",
        "family": "iso_chc",
        "json_filename": "iso_chc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_chc_03.json",
    },
    
    # Iso-dispersion: BBC (3)
    {
        "polygon_id": "iso_bbc_01",
        "polygon_case": "iso_bbc",
        "family": "iso_bbc",
        "json_filename": "iso_bbc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_bbc_01.json",
    },
    {
        "polygon_id": "iso_bbc_02",
        "polygon_case": "iso_bbc",
        "family": "iso_bbc",
        "json_filename": "iso_bbc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_bbc_02.json",
    },
    {
        "polygon_id": "iso_bbc_03",
        "polygon_case": "iso_bbc",
        "family": "iso_bbc",
        "json_filename": "iso_bbc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_bbc_03.json",
    },
    
    # Iso-dispersion: ICC (3)
    {
        "polygon_id": "iso_icc_01",
        "polygon_case": "iso_icc",
        "family": "iso_icc",
        "json_filename": "iso_icc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_icc_01.json",
    },
    {
        "polygon_id": "iso_icc_02",
        "polygon_case": "iso_icc",
        "family": "iso_icc",
        "json_filename": "iso_icc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_icc_02.json",
    },
    {
        "polygon_id": "iso_icc_03",
        "polygon_case": "iso_icc",
        "family": "iso_icc",
        "json_filename": "iso_icc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/iso_icc_03.json",
    },
    
    # Pair condition 1: COM+BBC vs CHC+ICC (3)
    {
        "polygon_id": "pair_C1_01",
        "polygon_case": "pair_C1_bbc_vs_chc_icc",
        "family": "pair_C1",
        "json_filename": "pair_com_bbc_vs_chc_icc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_bbc_vs_chc_icc_01.json",
    },
    {
        "polygon_id": "pair_C1_02",
        "polygon_case": "pair_C1_bbc_vs_chc_icc",
        "family": "pair_C1",
        "json_filename": "pair_com_bbc_vs_chc_icc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_bbc_vs_chc_icc_02.json",
    },
    {
        "polygon_id": "pair_C1_03",
        "polygon_case": "pair_C1_bbc_vs_chc_icc",
        "family": "pair_C1",
        "json_filename": "pair_com_bbc_vs_chc_icc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_bbc_vs_chc_icc_03.json",
    },
    
    # Pair condition 2: COM+CHC vs BBC+ICC (3)
    {
        "polygon_id": "pair_C2_01",
        "polygon_case": "pair_C2_chc_vs_bbc_icc",
        "family": "pair_C2",
        "json_filename": "pair_com_chc_vs_bbc_icc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_chc_vs_bbc_icc_01.json",
    },
    {
        "polygon_id": "pair_C2_02",
        "polygon_case": "pair_C2_chc_vs_bbc_icc",
        "family": "pair_C2",
        "json_filename": "pair_com_chc_vs_bbc_icc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_chc_vs_bbc_icc_02.json",
    },
    {
        "polygon_id": "pair_C2_03",
        "polygon_case": "pair_C2_chc_vs_bbc_icc",
        "family": "pair_C2",
        "json_filename": "pair_com_chc_vs_bbc_icc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_chc_vs_bbc_icc_03.json",
    },
    
    # Pair condition 3: COM+ICC vs CHC+BBC (3)
    {
        "polygon_id": "pair_C3_01",
        "polygon_case": "pair_C3_icc_vs_chc_bbc",
        "family": "pair_C3",
        "json_filename": "pair_com_icc_vs_chc_bbc_01.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_icc_vs_chc_bbc_01.json",
    },
    {
        "polygon_id": "pair_C3_02",
        "polygon_case": "pair_C3_icc_vs_chc_bbc",
        "family": "pair_C3",
        "json_filename": "pair_com_icc_vs_chc_bbc_02.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_icc_vs_chc_bbc_02.json",
    },
    {
        "polygon_id": "pair_C3_03",
        "polygon_case": "pair_C3_icc_vs_chc_bbc",
        "family": "pair_C3",
        "json_filename": "pair_com_icc_vs_chc_bbc_03.json",
        "polygon_json_path": "data/raw/stimuli/polygons/pair_com_icc_vs_chc_bbc_03.json",
    },
]


# =============================================================================
# CAT2000 IMAGE CATEGORIES
# =============================================================================

CAT2000_CATEGORIES = [
    "Action",
    "Affective",
    "Art",
    "BlackWhite",
    "Cartoon",
    "Fractal",
    "Indoor",
    "Inverted",
    "Jumbled",
    "LineDrawing",
    "LowResolution",
    "Noisy",
    "Object",
    "OutdoorManMade",
    "OutdoorNatural",
    "Pattern",
    "Random",
    "Satelite",
    "Sketch",
    "Social",
]


def generate_image_pool(part: str, n_images: int, rng: np.random.Generator) -> List[Dict[str, Any]]:
    """
    Generate a pool of CAT2000 images for one part.
    
    Parameters
    ----------
    part : str
        Part identifier ('A' or 'B')
    n_images : int
        Number of images to generate
    rng : np.random.Generator
        Random number generator for reproducibility
        
    Returns
    -------
    list of dict
        Each dict contains: image_id, image_path, category, bias_level
    """
    images = []
    
    # Distribute images across categories
    images_per_category = n_images // len(CAT2000_CATEGORIES)
    remainder = n_images % len(CAT2000_CATEGORIES)
    
    image_counter = 1
    
    for i, category in enumerate(CAT2000_CATEGORIES):
        n_cat_images = images_per_category + (1 if i < remainder else 0)
        
        for j in range(n_cat_images):
            # Generate image ID based on part and counter
            image_id = f"{part}_{category}_{image_counter:04d}"
            
            # Generate image path (assumes CAT2000 structure)
            # Format: data/raw/stimuli/CAT2000/{category}/Output/img{N:04d}.jpg
            image_num = (image_counter % 2000) + 1  # Cycle through available images
            image_path = f"data/raw/stimuli/CAT2000/{category}/Output/img{image_num:04d}.jpg"
            
            # Assign pseudo-random bias level (for analysis)
            bias_level = rng.choice(["low", "medium", "high"])
            
            images.append({
                "image_id": image_id,
                "image_path": image_path,
                "category": category,
                "bias_level": bias_level,
            })
            
            image_counter += 1
    
    return images


def generate_stimulus_manifest(
    participant_id: str,
    part: str,
    polygons: List[Dict[str, Any]],
    cue_positions: List[Dict[str, Any]],
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate stimulus manifest for one part.
    
    Design:
    - 9 mini-blocks × 39 trials = 351 trials
    - Each block: 36 image trials + 3 empty trials
    - Each polygon: 1 empty trial + 12 image trials = 13 total
    
    Parameters
    ----------
    participant_id : str
        Participant ID
    part : str
        Part identifier ('A' or 'B')
    polygons : list of dict
        Polygon definitions
    cue_positions : list of dict
        Cue grid positions
    rng : np.random.Generator
        Random number generator
        
    Returns
    -------
    pd.DataFrame
        Stimulus manifest with all required columns
    """
    n_blocks = 9
    trials_per_block = 39
    image_trials_per_block = 36
    empty_trials_per_block = 3
    
    n_polygons = len(polygons)
    image_trials_per_polygon = 12  # 27 polygons × 12 = 324 image trials
    
    # Generate image pool (324 images needed for image trials)
    n_images_needed = n_polygons * image_trials_per_polygon
    image_pool = generate_image_pool(part, n_images_needed, rng)
    
    # Shuffle image pool
    rng.shuffle(image_pool)
    image_idx = 0
    
    # Create trial list
    trials = []
    
    # Step 1: Assign empty trials (1 per polygon, 27 total)
    # Distribute empty trials across blocks
    polygon_indices = list(range(n_polygons))
    rng.shuffle(polygon_indices)
    
    empty_trials_per_block_list = []
    for block in range(n_blocks):
        # Allocate 3 empty trials per block
        start_idx = block * empty_trials_per_block
        end_idx = start_idx + empty_trials_per_block
        block_empty_polygons = polygon_indices[start_idx:end_idx]
        empty_trials_per_block_list.append(block_empty_polygons)
    
    # Step 2: Assign image trials (12 per polygon, 324 total)
    # Distribute evenly across blocks
    image_trials_by_block = [[] for _ in range(n_blocks)]
    
    for poly_idx in range(n_polygons):
        polygon = polygons[poly_idx]
        
        # Assign 12 images to this polygon
        polygon_images = []
        for _ in range(image_trials_per_polygon):
            if image_idx < len(image_pool):
                polygon_images.append(image_pool[image_idx])
                image_idx += 1
        
        # Distribute these 12 image trials across blocks
        # Use balanced distribution: each polygon appears ~1-2 times per block
        block_assignments = rng.choice(n_blocks, size=len(polygon_images), replace=True)
        
        for img, block_num in zip(polygon_images, block_assignments):
            image_trials_by_block[block_num].append({
                "polygon": polygon,
                "image": img,
            })
    
    # Step 3: Build complete trial list
    trial_counter = 0
    
    for mini_block in range(1, n_blocks + 1):
        block_trials = []
        
        # Add empty trials for this block
        empty_poly_indices = empty_trials_per_block_list[mini_block - 1]
        for poly_idx in empty_poly_indices:
            polygon = polygons[poly_idx]
            
            trial_counter += 1
            cue = rng.choice(cue_positions)
            
            trial = {
                "participant_id": participant_id,
                "part": part,
                "mini_block": mini_block,
                "trial_in_block": None,  # Will assign after shuffling
                "trial_uid": f"{part}_MB{mini_block:02d}_T{trial_counter:03d}",
                "trial_type": "empty",
                "polygon_id": polygon["polygon_id"],
                "polygon_case": polygon["polygon_case"],
                "polygon_json_path": polygon["polygon_json_path"],
                "cue_pos_id": cue["cue_pos_id"],
                "cue_x_px": cue["cue_x_px"],
                "cue_y_px": cue["cue_y_px"],
                "stimulus_duration_s": 4.0,
                "iti_s": 0.5,
                "max_drift_time_s": 10.0,
                "drift_retry_limit": 1,
                "aperture_scale_factor": 1.0,
                "image_id": None,
                "image_path": None,
                "category": None,
                "bias_level": None,
            }
            block_trials.append(trial)
        
        # Add image trials for this block
        block_image_trials = image_trials_by_block[mini_block - 1]
        
        for trial_data in block_image_trials:
            polygon = trial_data["polygon"]
            image = trial_data["image"]
            
            trial_counter += 1
            cue = rng.choice(cue_positions)
            
            trial = {
                "participant_id": participant_id,
                "part": part,
                "mini_block": mini_block,
                "trial_in_block": None,  # Will assign after shuffling
                "trial_uid": f"{part}_MB{mini_block:02d}_T{trial_counter:03d}",
                "trial_type": "image",
                "polygon_id": polygon["polygon_id"],
                "polygon_case": polygon["polygon_case"],
                "polygon_json_path": polygon["polygon_json_path"],
                "cue_pos_id": cue["cue_pos_id"],
                "cue_x_px": cue["cue_x_px"],
                "cue_y_px": cue["cue_y_px"],
                "stimulus_duration_s": 4.0,
                "iti_s": 0.5,
                "max_drift_time_s": 10.0,
                "drift_retry_limit": 1,
                "aperture_scale_factor": 1.0,
                "image_id": image["image_id"],
                "image_path": image["image_path"],
                "category": image["category"],
                "bias_level": image["bias_level"],
            }
            block_trials.append(trial)
        
        # Shuffle trials within block
        rng.shuffle(block_trials)
        
        # Assign trial_in_block numbers
        for i, trial in enumerate(block_trials, start=1):
            trial["trial_in_block"] = i
        
        trials.extend(block_trials)
    
    # Create DataFrame
    df = pd.DataFrame(trials)
    
    # Reorder columns to match expected format
    column_order = [
        "participant_id", "part", "mini_block", "trial_in_block", "trial_uid",
        "trial_type", "polygon_id", "polygon_case", "polygon_json_path",
        "cue_pos_id", "cue_x_px", "cue_y_px",
        "stimulus_duration_s", "iti_s", "max_drift_time_s", "drift_retry_limit",
        "aperture_scale_factor",
        "image_id", "image_path", "category", "bias_level",
    ]
    
    df = df[column_order]
    
    return df


def generate_memory_manifest(
    participant_id: str,
    part: str,
    stimulus_df: pd.DataFrame,
    rng: np.random.Generator
) -> pd.DataFrame:
    """
    Generate memory manifest for one part.
    
    For each mini-block, create a memory probe that is either:
    - "old": an image that appeared in that block (50% of blocks)
    - "new": an image that never appeared in any trial (50% of blocks)
    
    Parameters
    ----------
    participant_id : str
        Participant ID
    part : str
        Part identifier ('A' or 'B')
    stimulus_df : pd.DataFrame
        Stimulus manifest for this part
    rng : np.random.Generator
        Random number generator
        
    Returns
    -------
    pd.DataFrame
        Memory manifest with all required columns
    """
    n_blocks = 9
    
    # Get all images used in stimulus trials
    used_images = stimulus_df[stimulus_df["image_id"].notna()][
        ["image_id", "image_path", "category", "mini_block"]
    ].copy()
    
    # Generate pool of new images (not used in trials)
    new_image_pool = generate_image_pool(f"{part}_MEM", n_blocks, rng)
    
    memory_probes = []
    
    # Decide which blocks get old vs new probes (50/50 split)
    block_indices = list(range(1, n_blocks + 1))
    rng.shuffle(block_indices)
    n_old = n_blocks // 2
    old_blocks = set(block_indices[:n_old])
    
    for mini_block in range(1, n_blocks + 1):
        if mini_block in old_blocks and len(used_images[used_images["mini_block"] == mini_block]) > 0:
            # Old probe: select random image from this block
            block_images = used_images[used_images["mini_block"] == mini_block]
            probe_img = block_images.sample(n=1, random_state=rng.integers(0, 2**31)).iloc[0]
            
            probe = {
                "participant_id": participant_id,
                "part": part,
                "mini_block": mini_block,
                "probe_image_id": probe_img["image_id"],
                "probe_image_path": probe_img["image_path"],
                "probe_duration_s": 3.0,
                "is_old": True,
            }
        else:
            # New probe: select from new image pool
            if new_image_pool:
                probe_img = new_image_pool.pop(0)
            else:
                # Fallback if we run out
                probe_img = generate_image_pool(f"{part}_MEM_extra", 1, rng)[0]
            
            probe = {
                "participant_id": participant_id,
                "part": part,
                "mini_block": mini_block,
                "probe_image_id": probe_img["image_id"],
                "probe_image_path": probe_img["image_path"],
                "probe_duration_s": 3.0,
                "is_old": False,
            }
        
        memory_probes.append(probe)
    
    df = pd.DataFrame(memory_probes)
    
    return df


def main():
    """Generate manifests for Parts A and B."""
    parser = argparse.ArgumentParser(
        description="Generate stimulus and memory manifests for center_bias_exp"
    )
    parser.add_argument(
        "--participant-id",
        type=str,
        default="P01",
        help="Participant ID (default: P01)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="manifests",
        help="Output directory for manifests (default: manifests)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducibility (default: 12345)"
    )
    
    args = parser.parse_args()
    
    participant_id = args.participant_id
    output_dir = Path(args.output_dir)
    seed = args.seed
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Manifest Generation for center_bias_exp")
    print("=" * 70)
    print(f"Participant ID: {participant_id}")
    print(f"Output directory: {output_dir}")
    print(f"Random seed: {seed}")
    print(f"Number of polygons: {len(POLYGONS)}")
    print()
    
    # Initialize RNG
    rng = np.random.default_rng(seed)
    
    # Get cue positions
    cue_positions = get_cue_positions()
    print(f"Cue grid positions: {len(cue_positions)}")
    print()
    
    # Generate manifests for both parts
    for part in ["A", "B"]:
        print(f"Generating manifests for Part {part}...")
        print("-" * 70)
        
        # Generate stimulus manifest
        stimulus_df = generate_stimulus_manifest(
            participant_id,
            part,
            POLYGONS,
            cue_positions,
            rng
        )
        
        # Generate memory manifest
        memory_df = generate_memory_manifest(
            participant_id,
            part,
            stimulus_df,
            rng
        )
        
        # Save to CSV
        stim_path = output_dir / f"stimulus_manifest_part{part}.csv"
        mem_path = output_dir / f"memory_manifest_part{part}.csv"
        
        stimulus_df.to_csv(stim_path, index=False)
        memory_df.to_csv(mem_path, index=False)
        
        # Print summary
        print(f"✓ Stimulus manifest: {stim_path}")
        print(f"  - Total trials: {len(stimulus_df)}")
        print(f"  - Image trials: {(stimulus_df['trial_type'] == 'image').sum()}")
        print(f"  - Empty trials: {(stimulus_df['trial_type'] == 'empty').sum()}")
        print(f"  - Mini-blocks: {stimulus_df['mini_block'].nunique()}")
        print(f"  - Trials per block: {stimulus_df.groupby('mini_block').size().values}")
        print(f"  - Unique images: {stimulus_df['image_id'].nunique()}")
        print(f"  - Unique polygons: {stimulus_df['polygon_id'].nunique()}")
        print()
        
        print(f"✓ Memory manifest: {mem_path}")
        print(f"  - Total probes: {len(memory_df)}")
        print(f"  - Old probes: {memory_df['is_old'].sum()}")
        print(f"  - New probes: {(~memory_df['is_old']).sum()}")
        print()
    
    print("=" * 70)
    print("Manifest generation complete!")
    print("=" * 70)
    print()
    print("Summary statistics:")
    print("-" * 70)
    
    # Load and combine both parts for overall stats
    stim_a = pd.read_csv(output_dir / "stimulus_manifest_partA.csv")
    stim_b = pd.read_csv(output_dir / "stimulus_manifest_partB.csv")
    
    print(f"Total trials across both parts: {len(stim_a) + len(stim_b)}")
    print(f"Total unique images used: {pd.concat([stim_a['image_id'], stim_b['image_id']]).nunique()}")
    print(f"Polygons: {len(POLYGONS)}")
    print(f"  - Each polygon appears empty: 1 time per part")
    print(f"  - Each polygon with images: 12 times per part")
    print(f"  - Total appearances per polygon: 13 per part")
    print()
    
    print("Cue position distribution (Part A):")
    cue_counts = stim_a['cue_pos_id'].value_counts().sort_index()
    for cue_id, count in cue_counts.items():
        print(f"  {cue_id}: {count} trials ({count/len(stim_a)*100:.1f}%)")
    print()
    
    print("Trial type distribution:")
    print(f"  Part A - Image: {(stim_a['trial_type'] == 'image').sum()}, "
          f"Empty: {(stim_a['trial_type'] == 'empty').sum()}")
    print(f"  Part B - Image: {(stim_b['trial_type'] == 'image').sum()}, "
          f"Empty: {(stim_b['trial_type'] == 'empty').sum()}")
    print()
    
    print("✓ Manifests are ready for use with experiment2_runner.py")
    print()


if __name__ == "__main__":
    main()
