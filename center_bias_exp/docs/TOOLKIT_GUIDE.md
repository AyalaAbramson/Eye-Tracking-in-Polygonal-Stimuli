# **Center Bias Experiment - Analysis Toolkit Guide**

Complete guide for using the 4 analysis tools created for your experiment.

---

## **QUICK START**

### **Step 1: Convert EDF to ASC** (if not already done)

```bash
# On EyeLink Host PC or using edf2asc utility
cd data/raw/participant_P01/part_A/session_*/edf
edf2asc -t P01A.edf

# This creates P01A.asc with all events and messages
```

### **Step 2: Extract Fixations**

```bash
# Extract fixations for one session
python src/extract_fixations.py \
  --asc data/raw/participant_P01/part_A/session_20260115_103203/edf/P01A.asc \
  --trial-csv data/raw/participant_P01/part_A/session_20260115_103203/logs_trial/trials.csv \
  --output-dir outputs/fixations

# Output:
#   outputs/fixations/session_20260115_103203_fixations.csv
#   outputs/fixations/session_20260115_103203_fixations_summary.csv
#   outputs/fixations/session_20260115_103203_quality_report.txt
```

### **Step 3: Validate Data Quality**

```bash
# Check all pilot data for issues
python src/validate_data_quality.py --data-root data/raw --output-dir outputs/quality

# Output:
#   outputs/quality/data_quality_report.txt
#   outputs/quality/participant_quality.csv
```

### **Step 4: Run Statistical Analysis**

```bash
# Analyze Fix2 data from all participants
python src/analyze_center_bias.py \
  --fixations outputs/fixations/*_fixations_summary.csv \
  --manifest manifests/stimulus_manifest_partA.csv \
  --output-dir outputs/analysis

# Output:
#   outputs/analysis/figures/*.png
#   outputs/analysis/analysis_report.txt
```

### **Step 5: Verify Polygons (Optional)**

```bash
# Visual verification on your experiment setup
python src/visualize_polygons.py --save-screenshots

# Controls: SPACE=next, C=toggle centers, S=screenshot, ESC=quit
# Output: outputs/polygon_verification/*.png
```

---

## **TOOL 1: FIXATION EXTRACTION** (`extract_fixations.py`)

### **Purpose**
Parses EyeLink .asc files to extract Fix1-4 for each trial and compute distances to all geometric centers.

### **Input**
- `.asc` file (converted from EDF)
- `trials.csv` (with center coordinates)

### **Output Files**

**1. `*_fixations.csv` (long format)**
One row per fixation (up to 4 per trial):

| Column | Description |
|--------|-------------|
| `trial_uid` | Trial identifier (e.g., A_MB01_T001) |
| `fixation_number` | 1, 2, 3, or 4 |
| `onset_latency_ms` | Time from STIM_ON to fixation start |
| `duration_ms` | Fixation duration |
| `x_px`, `y_px` | Fixation coordinates |
| `dist_com_px` | Distance to Center of Mass |
| `dist_chc_px` | Distance to Convex Hull Center |
| `dist_bbc_px` | Distance to Bounding Box Center |
| `dist_icc_px` | Distance to Inscribed Circle Center |
| `winner` | Closest center (com/chc/bbc/icc) |
| `winner_margin_px` | Distance to 2nd-closest center |

**2. `*_fixations_summary.csv` (wide format)**
One row per trial with Fix1-4 data:

| Column Pattern | Description |
|----------------|-------------|
| `fix2_exists` | Boolean: did Fix2 occur? |
| `fix2_winner` | Which center was closest? |
| `fix2_dist_com_px` | Distance to COM |
| ... | Same for fix1, fix3, fix4 |

**3. `*_quality_report.txt`**
Summary statistics:
- Trials missing Fix2 (exclusion rate)
- Mean onset latency and duration
- Winner distribution
- Mean distances to each center

### **Batch Processing**

Extract fixations for all sessions:

