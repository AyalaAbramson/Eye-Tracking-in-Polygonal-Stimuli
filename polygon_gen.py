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
TRIAL_REPETITIONS = 1  # Number of times each polygon combination repeats
DEBUG_MODE = True  # Toggle to False for the real experiment

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
    has_texture = False
    if texture_path and os.path.exists(texture_path):
        try:
            texture = Image.open(texture_path).convert("RGB")
            texture = ImageOps.fit(texture, size, Image.Resampling.LANCZOS)
            final_img.paste(texture, (0, 0), mask)
            has_texture = True
        except Exception as e:
            print(f"Error loading texture: {e}")

    # Draw the final outline ONLY if there is no image filling the polygon
    if not has_texture:
        draw = ImageDraw.Draw(final_img)
        draw.polygon(points, outline="black", width=5)

    return final_img, points, None


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
    base_points = []
    for i in range(num_vertices):
        angle = (2 * math.pi * i / num_vertices) - (math.pi / 2) + rotation_rad
        base_x = center_x + base_radius * math.cos(angle)
        base_y = center_y + base_radius * math.sin(angle)
        base_points.append((base_x, base_y))  # points for debug mode

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

    has_texture = False
    if texture_path and os.path.exists(texture_path):
        try:
            texture = Image.open(texture_path).convert("RGB")
            texture = ImageOps.fit(texture, size, Image.Resampling.LANCZOS)
            final_img.paste(texture, (0, 0), mask)
            has_texture = True
        except Exception as e:
            print(f"Error loading image: {e}")

    # Draw the final outline ONLY if there is no image filling the polygon
    if not has_texture:
        draw = ImageDraw.Draw(final_img)
        draw.polygon(points, outline="black", width=5)

    return final_img, points, base_points


