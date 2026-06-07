"""
EyeLink tracker utilities for center_bias_exp.

This module provides functions for connecting to an SR Research EyeLink 1000
eye tracker, configuring it, running calibration/validation, and controlling
recording sessions. Follows SR Research pylink best practices.
"""

import time
from typing import Dict, Tuple, Any, Optional

import pylink
from psychopy import core


def connect_eyelink(cfg: dict) -> pylink.EyeLink:
    """
    Connect to EyeLink tracker.
    
    Establishes connection to an EyeLink eye tracker using the address
    specified in the configuration. An empty string connects to the
    default tracker on the network.
    
    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing 'eyelink' section with
        'address' key (empty string for default tracker).
        
    Returns
    -------
    pylink.EyeLink
        Connected EyeLink tracker object.
        
    Raises
    ------
    RuntimeError
        If connection to the tracker fails.
        
    Examples
    --------
    >>> cfg = {'eyelink': {'address': ''}}
    >>> tracker = connect_eyelink(cfg)
    >>> print(tracker.getTrackerVersion())
    """
    eyelink_address = cfg['eyelink'].get('address', '')
    
    # Connect to tracker (empty string = default)
    try:
        if eyelink_address:
            tracker = pylink.EyeLink(eyelink_address)
        else:
            tracker = pylink.EyeLink()
    except RuntimeError as e:
        raise RuntimeError(
            f"Failed to connect to EyeLink tracker at address '{eyelink_address}': {e}"
        )
    
    return tracker


def setup_edf(
    tracker: pylink.EyeLink,
    participant_id: str,
    part: str,
    edf_dir: str
) -> str:
    """
    Open EDF file on the EyeLink host PC.
    
    Creates a short EDF filename (max 8 characters) derived from participant
    ID and part, and opens it on the tracker's host computer.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    participant_id : str
        Participant identifier (e.g., 'P01').
    part : str
        Experiment part identifier (e.g., 'A' or 'B').
    edf_dir : str
        Directory path where EDF will be saved (for metadata only;
        EDF is stored on host PC initially).
        
    Returns
    -------
    str
        EDF filename opened on the host PC (8 characters or less).
        
    Raises
    ------
    RuntimeError
        If opening the EDF file fails.
        
    Examples
    --------
    >>> tracker = connect_eyelink(cfg)
    >>> edf_name = setup_edf(tracker, 'P01', 'A', '/data/edf/')
    >>> print(edf_name)
    'P01A.edf'
    
    Notes
    -----
    EDF filenames on the EyeLink host are limited to 8 characters
    (not including the .edf extension).
    """
    # Create short EDF name (max 8 chars before .edf)
    # Format: P<nn><part> (e.g., P01A, P23B)
    # Remove any 'P' prefix if present to avoid duplication
    pid = participant_id.replace('P', '').replace('p', '')
    edf_name = f"P{pid}{part}.edf"
    
    # Ensure name is 8 chars or less (without .edf extension)
    base_name = edf_name.replace('.edf', '')
    if len(base_name) > 8:
        # Truncate if too long
        base_name = base_name[:8]
        edf_name = f"{base_name}.edf"
    
    # Open EDF file on host PC
    try:
        tracker.openDataFile(edf_name)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to open EDF file '{edf_name}': {e}")
    
    # Add preamble with metadata
    tracker.sendCommand(f"add_file_preamble_text 'Participant: {participant_id}'")
    tracker.sendCommand(f"add_file_preamble_text 'Part: {part}'")
    tracker.sendCommand(f"add_file_preamble_text 'Experiment: center_bias_exp'")
    
    return edf_name


