# Bug Fixes - Round 3 (Critical Issues from Pilot Test)

## Three Critical Issues Fixed

Based on your pilot test of the first block, I've identified and fixed three critical issues:

---

### Bug 1: iso_com_01 Clipped at Middle ✅ FIXED

**Problem**: The iso_com_01 polygon was being cut off in the middle of the screen, not showing fully.

**Root Cause**: The size multipliers I set in Round 2 were TOO LARGE:
- Very compact shapes (iso_chc, iso_com): 1.20 multiplier → 2384px
- Screen height: 2160px
- **2384px > 2160px = CLIPPING!**

The original calculation was mathematically wrong. I didn't account for the screen size limit.

**Correct Calculation**:
- Base aperture size: 1987px (92% of 2160px screen height)
- Maximum safe size: ~2052px (95% of 2160px to prevent clipping)
- Maximum multiplier: 2052 / 1987 = 1.033 (only 3.3% boost possible!)

**Fix Applied**:
- Very compact shapes: 1.03 multiplier (3% boost) → 2047px ✓ fits safely
- Compact shapes: 1.015 multiplier (1.5% boost) → 2017px ✓ fits safely
- Standard shapes: 1.0 multiplier → 1987px

**File Changed**: [src/psychopy_utils.py](../src/psychopy_utils.py) (lines 343-361)

**New Code**:
```python
# Very small shapes get 3% size boost (from 1987 to 2047px)
very_compact_shapes = ['iso_chc_01', 'iso_chc_02', 'iso_chc_03',
                       'iso_com_01', 'iso_com_02', 'iso_com_03']

# Moderately small shapes get 1.5% size boost (from 1987 to 2017px)
compact_shapes = ['allfar_convex', 'iso_bbc_02', 'iso_bbc_03',
                  'iso_icc_01', 'iso_icc_02', 'iso_icc_03']

if shape_name in very_compact_shapes:
    display_multiplier = 1.03  # Safe for 2160px display
elif shape_name in compact_shapes:
    display_multiplier = 1.015  # Safe for 2160px display
else:
    display_multiplier = 1.0
```

**Why This Works**: The polygons now stay within the screen bounds (2052px maximum) while still giving compact shapes a small visibility boost.

---

### Bug 2: Binocular Recording Not Working ✅ FIXED

**Problem**: You reported "it looks like the recording is done in monocular phase even though we state that its binacolur mode"

**Root Cause**: The `binocular_enabled` config setting was defined in the YAML file, but the critical `setRecordingParseType()` command was NEVER called to tell the EyeLink tracker to actually record from both eyes.

**Fix Applied**: Added explicit binocular mode configuration with `setRecordingParseType(0)` where:
- 0 = BINOCULAR (both eyes)
- 1 = LEFT_ONLY (monocular left)
- 2 = RIGHT_ONLY (monocular right)

**File Changed**: [src/eyetracker_utils.py](../src/eyetracker_utils.py) (lines 213-224)

**New Code**:
```python
# CRITICAL: Set binocular recording mode
# This tells the tracker to record from BOTH eyes, not just one
binocular_enabled = eyelink_cfg.get('binocular_enabled', True)
if binocular_enabled:
    tracker.sendCommand("binocular_enabled = YES")
    # setRecordingParseType: 0=BINOCULAR, 1=LEFT_ONLY, 2=RIGHT_ONLY
    tracker.setRecordingParseType(0)
    print("EyeLink configured for BINOCULAR recording (both eyes)")
else:
    tracker.sendCommand("binocular_enabled = NO")
    tracker.setRecordingParseType(1)  # Default to LEFT eye if monocular
    print("EyeLink configured for MONOCULAR recording (left eye)")
```

**Verification**: When you run the experiment now, you should see in the console:
```
EyeLink configured for BINOCULAR recording (both eyes)
```

And when you convert the EDF file, you should see data for BOTH eyes (left and right columns).

---

### Bug 3: EyeLink Staying in Offline Mode ✅ CLARIFIED (Not a Bug!)

**Your Concern**: "it looks like the EyeLink stays in offline mode after the drift correction, does we still recored all the data?"

**Explanation**: This is actually CORRECT behavior! Here's why:

**Standard EyeLink Recording Pattern**:
1. **Before drift correction**: Tracker goes to OFFLINE mode (line 730)
2. **Drift correction runs**: Tracker is in OFFLINE mode (not recording)
3. **After drift correction**: Tracker STAYS in OFFLINE mode
4. **Trial starts**: `start_recording()` is called (line 179) → Recording RESUMES
5. **Trial ends**: `stop_recording()` is called → Back to OFFLINE mode

**Why This is Correct**:
- Drift correction is NOT part of the trial - it shouldn't be recorded
- Recording starts at the beginning of each trial (after drift correction)
- The EDF file will contain continuous recording during each trial
- Between trials, the tracker is offline (saves file space, prevents junk data)

**Data Recording Confirmation**:
- Recording starts: Line 179 of experiment2_runner.py → `start_recording(tracker, exp_clock)`
- Recording stops: Line 537 of experiment2_runner.py → `stop_recording(tracker, exp_clock)`
- Each trial has its own continuous recording segment

**File Changed**: [src/eyetracker_utils.py](../src/eyetracker_utils.py) (lines 780-783)

