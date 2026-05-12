import os
import glob
import random
import itertools

# Import the backend functions from our core file
from core_functions import generate_auto_polygon, generate_manual_polygon, run_full_experiment

# =====================================================================
# 1. EXPERIMENT CONFIGURATION
# =====================================================================
IMAGE_DATABASE_PATH = r"C:\Users\User\Desktop\דברים\תמונות"
IMAGE_SIZE = (800, 800)
DISPLAY_TIME_SEC = 5
FIXATION_TIME_SEC = 1.0
TRIAL_REPETITIONS = 3    # Number of times each generated shape repeats

# Toggle this to True to see grids, centers, and vertices.
# Toggle to False for the clean, real experiment.
DEBUG_MODE = True

random.seed(42)

# =====================================================================
# 2. GATHER IMAGES
# =====================================================================
image_files = glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.jpg"), recursive=True) + \
              glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.png"), recursive=True)
image_files.sort()

if not image_files:
    print(f"Warning: No images found in {IMAGE_DATABASE_PATH}")

# =====================================================================
# 3. PREPARE AUTOMATED EXPERIMENT TRIALS
# =====================================================================
auto_polygon_types = [4, 5]
stretch_val = 50
stretch_steps = [step * stretch_val for step in range(-2, 3)]
rotation_options = [0, 90]
fill_options = [True]
concave_options = [None, 2]

# Multiply by TRIAL_REPETITIONS
base_auto_combos = list(itertools.product(auto_polygon_types, stretch_steps, rotation_options, fill_options, concave_options))
auto_combos = base_auto_combos * TRIAL_REPETITIONS
random.shuffle(auto_combos)

trial_data_auto = []
for sides, s_amt, rot, is_filled, c_idx in auto_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, actual_points, base_points = generate_auto_polygon(
        num_vertices=sides, stretch_amt=s_amt, rotation_deg=rot,
        target_idx=0, concave_idx=c_idx, texture_path=tex, size=IMAGE_SIZE
    )
    trial_data_auto.append({
        "image": img, "type": "auto", "points": actual_points, "base_points": base_points
    })

# =====================================================================
# 4. PREPARE MANUAL EXPERIMENT TRIALS
# =====================================================================
manual_shapes = [
    ([200, 100, 200, 100], [90, 90, 90, 90]),
    ([250, 200, 250], [150, 110, 100]),
]

# Multiply by TRIAL_REPETITIONS
base_manual_combos = list(itertools.product(manual_shapes, rotation_options, fill_options))
manual_combos = base_manual_combos * TRIAL_REPETITIONS
random.shuffle(manual_combos)

trial_data_manual = []
for (radii, angles), rot, is_filled in manual_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, actual_points, base_points = generate_manual_polygon(
        manual_radii=radii, manual_angles_deg=angles, rotation_deg=rot,
        texture_path=tex, size=IMAGE_SIZE
    )
    trial_data_manual.append({
        "image": img, "type": "manual", "points": actual_points, "base_points": base_points
    })

# =====================================================================
# 5. EXECUTE EXPERIMENT
# =====================================================================
mode_str = "DEBUG" if DEBUG_MODE else "REAL"

# Choose which experiment to run here:
print(f"Starting {mode_str} experiment with {len(trial_data_auto)} automated trials...")
run_full_experiment(trial_data_auto, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)

# To run manual instead, uncomment the line below and comment the one above:
# run_full_experiment(trial_data_manual, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)