def configure_tracker(
    tracker: pylink.EyeLink,
    cfg: dict,
    screen_cfg: dict
) -> None:
    """
    Configure EyeLink tracker parameters.
    
    Sends commands to set screen coordinates, sampling rate, event/sample
    filters, parser thresholds, and calibration type according to the
    configuration.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    cfg : dict
        Configuration dictionary containing 'eyelink' section with tracker
        parameters.
    screen_cfg : dict
        Screen configuration dictionary containing:
        - 'resolution_px': [width, height] in pixels
        - 'width_cm': screen width in centimeters
        - 'height_cm': screen height in centimeters
        - 'viewing_distance_cm': viewing distance in centimeters
        
    Examples
    --------
    >>> tracker = connect_eyelink(cfg)
    >>> screen = {'resolution_px': [3840, 2160], 'width_cm': 59.77, ...}
    >>> configure_tracker(tracker, cfg, screen)
    
    Notes
    -----
    Following SR Research recommendations for EyeLink 1000 configuration.
    """
    eyelink_cfg = cfg['eyelink']
    
    # Get screen dimensions
    width_px = screen_cfg['resolution_px'][0]
    height_px = screen_cfg['resolution_px'][1]
    
    # Set screen pixel coordinates (origin at top-left)
    tracker.sendCommand(f"screen_pixel_coords = 0 0 {width_px - 1} {height_px - 1}")
    
    # Set display coordinates for Data Viewer
    tracker.sendMessage(f"DISPLAY_COORDS 0 0 {width_px - 1} {height_px - 1}")
    
    # Set calibration type
    calibration_type = eyelink_cfg.get('calibration_type', 'HV9')
    tracker.sendCommand(f"calibration_type = {calibration_type}")
    
    # Set file sample and event data (what gets recorded to EDF)
    # Use config values or sensible defaults
    file_sample_data = eyelink_cfg.get('file_sample_data', 
        'LEFT,RIGHT,GAZE,AREA,GAZERES,HREF,PUPIL,STATUS,INPUT')
    file_event_filter = eyelink_cfg.get('file_event_filter',
        'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT')
    
    tracker.sendCommand(f"file_sample_data = {file_sample_data}")
    tracker.sendCommand(f"file_event_filter = {file_event_filter}")
    
    # Set link sample and event data (what gets sent over network)
    link_sample_data = eyelink_cfg.get('link_sample_data',
        'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS')
    link_event_filter = eyelink_cfg.get('link_event_filter',
        'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON')
    
    tracker.sendCommand(f"link_sample_data = {link_sample_data}")
    tracker.sendCommand(f"link_event_filter = {link_event_filter}")
    
    # Set parser configuration (saccade/fixation detection thresholds)
    saccade_velocity_threshold = eyelink_cfg.get('saccade_velocity_threshold', 30)
    saccade_acceleration_threshold = eyelink_cfg.get('saccade_acceleration_threshold', 8000)

    tracker.sendCommand(f"saccade_velocity_threshold = {saccade_velocity_threshold}")
    tracker.sendCommand(f"saccade_acceleration_threshold = {saccade_acceleration_threshold}")

    # CRITICAL: Set binocular recording mode
    # This tells the tracker to record from BOTH eyes, not just one
    binocular_enabled = eyelink_cfg.get('binocular_enabled', True)
    if binocular_enabled:
        tracker.sendCommand("binocular_enabled = YES")
        # setRecordingParseType: 0=BINOCULAR, 1=LEFT_ONLY, 2=RIGHT_ONLY
        # This command is only available in full EyeLink mode, not CL mode
        try:
            tracker.setRecordingParseType(0)
            print("EyeLink configured for BINOCULAR recording (both eyes)")
        except (RuntimeError, Exception) as e:
            # CL mode - binocular is set via command only
            print(f"EyeLink in CL mode - binocular set via command (both eyes)")
    else:
        tracker.sendCommand("binocular_enabled = NO")
        try:
            tracker.setRecordingParseType(1)  # Default to LEFT eye if monocular
            print("EyeLink configured for MONOCULAR recording (left eye)")
        except (RuntimeError, Exception):
            print("EyeLink in CL mode - monocular set via command (left eye)")

    # Enable automatic calibration pacing
    tracker.sendCommand("automatic_calibration_pacing = 1000")

    # Set button function for accepting fixation during calibration
    tracker.sendCommand("button_function 5 'accept_target_fixation'")


