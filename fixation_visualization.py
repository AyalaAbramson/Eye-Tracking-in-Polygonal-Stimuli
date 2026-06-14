"""
Visualize eye-tracking fixations overlaid on target polygon stimuli.

All trials are identical across participants, so the same `target_trial` can be
compared across sessions. The module exposes two visualization modes:

    - plot_single_subject(session_folder, target_trial)
    - plot_aggregated_subjects(root_dir, target_trial)

Time synchronization between the EyeLink clock (ASC file) and the experiment
clock (CSV) is performed using the first ``TRIAL_START`` sync message.
"""

import os
import glob
import json

import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def parse_polygon_str(poly_str):
    """Parse a 'x,y;x,y;...' polygon string into a list of (x, y) tuples."""
    if pd.isna(poly_str) or not poly_str:
        return []
    points = []
    for pair in str(poly_str).split(';'):
        if ',' in pair:
            x, y = map(float, pair.split(','))
            points.append((x, y))
    return points


def _resolve_asc_path(session_folder):
    """Return the path to the single .asc file inside the session's edf folder."""
    edf_dir = os.path.join(session_folder, 'edf')
    asc_files = glob.glob(os.path.join(edf_dir, '*.asc'))
    if not asc_files:
        raise FileNotFoundError(f"No .asc file found in {edf_dir}")
    return asc_files[0]


def _read_time_offset(asc_file_path):
    """
    Compute the EyeLink->experiment clock offset from the first TRIAL_START msg.

    Message format:  MSG <eyelink_ms> TRIAL_START <exp_clock_s> index=N type=...

        time_offset = (eyelink_ms / 1000.0) - exp_clock_s
    """
    with open(asc_file_path, 'r') as f:
        for line in f:
            if 'TRIAL_START' not in line:
                continue
            parts = line.split()
            # parts: ['MSG', '<eyelink_ms>', 'TRIAL_START', '<exp_clock_s>', ...]
            try:
                eyelink_ms = float(parts[1])
                exp_clock_s = float(parts[3])
            except (IndexError, ValueError):
                continue
            return (eyelink_ms / 1000.0) - exp_clock_s
    raise ValueError(f"No TRIAL_START message found in {asc_file_path}")


def _place_polygon(polygon, offset):
    """
    Map polygon vertices from the 1100x1100 image space onto the screen by
    translation only (Offset Mapping) -- no scaling/stretching.

    The polygon is authored in image space (IMAGE_SIZE in run_experiment.py) and
    the stimulus image is blitted at its top-left corner on screen, so adding
    that offset lands the polygon in the same screen-pixel coordinate system as
    the fixations while preserving its native size and aspect ratio.
    """
    offset_x, offset_y = offset
    return [(x + offset_x, y + offset_y) for x, y in polygon]


def _load_trial_row(session_folder, target_trial):
    """Return the CSV row (Series) for `target_trial`, or None if absent."""
    trials_csv_path = os.path.join(session_folder, 'trials.csv')
    df = pd.read_csv(trials_csv_path)
    df = df[df['trial_index'].notna()].copy()
    df['trial_index'] = df['trial_index'].astype(int)

    trial_data = df[df['trial_index'] == target_trial]
    if trial_data.empty:
        return None
    return trial_data.iloc[0]


