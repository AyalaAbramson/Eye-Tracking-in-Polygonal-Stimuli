# Experiment Readiness Checklist

## ✅ Code Implementation (COMPLETE)
- [x] config_loader.py - Configuration and manifest loading
- [x] geometry_utils.py - Visual angle conversions and polygon transforms
- [x] logging_utils.py - Session paths and CSV logging
- [x] eyetracker_utils.py - EyeLink connection and control
- [x] psychopy_utils.py - Window, stimuli, and rendering
- [x] experiment2_runner.py - Main experiment orchestration
- [x] cue_grid.py - 9-point fixation cue grid

## ✅ Configuration Files (COMPLETE)
- [x] config/experiment_config.yaml - Screen, EyeLink, drift, AOI settings
- [x] config/analysis_config.yaml - Analysis parameters
- [x] config/logging_config.yaml - Logging configuration

## ✅ Data Files (COMPLETE)
- [x] manifests/stimulus_manifest_partA.csv (351 trials)
- [x] manifests/stimulus_manifest_partB.csv (351 trials)
- [x] manifests/memory_manifest_partA.csv (9 probes)
- [x] manifests/memory_manifest_partB.csv (9 probes)
- [x] manifests/polygon_geometry.csv (27 polygons)
- [x] docs/polygon_mapping.csv (27 polygon definitions)

## ✅ Stimulus Files (ASSUMED AVAILABLE)
- [ ] data/raw/stimuli/polygons/*.json (27 polygon files) - EXIST
- [ ] data/raw/stimuli/CAT2000/{category}/Output/*.jpg - TO BE VERIFIED

## ⚠️ Python Dependencies (TO BE INSTALLED)

### Required packages:
```bash
pip install pandas numpy pyyaml psychopy pillow
```

### EyeLink SDK (optional for testing without hardware):
```bash
# Install from SR Research or:
pip install pylink-square
```

## 🔧 Pre-Experiment Setup

### 1. Install Dependencies
```bash
cd /Users/brahan/Research/CenterBias/center_bias_exp
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify EyeLink Configuration
- Update `config/experiment_config.yaml`:
  - Set `eyelink.address` to your EyeLink IP (e.g., "100.1.1.1")
  - Or set to `null` for USB connection

### 3. Test Connectivity (without EyeLink)
```bash
python test_connectivity.py
```
This will test:
- Python imports
- Config loading
- Manifest validation
- PsychoPy window creation
- (Skip EyeLink if not connected)

### 4. Verify Stimulus Files
- Check that polygon JSON files exist in `data/raw/stimuli/polygons/`
- Ensure CAT2000 images exist or update image paths in manifests
- Or use placeholder images for testing

### 5. Run Experiment (with EyeLink)
```bash
# Part A
python src/experiment2_runner.py --participant-id P01 --part A

# Part B  
python src/experiment2_runner.py --participant-id P01 --part B
```

## 📋 Expected Output Structure

After running experiment for P01 Part A:
```
data/raw/
  participant_P01/
    part_A/
      session_20260114_143022/
        edf/
          P01_A.edf
        logs_trial/
          trials.csv (351 rows with 70+ columns)
        logs_block/
          blocks.csv (9 rows)
        logs_memory/
          memory.csv (9 rows)
        logs_session/
          session_metadata.json
```

## 🎯 Quick Start (Testing Mode)

For testing without real stimuli or EyeLink:

1. **Install minimal dependencies:**
   ```bash
   pip install pandas numpy pyyaml pillow
   ```

2. **Mock PsychoPy (optional for code testing):**
   - Comment out PsychoPy imports temporarily
   - Or install: `pip install psychopy`

3. **Validate manifests:**
   ```bash
   python -c "import pandas as pd; print(pd.read_csv('manifests/stimulus_manifest_partA.csv').info())"
   ```

## ✅ You Are Ready When:

1. ✅ All Python modules import without errors
2. ✅ Config file loads successfully
3. ✅ All manifests load with correct row counts:
   - Stimulus: 702 trials total (351 per part)
   - Memory: 18 probes total (9 per part)
   - Geometry: 27 polygons
4. ✅ PsychoPy window can be created (test_connectivity.py passes)
5. ✅ EyeLink connects (or skip for dry run)
6. ✅ At least one polygon JSON loads successfully
7. ✅ At least one test image exists (or create dummy for testing)

## 🚀 Current Status

**Code:** ✅ 100% Complete  
**Config:** ✅ 100% Complete  
**Manifests:** ✅ 100% Complete  
**Dependencies:** ⚠️ Need installation  
**Stimulus Files:** ⚠️ Need verification  

**Next Step:** Install dependencies and run connectivity test!