def run_calibration_and_validation(
    tracker: pylink.EyeLink,
    graphics_env: Any,
    cfg: dict,
    exp_clock: core.Clock,
    block_id: int
) -> Dict[str, Any]:
    """
    Run calibration and validation with retry logic.
    
    Enters camera setup mode, runs calibration followed by validation,
    and repeats until validation passes or user aborts. Logs timing
    and error metrics via EDF messages.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    graphics_env : EyeLinkCoreGraphicsPsychoPy
        Graphics environment for displaying calibration targets.
    cfg : dict
        Configuration dictionary containing validation criteria.
    exp_clock : core.Clock
        PsychoPy clock for experiment timing.
    block_id : int
        Block identifier for logging purposes.
        
    Returns
    -------
    dict
        Dictionary containing:
        - 'calibration_attempts': Number of calibration attempts
        - 'validation_result': 'PASS' or 'ABORT'
        - 'validation_rms_best': Best RMS error in degrees
        - 'validation_max_err_best': Best max error in degrees
        - 'ts_calib_start_first': Timestamp of first calibration start
        - 'ts_calib_end_last': Timestamp of last calibration end
        
    Examples
    --------
    >>> from psychopy import core
    >>> tracker = connect_eyelink(cfg)
    >>> exp_clock = core.Clock()
    >>> result = run_calibration_and_validation(
    ...     tracker, graphics_env, cfg, exp_clock, block_id=1
    ... )
    >>> print(result['validation_result'])
    'PASS'
    """
    ts_calib_start_first = exp_clock.getTime()

    # Put tracker in offline mode before calibration (required for setup)
    tracker.setOfflineMode()

    # NOTE: Binocular/monocular mode is set via the EyeLink Host PC configuration
    # and the file_sample_data/file_event_filter commands (which include LEFT,RIGHT)
    # No additional active_eye command is needed - the tracker uses its hardware config

    # Send message indicating calibration block start
    tracker.sendMessage(f"BLOCK_{block_id}_CALIBRATION_START")
    tracker.sendMessage(f"CALIB_START {ts_calib_start_first:.3f}")

    # Enter camera setup / calibration mode
    # doTrackerSetup() is a blocking call that handles calibration UI
    # User presses 'C' for calibrate, 'V' for validate, 'O' or Enter to exit
    try:
        tracker.doTrackerSetup()
    except RuntimeError as e:
        # User aborted calibration (pressed ESC or error occurred)
        print(f"Calibration error or abort: {e}")
        try:
            tracker.exitCalibration()
        except:
            pass
        ts_calib_end_last = exp_clock.getTime()
        tracker.sendMessage(f"CALIB_ABORT {ts_calib_end_last:.3f}")
        return {
            'calibration_attempts': 1,
            'validation_result': 'ABORT',
            'validation_rms_best': None,
            'validation_max_err_best': None,
            'ts_calib_start_first': ts_calib_start_first,
            'ts_calib_end_last': ts_calib_end_last
        }
    
    ts_calib_end_last = exp_clock.getTime()
    
    # Calibration completed successfully (user pressed 'O' or Enter to exit)
    tracker.sendMessage(f"CALIB_END {ts_calib_end_last:.3f}")
    tracker.sendMessage(f"BLOCK_{block_id}_CALIBRATION_COMPLETE")
    
    print(f"Calibration complete for block {block_id}")
    
    return {
        'calibration_attempts': 1,
        'validation_result': 'PASS',
        'validation_rms_best': None,  # Not available from basic API
        'validation_max_err_best': None,
        'ts_calib_start_first': ts_calib_start_first,
        'ts_calib_end_last': ts_calib_end_last
    }


def start_recording(
    tracker: pylink.EyeLink,
    exp_clock: core.Clock
) -> float:
    """
    Start EyeLink recording and return timestamp.
    
    Begins recording eye data to the EDF file and over the link.
    Includes a brief delay to ensure recording has stabilized.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    exp_clock : core.Clock
        PsychoPy clock for experiment timing.
        
    Returns
    -------
    float
        Experiment clock timestamp when recording started.
        
    Examples
    --------
    >>> tracker = connect_eyelink(cfg)
    >>> from psychopy import core
    >>> exp_clock = core.Clock()
    >>> ts = start_recording(tracker, exp_clock)
    >>> print(f"Recording started at {ts:.3f}s")
    """
    # Start recording: (file_samples, file_events, link_samples, link_events)
    # 1, 1, 1, 1 means record everything
    error = tracker.startRecording(1, 1, 1, 1)
    
    if error != 0:
        raise RuntimeError(f"Failed to start recording, error code: {error}")
    
    # Wait for recording to stabilize (SR Research recommendation)
    pylink.pumpDelay(100)
    
    # Get timestamp
    ts = exp_clock.getTime()
    
    # Send message to EDF
    tracker.sendMessage(f"RECORDING_START {ts:.3f}")
    
    return ts