```bash
# Create batch script (bash/PowerShell)
for session in data/raw/participant_*/part_*/session_*/; do
  asc_file="${session}edf/*.asc"
  trial_csv="${session}logs_trial/trials.csv"

  python src/extract_fixations.py \
    --asc "$asc_file" \
    --trial-csv "$trial_csv" \
    --output-dir outputs/fixations
done
```

---

## **TOOL 2: DATA QUALITY VALIDATION** (`validate_data_quality.py`)

### **Purpose**
Automated quality control for all pilot data, checking for clipping, calibration issues, and fixation success.

### **Checks Performed**

1. **Fixation Success Rate**
   - Target: >95% success
   - Warning: 85-95%
   - Error: <85%

2. **Polygon Clipping**
   - Checks for missing geometry data
   - Flags critical polygons (allfar_concave, etc.)

3. **Trial Completion**
   - Expected: 351 trials per session
   - Warning: <90% completion

4. **Calibration Quality**
   - Checks validation RMS values (if logged)
   - Target: <1.5°

5. **Fatigue Effects**
   - Compares first vs. last block success rates
   - Warning: >10% decline

### **Output Files**

**1. `data_quality_report.txt`**
Comprehensive report with:
- Summary (OK/WARNING/ERROR counts)
- Per-session details
- Specific issues identified
- Recommendations for action

**2. `participant_quality.csv`**
Metrics table for each session:

| Column | Description |
|--------|-------------|
| `participant_id` | Participant ID |
| `part` | A or B |
| `n_trials` | Total trials |
| `severity` | OK / WARNING / ERROR |
| `fixation_success_rate` | Percentage |
| `mean_fixation_time_s` | Average time to achieve fixation |
| ... | Additional metrics |

### **Example Output**

```
SUMMARY
-------
Total sessions validated: 5
Sessions with issues: 2
  - OK: 3
  - WARNING: 2
  - ERROR: 0

[1] P01 Part A - OK
    Path: data/raw/participant_P01/part_A/session_20260115_103203
    Trials: 351
    No issues detected ✓

[2] P02 Part A - WARNING
    Path: data/raw/participant_P02/part_A/session_20260115_110145
    Trials: 351
    Issues (1):
      - [Fixation Success] MODERATE fixation success rate: 92.3% (target: >95%)
```

---

## **TOOL 3: STATISTICAL ANALYSIS** (`analyze_center_bias.py`)

### **Purpose**
Implements your pre-registered analysis plan with linear mixed models and robustness checks.

### **Analyses Performed**

**1. PRIMARY: Distance-Based Linear Mixed Model**
```
Model: distance_px ~ C(center) + C(trial_type) + C(polygon_case) +
                    (1 | participant_id) + (1 | polygon_id)
```

Tests:
- Main effect of center type (F-test)
- Pairwise comparisons (Holm-corrected)
- Identifies "winner" center (lowest mean distance)

**2. SECONDARY: Winner Probability**
- Chi-square test: Are win proportions equal?
- Win probability for each center
- Confidence intervals

**3. ROBUSTNESS CHECKS**
- Winner consistency across image categories
- Winner consistency across polygon cases
- Trial type effects (image vs. empty)

### **Output Files**

**Figures** (`outputs/analysis/figures/`):
1. `fig1_mean_distances.png` - Bar plot with error bars
2. `fig2_winner_distribution.png` - Pie chart
3. `fig3_winner_by_category.png` - Heatmap
4. `fig4_distance_distributions.png` - Violin plots

**Text Output**:
```
PRIMARY ANALYSIS: Distance-Based Linear Mixed Model (Fix2)
==========================================================================

CENTER EFFECTS (Distance from Fixation 2)
--------------------------------------------------------------------------
Center      Mean Dist (px)  Coef vs COM  p-value
--------------------------------------------------------------------------
COM         124.56             0.00       1.0000
CHC         156.23            31.67       0.0012 **
BBC         142.89            18.33       0.0234 *
ICC         138.45            13.89       0.0456 *
--------------------------------------------------------------------------

Pairwise Comparisons (Holm-Bonferroni corrected):
--------------------------------------------------------------------------
COM vs CHC:  t= -5.23, p=0.0001, p_adj=0.0006 ***
COM vs BBC:  t= -2.45, p=0.0234, p_adj=0.0702
...
```

