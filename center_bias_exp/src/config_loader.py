"""
Configuration and manifest loading utilities for center_bias_exp.

This module provides functions to load and validate experiment configuration
and manifest files (stimulus, memory, polygon geometry).
"""

from pathlib import Path
from typing import Tuple

import pandas as pd
import yaml


def load_experiment_config(path: str) -> dict:
    """
    Load and validate experiment configuration from a YAML file.
    
    Reads the YAML configuration file and validates that it contains all
    required top-level sections for the experiment.
    
    Parameters
    ----------
    path : str
        Path to the YAML configuration file.
        
    Returns
    -------
    dict
        Nested dictionary containing all configuration sections.
        
    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If required configuration sections are missing.
    yaml.YAMLError
        If the YAML file is malformed.
        
    Examples
    --------
    >>> cfg = load_experiment_config('config/experiment_config.yaml')
    >>> print(cfg['screen']['width_px'])
    3840
    """
    config_path = Path(path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        raise ValueError(f"Configuration file is empty: {path}")
    
    # Validate required sections
    required_sections = [
        'experiment',
        'screen',
        'eyelink',
        'drift_gate',
        'aoi',
        'paths',
        'logging'
    ]
    
    missing_sections = [sec for sec in required_sections if sec not in config]
    
    if missing_sections:
        raise ValueError(
            f"Configuration file missing required sections: {', '.join(missing_sections)}. "
            f"Required sections are: {', '.join(required_sections)}"
        )
    
    return config


def load_manifests(cfg: dict) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and validate all experiment manifest files.
    
    Reads stimulus manifest, memory manifest, and polygon geometry CSV files
    from paths specified in the configuration, and validates that each contains
    the required columns for the experiment.
    
    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing a 'paths' section with keys:
        'stimulus_manifest', 'memory_manifest', 'polygon_geometry'.
        
    Returns
    -------
    tuple of (pd.DataFrame, pd.DataFrame, pd.DataFrame)
        - stimulus_manifest: Trial-level stimulus information
        - memory_manifest: Memory probe information
        - polygon_geometry: Polygon geometry with polygon_id as index
        
    Raises
    ------
    KeyError
        If the configuration does not contain required path keys.
    FileNotFoundError
        If any manifest file does not exist.
    ValueError
        If any manifest is missing required columns.
        
    Examples
    --------
    >>> cfg = load_experiment_config('config/experiment_config.yaml')
    >>> stim_df, mem_df, poly_df = load_manifests(cfg)
    >>> print(stim_df.columns)
    """
    # Extract paths from configuration
    # Support both flat keys (stimulus_manifest) and nested keys (manifests.stimulus)
    try:
        paths = cfg['paths']
        
        # Check for nested 'manifests' structure first, then fall back to flat keys
        if 'manifests' in paths:
            manifests = paths['manifests']
            stimulus_path = manifests.get('stimulus')
            memory_path = manifests.get('memory')
            polygon_path = manifests.get('geometry')
        else:
            stimulus_path = paths.get('stimulus_manifest')
            memory_path = paths.get('memory_manifest')
            polygon_path = paths.get('polygon_geometry')
        
        # Validate all paths are present
        if not stimulus_path:
            raise KeyError("stimulus manifest path")
        if not memory_path:
            raise KeyError("memory manifest path")
        if not polygon_path:
            raise KeyError("polygon geometry path")
            
    except KeyError as e:
        raise KeyError(
            f"Configuration missing required path key: {e}. "
            "Expected 'paths' section with either nested 'manifests' (stimulus, memory, geometry) "
            "or flat keys (stimulus_manifest, memory_manifest, polygon_geometry)."
        )
    
    # Load stimulus manifest
    stimulus_path = Path(stimulus_path)
    if not stimulus_path.exists():
        raise FileNotFoundError(f"Stimulus manifest not found: {stimulus_path}")
    
    stimulus_manifest = pd.read_csv(stimulus_path)
    
    # Validate stimulus manifest columns
    # Note: participant_id is set at runtime, not in the manifest
    required_stimulus_cols = [
        'part',
        'mini_block',
        'trial_in_block',
        'trial_uid',
        'trial_type',
        'polygon_id',
        'polygon_case',
        'polygon_json_path',
        'cue_pos_id',
        'cue_x_px',
        'cue_y_px',
        'stimulus_duration_s',
        'iti_s',
        'max_drift_time_s',
        'drift_retry_limit'
    ]
    
    missing_stimulus_cols = [
        col for col in required_stimulus_cols 
        if col not in stimulus_manifest.columns
    ]
    
    if missing_stimulus_cols:
        raise ValueError(
            f"Stimulus manifest missing required columns: {', '.join(missing_stimulus_cols)}. "
            f"Found columns: {', '.join(stimulus_manifest.columns.tolist())}"
        )
    
    # Load memory manifest
    memory_path = Path(memory_path)
    if not memory_path.exists():
        raise FileNotFoundError(f"Memory manifest not found: {memory_path}")
    
    memory_manifest = pd.read_csv(memory_path)
    
    # Validate memory manifest columns
    # Note: participant_id is set at runtime, not in the manifest
    required_memory_cols = [
        'part',
        'mini_block',
        'probe_image_id',
        'probe_image_path',
        'probe_duration_s'
    ]
    
    missing_memory_cols = [
        col for col in required_memory_cols 
        if col not in memory_manifest.columns
    ]
    
    if missing_memory_cols:
        raise ValueError(
            f"Memory manifest missing required columns: {', '.join(missing_memory_cols)}. "
            f"Found columns: {', '.join(memory_manifest.columns.tolist())}"
        )
    
    # Load polygon geometry
    polygon_path = Path(polygon_path)
    if not polygon_path.exists():
        raise FileNotFoundError(f"Polygon geometry manifest not found: {polygon_path}")
    
    polygon_geometry = pd.read_csv(polygon_path)
    
    # Validate polygon geometry columns
    if 'polygon_id' not in polygon_geometry.columns:
        raise ValueError(
            f"Polygon geometry missing required column 'polygon_id'. "
            f"Found columns: {', '.join(polygon_geometry.columns.tolist())}"
        )
    
    # Check for at least one center column (e.g., center_mass_x_px)
    center_cols = [col for col in polygon_geometry.columns if 'center' in col.lower()]
    
    if not center_cols:
        raise ValueError(
            f"Polygon geometry missing center columns (e.g., 'center_mass_x_px'). "
            f"Found columns: {', '.join(polygon_geometry.columns.tolist())}"
        )
    
    # Set polygon_id as index
    polygon_geometry = polygon_geometry.set_index('polygon_id')
    
    return stimulus_manifest, memory_manifest, polygon_geometry