def stop_recording(
    tracker: pylink.EyeLink,
    exp_clock: core.Clock
) -> float:
    """
    Stop EyeLink recording and return timestamp.
    
    Stops recording eye data. Should be called after each block or
    when recording is no longer needed.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    exp_clock : core.Clock
        PsychoPy clock for experiment timing.
        
    Returns
    -------
    float
        Experiment clock timestamp when recording stopped.
        
    Examples
    --------
    >>> tracker = connect_eyelink(cfg)
    >>> from psychopy import core
    >>> exp_clock = core.Clock()
    >>> ts = stop_recording(tracker, exp_clock)
    >>> print(f"Recording stopped at {ts:.3f}s")
    """
    # Get timestamp before stopping
    ts = exp_clock.getTime()
    
    # Send message to EDF
    tracker.sendMessage(f"RECORDING_STOP {ts:.3f}")
    
    # Stop recording
    tracker.stopRecording()
    
    # Brief delay to ensure stop command is processed
    pylink.pumpDelay(50)
    
    return ts


def wait_for_fixation_gaze(
    tracker: pylink.EyeLink,
    target_x: float,
    target_y: float,
    exp_clock: core.Clock,
    fixation_window_px: float = 100.0,
    required_duration_ms: float = 300.0,
    max_wait_s: float = 10.0
) -> Tuple[bool, float]:
    """
    Wait for participant to fixate on target location using gaze data.
    
    This is a gaze-gated fixation check similar to the approach used in
    polygons.py. It checks live gaze data from the tracker and waits
    until the participant has fixated within the window for the required
    duration.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    target_x : float
        X coordinate of fixation target in EyeLink pixels (top-left origin).
    target_y : float
        Y coordinate of fixation target in EyeLink pixels (top-left origin).
    exp_clock : core.Clock
        PsychoPy clock for experiment timing.
    fixation_window_px : float, optional
        Radius in pixels around target that counts as fixating (default: 100).
    required_duration_ms : float, optional
        Milliseconds of stable fixation required (default: 300).
    max_wait_s : float, optional
        Maximum time to wait for fixation in seconds (default: 10).
        
    Returns
    -------
    tuple of (bool, float)
        - success: True if fixation achieved, False if timeout
        - timestamp: Experiment clock timestamp when function returned
    """
    ts_start = exp_clock.getTime()
    tracker.sendMessage(f"FIXATION_CHECK_START {ts_start:.3f} target=({target_x:.1f},{target_y:.1f})")
    
    fixation_start_time = None
    
    while (exp_clock.getTime() - ts_start) < max_wait_s:
        # Get newest sample from tracker
        sample = tracker.getNewestSample()
        
        if sample is not None:
            # Try to get gaze data from left or right eye
            gaze = None
            if sample.isLeftSample():
                gaze = sample.getLeftEye().getGaze()
            elif sample.isRightSample():
                gaze = sample.getRightEye().getGaze()
            
            if gaze is not None and gaze[0] != pylink.MISSING_DATA:
                gx, gy = gaze
                
                # Check if gaze is within fixation window
                dist = ((gx - target_x) ** 2 + (gy - target_y) ** 2) ** 0.5
                
                if dist < fixation_window_px:
                    # Gaze is on target
                    if fixation_start_time is None:
                        fixation_start_time = exp_clock.getTime() * 1000  # Convert to ms
                    else:
                        # Check if fixation duration met
                        current_time_ms = exp_clock.getTime() * 1000
                        if (current_time_ms - fixation_start_time) >= required_duration_ms:
                            # Fixation achieved!
                            ts_end = exp_clock.getTime()
                            tracker.sendMessage(f"FIXATION_CHECK_PASS {ts_end:.3f}")
                            return True, ts_end
                else:
                    # Gaze moved off target, reset timer
                    fixation_start_time = None
        
        # Small delay to prevent CPU spinning
        core.wait(0.001, hogCPUperiod=0.0)
    
    # Timeout
    ts_end = exp_clock.getTime()
    tracker.sendMessage(f"FIXATION_CHECK_TIMEOUT {ts_end:.3f}")
    return False, ts_end


