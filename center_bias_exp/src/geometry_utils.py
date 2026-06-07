"""
Geometry and visual angle conversion utilities for center_bias_exp.

This module provides functions for converting between pixel and degree coordinates,
and for transforming polygon geometry data into screen coordinates with both
pixel and degree representations.
"""

import numpy as np
import pandas as pd
from typing import Dict


def deg2pix_x(deg: float, screen_cfg: dict) -> float:
    """
    Convert horizontal visual angle (degrees) to pixels.
    
    Uses the standard visual angle formula:
    distance_cm = viewing_distance_cm * tan(angle_rad)
    distance_px = distance_cm * (resolution_px / screen_width_cm)
    
    Parameters
    ----------
    deg : float
        Horizontal visual angle in degrees.
    screen_cfg : dict
        Screen configuration dictionary with keys:
        - 'width_cm': Screen width in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        
    Returns
    -------
    float
        Horizontal distance in pixels.
        
    Examples
    --------
    >>> screen = {
    ...     'width_cm': 59.77,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160]
    ... }
    >>> deg2pix_x(5.0, screen)
    570.5
    """
    viewing_distance_cm = screen_cfg['viewing_distance_cm']
    width_cm = screen_cfg['width_cm']
    width_px = screen_cfg['resolution_px'][0]
    
    # Convert degrees to radians
    angle_rad = np.deg2rad(deg)
    
    # Calculate distance in cm
    distance_cm = viewing_distance_cm * np.tan(angle_rad)
    
    # Convert to pixels
    pixels_per_cm = width_px / width_cm
    distance_px = distance_cm * pixels_per_cm
    
    return distance_px


def deg2pix_y(deg: float, screen_cfg: dict) -> float:
    """
    Convert vertical visual angle (degrees) to pixels.
    
    Uses the standard visual angle formula:
    distance_cm = viewing_distance_cm * tan(angle_rad)
    distance_px = distance_cm * (resolution_px / screen_height_cm)
    
    Parameters
    ----------
    deg : float
        Vertical visual angle in degrees.
    screen_cfg : dict
        Screen configuration dictionary with keys:
        - 'height_cm': Screen height in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        
    Returns
    -------
    float
        Vertical distance in pixels.
        
    Examples
    --------
    >>> screen = {
    ...     'height_cm': 33.62,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160]
    ... }
    >>> deg2pix_y(3.0, screen)
    207.2
    """
    viewing_distance_cm = screen_cfg['viewing_distance_cm']
    height_cm = screen_cfg['height_cm']
    height_px = screen_cfg['resolution_px'][1]
    
    # Convert degrees to radians
    angle_rad = np.deg2rad(deg)
    
    # Calculate distance in cm
    distance_cm = viewing_distance_cm * np.tan(angle_rad)
    
    # Convert to pixels
    pixels_per_cm = height_px / height_cm
    distance_px = distance_cm * pixels_per_cm
    
    return distance_px


def pix2deg_x(px: float, screen_cfg: dict) -> float:
    """
    Convert horizontal pixels to visual angle (degrees).
    
    Inverse of deg2pix_x using:
    distance_cm = distance_px * (screen_width_cm / resolution_px)
    angle_rad = atan(distance_cm / viewing_distance_cm)
    
    Parameters
    ----------
    px : float
        Horizontal distance in pixels.
    screen_cfg : dict
        Screen configuration dictionary with keys:
        - 'width_cm': Screen width in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        
    Returns
    -------
    float
        Horizontal visual angle in degrees.
        
    Examples
    --------
    >>> screen = {
    ...     'width_cm': 59.77,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160]
    ... }
    >>> pix2deg_x(570.5, screen)
    5.0
    """
    viewing_distance_cm = screen_cfg['viewing_distance_cm']
    width_cm = screen_cfg['width_cm']
    width_px = screen_cfg['resolution_px'][0]
    
    # Convert pixels to cm
    cm_per_pixel = width_cm / width_px
    distance_cm = px * cm_per_pixel
    
    # Calculate angle
    angle_rad = np.arctan(distance_cm / viewing_distance_cm)
    
    # Convert to degrees
    angle_deg = np.rad2deg(angle_rad)
    
    return angle_deg


def pix2deg_y(px: float, screen_cfg: dict) -> float:
    """
    Convert vertical pixels to visual angle (degrees).
    
    Inverse of deg2pix_y using:
    distance_cm = distance_px * (screen_height_cm / resolution_px)
    angle_rad = atan(distance_cm / viewing_distance_cm)
    
    Parameters
    ----------
    px : float
        Vertical distance in pixels.
    screen_cfg : dict
        Screen configuration dictionary with keys:
        - 'height_cm': Screen height in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        
    Returns
    -------
    float
        Vertical visual angle in degrees.
        
    Examples
    --------
    >>> screen = {
    ...     'height_cm': 33.62,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160]
    ... }
    >>> pix2deg_y(207.2, screen)
    3.0
    """
    viewing_distance_cm = screen_cfg['viewing_distance_cm']
    height_cm = screen_cfg['height_cm']
    height_px = screen_cfg['resolution_px'][1]
    
    # Convert pixels to cm
    cm_per_pixel = height_cm / height_px
    distance_cm = px * cm_per_pixel
    
    # Calculate angle
    angle_rad = np.arctan(distance_cm / viewing_distance_cm)
    
    # Convert to degrees
    angle_deg = np.rad2deg(angle_rad)
    
    return angle_deg


