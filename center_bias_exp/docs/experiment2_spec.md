Below is a **complete coding guide** for `experiment2_runner` that a code‑generation tool can implement directly. It integrates your latest design: 27 polygons, CAT2000 subset, 2 parts × 9 mini‑blocks × 39 trials, calibration+validation before each block, memory probe + 1‑min break after each block, and rich logging in both px and deg for robust analysis.[1][2][3]

***

## 1. High‑level behavior

`experiment2_runner.py` is a **pure Python script** (no Builder) that:

- Reads pre‑computed `stimulus_manifest.csv`, `memory_manifest.csv`, `polygon_geometry.csv`.  
- Sets up a 27" 4K PsychoPy window (3840×2160, `units='pix'`), viewing distance 70 cm.  
- Connects to an EyeLink 1000 (fixed head, 1000 Hz, default parsing filters).[1]
- For each participant and part (A/B):  
  - Runs **9 mini‑blocks** of **39 trials** each (36 masked images + 3 empty polygons).  
  - For each block: Calibration+validation → trials → memory probe → 1‑minute break.  
- Logs **everything** needed for analysis:
  - Full EDF gaze data at 1000 Hz with rich messages + AOIs.  
  - Trial‑, block‑, and session‑level CSVs including geometry, cue, timing, drift, calibration metrics, memory results, etc., in **both px and deg** where relevant.[3]

***

## 2. File & folder structure (code expectations)

The runner assumes the repo layout:

```text
center_bias_exp/
  config/
    experiment_config.yaml
  manifests/
    stimulus_manifest.csv
    memory_manifest.csv
    polygon_geometry.csv
  stimuli/
    polygons/*.json              # 27 polygon JSONs you listed
    images/CAT2000/<category>/*.jpg
  data/
    raw/                         # auto-created per session
  src/
    experiment2_runner.py
    config_loader.py
    psychopy_utils.py
    eyetracker_utils.py
    geometry_utils.py
    logging_utils.py
```

The script is run from repo root with `python src/experiment2_runner.py --participant-id P01 --part A`.

***

## 3. Configuration and manifests

### 3.1 YAML config → `load_experiment_config`

Implement `config_loader.load_experiment_config(path)`:

- Reads `experiment_config.yaml` (template given in previous message).  
- Returns nested dict `cfg` with keys: `experiment`, `screen`, `eyelink`, `drift_gate`, `aoi`, `paths`, `logging`.[2]

### 3.2 Manifests & geometry → `load_manifests`

`config_loader.load_manifests(cfg)`:

- Loads `stimulus_manifest.csv`, `memory_manifest.csv`, `polygon_geometry.csv` with `pandas.read_csv`.  
- Validates required columns:
  - Stimulus manifest: identity, polygon/image fields, cue + timing fields.  
  - Memory manifest: participant/part/block + probe info.  
  - Geometry table: centers etc. keyed by `polygon_id`.  
- Returns `(stim_df, mem_df, geom_df)`.

***

## 4. Geometry utilities

`geometry_utils.py` provides conversions and polygon transforms, using screen config (`screen_cfg`) from YAML.

### 4.1 px↔deg conversion

Given:

- width in cm, height in cm, viewing distance in cm, resolution in px.[4][5]

Implement:

```python
def deg2pix_x(deg, screen_cfg) -> float
def deg2pix_y(deg, screen_cfg) -> float
def pix2deg_x(px, screen_cfg) -> float
def pix2deg_y(px, screen_cfg) -> float
```

Use standard visual angle formula:  
\(\text{size_cm} = 2 \cdot d \cdot \tan(\theta/2)\); convert from px via cm/px scaling.[5][4]

### 4.2 Polygon center transform

`apply_polygon_transform(geom_row, aperture_scale_factor, screen_cfg) -> dict`:

- Inputs:
  - `geom_row`: row from `geom_df` with canonical center coordinates in px/deg.  
  - `aperture_scale_factor`: float from manifest (1.0 if no extra scaling).  
  - `screen_cfg`: dict with resolution, width, height, distance.  