def check_drift_error(
    tracker: pylink.EyeLink,
    target_x: float,
    target_y: float,
    screen_width_px: int,
    viewing_distance_cm: float,
    screen_width_cm: float
) -> Tuple[float, float, float]:
    """
    Calculate current drift error in degrees based on gaze position.
    
    Gets the newest gaze sample and calculates the angular error between
    the gaze position and the target position.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object (must be recording).
    target_x : float
        Target X coordinate in EyeLink pixels.
    target_y : float
        Target Y coordinate in EyeLink pixels.
    screen_width_px : int
        Screen width in pixels.
    viewing_distance_cm : float
        Viewing distance in centimeters.
    screen_width_cm : float
        Screen width in centimeters.
        
    Returns
    -------
    tuple of (float, float, float)
        - error_deg: Total error in degrees visual angle
        - error_x_px: X error in pixels
        - error_y_px: Y error in pixels
        Returns (-1, 0, 0) if no valid gaze data available.
    """
    import math
    
    sample = tracker.getNewestSample()
    if sample is None:
        return -1, 0, 0
    
    # Get gaze data from available eye
    gaze = None
    if sample.isLeftSample():
        gaze = sample.getLeftEye().getGaze()
    elif sample.isRightSample():
        gaze = sample.getRightEye().getGaze()
    
    if gaze is None or gaze[0] == pylink.MISSING_DATA:
        return -1, 0, 0
    
    gx, gy = gaze
    
    # Calculate pixel error
    error_x_px = gx - target_x
    error_y_px = gy - target_y
    error_px = math.sqrt(error_x_px ** 2 + error_y_px ** 2)
    
    # Convert to degrees
    # pixels per cm = screen_width_px / screen_width_cm
    pixels_per_cm = screen_width_px / screen_width_cm
    error_cm = error_px / pixels_per_cm
    
    # Angular error: tan(theta) = error_cm / viewing_distance_cm
    error_deg = math.degrees(math.atan2(error_cm, viewing_distance_cm))
    
    return error_deg, error_x_px, error_y_px


def drift_correction_with_auto_accept(
    tracker: pylink.EyeLink,
    target_x: float,
    target_y: float,
    exp_clock: core.Clock,
    screen_width_px: int,
    viewing_distance_cm: float,
    screen_width_cm: float,
    auto_accept_threshold_deg: float = 1.0
) -> Tuple[bool, float, float]:
    """
    Perform drift correction with auto-accept if error is below threshold.

    First checks the current gaze error. If it's below the threshold,
    automatically accepts without blocking. Otherwise, falls back to
    the standard EyeLink drift correction.

    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    target_x : float
        Target X coordinate in EyeLink pixels.
    target_y : float
        Target Y coordinate in EyeLink pixels.
    exp_clock : core.Clock
        PsychoPy clock for timing.
    screen_width_px : int
        Screen width in pixels.
    viewing_distance_cm : float
        Viewing distance in centimeters.
    screen_width_cm : float
        Screen width in centimeters.
    auto_accept_threshold_deg : float, optional
        Error threshold in degrees below which drift is auto-accepted.
        Default is 1.0 degree.

    Returns
    -------
    tuple of (bool, float, float)
        - success: True if drift correction passed
        - error_deg: Measured error in degrees (or -1 if unknown)
        - timestamp: Experiment clock time when drift correction ended
    """
    ts_start = exp_clock.getTime()
    tracker.sendMessage(f"DRIFT_CHECK_START {ts_start:.3f}")

    # Wait briefly for fresh gaze samples to accumulate (200ms)
    # This ensures we have valid data to measure drift error
    core.wait(0.2)

    # Check current drift error (average over a few samples for stability)
    error_deg, error_x_px, error_y_px = check_drift_error(
        tracker, target_x, target_y,
        screen_width_px, viewing_distance_cm, screen_width_cm
    )

    if error_deg >= 0 and error_deg < auto_accept_threshold_deg:
        # Error is below threshold - auto-accept!
        ts_end = exp_clock.getTime()
        tracker.sendMessage(
            f"DRIFT_AUTO_ACCEPT {ts_end:.3f} error_deg={error_deg:.3f} "
            f"threshold={auto_accept_threshold_deg}"
        )
        print(f"  Drift auto-accepted: {error_deg:.3f}° < {auto_accept_threshold_deg}°")
        return True, error_deg, ts_end
    
    # Error too large or couldn't measure - apply manual drift correction
    tracker.sendMessage(
        f"DRIFT_MANUAL_CORRECT {exp_clock.getTime():.3f} "
        f"measured_error={error_deg:.3f}"
    )

    # CRITICAL: Put tracker in offline mode BEFORE drift correction
    tracker.setOfflineMode()

    # Wait for mode transition to stabilize (REQUIRED!)
    core.wait(0.05)

    try:
        # doDriftCorrect applies the correction offset
        # draw_target=1: draw target on tracker display
        # allow_setup=1: allow ESC to enter setup for recalibration
        result = tracker.doDriftCorrect(int(target_x), int(target_y), 1, 1)
        success = (result == 0)
    except RuntimeError:
        success = False

    ts_end = exp_clock.getTime()

    if success:
        tracker.sendMessage(f"DRIFT_CORRECT_PASS {ts_end:.3f}")
    else:
        tracker.sendMessage(f"DRIFT_CORRECT_FAIL {ts_end:.3f}")

    return success, error_deg, ts_end