### **Requirements**

Install dependencies:
```bash
pip install statsmodels scipy matplotlib seaborn pandas numpy
```

### **Usage**

```bash
# Full analysis
python src/analyze_center_bias.py \
  --fixations outputs/fixations/*_fixations_summary.csv \
  --manifest manifests/stimulus_manifest_partA.csv \
  --output-dir outputs/analysis

# Figures only (skip statistical models)
python src/analyze_center_bias.py \
  --fixations outputs/fixations/*_fixations_summary.csv \
  --manifest manifests/stimulus_manifest_partA.csv \
  --figures-only
```

---

## **TOOL 4: POLYGON VISUALIZATION** (`visualize_polygons.py`)

### **Purpose**
Interactive visualization to verify polygons display correctly on your experimental setup.

### **Features**

1. **Visual Inspection**
   - Displays each of 27 polygons
   - Shows center markers (color-coded)
   - Shows bounding box
   - Shows screen safe zone (red boundary at 95%)

2. **Interactive Controls**
   - `SPACE`: Next polygon
   - `BACKSPACE`: Previous polygon
   - `C`: Toggle center markers on/off
   - `B`: Toggle bounding box on/off
   - `S`: Save screenshot
   - `ESC`: Quit

3. **Verification Report**
   - Lists all polygons with dimensions
   - Flags any that exceed safe bounds
   - Saves to `outputs/polygon_verification/verification_report.txt`

### **Output**

**verification_report.txt**:
```
POLYGON VERIFICATION REPORT
=============================================================================

SUMMARY
-------
Total polygons checked: 27
Polygons with clipping: 0

POLYGON DETAILS
---------------
Polygon ID                         Case                          Max Extent (px) Clipped?
-----------------------------------------------------------------------------------------
allfar_concave_01                  allfar_concave                993.5           NO ✓
allfar_convex_01                   allfar_convex                 993.5           NO ✓
...
```

### **Usage**

```bash
# Show all polygons interactively
python src/visualize_polygons.py

# Show specific polygon only
python src/visualize_polygons.py --polygon allfar_concave_01

# Save screenshots of all polygons
python src/visualize_polygons.py --save-screenshots
```

---

## **COMPLETE WORKFLOW: PILOT TO PUBLICATION**

### **Phase 1: Pilot Data Collection** (CURRENT)
```bash
# 1. Run pilot participants (P01-P05)
python src/experiment2_runner.py --participant-id P01 --part A

# 2. Validate data quality
python src/validate_data_quality.py --data-root data/raw

# 3. Check for issues
cat outputs/quality/data_quality_report.txt

# 4. Verify polygons (one-time check)
python src/visualize_polygons.py --save-screenshots
```

### **Phase 2: Full Data Collection** (NEXT 2 WEEKS)
```bash
# 1. Run 20 participants × 2 parts = 40 sessions
for PID in P06 P07 ... P25; do
  # Part A (Day 1)
  python src/experiment2_runner.py --participant-id $PID --part A

  # Part B (Day 2)
  python src/experiment2_runner.py --participant-id $PID --part B
done

# 2. Convert EDF to ASC (batch)
for edf in data/raw/participant_*/part_*/session_*/edf/*.edf; do
  edf2asc -t "$edf"
done

# 3. Extract fixations (batch)
for session in data/raw/participant_*/part_*/session_*/; do
  python src/extract_fixations.py \
    --asc "${session}edf/*.asc" \
    --trial-csv "${session}logs_trial/trials.csv" \
    --output-dir outputs/fixations
done

# 4. Validate all data
python src/validate_data_quality.py --data-root data/raw
```

