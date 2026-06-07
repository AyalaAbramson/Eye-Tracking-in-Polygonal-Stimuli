"""
Main entry point for Experiment 2 (center bias, EyeLink + PsychoPy).

This script runs the complete experiment: 2 parts (A/B) × 9 mini-blocks × 39 trials.
Each block includes calibration/validation, trials with drift correction,
memory probe, and timed break. Logs comprehensive data to CSV and EDF files.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from psychopy import core, event, visual

# Import helper modules
from config_loader import load_experiment_config, load_manifests
from geometry_utils import apply_polygon_transform, pix2deg_x, pix2deg_y, deg2pix_x, deg2pix_y
from psychopy_utils import (
    create_monitor_and_window,
    draw_instructions,
    draw_fixation_cue,
    prepare_polygon_shape,
    prepare_masked_image,
)
from eyetracker_utils import (
    connect_eyelink,
    setup_edf,
    configure_tracker,
    run_calibration_and_validation,
    start_recording,
    stop_recording,
    drift_correction_with_auto_accept,
)
from eye_dominance_test import run_eye_dominance_test
from logging_utils import (
    init_session_paths,
    write_session_metadata,
    init_trial_logger,
    init_block_logger,
    init_memory_logger,
    log_trial_row,
    log_block_row,
    log_memory_row,
)

try:
    import pylink
except ImportError:
    print("Warning: pylink not available. EyeLink functionality will be limited.")
    pylink = None

# Import EyeLink graphics environment from SR Research library (experiement_base)
EyeLinkCoreGraphicsPsychoPy = None
if pylink is not None:
    try:
        from experiement_base.EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
        print("EyeLinkCoreGraphicsPsychoPy loaded from experiement_base")
    except ImportError as e:
        print(f"Warning: Could not import EyeLinkCoreGraphicsPsychoPy: {e}")
        EyeLinkCoreGraphicsPsychoPy = None

# Also import helper functions from the base module
try:
    from experiement_base import base as eyelink_base
    print("EyeLink base utilities loaded")
except ImportError as e:
    print(f"Warning: Could not import eyelink_base: {e}")
    eyelink_base = None


def run_single_trial(
    trial_row: pd.Series,
    geom_df: pd.DataFrame,
    tracker: Any,
    graphics_env: Any,
    win: visual.Window,
    exp_clock: core.Clock,
    cfg: dict,
    screen_cfg: dict,
    participant_id: str,
    part: str,
    mini_block: int,
    last_calib_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run a single trial: drift correction, stimulus presentation, logging.
    
    Parameters
    ----------
    trial_row : pd.Series
        Row from stimulus manifest containing trial parameters.
    geom_df : pd.DataFrame
        Polygon geometry data indexed by polygon_id.
    tracker : pylink.EyeLink
        Connected EyeLink tracker.
    graphics_env : EyeLinkCoreGraphicsPsychoPy
        Graphics environment for calibration (if recalibration needed).
    win : visual.Window
        PsychoPy window.
    exp_clock : core.Clock
        Experiment clock for timestamps.
    cfg : dict
        Full experiment configuration.
    screen_cfg : dict
        Screen configuration subset.
    participant_id : str
        Participant ID.
    part : str
        Part identifier (A or B).
    mini_block : int
        Current mini-block number.
    last_calib_info : dict
        Last calibration info for logging validation metrics.
        
    Returns
    -------
    dict
        Trial result containing all logged fields and status flags,
        including 'recalibrated' flag if recalibration occurred.
    """
    # Initialize trial clock
    trial_clock = core.Clock()
    trial_clock.reset()
    
    # Extract trial parameters
    trial_uid = trial_row['trial_uid']
    mini_block = trial_row['mini_block']
    trial_in_block = trial_row['trial_in_block']
    trial_type = trial_row['trial_type']
    polygon_id = trial_row['polygon_id']
    polygon_case = trial_row['polygon_case']
    polygon_json_path = trial_row['polygon_json_path']
    cue_pos_id = trial_row['cue_pos_id']
    cue_x_px = trial_row['cue_x_px']
    cue_y_px = trial_row['cue_y_px']
    stimulus_duration_s = trial_row['stimulus_duration_s']
    iti_s = trial_row['iti_s']
    max_drift_time_s = trial_row.get('max_drift_time_s', 10.0)
    drift_retry_limit = trial_row.get('drift_retry_limit', 1)
    
    # Get aperture scale factor (default 1.0)
    aperture_scale_factor = trial_row.get('aperture_scale_factor', 1.0)
    
    # Get optional image-related fields
    image_id = trial_row.get('image_id', None)
    image_path = trial_row.get('image_path', None)
    category = trial_row.get('category', None)
    bias_level = trial_row.get('bias_level', None)
    
    # Get polygon geometry and transform to screen coordinates
    if polygon_id in geom_df.index:
        geom_row = geom_df.loc[polygon_id]
        geom_info = apply_polygon_transform(geom_row, aperture_scale_factor, screen_cfg)
    else:
        # No geometry for empty polygon trials
        geom_info = {}
    
    # Convert cue position to degrees
    cue_x_deg = pix2deg_x(cue_x_px, screen_cfg)
    cue_y_deg = pix2deg_y(cue_y_px, screen_cfg)
    
    # Get AOI radius in both units
    aoi_radius_deg = cfg.get('aoi', {}).get('radius_deg', 2.0)
    aoi_radius_px = deg2pix_x(aoi_radius_deg, screen_cfg)
    
    # Get validation metrics from last calibration
    validation_rms_before_trial = last_calib_info.get('validation_rms_best')
    validation_max_err_before_trial = last_calib_info.get('validation_max_err_best')
    
    # Start trial timestamp
    ts_trial_start = exp_clock.getTime()
    
    # Send trial messages to EDF BEFORE starting recording
    tracker.sendMessage(f"TRIALID {trial_uid}")
    tracker.sendMessage(
        f"TRIAL_START mini_block={mini_block} trial_in_block={trial_in_block} "
        f"trial_type={trial_type} polygon_id={polygon_id}"
    )

    # Send trial variables
    tracker.sendMessage(f"!V TRIAL_VAR trial_uid {trial_uid}")
    tracker.sendMessage(f"!V TRIAL_VAR mini_block {mini_block}")
    tracker.sendMessage(f"!V TRIAL_VAR trial_in_block {trial_in_block}")
    tracker.sendMessage(f"!V TRIAL_VAR trial_type {trial_type}")
    tracker.sendMessage(f"!V TRIAL_VAR polygon_id {polygon_id}")
    tracker.sendMessage(f"!V TRIAL_VAR polygon_case {polygon_case}")
    tracker.sendMessage(f"!V TRIAL_VAR cue_pos_id {cue_pos_id}")
    tracker.sendMessage(f"!V TRIAL_VAR cue_x_px {cue_x_px:.1f}")
    tracker.sendMessage(f"!V TRIAL_VAR cue_y_px {cue_y_px:.1f}")
    # Additional trial variables for image trials
    if 'image_id' in trial_row and pd.notna(trial_row.get('image_id')):
        tracker.sendMessage(f"!V TRIAL_VAR image_id {trial_row['image_id']}")
    if 'category' in trial_row and pd.notna(trial_row.get('category')):
        tracker.sendMessage(f"!V TRIAL_VAR category {trial_row['category']}")
    if 'bias_level' in trial_row and pd.notna(trial_row.get('bias_level')):
        tracker.sendMessage(f"!V TRIAL_VAR bias_level {trial_row['bias_level']}")

    # Define AOIs (if geometry exists)
    if geom_info:
        aoi_id = 1
        for center_type in ['mass', 'hull', 'bbc', 'icc']:
            x_key = f'center_{center_type}_x_px'
            y_key = f'center_{center_type}_y_px'
            if x_key in geom_info and y_key in geom_info:
                x_px = geom_info[x_key]
                y_px = geom_info[y_key]
                tracker.sendMessage(
                    f"!V IAREA CIRCLE {aoi_id} center_{center_type} "
                    f"{x_px:.1f} {y_px:.1f} {aoi_radius_px:.1f}"
                )
                aoi_id += 1

        # Screen center AOI
        screen_center_x = geom_info.get('center_screen_x_px', screen_cfg['resolution_px'][0] / 2)
        screen_center_y = geom_info.get('center_screen_y_px', screen_cfg['resolution_px'][1] / 2)
        tracker.sendMessage(
            f"!V IAREA CIRCLE {aoi_id} center_screen "
            f"{screen_center_x:.1f} {screen_center_y:.1f} {aoi_radius_px:.1f}"
        )

    # =========================================================================
    # PHASE 1: DRIFT CORRECTION (at cue location)
    # Standard eye-tracking practice: drift correct BEFORE each trial
    # =========================================================================
    # Convert cue coordinates from EyeLink (top-left origin) to PsychoPy (center origin)
    W, H = screen_cfg['resolution_px']
    cue_x_psychopy = cue_x_px - W/2
    cue_y_psychopy = (H/2) - cue_y_px  # Flip y-axis

    # Display drift correction target BEFORE drift correction
    draw_fixation_cue(win, cue_x_psychopy, cue_y_psychopy, size_px=20.0)

    # Start recording briefly to measure drift (needed for auto-accept check)
    ts_recording_start = start_recording(tracker, exp_clock)

    fixation_start_time = exp_clock.getTime()
    fixation_achieved = False
    fixation_attempts = 1

    # Get auto-accept threshold from config (default 1.0 degree)
    auto_accept_threshold = cfg.get('drift_gate', {}).get('auto_accept_threshold_deg', 1.0)

    # Perform drift correction with auto-accept
    fixation_success, drift_error_deg, _ = drift_correction_with_auto_accept(
        tracker, cue_x_px, cue_y_px, exp_clock,
        screen_cfg['resolution_px'][0],
        screen_cfg['viewing_distance_cm'],
        screen_cfg['width_cm'],
        auto_accept_threshold_deg=auto_accept_threshold
    )

    if fixation_success:
        fixation_achieved = True
        tracker.sendMessage(f"DRIFT_CORRECT_OK error_deg={drift_error_deg:.3f}")
    else:
        # Drift correction failed - participant may need recalibration
        tracker.sendMessage(f"DRIFT_CORRECT_FAILED")
        fixation_achieved = False

    fixation_total_time_s = exp_clock.getTime() - fixation_start_time

    # =========================================================================
    # PHASE 2: CUE FIXATION
    # Display cue and wait for fixation confirmation
    # =========================================================================
    # Restart recording for trial (drift correction may have stopped it)
    stop_recording(tracker, exp_clock)
    ts_recording_start = start_recording(tracker, exp_clock)

    # Display fixation cue again
    draw_fixation_cue(win, cue_x_psychopy, cue_y_psychopy, size_px=20.0)
    ts_cue_onset = exp_clock.getTime()
    tracker.sendMessage(f"CUE_ON {ts_cue_onset:.3f} pos=({cue_x_px:.1f},{cue_y_px:.1f})")

    # Brief cue display (100ms) - minimal temporal marker
    # Drift correction already verified fixation, so no long delay needed
    core.wait(0.1)

    ts_cue_offset = exp_clock.getTime()
    tracker.sendMessage(f"CUE_OFF {ts_cue_offset:.3f}")

    # If drift correction failed, return with abort flag
    if not fixation_achieved:
        stop_recording(tracker, exp_clock)
        
        trial_data = {
            'timestamp': datetime.now().isoformat(),
            'participant_id': participant_id,
            'part': part,
            'mini_block': mini_block,
            'trial_in_block': trial_in_block,
            'trial_uid': trial_uid,
            'trial_type': trial_type,
            'polygon_id': polygon_id,
            'polygon_case': polygon_case,
            'polygon_json_path': polygon_json_path,
            'aperture_scale_factor': aperture_scale_factor,
            'cue_pos_id': cue_pos_id,
            'cue_x_px': cue_x_px,
            'cue_y_px': cue_y_px,
            'cue_x_deg': cue_x_deg,
            'cue_y_deg': cue_y_deg,
            'stimulus_duration_s': stimulus_duration_s,
            'iti_s': iti_s,
            'max_drift_time_s': max_drift_time_s,
            'drift_retry_limit': drift_retry_limit,
            'aoi_radius_deg': aoi_radius_deg,
            'aoi_radius_px': aoi_radius_px,
            'validation_rms_before_trial': validation_rms_before_trial,
            'validation_max_err_before_trial': validation_max_err_before_trial,
            'fixation_achieved': False,
            'fixation_attempts': fixation_attempts,
            'fixation_total_time_s': fixation_total_time_s,
            'trial_start_time': ts_trial_start,
            'trial_end_time': exp_clock.getTime(),
            'trial_duration_s': exp_clock.getTime() - ts_trial_start,
            'aborted': True,
            'user_abort': True,
        }
        trial_data.update(geom_info)
        return trial_data
    
    # Stimulus presentation
    # Prepare polygon shape if applicable
    polygon_shape = None
    stimulus_prepared = False
    
    try:
        if trial_type in ("image", "polygon", "empty") and polygon_json_path:
            polygon_shape = prepare_polygon_shape(
                win,
                polygon_json_path,
                aperture_scale_factor=aperture_scale_factor,
            )
        stimulus_prepared = True
    except Exception as e:
        print(f"Warning: Could not prepare polygon shape: {e}")
        tracker.sendMessage(f"STIMULUS_LOAD_ERROR polygon_shape {str(e)[:50]}")
        stimulus_prepared = False
    
    # Display stimulus based on trial type
    stimulus_displayed = False
    
    if trial_type == "image" and stimulus_prepared and polygon_shape is not None:
        # Image trial: display masked image
        if image_path and pd.notna(image_path):
            try:
                # Extract shape name from polygon_json_path for margin optimization
                from pathlib import Path
                shape_name = Path(polygon_json_path).stem if polygon_json_path else ""

                image_stim = prepare_masked_image(
                    win,
                    image_path,
                    polygon_shape,
                    shape_name=shape_name,
                    position=(0, 0),
                )
                
                # Draw masked image
                image_stim.draw()
                
                # Optionally draw polygon outline on top (white outline)
                # Uncomment next line if you want to see the polygon border
                # polygon_shape.draw()
                
                win.flip()
                ts_stimulus_onset = exp_clock.getTime()
                tracker.sendMessage(f"STIM_ON {ts_stimulus_onset:.3f}")
                stimulus_displayed = True
                
            except Exception as e:
                print(f"Warning: Could not load/display image {image_path}: {e}")
                tracker.sendMessage(f"STIMULUS_LOAD_ERROR image {str(e)[:50]}")
        else:
            print(f"Warning: Image trial but no image_path provided")
            tracker.sendMessage("STIMULUS_LOAD_ERROR missing_image_path")
    
    elif trial_type == "empty" and stimulus_prepared and polygon_shape is not None:
        # Empty trial: display polygon outline only
        try:
            polygon_shape.draw()
            win.flip()
            ts_stimulus_onset = exp_clock.getTime()
            tracker.sendMessage(f"STIM_ON {ts_stimulus_onset:.3f}")
            stimulus_displayed = True
            
        except Exception as e:
            print(f"Warning: Could not display polygon: {e}")
            tracker.sendMessage(f"STIMULUS_LOAD_ERROR polygon_display {str(e)[:50]}")
    
    elif trial_type == "polygon" and stimulus_prepared and polygon_shape is not None:
        # Polygon-only trial: display polygon outline
        try:
            polygon_shape.draw()
            win.flip()
            ts_stimulus_onset = exp_clock.getTime()
            tracker.sendMessage(f"STIM_ON {ts_stimulus_onset:.3f}")
            stimulus_displayed = True
            
        except Exception as e:
            print(f"Warning: Could not display polygon: {e}")
            tracker.sendMessage(f"STIMULUS_LOAD_ERROR polygon_display {str(e)[:50]}")
    
    # Fallback: show blank screen if stimulus could not be displayed
    if not stimulus_displayed:
        print(f"Warning: Falling back to blank screen for trial {trial_uid}")
        tracker.sendMessage("STIMULUS_FALLBACK_BLANK stimulus_load_failed")
        win.flip()
        ts_stimulus_onset = exp_clock.getTime()
        tracker.sendMessage(f"STIM_ON {ts_stimulus_onset:.3f}")
    
    # Wait for stimulus duration (with ESC check)
    stimulus_start = exp_clock.getTime()
    while (exp_clock.getTime() - stimulus_start) < stimulus_duration_s:
        keys = event.getKeys(['escape'])
        if 'escape' in keys:
            tracker.sendMessage("USER_ABORT_ESC")
            stop_recording(tracker, exp_clock)
            return {
                'timestamp': datetime.now().isoformat(),
                'participant_id': participant_id,
                'part': part,
                'mini_block': mini_block,
                'trial_in_block': trial_in_block,
                'trial_uid': trial_uid,
                'aborted': True,
                'user_abort': True
            }
        core.wait(0.01)  # Small sleep to prevent CPU spinning
    
    # Clear screen (gray background for ITI)
    win.flip()
    ts_stimulus_offset = exp_clock.getTime()
    ts_iti_onset = ts_stimulus_offset
    tracker.sendMessage(f"STIM_OFF {ts_stimulus_offset:.3f}")
    tracker.sendMessage(f"ITI_ON {ts_iti_onset:.3f}")
    
    # ITI (with ESC check)
    iti_start = exp_clock.getTime()
    while (exp_clock.getTime() - iti_start) < iti_s:
        keys = event.getKeys(['escape'])
        if 'escape' in keys:
            tracker.sendMessage("USER_ABORT_ESC")
            stop_recording(tracker, exp_clock)
            return {
                'timestamp': datetime.now().isoformat(),
                'participant_id': participant_id,
                'part': part,
                'mini_block': mini_block,
                'trial_in_block': trial_in_block,
                'trial_uid': trial_uid,
                'aborted': True,
                'user_abort': True
            }
        core.wait(0.01)
    ts_iti_offset = exp_clock.getTime()
    tracker.sendMessage(f"ITI_OFF {ts_iti_offset:.3f}")
    
    # End trial
    ts_trial_end = exp_clock.getTime()
    tracker.sendMessage(f"TRIAL_END {ts_trial_end:.3f}")
    
    # Stop recording
    stop_recording(tracker, exp_clock)
    
    # Send trial result
    tracker.sendMessage("TRIAL_RESULT OK")
    
    # Compile trial data
    trial_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': participant_id,
        'part': part,
        'mini_block': mini_block,
        'trial_in_block': trial_in_block,
        'trial_uid': trial_uid,
        'trial_type': trial_type,
        'polygon_id': polygon_id,
        'polygon_case': polygon_case,
        'polygon_json_path': polygon_json_path,
        'image_id': image_id,
        'image_path': image_path,
        'category': category,
        'bias_level': bias_level,
        'aperture_scale_factor': aperture_scale_factor,
        'cue_pos_id': cue_pos_id,
        'cue_x_px': cue_x_px,
        'cue_y_px': cue_y_px,
        'cue_x_deg': cue_x_deg,
        'cue_y_deg': cue_y_deg,
        'stimulus_duration_s': stimulus_duration_s,
        'iti_s': iti_s,
        'max_drift_time_s': max_drift_time_s,
        'drift_retry_limit': drift_retry_limit,
        'aoi_radius_deg': aoi_radius_deg,
        'aoi_radius_px': aoi_radius_px,
        'validation_rms_before_trial': validation_rms_before_trial,
        'validation_max_err_before_trial': validation_max_err_before_trial,
        'fixation_achieved': fixation_achieved,
        'fixation_attempts': fixation_attempts,
        'fixation_total_time_s': fixation_total_time_s,
        'ts_trial_start': ts_trial_start,
        'ts_recording_start': ts_recording_start,
        'ts_cue_onset': ts_cue_onset,
        'ts_fixation_end': exp_clock.getTime(),  # When fixation gating ended
        'ts_stim_onset': ts_stimulus_onset,
        'ts_stim_offset': ts_stimulus_offset,
        'ts_iti_onset': ts_iti_onset,
        'ts_iti_offset': ts_iti_offset,
        'ts_recording_stop': exp_clock.getTime(),  # Will be updated by stop_recording
        'ts_trial_end': ts_trial_end,
        'trial_start_time': ts_trial_start,
        'trial_end_time': ts_trial_end,
        'trial_duration_s': ts_trial_end - ts_trial_start,
        'aborted': False
    }
    
    # Add geometry info
    trial_data.update(geom_info)
    
    return trial_data


