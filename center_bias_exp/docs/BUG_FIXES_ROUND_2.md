# Bug Fixes - Round 2

## Three Critical Bugs Fixed

### Bug 1: Drift Correction Still Stuck ✅ FIXED

**Problem**: After drift correction completed, the EyeLink display stayed active instead of returning control to PsychoPy. The previous fix (`pylink.closeGraphics()`) was incorrect.

**Root Cause**: The `pylink.closeGraphics()` call was closing the graphics environment for the ENTIRE experiment, not just for the drift correction display. The graphics are opened once at the start with `pylink.openGraphicsEx(graphics_env)` and should stay open throughout.

**Fix Applied**:
- Removed the incorrect `pylink.closeGraphics()` call
- Added `tracker.setOfflineMode()` to properly return the tracker to offline state
- Increased wait time to 0.1s for tracker to stabilize

**File**: [src/eyetracker_utils.py](../src/eyetracker_utils.py) (lines 758-763)

**Code Change**:
```python
# BEFORE (WRONG):
pylink.closeGraphics()
core.wait(0.01)

# AFTER (CORRECT):
tracker.setOfflineMode()
core.wait(0.1)
```

**Why This Works**: After drift correction completes, the tracker needs to be explicitly returned to offline mode. This clears the graphics state without closing the graphics environment that the whole experiment depends on.

---

### Bug 2: Eye Dominance Test Missing Fixation Cross ✅ FIXED

**Problem**: During the eye dominance test, participants saw only the instructions screen. The fixation cross (+) that they're supposed to focus on was never displayed.

**Root Cause**: The fixation cross stimulus was created (line 66-74) but never drawn before flipping the window (line 77-78).

**Fix Applied**: Added `fixation.draw()` call before `win.flip()`

**File**: [src/eye_dominance_test.py](../src/eye_dominance_test.py) (lines 76-79)

**Code Change**:
```python
# BEFORE (WRONG):
instr_text.draw()
win.flip()

# AFTER (CORRECT):
instr_text.draw()
fixation.draw()  # Draw the + symbol!
win.flip()
```

**Why This Works**: PsychoPy only displays stimuli that have been explicitly drawn before `win.flip()` is called. The fixation cross was created but never added to the draw buffer.

---

### Bug 3: Compact Shapes Not Appearing Larger ⏳ DEBUGGING

**Problem**: User reports that compact masked visuals don't appear bigger in the actual experiment, despite the size multiplier code.

**Investigation**: Added comprehensive debug output to track:
1. Whether shape names are being correctly extracted
2. Which display multiplier is being applied (1.0, 1.13, or 1.20)
3. The final polygon dimensions used for masking

**Debug Output Added**:

In [src/psychopy_utils.py](../src/psychopy_utils.py):

**Line 351, 355, 358** - Debug shape multiplier:
```python
if shape_name in very_compact_shapes:
    display_multiplier = 1.20
    print(f"DEBUG: Shape '{shape_name}': 20% size boost (very compact) - multiplier={display_multiplier}")
elif shape_name in compact_shapes:
    display_multiplier = 1.13
    print(f"DEBUG: Shape '{shape_name}': 13% size boost (compact) - multiplier={display_multiplier}")
else:
    display_multiplier = 1.0
    print(f"DEBUG: Shape '{shape_name}': standard size - multiplier={display_multiplier}")
```

**Lines 505, 508, 511** - Debug masked image dimensions:
```python
if shape_name in very_compact_shapes:
    margin_factor = 0.88
    print(f"DEBUG MASK: Shape '{shape_name}' very compact - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")
elif shape_name in compact_shapes:
    margin_factor = 0.85
    print(f"DEBUG MASK: Shape '{shape_name}' compact - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")
else:
    margin_factor = 0.75
    print(f"DEBUG MASK: Shape '{shape_name}' standard - margin={margin_factor}, poly_max_dim={poly_max_dim:.0f}px")
```

**Next Steps**:
1. Run the experiment with a compact shape (e.g., iso_chc_01 or allfar_convex)
2. Check the console output for the DEBUG messages
3. Report what you see:
   - What shape name is detected?
   - What multiplier is applied?
   - What is the poly_max_dim value?

**Expected Output for iso_chc_01**:
```
DEBUG: Shape 'iso_chc_01': 20% size boost (very compact) - multiplier=1.2
DEBUG MASK: Shape 'iso_chc_01' very compact - margin=0.88, poly_max_dim=2384px
```

**Expected Output for allfar_convex**:
```
DEBUG: Shape 'allfar_convex': 13% size boost (compact) - multiplier=1.13
DEBUG MASK: Shape 'allfar_convex' compact - margin=0.85, poly_max_dim=2245px
```

**Expected Output for allfar_concave** (standard):
```
DEBUG: Shape 'allfar_concave': standard size - multiplier=1.0
DEBUG MASK: Shape 'allfar_concave' standard - margin=0.75, poly_max_dim=1987px
```

**Possible Issues**:
- Shape name might not match exactly (e.g., 'iso_chc_1' instead of 'iso_chc_01')
- Shape name might have extra characters or underscores
- aperture_scale_factor might not be set correctly

---

## Testing Instructions

### Test 1: Drift Correction (CRITICAL)
1. Run experiment with `python src/experiment_launcher.py`
2. Complete eye dominance test
3. Complete initial calibration
4. Start first trial
5. When drift correction appears, press SPACE to accept
6. **EXPECTED**: Screen should immediately return to PsychoPy display (black screen or stimulus)
7. **FAILURE**: If EyeLink graphics stay visible, report immediately

### Test 2: Eye Dominance Test
1. Run experiment
2. At eye dominance test screen, look for:
   - Instructions text (should be visible)
   - **Large white + symbol in center** (should be visible NOW)
3. Press L, R, or S to complete test
4. **EXPECTED**: Both instructions AND fixation cross visible simultaneously

### Test 3: Shape Sizing
1. Run experiment through to first trial with a compact shape
2. Watch the console output for DEBUG messages
3. Copy the DEBUG output and report it
4. Visual check: Do compact shapes (iso_chc, iso_com, allfar_convex) look larger than standard shapes (allfar_concave)?

---

## Summary of Changes

| File | Lines | Change |
|------|-------|--------|
| src/eyetracker_utils.py | 758-763 | Fixed drift correction by using setOfflineMode() instead of closeGraphics() |
| src/eye_dominance_test.py | 76-79 | Added fixation.draw() to display the + symbol |
| src/psychopy_utils.py | 351, 355, 358 | Added debug output for shape multiplier |
| src/psychopy_utils.py | 505, 508, 511 | Added debug output for masked image dimensions |

---

## Next Steps After Testing

1. **If drift correction works**: Remove or reduce debug wait time (currently 0.1s might be slightly long)
2. **If eye dominance works**: No changes needed, feature complete
3. **If shape sizing issues persist**: Analyze debug output to identify root cause
4. **When all tests pass**: Remove debug print statements for cleaner console output

---

## Contact

If you encounter any issues during testing, report:
1. Which bug is still occurring
2. Console output (especially DEBUG messages for shape sizing)
3. Exact steps to reproduce
4. Any error messages
