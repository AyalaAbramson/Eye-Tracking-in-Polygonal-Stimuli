# Gaze-Contingent Polygon Experiment Engine

An advanced Python-based framework designed for generating customized polygon stimuli and running automated eye-tracking psychophysical experiments. Affiliated with the **Computer Vision Laboratory (ICVL)**, this project investigates human eye-movement patterns and gaze biases under gradual, parametric structural manipulations.

## 🚀 Core Features & Capabilities

* **Parametric Shape Manipulations**:
    * *Vertex Stretching*: Smoothly alter the radius of specific target vertices (Zero-Point logic ensures a flat edge at 0 stretch).
    * *Concavity Induction*: Fold specific vertices inward based on a predefined depth ratio.
    * *Spatial Rotation*: Rotate the entire geometric structure to test spatial orientations.
* **Pre-Rendering Engine**: Uses PIL (Python Imaging Library) to generate and save stimuli to a local directory prior to runtime, ensuring zero frame-drops and seamless Pygame Surface conversion during the experiment.
* **Texture Mapping**: Masks and fills polygons using high-resolution images from a local database.
* **Strict Gaze-Contingent Fixation**: Enforces visual attention using spatial (e.g., 100px radius) and temporal (e.g., 300ms dwell-time) thresholds before advancing trials.
    * *Blink & Loss Filtering*: Automatically resets fixation timers if the tracker loses the pupil or the user blinks.
* **Seamless EyeLink Integration**: Automated `TRIALID` tagging, `STIM_ON`/`STIM_OFF` precision logging, and hardware-accelerated calibration setup.
* **Virtual Dummy Mode**: Full end-to-end local testing capabilities without physical tracking hardware via simulated `pylink` objects.

## 📂 Repository Structure & Component Architecture

### 1. `run_experiment.py` (Master Script)
The central orchestrator of the pipeline:
* **Configuration**: Defines image dimensions, display timings, debug overlays, and tracker parameters.
* **Trial Building**: Generates a randomized, balanced factorial combination of all automated and manual polygon manipulations.
* **EyeLink Initialization**: Connects to the Host PC and strictly enforces the DOS-compliant 8-character `.EDF` filename limit.
* **Data Retrieval**: Automatically locks the session log upon termination and uses `receiveDataFile` to securely download the data.

### 2. `core_functions.py` (Execution Engine)
Houses the mathematical, graphical, and real-time interaction logic:
* **Stimulus Generation**: Contains the mathematical radial-angular logic for rendering polygons.
* **Main Loop (The "Sandwich" Architecture)**:
    * *Stage 1*: Tracker setup, camera stabilization, and active Gaze-Contingent fixation monitoring.
    * *Stage 2*: Screen flush, stimulus display, and exact time-zero (`STIM_ON`) synchronization.
    * *Stage 3*: Trial teardown, screen clearing, and recording pause to optimize file size.

### 3. `stimuli/` (Output Directory)
* Automatically generated folder storing high-resolution PNGs of all trials for use as background overlays in **EyeLink Data Viewer**.

## 🛠️ Execution & Setup

**Prerequisites:** * Python 3.8+
* Pygame 2.x
* NumPy & Pillow (PIL)
* SR Research EyeLink Developers Kit (`pylink`)

**Environment Configuration:**
1. Open `run_experiment.py`.
2. Toggle Hardware Mode:
    * *Laboratory Environment*: Set `TRACKER_IP = "100.1.1.1"`.
    * *Local Testing (Dummy Mode)*: Set `TRACKER_IP = None` to simulate the tracker on your personal machine.

**Running the Protocol:**
`python run_experiment.py`

**Runtime Controls:**
* SPACEBAR: Manually override fixation wait screens (crucial for Dummy Mode testing or upon severe tracking loss).
* Q or ESC: Safely abort the trial loop, clear the screen, and trigger the immediate download of the .EDF file.

## 📊 Technical Debugging Overlays

When DEBUG_MODE = True is activated in the configuration block, the engine bypasses clean visual rendering to project real-time structural data directly onto the viewport:

* 🔵 **Blue Circles**: Explicit locations of the main calibration/fixation grid.
* 🟢 **Green Circles**: Boundaries of the localized stimulus placement grid.
* 🟠 **Orange Polygons**: The theoretical regular base skeleton before structural deformation.
* 🟣 **Magenta Vectors**: Mathematical lines connecting the localized center directly to individual outer vertices.
* 🩵 **Cyan Concentric Target**: Highlights the precise index of the deformed concave vertex under investigation.