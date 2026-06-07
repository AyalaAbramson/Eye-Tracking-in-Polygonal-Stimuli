# Verification Tools Guide

Three new tools to verify the experiment is working correctly.

---

## Tool 1: Check Binocular Recording ✅

**Purpose**: Verify that the EyeLink is recording data from BOTH eyes (binocular mode).

**Usage**:
```bash
# Check an EDF file (will auto-convert to ASC)
python src/check_binocular_recording.py data/raw/participant_P01/part_A/session_*/edf/*.edf

# Or check an ASC file directly
python src/check_binocular_recording.py data/raw/participant_P01/part_A/session_*/edf/*.asc
```

**Expected Output**:
```
============================================================
BINOCULAR RECORDING CHECK RESULTS
============================================================
File: P01A.edf
Samples analyzed: 1000

Left eye data found:  YES ✓ (998 samples)
Right eye data found: YES ✓ (995 samples)

Recording mode: BINOCULAR ✓✓

✓ SUCCESS: Both eyes are being recorded!
============================================================
```

**What to Check**:
- Both "Left eye" and "Right eye" should say "YES ✓"
- Recording mode should say "BINOCULAR ✓✓"
- If you see "MONOCULAR ✗", contact me immediately

---

## Tool 2: Regenerate Stimuli with Updated Sizes

**Purpose**: Pre-render all masked images using the NEW size multipliers (3% and 1.5% boosts).

**Why**: This ensures the stimuli in your experiment match the fixed size settings.

**Usage**:
```bash
# Regenerate Part A only
python src/regenerate_stimuli.py --part A

# Regenerate Part B only
python src/regenerate_stimuli.py --part B

# Regenerate both parts
python src/regenerate_stimuli.py --all
```

**What It Does**:
- Creates pre-rendered PNG files for all masked images
- Applies the correct size multipliers:
  - Very compact shapes (iso_chc, iso_com): 1.03x (3% boost) → 2047px
  - Compact shapes (allfar_convex, iso_bbc, iso_icc): 1.015x (1.5% boost) → 2017px
  - Standard shapes: 1.0x → 1987px
- Saves to `outputs/rendered_stimuli/part_A/` and `part_B/`

**Output**:
```
============================================================
Regenerating Part A Stimuli
============================================================

Loading manifest: manifests/stimulus_manifest_partA.csv
Found 351 trials for Part A
Found 156 unique stimulus combinations

Rendering: 100%|████████████████████| 156/156 [02:15<00:00,  1.15it/s]

============================================================
Regeneration Complete
============================================================
Successfully rendered: 156
Errors: 0
Output directory: outputs/rendered_stimuli/part_A
============================================================
```

**NOTE**: This takes ~2-3 minutes per part. Be patient!

---

## Tool 3: Visual Inspection of All Stimuli 🔍

**Purpose**: Create a comprehensive visual overview of ALL stimuli at experiment scale so you can inspect them.

**Usage**:
```bash
# Inspect Part A stimuli
python src/inspect_stimuli_visual.py --part A

# Inspect and save individual shape files
python src/inspect_stimuli_visual.py --part A --save-individual

# Inspect Part B
python src/inspect_stimuli_visual.py --part B
```

**What It Creates**:

### 1. Grid Visualization
Shows all shapes side-by-side with labels:
- Shape name
- Category (Very Compact / Compact / Standard)
- Size multiplier
- Final size in pixels

File: `outputs/stimulus_inspection/part_A/part_A_stimulus_grid.png`

### 2. Summary Figure
Two plots:
- **Left**: Bar chart of shape sizes (sorted by size)
  - Blue dashed line = Base size (1987px)
  - Red dashed line = Screen height (2160px)
  - **All bars should be BELOW the red line** (no clipping!)
- **Right**: Pie chart of category distribution

File: `outputs/stimulus_inspection/part_A/part_A_summary.png`

### 3. Console Summary Table
```
============================================================
SUMMARY
============================================================
Shape                Category        Multiplier   Final Size
------------------------------------------------------------
iso_com_01           Very Compact    1.030        2047px
iso_chc_01           Very Compact    1.030        2047px
allfar_convex        Compact         1.015        2017px
iso_bbc_02           Compact         1.015        2017px
allfar_concave       Standard        1.000        1987px
...
============================================================
```

**What to Check**:
1. **No clipping**: All bars in the summary figure should be BELOW the red line (2160px)
2. **Size differences**: Very compact shapes should be slightly larger than standard shapes
3. **Categories**: Verify shapes are categorized correctly

---

## Complete Workflow for Verification

### Step 1: Run a Test Session
```bash
python src/experiment_launcher.py
```
- Complete at least 1 block
- Let it finish and save the EDF file

### Step 2: Check Binocular Recording
```bash
python src/check_binocular_recording.py data/raw/participant_P01/part_A/session_*/edf/*.edf
```
- Verify you see "BINOCULAR ✓✓"
- If not, report immediately

### Step 3: Regenerate Stimuli (Optional but Recommended)
```bash
python src/regenerate_stimuli.py --part A
```
- This creates pre-rendered versions with correct sizes
- Speeds up experiment (pre-rendered images load faster)

### Step 4: Visual Inspection
```bash
python src/inspect_stimuli_visual.py --part A
```
- Check the generated plots
- Verify no shapes exceed screen bounds
- Confirm size differences look reasonable

### Step 5: Report Results
Send me:
1. Screenshot of the binocular recording check output
2. The summary figure from visual inspection (`part_A_summary.png`)
3. Any issues or concerns you notice

---

## Troubleshooting

### "edf2asc not found"
**Problem**: The EDF converter tool is not installed.

**Solution**: Download and install SR Research EDF utilities:
- https://www.sr-research.com/support/
- Install the "EDF Access API" package
- Add to your system PATH

### "MONOCULAR ✗" detected
**Problem**: Only one eye is being recorded.

**Solution**:
1. Check console output from experiment - should say "EyeLink in CL mode - binocular set via command (both eyes)"
2. If still monocular, the `binocular_enabled = YES` command may not be working
3. Contact me with full error details

### Shapes still clipped in visual inspection
**Problem**: Some shapes exceed the red line in the summary figure.

**Solution**:
1. Check which shapes are clipped
2. Report the shape names to me
3. I'll adjust the multipliers further

### PsychoPy window doesn't close
**Problem**: Window stays open after running inspection tool.

**Solution**:
- Just close it manually
- This is normal - matplotlib `plt.show()` keeps it open for you to examine

---

## Quick Reference Commands

```bash
# Check binocular recording
python src/check_binocular_recording.py <path_to_edf>

# Regenerate stimuli
python src/regenerate_stimuli.py --part A

# Visual inspection
python src/inspect_stimuli_visual.py --part A

# All three in sequence
python src/check_binocular_recording.py data/raw/participant_P01/part_A/session_*/edf/*.edf
python src/regenerate_stimuli.py --part A
python src/inspect_stimuli_visual.py --part A
```

---

## Expected Results Summary

After running all tools, you should see:

✅ **Binocular Check**: "BINOCULAR ✓✓"
✅ **Regeneration**: 156 stimuli rendered successfully (Part A)
✅ **Visual Inspection**: All shapes fit within screen bounds (below red line)
✅ **Size Hierarchy**: Very compact (2047px) > Compact (2017px) > Standard (1987px)

If ANY of these checks fail, report to me immediately before collecting real data!
