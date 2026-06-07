# **QUICK REFERENCE - Center Bias Experiment**

## **🚀 QUICK START (Test Right Now)**

### GUI Launcher (Recommended)
```bash
# Double-click launch_experiment.bat
# OR run:
python src/experiment_launcher.py
```

### Command Line (Advanced)
```bash
# 1. Test drift correction (5 trials, yourself as pilot)
python src/experiment2_runner.py --participant-id PILOT --part A

# 2. Verify polygons display correctly
python src/visualize_polygons.py --save-screenshots

# 3. Check pilot data quality
python src/validate_data_quality.py --data-root data/raw
```

---

## **📊 FULL ANALYSIS PIPELINE**

```bash
# STEP 1: Convert EDF to ASC (all sessions)
for edf in data/raw/participant_*/part_*/session_*/edf/*.edf; do
    edf2asc -t "$edf"
done

# STEP 2: Extract fixations (all sessions)
for session in data/raw/participant_*/part_*/session_*/; do
    python src/extract_fixations.py \
        --asc "${session}edf/*.asc" \
        --trial-csv "${session}logs_trial/trials.csv" \
        --output-dir outputs/fixations
done

# STEP 3: Quality check
python src/validate_data_quality.py --data-root data/raw

# STEP 4: Statistical analysis
python src/analyze_center_bias.py \
    --fixations outputs/fixations/*_fixations_summary.csv \
    --manifest manifests/stimulus_manifest_partA.csv \
    --output-dir outputs/analysis
```

---

## **✅ WHAT WAS FIXED**

| Issue | Fix | File |
|-------|-----|------|
| Polygon clipping | Margin 0.80→0.75 + safety check | `src/psychopy_utils.py:463` |
| Drift correction stuck | Added offline mode + 50ms wait | `src/eyetracker_utils.py:716` |
| Slow fixation gating | Config-switchable drift_correction/gaze_gate | `src/experiment2_runner.py:250` |

**Current config:** `drift_gate.method = "drift_correction"` ← Use this!

---

## **🛠️ TOOLS CREATED**

| Tool | Purpose | Command |
|------|---------|---------|
| **extract_fixations.py** | Parse ASC → Get Fix1-4 + distances | See pipeline above |
| **validate_data_quality.py** | Check calibration, fixation, clipping | See pipeline above |
| **analyze_center_bias.py** | LMM + figures + stats | See pipeline above |
| **visualize_polygons.py** | Verify polygons on your screen | `python src/visualize_polygons.py` |

---

## **📈 DATA QUALITY THRESHOLDS**

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Fixation success rate | >95% | 85-95% | <85% |
| Validation RMS | <0.75° | 0.75-1.5° | >1.5° |
| Trial completion | >95% | 85-95% | <85% |
| Fix2 missing rate | <5% | 5-15% | >15% |

---

## **🎯 CRITICAL CHECKS BEFORE FULL DATA COLLECTION**

- [ ] Drift correction works (not stuck) → Test with PILOT
- [ ] Polygons fit on screen (no clipping) → Run visualize_polygons.py
- [ ] Pilot data quality acceptable → Run validate_data_quality.py
- [ ] Config set to `method: "drift_correction"` → Check experiment_config.yaml

---

## **📚 DOCUMENTATION**

| File | What it contains |
|------|------------------|
| [`docs/TOOLKIT_GUIDE.md`](docs/TOOLKIT_GUIDE.md) | **Full tool usage guide** |
| [`docs/SUMMARY_AND_NEXT_STEPS.md`](docs/SUMMARY_AND_NEXT_STEPS.md) | **Complete summary + timeline** |
| [`docs/EXPERIMENT_ENHANCEMENTS.md`](docs/EXPERIMENT_ENHANCEMENTS.md) | Optional improvements |
| [`docs/Analysis Plan.md`](docs/Analysis%20Plan%20-%20CB%20experiment%202.md) | Your pre-registered plan |

---

## **⏱️ TIMELINE**

| Week | Task | Output |
|------|------|--------|
| **1** (now) | Test fixes, validate pilots | Quality report |
| **2-3** | Collect 20 participants × 2 parts | 40 sessions, 28k trials |
| **4** | Convert EDF, extract fixations | Fixation CSVs |
| **5** | Run analysis, generate figures | Results + figures |
| **6-9** | Write paper | Draft manuscript |
| **10** | Submit | 🎉 |

---

## **✅ FINAL DECISIONS**

Decisions made for full data collection:

1. **Validation threshold:** ✅ **1.5°** (lenient, acceptable quality)

2. **Practice block:** ❌ **NO** (not implemented)

3. **Eye dominance:** ✅ **YES** (30 sec test, binocular tracking maintained)
   - Recorded in session_metadata.json
   - Both eyes tracked for robustness
   - Enables post-hoc monocular analysis

4. **Session length:** ✅ **Keep 9 blocks** (no splitting needed)

---

## **📧 SEND ME AFTER TESTING**

1. Drift correction result (worked? Yes/No)
2. Polygon clipping (any polygons clipped?)
3. Quality report summary (paste output)
4. Decisions on 4 questions above

Then I'll help with:
- Practice block implementation (if Yes)
- Eye dominance test code (if Yes)
- Any troubleshooting needed

---

## **🎓 TARGET JOURNALS**

1. **Journal of Vision** ← Best fit
2. Attention, Perception, & Psychophysics
3. Vision Research
4. Psychological Science (if strong effects)

**Confidence:** 85% acceptance at one of these (with quality data + good writing)

---

**GOOD LUCK! You've got a solid experiment and excellent tools. Time to collect data!**