def run_block(
    mini_block: int,
    stim_block_df: pd.DataFrame,
    mem_row: pd.Series,
    geom_df: pd.DataFrame,
    tracker: Any,
    graphics_env: Any,
    win: visual.Window,
    exp_clock: core.Clock,
    cfg: dict,
    screen_cfg: dict,
    participant_id: str,
    part: str,
    trial_file_handle: Any,
    trial_writer: Any,
    block_file_handle: Any,
    block_writer: Any,
    memory_file_handle: Any,
    memory_writer: Any,
    session_paths: Dict[str, Path] = None,
    edf_name: str = None
) -> Dict[str, Any]:
    """
    Run a single mini-block: calibration, trials, memory probe, break.
    
    Parameters
    ----------
    mini_block : int
        Block number (1-9).
    stim_block_df : pd.DataFrame
        Stimulus manifest rows for this block (39 trials).
    mem_row : pd.Series
        Memory probe row for this block.
    geom_df : pd.DataFrame
        Polygon geometry data.
    tracker : pylink.EyeLink
        Connected EyeLink tracker.
    graphics_env : EyeLinkCoreGraphicsPsychoPy
        Graphics environment for calibration.
    win : visual.Window
        PsychoPy window.
    exp_clock : core.Clock
        Experiment clock.
    cfg : dict
        Full experiment configuration.
    screen_cfg : dict
        Screen configuration.
    participant_id : str
        Participant ID.
    part : str
        Part identifier (A or B).
    trial_file_handle : file
        Open file handle for trial CSV.
    trial_writer : csv.DictWriter
        CSV writer for trials.
    block_file_handle : file
        Open file handle for block CSV.
    block_writer : csv.DictWriter
        CSV writer for blocks.
    memory_file_handle : file
        Open file handle for memory CSV.
    memory_writer : csv.DictWriter
        CSV writer for memory probes.
        
    Returns
    -------
    dict
        Block summary statistics.
    """
    print(f"\n=== Starting Mini-Block {mini_block} ===")
    
    block_start_ts = exp_clock.getTime()
    
    # Calibration and validation
    print("Running calibration and validation...")
    calib_info = run_calibration_and_validation(
        tracker, graphics_env, cfg, exp_clock, mini_block
    )
    
    print(f"Calibration complete: {calib_info['validation_result']}")
    
    # Check if calibration was aborted
    if calib_info['validation_result'] == 'ABORT':
        print("Calibration aborted. Exiting block.")
        return {'aborted': True}
    
    # Initialize counters
    n_trials_planned = len(stim_block_df)
    n_trials_completed = 0
    n_drift_failures = 0
    
    # Run trials
    print(f"Running {n_trials_planned} trials...")
    
    for idx, trial_row in stim_block_df.iterrows():
        trial_result = run_single_trial(
            trial_row,
            geom_df,
            tracker,
            graphics_env,
            win,
            exp_clock,
            cfg,
            screen_cfg,
            participant_id,
            part,
            mini_block,
            calib_info
        )
        
        # Log trial data
        log_trial_row(trial_writer, trial_file_handle, trial_result, flush=True)
        
        if trial_result.get('aborted', False):
            n_drift_failures += 1
        else:
            n_trials_completed += 1
        
        # Check for abort key
        keys = event.getKeys(['escape'])
        if 'escape' in keys:
            print("Escape pressed. Aborting experiment.")
            return {'aborted': True, 'user_abort': True}
    
    print(f"Completed {n_trials_completed}/{n_trials_planned} trials")
    
    # Memory probe
    print("Running memory probe...")
    probe_start_ts = exp_clock.getTime()
    
    probe_image_id = mem_row['probe_image_id']
    probe_image_path = mem_row['probe_image_path']
    probe_duration_s = 3.0  # Fixed 3 second display
    is_old = mem_row.get('is_old', None)
    
    # Step 1: Show "Memory task ahead" screen
    memory_ahead_text = visual.TextStim(
        win,
        text="Memory Task Ahead",
        pos=(0, 0),
        height=48,
        color='white'
    )
    memory_ahead_text.draw()
    win.flip()
    tracker.sendMessage(f"MEMORY_TASK_AHEAD block={mini_block}")
    core.wait(2.0)  # Show for 2 seconds
    
    # Step 2: Load and display probe image for 3 seconds
    try:
        probe_image = visual.ImageStim(
            win,
            image=probe_image_path,
            pos=(0, 0),
            units='pix'
        )
        
        # Show image for 3 seconds
        probe_image.draw()
        win.flip()
        ts_probe_onset = exp_clock.getTime()
        tracker.sendMessage(f"MEMORY_PROBE_START block={mini_block} image={probe_image_id}")
        tracker.sendMessage(f"MEM_PROBE_ON {ts_probe_onset:.3f}")
        core.wait(probe_duration_s)
        ts_probe_offset = exp_clock.getTime()
        tracker.sendMessage(f"MEM_PROBE_OFF {ts_probe_offset:.3f}")
        
        # Step 3: Show response prompt
        prompt = visual.TextStim(
            win,
            text="Have you seen this image before?\n\nNumpad 4 = NEW (No)     Numpad 6 = OLD (Yes)",
            pos=(0, 0),
            height=32,
            color='white'
        )
        prompt.draw()
        win.flip()
        
        # Wait for response
        response_clock = core.Clock()
        keys = event.waitKeys(keyList=['num_4', 'num_6', 'escape'])
        response_time_ms = response_clock.getTime() * 1000
        
    except Exception as e:
        print(f"Warning: Could not load probe image {probe_image_path}: {e}")
        # Fallback to text-only prompt
        draw_instructions(
            win,
            f"Memory Probe\n\n"
            f"Have you seen this image before?\n\n"
            f"Numpad 4 = NEW (No)     Numpad 6 = OLD (Yes)"
        )
        tracker.sendMessage(f"MEMORY_PROBE_START block={mini_block} image={probe_image_id}")
        ts_probe_onset = exp_clock.getTime()
        response_clock = core.Clock()
        keys = event.waitKeys(keyList=['num_4', 'num_6', 'escape'])
        response_time_ms = response_clock.getTime() * 1000
        ts_probe_offset = exp_clock.getTime()
    
    if 'escape' in keys:
        return {'aborted': True, 'user_abort': True}
    
    response = 'old' if 'num_6' in keys else 'new'
    correct = None
    if is_old is not None:
        expected = 'old' if is_old else 'new'
        correct = (response == expected)
    
    probe_end_ts = exp_clock.getTime()
    correct_int = 1 if correct else (0 if correct is False else -1)
    tracker.sendMessage(
        f"MEM_RESP key={response} rt={response_time_ms/1000:.3f} correct={correct_int}"
    )
    tracker.sendMessage(f"MEMORY_PROBE_END response={response}")
    
    # Step 4: Show "Thank you" message
    thank_you_text = visual.TextStim(
        win,
        text="Thank you!",
        pos=(0, 0),
        height=48,
        color='white'
    )
    thank_you_text.draw()
    win.flip()
    tracker.sendMessage("MEMORY_THANK_YOU")
    core.wait(1.5)  # Show for 1.5 seconds
    
    # Log memory data
    memory_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': participant_id,
        'part': part,
        'mini_block': mini_block,
        'probe_image_id': probe_image_id,
        'probe_image_path': probe_image_path,
        'probe_duration_s': probe_duration_s,
        'is_old': is_old,
        'response': response,
        'response_time_ms': response_time_ms,
        'correct': correct,
        'probe_start_time': probe_start_ts,
        'probe_end_time': probe_end_ts
    }
    log_memory_row(memory_writer, memory_file_handle, memory_data, flush=True)
    
    # Timed break with countdown
    break_duration_actual_s = 0.0
    if mini_block < 9:  # No break after last block
        print("Starting 30-second break...")
        break_duration_planned_s = 30.0
        break_start_ts = exp_clock.getTime()
        
        # Create text stimuli for break screen
        break_title = visual.TextStim(
            win,
            text=f"Block {mini_block} of 9 complete!",
            pos=(0, 100),
            height=40,
            color='white'
        )
        break_subtitle = visual.TextStim(
            win,
            text="Take a short break. Next block starts in:",
            pos=(0, 30),
            height=28,
            color='white'
        )
        timer_text = visual.TextStim(
            win,
            text="60",
            pos=(0, -60),
            height=72,
            color='yellow'
        )
        
        tracker.sendMessage(f"BREAK_START block={mini_block}")
        
        # Backup EDF file during break (participant is away from tracker)
        edf_backup_success = False
        if session_paths and edf_name:
            try:
                # Show backup message
                backup_msg = visual.TextStim(
                    win,
                    text="Saving data backup...",
                    pos=(0, 0),
                    height=32,
                    color='white'
                )
                backup_msg.draw()
                win.flip()
                
                print(f"Backing up EDF after block {mini_block}...")
                tracker.sendMessage(f"EDF_BACKUP_START block={mini_block}")
                
                # Close current EDF file
                tracker.closeDataFile()
                
                # Retrieve EDF file from Host PC
                backup_filename = f"{edf_name[:-4]}_block{mini_block}.edf"  # e.g., P01A_block3.edf
                backup_path = session_paths['edf'] / backup_filename
                tracker.receiveDataFile(edf_name, str(backup_path))
                
                # Re-open the same EDF file to continue recording
                tracker.openDataFile(edf_name)
                
                # Re-send display coordinates for Data Viewer
                width_px = screen_cfg['resolution_px'][0]
                height_px = screen_cfg['resolution_px'][1]
                tracker.sendMessage(f"DISPLAY_COORDS 0 0 {width_px - 1} {height_px - 1}")
                tracker.sendMessage(f"EDF_BACKUP_END block={mini_block} file={backup_filename}")
                
                edf_backup_success = True
                print(f"EDF backup saved: {backup_path}")
                
            except Exception as e:
                print(f"Warning: EDF backup failed: {e}")
                tracker.sendMessage(f"EDF_BACKUP_FAILED block={mini_block} error={str(e)[:50]}")
                # Try to reopen EDF file if backup failed mid-way
                try:
                    tracker.openDataFile(edf_name)
                except:
                    pass
        
        # Countdown timer
        remaining = int(break_duration_planned_s)
        while remaining > 0:
            timer_text.text = str(remaining)
            break_title.draw()
            break_subtitle.draw()
            timer_text.draw()
            win.flip()
            
            # Check for ESC during break
            keys = event.getKeys(['escape'])
            if 'escape' in keys:
                return {'aborted': True, 'user_abort': True}
            
            core.wait(1.0)
            remaining -= 1
        
        break_end_ts = exp_clock.getTime()
        break_duration_actual_s = break_end_ts - break_start_ts
        tracker.sendMessage(f"BREAK_END duration={break_duration_actual_s:.1f}")
        
        print(f"Break complete ({break_duration_actual_s:.1f}s).")
    
    block_end_ts = exp_clock.getTime()
    
    # Log block data
    block_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': participant_id,
        'part': part,
        'mini_block': mini_block,
        'calibration_start_time': calib_info.get('ts_calib_start_first'),
        'calibration_end_time': calib_info.get('ts_calib_end_last'),
        'calibration_result': calib_info.get('validation_result'),
        'calibration_error_deg': calib_info.get('validation_rms_best'),
        'validation_result': calib_info.get('validation_result'),
        'validation_error_avg_deg': calib_info.get('validation_rms_best'),
        'validation_error_max_deg': calib_info.get('validation_max_err_best'),
        'n_trials': n_trials_planned,
        'n_trials_completed': n_trials_completed,
        'n_drift_failures': n_drift_failures,
        'memory_response': response,
        'memory_correct': correct,
        'memory_rt_ms': response_time_ms,
        'break_duration_actual_s': break_duration_actual_s,
        'block_start_time': block_start_ts,
        'block_end_time': block_end_ts,
        'block_duration_s': block_end_ts - block_start_ts
    }
    log_block_row(block_writer, block_file_handle, block_data, flush=True)
    
    print(f"=== Mini-Block {mini_block} Complete ===\n")
    
    return {'aborted': False}


