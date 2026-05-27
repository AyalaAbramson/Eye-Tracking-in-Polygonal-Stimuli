import os
import glob
import random
import itertools
import pygame
import pylink # need to install the right directory
import sys
# Import the backend functions from our core file
from core_functions import generate_auto_polygon, generate_manual_polygon, run_full_experiment

# =====================================================================
# 1. EXPERIMENT CONFIGURATION
# =====================================================================
IMAGE_DATABASE_PATH = r"C:\Users\User\Desktop\דברים\תמונות"
IMAGE_SIZE = (800, 800)
DISPLAY_TIME_SEC = 5
FIXATION_TIME_SEC = 1.0
TRIAL_REPETITIONS = 1  # Number of times each generated shape repeats

# Tracker Configuration
TRACKER_IP = None  # Change to None if testing at home without a tracker
tracker = None # Initialize tracker as None to ensure it is accessible in the 'finally' block
EDF_FILENAME = "Check1.EDF"  # STRICT LIMIT: Maximum 8 characters!

# Toggle this to True to see grids, centers, and vertices.
# Toggle to False for the clean, real experiment.
DEBUG_MODE = False

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
auto_polygon_types = [6]
stretch_val = 20
stretch_steps = [step * stretch_val for step in range(-2, 3)]
rotation_options = [0, 90]
fill_options = [True]
concave_options = [2]
concave_ratio = [0.2]

# Multiply by TRIAL_REPETITIONS
base_auto_combos = list(
    itertools.product(auto_polygon_types, stretch_steps, rotation_options, fill_options, concave_options,
                      concave_ratio))
auto_combos = base_auto_combos * TRIAL_REPETITIONS
random.shuffle(auto_combos)

trial_data_auto = []
for sides, s_amt, rot, is_filled, c_idx, c_ratio in auto_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, actual_points, base_points = generate_auto_polygon(
        num_vertices=sides, stretch_amt=s_amt, rotation_deg=rot,
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
# 5. INITIALIZE PYGAME AND EYELINK
# =====================================================================
# Initialize Pygame here so the EyeLink calibration can use the screen
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
sw, sh = screen.get_size()

try:
    if TRACKER_IP is not None:
        print(f"Connecting to EyeLink tracker at {TRACKER_IP}...")
        tracker = pylink.EyeLink(TRACKER_IP)
    else:
        print("Initializing EyeLink in DUMMY MODE (No physical tracker)...")
        # Creating a virtual tracker object to test all pylink functions
        tracker = pylink.EyeLink(None)

    tracker.openDataFile(EDF_FILENAME)
    print(f"Data file {EDF_FILENAME} opened.")

    # file: data saved to EDF
    # link: data sent to tracker in real-time
    # sample data suitable for EyeLink 1000 PLUS version
    tracker.sendCommand("file_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT")
    tracker.sendCommand("file_sample_data = LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT")
    tracker.sendCommand("link_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT")
    tracker.sendCommand("link_sample_data = LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT")
    tracker.sendCommand("sample_rate 1000")

    # calibration definition
    tracker.sendCommand("calibration_type = HV9")
    tracker.sendCommand(f"screen_pixel_coords = 0 0 {sw - 1} {sh - 1}")

    pylink.openGraphics()
    pylink.setCalibrationColors((128, 128, 128), (0, 0, 0))

    print("Starting calibration setup...")
    tracker.doTrackerSetup()

except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize pylink: {e}")
    pygame.quit()
    sys.exit()

# =====================================================================
# 6. EXECUTE EXPERIMENT
# =====================================================================
mode_str = "DEBUG" if DEBUG_MODE else "REAL"

# uncomment the line for the wanted experiment:


print(f"Starting {mode_str} experiment")
try:
    # --- Auto polygons experiment ---
    run_full_experiment(trial_data_auto, tracker=tracker, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)

    # --- Manual polygons experiment ---
    # run_full_experiment(trial_data_manual, tracker=tracker, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)

finally:
    # closes edf file if the experiment crashed
    if tracker is not None:
        try:
            tracker.stopRecording()
            tracker.closeDataFile()
            tracker.receiveDataFile(EDF_FILENAME, EDF_FILENAME)
            tracker.close()
            print("EDF file saved and tracker connection closed safely.")
        except Exception as e:
            print(f"Error during cleanup: {e}")

# =====================================================================
# 7. CLEANUP AND DOWNLOAD DATA
# =====================================================================
if tracker is not None:
    print("Closing data file and downloading to local computer...")
    tracker.closeDataFile()

    # Download the EDF from the Host PC to the current directory
    tracker.receiveDataFile(EDF_FILENAME, EDF_FILENAME)
    tracker.close()
    print("Download complete.")

pygame.quit()
sys.exit()