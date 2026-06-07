"""
Plot P02 trials showing:
- Masked images exactly as shown in experiment
- Fixation 0: The last fixation DURING CUE phase (before STIM_ON)
- Fixation 2: The second fixation AFTER STIM_ON (during stimulus viewing)

Saves to outputs/p02_cue_stim_fixations/
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Circle
from PIL import Image, ImageDraw
import json
from pathlib import Path
import re

# Constants
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
SCREEN_CENTER_X = SCREEN_WIDTH // 2  # 1920
SCREEN_CENTER_Y = SCREEN_HEIGHT // 2  # 1080
APERTURE_SCALE = 1987
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080

# Paths
P02_SESSION = Path("data/raw/participant_P02/part_A/session_20260115_103203")
TRIALS_CSV = P02_SESSION / "logs_trial/trials.csv"
EDF_DIR = P02_SESSION / "edf"
GEOM_CSV = Path("manifests/polygon_geometry.csv")
OUTPUT_DIR = Path("outputs/p02_cue_stim_fixations")


def parse_asc_with_phases(asc_path):
    """
    Parse ASC file and separate fixations by phase (cue vs stimulus).
    
    Returns dict: {trial_uid: {'cue_fixations': [...], 'stim_fixations': [...]}}
    """
    trials = {}
    current_trial = None
    stim_on_time = None
    trial_end_time = None
    
    with open(asc_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Look for TRIALID marker
            if 'TRIALID' in line and 'MSG' in line:
                match = re.search(r'TRIALID\s+(\S+)', line)
                if match:
                    current_trial = match.group(1)
                    trials[current_trial] = {
                        'cue_fixations': [],
                        'stim_fixations': [],
                        'stim_on_time': None
                    }
                    stim_on_time = None
                    # Extract timestamp
                    ts_match = re.match(r'MSG\s+(\d+)', line)
                    if ts_match:
                        trials[current_trial]['trial_start_time'] = int(ts_match.group(1))
            
            # Look for STIM_ON marker
            elif 'STIM_ON' in line and 'MSG' in line and current_trial:
                ts_match = re.match(r'MSG\s+(\d+)', line)
                if ts_match:
                    stim_on_time = int(ts_match.group(1))
                    trials[current_trial]['stim_on_time'] = stim_on_time
            
            # Look for TRIAL_END marker
            elif 'TRIAL_END' in line and 'MSG' in line and current_trial:
                ts_match = re.match(r'MSG\s+(\d+)', line)
                if ts_match:
                    trial_end_time = int(ts_match.group(1))
                    trials[current_trial]['trial_end_time'] = trial_end_time
                # Reset for next trial
                current_trial = None
                stim_on_time = None
            
            # Parse fixation events (EFIX)
            elif line.startswith('EFIX') and current_trial:
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        # EFIX R start end duration x y pupil
                        fix_start = int(parts[2])
                        fix_end = int(parts[3])
                        duration = int(parts[4])
                        x = float(parts[5])
                        y = float(parts[6])
                        
                        fix_data = {
                            'x': x, 'y': y,
                            'start': fix_start, 'end': fix_end,
                            'duration': duration
                        }
                        
                        # Classify by phase
                        if stim_on_time is None:
                            # Before STIM_ON -> cue phase
                            trials[current_trial]['cue_fixations'].append(fix_data)
                        else:
                            # After STIM_ON -> stimulus phase
                            trials[current_trial]['stim_fixations'].append(fix_data)
                    except (ValueError, IndexError):
                        pass
    
    return trials


def load_polygon_vertices(json_path, scale=APERTURE_SCALE):
    """Load polygon vertices from JSON and scale to aperture size."""
    full_path = Path(json_path)
    if not full_path.exists():
        full_path = Path("data/raw/stimuli/polygons") / Path(json_path).name
    
    if not full_path.exists():
        return None
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    # Handle different JSON formats
    if 'vertices_xy' in data:
        vertices = np.array(data['vertices_xy'])
    elif 'theta' in data:
        theta_data = data['theta']
        
        # Check if theta is a dict (new format) or list (old consolidated format)
        if isinstance(theta_data, dict):
            # New format: dict with angles_deg and radii_norm
            angles = np.array(theta_data['angles_deg']) * np.pi / 180
            radii = np.array(theta_data['radii_norm'])
        elif isinstance(theta_data, list):
            # Old consolidated format: theta is list of radii at evenly spaced angles
            n_points = len(theta_data)
            angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
            # theta values are radii in some unit - need to normalize
            radii = np.array(theta_data)
            # Normalize radii to -1 to 1 range
            max_radius = np.max(np.abs(radii))
            if max_radius > 0:
                radii = radii / max_radius
        else:
            return None
        
        vertices = np.column_stack([
            radii * np.cos(angles),
            radii * np.sin(angles)
        ])
    else:
        return None
    
    # Vertices are normalized (-1 to 1), scale to aperture
    vertices_scaled = vertices * (scale / 2)
    
    # Convert to screen coordinates (center at screen center)
    vertices_screen = vertices_scaled.copy()
    vertices_screen[:, 0] += SCREEN_CENTER_X
    vertices_screen[:, 1] += SCREEN_CENTER_Y
    
    return vertices_screen


def create_masked_stimulus(image_path, vertices_screen, trial_type):
    """
    Create masked stimulus exactly as shown in experiment.
    Returns PIL Image positioned at screen center.
    """
    if trial_type == 'empty' or pd.isna(image_path) or not Path(image_path).exists():
        # Empty trial - create black polygon on gray background
        result = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), (128, 128, 128, 255))
        if vertices_screen is not None:
            draw = ImageDraw.Draw(result)
            poly_points = [tuple(p) for p in vertices_screen]
            draw.polygon(poly_points, fill=(0, 0, 0, 255), outline=(255, 255, 255))
        return result
    
    # Load image
    img = Image.open(image_path).convert('RGBA')
    img_w, img_h = img.size  # 1920x1080
    
    # Create full screen canvas with gray background
    result = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), (128, 128, 128, 255))
    
    if vertices_screen is None:
        # No polygon - just center the image
        img_left = SCREEN_CENTER_X - img_w // 2
        img_top = SCREEN_CENTER_Y - img_h // 2
        result.paste(img, (img_left, img_top))
        return result
    
    # Calculate polygon bounds in image space
    # Image is centered at screen center
    img_left = SCREEN_CENTER_X - img_w // 2
    img_top = SCREEN_CENTER_Y - img_h // 2
    
    # Convert polygon screen coords to image coords
    poly_in_img = vertices_screen.copy()
    poly_in_img[:, 0] -= img_left
    poly_in_img[:, 1] -= img_top
    
    # Create mask for the image
    mask = Image.new('L', (img_w, img_h), 0)
    draw = ImageDraw.Draw(mask)
    poly_points = [tuple(p) for p in poly_in_img]
    draw.polygon(poly_points, fill=255)
    
    # Apply mask to image
    masked_img = Image.new('RGBA', (img_w, img_h), (128, 128, 128, 255))
    masked_img.paste(img, (0, 0), mask)
    
    # Paste masked image onto canvas
    result.paste(masked_img, (img_left, img_top))
    
    return result


def plot_trial_with_cue_and_stim_fix(trial_row, geom_dict, trial_fixations, output_dir):
    """
    Plot trial showing masked image with cue fixation and 2nd stimulus fixation.
    """
    trial_uid = trial_row['trial_uid']
    trial_type = trial_row['trial_type']
    polygon_id = trial_row['polygon_id']
    polygon_case = trial_row['polygon_case']
    json_path = trial_row['polygon_json_path']
    
    # Load polygon vertices
    vertices = load_polygon_vertices(json_path)
    
    # Create masked stimulus
    image_path = trial_row.get('image_path', None)
    stimulus = create_masked_stimulus(image_path, vertices, trial_type)
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(19.2, 10.8), dpi=100)
    ax.set_xlim(0, SCREEN_WIDTH)
    ax.set_ylim(SCREEN_HEIGHT, 0)  # Flip Y axis
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Display stimulus
    ax.imshow(stimulus, extent=[0, SCREEN_WIDTH, SCREEN_HEIGHT, 0])
    
    # Plot centers
    centers_plotted = []
    
    # Screen center
    ax.scatter([SCREEN_CENTER_X], [SCREEN_CENTER_Y], c='yellow', s=300, 
               marker='*', label='Screen Center', zorder=10, edgecolors='black', linewidths=1)
    centers_plotted.append(('SCREEN', SCREEN_CENTER_X, SCREEN_CENTER_Y))
    
    def is_valid(val):
        if val is None:
            return False
        try:
            return pd.notna(val)
        except:
            return val is not None
    
    # Plot polygon centers
    if is_valid(geom_dict.get('center_com_x_canonical_px')):
        cx = SCREEN_CENTER_X + geom_dict['center_com_x_canonical_px']
        cy = SCREEN_CENTER_Y + geom_dict['center_com_y_canonical_px']
        ax.scatter([cx], [cy], c='red', s=200, marker='o', label='COM', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('COM', cx, cy))
    
    if is_valid(geom_dict.get('center_bbc_x_canonical_px')):
        cx = SCREEN_CENTER_X + geom_dict['center_bbc_x_canonical_px']
        cy = SCREEN_CENTER_Y + geom_dict['center_bbc_y_canonical_px']
        ax.scatter([cx], [cy], c='blue', s=200, marker='s', label='BBC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('BBC', cx, cy))
    
    if is_valid(geom_dict.get('center_chc_x_canonical_px')):
        cx = SCREEN_CENTER_X + geom_dict['center_chc_x_canonical_px']
        cy = SCREEN_CENTER_Y + geom_dict['center_chc_y_canonical_px']
        ax.scatter([cx], [cy], c='green', s=200, marker='^', label='CHC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('CHC', cx, cy))
    
    if is_valid(geom_dict.get('center_icc_x_canonical_px')):
        cx = SCREEN_CENTER_X + geom_dict['center_icc_x_canonical_px']
        cy = SCREEN_CENTER_Y + geom_dict['center_icc_y_canonical_px']
        ax.scatter([cx], [cy], c='magenta', s=200, marker='D', label='ICC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('ICC', cx, cy))
    
    # Plot cue position
    cue_x = trial_row['cue_x_px']
    cue_y = trial_row['cue_y_px']
    ax.scatter([cue_x], [cue_y], c='orange', s=400, marker='+', 
               label=f'Cue Position', zorder=11, linewidths=4)
    
    # Get fixations
    cue_fixations = trial_fixations.get('cue_fixations', [])
    stim_fixations = trial_fixations.get('stim_fixations', [])
    
    # Plot CUE FIXATION (last fixation during cue phase - closest to stimulus onset)
    cue_fix_plotted = False
    if cue_fixations:
        # Use the LAST cue fixation (most representative of where they were looking)
        last_cue_fix = cue_fixations[-1]
        fix_x, fix_y = last_cue_fix['x'], last_cue_fix['y']
        ax.scatter([fix_x], [fix_y], c='cyan', s=500, marker='o', 
                   label=f'Cue Fixation (last during cue)', zorder=12, 
                   edgecolors='black', linewidths=3, alpha=0.8)
        cue_fix_plotted = True
        
        # Draw line from cue position to cue fixation
        ax.plot([cue_x, fix_x], [cue_y, fix_y], '--', color='cyan', alpha=0.5, linewidth=2)
        
        # Calculate distance
        cue_fix_dist = np.sqrt((fix_x - cue_x)**2 + (fix_y - cue_y)**2)
    else:
        cue_fix_dist = None
    
    # Plot STIMULUS FIXATION #2 (second fixation after stimulus onset)
    stim_fix_plotted = False
    if len(stim_fixations) >= 2:
        fix2 = stim_fixations[1]  # Index 1 = second fixation
        fix_x, fix_y = fix2['x'], fix2['y']
        ax.scatter([fix_x], [fix_y], c='white', s=500, marker='X', 
                   label=f'Stim Fix #2', zorder=12, 
                   edgecolors='black', linewidths=3)
        stim_fix_plotted = True
        
        # Find closest center
        min_dist = float('inf')
        closest_center = 'N/A'
        for name, cx, cy in centers_plotted:
            dist = np.sqrt((fix_x - cx)**2 + (fix_y - cy)**2)
            if dist < min_dist:
                min_dist = dist
                closest_center = name
    else:
        closest_center = 'N/A'
        min_dist = None
    
    # Title
    title = f"{trial_uid} | {polygon_id} ({polygon_case}) | Type: {trial_type}\n"
    title += f"Cue: {trial_row['cue_pos_id']} | "
    if cue_fix_dist is not None:
        title += f"Cue Fix Dist: {cue_fix_dist:.0f}px | "
    title += f"Cue fixes: {len(cue_fixations)} | Stim fixes: {len(stim_fixations)}"
    if stim_fix_plotted:
        title += f" | Fix#2 closest to: {closest_center} ({min_dist:.0f}px)"
    
    ax.set_title(title, fontsize=11, fontweight='bold', color='white', 
                 bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    # Legend
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9, facecolor='black', 
              labelcolor='white', edgecolor='white')
    
    # Save
    output_path = output_dir / f"{trial_uid}.png"
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#404040', 
                pad_inches=0.1)
    plt.close()
    
    return output_path, cue_fix_dist, len(cue_fixations), len(stim_fixations)


def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load trial data
    print("Loading trial data...")
    trials_df = pd.read_csv(TRIALS_CSV)
    print(f"Loaded {len(trials_df)} trials")
    
    # Load geometry data
    print("Loading geometry data...")
    geom_df = pd.read_csv(GEOM_CSV)
    
    # Parse fixations from ASC files
    print("\nParsing fixation data from ASC files...")
    all_fixations = {}
    
    for asc_file in EDF_DIR.glob("*.asc"):
        print(f"  Processing {asc_file.name}...")
        fixations = parse_asc_with_phases(asc_file)
        all_fixations.update(fixations)
        print(f"    Found data for {len(fixations)} trials")
    
    print(f"Total fixation data for {len(all_fixations)} trials")
    
    # Process each trial
    print("\nGenerating plots...")
    results = []
    
    for idx, trial_row in trials_df.iterrows():
        trial_uid = trial_row['trial_uid']
        polygon_id = trial_row['polygon_id']
        
        # Skip aborted trials
        if trial_row.get('aborted', False):
            print(f"  Skipping aborted trial {trial_uid}")
            continue
        
        # Get geometry for this polygon
        geom_match = geom_df[geom_df['polygon_id'] == polygon_id]
        if len(geom_match) == 0:
            geom_dict = {}
        else:
            geom_dict = geom_match.iloc[0].to_dict()
        
        # Get fixations for this trial
        trial_fixations = all_fixations.get(trial_uid, {'cue_fixations': [], 'stim_fixations': []})
        
        try:
            output_path, cue_dist, n_cue, n_stim = plot_trial_with_cue_and_stim_fix(
                trial_row, geom_dict, trial_fixations, OUTPUT_DIR
            )
            print(f"  {trial_uid}: cue_dist={cue_dist:.0f}px, cue_fixes={n_cue}, stim_fixes={n_stim}" if cue_dist else f"  {trial_uid}: no cue fix, stim_fixes={n_stim}")
            
            results.append({
                'trial_uid': trial_uid,
                'cue_fix_distance_px': cue_dist,
                'n_cue_fixations': n_cue,
                'n_stim_fixations': n_stim
            })
        except Exception as e:
            print(f"  Error plotting {trial_uid}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save results summary
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "fixation_summary.csv", index=False)
    
    # Print summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    if len(results_df) > 0:
        print(f"Trials processed: {len(results_df)}")
        print(f"Mean cue fixation distance: {results_df['cue_fix_distance_px'].mean():.1f}px")
        print(f"Trials with cue fix within 100px of cue: {(results_df['cue_fix_distance_px'] < 100).sum()}")
        print(f"Trials with cue fix within 200px of cue: {(results_df['cue_fix_distance_px'] < 200).sum()}")
    
    print(f"\nPlots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