def run_full_experiment(trial_list, display_duration_sec=3, debug=False):
    """
    Handles the full-screen display loop: Fixation -> Pause/Wait -> Stimulus.
    """
    window_name = "Experiment"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.waitKey(500)  # Stabilization pause

    # Detect actual screen resolution
    rect = cv2.getWindowImageRect(window_name)
    sw, sh = rect[2], rect[3]
    if sh < 100:
        sw, sh = 1920, 1080  # Fallback resolution

    # --- Define Main Fixation Grid (Large, 80% of screen) ---
    grid_size = int(sh * 0.8)
    center_x = sw // 2
    center_y = sh // 2

    start_x = center_x - (grid_size // 2)
    end_x = center_x + (grid_size // 2)
    start_y = center_y - (grid_size // 2)
    end_y = center_y + (grid_size // 2)

    grid_x = np.linspace(start_x, end_x, 3, dtype=int)
    grid_y = np.linspace(start_y, end_y, 3, dtype=int)
    grid_points = list(itertools.product(grid_x, grid_y))

    # --- Define Mini-Grid for Polygon Placement (Small, e.g., 20% of screen) ---
    mini_grid_size = int(sh * 0.2)  # Change 0.2 to adjust the spread of the polygons

    m_start_x = center_x - (mini_grid_size // 2)
    m_end_x = center_x + (mini_grid_size // 2)
    m_start_y = center_y - (mini_grid_size // 2)
    m_end_y = center_y + (mini_grid_size // 2)

    mini_grid_x = np.linspace(m_start_x, m_end_x, 3, dtype=int)
    mini_grid_y = np.linspace(m_start_y, m_end_y, 3, dtype=int)
    mini_grid_points = list(itertools.product(mini_grid_x, mini_grid_y))

    for trial in trial_list:
        # --- Fixation Screen Step ---
        target_point = random.choice(grid_points)
        px, py = target_point

        # Create a white background for the fixation cross
        fixation_screen = np.full((sh, sw, 3), 255, dtype=np.uint8)
        cross_size = 20

        # Draw Grids on Fixation (ONLY IN DEBUG MODE)
        if debug:
            for gx, gy in grid_points:
                cv2.circle(fixation_screen, (gx, gy), 5, (255, 0, 0), -1)
            for mx, my in mini_grid_points:
                cv2.circle(fixation_screen, (mx, my), 5, (0, 255, 0), -1)

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

        # NEW: Choose a random center point from the MINI-GRID for the polygon
        stim_px, stim_py = random.choice(mini_grid_points)

        # Calculate the ideal top-left coordinate to place the center of the image on the grid point
        x_off = stim_px - (w // 2)
        y_off = stim_py - (h // 2)

        # Safely calculate boundaries to prevent drawing outside the screen
        # 1. Screen coordinates (where to draw on the monitor)
        screen_x1 = max(0, x_off)
        screen_y1 = max(0, y_off)
        screen_x2 = min(sw, x_off + w)
        screen_y2 = min(sh, y_off + h)

        # 2. Image coordinates (what part of the polygon image to crop if it goes out of bounds)
        img_x1 = max(0, -x_off)
        img_y1 = max(0, -y_off)
        img_x2 = img_x1 + (screen_x2 - screen_x1)
        img_y2 = img_y1 + (screen_y2 - screen_y1)

        # Safely copy the image slice onto the full screen canvas
        if screen_x1 < screen_x2 and screen_y1 < screen_y2:
            full_screen_img[screen_y1:screen_y2, screen_x1:screen_x2] = open_cv_image[img_y1:img_y2, img_x1:img_x2]

        # Draw Overlays on Stimulus (ONLY IN DEBUG MODE)
        if debug:
            for gx, gy in grid_points:
                cv2.circle(full_screen_img, (gx, gy), 5, (255, 0, 0), -1)
            for mx, my in mini_grid_points:
                cv2.circle(full_screen_img, (mx, my), 5, (0, 255, 0), -1)

            cv2.circle(full_screen_img, (stim_px, stim_py), 8, (0, 0, 255), -1)

            base_pts = trial.get("base_points")
            if base_pts:
                screen_base_pts = [(int(bx + x_off), int(by + y_off)) for bx, by in base_pts]
                for i in range(len(screen_base_pts)):
                    p1 = screen_base_pts[i]
                    p2 = screen_base_pts[(i + 1) % len(screen_base_pts)]
                    cv2.line(full_screen_img, p1, p2, (0, 165, 255), 2)

            for px_img, py_img in trial.get("points", []):
                sx, sy = int(px_img + x_off), int(py_img + y_off)
                cv2.line(full_screen_img, (stim_px, stim_py), (sx, sy), (255, 0, 255), 2)
                cv2.circle(full_screen_img, (sx, sy), 6, (255, 0, 255), -1)

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
auto_polygon_types = [4, 5]
stretch_val = 50
stretch_steps = [step * stretch_val for step in range(-2, 3)]
rotation_options = [0, 90]
fill_options = [True]
concave_options = [None, 2]

# Generate all automated combinations
base_auto_combos = list(
    itertools.product(auto_polygon_types, stretch_steps, rotation_options, fill_options, concave_options))
auto_combos = base_auto_combos * TRIAL_REPETITIONS
random.shuffle(auto_combos)

trial_data_auto = []
for sides, s_amt, rot, is_filled, c_idx in auto_combos:
    tex = random.choice(image_files) if (image_files and is_filled) else None

    img, actual_points, base_points = generate_auto_polygon(
        num_vertices=sides,
        stretch_amt=s_amt,
        rotation_deg=rot,
        target_idx=0,  # The vertex that gets stretched
        concave_idx=c_idx,
        texture_path=tex,
        size=IMAGE_SIZE
    )
    trial_data_auto.append({"image": img, "type": "auto", "points": actual_points,
                            "base_points": base_points})

# --- 3. PREPARE MANUAL EXPERIMENT ---
# Define your manual shapes as pairs of (radii_list, angles_list)
manual_shapes = [
    # Example 1: Square with varied radii
    ([200, 100, 200, 100], [90, 90, 90, 90]),
    # Example 2: Triangle with specific angles
    ([250, 200, 250], [150, 110, 100]),
]

# Manual combinations (Shape x Rotation x Fill)
base_manual_combos = list(itertools.product(manual_shapes, rotation_options, fill_options))
manual_combos = base_manual_combos * TRIAL_REPETITIONS
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
run_full_experiment(trial_data_auto, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)

# To run manual instead, uncomment the line below and comment the one above:
# run_full_experiment(trial_data_manual, display_duration_sec=DISPLAY_TIME_SEC, debug=DEBUG_MODE)
