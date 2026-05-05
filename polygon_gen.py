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

# Setting the seed here ensures the shuffle and image selection
# are identical every time the script runs.
random.seed(42)


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


def run_automated_experiment(trial_list, display_duration_sec=3):
    """
    Handles the fullscreen display and timing of the stimulus sequence.
    """
    window_name = "Polygons"

    # Set up the window for true fullscreen display
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Short pause to allow the OS to stabilize the fullscreen window
    cv2.waitKey(500)

    for i, trial in enumerate(trial_list):
        # Convert PIL Image to OpenCV format (BGR)
        pil_image = trial["image"]
        open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # Get actual screen resolution
        rect = cv2.getWindowImageRect(window_name)
        sw, sh = rect[2], rect[3]

        # Fallback if window dimensions are not yet detected correctly
        if sh < 100:
            sw, sh = 1920, 1080

        # Create a full-screen white canvas
        full_screen_img = np.full((sh, sw, 3), 255, dtype=np.uint8)

        # Calculate offsets to center the stimulus
        h, w = open_cv_image.shape[:2]
        y_off, x_off = max(0, (sh - h) // 2), max(0, (sw - w) // 2)

        # Securely copy the stimulus onto the canvas (prevents broadcast errors)
        slice_h, slice_w = min(h, sh), min(w, sw)
        full_screen_img[y_off:y_off + slice_h, x_off:x_off + slice_w] = open_cv_image[:slice_h, :slice_w]

        # Display and wait
        cv2.imshow(window_name, full_screen_img)

        # Close experiment if 'q' is pressed
        if cv2.waitKey(int(display_duration_sec * 1000)) & 0xFF == ord('q'):
            print("Experiment terminated by user.")
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
#run_automated_experiment(trial_data_auto, display_duration_sec=DISPLAY_TIME_SEC)

# To run manual instead, uncomment the line below and comment the one above:
run_automated_experiment(trial_data_manual, display_duration_sec=DISPLAY_TIME_SEC)
