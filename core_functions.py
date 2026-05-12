import os
import math
import random
import itertools
from psychopy import visual, event, core
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def wait_for_fixation(target_point, window_name):
    """
    Pauses the experiment on the fixation screen until a signal is received.
    Returns True to proceed to the stimulus, or False to quit the experiment.
    """
    while True:
        # FUTURE EYE-TRACKER IMPLEMENTATION:
        # if eye_tracker.is_looking_at(target_point):
        #     return True

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            return True
        if key == ord('q') or key == 27:
            return False


def generate_manual_polygon(manual_radii, manual_angles_deg, rotation_deg=0, size=(800, 800),
                            texture_path=None):
    """
    Generates a polygon based strictly on manual lists of radii and angles.
    Returns: image, list of actual points, None (no base skeleton for manual)
    """
    if len(manual_radii) != len(manual_angles_deg):
        raise ValueError("The number of radii must match the number of angles.")

    angles_sum = sum(manual_angles_deg)
    if angles_sum != 360:
        raise ValueError(f"The sum of manual angles must be 360. Current: {angles_sum}")

    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    center_x, center_y = size[0] // 2, size[1] // 2
    rotation_rad = math.radians(rotation_deg)

    points = []
    for i in range(len(manual_radii)):
        cumulative_angle = sum(manual_angles_deg[:i])
        angle = math.radians(cumulative_angle) - (math.pi / 2) + rotation_rad

        radius = manual_radii[i]
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append((x, y))

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
            print(f"Error loading texture: {e}")

    if not has_texture:
        draw = ImageDraw.Draw(final_img)
        draw.polygon(points, outline="black", width=5)

    return final_img, points, None


def generate_auto_polygon(num_vertices=None, stretch_amt=0, rotation_deg=0, target_idx=None,
                          concave_idx=None, concave_ratio=0, size=(800, 800), texture_path=None):
    """
    Generates a polygon with a specific concave vertex and a target vertex.
    Returns: image, list of actual points, list of base (skeleton) points
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
        base_points.append((base_x, base_y))

        if concave_idx is not None and i == concave_idx:
            flat_edge_radius = base_radius * math.cos(2 * math.pi / num_vertices)
            concave_depth = base_radius * concave_ratio
            current_radius = flat_edge_radius - concave_depth
        elif target_idx is not None and i == target_idx:
            flat_edge_radius = base_radius * math.cos(2 * math.pi / num_vertices)
            current_radius = flat_edge_radius + stretch_amt
        else:
            current_radius = base_radius

        x = center_x + current_radius * math.cos(angle)
        y = center_y + current_radius * math.sin(angle)
        points.append((x, y))

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

    if not has_texture:
        draw = ImageDraw.Draw(final_img)
        draw.polygon(points, outline="black", width=5)

    return final_img, points, base_points


def run_full_experiment(trial_list, display_duration_sec=3, debug=False):
    """
    Handles the full-screen display loop.
    If debug=True, draws technical overlays (grids, vertices) over the display.
    """
    window_name = "Experiment" + (" (DEBUG MODE)" if debug else "")
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.waitKey(500)

    rect = cv2.getWindowImageRect(window_name)
    sw, sh = rect[2], rect[3]
    if sh < 100:
        sw, sh = 1920, 1080

    # --- Define Grids ---
    grid_size = int(sh * 0.8)
    center_x = sw // 2
    center_y = sh // 2

    start_x, end_x = center_x - (grid_size // 2), center_x + (grid_size // 2)
    start_y, end_y = center_y - (grid_size // 2), center_y + (grid_size // 2)

    grid_points = list(itertools.product(
        np.linspace(start_x, end_x, 3, dtype=int),
        np.linspace(start_y, end_y, 3, dtype=int)
    ))

    mini_grid_size = int(sh * 0.2)
    m_start_x, m_end_x = center_x - (mini_grid_size // 2), center_x + (mini_grid_size // 2)
    m_start_y, m_end_y = center_y - (mini_grid_size // 2), center_y + (mini_grid_size // 2)

    mini_grid_points = list(itertools.product(
        np.linspace(m_start_x, m_end_x, 3, dtype=int),
        np.linspace(m_start_y, m_end_y, 3, dtype=int)
    ))

    for trial in trial_list:
        # --- Fixation Screen Step ---
        target_point = random.choice(grid_points)
        px, py = target_point

        fixation_screen = np.full((sh, sw, 3), 255, dtype=np.uint8)

        # Draw Grids on Fixation (ONLY IN DEBUG MODE)
        if debug:
            for gx, gy in grid_points:
                cv2.circle(fixation_screen, (gx, gy), 5, (255, 0, 0), -1)
            for mx, my in mini_grid_points:
                cv2.circle(fixation_screen, (mx, my), 5, (0, 255, 0), -1)

        cross_size = 20
        cv2.line(fixation_screen, (px - cross_size, py), (px + cross_size, py), (0, 0, 0), 2)
        cv2.line(fixation_screen, (px, py - cross_size), (px, py + cross_size), (0, 0, 0), 2)

        cv2.imshow(window_name, fixation_screen)

        if not wait_for_fixation(target_point, window_name):
            print("Experiment terminated by user.")
            break

        # --- Stimulus Display Step ---
        pil_image = trial["image"]
        open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        full_screen_img = np.full((sh, sw, 3), 255, dtype=np.uint8)
        h, w = open_cv_image.shape[:2]

        stim_px, stim_py = random.choice(mini_grid_points)
        x_off, y_off = stim_px - (w // 2), stim_py - (h // 2)

        screen_x1, screen_y1 = max(0, x_off), max(0, y_off)
        screen_x2, screen_y2 = min(sw, x_off + w), min(sh, y_off + h)

        img_x1, img_y1 = max(0, -x_off), max(0, -y_off)
        img_x2, img_y2 = img_x1 + (screen_x2 - screen_x1), img_y1 + (screen_y2 - screen_y1)

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

            # --- NEW: Highlight the concave vertex ---
            c_idx = trial.get("concave_idx")
            if c_idx is not None:
                pts = trial.get("points", [])
                if 0 <= c_idx < len(pts):
                    cx_img, cy_img = pts[c_idx]
                    sx, sy = int(cx_img + x_off), int(cy_img + y_off)

                    # Draw a prominent cyan ring around the concave vertex
                    cv2.circle(full_screen_img, (sx, sy), 14, (255, 255, 0), 3)
        cv2.imshow(window_name, full_screen_img)

        # Wait for the defined duration, or exit if 'q' or 'Esc' is pressed
        key = cv2.waitKey(int(display_duration_sec * 1000)) & 0xFF
        if key == ord('q') or key == 27:
            print("Experiment terminated by user.")
            break

    cv2.destroyAllWindows()