def apply_polygon_transform(
    geom_row: pd.Series,
    aperture_scale_factor: float,
    screen_cfg: dict
) -> Dict[str, float]:
    """
    Transform canonical polygon geometry to screen coordinates.
    
    Takes canonical polygon center coordinates (center of mass, convex hull,
    bounding box circle, inscribed circle), scales them by the aperture factor,
    translates them to screen coordinates, and computes both pixel and degree
    representations along with polar coordinates from screen center.
    
    Parameters
    ----------
    geom_row : pd.Series
        Row from polygon_geometry DataFrame containing canonical center
        coordinates with keys like:
        - 'center_mass_x_px', 'center_mass_y_px'
        - 'center_hull_x_px', 'center_hull_y_px'
        - 'center_bbc_x_px', 'center_bbc_y_px'
        - 'center_icc_x_px', 'center_icc_y_px'
    aperture_scale_factor : float
        Scaling factor to apply to canonical coordinates (e.g., 0.8 for 80% size).
    screen_cfg : dict
        Screen configuration dictionary with keys:
        - 'width_cm': Screen width in centimeters
        - 'height_cm': Screen height in centimeters
        - 'viewing_distance_cm': Viewing distance in centimeters
        - 'resolution_px': [width_px, height_px] screen resolution
        
    Returns
    -------
    dict
        Dictionary containing transformed coordinates for all centers:
        - 'center_screen_x_px', 'center_screen_y_px': Screen center in pixels
        - 'center_screen_x_deg', 'center_screen_y_deg': Screen center in degrees (0, 0)
        - For each center type (mass, hull, bbc, icc):
            - 'center_{type}_x_px', 'center_{type}_y_px': Pixel coordinates
            - 'center_{type}_x_deg', 'center_{type}_y_deg': Degree coordinates
            - 'dist_center_{type}_to_screen_deg': Euclidean distance from screen center
            - 'angle_center_{type}_to_screen_deg': Polar angle from screen center (0=right, 90=up)
            
    Examples
    --------
    >>> geom_row = pd.Series({
    ...     'center_mass_x_px': 100.0,
    ...     'center_mass_y_px': 50.0,
    ...     'center_hull_x_px': 105.0,
    ...     'center_hull_y_px': 48.0
    ... })
    >>> screen = {
    ...     'width_cm': 59.77,
    ...     'height_cm': 33.62,
    ...     'viewing_distance_cm': 70.0,
    ...     'resolution_px': [3840, 2160]
    ... }
    >>> result = apply_polygon_transform(geom_row, 1.0, screen)
    >>> print(result['center_mass_x_px'])
    2020.0
    """
    # Get screen dimensions
    width_px = screen_cfg['resolution_px'][0]
    height_px = screen_cfg['resolution_px'][1]
    
    # Calculate screen center
    screen_center_x_px = width_px / 2.0
    screen_center_y_px = height_px / 2.0
    
    # IMPORTANT: This function assumes canonical polygon centers in geom_row
    # are relative to polygon center (0,0), NOT absolute screen coordinates.
    # They will be scaled and translated to screen center coordinates below.
    
    # Initialize result dictionary with screen center
    result = {
        'center_screen_x_px': screen_center_x_px,
        'center_screen_y_px': screen_center_y_px,
        'center_screen_x_deg': 0.0,
        'center_screen_y_deg': 0.0
    }
    
    # Center types to process
    center_types = ['mass', 'hull', 'bbc', 'icc']
    
    for center_type in center_types:
        # Get canonical coordinates
        canonical_x_key = f'center_{center_type}_x_px'
        canonical_y_key = f'center_{center_type}_y_px'
        
        # Check if this center type exists in the geometry row
        if canonical_x_key not in geom_row or canonical_y_key not in geom_row:
            continue
        
        canonical_x = geom_row[canonical_x_key]
        canonical_y = geom_row[canonical_y_key]
        
        # Scale canonical coordinates
        scaled_x = canonical_x * aperture_scale_factor
        scaled_y = canonical_y * aperture_scale_factor
        
        # Translate to screen coordinates
        # Canonical coordinates are relative to their own center (0,0)
        # Screen coordinates place (0,0) at top-left, with center at (W/2, H/2)
        screen_x_px = screen_center_x_px + scaled_x
        screen_y_px = screen_center_y_px + scaled_y
        
        # Convert to degrees (relative to screen center)
        # For degrees, we use the offset from screen center
        screen_x_deg = pix2deg_x(scaled_x, screen_cfg)
        screen_y_deg = pix2deg_y(scaled_y, screen_cfg)
        
        # Calculate distance from screen center in degrees
        distance_deg = np.sqrt(screen_x_deg**2 + screen_y_deg**2)
        
        # Calculate polar angle from screen center
        # atan2(y, x) gives angle in radians, convert to degrees
        # 0° = right (positive x), 90° = up (positive y)
        angle_rad = np.arctan2(screen_y_deg, screen_x_deg)
        angle_deg = np.rad2deg(angle_rad)
        
        # Add to result dictionary
        result[f'center_{center_type}_x_px'] = screen_x_px
        result[f'center_{center_type}_y_px'] = screen_y_px
        result[f'center_{center_type}_x_deg'] = screen_x_deg
        result[f'center_{center_type}_y_deg'] = screen_y_deg
        result[f'dist_center_{center_type}_to_screen_deg'] = distance_deg
        result[f'angle_center_{center_type}_to_screen_deg'] = angle_deg
    
    return result
