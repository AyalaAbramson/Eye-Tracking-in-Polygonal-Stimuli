"""
Logging utilities for center_bias_exp.

This module provides functions for creating session directory structures,
initializing CSV loggers, and writing trial, block, and memory data to CSV files.
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any, Optional


def init_session_paths(cfg: dict, participant_id: str, part: str) -> Dict[str, Path]:
    """
    Create session directory structure and return paths.
    
    Creates a timestamped session directory within the participant/part folder
    structure, with subdirectories for different types of log files.
    
    Directory structure created:
    data/raw/participant_<ID>/part_<A|B>/session_<YYYYmmdd_HHMMSS>/
        edf/
        logs_trial/
        logs_block/
        logs_session/
        logs_memory/
    
    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing a 'paths' section with
        'data_root' key (defaults to 'data/raw' if not specified).
    participant_id : str
        Participant identifier (e.g., 'P01').
    part : str
        Experiment part identifier (e.g., 'A' or 'B').
        
    Returns
    -------
    dict
        Dictionary containing absolute Path objects for:
        - 'session_root': Main session directory
        - 'edf': EyeLink data files directory
        - 'logs_trial': Trial-level logs directory
        - 'logs_block': Block-level logs directory
        - 'logs_session': Session-level logs directory
        - 'logs_memory': Memory probe logs directory
        
    Examples
    --------
    >>> cfg = {'paths': {'data_root': 'data/raw'}}
    >>> paths = init_session_paths(cfg, 'P01', 'A')
    >>> print(paths['session_root'])
    /path/to/data/raw/participant_P01/part_A/session_20260114_153045
    """
    # Get data root from config, with default fallback
    data_root = cfg.get('paths', {}).get('data_root', 'data/raw')
    data_root_path = Path(data_root)
    
    # Generate timestamp for session
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Build session directory path
    session_root = (
        data_root_path 
        / f'participant_{participant_id}' 
        / f'part_{part}' 
        / f'session_{timestamp}'
    )
    
    # Create subdirectories
    subdirs = {
        'session_root': session_root,
        'edf': session_root / 'edf',
        'logs_trial': session_root / 'logs_trial',
        'logs_block': session_root / 'logs_block',
        'logs_session': session_root / 'logs_session',
        'logs_memory': session_root / 'logs_memory'
    }
    
    # Create all directories
    for path in subdirs.values():
        path.mkdir(parents=True, exist_ok=True)
    
    # Convert to absolute paths
    subdirs = {key: path.resolve() for key, path in subdirs.items()}
    
    return subdirs


def write_session_metadata(path: str, metadata: dict) -> None:
    """
    Write session metadata to a JSON file.
    
    Parameters
    ----------
    path : str
        Path where the JSON file should be written.
    metadata : dict
        Dictionary containing session metadata to serialize.
        
    Examples
    --------
    >>> metadata = {
    ...     'participant_id': 'P01',
    ...     'part': 'A',
    ...     'start_time': '2026-01-14 15:30:45',
    ...     'screen_width_px': 3840
    ... }
    >>> write_session_metadata('data/session_metadata.json', metadata)
    """
    path_obj = Path(path)
    
    with open(path_obj, 'w') as f:
        json.dump(metadata, f, indent=2)


def init_trial_logger(csv_path: str) -> Tuple[io.TextIOBase, csv.DictWriter]:
    """
    Initialize CSV logger for trial-level data.
    
    Opens a CSV file and creates a DictWriter with headers for trial data.
    The header row is written immediately.
    
    Parameters
    ----------
    csv_path : str
        Path where the CSV file should be created.
        
    Returns
    -------
    tuple of (file_handle, csv.DictWriter)
        - file_handle: Open file object (caller must close)
        - writer: DictWriter instance ready to write rows
        
    Examples
    --------
    >>> f, writer = init_trial_logger('data/trials.csv')
    >>> writer.writerow({'trial_uid': 'T001', 'response_time_ms': 450})
    >>> f.close()
    """
    # Define trial-level columns
    fieldnames = [
        'timestamp',
        'participant_id',
        'part',
        'mini_block',
        'trial_in_block',
        'trial_uid',
        'trial_type',
        'polygon_id',
        'polygon_case',
        'polygon_json_path',
        'image_id',
        'image_path',
        'category',
        'bias_level',
        'aperture_scale_factor',
        'cue_pos_id',
        'cue_x_px',
        'cue_y_px',
        'cue_x_deg',
        'cue_y_deg',
        'stimulus_duration_s',
        'iti_s',
        'max_drift_time_s',
        'drift_retry_limit',
        'aoi_radius_deg',
        'aoi_radius_px',
        'validation_rms_before_trial',
        'validation_max_err_before_trial',
        'center_screen_x_px',
        'center_screen_y_px',
        'center_screen_x_deg',
        'center_screen_y_deg',
        'center_mass_x_px',
        'center_mass_y_px',
        'center_mass_x_deg',
        'center_mass_y_deg',
        'dist_center_mass_to_screen_deg',
        'angle_center_mass_to_screen_deg',
        'center_hull_x_px',
        'center_hull_y_px',
        'center_hull_x_deg',
        'center_hull_y_deg',
        'dist_center_hull_to_screen_deg',
        'angle_center_hull_to_screen_deg',
        'center_bbc_x_px',
        'center_bbc_y_px',
        'center_bbc_x_deg',
        'center_bbc_y_deg',
        'dist_center_bbc_to_screen_deg',
        'angle_center_bbc_to_screen_deg',
        'center_icc_x_px',
        'center_icc_y_px',
        'center_icc_x_deg',
        'center_icc_y_deg',
        'dist_center_icc_to_screen_deg',
        'angle_center_icc_to_screen_deg',
        'fixation_achieved',
        'fixation_attempts',
        'fixation_total_time_s',
        'ts_trial_start',
        'ts_recording_start',
        'ts_cue_onset',
        'ts_fixation_end',
        'ts_stim_onset',
        'ts_stim_offset',
        'ts_iti_onset',
        'ts_iti_offset',
        'ts_recording_stop',
        'ts_trial_end',
        'trial_start_time',
        'trial_end_time',
        'trial_duration_s',
        'aborted',
        'user_abort'
    ]
    
    # Open file and create writer
    file_handle = open(csv_path, 'w', newline='')
    writer = csv.DictWriter(file_handle, fieldnames=fieldnames, extrasaction='ignore')
    
    # Write header
    writer.writeheader()
    
    return file_handle, writer


def init_block_logger(csv_path: str) -> Tuple[io.TextIOBase, csv.DictWriter]:
    """
    Initialize CSV logger for block-level data.
    
    Opens a CSV file and creates a DictWriter with headers for block data.
    The header row is written immediately.
    
    Parameters
    ----------
    csv_path : str
        Path where the CSV file should be created.
        
    Returns
    -------
    tuple of (file_handle, csv.DictWriter)
        - file_handle: Open file object (caller must close)
        - writer: DictWriter instance ready to write rows
        
    Examples
    --------
    >>> f, writer = init_block_logger('data/blocks.csv')
    >>> writer.writerow({'mini_block': 1, 'n_trials': 39})
    >>> f.close()
    """
    # Define block-level columns
    fieldnames = [
        'timestamp',
        'participant_id',
        'part',
        'mini_block',
        'calibration_start_time',
        'calibration_end_time',
        'calibration_result',
        'calibration_error_deg',
        'validation_result',
        'validation_error_avg_deg',
        'validation_error_max_deg',
        'n_trials',
        'n_trials_completed',
        'n_drift_failures',
        'n_recalibrations_within_block',
        'memory_response',
        'memory_correct',
        'memory_rt_ms',
        'break_duration_actual_s',
        'block_start_time',
        'block_end_time',
        'block_duration_s'
    ]
    
    # Open file and create writer
    file_handle = open(csv_path, 'w', newline='')
    writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
    
    # Write header
    writer.writeheader()
    
    return file_handle, writer


def init_memory_logger(csv_path: str) -> Tuple[io.TextIOBase, csv.DictWriter]:
    """
    Initialize CSV logger for memory probe data.
    
    Opens a CSV file and creates a DictWriter with headers for memory probe data.
    The header row is written immediately.
    
    Parameters
    ----------
    csv_path : str
        Path where the CSV file should be created.
        
    Returns
    -------
    tuple of (file_handle, csv.DictWriter)
        - file_handle: Open file object (caller must close)
        - writer: DictWriter instance ready to write rows
        
    Examples
    --------
    >>> f, writer = init_memory_logger('data/memory.csv')
    >>> writer.writerow({'probe_image_id': 'img001', 'response': 'old'})
    >>> f.close()
    """
    # Define memory probe columns
    fieldnames = [
        'timestamp',
        'participant_id',
        'part',
        'mini_block',
        'probe_image_id',
        'probe_image_path',
        'probe_duration_s',
        'is_old',
        'response',
        'response_time_ms',
        'correct',
        'probe_start_time',
        'probe_end_time'
    ]
    
    # Open file and create writer
    file_handle = open(csv_path, 'w', newline='')
    writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
    
    # Write header
    writer.writeheader()
    
    return file_handle, writer


def log_trial_row(
    writer: csv.DictWriter,
    file_handle: io.TextIOBase,
    row_data: Dict[str, Any],
    flush: bool = True
) -> None:
    """
    Write a single trial data row to CSV.
    
    Parameters
    ----------
    writer : csv.DictWriter
        DictWriter instance created by init_trial_logger.
    file_handle : io.TextIOBase
        File handle to flush if requested.
    row_data : dict
        Dictionary containing trial data to write. Keys should match
        the fieldnames defined in init_trial_logger.
    flush : bool, optional
        If True, flush the file buffer after writing (default: True).
        
    Examples
    --------
    >>> f, writer = init_trial_logger('data/trials.csv')
    >>> data = {'trial_uid': 'T001', 'participant_id': 'P01'}
    >>> log_trial_row(writer, f, data)
    >>> f.close()
    """
    writer.writerow(row_data)
    if flush:
        file_handle.flush()


def log_block_row(
    writer: csv.DictWriter,
    file_handle: io.TextIOBase,
    row_data: Dict[str, Any],
    flush: bool = True
) -> None:
    """
    Write a single block data row to CSV.
    
    Parameters
    ----------
    writer : csv.DictWriter
        DictWriter instance created by init_block_logger.
    file_handle : io.TextIOBase
        File handle to flush if requested.
    row_data : dict
        Dictionary containing block data to write. Keys should match
        the fieldnames defined in init_block_logger.
    flush : bool, optional
        If True, flush the file buffer after writing (default: True).
        
    Examples
    --------
    >>> f, writer = init_block_logger('data/blocks.csv')
    >>> data = {'mini_block': 1, 'participant_id': 'P01'}
    >>> log_block_row(writer, f, data)
    >>> f.close()
    """
    writer.writerow(row_data)
    if flush:
        file_handle.flush()


def log_memory_row(
    writer: csv.DictWriter,
    file_handle: io.TextIOBase,
    row_data: Dict[str, Any],
    flush: bool = True
) -> None:
    """
    Write a single memory probe data row to CSV.
    
    Parameters
    ----------
    writer : csv.DictWriter
        DictWriter instance created by init_memory_logger.
    file_handle : io.TextIOBase
        File handle to flush if requested.
    row_data : dict
        Dictionary containing memory probe data to write. Keys should match
        the fieldnames defined in init_memory_logger.
    flush : bool, optional
        If True, flush the file buffer after writing (default: True).
        
    Examples
    --------
    >>> f, writer = init_memory_logger('data/memory.csv')
    >>> data = {'probe_image_id': 'img001', 'response': 'old'}
    >>> log_memory_row(writer, f, data)
    >>> f.close()
    """
    writer.writerow(row_data)
    if flush:
        file_handle.flush()
