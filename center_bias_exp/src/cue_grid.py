"""
Cue grid definitions for center_bias_exp.

This module defines the 9-point fixation cue grid used in the experiment.
The grid positions are at 25%, 50%, and 75% of screen width and height,
using EyeLink coordinate system (origin at top-left, x right, y down).

The experiment runner reads cue positions from the stimulus manifest CSV.
This module is provided for manifest generation and validation purposes.
"""

from typing import List, Dict, Any

# Screen dimensions (4K)
SCREEN_WIDTH_PX = 3840
SCREEN_HEIGHT_PX = 2160

# Grid percentages
GRID_X_PERCENTAGES = [0.25, 0.50, 0.75]
GRID_Y_PERCENTAGES = [0.25, 0.50, 0.75]

# Computed grid positions in pixels (EyeLink coordinates: top-left origin)
GRID_X_PX = [int(p * SCREEN_WIDTH_PX) for p in GRID_X_PERCENTAGES]   # [960, 1920, 2880]
GRID_Y_PX = [int(p * SCREEN_HEIGHT_PX) for p in GRID_Y_PERCENTAGES]  # [540, 1080, 1620]

# 9-point cue grid
# Grid positions are labeled as grid_RC where:
#   R = row (1=top, 2=middle, 3=bottom)
#   C = column (1=left, 2=center, 3=right)
CUE_GRID = [
    # Row 1 (top): y=540
    {"cue_pos_id": "grid_11", "cue_x_px": 960,  "cue_y_px": 540,  "row": 1, "col": 1, "label": "top-left"},
    {"cue_pos_id": "grid_12", "cue_x_px": 1920, "cue_y_px": 540,  "row": 1, "col": 2, "label": "top-center"},
    {"cue_pos_id": "grid_13", "cue_x_px": 2880, "cue_y_px": 540,  "row": 1, "col": 3, "label": "top-right"},
    
    # Row 2 (middle): y=1080
    {"cue_pos_id": "grid_21", "cue_x_px": 960,  "cue_y_px": 1080, "row": 2, "col": 1, "label": "middle-left"},
    {"cue_pos_id": "grid_22", "cue_x_px": 1920, "cue_y_px": 1080, "row": 2, "col": 2, "label": "center"},
    {"cue_pos_id": "grid_23", "cue_x_px": 2880, "cue_y_px": 1080, "row": 2, "col": 3, "label": "middle-right"},
    
    # Row 3 (bottom): y=1620
    {"cue_pos_id": "grid_31", "cue_x_px": 960,  "cue_y_px": 1620, "row": 3, "col": 1, "label": "bottom-left"},
    {"cue_pos_id": "grid_32", "cue_x_px": 1920, "cue_y_px": 1620, "row": 3, "col": 2, "label": "bottom-center"},
    {"cue_pos_id": "grid_33", "cue_x_px": 2880, "cue_y_px": 1620, "row": 3, "col": 3, "label": "bottom-right"},
]


def get_cue_positions() -> List[Dict[str, Any]]:
    """
    Get a copy of the 9-point cue grid positions.
    
    Returns
    -------
    list of dict
        List of 9 cue position dictionaries, each containing:
        - cue_pos_id: str - Grid position ID (e.g., 'grid_11', 'grid_22')
        - cue_x_px: int - X coordinate in pixels (EyeLink coords, top-left origin)
        - cue_y_px: int - Y coordinate in pixels (EyeLink coords, top-left origin)
        - row: int - Grid row (1=top, 2=middle, 3=bottom)
        - col: int - Grid column (1=left, 2=center, 3=right)
        - label: str - Human-readable label (e.g., 'top-left', 'center')
        
    Examples
    --------
    >>> cues = get_cue_positions()
    >>> len(cues)
    9
    >>> cues[0]
    {'cue_pos_id': 'grid_11', 'cue_x_px': 960, 'cue_y_px': 540, ...}
    >>> center_cue = [c for c in cues if c['label'] == 'center'][0]
    >>> center_cue['cue_x_px'], center_cue['cue_y_px']
    (1920, 1080)
    
    Notes
    -----
    Coordinates are in EyeLink convention (origin at top-left).
    The experiment runner will convert these to PsychoPy convention
    (origin at center) internally when drawing the fixation cue.
    """
    return [cue.copy() for cue in CUE_GRID]


