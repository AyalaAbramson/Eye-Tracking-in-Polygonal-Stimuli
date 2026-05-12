from PIL import Image, ImageDraw
import math
import random
import itertools
import cv2
import numpy as np
import pandas as pd  # Optional: for saving the trial list easily


def generate_polygon_stimulus(num_vertices, stretch_amt, rotation_deg, target_idx=0, size=(800, 800), highlight_target=False):
    """
    Generates a single static image of a polygon.
    If highlight_target is True, the stretched vertex is marked with a red dot.
    """
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)

    center_x, center_y = size[0] // 2, size[1] // 2
    base_radius = 180
    rotation_rad = math.radians(rotation_deg)

    points = []  # A list that contains all polygon points
    for i in range(num_vertices):
        # Calculate angle and add global rotation
        angle = (2 * math.pi * i / num_vertices) - (math.pi / 2) + rotation_rad

        # Apply stretch only to the target vertex
        current_radius = base_radius + stretch_amt if i == target_idx else base_radius

        x = center_x + current_radius * math.cos(angle)
        y = center_y + current_radius * math.sin(angle)
        points.append((x, y))

    # Draw the polygon skeleton
    draw.polygon(points, outline="black", width=5)

    # NEW: Highlight the target vertex if requested
    if highlight_target:
        target_x, target_y = points[target_idx]
        dot_radius = 6
        # Draw a red circle around the vertex coordinates
        draw.ellipse(
            (target_x - dot_radius, target_y - dot_radius,
             target_x + dot_radius, target_y + dot_radius),
            fill="red", outline="black"
        )

    # Return the image and the target coordinates
    target_pos = points[target_idx]
    return img, target_pos


def run_automated_experiment(trial_list, display_duration_sec=3):
    """
    Displays the trials automatically with a fixed time interval.

    Args:
        trial_list (list): List of trial dictionaries.
        display_duration_ms (int): Time to show each image in milliseconds.
    """
    print(f"Starting experiment. Each trial lasts {display_duration_sec}sec.")
    print("Press 'q' at any time to stop the experiment.")

    window_name = "Polygons"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    display_duration_ms = display_duration_sec*1000

    for i, trial in enumerate(trial_list):
        # 1. Get the image (assuming it's stored in the dict)
        pil_image = trial["image"]

        # 2. Convert PIL image to OpenCV format (BGR)
        open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # 3. Display the image
        cv2.imshow(window_name, open_cv_image)

        # 4. Wait for the specified time OR for a 'q' key press to quit
        # cv2.waitKey returns the code of the pressed key
        key = cv2.waitKey(display_duration_ms) & 0xFF
        if key == ord('q'):
            print("Experiment terminated by user.")
            break

    cv2.destroyAllWindows()


# --- Example Execution Workflow ---

# Assuming you already have polygon_types, stretch_steps, and rotation_options defined:
polygon_types = [5, 6]
stretch_steps = [step * 50 for step in range(-2, 3)]
rotation_options = [0, 90, 180]

all_combinations = list(itertools.product(polygon_types, stretch_steps, rotation_options))
random.shuffle(all_combinations)

trial_data = []
for i, (sides, stretch, rot) in enumerate(all_combinations):
    stimulus_img, target_coords = generate_polygon_stimulus(sides, stretch, rot, highlight_target = True)
    trial_data.append({
        "trial_id": i + 1,
        "image": stimulus_img,
        "sides": sides,
        "stretch_pixels": stretch,
        "rotation_deg": rot
    })

# Run the automated display with 1.5 seconds per image
run_automated_experiment(trial_data, display_duration_sec=5)