- Behavior:
  - Multiplies canonical px centers by `aperture_scale_factor`.  
  - Translates centers to **screen center** (i.e., adds `(W/2, H/2)` in px).  
  - Computes deg equivalents using `pix2deg_x/y`.  
  - Computes:
    - For each K ∈ {com, chc, bbc, icc}:
      - `center_<K>_x_px`, `center_<K>_y_px`, `center_<K>_x_deg`, `center_<K>_y_deg`.  
      - `dist_center_<K>_to_screen_deg`, `angle_center_<K>_to_screen_deg`.  
    - Screen center fields:
      - `center_screen_x_px = W/2`, `center_screen_y_px = H/2`.  
      - `center_screen_x_deg = 0`, `center_screen_y_deg = 0`.  
- Returns dict to be merged into trial row.

***

## 5. PsychoPy utilities

### 5.1 Monitor and window

`psychopy_utils.create_monitor_and_window(screen_cfg) -> (monitor, win)`:

- Build `Monitor` with:
  - width (cm) = `screen_cfg["width_cm"]`, distance (cm) = `screen_cfg["viewing_distance_cm"]`.  
  - `setSizePix(resolution_px)`.  
- Create `Window`:

```python
win = visual.Window(
    size=screen_cfg["resolution_px"],
    monitor=monitor,
    units='pix',
    fullscr=True,
    color=[gray, gray, gray],
    allowGUI=False
)
```

Where `gray = screen_cfg["background_gray"]`.[2][4]

### 5.2 Basic drawing helpers

- `draw_instructions(win, text)`:
  - Draw centered `TextStim`, wait for key (e.g., `space`).  
- `draw_fixation_cue(win, x_px, y_px, size_px)`:
  - Draw a small `Circle` or `ShapeStim` at given px coords.  
- Stimulus prep:
  - `prepare_polygon_shape(win, polygon_vertices_px, line_color, fill_color)` → returns `ShapeStim`.  
  - `prepare_masked_image(win, image_path, polygon_mask)` → returns `ImageStim` with `mask` or alpha channel.  

Implementation details (how JSON stores vertices, how masks are constructed) can be filled by the coding tool; runner only needs consistent function signatures.

***

## 6. EyeLink utilities

### 6.1 Connect and EDF setup

`eyetracker_utils.connect_eyelink(cfg) -> tracker`:

- Uses `pylink.EyeLink()` with optional `address`.[6][1]

`setup_edf(tracker, participant_id, part, edf_dir) -> edf_name`:

- EDF name pattern: `<participant_id>_<part>.edf` (max 8 chars; consider compacting).  
- `tracker.openDataFile(edf_name)`; create `edf_dir` in session folder.

### 6.2 Tracker configuration

`configure_tracker(tracker, cfg, screen_cfg)`:

- Sets:
  - `screen_pixel_coords` and `DISPLAY_COORDS` from (0,0) to (W-1,H-1).  
  - `screen_phys_coords` in mm as left, top, right, bottom around 0.[7]
  - `screen_distance` in mm.  
  - `sample_rate = 1000`.  
  - `binocular_enabled` based on config.  
  - sample/event filters from YAML (`file_sample_data`, etc.).  
  - parser thresholds (`saccade_velocity_threshold`, etc.) as YAML values.  
  - `calibration_type = HV9`.  
  - `recording_parse_type = GAZE`.  

All commands also stored into `session_metadata.json` for reproducibility.

### 6.3 Calibration & validation loop

`run_calibration_and_validation(tracker, graphics_env, cfg, expClock, block_id) -> dict`:

- Loops until validation passes thresholds in `analysis_config.yaml` or experimenter aborts.[8]
- Logs EyeLink messages:
  - `"CALIB_START block=<id> attempt=<k>"`, `"CALIB_END ... RMS=<...> MAX=<...> PASS=<0/1>"`.  
