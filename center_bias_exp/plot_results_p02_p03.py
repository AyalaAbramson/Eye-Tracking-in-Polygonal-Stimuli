"""
Plot experiment results for P02 and P03:
- Masked stimuli exactly as shown in experiment
- All polygon centers (COM, BBC, CHC, ICC with proper inscribed circle)
- Cue fixation (last fixation before STIM_ON)
- Fixation #2 (second fixation after STIM_ON)

Outputs:
1. Per-participant plots: outputs/results_by_participant/{participant}/
2. Per-stimulus plots (both participants): outputs/results_by_stimulus/
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
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon as ShapelyPolygon
from shapely import maximum_inscribed_circle

# Constants
SCREEN_WIDTH = 3840
SCREEN_HEIGHT = 2160
SCREEN_CENTER_X = SCREEN_WIDTH // 2  # 1920
SCREEN_CENTER_Y = SCREEN_HEIGHT // 2  # 1080
APERTURE_SCALE = 1987
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080

# Session paths
SESSIONS = {
    'P02': Path("data/raw/participant_P02/part_A/session_20260115_103203"),
    'P03': Path("data/raw/participant_P03/part_A/session_20260115_131914"),
}

# Output directories
OUTPUT_BY_PARTICIPANT = Path("outputs/results_by_participant")
OUTPUT_BY_STIMULUS = Path("outputs/results_by_stimulus")


def parse_asc_with_phases(asc_path):
    """
    Parse ASC file and separate fixations by phase (cue vs stimulus).
    
    Returns dict: {trial_uid: {'cue_fixations': [...], 'stim_fixations': [...]}}
    """
    trials = {}
    current_trial = None
    stim_on_time = None
    
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
                current_trial = None
                stim_on_time = None
            
            # Parse fixation events (EFIX)
            elif line.startswith('EFIX') and current_trial:
                parts = line.split()
                if len(parts) >= 7:
                    try:
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
                        
                        if stim_on_time is None:
                            trials[current_trial]['cue_fixations'].append(fix_data)
                        else:
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
        
        if isinstance(theta_data, dict):
            angles = np.array(theta_data['angles_deg']) * np.pi / 180
            radii = np.array(theta_data['radii_norm'])
        elif isinstance(theta_data, list):
            n_points = len(theta_data)
            angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
            radii = np.array(theta_data)
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
    
    # Calculate current bounding box and normalize
    min_xy = vertices.min(axis=0)
    max_xy = vertices.max(axis=0)
    current_width = max_xy[0] - min_xy[0]
    current_height = max_xy[1] - min_xy[1]
    current_max_dim = max(current_width, current_height)
    
    # Center the polygon
    center_x = (min_xy[0] + max_xy[0]) / 2
    center_y = (min_xy[1] + max_xy[1]) / 2
    
    # Normalize and scale to aperture size
    if current_max_dim > 0:
        normalize_scale = scale / current_max_dim
    else:
        normalize_scale = scale
    
    vertices_scaled = np.column_stack([
        (vertices[:, 0] - center_x) * normalize_scale,
        (vertices[:, 1] - center_y) * normalize_scale
    ])
    
    # Convert to screen coordinates (center at screen center)
    vertices_screen = vertices_scaled.copy()
    vertices_screen[:, 0] += SCREEN_CENTER_X
    vertices_screen[:, 1] += SCREEN_CENTER_Y
    
    return vertices_screen


def calculate_polygon_centers(vertices_screen):
    """
    Calculate all polygon centers from screen-space vertices.
    
    Returns dict with:
    - SCREEN: Screen center
    - COM: Center of mass (centroid)
    - BBC: Bounding box center
    - CHC: Convex hull centroid
    - ICC: Inscribed circle center (largest circle that fits inside)
    """
    centers = {}
    
    # Screen center
    centers['SCREEN'] = (SCREEN_CENTER_X, SCREEN_CENTER_Y)
    
    if vertices_screen is None or len(vertices_screen) < 3:
        return centers
    
    # Convert to polygon-centered coords for calculations
    verts = vertices_screen - np.array([SCREEN_CENTER_X, SCREEN_CENTER_Y])
    
    # COM - Center of mass (centroid using shoelace formula)
    n = len(verts)
    area = 0
    cx = 0
    cy = 0
    for i in range(n):
        j = (i + 1) % n
        cross = verts[i, 0] * verts[j, 1] - verts[j, 0] * verts[i, 1]
        area += cross
        cx += (verts[i, 0] + verts[j, 0]) * cross
        cy += (verts[i, 1] + verts[j, 1]) * cross
    area = area / 2
    if abs(area) > 1e-10:
        cx = cx / (6 * area)
        cy = cy / (6 * area)
    else:
        cx = np.mean(verts[:, 0])
        cy = np.mean(verts[:, 1])
    centers['COM'] = (SCREEN_CENTER_X + cx, SCREEN_CENTER_Y + cy)
    
    # BBC - Bounding box center
    min_x, min_y = verts.min(axis=0)
    max_x, max_y = verts.max(axis=0)
    bbc_x = (min_x + max_x) / 2
    bbc_y = (min_y + max_y) / 2
    centers['BBC'] = (SCREEN_CENTER_X + bbc_x, SCREEN_CENTER_Y + bbc_y)
    
    # CHC - Convex hull centroid
    try:
        hull = ConvexHull(verts)
        hull_points = verts[hull.vertices]
        chc_x = np.mean(hull_points[:, 0])
        chc_y = np.mean(hull_points[:, 1])
        centers['CHC'] = (SCREEN_CENTER_X + chc_x, SCREEN_CENTER_Y + chc_y)
    except:
        centers['CHC'] = centers['COM']
    
    # ICC - Maximum inscribed circle center using shapely
    try:
        # Create shapely polygon from vertices
        shapely_poly = ShapelyPolygon(verts)
        # Get maximum inscribed circle - returns a LineString where:
        # - first point is the center of the inscribed circle
        # - second point is the nearest point on the boundary
        # - the line length is the radius
        mic_line = maximum_inscribed_circle(shapely_poly)
        coords = list(mic_line.coords)
        icc_center_x, icc_center_y = coords[0]  # First point is center
        icc_radius = mic_line.length  # Length of line is the radius
        centers['ICC'] = (SCREEN_CENTER_X + icc_center_x, SCREEN_CENTER_Y + icc_center_y)
        centers['ICC_radius'] = icc_radius
    except Exception as e:
        print(f"    ICC calculation error: {e}")
        centers['ICC'] = centers['COM']
        centers['ICC_radius'] = 0
    
    return centers


def create_masked_stimulus(image_path, vertices_screen, trial_type):
    """Create masked stimulus exactly as shown in experiment."""
    if trial_type == 'empty' or pd.isna(image_path) or not Path(image_path).exists():
        result = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), (128, 128, 128, 255))
        if vertices_screen is not None:
            draw = ImageDraw.Draw(result)
            poly_points = [tuple(p) for p in vertices_screen.astype(int)]
            draw.polygon(poly_points, fill=(0, 0, 0, 255), outline=(255, 255, 255))
        return result
    
    img = Image.open(image_path).convert('RGBA')
    img_w, img_h = img.size
    
    result = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), (128, 128, 128, 255))
    
    if vertices_screen is None:
        img_left = SCREEN_CENTER_X - img_w // 2
        img_top = SCREEN_CENTER_Y - img_h // 2
        result.paste(img, (img_left, img_top))
        return result
    
    img_left = SCREEN_CENTER_X - img_w // 2
    img_top = SCREEN_CENTER_Y - img_h // 2
    
    # Convert polygon screen coords to image coords
    poly_in_img = vertices_screen.copy()
    poly_in_img[:, 0] -= img_left
    poly_in_img[:, 1] -= img_top
    
    # Create mask
    mask = Image.new('L', (img_w, img_h), 0)
    draw = ImageDraw.Draw(mask)
    poly_points = [tuple(p) for p in poly_in_img.astype(int)]
    draw.polygon(poly_points, fill=255)
    
    # Apply mask
    masked_img = Image.new('RGBA', (img_w, img_h), (128, 128, 128, 255))
    masked_img.paste(img, (0, 0), mask)
    
    result.paste(masked_img, (img_left, img_top))
    
    return result


def plot_trial(trial_row, vertices, centers, trial_fixations, participant_id, output_dir, 
               other_participant_fix=None, other_participant_id=None):
    """
    Plot trial with masked stimulus, centers, and fixations.
    """
    trial_uid = trial_row['trial_uid']
    trial_type = trial_row['trial_type']
    polygon_id = trial_row['polygon_id']
    polygon_case = trial_row['polygon_case']
    image_path = trial_row.get('image_path', None)
    
    # Create masked stimulus
    stimulus = create_masked_stimulus(image_path, vertices, trial_type)
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(19.2, 10.8), dpi=100)
    ax.set_xlim(0, SCREEN_WIDTH)
    ax.set_ylim(SCREEN_HEIGHT, 0)  # Flip Y axis
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Display stimulus
    ax.imshow(stimulus, extent=[0, SCREEN_WIDTH, SCREEN_HEIGHT, 0])
    
    # Plot polygon outline
    if vertices is not None:
        polygon_patch = MplPolygon(vertices, fill=False, edgecolor='white', 
                                   linewidth=2, linestyle='--', alpha=0.5)
        ax.add_patch(polygon_patch)
    
    # Plot centers with distinct markers
    center_styles = {
        'SCREEN': {'color': 'yellow', 'marker': '*', 'size': 400, 'label': 'Screen'},
        'COM': {'color': 'red', 'marker': 'o', 'size': 250, 'label': 'COM'},
        'BBC': {'color': 'blue', 'marker': 's', 'size': 200, 'label': 'BBC'},
        'CHC': {'color': 'green', 'marker': '^', 'size': 200, 'label': 'CHC'},
        'ICC': {'color': 'magenta', 'marker': 'D', 'size': 200, 'label': 'ICC'},
    }
    
    for center_name, value in centers.items():
        if center_name == 'ICC_radius':
            continue
        if not isinstance(value, tuple) or len(value) != 2:
            continue
        cx, cy = value
        style = center_styles.get(center_name, {'color': 'white', 'marker': 'x', 'size': 100})
        ax.scatter([cx], [cy], c=style['color'], s=style['size'], 
                   marker=style['marker'], label=style['label'], 
                   zorder=10, edgecolors='black', linewidths=1)
    
    # Draw ICC inscribed circle
    if 'ICC_radius' in centers and centers['ICC_radius'] > 0:
        icc_circle = plt.Circle(centers['ICC'], centers['ICC_radius'], 
                               fill=False, color='magenta', linewidth=2, linestyle=':')
        ax.add_patch(icc_circle)
    
    # Plot cue position
    cue_x = trial_row['cue_x_px']
    cue_y = trial_row['cue_y_px']
    ax.scatter([cue_x], [cue_y], c='orange', s=500, marker='+', 
               label='Cue Position', zorder=11, linewidths=4)
    
    # Get fixations
    cue_fixations = trial_fixations.get('cue_fixations', [])
    stim_fixations = trial_fixations.get('stim_fixations', [])
    
    # Plot cue fixation (last fixation before STIM_ON)
    cue_fix_dist = None
    if cue_fixations:
        last_cue_fix = cue_fixations[-1]
        fix_x, fix_y = last_cue_fix['x'], last_cue_fix['y']
        ax.scatter([fix_x], [fix_y], c='cyan', s=400, marker='o', 
                   label=f'{participant_id} Cue Fix', zorder=12, 
                   edgecolors='black', linewidths=2, alpha=0.8)
        ax.plot([cue_x, fix_x], [cue_y, fix_y], '--', color='cyan', alpha=0.5, linewidth=2)
        cue_fix_dist = np.sqrt((fix_x - cue_x)**2 + (fix_y - cue_y)**2)
    
    # Plot fixation #2 (second fixation after STIM_ON)
    closest_center = 'N/A'
    min_dist = None
    if len(stim_fixations) >= 2:
        fix2 = stim_fixations[1]
        fix_x, fix_y = fix2['x'], fix2['y']
        ax.scatter([fix_x], [fix_y], c='lime', s=500, marker='X', 
                   label=f'{participant_id} Fix #2', zorder=12, 
                   edgecolors='black', linewidths=2)
        
        # Find closest center
        min_dist = float('inf')
        for name, value in centers.items():
            if name == 'ICC_radius':
                continue
            if not isinstance(value, tuple) or len(value) != 2:
                continue
            cx, cy = value
            dist = np.sqrt((fix_x - cx)**2 + (fix_y - cy)**2)
            if dist < min_dist:
                min_dist = dist
                closest_center = name
    
    # Plot other participant's fixation #2 (for combined plots)
    if other_participant_fix is not None and len(other_participant_fix.get('stim_fixations', [])) >= 2:
        fix2 = other_participant_fix['stim_fixations'][1]
        fix_x, fix_y = fix2['x'], fix2['y']
        ax.scatter([fix_x], [fix_y], c='orange', s=500, marker='P', 
                   label=f'{other_participant_id} Fix #2', zorder=12, 
                   edgecolors='black', linewidths=2)
    
    # Title
    title = f"{trial_uid} | {polygon_id} ({polygon_case}) | Type: {trial_type}\n"
    title += f"Cue: {trial_row['cue_pos_id']} | "
    if cue_fix_dist is not None:
        title += f"Cue Fix Dist: {cue_fix_dist:.0f}px | "
    title += f"Cue fixes: {len(cue_fixations)} | Stim fixes: {len(stim_fixations)}"
    if min_dist is not None:
        title += f" | Fix#2 closest: {closest_center} ({min_dist:.0f}px)"
    
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
    
    return {
        'trial_uid': trial_uid,
        'cue_fix_dist': cue_fix_dist,
        'n_cue_fix': len(cue_fixations),
        'n_stim_fix': len(stim_fixations),
        'closest_center': closest_center,
        'closest_dist': min_dist
    }


def process_participant(participant_id, session_path, output_dir, max_trials=None):
    """Process all trials for a single participant."""
    print(f"\n{'='*60}")
    print(f"Processing {participant_id}")
    print(f"{'='*60}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load trial data
    trials_csv = session_path / "logs_trial/trials.csv"
    trials_df = pd.read_csv(trials_csv)
    print(f"Loaded {len(trials_df)} trials")
    
    # Parse fixation data from ASC files (use block files for all participants)
    edf_dir = session_path / "edf"
    all_fixations = {}
    
    for asc_file in sorted(edf_dir.glob("*_block*.asc")):
        print(f"  Parsing {asc_file.name}...")
        fixations = parse_asc_with_phases(asc_file)
        all_fixations.update(fixations)
        print(f"    Found data for {len(fixations)} trials")
    
    print(f"Total fixation data for {len(all_fixations)} trials")
    
    # Process each trial
    results = []
    count = 0
    
    for idx, trial_row in trials_df.iterrows():
        if max_trials is not None and count >= max_trials:
            break
            
        trial_uid = trial_row['trial_uid']
        
        if trial_row.get('aborted', False):
            continue
        
        # Load polygon vertices
        json_path = trial_row['polygon_json_path']
        vertices = load_polygon_vertices(json_path)
        
        # Calculate centers
        centers = calculate_polygon_centers(vertices)
        
        # Get fixations
        trial_fixations = all_fixations.get(trial_uid, {'cue_fixations': [], 'stim_fixations': []})
        
        try:
            result = plot_trial(
                trial_row, vertices, centers, trial_fixations,
                participant_id, output_dir
            )
            results.append(result)
            count += 1
            
            status = f"cue_dist={result['cue_fix_dist']:.0f}px" if result['cue_fix_dist'] else "no cue fix"
            print(f"  {trial_uid}: {status}, closest={result['closest_center']}")
            
        except Exception as e:
            print(f"  Error plotting {trial_uid}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save summary
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_dir / "summary.csv", index=False)
    
    print(f"\nSaved {len(results)} plots to {output_dir}")
    
    return trials_df, all_fixations


def process_combined_stimuli(p02_trials, p02_fix, p03_trials, p03_fix, output_dir, max_trials=None):
    """Create combined plots showing both participants' fixations for each stimulus."""
    print(f"\n{'='*60}")
    print("Creating combined stimulus plots")
    print(f"{'='*60}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find common trials (by trial_uid)
    p02_uids = set(p02_trials['trial_uid'])
    p03_uids = set(p03_trials['trial_uid'])
    common_uids = p02_uids & p03_uids
    
    print(f"P02 trials: {len(p02_uids)}")
    print(f"P03 trials: {len(p03_uids)}")
    print(f"Common trials: {len(common_uids)}")
    
    # Use P03 as the base (full data)
    count = 0
    for idx, trial_row in p03_trials.iterrows():
        if max_trials is not None and count >= max_trials:
            break
            
        trial_uid = trial_row['trial_uid']
        
        if trial_row.get('aborted', False):
            continue
        
        # Load polygon vertices
        json_path = trial_row['polygon_json_path']
        vertices = load_polygon_vertices(json_path)
        centers = calculate_polygon_centers(vertices)
        
        # Get P03 fixations
        p03_trial_fix = p03_fix.get(trial_uid, {'cue_fixations': [], 'stim_fixations': []})
        
        # Get P02 fixations (if available)
        p02_trial_fix = p02_fix.get(trial_uid, None)
        
        # Create combined plot
        try:
            plot_combined_trial(
                trial_row, vertices, centers,
                p03_trial_fix, 'P03',
                p02_trial_fix, 'P02',
                output_dir
            )
            count += 1
            print(f"  {trial_uid}: plotted")
        except Exception as e:
            print(f"  Error plotting {trial_uid}: {e}")


def plot_combined_trial(trial_row, vertices, centers, p03_fix, p03_id, p02_fix, p02_id, output_dir):
    """Plot trial with both participants' fixation #2."""
    trial_uid = trial_row['trial_uid']
    trial_type = trial_row['trial_type']
    polygon_id = trial_row['polygon_id']
    polygon_case = trial_row['polygon_case']
    image_path = trial_row.get('image_path', None)
    
    # Create masked stimulus
    stimulus = create_masked_stimulus(image_path, vertices, trial_type)
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(19.2, 10.8), dpi=100)
    ax.set_xlim(0, SCREEN_WIDTH)
    ax.set_ylim(SCREEN_HEIGHT, 0)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Display stimulus
    ax.imshow(stimulus, extent=[0, SCREEN_WIDTH, SCREEN_HEIGHT, 0])
    
    # Plot polygon outline
    if vertices is not None:
        polygon_patch = MplPolygon(vertices, fill=False, edgecolor='white', 
                                   linewidth=2, linestyle='--', alpha=0.5)
        ax.add_patch(polygon_patch)
    
    # Plot centers
    center_styles = {
        'SCREEN': {'color': 'yellow', 'marker': '*', 'size': 400, 'label': 'Screen'},
        'COM': {'color': 'red', 'marker': 'o', 'size': 250, 'label': 'COM'},
        'BBC': {'color': 'blue', 'marker': 's', 'size': 200, 'label': 'BBC'},
        'CHC': {'color': 'green', 'marker': '^', 'size': 200, 'label': 'CHC'},
        'ICC': {'color': 'magenta', 'marker': 'D', 'size': 200, 'label': 'ICC'},
    }
    
    for center_name, value in centers.items():
        if center_name == 'ICC_radius':
            continue
        if not isinstance(value, tuple) or len(value) != 2:
            continue
        cx, cy = value
        style = center_styles.get(center_name, {'color': 'white', 'marker': 'x', 'size': 100})
        ax.scatter([cx], [cy], c=style['color'], s=style['size'], 
                   marker=style['marker'], label=style['label'], 
                   zorder=10, edgecolors='black', linewidths=1)
    
    # Draw ICC inscribed circle
    if 'ICC_radius' in centers and centers['ICC_radius'] > 0:
        icc_circle = plt.Circle(centers['ICC'], centers['ICC_radius'], 
                               fill=False, color='magenta', linewidth=2, linestyle=':')
        ax.add_patch(icc_circle)
    
    # Plot cue position
    cue_x = trial_row['cue_x_px']
    cue_y = trial_row['cue_y_px']
    ax.scatter([cue_x], [cue_y], c='orange', s=500, marker='+', 
               label='Cue Position', zorder=11, linewidths=4)
    
    # Plot P03 fixation #2
    p03_stim_fix = p03_fix.get('stim_fixations', [])
    p03_closest = 'N/A'
    if len(p03_stim_fix) >= 2:
        fix2 = p03_stim_fix[1]
        fix_x, fix_y = fix2['x'], fix2['y']
        ax.scatter([fix_x], [fix_y], c='lime', s=500, marker='X', 
                   label=f'{p03_id} Fix #2', zorder=12, 
                   edgecolors='black', linewidths=2)
        
        # Find closest center
        min_dist = float('inf')
        for name, value in centers.items():
            if name == 'ICC_radius':
                continue
            if not isinstance(value, tuple) or len(value) != 2:
                continue
            cx, cy = value
            dist = np.sqrt((fix_x - cx)**2 + (fix_y - cy)**2)
            if dist < min_dist:
                min_dist = dist
                p03_closest = name
    
    # Plot P02 fixation #2
    p02_closest = 'N/A'
    if p02_fix is not None:
        p02_stim_fix = p02_fix.get('stim_fixations', [])
        if len(p02_stim_fix) >= 2:
            fix2 = p02_stim_fix[1]
            fix_x, fix_y = fix2['x'], fix2['y']
            ax.scatter([fix_x], [fix_y], c='cyan', s=500, marker='P', 
                       label=f'{p02_id} Fix #2', zorder=12, 
                       edgecolors='black', linewidths=2)
            
            # Find closest center
            min_dist = float('inf')
            for name, value in centers.items():
                if name == 'ICC_radius':
                    continue
                if not isinstance(value, tuple) or len(value) != 2:
                    continue
                cx, cy = value
                dist = np.sqrt((fix_x - cx)**2 + (fix_y - cy)**2)
                if dist < min_dist:
                    min_dist = dist
                    p02_closest = name
    
    # Title
    title = f"{trial_uid} | {polygon_id} ({polygon_case})\n"
    title += f"P03 closest: {p03_closest} | P02 closest: {p02_closest}"
    
    ax.set_title(title, fontsize=12, fontweight='bold', color='white', 
                 bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    # Legend
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9, facecolor='black', 
              labelcolor='white', edgecolor='white')
    
    # Save
    output_path = output_dir / f"{trial_uid}.png"
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#404040', 
                pad_inches=0.1)
    plt.close()


def main():
    print("=" * 70)
    print("Plotting P02 and P03 Results (using shapely.maximum_inscribed_circle for ICC)")
    print("=" * 70)
    
    # Process P02 (all trials)
    p02_output = OUTPUT_BY_PARTICIPANT / "P02"
    p02_trials, p02_fix = process_participant('P02', SESSIONS['P02'], p02_output)
    
    # Process P03 (all trials, using P03A.asc combined file)
    p03_output = OUTPUT_BY_PARTICIPANT / "P03"
    p03_trials, p03_fix = process_participant('P03', SESSIONS['P03'], p03_output)
    
    # Create combined stimulus plots
    process_combined_stimuli(p02_trials, p02_fix, p03_trials, p03_fix, OUTPUT_BY_STIMULUS)
    
    print("\n" + "=" * 70)
    print("Complete!")
    print(f"Per-participant plots: {OUTPUT_BY_PARTICIPANT}")
    print(f"Combined stimulus plots: {OUTPUT_BY_STIMULUS}")
    print("=" * 70)


if __name__ == "__main__":
    main()
