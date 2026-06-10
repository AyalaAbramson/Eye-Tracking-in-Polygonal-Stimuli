import os
import csv
import glob
import json
import math
import random
import itertools
from datetime import datetime

# Import the backend functions from our core file
from core_functions import generate_auto_polygon, generate_manual_polygon, run_full_experiment

# =====================================================================
# 1. EXPERIMENT CONFIGURATION
# =====================================================================
IMAGE_DATABASE_PATH = r"C:\Users\owner\Desktop\new-project\Trials_images"  # Update this to your actual image folder path.
# Separate image folder used ONLY for the "did not appear" memory-task probes,
# so those fill pictures are guaranteed never to show up in the actual trials.
MEMORY_UNUSED_IMAGE_PATH = r"C:\Users\owner\Desktop\new-project\memory_task_images"  # Update this to your actual unused image folder path.
IMAGE_SIZE = (1100, 1100)
MEMORY_BLOCK_SIZE = 21  # A memory task runs after every this-many trials.
DISPLAY_TIME_SEC = 3
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

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")


def gather_images(folder):
    """Return all image files under folder, matching extensions case-insensitively."""
    files = [
        os.path.join(root, name)
        for root, _dirs, names in os.walk(folder)
        for name in names
        if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS
    ]
    files.sort()
    return files


# Images used ONLY for memory-task "did not appear" probes (never in trials).
memory_unused_images = gather_images(MEMORY_UNUSED_IMAGE_PATH)

if not memory_unused_images:
    print(f"Warning: No memory-task images found in {MEMORY_UNUSED_IMAGE_PATH}")

# =====================================================================
# 3. PREPARE AUTOMATED EXPERIMENT TRIALS
# =====================================================================
# 3*4*5*2 + 6 = 126 --> 378 sec --> 6 min
# 21 trials per block
auto_polygon_types = [5, 6, 7]
num_of_steps = [-1, 0, 1, 3, 4] # 0 = flat edge
rotation_options = [0, 45, 90, 135, 180]
fill_options = [True, False]
concave_options = [None]  # None = no concavity
concave_ratio = [0.0]     

# for step == 1 (no stretch) create only one rotation combo
def get_rotations(step):
    return [rotation_options[0]] if step == 1 else rotation_options

# Multiply by TRIAL_REPETITIONS
base_auto_combos = [
    (sides, step, rot, is_filled, c_idx, c_ratio)
    for sides in auto_polygon_types
    for step in num_of_steps
    # num_of_steps == 1 has no stretch, so all rotations look the same -> use only one rotation
    for rot in get_rotations(step)
    for is_filled in fill_options
    for c_idx in concave_options
    for c_ratio in concave_ratio
]
auto_combos = base_auto_combos * TRIAL_REPETITIONS
random.shuffle(auto_combos)


def make_image_sampler(images):
    """Yield images without replacement, in a fixed (non-random) order.

    Images are returned in the sorted order in which they were gathered, so the
    textured polygons appear in exactly the same order on every run. Each image
    is used once before any repeats; when the list is exhausted it simply starts
    again from the beginning. Returns None forever when no images are available.
    """
    index = 0

    def next_image():
        nonlocal index
        if not images:
            return None
        image = images[index % len(images)]
        index += 1
        return image

    return next_image

next_trial_image = make_image_sampler(image_files)

trial_data_auto = []
for sides, step, rot, is_filled, c_idx, c_ratio in auto_combos:
    tex = next_trial_image() if is_filled else None

    img, actual_points, base_points = generate_auto_polygon(
        num_vertices=sides, step=step, rotation_deg=rot,
        target_idx=0, concave_idx=c_idx, concave_ratio=c_ratio, texture_path=tex, size=IMAGE_SIZE
    )
    trial_data_auto.append({
        "image": img, "type": "auto", "points": actual_points, "base_points": base_points, "concave_idx": c_idx
    })

# =====================================================================
# 4. PREPARE MANUAL EXPERIMENT TRIALS - not used in this experiment
# =====================================================================
manual_shapes = [
    ([200, 100, 200, 100], [90, 90, 90, 90]),
    ([250, 200, 250], [150, 110, 100]),
]

# Multiply by TRIAL_REPETITIONS
base_manual_combos = list(itertools.product(manual_shapes, rotation_options, fill_options))
manual_combos = base_manual_combos * TRIAL_REPETITIONS
random.shuffle(manual_combos)

next_manual_image = make_image_sampler(image_files)

trial_data_manual = []
for (radii, angles), rot, is_filled in manual_combos:
    tex = next_manual_image() if is_filled else None

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


def build_memory_probes(trials, block_size, unused_images):
    """Create one memory-task probe per block.

    The correct answer is "1" (appeared) once every two blocks; on those blocks
    the probe is one of the polygons actually shown in that block (same fill).
    On the other blocks the correct answer is "2" (did not appear): a freshly
    generated polygon filled with a picture from the unused-images folder, so it
    is guaranteed never to have appeared in the experiment.
    """
    probes = []
    n_blocks = math.ceil(len(trials) / block_size) if trials else 0
    for b in range(n_blocks):
        block_trials = trials[b * block_size:(b + 1) * block_size]
        # Alternate, starting with "appeared" on the first block.
        correct = "1" if (b % 2 == 0) else "2"

        if correct == "1" and block_trials:
            probe_img = random.choice(block_trials)["image"]
        else:
            correct = "2"  # fall back to "did not appear" if the block is empty
            tex = random.choice(unused_images) if unused_images else None
            sides = random.choice(auto_polygon_types)
            step = random.choice(num_of_steps)
            rot = random.choice(get_rotations(step))
            probe_img, _, _ = generate_auto_polygon(
                num_vertices=sides, step=step, rotation_deg=rot,
                target_idx=0, concave_idx=None, concave_ratio=concave_ratio[0],
                texture_path=tex, size=IMAGE_SIZE,
            )
        probes.append({"image": probe_img, "correct": correct})
    return probes


memory_probes = build_memory_probes(ACTIVE_TRIALS, MEMORY_BLOCK_SIZE, memory_unused_images)

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
        "block_size": MEMORY_BLOCK_SIZE,
        "n_blocks": len(memory_probes),
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
            block_size=MEMORY_BLOCK_SIZE,
            memory_probes=memory_probes,
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