- Returns:
  - `calibration_attempts`, `validation_rms_best`, `validation_max_err_best`, `ts_calib_start_first`, `ts_calib_end_last`.

### 6.4 Recording and drift helpers

- `start_recording(tracker, expClock) -> ts_recording_start`:
  - `tracker.setOfflineMode()` then `tracker.startRecording(1, 1, 1, 1)`; wait 100 ms; get `expClock.getTime()`.  
- `stop_recording(tracker, expClock) -> ts_recording_stop`:
  - `tracker.stopRecording()`; optional small wait; return `expClock.getTime()`.  

- `drift_correction_builtin(tracker, cue_x, cue_y, expClock) -> (success_bool, ts_drift_end)`:
  - Calls `doDriftCorrect(cue_x, cue_y, 1, 1)`; sets boolean based on return code; `ts_drift_end = expClock.getTime()`.  

- `drift_correction_gaze_gate(...)`:
  - Only used if `cfg["drift_gate"]["use_builtin"]=False`; implements gaze‑contingent fixation gate with radius/dwell/max_time from YAML.

***

## 7. Logging utilities

### 7.1 Session paths

`logging_utils.init_session_paths(cfg, participant_id, part) -> paths_dict`:

- Creates folder:

```text
data/raw/participant_<ID>/part_<A|B>/session_<YYYYmmdd_HHMMSS>/
  edf/
  logs_trial/
  logs_block/
  logs_session/
  logs_memory/
```

- Returns dict with paths to each subfolder.

### 7.2 Writers

- `init_trial_logger(path) -> (file_handle, csv_writer)`  
- `init_block_logger(path) -> ...`  
- `init_memory_logger(path) -> ...`  
- Writers write header row at first call; all rows are dicts with consistent keys.

### 7.3 Session metadata

`logging_utils.write_session_metadata(path, metadata_dict)`:

- JSON with:
  - participant, part, session timestamp.  
  - config snapshot (`screen`, `eyelink`, `drift_gate`, `aoi`).  
  - manifest filenames and optional git hashes.  
  - EyeLink commands actually sent.

***

## 8. Main runner: `experiment2_runner.py`

### 8.1 CLI and setup

1. Parse args:
   - `--participant-id`, `--part` (`A` or `B`), `--config` (optional).  
2. `cfg = load_experiment_config(config_path)`.  
3. `stim_df, mem_df, geom_df = load_manifests(cfg)`.  
4. Filter manifests:
   - `stim_part = stim_df[(participant_id, part)]`  
   - `mem_part = mem_df[(participant_id, part)]`.  
5. `(monitor, win) = create_monitor_and_window(cfg["screen"])`.  
6. `expClock = core.Clock()` (starts at 0).  
7. Create session paths and open CSV writers.  
8. Connect to EyeLink, open EDF, configure tracker, set up graphics env.  
9. Write session_metadata JSON.  
10. Show instructions; wait for experimenter key; send `SESSION_START` message.

### 8.2 Block loop (9 mini‑blocks × 39 trials)

For `mini_block` in `1..9`:

```python
stim_block_df = stim_part[stim_part["mini_block"] == mini_block].sort_values("trial_in_block")
mem_row = mem_part[mem_part["mini_block"] == mini_block].iloc[0]
run_block(mini_block, stim_block_df, mem_row, ...)
```

***

## 9. Block implementation: `run_block(...)`

### 9.1 Block structure

1. `block_start_ts = expClock.getTime()`.  
2. `calib_info = run_calibration_and_validation(...)`.  
3. Initialize counters:
   - `n_trials_planned = len(stim_block_df)` (assert =39).  
   - `n_trials_completed = 0`, `n_trials_aborted = 0`, `n_recalibrations = 0`.  
4. For each trial row:  
   - `trial_result = run_single_trial(...)`.  
   - Update counters based on `trial_result["aborted_trial"]` and `["recalibrated"]`.  
