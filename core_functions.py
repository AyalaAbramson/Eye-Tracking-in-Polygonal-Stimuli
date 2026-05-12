import os
import math
import random
import itertools
import numpy as np
import pygame
from PIL import Image, ImageDraw, ImageOps


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
    Handles the full-screen display loop using Pygame.
    If debug=True, draws technical overlays (grids, vertices) over the display.
    """
    import pygame
    pygame.init()

    # 1. Setup fullscreen window
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    sw, sh = screen.get_size()
    center_x, center_y = sw // 2, sh // 2

    # Define basic colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    MAGENTA = (255, 0, 255)
    CYAN = (0, 255, 255)
    ORANGE = (255, 165, 0)

    # 2. Define Grids
    grid_size = int(sh * 0.8)
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

    cross_size = 20
    clock = pygame.time.Clock()

    for trial in trial_list:
        # ==========================================
        # STAGE 1: FIXATION SCREEN
        # ==========================================
        target_point = random.choice(grid_points)
        px, py = target_point

        screen.fill(WHITE)

        # Draw Grids on Fixation (ONLY IN DEBUG MODE)
        if debug:
            for gx, gy in grid_points:
                pygame.draw.circle(screen, BLUE, (gx, gy), 5)
            for mx, my in mini_grid_points:
                pygame.draw.circle(screen, GREEN, (mx, my), 5)

        # Draw Fixation Cross (+)
        pygame.draw.line(screen, BLACK, (px - cross_size, py), (px + cross_size, py), 2)
        pygame.draw.line(screen, BLACK, (px, py - cross_size), (px, py + cross_size), 2)

        pygame.display.flip()

        # Wait for SPACE to continue, or Q/ESC to abort
        waiting_for_fixation = True
        abort = False
        while waiting_for_fixation:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        waiting_for_fixation = False
                    elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        abort = True
                        waiting_for_fixation = False
            clock.tick(60)  # Prevents the loop from freezing the computer

        if abort:
            print("Experiment terminated by user.")
            break

        # ==========================================
        # STAGE 2: STIMULUS DISPLAY
        # ==========================================
        screen.fill(WHITE)

        # Convert PIL Image to Pygame Surface
        pil_image = trial["image"]
        mode = pil_image.mode
        size = pil_image.size
        data = pil_image.tobytes()
        py_image = pygame.image.fromstring(data, size, mode)

        stim_px, stim_py = random.choice(mini_grid_points)
        w, h = size

        # Calculate top-left coordinates to center the image perfectly
        top_left_x = stim_px - (w // 2)
        top_left_y = stim_py - (h // 2)

        # Blit (draw) the image onto the screen
        screen.blit(py_image, (top_left_x, top_left_y))

        # Draw Overlays on Stimulus (ONLY IN DEBUG MODE)
        if debug:
            for gx, gy in grid_points:
                pygame.draw.circle(screen, BLUE, (gx, gy), 5)
            for mx, my in mini_grid_points:
                pygame.draw.circle(screen, GREEN, (mx, my), 5)

            pygame.draw.circle(screen, RED, (stim_px, stim_py), 8)

            # Draw base skeleton
            base_pts = trial.get("base_points")
            if base_pts:
                screen_base_pts = [(int(bx + top_left_x), int(by + top_left_y)) for bx, by in base_pts]
                if len(screen_base_pts) > 2:
                    pygame.draw.polygon(screen, ORANGE, screen_base_pts, 2)

            # Draw lines and actual points
            for px_img, py_img in trial.get("points", []):
                sx, sy = int(px_img + top_left_x), int(py_img + top_left_y)
                pygame.draw.line(screen, MAGENTA, (stim_px, stim_py), (sx, sy), 2)
                pygame.draw.circle(screen, MAGENTA, (sx, sy), 6)

            # Highlight the concave vertex
            c_idx = trial.get("concave_idx")
            if c_idx is not None:
                pts = trial.get("points", [])
                if 0 <= c_idx < len(pts):
                    cx_img, cy_img = pts[c_idx]
                    sx, sy = int(cx_img + top_left_x), int(cy_img + top_left_y)
                    pygame.draw.circle(screen, CYAN, (sx, sy), 14, 3)

        pygame.display.flip()

        # Display for duration, but allow breaking out early with Q/ESC
        start_ticks = pygame.time.get_ticks()
        duration_ms = display_duration_sec * 1000
        stimulus_running = True

        while stimulus_running:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        abort = True
                        stimulus_running = False

            # Check if time is up
            if pygame.time.get_ticks() - start_ticks > duration_ms:
                stimulus_running = False

            clock.tick(60)

        if abort:
            print("Experiment terminated by user.")
            break

    # Safely close Pygame window at the end
    pygame.quit()