import os
import csv
import glob
import json
import random
import itertools
from datetime import datetime

# Import the backend functions from our core file
from core_functions import generate_auto_polygon, generate_manual_polygon, run_full_experiment

# =====================================================================
# 1. EXPERIMENT CONFIGURATION
# =====================================================================
IMAGE_DATABASE_PATH = r"C:\Users\User\Desktop\דברים\תמונות"
IMAGE_SIZE = (800, 800)
DISPLAY_TIME_SEC = 5
FIXATION_TIME_SEC = 1.0
TRIAL_REPETITIONS = 1    # Number of times each generated shape repeats

# Toggle this to True to see grids, centers, and vertices.
# Toggle to False for the clean, real experiment.
DEBUG_MODE = False

# --- EyeLink 1000 Plus configuration ---
USE_EYELINK = False            # Set False for a behavioural-only test (no tracker).
EYELINK_DUMMY_MODE = True      # True = simulate a tracker (no hardware) for testing.
EYELINK_ADDRESS = "100.1.1.1"  # EyeLink 1000 Plus default Host PC address.
CALIBRATION_TYPE = "HV9"       # HV3 / HV5 / HV9 / HV13.
BINOCULAR = False              # Record one eye.

# Gaze-gated fixation parameters (only used when the tracker is connected).
FIXATION_WINDOW_PX = 100.0     # Acceptance radius around the fixation cross.
FIXATION_REQUIRED_MS = 300.0   # Stable dwell needed to auto-advance.
FIXATION_MAX_WAIT_S = 10.0     # Timeout before the trial proceeds anyway.

# Where all participant data is stored.
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")

# Per-trial CSV column order (must match the row written in run_full_experiment).
TRIAL_CSV_HEADER = [
    "trial_index", "wall_clock", "trial_type",
    "fixation_x_px", "fixation_y_px",
    "stim_center_x_px", "stim_center_y_px",
    "stim_top_left_x_px", "stim_top_left_y_px",
    "stim_w_px", "stim_h_px",
    "concave_idx",
    "fixation_outcome", "fixation_ts_s",
    "stim_on_ts_s", "stim_off_ts_s", "stim_duration_s",
    "polygon_points_imgspace", "polygon_base_points_imgspace",
    "aborted",
]

random.seed(42)


def prompt_participant_info():
    """Collect participant metadata from the console before the window opens."""
    print("\n" + "=" * 55)
    print(" Polygon center-bias experiment - participant intake")
    print("=" * 55)
    participant_id = input("Participant ID (e.g. P01): ").strip() or "P00"
    age = input("Age (optional): ").strip()
    gender = input("Gender (optional): ").strip()
    return {
        "participant_id": participant_id,
        "age": age or "NA",
        "gender": gender or "NA",
        "timestamp": datetime.now().isoformat(),
    }

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
auto_polygon_types = [5, 6, 7]
num_of_steps = [0, 1, 2, 3] # 0 = flat edge
rotation_options = [0, 60, 120, 180, 240, 300]
fill_options = [True]
concave_options = [None]  # None = no concavity
concave_ratio = [0.2]       

# Multiply by TRIAL_REPETITIONS
base_auto_combos = list(itertools.product(auto_polygon_types, num_of_steps, rotation_options, fill_options, concave_options, concave_ratio))
auto_combos = base_auto_combos * TRIAL_REPETITIONS
random.shuffle(auto_combos)

trial_data_auto = []
for sides, step, rot, is_filled, c_idx, c_ratio in auto_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, actual_points, base_points = generate_auto_polygon(
        num_vertices=sides, step=step, rotation_deg=rot,
        target_idx=0, concave_idx=c_idx, concave_ratio=c_ratio, texture_path=tex, size=IMAGE_SIZE
    )
    trial_data_auto.append({
        "image": img, "type": "auto", "points": actual_points, "base_points": base_points, "concave_idx": c_idx
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
        "image": img, "type": "manual", "points": actual_points, "base_points": base_points, "concave_idx": None
    })

# =====================================================================
# 5. EXECUTE EXPERIMENT
# =====================================================================
# Choose which trial list to run: trial_data_auto or trial_data_manual.
ACTIVE_TRIALS = trial_data_auto

mode_str = "DEBUG" if DEBUG_MODE else "REAL"

# --- Participant intake (console prompt) ---
participant_info = prompt_participant_info()
participant_id = participant_info["participant_id"]

