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


def generate_polygon_stimulus(num_vertices=None, stretch_amt=0, rotation_deg=0, target_idx=None,
                              size=(800, 800), texture_path=None,
                              concave_idx=None):
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


# --- EXECUTION ---

# Gather all image files from the specified directory and subdirectories
image_files = glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.jpg"), recursive=True) + \
              glob.glob(os.path.join(IMAGE_DATABASE_PATH, "**/*.png"), recursive=True)

# Sorting ensures that random.choice behaves identically across different machines/runs
image_files.sort()

if not image_files:
    print(f"No images found in {IMAGE_DATABASE_PATH}. Check your path!")
else:
    print(f"Found {len(image_files)} images.")

# Define experimental parameters
polygon_types = [4, 5, 6]
stretch_val = 50   # stretch amount
stretch_steps = [step * stretch_val for step in range(-2, 3)]  # 5 stretch options
rotation_options = [0, 45, 90]
fill = [True, False]  # Empty / image fill
concave_idx = [None, 0]  # Change according to wanted concave vertex
reps = 0  # number of repetitions for each polygon in the experiment
manual_degrees = []  # Relevant to manual polygon:  sum=360
manual_radius = []  # Relevant to manual polygon: len = len of manual degrees

# Generate all possible combinations of the factors
all_combinations = list(itertools.product(polygon_types, stretch_steps, rotation_options, fill, concave_idx))

# Shuffle the combinations (Order is consistent because of random.seed)
random.shuffle(all_combinations)

trial_data = []

# Build the stimulus list
for i, (sides, stretch, rot) in enumerate(all_combinations):
    # Pick a texture randomly. Because of the seed, the same image
    # will be paired with the same polygon parameters every time.
    current_tex = random.choice(image_files) if image_files else None

    stim_img, coords = generate_polygon_stimulus(
        sides, stretch, rot,
        highlight_target=True,
        size=IMAGE_SIZE,
        texture_path=current_tex
    )

    # Store necessary data for the experiment loop
    trial_data.append({
        "image": stim_img,
        "sides": sides,
        "stretch": stretch,
        "rot": rot,
        "texture": current_tex
    })

# Start the automated display
run_automated_experiment(trial_data, display_duration_sec=DISPLAY_TIME_SEC)