5. `mem_result = run_memory_probe(mem_row, ...)`.  
6. `break_result = run_timed_break(mini_block, 60.0, win, expClock)`.  
7. `block_end_ts = expClock.getTime()`.  
8. Write block CSV row containing:
   - identity (participant, part, mini_block).  
   - counts and calibration metrics.  
   - `mem_result` (probe image, response, RT, correctness).  
   - `break_duration_planned_s=60`, `break_duration_actual_s`.  
   - `block_start_ts`, `block_end_ts`, `block_duration_s`.

***

## 10. Trial implementation: `run_single_trial(...)`

Key responsibilities: **start/stop recording**, **send EyeLink messages**, **display cue & stimulus**, **perform drift correction**, **log detailed trial row**.

### 10.1 Setup

1. `trialClock = core.Clock(); trialClock.reset()`.  
2. `ts_trial_start = expClock.getTime()`.  
3. Extract row variables (identity, polygon_id, image, cue, timing).  
4. `geom_row = geom_df.loc[polygon_id]`.  
5. `geom_info = apply_polygon_transform(geom_row, aperture_scale_factor, screen_cfg)`.  
6. Compute AOI radius px from `cfg["aoi"]["radius_deg"]` via `deg2pix_x/y`.  

### 10.2 Start EyeLink recording

1. `ts_recording_start = start_recording(tracker, expClock)`.  
2. Send:

```python
tracker.sendMessage(f"TRIALID {trial_uid}")
tracker.sendMessage("TRIAL_START mini_block=%d trial_in_block=%d" % (...))
# TRIAL_VAR messages
...
```

3. Send AOI definitions for CoM, CHC, BBC, ICC, and screen center:

```python
aoi_id = 1
for label, (x, y) in centers_px.items():
    tracker.sendMessage(f"!V IAREA CIRCLE {aoi_id} {label} {x:.1f} {y:.1f} {radius_px:.1f}")
    aoi_id += 1
```

### 10.3 Cue and drift

1. Draw cue at `cue_x_px, cue_y_px` on gray; `win.flip()` → `ts_cue_onset`.  
2. `tracker.sendMessage("CUE_ON")`.  
3. Run drift gate using built‑in EyeLink or custom gaze gate depending on config; get `(drift_ok_first, ts_drift_end)`.  
4. Send `"DRIFT_OK"` or `"DRIFT_FAIL"`.  

If drift fails:

- Stop recording; send `"DRIFT_FAIL_RECALIB"`.  
- Run `run_calibration_and_validation` again; increment `n_recalibrations`.  
- Restart recording; re‑send TRIAL_VARs if desired; draw cue again; re‑attempt drift once more → `drift_ok_retry`.  
- If second attempt fails:
  - `aborted_trial=True`.  
  - `tracker.sendMessage("TRIAL_RESULT ABORTED")`; `stop_recording`.  
  - Log trial row with drift fields filled but stimulus timestamps as NaN; return result dict.

### 10.4 Stimulus (if drift succeeded)

1. Prepare stimulus based on `trial_type`:
   - Load polygon vertices from JSON; scale/center to screen.  
   - For `"image"`: load CAT2000 image, apply polygon mask.  
   - For `"empty"`: draw polygon alone (filled or outline).  

2. Present stimulus:

   - Draw; `win.flip()` → `ts_stim_onset`.  
   - `tracker.sendMessage("STIM_ON")`.  
   - Keep on screen until `trialClock.getTime() >= stimulus_duration_s` (4.0 s).  

3. ITI:

   - Draw gray; `win.flip()` → `ts_stim_offset`, `ts_iti_onset`.  
   - `tracker.sendMessage("STIM_OFF")`; `tracker.sendMessage("ITI_ON")`.  
   - Show gray for `iti_s` (=0.5 s); final `win.flip()` → `ts_iti_offset`; send `"ITI_OFF"`.  

### 10.5 End of trial & logging

