# Experiment Launcher GUI - User Guide

## Quick Start

**Double-click**: `launch_experiment.bat`

This opens a simple GUI where you can:
- Enter participant information
- Select experiment part (A or B)
- Choose to run full session or split into thirds
- Launch the experiment

## GUI Fields

### Required Fields

**Participant Number** (Required)
- Enter a number (e.g., `1`, `15`, `23`)
- Will be formatted as `P01`, `P15`, `P23`, etc.
- This is the primary identifier used in all data files

### Optional Fields

**Participant ID** (Optional)
- Additional identifier (e.g., student ID, code name)
- Not used in file names, only saved in demographics
- Can be left blank

**Age** (Optional)
- Participant's age
- Used for demographics only
- Can be left blank

**Gender**
- Select from: Male, Female, Non-binary, Prefer not to say, Other
- Defaults to "Prefer not to say"

## Experiment Settings

### Experiment Part
- **Part A**: First session
- **Part B**: Second session (different stimuli)

Typically participants do both parts on separate days.

### Block Range

**All blocks (1-9)** - Default
- Complete session: ~45 minutes
- Recommended for most participants

**Blocks 1-3** - First third
- ~15 minutes
- Use if participant needs to split session into 3 parts

**Blocks 4-6** - Middle third
- ~15 minutes
- Run after completing blocks 1-3

**Blocks 7-9** - Final third
- ~15 minutes
- Run after completing blocks 4-6

## When to Split Sessions

Split the session into thirds (1-3, 4-6, 7-9) if:
- Participant needs a bathroom break
- Participant is fatigued
- Time constraints require splitting
- Calibration quality degrades

**Important**: All three segments must be completed on the same day for valid data.

## Data Storage

### Demographics Data
**Location**: `data/demographics/participant_demographics.jsonl`

Contains:
```json
{
  "participant_number": "15",
  "participant_id": "P15",
  "subject_id": "STUDENT123",
  "age": "22",
  "gender": "Female",
  "timestamp": "2026-01-17T16:45:23.123456"
}
```

### Experimental Data
**Location**: `data/raw/participant_P##/part_X/session_TIMESTAMP/`

Files:
- `logs_session/session_metadata.json` - Contains dominant_eye
- `logs_trial/trials.csv` - Trial-by-trial data
- `logs_block/blocks.csv` - Block summaries
- `logs_memory/memory.csv` - Memory probe data
- `edf/*.edf` - EyeLink raw data

## Example Workflow

### Full Session (No Breaks)
1. Open GUI (`launch_experiment.bat`)
2. Enter participant number: `5`
3. Fill in demographics (optional)
4. Select Part: A
5. Select Blocks: **All blocks (1-9)**
6. Click "Launch Experiment"

Result: Participant P05 completes full Part A (~45 min)

### Split Session (With Breaks)

**First segment:**
1. Enter participant number: `5`
2. Select Part: A
3. Select Blocks: **Blocks 1-3**
4. Launch → Complete 3 blocks

**Break (5-10 minutes)**

**Second segment:**
1. Enter participant number: `5` (same)
2. Select Part: A (same)
3. Select Blocks: **Blocks 4-6**
4. Launch → Complete 3 blocks

**Break (5-10 minutes)**

**Third segment:**
1. Enter participant number: `5` (same)
2. Select Part: A (same)
3. Select Blocks: **Blocks 7-9**
4. Launch → Complete final 3 blocks

Result: Three separate sessions for P05 Part A, all on same day

## Command-Line Alternative

The GUI is just a wrapper around the experiment runner. You can also launch directly:

```bash
# Full session
python src/experiment2_runner.py --participant-id P05 --part A

# Partial session
python src/experiment2_runner.py --participant-id P05 --part A --blocks 1-3
python src/experiment2_runner.py --participant-id P05 --part A --blocks 4-6
python src/experiment2_runner.py --participant-id P05 --part A --blocks 7-9
```

## Troubleshooting

**GUI doesn't open:**
- Check Python is installed and in PATH
- Try: `python src/experiment_launcher.py`

**"Participant number is required" error:**
- Enter a number in the Participant Number field

**Experiment doesn't launch:**
- Check `src/experiment2_runner.py` exists
- Verify EyeLink is connected
- Check console for error messages

**Can't enter text in fields:**
- Click inside the text field first
- Press Tab to move between fields

## Tips

1. **Pre-fill demographics**: Have participant fill out paper form first, then enter into GUI
2. **Test first**: Do a quick test run with `P99` before first real participant
3. **Keep log**: Write down participant number and which blocks were completed
4. **Same day**: If splitting session, complete all segments same day
5. **Calibration**: Each segment starts with new calibration (expected)

## Data Analysis

When analyzing split sessions, the data will be in separate session folders but all have the same participant ID (P##). The analysis scripts will combine them automatically when you specify the participant root directory.

Example directory structure after split session:
```
data/raw/
  participant_P05/
    part_A/
      session_20260117_143022/  # Blocks 1-3
      session_20260117_145530/  # Blocks 4-6
      session_20260117_152010/  # Blocks 7-9
```

The `extract_fixations.py` and `validate_data_quality.py` scripts will process all three sessions for P05 Part A.