### **Phase 3: Analysis** (WEEK 3)
```bash
# 1. Run confirmatory analysis
python src/analyze_center_bias.py \
  --fixations outputs/fixations/*_fixations_summary.csv \
  --manifest manifests/stimulus_manifest_partA.csv \
  --output-dir outputs/analysis_partA

python src/analyze_center_bias.py \
  --fixations outputs/fixations/*_fixations_summary.csv \
  --manifest manifests/stimulus_manifest_partB.csv \
  --output-dir outputs/analysis_partB

# 2. Review results
cat outputs/analysis_partA/analysis_report.txt
cat outputs/analysis_partB/analysis_report.txt

# 3. Generate publication figures
# (Already created by analyze_center_bias.py)
ls outputs/analysis_partA/figures/
```

### **Phase 4: Writing** (WEEKS 4-7)
- Use figures from `outputs/analysis/figures/`
- Report statistics from analysis console output
- Include quality metrics from validation reports

---

## **TROUBLESHOOTING**

### **Problem: "No fixations found in ASC file"**

**Solution:**
- Check that EDF was converted to ASC: `ls data/raw/.../edf/*.asc`
- Convert manually: `edf2asc -t file.edf`
- Verify ASC contains fixation events: `grep "EFIX" file.asc | head`

### **Problem: "Missing center coordinates in trials.csv"**

**Solution:**
- Check that `center_mass_x_px` columns exist in trials.csv
- Re-run experiment with updated code (polygon geometry should be auto-computed)
- If missing, compute manually from polygon_geometry.csv

### **Problem: "Model fit failed in analyze_center_bias.py"**

**Solution:**
- Install correct statsmodels version: `pip install statsmodels==0.14.0`
- Check data has multiple participants: `df['participant_id'].nunique()` should be >1
- Try simpler random effects structure (edit formula in script)

### **Problem: "Polygon visualization shows clipping"**

**Solution:**
- The margin_factor fix (0.75) should prevent this
- If still clipping, reduce aperture_scale in config: `aperture_scale_factor = 1800` (instead of 1987)
- Re-run visualization to verify

---

## **TIPS FOR TIER-1 PUBLICATION**

### **1. Data Quality**
- Exclude participants with <85% fixation success rate
- Report exclusion criteria transparently
- Show quality metrics in supplementary materials

### **2. Statistical Reporting**
```
"Linear mixed-effects models revealed a significant main effect of center type
(F(3, 18) = 12.45, p < 0.001). Pairwise comparisons (Holm-corrected) showed
that Fixation 2 landed significantly closer to the Center of Mass (M = 124.6 px,
SD = 45.2) compared to the Convex Hull Center (M = 156.2 px, SD = 52.1;
t(18) = 5.23, p_adj < 0.001), Bounding Box Center (M = 142.9 px, SD = 48.7;
t(18) = 2.45, p_adj = 0.070), and Inscribed Circle Center (M = 138.5 px,
SD = 46.3; t(18) = 2.12, p_adj = 0.092)."
```

### **3. Figures**
- Use publication-ready figures from `analyze_center_bias.py`
- Edit in vector graphics editor (Inkscape/Illustrator) if needed
- Follow journal style guidelines (Nature, Science, J Neuroscience, etc.)

### **4. Reproducibility**
- Deposit data on OSF: https://osf.io/
- Include:
  - Raw EDF files
  - Extracted fixations CSVs
  - Analysis scripts (these 4 tools!)
  - Manifests and config files

---

## **NEXT STEPS**

1. **TODAY**: Run `validate_data_quality.py` on pilot data
2. **THIS WEEK**: Run `visualize_polygons.py` to verify no clipping
3. **NEXT WEEK**: Convert 1 pilot EDF to ASC and test `extract_fixations.py`
4. **WEEK 2-3**: Collect 20 participants
5. **WEEK 4**: Run full analysis pipeline
6. **WEEK 5+**: Write paper

---

**Questions?** Check the inline documentation in each script or contact lab.