# --------------------------------------------------------------------------- #
# Core extraction
# --------------------------------------------------------------------------- #
def extract_valid_fixations(session_folder, target_trial):
    """
    Extract time-synced, in-window fixations for `target_trial` in a session.

    Steps:
        1. Read stim window (stim_on_ts_s, stim_off_ts_s) and polygon from CSV.
        2. Compute the clock offset from the first TRIAL_START message.
        3. Parse EFIX lines, align each fixation start to the CSV clock:
               aligned_start_s = (fixation_start_ms / 1000.0) - time_offset
        4. Keep only fixations whose aligned_start_s is within the stim window.

    Returns a dict with keys:
        'x', 'y'            -> lists of fixation coordinates (image space)
        'polygon'           -> list of (x, y) vertices
        'base_centroid'     -> (stim_center_x_px, stim_center_y_px) from the CSV
        'stim_on', 'stim_off'
        'time_offset'
    or None if the trial is not present in the CSV.
    """
    trial_row = _load_trial_row(session_folder, target_trial)
    if trial_row is None:
        return None

    stim_on = float(trial_row['stim_on_ts_s'])
    stim_off = float(trial_row['stim_off_ts_s'])
    polygon = parse_polygon_str(trial_row['polygon_points_imgspace'])

    # Offset Mapping: translate the polygon from image space to its on-screen
    # position (stimulus top-left) so it aligns with the fixations, undistorted.
    stim_offset = (float(trial_row['stim_top_left_x_px']),
                   float(trial_row['stim_top_left_y_px']))
    polygon = _place_polygon(polygon, stim_offset)

    # Base centroid: the intended stimulus center recorded in the CSV. Already
    # in screen pixels, so no offset mapping is needed.
    base_centroid = (float(trial_row['stim_center_x_px']),
                     float(trial_row['stim_center_y_px']))

    asc_file_path = _resolve_asc_path(session_folder)
    time_offset = _read_time_offset(asc_file_path)

    fixations_x = []
    fixations_y = []

    with open(asc_file_path, 'r') as f:
        for line in f:
            if not line.startswith('EFIX'):
                continue
            parts = line.split()
            # EFIX R  start_ms  end_ms  dur_ms  x_px  y_px  pupil
            if len(parts) < 7:
                continue
            try:
                fixation_start_ms = float(parts[2])
                x = float(parts[5])
                y = float(parts[6])
            except ValueError:
                # Skip rows with missing/corrupt samples (e.g. '.')
                continue

            aligned_start_s = (fixation_start_ms / 1000.0) - time_offset
            if stim_on <= aligned_start_s <= stim_off:
                fixations_x.append(x)
                fixations_y.append(y)

    return {
        'x': fixations_x,
        'y': fixations_y,
        'polygon': polygon,
        'base_centroid': base_centroid,
        'stim_on': stim_on,
        'stim_off': stim_off,
        'time_offset': time_offset,
    }


def find_session_folders(root_dir):
    """
    Return every session folder under `root_dir`.

    A session folder is any directory that directly contains a 'trials.csv'.
    This handles the root/participant_*/session_*/ layout as well as sessions
    placed directly under the root.
    """
    sessions = []
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        if 'trials.csv' in filenames:
            sessions.append(dirpath)
    return sorted(sessions)


# --------------------------------------------------------------------------- #
# Plotting helpers
# --------------------------------------------------------------------------- #
def _draw_polygon(ax, polygon):
    """Draw polygon outline + light fill, and return its centroid (x, y)."""
    if not polygon:
        return None

    px, py = zip(*polygon)
    px_closed = list(px) + [px[0]]
    py_closed = list(py) + [py[0]]
    ax.plot(px_closed, py_closed, color='#2C3E50', linewidth=2.5,
            label='Polygon boundary', zorder=2)
    ax.fill(px_closed, py_closed, color='#3498DB', alpha=0.15,
            label='Polygon interior', zorder=1)

    if len(polygon) >= 3:
        centroid = Polygon(polygon).centroid
        return (centroid.x, centroid.y)
    return None


def _draw_centroid(ax, actual_centroid, base_centroid,
                   show_actual=True, show_base=True):
    """Plot the polygon centroid(s) on top of everything else.

    actual_centroid : geometric center of the drawn polygon (yellow dot).
    base_centroid   : intended stimulus center from the CSV (black dot).
    Use show_actual / show_base to toggle which markers are drawn. Both use
    the same marker size.
    """
    size = 20
    if show_actual and actual_centroid is not None:
        ax.scatter([actual_centroid[0]], [actual_centroid[1]], color='#F1C40F',
                   s=size, marker='o', edgecolors='black', linewidths=2.0,
                   label='Actual centroid', zorder=11)
    if show_base and base_centroid is not None:
        ax.scatter([base_centroid[0]], [base_centroid[1]], color='black',
                   s=size, marker='o', edgecolors='black', linewidths=2.0,
                   label='Base centroid', zorder=11)


