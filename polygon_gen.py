import os
import glob
import math
import random
import itertools
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

# --- CONFIGURATION ---
# Set the path to your image folder here
IMAGE_DATABASE_PATH = r"C:\Users\User\Desktop\דברים\תמונות"  # change according to data path
IMAGE_SIZE = (800, 800)
DISPLAY_TIME_SEC = 5
FIXATION_TIME_SEC = 1.0  # calibration "+" duration

# Setting the seed here ensures the shuffle and image selection
# are identical every time the script runs.
random.seed(42)


def wait_for_fixation(target_point, window_name):
    """
    Pauses the experiment on the fixation screen until a signal is received.
    Returns True to proceed to the stimulus, or False to quit the experiment.
    """
    while True:
        # FUTURE EYE-TRACKER IMPLEMENTATION:
        # Check if the user's gaze is on the target_point
        # if eye_tracker.is_looking_at(target_point):
        #     return True

        key = cv2.waitKey(1) & 0xFF

        # Press 'Space' to manually continue to the next stimulus
        if key == ord(' '):
            return True

        # Press 'q' to completely abort the experiment
        if key == ord('q'):
            return False


def generate_manual_polygon(manual_radii, manual_angles_deg, rotation_deg=0, size=(800, 800),
                            texture_path=None):
    """
    Generates a polygon based strictly on manual lists of radii and angles
    no vertex stretching
    with rotation option
    with image fill option
    """
    #  ---Validation---
    #  1. Ensure we have the same number of radii and angles

    if len(manual_radii) != len(manual_angles_deg):
        raise ValueError("The number of radii must match the number of angles.")

    #  2. Ensure the intervals sum up to a full circle
    angles_sum = sum(manual_angles_deg)
    if angles_sum != 360:
        raise ValueError(f"The sum of manual angles must be 360. Current: {angles_sum}")

    # Setup mask and drawing canvas
    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    center_x, center_y = size[0] // 2, size[1] // 2
    rotation_rad = math.radians(rotation_deg)  # rotation in radians

    points = []
    for i in range(len(manual_radii)):
        # Calculate the cumulative angle to place the vertex.
        # vertex 0 is at 0 degrees, vertex 1 is at angles[0], etc.
        cumulative_angle = sum(manual_angles_deg[:i])
        angle = math.radians(cumulative_angle) - (math.pi / 2) + rotation_rad

        radius = manual_radii[i]
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

    # Create the polygon shape
    mask_draw.polygon(points, fill=255)
    final_img = Image.new("RGB", size, "white")

    # Apply texture if provided
    if texture_path and os.path.exists(texture_path):
        try:
            texture = Image.open(texture_path).convert("RGB")
            texture = ImageOps.fit(texture, size, Image.Resampling.LANCZOS)
            final_img.paste(texture, (0, 0), mask)
        except Exception as e:
            print(f"Error loading texture: {e}")

    # Draw the final outline
    draw = ImageDraw.Draw(final_img)
    draw.polygon(points, outline="black", width=5)

    return final_img


def generate_auto_polygon(num_vertices=None, stretch_amt=0, rotation_deg=0, target_idx=None,
                          concave_idx=None, size=(800, 800), texture_path=None):
    """
    Generates a polygon with a specific concave vertex and a target vertex
    whose stretch starts from a flat-edge position.
    With rotation option.
    With image fill option.
    """
    if num_vertices is None or num_vertices < 3:
        raise ValueError("Number of vertices should be 3 or more.")

    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)

    center_x, center_y = size[0] // 2, size[1] // 2
    base_radius = 200
    rotation_rad = math.radians(rotation_deg)

    points = []
    for i in range(num_vertices):
        angle = (2 * math.pi * i / num_vertices) - (math.pi / 2) + rotation_rad

        # --- RADIUS LOGIC ---

        # 1. First priority: Is it the concave vertex? (Folded inward)
        if concave_idx is not None and i == concave_idx:
            current_radius = base_radius / 2

        # 2. Second priority: Is it the target vertex? (Starts from flat edge)
        elif target_idx is not None and i == target_idx:
            # 0 stretch = straight line.
            # For "normal" vertex: stretch_amt = base_radius - flat_edge_radius.
            flat_edge_radius = base_radius * math.cos(math.pi / num_vertices)
            current_radius = flat_edge_radius + stretch_amt

        # 3. Default: All other vertices stay at the base radius
        else:
            current_radius = base_radius

        x = center_x + current_radius * math.cos(angle)
        y = center_y + current_radius * math.sin(angle)
        points.append((x, y))

    # --- RENDER LOGIC ---
    mask_draw.polygon(points, fill=255)
    final_img = Image.new("RGB", size, "white")

    if texture_path and os.path.exists(texture_path):
        try:
            texture = Image.open(texture_path).convert("RGB")
            texture = ImageOps.fit(texture, size, Image.Resampling.LANCZOS)
            final_img.paste(texture, (0, 0), mask)
        except Exception as e:
            print(f"Error loading image: {e}")

    draw = ImageDraw.Draw(final_img)
    draw.polygon(points, outline="black", width=5)

    return final_img, points[target_idx]


