"""
EyeLink 1000 Plus interface for the polygon center-bias experiment (Pygame).

This module provides the eye-tracker side of the experiment: connecting to the
SR Research EyeLink 1000 Plus Host PC, opening/configuring an EDF data file,
running calibration/validation, controlling recording, and a gaze-gated
fixation check with manual (key-press) override.

It is adapted from center_bias_exp/src/eyetracker_utils.py, but with the
PsychoPy dependency removed: calibration graphics use pylink's built-in
SDL/pygame graphics (pylink.openGraphics), timing uses a perf_counter-based
clock, and all gaze coordinates are in Pygame's top-left-origin pixel space
(which matches the EyeLink screen_pixel_coords convention).

pylink is imported lazily so this file can be inspected on machines without the
SR Research library installed. The actual experiment must be run on the lab PC
where pylink is available and the Host PC is reachable.
"""

import time

try:
    import pylink
    PYLINK_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on lab machine setup
    pylink = None
    PYLINK_AVAILABLE = False


# Sentinel returned by gaze checks for the source that ended the wait.
FIXATION_GAZE = "gaze"        # auto-advanced: gaze held on target long enough
FIXATION_MANUAL = "manual"    # experimenter pressed SPACE to accept
FIXATION_ABORT = "abort"      # experimenter pressed Q / ESC
FIXATION_TIMEOUT = "timeout"  # max wait elapsed without a stable fixation


class ExpClock:
    """Minimal monotonic clock (seconds) replacing psychopy.core.Clock.

    getTime() returns seconds elapsed since construction (or last reset).
    """

    def __init__(self):
        self._start = time.perf_counter()

    def reset(self):
        self._start = time.perf_counter()

    def getTime(self):
        return time.perf_counter() - self._start


def connect_eyelink(address="100.1.1.1", dummy_mode=False):
    """Connect to the EyeLink Host PC.

    Parameters
    ----------
    address : str
        Host PC IP address. The EyeLink 1000 Plus default is "100.1.1.1".
        Pass an empty string to let pylink use its own default.
    dummy_mode : bool
        If True, connect in simulation mode (no physical tracker) for testing
        the integration on a laptop.

    Returns
    -------
    pylink.EyeLink
        Connected (or simulated) tracker object.
    """
    if not PYLINK_AVAILABLE:
        raise RuntimeError(
            "pylink is not installed. Install the SR Research pylink package "
            "and run this on the EyeLink host-connected machine."
        )

    try:
        if dummy_mode:
            tracker = pylink.EyeLink(None)  # None => dummy / no connection
        elif address:
            tracker = pylink.EyeLink(address)
        else:
            tracker = pylink.EyeLink()
    except RuntimeError as e:
        raise RuntimeError(
            f"Failed to connect to EyeLink tracker at address '{address}': {e}"
        )

    return tracker


def setup_edf(tracker, participant_id, edf_dir):
    """Open an EDF data file on the Host PC.

    EDF filenames on the host are limited to 8 characters (before .edf), so the
    participant id is sanitised and truncated.

    Parameters
    ----------
    tracker : pylink.EyeLink
    participant_id : str
        e.g. "P01". Only alphanumerics are kept.
    edf_dir : str
        Local directory the EDF will eventually be copied to (recorded in the
        preamble for traceability; the file lives on the host until retrieval).

    Returns
    -------
    str
        EDF filename opened on the host (<= 8 chars + ".edf").
    """
    safe = "".join(ch for ch in str(participant_id) if ch.isalnum())
    if not safe:
        safe = "SUBJ"
    base_name = safe[:8]
    edf_name = f"{base_name}.edf"

    try:
        tracker.openDataFile(edf_name)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to open EDF file '{edf_name}': {e}")

    # Preamble (free-text, stored inside the EDF for provenance)
    tracker.sendCommand(f"add_file_preamble_text 'Participant: {participant_id}'")
    tracker.sendCommand("add_file_preamble_text 'Experiment: polygon_center_bias'")
    tracker.sendCommand(f"add_file_preamble_text 'Local EDF dir: {edf_dir}'")

    return edf_name


