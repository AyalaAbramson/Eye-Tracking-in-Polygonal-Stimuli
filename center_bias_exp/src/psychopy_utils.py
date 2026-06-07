"""
PsychoPy utilities for center_bias_exp.

This module provides functions for creating PsychoPy windows, monitors,
and drawing basic stimuli like instructions, fixation cues, and preparing
polygon shapes and masked images.
"""

from typing import Tuple, Any, Optional
import json
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw

from psychopy import visual, monitors, event, core


def create_monitor_and_window(
    screen_cfg: dict
) -> Tuple[monitors.Monitor, visual.Window]:
    """
    Create PsychoPy Monitor and Window for the experiment.
    
    Builds a Monitor object with physical dimensions and viewing distance,
    then creates a full-screen Window with pixel units and gray background.
    
    Parameters
    ----------
    screen_cfg : dict
        Screen configuration dictionary containing:
        - 'width_cm': Screen width in centimeters
        - 'height_cm': Screen height in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        - 'background_color': RGB color for background (optional, default: [0, 0, 0])
        
    Returns
    -------
    tuple of (monitors.Monitor, visual.Window)
        - monitor: Configured Monitor object
        - window: Full-screen Window with units='pix'
        
    Examples
    --------
    >>> screen = {
    ...     'width_cm': 59.77,
    ...     'height_cm': 33.62,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160],
    ...     'background_color': [0, 0, 0]
    ... }
    >>> mon, win = create_monitor_and_window(screen)
    >>> print(win.size)
    [3840 2160]
    
    Notes
    -----
    The window is created in full-screen mode with allowGUI=False for
    experimental control. Units are set to 'pix' with origin at center.
    """
    # Extract screen parameters
    width_cm = screen_cfg['width_cm']
    distance_cm = screen_cfg['viewing_distance_cm']
    resolution_px = screen_cfg['resolution_px']
    background_color = screen_cfg.get('background_color', [0, 0, 0])
    
    # Create monitor object
    mon = monitors.Monitor('experiment_monitor')
    mon.setWidth(width_cm)
    mon.setDistance(distance_cm)
    mon.setSizePix(resolution_px)
    
    # Create window
    win = visual.Window(
        size=resolution_px,
        monitor=mon,
        units='pix',
        fullscr=True,
        allowGUI=False,
        color=background_color,
        colorSpace='rgb',
        screen=0
    )
    
    # Hide mouse cursor during experiment
    win.mouseVisible = False
    
    return mon, win


def draw_instructions(
    win: visual.Window, 
    text: str,
    wait_for_keypress: bool = True,
    allowed_keys: list = None
) -> Optional[str]:
    """
    Display instruction text and optionally wait for keypress.
    
    Shows centered text on the screen and blocks until the participant
    presses an allowed key to continue.
    
    Parameters
    ----------
    win : visual.Window
        PsychoPy window to draw on.
    text : str
        Instruction text to display. Can include newlines for
        multi-line instructions.
    wait_for_keypress : bool, optional
        If True (default), wait for keypress before returning.
        If False, display text and return immediately.
    allowed_keys : list, optional
        List of keys that will advance. Default is ['space'].
        
    Returns
    -------
    str or None
        The key that was pressed, or None if wait_for_keypress=False.
        
    Examples
    --------
    >>> mon, win = create_monitor_and_window(screen_cfg)
    >>> draw_instructions(win, "Welcome to the experiment.\\n\\nPress SPACE to begin.")
    
    Notes
    -----
    Text is displayed in white color with a reasonable font size.
    Event buffer is cleared before waiting to avoid stale keypresses.
    """
    if allowed_keys is None:
        allowed_keys = ['space']
    
    # Create text stimulus
    instruction_text = visual.TextStim(
        win,
        text=text,
        pos=(0, 0),
        height=40,
        color='white',
        wrapWidth=win.size[0] * 0.8  # Wrap at 80% of window width
    )
    
    # Draw and flip
    instruction_text.draw()
    win.flip()
    
    if not wait_for_keypress:
        return None
    
    # Clear any pending events to avoid stale keypresses
    event.clearEvents()
    
    # Wait for allowed key with a loop to ensure responsiveness
    key_pressed = None
    while key_pressed is None:
        # Check for keys
        keys = event.getKeys(keyList=allowed_keys)
        if keys:
            key_pressed = keys[0]
        
        # Small delay to prevent CPU spinning
        core.wait(0.01, hogCPUperiod=0.0)
        
        # Redraw to keep display active
        instruction_text.draw()
        win.flip()
    
    return key_pressed