def run_full_experiment(trial_list, display_duration_sec=3):
    """
    Handles the full-screen display loop: Fixation -> Pause/Wait -> Stimulus.
    """
    window_name = "Experiment"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.waitKey(500) # Stabilization pause

    # Detect actual screen resolution
    rect = cv2.getWindowImageRect(window_name)
    sw, sh = rect[2], rect[3]
    if sh < 100:
        sw, sh = 1920, 1080 # Fallback resolution

    # --- NEW: Define 3x3 Fixation Grid ---
    # Create a margin of 10% from the edges of the screen
    margin_x, margin_y = sw // 10, sh // 10
    grid_x = np.linspace(margin_x, sw - margin_x, 3, dtype=int)
    grid_y = np.linspace(margin_y, sh - margin_y, 3, dtype=int)
    grid_points = list(itertools.product(grid_x, grid_y))

    for trial in trial_list:
        # --- NEW: Fixation Screen Step ---
        target_point = random.choice(grid_points)
        px, py = target_point

        # Create a white background for the fixation cross
        fixation_screen = np.full((sh, sw, 3), 255, dtype=np.uint8)
        cross_size = 20

        # Draw the cross (+)
        cv2.line(fixation_screen, (px - cross_size, py), (px + cross_size, py), (0, 0, 0), 2)
        cv2.line(fixation_screen, (px, py - cross_size), (px, py + cross_size), (0, 0, 0), 2)

        cv2.imshow(window_name, fixation_screen)

        # Pause execution here until Eye-tracker feedback or Spacebar press
        continue_experiment = wait_for_fixation(target_point, window_name)

        if not continue_experiment:
            print("Experiment terminated by user.")
            break

        # --- Stimulus Display Step ---
        pil_image = trial["image"]
        open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        full_screen_img = np.full((sh, sw, 3), 255, dtype=np.uint8)
        h, w = open_cv_image.shape[:2]
        y_off, x_off = max(0, (sh - h) // 2), max(0, (sw - w) // 2)  # Ensure offsets are never negative
        slice_h, slice_w = min(h, sh), min(w, sw)   # Ensure the slice dimensions do not exceed the screen size
        full_screen_img[y_off:y_off + slice_h, x_off:x_off + slice_w] = open_cv_image[:slice_h, :slice_w]

        cv2.imshow(window_name, full_screen_img)

        # Display the stimulus for the predefined duration
        if cv2.waitKey(int(display_duration_sec * 1000)) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


# --- 1. GATHER IMAGES ---
image_files = glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.jpg"), recursive=True) + \
              glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.png"), recursive=True)
image_files.sort()

if not image_files:
    print(f"Warning: No images found in {IMAGE_DATABASE_PATH}")

# --- 2. PREPARE AUTOMATED EXPERIMENT ---
# Factors for the automated generation
auto_polygon_types = [4, 5, 6]
stretch_val = 50
stretch_steps = [step * stretch_val for step in range(-2, 3)]
rotation_options = [0, 45, 90]
fill_options = [True, False]
concave_options = [None, 2]

# Generate all automated combinations
auto_combos = list(
    itertools.product(auto_polygon_types, stretch_steps, rotation_options, fill_options, concave_options))
random.shuffle(auto_combos)

trial_data_auto = []
for sides, s_amt, rot, is_filled, c_idx in auto_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, _ = generate_auto_polygon(
        num_vertices=sides,
        stretch_amt=s_amt,
        rotation_deg=rot,
        target_idx=0,  # The vertex that gets stretched
        concave_idx=c_idx,
        texture_path=tex,
        size=IMAGE_SIZE
    )
    trial_data_auto.append({"image": img, "type": "auto"})

# --- 3. PREPARE MANUAL EXPERIMENT ---
# Define your manual shapes as pairs of (radii_list, angles_list)
manual_shapes = [
    # Example 1: Square with varied radii
    ([200, 100, 200, 100], [90, 90, 90, 90]),
    # Example 2: Triangle with specific angles
    ([250, 200, 250], [150, 110, 100]),
]

# Manual combinations (Shape x Rotation x Fill)
manual_combos = list(itertools.product(manual_shapes, rotation_options, fill_options))
random.shuffle(manual_combos)

trial_data_manual = []
for (radii, angles), rot, is_filled in manual_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img = generate_manual_polygon(
        manual_radii=radii,
        manual_angles_deg=angles,
        rotation_deg=rot,
        texture_path=tex,
        size=IMAGE_SIZE
    )
    trial_data_manual.append({"image": img, "type": "manual"})

# --- 4. START EXPERIMENT ---
# Change the list name to switch between experiments

print(f"Starting experiment with {len(trial_data_auto)} automated trials...")
# run_full_experiment(trial_data_auto, display_duration_sec=DISPLAY_TIME_SEC)

# To run manual instead, uncomment the line below and comment the one above:
# run_full_experiment(trial_data_manual, display_duration_sec=DISPLAY_TIME_SEC)