# --- Build the per-session data folder ---
#   data/raw/participant_<ID>/session_<timestamp>/{edf, trials.csv, metadata.json}
session_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
session_root = os.path.join(
    DATA_ROOT, f"participant_{participant_id}", f"session_{session_stamp}"
)
edf_dir = os.path.join(session_root, "edf")
os.makedirs(edf_dir, exist_ok=True)

trial_csv_path = os.path.join(session_root, "trials.csv")
metadata_path = os.path.join(session_root, "session_metadata.json")

# --- Optional EyeLink setup ---
tracker = None
exp_clock = None
screen = None
edf_name = None

if USE_EYELINK:
    import pygame
    import eyelink_interface as eli

    # Determine the full-screen resolution to configure the tracker with.
    pygame.init()
    _info = pygame.display.Info()
    screen_w, screen_h = _info.current_w, _info.current_h

    print(f"\nConnecting to EyeLink at '{EYELINK_ADDRESS}' "
          f"(dummy={EYELINK_DUMMY_MODE}) ...")
    tracker = eli.connect_eyelink(address=EYELINK_ADDRESS, dummy_mode=EYELINK_DUMMY_MODE)
    exp_clock = eli.ExpClock()

    edf_name = eli.setup_edf(tracker, participant_id, edf_dir)
    print(f"EDF opened on host: {edf_name}")

    eli.configure_tracker(tracker, screen_w, screen_h,
                          calibration_type=CALIBRATION_TYPE, binocular=BINOCULAR)

    # Open pylink's built-in calibration graphics; reuse the surface for stimuli.
    screen = eli.open_calibration_graphics(tracker, screen_w, screen_h)

    print("Starting calibration. In the camera-setup screen: "
          "'C' calibrate, 'V' validate, 'O'/Enter to accept and begin.")
    calib = eli.do_calibration(tracker, exp_clock)
    if calib["result"] == "ABORT":
        print("Calibration aborted - closing without running trials.")
        eli.close_tracker(tracker, edf_name, os.path.join(edf_dir, edf_name), exp_clock)
        raise SystemExit(0)

# --- Write session metadata ---
with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump({
        "participant": participant_info,
        "session_stamp": session_stamp,
        "mode": mode_str,
        "n_trials": len(ACTIVE_TRIALS),
        "trial_set": "auto" if ACTIVE_TRIALS is trial_data_auto else "manual",
        "display_time_sec": DISPLAY_TIME_SEC,
        "image_size": list(IMAGE_SIZE),
        "use_eyelink": USE_EYELINK,
        "eyelink": {
            "dummy_mode": EYELINK_DUMMY_MODE,
            "address": EYELINK_ADDRESS,
            "calibration_type": CALIBRATION_TYPE,
            "binocular": BINOCULAR,
            "edf_name": edf_name,
            "fixation_window_px": FIXATION_WINDOW_PX,
            "fixation_required_ms": FIXATION_REQUIRED_MS,
            "fixation_max_wait_s": FIXATION_MAX_WAIT_S,
        },
    }, f, indent=2)
print(f"Session metadata written to {metadata_path}")

# --- Run the experiment, logging one CSV row per trial ---
print(f"\nStarting {mode_str} experiment with {len(ACTIVE_TRIALS)} trials...")
try:
    with open(trial_csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(TRIAL_CSV_HEADER)
        run_full_experiment(
            ACTIVE_TRIALS,
            display_duration_sec=DISPLAY_TIME_SEC,
            debug=DEBUG_MODE,
            tracker=tracker,
            exp_clock=exp_clock,
            screen=screen,
            trial_writer=writer,
            trial_file=csv_file,
            fixation_window_px=FIXATION_WINDOW_PX,
            fixation_required_ms=FIXATION_REQUIRED_MS,
            fixation_max_wait_s=FIXATION_MAX_WAIT_S,
        )
    print(f"Trial data saved to {trial_csv_path}")
except KeyboardInterrupt:
    # Ctrl+C: rows already written are flushed per-trial, so data is preserved.
    print("\nExperiment interrupted (Ctrl+C). Saving collected data...")
finally:
    # --- Always retrieve the EDF and close the tracker, even on error ---
    if USE_EYELINK and tracker is not None:
        import eyelink_interface as eli
        eli.close_tracker(tracker, edf_name, os.path.join(edf_dir, edf_name), exp_clock)
        print(f"EDF saved to {os.path.join(edf_dir, edf_name)}")

print(f"\nExperiment complete. All data in: {session_root}")