def get_cue_by_id(cue_pos_id: str) -> Dict[str, Any]:
    """
    Get a specific cue position by its ID.
    
    Parameters
    ----------
    cue_pos_id : str
        Cue position ID (e.g., 'grid_11', 'grid_22')
        
    Returns
    -------
    dict
        Cue position dictionary with coordinates and metadata.
        
    Raises
    ------
    ValueError
        If cue_pos_id is not found in the grid.
        
    Examples
    --------
    >>> cue = get_cue_by_id('grid_22')
    >>> cue['cue_x_px'], cue['cue_y_px']
    (1920, 1080)
    >>> cue['label']
    'center'
    """
    for cue in CUE_GRID:
        if cue['cue_pos_id'] == cue_pos_id:
            return cue.copy()
    
    raise ValueError(
        f"Cue position ID '{cue_pos_id}' not found. "
        f"Valid IDs: {[c['cue_pos_id'] for c in CUE_GRID]}"
    )


def get_cue_by_position(row: int, col: int) -> Dict[str, Any]:
    """
    Get a cue position by its row and column indices.
    
    Parameters
    ----------
    row : int
        Row index (1=top, 2=middle, 3=bottom)
    col : int
        Column index (1=left, 2=center, 3=right)
        
    Returns
    -------
    dict
        Cue position dictionary with coordinates and metadata.
        
    Raises
    ------
    ValueError
        If row or col is out of range [1, 3].
        
    Examples
    --------
    >>> cue = get_cue_by_position(2, 2)  # Center position
    >>> cue['cue_pos_id']
    'grid_22'
    >>> cue['cue_x_px'], cue['cue_y_px']
    (1920, 1080)
    """
    if not (1 <= row <= 3):
        raise ValueError(f"Row must be 1, 2, or 3, got {row}")
    if not (1 <= col <= 3):
        raise ValueError(f"Column must be 1, 2, or 3, got {col}")
    
    for cue in CUE_GRID:
        if cue['row'] == row and cue['col'] == col:
            return cue.copy()
    
    # Should never reach here if validation above is correct
    raise ValueError(f"No cue found at row={row}, col={col}")


def validate_cue_position(cue_pos_id: str, cue_x_px: int, cue_y_px: int) -> bool:
    """
    Validate that cue coordinates match the expected grid position.
    
    Parameters
    ----------
    cue_pos_id : str
        Cue position ID from manifest.
    cue_x_px : int
        X coordinate in pixels from manifest.
    cue_y_px : int
        Y coordinate in pixels from manifest.
        
    Returns
    -------
    bool
        True if coordinates match the expected grid position, False otherwise.
        
    Examples
    --------
    >>> validate_cue_position('grid_22', 1920, 1080)
    True
    >>> validate_cue_position('grid_22', 1920, 540)
    False
    >>> validate_cue_position('invalid_id', 960, 540)
    False
    """
    try:
        expected_cue = get_cue_by_id(cue_pos_id)
        return (
            expected_cue['cue_x_px'] == cue_x_px and
            expected_cue['cue_y_px'] == cue_y_px
        )
    except ValueError:
        return False


if __name__ == "__main__":
    # Demo / validation output
    print("Cue Grid Definition (EyeLink coordinates)")
    print("=" * 60)
    print(f"Screen: {SCREEN_WIDTH_PX}×{SCREEN_HEIGHT_PX} pixels")
    print(f"Grid X: {GRID_X_PX} px (25%, 50%, 75% of width)")
    print(f"Grid Y: {GRID_Y_PX} px (25%, 50%, 75% of height)")
    print("\nAll 9 cue positions:")
    print("-" * 60)
    
    for cue in CUE_GRID:
        print(f"{cue['cue_pos_id']:<10} ({cue['row']},{cue['col']}) "
              f"x={cue['cue_x_px']:>4} y={cue['cue_y_px']:>4}  {cue['label']:<15}")
    
    print("\nValidation tests:")
    print("-" * 60)
    assert len(CUE_GRID) == 9, "Should have exactly 9 positions"
    assert get_cue_by_id('grid_22')['label'] == 'center', "Center should be grid_22"
    assert validate_cue_position('grid_22', 1920, 1080), "Center validation failed"
    assert not validate_cue_position('grid_22', 0, 0), "Should reject wrong coords"
    print("✓ All validation tests passed")