def configure_tracker(tracker, screen_width_px, screen_height_px,
                      calibration_type="HV9", binocular=True):
    """Configure tracker screen coords, data filters and calibration type.

    Coordinates use a top-left origin (0,0) matching Pygame's surface space,
    so live gaze samples can be compared directly to Pygame draw coordinates.

    Parameters
    ----------
    tracker : pylink.EyeLink
    screen_width_px, screen_height_px : int
        Full-screen resolution in pixels.
    calibration_type : str
        One of HV3 / HV5 / HV9 / HV13 (default HV9).
    binocular : bool
        Record both eyes if True, else left eye only.
    """
    # Make sure the host is idle before sending setup commands.
    tracker.setOfflineMode()
    pylink.pumpDelay(100)

    # Screen pixel coordinates (top-left origin) + Data Viewer display coords.
    coords = f"0 0 {screen_width_px - 1} {screen_height_px - 1}"
    tracker.sendCommand(f"screen_pixel_coords = {coords}")
    tracker.sendMessage(f"DISPLAY_COORDS {coords}")

    # Calibration geometry.
    tracker.sendCommand(f"calibration_type = {calibration_type}")
    tracker.sendCommand("automatic_calibration_pacing = 1000")

    # What is written to the EDF file.
    tracker.sendCommand(
        "file_sample_data = LEFT,RIGHT,GAZE,AREA,GAZERES,HREF,PUPIL,STATUS,INPUT"
    )
    tracker.sendCommand(
        "file_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT"
    )

    # What is streamed over the link (used by the live gaze-gated fixation check).
    tracker.sendCommand("link_sample_data = LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS")
    tracker.sendCommand("link_event_filter = LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON")

    # Saccade/fixation parser thresholds (cognitive defaults).
    tracker.sendCommand("saccade_velocity_threshold = 30")
    tracker.sendCommand("saccade_acceleration_threshold = 8000")

    # Binocular vs monocular.
    if binocular:
        tracker.sendCommand("binocular_enabled = YES")
    else:
        tracker.sendCommand("binocular_enabled = NO")


def open_calibration_graphics(tracker, screen_width_px, screen_height_px):
    """Open pylink's built-in SDL/pygame calibration graphics.

    This must be called before do_calibration(). It opens (or takes over) the
    full-screen pygame display used both for calibration targets and, via
    pygame.display.get_surface(), for drawing the experiment stimuli.

    Returns
    -------
    pygame.Surface
        The full-screen display surface to blit stimuli onto.
    """
    import pygame

    # openGraphics sets up a fullscreen pygame display at the given resolution
    # and wires it into pylink for camera-setup / calibration / drift display.
    pylink.openGraphics((screen_width_px, screen_height_px), 32)

    # Use a clear beep set for calibration feedback (target onset, good, error).
    try:
        pylink.setCalibrationSounds("", "", "")
    except Exception:
        pass

    return pygame.display.get_surface()


def do_calibration(tracker, exp_clock):
    """Run camera setup, calibration and validation (blocking).

    doTrackerSetup() shows the EyeLink camera-setup screen. The experimenter
    presses 'C' to calibrate, 'V' to validate, and 'O'/Enter to exit and begin
    the experiment. Calibration graphics must already be open.

    Returns
    -------
    dict
        {'result': 'PASS' | 'ABORT', 'ts_start': float, 'ts_end': float}
    """
    ts_start = exp_clock.getTime()
    tracker.setOfflineMode()
    pylink.pumpDelay(100)

    tracker.sendMessage(f"CALIBRATION_START {ts_start:.3f}")

    try:
        tracker.doTrackerSetup()
        result = "PASS"
    except RuntimeError as e:
        print(f"Calibration aborted/error: {e}")
        try:
            tracker.exitCalibration()
        except Exception:
            pass
        result = "ABORT"

    ts_end = exp_clock.getTime()
    tracker.sendMessage(f"CALIBRATION_END {ts_end:.3f} result={result}")
    return {"result": result, "ts_start": ts_start, "ts_end": ts_end}


def start_recording(tracker, exp_clock):
    """Begin recording samples+events to EDF and over the link.

    Returns the experiment-clock timestamp when recording started.
    """
    # (file_samples, file_events, link_samples, link_events) all enabled.
    error = tracker.startRecording(1, 1, 1, 1)
    if error != 0:
        raise RuntimeError(f"startRecording failed, error code: {error}")

    # Let the recording stabilise (SR Research recommendation).
    pylink.pumpDelay(100)

    ts = exp_clock.getTime()
    tracker.sendMessage(f"RECORDING_START {ts:.3f}")
    return ts


def stop_recording(tracker, exp_clock):
    """Stop recording. Returns the experiment-clock timestamp."""
    ts = exp_clock.getTime()
    tracker.sendMessage(f"RECORDING_STOP {ts:.3f}")
    # Flush any pending data before stopping.
    pylink.pumpDelay(100)
    tracker.stopRecording()
    pylink.pumpDelay(50)
    return ts


def _get_gaze(tracker):
    """Return the newest valid (x, y) gaze sample, or None.

    Prefers whichever eye reports a sample; for binocular data the right eye is
    used if present, else the left.
    """
    sample = tracker.getNewestSample()
    if sample is None:
        return None

    gaze = None
    if sample.isRightSample():
        gaze = sample.getRightEye().getGaze()
    elif sample.isLeftSample():
        gaze = sample.getLeftEye().getGaze()

    if gaze is None or gaze[0] == pylink.MISSING_DATA or gaze[1] == pylink.MISSING_DATA:
        return None
    return gaze[0], gaze[1]