def draw_fixation_cue(
    win: visual.Window,
    x_px: float,
    y_px: float,
    size_px: float = 20.0
) -> None:
    """
    Draw a circular fixation cue at specified coordinates.
    
    Draws a small circular cue (typically for fixation or drift correction)
    at the given pixel coordinates and flips the window once.
    
    Parameters
    ----------
    win : visual.Window
        PsychoPy window to draw on.
    x_px : float
        X coordinate in pixels (PsychoPy convention: origin at window center,
        positive x is right).
    y_px : float
        Y coordinate in pixels (PsychoPy convention: origin at window center,
        positive y is up).
    size_px : float, optional
        Diameter of the cue circle in pixels (default: 20.0).
        
    Examples
    --------
    >>> mon, win = create_monitor_and_window(screen_cfg)
    >>> draw_fixation_cue(win, 0, 0, size_px=30)  # Center of screen
    >>> draw_fixation_cue(win, 200, -100, size_px=20)  # Offset position
    
    Notes
    -----
    The cue is drawn as a white circle. For PsychoPy with units='pix',
    pixel coordinates have origin at center: (0, 0) is screen center,
    positive x is right, positive y is up.
    
    IMPORTANT: If your cue coordinates come from EyeLink (origin at top-left),
    you must convert them before calling this function:
        x_psychopy = x_eyelink - width/2
        y_psychopy = height/2 - y_eyelink
    """
    # Create circular cue (red for visibility)
    cue = visual.Circle(
        win,
        radius=size_px / 2.0,
        pos=(x_px, y_px),
        fillColor='red',
        lineColor='red',
        units='pix'
    )
    
    # Draw and flip
    cue.draw()
    win.flip()