def _format_axes(ax, title):
    """Apply shared image-space formatting (inverted Y, fixed limits)."""
    ax.set_title(title, fontsize=14, pad=15)
    ax.set_xlabel('X coordinate (pixels)', fontsize=11)
    ax.set_ylabel('Y coordinate (pixels)', fontsize=11)
    ax.set_xlim(0, 2560)
    ax.set_ylim(1440, 0)          # invert Y: (0,0) at the top-left
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='upper right', frameon=True, shadow=True)


# --------------------------------------------------------------------------- #
# Mode A: single subject
# --------------------------------------------------------------------------- #
def plot_single_subject(session_folder, target_trial,
                        show_actual=True, show_base=True):
    """Plot the polygon + valid fixations for one participant / one trial.

    show_actual / show_base toggle the actual (polygon) and base (CSV) centroids.
    """
    data = extract_valid_fixations(session_folder, target_trial)
    if data is None:
        print(f"Trial {target_trial} not found in {session_folder}")
        return

    print(f"[single] {os.path.basename(session_folder)}: "
          f"{len(data['x'])} valid fixations "
          f"(offset={data['time_offset']:.3f}s)")

    fig, ax = plt.subplots(figsize=(9, 9))
    centroid = _draw_polygon(ax, data['polygon'])

    if data['x']:
        ax.scatter(data['x'], data['y'], color='#2ECC71', s=70, alpha=0.85,
                   edgecolors='white', label='Fixations', zorder=5)

    _draw_centroid(ax, centroid, data['base_centroid'],
                   show_actual=show_actual, show_base=show_base)
    _format_axes(ax, f"Fixations - Trial {target_trial}\n"
                     f"{os.path.basename(session_folder)}")
    plt.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- #
# Mode B: aggregated subjects
# --------------------------------------------------------------------------- #
def plot_aggregated_subjects(root_dir, target_trial,
                             show_actual=True, show_base=True):
    """
    Plot valid fixations for `target_trial` across ALL sessions under root_dir.

    The polygon is identical across participants, so the first session that
    provides one defines the drawn polygon and centroids. Low scatter alpha
    reveals fixation density where points overlap. show_actual / show_base
    toggle the actual (polygon) and base (CSV) centroids.
    """
    sessions = find_session_folders(root_dir)
    if not sessions:
        print(f"No session folders found under {root_dir}")
        return

    all_x = []
    all_y = []
    polygon = []
    base_centroid = None
    n_sessions = 0

    for session_folder in sessions:
        data = extract_valid_fixations(session_folder, target_trial)
        print(f"Session {session_folder} - Center: {data['base_centroid']}")
        if data is None:
            continue
        n_sessions += 1
        all_x.extend(data['x'])
        all_y.extend(data['y'])
        if not polygon and data['polygon']:
            polygon = data['polygon']
        if base_centroid is None:
            base_centroid = data['base_centroid']
        print(f"[agg] {os.path.basename(session_folder)}: "
              f"{len(data['x'])} valid fixations")

    print(f"[agg] {len(all_x)} fixations from {n_sessions} sessions "
          f"for trial {target_trial}")

    fig, ax = plt.subplots(figsize=(9, 9))
    centroid = _draw_polygon(ax, polygon)

    if all_x:
        ax.scatter(all_x, all_y, color='#E74C3C', s=55, alpha=0.25,
                   edgecolors='none',
                   label=f'Fixations ({n_sessions} subjects)', zorder=5)

    _draw_centroid(ax, centroid, base_centroid,
                   show_actual=show_actual, show_base=show_base)
    _format_axes(ax, f"Aggregated fixations - Trial {target_trial}\n"
                     f"{n_sessions} subjects")
    plt.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    root_dir = r'C:\Users\User\Desktop\Analysis\data\raw'
    target_trial = 3

    # Mode A: a single session (one participant).
    example_session = os.path.join(
        root_dir, 'participant_315328062', 'session_20260611_153617')
    #plot_single_subject(example_session, target_trial)

    # Mode B: every session under the root directory.
    plot_aggregated_subjects(root_dir, target_trial)


if __name__ == '__main__':
    main()
