"""
Plot P02 trials exactly as shown in experiment, with centers and fixations.
Creates separate plots for fixation 1, 2, 3 for each trial.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Circle
from PIL import Image
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
OUTPUT_DIR = Path("outputs/p02_trial_plots")

def load_polygon_vertices(json_path, scale=APERTURE_SCALE):
    """Load polygon vertices from JSON and scale to aperture size."""
    full_path = Path(json_path)
    if not full_path.exists():
        full_path = Path("data/raw/stimuli/polygons") / Path(json_path).name
    
    with open(full_path, 'r') as f:
        data = json.load(f)
    
    # Handle different JSON formats
    if 'vertices_xy' in data:
        vertices = np.array(data['vertices_xy'])
    elif 'theta' in data:
        # Radial format - convert to cartesian
        theta_data = data['theta']
        angles = np.array(theta_data['angles_deg']) * np.pi / 180
        radii = np.array(theta_data['radii_norm'])
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

def create_masked_image_for_plot(image_path, vertices_screen):
    """Create the masked image as shown in experiment."""
    from PIL import Image, ImageDraw
    
    img = Image.open(image_path).convert('RGBA')
    img_w, img_h = img.size  # 1920x1080
    
    # Calculate polygon bounds in image space
    # Polygon is centered at screen center, image is also centered at screen center
    # So we need to map polygon coords to image coords
    poly_in_img = vertices_screen.copy()
    poly_in_img[:, 0] -= (SCREEN_CENTER_X - img_w / 2)
    poly_in_img[:, 1] -= (SCREEN_CENTER_Y - img_h / 2)
    
    # Create mask
    mask = Image.new('L', (img_w, img_h), 0)
    draw = ImageDraw.Draw(mask)
    poly_points = [tuple(p) for p in poly_in_img]
    draw.polygon(poly_points, fill=255)
    
    # Apply mask
    result = Image.new('RGBA', (img_w, img_h), (128, 128, 128, 255))
    result.paste(img, (0, 0), mask)
    
    return result, poly_in_img

def parse_edf_fixations(edf_path):
    """
    Parse fixations from EDF file.
    Returns dict: {trial_uid: [(x, y, start_time, duration), ...]}
    """
    try:
        import pylink
    except ImportError:
        print("pylink not available, using ASC conversion method")
        return parse_asc_fixations(edf_path)
    
    # Try to use edf2asc if available
    asc_path = edf_path.with_suffix('.asc')
    if not asc_path.exists():
        # Try to convert
        import subprocess
        try:
            subprocess.run(['edf2asc', str(edf_path)], check=True, capture_output=True)
        except:
            print(f"Could not convert {edf_path} to ASC")
            return {}
    
    if asc_path.exists():
        return parse_asc_fixations(asc_path)
    
    return {}

def parse_asc_fixations(asc_path):
    """Parse fixations from ASC file."""
    fixations_by_trial = {}
    current_trial = None
    
    if not Path(asc_path).exists():
        return {}
    
    with open(asc_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Look for trial markers
            if 'TRIALID' in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == 'TRIALID' and i + 1 < len(parts):
                        current_trial = parts[i + 1]
                        if current_trial not in fixations_by_trial:
                            fixations_by_trial[current_trial] = []
                        break
            
            # Look for fixations (EFIX line)
            elif line.startswith('EFIX'):
                parts = line.split()
                if len(parts) >= 6 and current_trial:
                    try:
                        # EFIX R start end duration x y pupil
                        start = float(parts[2])
                        end = float(parts[3])
                        duration = float(parts[4])
                        x = float(parts[5])
                        y = float(parts[6])
                        fixations_by_trial[current_trial].append((x, y, start, duration))
                    except:
                        pass
    
    return fixations_by_trial

def convert_edf_to_asc(edf_path):
    """Convert EDF to ASC using edf2asc tool."""
    asc_path = edf_path.with_suffix('.asc')
    if asc_path.exists():
        return asc_path
    
    # Common locations for edf2asc
    edf2asc_paths = [
        r"C:\Program Files\SR Research\EyeLink\bin\edf2asc.exe",
        r"C:\Program Files (x86)\SR Research\EyeLink\bin\edf2asc.exe",
        r"C:\SR Research\EyeLink\bin\edf2asc.exe",
        "edf2asc",  # In PATH
    ]
    
    import subprocess
    for edf2asc in edf2asc_paths:
        try:
            result = subprocess.run(
                [edf2asc, '-y', str(edf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if asc_path.exists():
                return asc_path
        except (FileNotFoundError, OSError):
            continue
    
    print("    edf2asc not found - skipping fixation data")
    return None

def plot_trial_with_fixations(trial_row, geom_row, fixations, output_dir, fixation_num=1):
    """
    Plot a single trial with stimulus, centers, and specified fixation.
    """
    trial_uid = trial_row['trial_uid']
    trial_type = trial_row['trial_type']
    polygon_id = trial_row['polygon_id']
    polygon_case = trial_row['polygon_case']
    json_path = trial_row['polygon_json_path']
    
    # Handle geom_row being a dict (possibly empty)
    if isinstance(geom_row, dict):
        geom_dict = geom_row
    else:
        geom_dict = geom_row.to_dict() if hasattr(geom_row, 'to_dict') else {}
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 9), dpi=100)
    
    # Set up axes to match screen coordinates
    ax.set_xlim(0, SCREEN_WIDTH)
    ax.set_ylim(SCREEN_HEIGHT, 0)  # Flip Y axis (0 at top)
    ax.set_aspect('equal')
    ax.set_facecolor('#808080')  # Gray background
    
    # Load polygon vertices
    vertices = load_polygon_vertices(json_path)
    
    if trial_type == 'image':
        # Load and mask image
        image_path = trial_row['image_path']
        if pd.notna(image_path) and Path(image_path).exists():
            try:
                masked_img, poly_in_img = create_masked_image_for_plot(image_path, vertices)
                
                # Calculate image position on screen (centered)
                img_left = SCREEN_CENTER_X - IMAGE_WIDTH / 2
                img_top = SCREEN_CENTER_Y - IMAGE_HEIGHT / 2
                
                # Display image
                ax.imshow(masked_img, extent=[img_left, img_left + IMAGE_WIDTH, 
                                               img_top + IMAGE_HEIGHT, img_top])
            except Exception as e:
                print(f"Error loading image for {trial_uid}: {e}")
                # Draw polygon outline instead
                if vertices is not None:
                    poly_patch = MplPolygon(vertices, fill=False, edgecolor='white', linewidth=2)
                    ax.add_patch(poly_patch)
        else:
            # Draw polygon outline
            if vertices is not None:
                poly_patch = MplPolygon(vertices, fill=False, edgecolor='white', linewidth=2)
                ax.add_patch(poly_patch)
    
    elif trial_type == 'empty':
        # Empty trial - show polygon outline only
        if vertices is not None:
            poly_patch = MplPolygon(vertices, fill=True, facecolor='black', 
                                    edgecolor='white', linewidth=3)
            ax.add_patch(poly_patch)
    
    # Plot polygon outline for reference
    if vertices is not None:
        poly_outline = MplPolygon(vertices, fill=False, edgecolor='cyan', 
                                   linewidth=1, linestyle='--', alpha=0.5)
        ax.add_patch(poly_outline)
    
    # Plot centers
    center_colors = {
        'COM': 'red',
        'BBC': 'blue', 
        'CHC': 'green',
        'ICC': 'magenta',
        'SCREEN': 'yellow'
    }
    
    centers_plotted = []
    
    # Screen center
    ax.scatter([SCREEN_CENTER_X], [SCREEN_CENTER_Y], c='yellow', s=200, 
               marker='*', label='Screen Center', zorder=10, edgecolors='black')
    centers_plotted.append(('SCREEN', SCREEN_CENTER_X, SCREEN_CENTER_Y))
    
    # Helper to check if value is valid
    def is_valid(val):
        if val is None:
            return False
        try:
            return pd.notna(val)
        except:
            return val is not None
    
    # COM
    if is_valid(geom_dict.get('center_com_x_canonical_px')):
        com_x = SCREEN_CENTER_X + geom_dict['center_com_x_canonical_px']
        com_y = SCREEN_CENTER_Y + geom_dict['center_com_y_canonical_px']
        ax.scatter([com_x], [com_y], c='red', s=150, marker='o', 
                   label='COM', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('COM', com_x, com_y))
    
    # BBC
    if is_valid(geom_dict.get('center_bbc_x_canonical_px')):
        bbc_x = SCREEN_CENTER_X + geom_dict['center_bbc_x_canonical_px']
        bbc_y = SCREEN_CENTER_Y + geom_dict['center_bbc_y_canonical_px']
        ax.scatter([bbc_x], [bbc_y], c='blue', s=150, marker='s', 
                   label='BBC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('BBC', bbc_x, bbc_y))
    
    # CHC
    if is_valid(geom_dict.get('center_chc_x_canonical_px')):
        chc_x = SCREEN_CENTER_X + geom_dict['center_chc_x_canonical_px']
        chc_y = SCREEN_CENTER_Y + geom_dict['center_chc_y_canonical_px']
        ax.scatter([chc_x], [chc_y], c='green', s=150, marker='^', 
                   label='CHC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('CHC', chc_x, chc_y))
    
    # ICC
    if is_valid(geom_dict.get('center_icc_x_canonical_px')):
        icc_x = SCREEN_CENTER_X + geom_dict['center_icc_x_canonical_px']
        icc_y = SCREEN_CENTER_Y + geom_dict['center_icc_y_canonical_px']
        ax.scatter([icc_x], [icc_y], c='magenta', s=150, marker='D', 
                   label='ICC', zorder=10, edgecolors='white', linewidths=2)
        centers_plotted.append(('ICC', icc_x, icc_y))
    
    # Plot cue position
    cue_x = trial_row['cue_x_px']
    cue_y = trial_row['cue_y_px']
    ax.scatter([cue_x], [cue_y], c='orange', s=300, marker='+', 
               label=f'Cue ({trial_row["cue_pos_id"]})', zorder=11, linewidths=3)
    
    # Plot fixation
    fixation_plotted = False
    fix_x, fix_y = None, None
    
    if fixation_num == 0:
        # Fixation 0 = cue position (initial fixation before stimulus)
        # Use the first fixation in the list as the "cue fixation"
        if fixations and len(fixations) >= 1:
            fix = fixations[0]
            fix_x, fix_y = fix[0], fix[1]
            ax.scatter([fix_x], [fix_y], c='white', s=400, marker='x', 
                       label=f'Fixation 0 (Cue)', zorder=12, linewidths=4)
            ax.scatter([fix_x], [fix_y], c='black', s=300, marker='x', 
                       zorder=11, linewidths=2)
            fixation_plotted = True
    elif fixations and len(fixations) >= fixation_num:
        # Fixation N (1-indexed in the list, so fixation 2 = index 1)
        fix = fixations[fixation_num - 1]
        fix_x, fix_y = fix[0], fix[1]
        ax.scatter([fix_x], [fix_y], c='white', s=400, marker='x', 
                   label=f'Fixation {fixation_num}', zorder=12, linewidths=4)
        ax.scatter([fix_x], [fix_y], c='black', s=300, marker='x', 
                   zorder=11, linewidths=2)
        fixation_plotted = True
    
    # Add distance annotations if fixation was plotted
    if fixation_plotted and fix_x is not None:
        for name, cx, cy in centers_plotted:
            dist = np.sqrt((fix_x - cx)**2 + (fix_y - cy)**2)
            # Draw line from fixation to center
            ax.plot([fix_x, cx], [fix_y, cy], '--', color=center_colors.get(name, 'gray'), 
                    alpha=0.3, linewidth=1)
    
    # Title
    title = f"{trial_uid} | {polygon_id} ({polygon_case})\n"
    title += f"Type: {trial_type} | Cue: {trial_row['cue_pos_id']}"
    if fixation_plotted:
        if fixation_num == 0:
            title += f" | Fixation 0 (Cue)"
        else:
            title += f" | Fixation {fixation_num}"
    else:
        title += f" | No Fixation {fixation_num} data"
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    # Legend
    ax.legend(loc='upper left', fontsize=8, framealpha=0.8)
    
    # Add grid
    ax.axhline(SCREEN_CENTER_Y, color='white', alpha=0.2, linestyle=':')
    ax.axvline(SCREEN_CENTER_X, color='white', alpha=0.2, linestyle=':')
    
    # Save
    output_path = output_dir / f"{trial_uid}_fix{fixation_num}.png"
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#404040')
    plt.close()
    
    return output_path

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
    
    # Try to parse fixations from EDF files
    print("Parsing fixation data from EDF files...")
    all_fixations = {}
    
    for edf_file in EDF_DIR.glob("*.edf"):
        print(f"  Processing {edf_file.name}...")
        asc_path = convert_edf_to_asc(edf_file)
        if asc_path:
            fixations = parse_asc_fixations(asc_path)
            all_fixations.update(fixations)
            print(f"    Found fixations for {len(fixations)} trials")
        else:
            print(f"    Could not convert to ASC")
    
    print(f"Total fixations loaded for {len(all_fixations)} trials")
    
    # Process each trial
    print("\nGenerating plots...")
    
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
            geom_row = {}
        else:
            # Convert to dict and handle NaN values
            geom_row = {}
            for col, val in geom_match.iloc[0].items():
                if pd.notna(val):
                    geom_row[col] = val
        
        # Get fixations for this trial
        trial_fixations = all_fixations.get(trial_uid, [])
        
        # Create plots for fixation 0 (cue) and fixation 2
        for fix_num in [0, 2]:
            try:
                output_path = plot_trial_with_fixations(
                    trial_row, geom_row, trial_fixations, OUTPUT_DIR, fix_num
                )
                if fix_num == 0:
                    print(f"  {trial_uid}: {len(trial_fixations)} fixations -> {output_path.name}")
            except Exception as e:
                print(f"  Error plotting {trial_uid} fix{fix_num}: {e}")
    
    print(f"\nDone! Plots saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