def prepare_polygon_shape(
    win: visual.Window,
    polygon_json_path: str,
    aperture_scale_factor: float = 1.0,
    **kwargs
) -> visual.ShapeStim:
    """
    Prepare a polygon shape stimulus for display.
    
    Loads polygon geometry from a JSON file and creates a PsychoPy
    ShapeStim for drawing or masking.
    
    Parameters
    ----------
    win : visual.Window
        PsychoPy window to draw on.
    polygon_json_path : str
        Path to JSON file containing polygon vertex coordinates.
        Expected JSON structure: {"vertices_xy": [[x1, y1], [x2, y2], ...]}
        Vertices should be in canonical coordinates centered at (0, 0).
    aperture_scale_factor : float, optional
        Scale factor to apply to polygon vertices (default: 1.0).
    **kwargs
        Additional arguments for ShapeStim (e.g., fillColor, lineColor, lineWidth).
        Defaults: lineColor='white', fillColor=None (outline only).
        
    Returns
    -------
    visual.ShapeStim
        PsychoPy ShapeStim object with scaled polygon vertices.
        
    Raises
    ------
    FileNotFoundError
        If polygon_json_path does not exist.
    RuntimeError
        If JSON is malformed or missing required 'vertices_xy' field.
        
    Examples
    --------
    >>> mon, win = create_monitor_and_window(screen_cfg)
    >>> polygon = prepare_polygon_shape(
    ...     win, 
    ...     'stimuli/polygons/baseline_rectangle.json',
    ...     aperture_scale_factor=0.8
    ... )
    
    Notes
    -----
    Assumes the JSON contains a 'vertices_xy' field with vertex coordinates
    as a list of [x, y] pairs in canonical (centered) coordinates.
    The vertices are not translated; PsychoPy uses center-origin pixel units.
    """
    # Load JSON file
    json_path = Path(polygon_json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Polygon JSON not found: {polygon_json_path}")
    
    try:
        with open(json_path, 'r') as f:
            polygon_data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {polygon_json_path}: {e}")
    
    # Handle two formats: vertices_xy (standard) or theta (consolidated)
    if 'vertices_xy' in polygon_data:
        vertices = polygon_data['vertices_xy']
    elif 'theta' in polygon_data:
        # Consolidated format: theta values define radial polygon
        # Place vertices at equal angular intervals with radius varying by theta
        thetas = polygon_data['theta']
        n = len(thetas)
        area = polygon_data.get('area', 550)
        
        # Calculate base radius from area
        base_r = np.sqrt(area / np.pi) * 1.2
        mean_theta = np.mean(thetas)
        
        vertices = []
        for i, theta in enumerate(thetas):
            angle = 2 * np.pi * i / n
            local_r = base_r * (theta / mean_theta)
            x = local_r * np.cos(angle)
            y = local_r * np.sin(angle)
            vertices.append([x, y])
    else:
        raise RuntimeError(
            f"JSON file {polygon_json_path} missing required 'vertices_xy' or 'theta' field. "
            f"Available fields: {list(polygon_data.keys())}"
        )
    
    if not isinstance(vertices, list) or len(vertices) < 3:
        raise RuntimeError(
            f"'vertices' must be a list of at least 3 [x, y] pairs, "
            f"got {len(vertices) if isinstance(vertices, list) else 'non-list'}"
        )
    
    # Convert to numpy for calculations
    vertices_array = np.array(vertices)

    # Calculate current bounding box
    min_xy = vertices_array.min(axis=0)
    max_xy = vertices_array.max(axis=0)
    current_width = max_xy[0] - min_xy[0]
    current_height = max_xy[1] - min_xy[1]
    current_max_dim = max(current_width, current_height)

    # Apply shape-specific display scale multiplier for compact shapes
    # These shapes are naturally small/compact, so we make them larger on screen
    # NOTE: Base aperture_scale_factor is 1987px (92% of 2160px screen)
    # Maximum safe size is ~2052px (95% of screen), so max multiplier is 1.033
    # We use SMALLER increases to avoid clipping
    shape_name = Path(polygon_json_path).stem

    # Very small shapes get 3% size boost (from 1987 to 2047px)
    very_compact_shapes = ['iso_chc_01', 'iso_chc_02', 'iso_chc_03',
                           'iso_com_01', 'iso_com_02', 'iso_com_03']

    # Moderately small shapes get 1.5% size boost (from 1987 to 2017px)
    compact_shapes = ['allfar_convex', 'iso_bbc_02', 'iso_bbc_03',
                      'iso_icc_01', 'iso_icc_02', 'iso_icc_03']

    if shape_name in very_compact_shapes:
        # Make very compact shapes 3% larger on screen (safe for 2160px display)
        display_multiplier = 1.03
        print(f"DEBUG: Shape '{shape_name}': 3% size boost (very compact) - multiplier={display_multiplier}, final={int(aperture_scale_factor * display_multiplier)}px")
    elif shape_name in compact_shapes:
        # Make compact shapes 1.5% larger on screen (safe for 2160px display)
        display_multiplier = 1.015
        print(f"DEBUG: Shape '{shape_name}': 1.5% size boost (compact) - multiplier={display_multiplier}, final={int(aperture_scale_factor * display_multiplier)}px")
    else:
        display_multiplier = 1.0
        print(f"DEBUG: Shape '{shape_name}': standard size - multiplier={display_multiplier}, final={int(aperture_scale_factor * display_multiplier)}px")

    # Normalize polygon to target size, then apply aperture_scale_factor
    # aperture_scale_factor here represents the TARGET SIZE in pixels
    # (e.g., 1987 for 92% of 2160px screen height)
    # This ensures all polygons end up the same size regardless of canonical size
    adjusted_scale = aperture_scale_factor * display_multiplier

    if current_max_dim > 0:
        normalize_scale = adjusted_scale / current_max_dim
    else:
        normalize_scale = adjusted_scale
    
    # Center the polygon at origin and scale to target size
    center_x = (min_xy[0] + max_xy[0]) / 2
    center_y = (min_xy[1] + max_xy[1]) / 2
    
    scaled_vertices = [
        [(x - center_x) * normalize_scale, (y - center_y) * normalize_scale]
        for x, y in vertices
    ]
    
    # Set default styling (white outline, no fill)
    style_kwargs = {
        'lineColor': 'white',
        'fillColor': None,
        'lineWidth': 2
    }
    style_kwargs.update(kwargs)  # Allow caller to override defaults
    
    # Create ShapeStim with scaled vertices
    shape = visual.ShapeStim(
        win,
        vertices=scaled_vertices,
        units='pix',
        closeShape=True,
        **style_kwargs
    )
    
    return shape


def prepare_masked_image(
    win: visual.Window,
    image_path: str,
    polygon_shape: visual.ShapeStim,
    shape_name: str = "",
    position: Tuple[float, float] = (0, 0),
    **kwargs
) -> visual.ImageStim:
    """
    Prepare a masked image stimulus for display.
    
    Loads an image and applies a polygon mask to create a masked
    image stimulus for the experiment. The polygon is first scaled to fit
    INSIDE the original image dimensions, then the masked result is
    upscaled to the target display size.
    
    Parameters
    ----------
    win : visual.Window
        PsychoPy window to draw on.
    image_path : str
        Path to image file to load.
    polygon_shape : visual.ShapeStim
        Polygon shape stimulus to use as mask (from prepare_polygon_shape).
        The vertices of this shape define the mask boundary.
    shape_name : str, optional
        Name of the shape (extracted from polygon_json_path) for margin optimization.
        Compact shapes get larger display area (default: "").
    position : tuple of (float, float), optional
        Position (x, y) in pixels for image center (default: (0, 0)).
    **kwargs
        Additional arguments for ImageStim (e.g., size, opacity).
        
    Returns
    -------
    visual.ImageStim
        PsychoPy ImageStim object with applied polygon mask.
        
    Raises
    ------
    FileNotFoundError
        If image_path does not exist.
    RuntimeError
        If image cannot be loaded or mask creation fails.
        
    Notes
    -----
    The approach is:
    1. Load the original image (e.g., 1920x1080 CAT2000 images)
    2. Scale the polygon to fit entirely within the image area
    3. Create mask at image resolution
    4. Apply mask to image
    5. Display at the polygon's target size (aperture_scale_factor)
    """
    # Check if image exists
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Load the original image to get its dimensions
    try:
        original_img = Image.open(img_path)
        img_width, img_height = original_img.size
    except Exception as e:
        raise RuntimeError(f"Failed to load image {image_path}: {e}")
    
    # Get polygon vertices from shape (these are already scaled to target size)
    vertices = polygon_shape.vertices
    if vertices is None:
        raise RuntimeError("Polygon shape has no vertices for masking")
    vertices_len = len(vertices) if hasattr(vertices, '__len__') else 0
    if vertices_len < 3:
        raise RuntimeError(f"Polygon shape has insufficient vertices for masking: {vertices_len}")
    
    vertices_array = np.array(vertices)
    
    # Find bounding box of the polygon (already scaled to target display size)
    min_x, min_y = vertices_array.min(axis=0)
    max_x, max_y = vertices_array.max(axis=0)
    poly_width = max_x - min_x
    poly_height = max_y - min_y
    
    if poly_width <= 0 or poly_height <= 0:
        raise RuntimeError("Polygon has zero width or height, cannot create mask")
    
    # The polygon vertices are at target display size (e.g., ~1987 px)
    # We need to scale them DOWN to fit inside the original image
    # Use the smaller dimension of the image to ensure polygon fits completely
    img_min_dim = min(img_width, img_height)
    poly_max_dim = max(poly_width, poly_height)
    
    # Scale factor to fit polygon inside image (with larger margin for elongated shapes)
    # CRITICAL: Use conservative margin to prevent any clipping after upscaling
    # Use shape-specific margins: smaller margins for compact/isolated shapes, larger for elongated

    # Define shape categories with optimized margins (must match prepare_polygon_shape)
    very_compact_shapes = ['iso_chc_01', 'iso_chc_02', 'iso_chc_03',
                           'iso_com_01', 'iso_com_02', 'iso_com_03']
    compact_shapes = ['allfar_convex', 'iso_bbc_02', 'iso_bbc_03',
                      'iso_icc_01', 'iso_icc_02', 'iso_icc_03']

    # Determine margin based on shape compactness
    # Very compact shapes (3% display boost) need tighter margins to maximize use of image area
    if shape_name in very_compact_shapes:
        margin_factor = 0.88  # 12% margin for very compact shapes (MAXIMUM DISPLAY AREA)
        print(f"DEBUG MASK: Shape '{shape_name}' very compact - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")
    elif shape_name in compact_shapes:
        margin_factor = 0.85  # 15% margin for compact shapes (MORE DISPLAY AREA)
        print(f"DEBUG MASK: Shape '{shape_name}' compact - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")
    else:
        margin_factor = 0.75  # 25% margin for elongated shapes (conservative)
        print(f"DEBUG MASK: Shape '{shape_name}' standard - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")

    scale_to_image = (img_min_dim * margin_factor) / poly_max_dim
    
    # Scale vertices to fit inside image coordinates (centered)
    # Image center is (img_width/2, img_height/2)
    img_center_x = img_width / 2
    img_center_y = img_height / 2
    
    # Create mask at image resolution
    mask_img = Image.new('L', (img_width, img_height), 0)  # Black = transparent
    draw = ImageDraw.Draw(mask_img)
    
    # Transform polygon vertices to image coordinates
    # vertices are centered at (0,0) in display coords
    # We scale them and center them in the image
    mask_vertices = []
    for x, y in vertices:
        # Scale to fit image, center in image
        img_x = img_center_x + (x * scale_to_image)
        img_y = img_center_y - (y * scale_to_image)  # Flip y (image coords: y down)
        mask_vertices.append((img_x, img_y))
    
    # Draw filled polygon on mask (white = visible)
    draw.polygon(mask_vertices, fill=255)
    
    # Apply slight blur for anti-aliasing
    from PIL import ImageFilter
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Apply mask to the original image
    # Convert to RGBA for proper masking
    if original_img.mode != 'RGBA':
        original_img = original_img.convert('RGBA')
    
    # Create the masked image by setting alpha channel
    mask_array = np.array(mask_img)
    img_array = np.array(original_img)
    img_array[:, :, 3] = mask_array  # Set alpha channel
    
    masked_pil = Image.fromarray(img_array, 'RGBA')
    
    # Crop to the polygon's bounding box in image coordinates
    # to avoid unnecessary transparent areas
    bbox_left = int(img_center_x + min_x * scale_to_image)
    bbox_right = int(img_center_x + max_x * scale_to_image)
    bbox_top = int(img_center_y - max_y * scale_to_image)  # y is flipped
    bbox_bottom = int(img_center_y - min_y * scale_to_image)
    
    # Add small padding to ensure we don't clip edges
    padding = 5
    bbox_left = max(0, bbox_left - padding)
    bbox_right = min(img_width, bbox_right + padding)
    bbox_top = max(0, bbox_top - padding)
    bbox_bottom = min(img_height, bbox_bottom + padding)
    
    cropped = masked_pil.crop((bbox_left, bbox_top, bbox_right, bbox_bottom))
    
    # Calculate display size - the polygon should appear at its original target size
    # The cropped image needs to be scaled up to match
    cropped_width = bbox_right - bbox_left
    cropped_height = bbox_bottom - bbox_top
    
    # Scale factor from cropped size to target display size
    display_scale = poly_max_dim / (max(cropped_width, cropped_height) - 2 * padding)
    display_width = int(cropped_width * display_scale)
    display_height = int(cropped_height * display_scale)
    
    # Convert mask for PsychoPy (needs to be square normalized array)
    # Create a new square mask at the display size
    display_size = max(display_width, display_height)
    
    # SAFETY CHECK: Ensure final display size doesn't exceed screen bounds
    screen_safe_size = min(win.size[0], win.size[1]) * 0.95  # 95% of screen dimension
    if display_size > screen_safe_size:
        print(f"WARNING: Polygon display size ({display_size}px) exceeds safe screen bounds ({screen_safe_size:.0f}px)")
        print(f"         Rescaling to prevent clipping...")
        display_size = int(screen_safe_size)

    # Resize cropped image to display size
    cropped_resized = cropped.resize((display_size, display_size), Image.LANCZOS)
    
    # Save to temporary file for PsychoPy (it handles RGBA properly this way)
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    cropped_resized.save(temp_file.name, 'PNG')
    temp_file.close()
    
    # Create ImageStim - no mask needed since image already has alpha
    try:
        image_stim = visual.ImageStim(
            win,
            image=temp_file.name,
            pos=position,
            size=(display_size, display_size),
            units='pix',
            interpolate=True,
            **kwargs
        )
        # Store temp file path for cleanup
        image_stim._temp_file = temp_file.name
    except Exception as e:
        import os
        os.unlink(temp_file.name)
        raise RuntimeError(f"Failed to create ImageStim: {e}")
    
    return image_stim