1. `ts_recording_stop = stop_recording(tracker, expClock)`.  
2. `tracker.sendMessage("TRIAL_RESULT OK")`.  
3. `ts_trial_end = expClock.getTime()`.  

4. Build trial row dict with:

- Identity: `participant_id`, `part`, `session_timestamp`, `mini_block`, `trial_in_block`, `trial_uid`.  
- Stimulus: `trial_type`, `polygon_id`, `polygon_case`, `polygon_json_path`, `image_id`, `category`, `bias_level`, `image_path`, `aperture_scale_factor`.  
- Cue: `cue_pos_id`, `cue_x_px`, `cue_y_px`, `cue_x_deg`, `cue_y_deg`.  
- Drift: mode, `drift_window_radius_px/deg`, `dwell_time_ms`, `max_drift_time_s`, `drift_ok_first`, `recalibrated`, `drift_ok_retry`, `aborted_trial`, `validation_rms_before_trial`, `validation_max_err_before_trial`.  
- Geometry: all centers px/deg, distances/angles (from `geom_info`).  
- Timing: `ts_trial_start`, `ts_recording_start`, `ts_cue_onset`, `ts_drift_end`, `ts_stim_onset`, `ts_stim_offset`, `ts_iti_onset`, `ts_iti_offset`, `ts_recording_stop`, `ts_trial_end`.  

5. `log_trial_row(trial_writer, trial_row_dict)`; flush if configured.  

6. Return `{"aborted_trial": aborted_trial, "recalibrated": recalibrated}`.

***

## 11. Memory probe and breaks

### 11.1 Memory probe

`run_memory_probe(mem_row, tracker, win, expClock, memory_writer)`:

1. `ts_mem_start`; `tracker.sendMessage("MEMORY_PROBE_START block=%d" % mini_block)`.  
2. Present `probe_image` full‑screen for `probe_duration_s` (3 s):
   - `ts_probe_onset`, `ts_probe_offset`; `MEM_PROBE_ON/OFF` messages.  
3. Show `"Did you see this image in the last block? (Y/N)"`; `memClock.reset()`.  
4. Wait for `y` or `n`; get `rt_s`.  
5. Compute `is_correct` if `is_old` given.  
6. Send `MEM_RESP key=<...> rt=<...> correct=<0/1>`.  
7. `ts_mem_end = expClock.getTime()`.  
8. Log row: participant, part, mini_block, probe identifiers, `is_old`, `response_key`, `rt_s`, `is_correct`, `ts_mem_start`, `ts_mem_end`.  
9. Return minimal summary dict for block log (e.g., `{"response_key":..., "rt_s":..., "is_correct":...}`).

### 11.2 Timed break

`run_timed_break(mini_block, planned_duration_s, win, expClock)`:

- `breakClock.reset()`, `ts_break_start`.  
- Show countdown text each frame; allow experimenter key (e.g., `space`) to end break early.[9]
- `ts_break_end` when time elapsed or key pressed; `break_duration_actual_s = ts_break_end - ts_break_start`.  
- Optionally send `BREAK_START/END` messages to EyeLink.  
- Return `break_duration_actual_s`.

***

## 12. “More is better” logging guarantee

The above plan ensures:

- EDF contains full **1000 Hz** samples, default EyeLink event parsing, and a dense set of messages / AOIs for offline tools.[1]
- CSV logs capture **all metadata** needed to re‑derive:
  - position of every polygon center and cue in px & deg,  
  - distances/angles to screen center,  
  - state of calibration and drift per trial,  
  - exact timing of each event relative to a single experiment clock.  
- Redundancy (px and deg, manifest fields + geometry table + session metadata) makes analysis robust to conversion or config bugs and enables later exploratory correlations (e.g., drift success vs. polygon type, memory performance vs. center bias, etc.).[10][3]

With this guide, a coding assistant can now generate the full Python implementation of `experiment2_runner` and its helper modules in a way that is directly aligned with your experimental and analysis needs.