def wait_for_fixation_gaze(tracker, target_x, target_y, exp_clock,
                           fixation_window_px=100.0,
                           required_duration_ms=300.0,
                           max_wait_s=10.0,
                           pygame_events_fn=None):
    """Wait until gaze is held on (target_x, target_y), with manual override.

    The participant's gaze must stay within `fixation_window_px` of the target
    for `required_duration_ms` to auto-advance. The experimenter may at any time
    press SPACE to accept manually, or Q/ESC to abort. Coordinates are in
    top-left-origin pixels (same space as the displayed fixation cross).

    Parameters
    ----------
    tracker : pylink.EyeLink
    target_x, target_y : float
        Fixation target location in screen pixels.
    exp_clock : ExpClock
    fixation_window_px : float
        Acceptance radius around the target.
    required_duration_ms : float
        Stable dwell time needed to auto-accept.
    max_wait_s : float
        Hard timeout.
    pygame_events_fn : callable or None
        Function returning a list of pygame events to scan for SPACE/Q/ESC.
        Typically `pygame.event.get`. If None, only gaze gating is used.

    Returns
    -------
    tuple (str, float)
        (outcome, timestamp) where outcome is one of FIXATION_GAZE,
        FIXATION_MANUAL, FIXATION_ABORT, FIXATION_TIMEOUT.
    """
    import pygame

    ts_start = exp_clock.getTime()
    tracker.sendMessage(
        f"FIXATION_CHECK_START {ts_start:.3f} target=({target_x:.1f},{target_y:.1f})"
    )

    fixation_start_time = None

    while (exp_clock.getTime() - ts_start) < max_wait_s:
        # --- Manual override / abort via keyboard ---
        if pygame_events_fn is not None:
            for event in pygame_events_fn():
                if event.type == pygame.QUIT:
                    ts = exp_clock.getTime()
                    tracker.sendMessage(f"FIXATION_CHECK_ABORT {ts:.3f}")
                    return FIXATION_ABORT, ts
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        ts = exp_clock.getTime()
                        tracker.sendMessage(f"FIXATION_CHECK_MANUAL {ts:.3f}")
                        return FIXATION_MANUAL, ts
                    elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                        ts = exp_clock.getTime()
                        tracker.sendMessage(f"FIXATION_CHECK_ABORT {ts:.3f}")
                        return FIXATION_ABORT, ts

        # --- Gaze gating ---
        gaze = _get_gaze(tracker)
        if gaze is not None:
            gx, gy = gaze
            dist = ((gx - target_x) ** 2 + (gy - target_y) ** 2) ** 0.5
            if dist < fixation_window_px:
                now_ms = exp_clock.getTime() * 1000.0
                if fixation_start_time is None:
                    fixation_start_time = now_ms
                elif (now_ms - fixation_start_time) >= required_duration_ms:
                    ts = exp_clock.getTime()
                    tracker.sendMessage(f"FIXATION_CHECK_PASS {ts:.3f}")
                    return FIXATION_GAZE, ts
            else:
                fixation_start_time = None  # left the window, restart dwell

        pylink.msecDelay(1)

    ts = exp_clock.getTime()
    tracker.sendMessage(f"FIXATION_CHECK_TIMEOUT {ts:.3f}")
    return FIXATION_TIMEOUT, ts


def close_tracker(tracker, edf_name, local_edf_path, exp_clock=None):
    """Close the EDF file, pull it from the host, and close the connection.

    Parameters
    ----------
    tracker : pylink.EyeLink
    edf_name : str
        EDF filename on the host (from setup_edf).
    local_edf_path : str
        Full local path to copy the EDF to.
    exp_clock : ExpClock or None
        If given, a SESSION_END message is timestamped.
    """
    if tracker is None:
        return

    try:
        if exp_clock is not None:
            tracker.sendMessage(f"SESSION_END {exp_clock.getTime():.3f}")
    except Exception as e:
        print(f"Warning: could not send SESSION_END: {e}")

    # Make sure recording is stopped before closing the file.
    try:
        tracker.setOfflineMode()
        pylink.pumpDelay(100)
    except Exception:
        pass

    try:
        tracker.closeDataFile()
        print(f"Retrieving EDF '{edf_name}' -> {local_edf_path} ...")
        tracker.receiveDataFile(edf_name, str(local_edf_path))
        print("EDF retrieved successfully.")
    except Exception as e:
        print(f"Warning: error retrieving EDF file: {e}")

    try:
        tracker.close()
    except Exception as e:
        print(f"Warning: error closing tracker: {e}")

    # Close pylink calibration graphics if they were opened.
    try:
        pylink.closeGraphics()
    except Exception:
        pass
