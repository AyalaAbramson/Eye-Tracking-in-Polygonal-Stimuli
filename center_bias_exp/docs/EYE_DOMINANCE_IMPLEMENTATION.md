# Eye Dominance Test Implementation

## Overview

Eye dominance testing has been integrated into the experiment to enable post-hoc monocular analysis while maintaining binocular tracking throughout the session.

## Implementation Details

### Test Method
- **Method**: Hole-in-card test (standard clinical method)
- **Timing**: Runs immediately after window creation, before EyeLink setup
- **Duration**: ~30 seconds
- **User input**: Self-report via keyboard (L/R/S keys)

### Test Procedure
1. Participant extends both arms forward
2. Creates a small triangle/hole with hands
3. Views the fixation cross (+) through the hole with both eyes open
4. Brings hands slowly toward face
5. Hands naturally move toward dominant eye
6. Participant reports which eye (left/right) or skips test

### Data Recording

**Location**: Session metadata file
- **File**: `data/raw/participant_XXX/part_X/session_TIMESTAMP/logs_session/session_metadata.json`
- **Field**: `dominant_eye`
- **Values**: `'left'`, `'right'`, or `'unknown'`

### Tracking Configuration

**Important**: The experiment continues to track **BOTH eyes** (binocular mode) regardless of dominance.

**Why binocular tracking?**
- Better data quality (more robust)
- If one eye blinks, data from other eye still available
- Allows post-hoc monocular analysis by filtering data
- Maintains flexibility for future analyses

### Usage in Analysis

To analyze only the dominant eye in your analysis scripts:

```python
import json
import pandas as pd

# Load session metadata
with open('path/to/session_metadata.json') as f:
    metadata = json.load(f)

dominant_eye = metadata['dominant_eye']

# Filter fixation data by dominant eye
if dominant_eye == 'left':
    fixations_df = fixations_df[fixations_df['eye'] == 'L']
elif dominant_eye == 'right':
    fixations_df = fixations_df[fixations_df['eye'] == 'R']
# If 'unknown', use binocular average (current default)
```

## Testing

To test the eye dominance feature:

```bash
python src/experiment2_runner.py --participant-id TEST --part A
```

The test will appear immediately after the PsychoPy window opens.

## Skipping the Test

If a participant is unable to perform the test:
- Press `S` to skip
- Dominant eye will be recorded as `'unknown'`
- Experiment continues normally with binocular tracking

## Files Modified

1. **New file**: `src/eye_dominance_test.py`
   - Contains `run_eye_dominance_test()` function
   - Self-contained test implementation

2. **Modified**: `src/experiment2_runner.py`
   - Imports eye dominance test function
   - Runs test after window creation (line ~1040)
   - Records result in session metadata (line ~1119)

## Validation Threshold

As requested, validation threshold remains at **1.5°** (not tightened to 0.75°).

## No Practice Block

As requested, no practice block has been implemented.

## Summary

✅ Eye dominance test: **IMPLEMENTED**
✅ Binocular tracking: **MAINTAINED** (both eyes tracked)
✅ Data recorded: **session_metadata.json**
✅ Validation: **1.5°** (unchanged)
❌ Practice block: **NOT IMPLEMENTED** (as requested)

The implementation allows you to perform monocular analyses post-hoc while maintaining the benefits of binocular tracking during data collection.
