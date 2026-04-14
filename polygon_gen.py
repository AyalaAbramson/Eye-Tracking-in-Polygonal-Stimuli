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
    Displays the trials in true fullscreen with white background padding.
    """
    print(f"Starting experiment. Each trial lasts {display_duration_sec}sec.")
    print("Press 'q' at any time to stop the experiment.")

    window_name = "Polygons"

    # 1. Setup Fullscreen
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # 2. Give the OS time to adjust (fixes the "40 pixels" error)
    cv2.waitKey(500)

    display_duration_ms = int(display_duration_sec * 1000)

    for i, trial in enumerate(trial_list):
        pil_image = trial["image"]
        open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # 3. Securely get screen resolution
        rect = cv2.getWindowImageRect(window_name)
        sw, sh = rect[2], rect[3]

        # If the system still reports a tiny height (like 40), use a standard fallback
        if sh < 100:
            sw, sh = 1920, 1080

            # 4. Create the white background
        full_screen_img = np.full((sh, sw, 3), 255, dtype=np.uint8)

        h, w = open_cv_image.shape[:2]

        # 5. Calculate offsets and handle potential size mismatches
        y_off = max(0, (sh - h) // 2)
        x_off = max(0, (sw - w) // 2)

        # Slice logic to prevent ValueError if image is larger than screen
        slice_h = min(h, sh)
        slice_w = min(w, sw)

        # 6. Paste image into the white canvas
        full_screen_img[y_off:y_off + slice_h, x_off:x_off + slice_w] = open_cv_image[:slice_h, :slice_w]

        cv2.imshow(window_name, full_screen_img)

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