def main():
    """
    Main experiment entry point.
    
    Parses arguments, loads configuration, initializes systems,
    and runs all mini-blocks for the specified participant and part.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run Experiment 2: Center Bias with EyeLink"
    )
    parser.add_argument(
        '--participant-id',
        type=str,
        required=True,
        help='Participant identifier (e.g., P01)'
    )
    parser.add_argument(
        '--part',
        type=str,
        required=True,
        choices=['A', 'B'],
        help='Experiment part (A or B)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/experiment_config.yaml',
        help='Path to configuration YAML file'
    )
    parser.add_argument(
        '--blocks',
        type=str,
        default='all',
        choices=['all', '1-3', '4-6', '7-9'],
        help='Block range to run (default: all)'
    )

    args = parser.parse_args()

    participant_id = args.participant_id
    part = args.part
    config_path = args.config
    block_range = args.blocks
    
    # Parse block range
    if block_range == 'all':
        blocks_to_run = list(range(1, 10))
    elif block_range == '1-3':
        blocks_to_run = [1, 2, 3]
    elif block_range == '4-6':
        blocks_to_run = [4, 5, 6]
    elif block_range == '7-9':
        blocks_to_run = [7, 8, 9]
    else:
        blocks_to_run = list(range(1, 10))

    print(f"\n{'='*60}")
    print(f"Experiment 2: Center Bias")
    print(f"Participant: {participant_id}, Part: {part}")
    print(f"Blocks: {block_range} (mini-blocks {blocks_to_run[0]}-{blocks_to_run[-1]})")
    print(f"{'='*60}\n")
    
    # Load configuration
    print("Loading configuration...")
    try:
        cfg = load_experiment_config(config_path)
        print(f"Configuration loaded from {config_path}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Load manifests
    print("Loading manifests...")
    try:
        stim_df, mem_df, geom_df = load_manifests(cfg)
        print(f"Loaded {len(stim_df)} stimulus trials, {len(mem_df)} memory probes")
    except Exception as e:
        print(f"Error loading manifests: {e}")
        sys.exit(1)
    
    # Filter manifests for part only (manifests are now participant-independent)
    print(f"Filtering for part {part}...")
    stim_part = stim_df[stim_df['part'] == part]
    mem_part = mem_df[mem_df['part'] == part]
    
    if len(stim_part) == 0:
        print(f"No trials found for part {part}")
        sys.exit(1)
    
    print(f"Found {len(stim_part)} trials, {len(mem_part)} memory probes for participant {participant_id}")
    
    # Get screen and eyelink config
    screen_cfg = cfg['screen']
    eyelink_cfg = cfg['eyelink']
    
    # Create PsychoPy monitor and window
    print("Creating PsychoPy window...")
    try:
        monitor, win = create_monitor_and_window(screen_cfg)
        print("Window created successfully")
    except Exception as e:
        print(f"Error creating window: {e}")
        sys.exit(1)
    
    # Create experiment clock
    exp_clock = core.Clock()

    # Run eye dominance test (before EyeLink setup)
    print("\nRunning eye dominance test...")
    dominant_eye = run_eye_dominance_test(win)
    print(f"Dominant eye: {dominant_eye}")

    # Initialize session paths and loggers
    print("\nInitializing session directories...")
    try:
        session_paths = init_session_paths(cfg, participant_id, part)
        print(f"Session directory: {session_paths['session_root']}")
        
        # Initialize CSV loggers
        trial_csv_path = session_paths['logs_trial'] / 'trials.csv'
        block_csv_path = session_paths['logs_block'] / 'blocks.csv'
        memory_csv_path = session_paths['logs_memory'] / 'memory.csv'
        
        trial_fh, trial_writer = init_trial_logger(str(trial_csv_path))
        block_fh, block_writer = init_block_logger(str(block_csv_path))
        memory_fh, memory_writer = init_memory_logger(str(memory_csv_path))
        
        print("CSV loggers initialized")
    except Exception as e:
        print(f"Error initializing session: {e}")
        win.close()
        sys.exit(1)
    
    # Connect to EyeLink
    print("Connecting to EyeLink...")
    try:
        tracker = connect_eyelink(cfg)
        print(f"Connected to EyeLink (version {tracker.getTrackerVersion()})")
    except Exception as e:
        print(f"Error connecting to EyeLink: {e}")
        win.close()
        trial_fh.close()
        block_fh.close()
        memory_fh.close()
        sys.exit(1)
    
    # Setup EDF file
    print("Opening EDF file...")
    try:
        edf_name = setup_edf(tracker, participant_id, part, str(session_paths['edf']))
        print(f"EDF file opened: {edf_name}")
    except Exception as e:
        print(f"Error opening EDF: {e}")
        tracker.close()
        win.close()
        trial_fh.close()
        block_fh.close()
        memory_fh.close()
        sys.exit(1)
    
    # Configure tracker
    print("Configuring tracker...")
    try:
        configure_tracker(tracker, cfg, screen_cfg)
        print("Tracker configured successfully")
    except Exception as e:
        # In CL mode, some configuration commands may not be available
        # Print warning but continue if it's just a CL mode limitation
        error_msg = str(e)
        if "CL mode" in error_msg or "Not available" in error_msg:
            print(f"Warning: Some advanced features not available in EyeLink CL mode")
            print(f"Continuing with basic configuration...")
        else:
            # Real error - exit
            print(f"FATAL Error configuring tracker: {e}")
            import traceback
            traceback.print_exc()
            tracker.close()
            win.close()
            trial_fh.close()
            block_fh.close()
            memory_fh.close()
            sys.exit(1)
    
    # Write session metadata
    print("Writing session metadata...")
    try:
        metadata = {
            'participant_id': participant_id,
            'part': part,
            'session_timestamp': datetime.now().isoformat(),
            'config_path': config_path,
            'screen_config': screen_cfg,
            'eyelink_config': eyelink_cfg,
            'edf_name': edf_name,
            'n_trials': len(stim_part),
            'n_blocks': len(stim_part['mini_block'].unique()),
            'dominant_eye': dominant_eye
        }
        metadata_path = session_paths['logs_session'] / 'session_metadata.json'
        write_session_metadata(str(metadata_path), metadata)
        print(f"Metadata written to {metadata_path}")
    except Exception as e:
        print(f"Warning: Error writing metadata: {e}")
    
    # Show instructions BEFORE opening EyeLink graphics (critical for keyboard input)
    print("Showing instructions...")
    draw_instructions(
        win,
        f"Center Bias Experiment\n\n"
        f"Participant: {participant_id}\n"
        f"Part: {part}\n\n"
        f"You will complete 9 blocks of trials.\n"
        f"Each block begins with calibration.\n\n"
        f"Press SPACE to begin."
    )
    
    # Setup graphics environment for calibration AFTER instructions
    # (pylink.openGraphicsEx takes over keyboard/graphics control)
    graphics_env = None
    if EyeLinkCoreGraphicsPsychoPy:
        print("Setting up EyeLink graphics environment...")
        try:
            # Put tracker in offline mode before graphics setup (required)
            tracker.setOfflineMode()
            
            # Create graphics environment
            graphics_env = EyeLinkCoreGraphicsPsychoPy(tracker, win)
            print(f"Graphics env created: {graphics_env}")
            
            # Set calibration colors: foreground (target), background
            # PsychoPy uses (-1,-1,-1)=black, (1,1,1)=white, (0,0,0)=mid-gray
            foreground_color = (-1, -1, -1)  # Black target
            background_color = win.color     # Match window background
            graphics_env.setCalibrationColors(foreground_color, background_color)
            
            # Set calibration target type and size
            graphics_env.setTargetType('circle')
            graphics_env.setTargetSize(24)  # pixels
            
            # Disable calibration sounds (optional)
            graphics_env.setCalibrationSounds('', '', '')
            
            # Open the graphics environment
            pylink.openGraphicsEx(graphics_env)
            print("EyeLink graphics environment initialized")
        except Exception as e:
            print(f"Warning: Could not setup EyeLink graphics: {e}")
            import traceback
            traceback.print_exc()
            graphics_env = None
    else:
        print("Warning: EyeLinkCoreGraphicsPsychoPy not available")
    
    # Send session start message
    tracker.sendMessage(f"SESSION_START participant={participant_id} part={part}")
    
    # Run blocks
    try:
        for mini_block in blocks_to_run:
            # Get trials for this block
            stim_block = stim_part[stim_part['mini_block'] == mini_block].sort_values('trial_in_block')
            mem_block = mem_part[mem_part['mini_block'] == mini_block]

            if len(stim_block) == 0:
                print(f"Warning: No trials for block {mini_block}")
                continue
            
            if len(mem_block) == 0:
                print(f"Warning: No memory probe for block {mini_block}")
                # Create dummy memory row
                mem_row = pd.Series({
                    'probe_image_id': 'none',
                    'probe_image_path': '',
                    'probe_duration_s': 3.0,
                    'is_old': None
                })
            else:
                mem_row = mem_block.iloc[0]
            
            # Run block
            block_result = run_block(
                mini_block,
                stim_block,
                mem_row,
                geom_df,
                tracker,
                graphics_env,
                win,
                exp_clock,
                cfg,
                screen_cfg,
                participant_id,
                part,
                trial_fh,
                trial_writer,
                block_fh,
                block_writer,
                memory_fh,
                memory_writer,
                session_paths,
                edf_name
            )
            
            # Check for abort
            if block_result.get('aborted', False):
                print("Block aborted by user or system.")
                break
    
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user.")
    except Exception as e:
        print(f"\nError during experiment: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nCleaning up...")
        
        # Send session end message (guard against tracker being None)
        if tracker is not None:
            try:
                tracker.sendMessage(f"SESSION_END {exp_clock.getTime():.3f}")
            except Exception as e:
                print(f"Warning: Could not send session end message: {e}")
        
        # Close EDF and retrieve file
        if tracker is not None:
            try:
                print("Closing EDF...")
                tracker.closeDataFile()
                
                # Retrieve EDF file from host
                edf_local_path = session_paths['edf'] / edf_name
                print(f"Retrieving EDF file to {edf_local_path}...")
                tracker.receiveDataFile(edf_name, str(edf_local_path))
                print("EDF file retrieved successfully")
            except Exception as e:
                print(f"Warning: Error with EDF file: {e}")
            
            # Close tracker connection
            try:
                tracker.close()
            except Exception as e:
                print(f"Warning: Error closing tracker: {e}")
        
        # Close CSV files
        trial_fh.close()
        block_fh.close()
        memory_fh.close()
        
        # Close window
        win.close()
        
        print("\nExperiment complete!")
        print(f"Data saved to: {session_paths['session_root']}")


if __name__ == "__main__":
    main()


# python src/experiment2_runner.py --participant-id P05 --part A

# python src/check_binocular_recording.py "data\raw\participant_P00\part_A\session_20260117_190051/edf/*.edf"
# python src/check_binocular_recording.py "data\raw\participant_P00\part_A\session_20260117_201349/edf/*.edf"
# python src\extract_fixations.py "data\raw\participant_P00\part_A\session_20260117_201349\edf\P00A_block1.edf"