**Added Comment**:
```python
# NOTE: We do NOT need to call setOfflineMode() or restart recording here
# The tracker is already in offline mode (set at line 730) and will be
# put back into recording mode by the caller when the trial starts
# This is the standard EyeLink pattern for drift correction
```

**Your Data is Safe**: All eye movement data during trials IS being recorded. The offline mode between trials is intentional and correct.

---

## Summary of Changes

| File | Lines | Change | Status |
|------|-------|--------|--------|
| src/psychopy_utils.py | 343-361 | Reduced size multipliers to 1.03/1.015 to prevent clipping | ✅ |
| src/psychopy_utils.py | 505-514 | Updated comments to reflect new multipliers | ✅ |
| src/eyetracker_utils.py | 213-224 | Added setRecordingParseType(0) for binocular recording | ✅ |
| src/eyetracker_utils.py | 780-783 | Added clarifying comment about offline mode pattern | ✅ |

---

## Testing Instructions

### Test 1: Polygon Clipping (CRITICAL)
1. Run experiment with iso_com_01, iso_chc_01, or other compact shapes
2. **EXPECTED**: Polygons should be fully visible, NOT cut off
3. Check console for DEBUG messages:
   ```
   DEBUG: Shape 'iso_com_01': 3% size boost (very compact) - multiplier=1.03, final=2047px
   DEBUG MASK: Shape 'iso_com_01' very compact - margin=0.88, poly_max_dim=2047px
   ```
4. **FAILURE**: If any polygon is still clipped, report which one

### Test 2: Binocular Recording
1. Run a full trial with recording
2. After session, convert EDF to ASC: `edf2asc yourfile.edf`
3. Open the .asc file and search for "SAMPLES"
4. **EXPECTED**: You should see columns for BOTH eyes (left and right gaze coordinates)
5. Example line:
   ```
   1234567  950.2  540.1  1234.0 ...  960.5  545.3  1198.0 ...
            ^LEFT EYE GAZE^           ^RIGHT EYE GAZE^
   ```
6. **FAILURE**: If you only see data for one eye, report which eye

### Test 3: Data Recording During Trials
1. Run a few trials and complete normally
2. Check the EDF file size - should be growing significantly (NOT tiny)
3. Convert to ASC and verify you see:
   - START messages for each trial
   - Continuous sample data during trials
   - END messages for each trial
4. **EXPECTED**: All trial data is recorded between START/END markers
5. **FAILURE**: If no sample data between trials, report

---

## Expected Console Output

When running the experiment, you should now see:

```
EyeLink configured for BINOCULAR recording (both eyes)
...
DEBUG: Shape 'iso_com_01': 3% size boost (very compact) - multiplier=1.03, final=2047px
DEBUG MASK: Shape 'iso_com_01' very compact - margin=0.88, poly_max_dim=2047px
...
DEBUG: Shape 'allfar_convex': 1.5% size boost (compact) - multiplier=1.015, final=2017px
DEBUG MASK: Shape 'allfar_convex' compact - margin=0.85, poly_max_dim=2017px
...
DEBUG: Shape 'allfar_concave': standard size - multiplier=1.0, final=1987px
DEBUG MASK: Shape 'allfar_concave' standard - margin=0.75, poly_max_dim=1987px
```

---

## Important Notes

1. **Shape Size Reduction**: The size boost is now much smaller (1.5-3% instead of 13-20%) because we were exceeding screen bounds. This is the maximum safe boost for a 2160px display.

2. **Binocular Recording**: You'll now see "EyeLink configured for BINOCULAR recording (both eyes)" in the console. Verify this appears before each session.

3. **Offline Mode is Normal**: The tracker being in offline mode between trials is CORRECT and expected. Don't worry about this - your data is being recorded during trials.

4. **DEBUG Output**: The debug messages will help us verify that the correct multipliers are being applied. Check these against the expected values above.

---

## Next Steps

1. **Run another pilot block** with these fixes
2. **Report back**:
   - Are iso_com/iso_chc shapes fully visible now?
   - Do you see "BINOCULAR recording" in the console?
   - Does the EDF file contain data for both eyes when converted?
3. **Once confirmed working**: We can remove DEBUG print statements for cleaner output

---

## Why the Original Size Boost Failed

The original plan was to make compact shapes 13-20% larger to improve visibility. However, this was mathematically impossible given the screen constraints:

| Shape Type | Original Plan | Actual Size | Screen Height | Result |
|------------|---------------|-------------|---------------|--------|
| Very compact | 20% boost | 2384px | 2160px | ❌ CLIPPED |
| Compact | 13% boost | 2245px | 2160px | ❌ CLIPPED |
| Standard | No boost | 1987px | 2160px | ✓ OK |

The new approach uses much smaller boosts that stay within screen bounds:

| Shape Type | New Plan | Actual Size | Screen Height | Result |
|------------|----------|-------------|---------------|--------|
| Very compact | 3% boost | 2047px | 2160px | ✓ SAFE |
| Compact | 1.5% boost | 2017px | 2160px | ✓ SAFE |
| Standard | No boost | 1987px | 2160px | ✓ SAFE |

This ensures all polygons are fully visible while still giving compact shapes a slight visibility advantage.