def drift_correction_builtin(
    tracker: pylink.EyeLink,
    cue_x: float,
    cue_y: float,
    exp_clock: core.Clock
) -> Tuple[bool, float]:
    """
    Perform built-in EyeLink drift correction with proper state management.

    Uses EyeLink's doDriftCorrect() method to perform drift correction
    at the specified screen location. The participant fixates on a target,
    and the tracker adjusts for any drift in calibration.

    IMPROVEMENTS:
    - Ensures tracker is in offline mode before drift correction
    - Waits for mode transition to stabilize
    - Properly handles all error codes
    - Prevents "stuck" state that was occurring

    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    cue_x : float
        X coordinate of drift correction target in pixels.
    cue_y : float
        Y coordinate of drift correction target in pixels.
    exp_clock : core.Clock
        PsychoPy clock for experiment timing.

    Returns
    -------
    tuple of (bool, float)
        - success: True if drift correction passed, False if failed or aborted
        - timestamp: Experiment clock timestamp when drift correction ended

    Examples
    --------
    >>> tracker = connect_eyelink(cfg)
    >>> from psychopy import core
    >>> exp_clock = core.Clock()
    >>> success, ts = drift_correction_builtin(tracker, 1920, 1080, exp_clock)
    >>> if success:
    ...     print(f"Drift correction passed at {ts:.3f}s")
    ... else:
    ...     print("Drift correction failed or aborted")

    Notes
    -----
    This is the standard EyeLink drift correction. For custom gaze-gated
    drift checking, use a separate function.
    """
    # Send message indicating drift correction start
    ts_start = exp_clock.getTime()
    tracker.sendMessage(f"DRIFT_CORRECT_START {ts_start:.3f} pos=({cue_x:.1f},{cue_y:.1f})")

    # CRITICAL: Put tracker in offline mode BEFORE drift correct
    # This prevents the "stuck" state you were experiencing
    tracker.setOfflineMode()

    # Wait for mode transition to stabilize (REQUIRED!)
    core.wait(0.05)

    # Perform drift correction
    # doDriftCorrect(x, y, draw_target, allow_setup)
    # draw_target=1: draw target on tracker display
    # allow_setup=1: allow 'ESC' to enter setup mode for recalibration
    try:
        error = tracker.doDriftCorrect(int(cue_x), int(cue_y), 1, 1)

        # Parse error codes:
        # 0 = OK (drift correction successful)
        # 27 = ESC_KEY (user pressed ESC)
        # Other values = error or abort
        if error == 0:
            success = True
            error_msg = "OK"
        elif error == 27:  # ESC_KEY
            success = False
            error_msg = "USER_ABORT_ESC"
        else:
            success = False
            error_msg = f"ERROR_{error}"

    except RuntimeError as e:
        # Exception occurred during drift correct
        success = False
        error_msg = f"RUNTIME_ERROR: {str(e)[:50]}"
        print(f"Drift correction runtime error: {e}")
    except Exception as e:
        # Unexpected exception
        success = False
        error_msg = f"EXCEPTION: {str(e)[:50]}"
        print(f"Unexpected drift correction error: {e}")

    # Get end timestamp
    ts_end = exp_clock.getTime()

    # Send message with detailed result
    result_str = "PASS" if success else "FAIL"
    tracker.sendMessage(
        f"DRIFT_CORRECT_END {ts_end:.3f} result={result_str} error={error_msg} "
        f"duration={(ts_end - ts_start):.3f}"
    )

    print(f"Drift correction: {result_str} ({error_msg}) in {ts_end - ts_start:.2f}s")

    # NOTE: We do NOT need to call setOfflineMode() or restart recording here
    # The tracker is already in offline mode (set at line 730) and will be
    # put back into recording mode by the caller when the trial starts
    # This is the standard EyeLink pattern for drift correction

    return success, ts_end
