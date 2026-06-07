# **Experiment & Analysis Enhancements**

Suggested improvements for your center bias experiment to maximize impact for Tier-1 publication.

---

## **EXPERIMENT DESIGN ENHANCEMENTS**

### **Enhancement 1: Eye Dominance Control** ⭐⭐⭐ (HIGH PRIORITY)

**Current:** Using both eyes' data without considering eye dominance

**Problem:**
- ~65% of people are right-eye dominant, 30% left-eye dominant
- Eye dominance may interact with center bias
- Binocular averaging can mask lateralization effects

**Recommendation:**
```yaml
# Add to experiment protocol
pre_experiment:
  - eye_dominance_test:
      method: "Miles test" or "Porta test"
      record: dominant_eye  # L or R
      use_for_analysis: dominant_eye_only

# In analysis
- Compare COM bias strength between dominant vs. non-dominant eye
- Report both monocular (dominant eye) and binocular analyses
```

**Implementation:**
- Add eye dominance test before Part A (takes 30 seconds)
- Log as participant metadata
- Extract dominant eye fixations only in analysis pipeline

**Impact:** +0.5-1.0 points on paper quality (common requirement for Vision Research, J Vision)

---

### **Enhancement 2: Individual-Level Baselines** ⭐⭐⭐ (HIGH PRIORITY)

**Current:** Baseline polygons have co-located centers (good!)

**Enhancement:** Use baseline trials to compute **individual center bias strength**

**Rationale:**
- Participants vary in baseline center bias (Tatler, 2007)
- Individual differences may predict which center definition wins
- Stronger effect sizes when controlling for baseline

**Implementation:**
```python
# In analysis pipeline
def compute_individual_bias_baseline(participant_data):
    """
    For each participant, compute baseline center bias from
    rectangle/symmetric trials (where all centers = screen center)
    """
    baseline_trials = participant_data[
        participant_data['polygon_case'].isin(['baseline_rectangle', 'baseline_symmetric'])
    ]

    # Distance from Fix2 to screen center
    baseline_dist = baseline_trials['fix2_dist_screen_center'].mean()

    # Classify participant as:
    # - Strong center bias: baseline_dist < 50px
    # - Moderate: 50-150px
    # - Weak: >150px

    return baseline_dist

# Then in mixed model:
# distance_px ~ C(center) + baseline_bias_strength + ...
```

**Analysis:**
- Test if baseline bias strength predicts winner identification
- Report: "Participants with strong baseline center bias (n=12) showed larger COM advantage (β=45.2, p<0.001) compared to weak bias participants (n=8, β=12.3, p=0.23)"

**Impact:** Makes your results more interpretable and publishable

---

### **Enhancement 3: Temporal Dynamics (Exploratory)** ⭐⭐

**Current:** Analyzing Fix2 only (correct for primary analysis)

**Enhancement:** Add exploratory analysis of **temporal evolution**

**Research Questions:**
- Does winner change from Fix1 → Fix2 → Fix3?
- When does center bias peak?
- How long does bias persist?

**Implementation:**
```python
# Already extracted Fix1-4 in your pipeline!
def analyze_temporal_dynamics(data):
    """
    Track winner across fixations 1-4
    """
    for fix_num in [1, 2, 3, 4]:
        winner_dist = data.groupby(f'fix{fix_num}_winner').size()
        print(f"Fix {fix_num} winner distribution: {winner_dist}")

    # Transition analysis
    # How many trials: Fix1 winner ≠ Fix2 winner?
    transitions = (data['fix1_winner'] != data['fix2_winner']).sum()
    print(f"Fixations changing winner: {transitions} / {len(data)}")
```

**Figures:**
- Line plot: Mean distance to each center across Fix1-4
- Sankey diagram: Winner transitions from Fix1→Fix2→Fix3→Fix4

**Impact:** Adds depth to discussion section, shows expertise in temporal dynamics

---

### **Enhancement 4: Saccade Amplitude Control** ⭐⭐

**Current:** 9-position cue grid with varying distances to screen center

**Problem (you already identified):**
- Corner cues (grid_11, grid_33): 15.2° from center
- Edge cues (grid_12, grid_21): 10.8° from center
- Center cue (grid_22): 0° from center

**Saccade amplitude confound:**
- Longer saccades → greater endpoint variability
- Different saccade latencies by amplitude
- May bias where Fix2 lands

**Recommendation for FUTURE studies:**
- Use uniform-eccentricity cue grid (all cues 8-10° from center)
- Or: Include cue distance as covariate in mixed model

**For CURRENT data:**
```python
# In analysis
model_formula = """
    distance_px ~ C(center) + cue_distance_from_center + C(center):cue_distance_from_center + ...
"""

# This tests if center effect depends on saccade amplitude
```

**Alternative:** Report cue position as covariate, show it doesn't interact with center effect

---

## **ANALYSIS ENHANCEMENTS**

### **Enhancement 5: Effect Size Reporting** ⭐⭐⭐ (CRITICAL FOR PUBLICATION)

**Current:** p-values only

**Add:** Cohen's d, partial η², confidence intervals

**Why:** Tier-1 journals (Nature, Science, Psych Science) require effect sizes since 2016

**Implementation:**
```python
import numpy as np
from scipy import stats

def compute_cohens_d(group1, group2):
    """Cohen's d with pooled standard deviation"""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    d = (np.mean(group1) - np.mean(group2)) / pooled_std

    return d

# Report as:
# "COM showed smaller distance than CHC (M_diff = 31.7 px, 95% CI [18.2, 45.2], d = 0.72)"
```

**Interpretation guidelines:**
- d = 0.2: small
- d = 0.5: medium
- d = 0.8: large

**With 20 participants × 702 trials, you have 80% power to detect d > 0.3**

---

### **Enhancement 6: Bayesian Analysis (Supplementary)** ⭐⭐

**Current:** Frequentist stats (p-values)

**Enhancement:** Add Bayesian analysis for robustness

**Why:**
- Provides evidence FOR null hypothesis (important if no center dominates)
- Tier-1 journals increasingly expect Bayesian alternatives
- Quantifies uncertainty better than p-values

**Implementation:**
```python
# Install: pip install pymc3 arviz

import pymc3 as pm

with pm.Model() as model:
    # Priors
    center_effect = pm.Normal('center_effect', mu=0, sigma=50, shape=4)
    sigma = pm.HalfNormal('sigma', sigma=50)

    # Likelihood
    mu = center_effect[center_idx]  # Index by center type
    y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=distances)

    # Sample
    trace = pm.sample(2000, return_inferencedata=True)

# Report Bayes Factors:
# "Bayesian analysis showed decisive evidence for COM advantage (BF10 > 100)"
```

**Alternative (simpler):** Use JASP software for Bayesian t-tests, report in supplement

---

### **Enhancement 7: Machine Learning Classifier (Exploratory)** ⭐

**Research question:** Can we predict which center will win from **trial features**?

**Features:**
- Image category
- Polygon case
- Cue position
- Participant baseline bias
- Trial number (fatigue)

**Implementation:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

# Prepare data
X = data[['category_encoded', 'polygon_case_encoded', 'cue_distance',
          'participant_baseline_bias', 'trial_in_session']]
y = data['fix2_winner']  # com/chc/bbc/icc

# Train classifier
rf = RandomForestClassifier(n_estimators=100, random_state=42)
accuracy = cross_val_score(rf, X, y, cv=5).mean()

print(f"Prediction accuracy: {accuracy*100:.1f}%")

# Feature importance
for feature, importance in zip(X.columns, rf.feature_importances_):
    print(f"{feature}: {importance:.3f}")
```

**Expected result:**
- If COM truly dominates: accuracy ~80-90% (high predictability)
- If context-dependent: accuracy ~40-50% (better than 25% chance)

**Impact:** Shows sophistication, good for discussion section

---

### **Enhancement 8: Replication Analysis** ⭐⭐⭐ (IMPORTANT)

**You have 3 replicates per polygon case** - USE THIS!

**Analysis:**
```python
# Test consistency across replicates
for case in ['pair_C1', 'pair_C2', 'pair_C3', 'iso_com', 'iso_chc', 'iso_bbc', 'iso_icc']:
    # Get all 3 replicates for this case
    replicates = [f"{case}_01", f"{case}_02", f"{case}_03"]

    for rep in replicates:
        rep_data = data[data['polygon_id'] == rep]
        winner = rep_data['fix2_winner'].mode()[0]
        print(f"{rep}: Winner = {winner}")

    # Chi-square test: Are winners consistent across replicates?
    # If p > 0.05: winners ARE consistent (good!)
```

**Report:**
- "Results were highly consistent across the 3 replicate polygons for each case type (χ² < 2.5, p > 0.4 for all cases), indicating effects are not driven by specific polygon geometries."

**This is CRITICAL for ruling out shape-specific artifacts**

---

### **Enhancement 9: Publication-Ready Visualizations** ⭐⭐⭐

**Beyond the 4 basic plots, add:**

**Figure 5: Spatial Heatmap**
```python
import matplotlib.pyplot as plt
import numpy as np

# Create 2D histogram of Fix2 landing positions
fig, axes = plt.subplots(2, 2, figsize=(12, 12))

for i, center in enumerate(['com', 'chc', 'bbc', 'icc']):
    ax = axes[i // 2, i % 2]

    # All Fix2 positions
    x = data['fix2_x_px']
    y = data['fix2_y_px']

    # 2D histogram
    h = ax.hist2d(x, y, bins=50, cmap='hot')

    # Mark center position
    center_x = data[f'center_{center}_x_px'].iloc[0]
    center_y = data[f'center_{center}_y_px'].iloc[0]
    ax.scatter(center_x, center_y, c='cyan', s=200, marker='x', linewidths=3)

    ax.set_title(f'Fix2 Distribution - {center.upper()} center marked')
    ax.set_xlabel('X position (px)')
    ax.set_ylabel('Y position (px)')

plt.tight_layout()
plt.savefig('fig5_spatial_heatmap.png', dpi=300)
```

**Figure 6: Individual Differences**
```python
# Participant-level winner distributions
participant_winners = data.groupby(['participant_id', 'fix2_winner']).size().unstack(fill_value=0)

# Stacked bar chart
participant_winners.plot(kind='bar', stacked=True, figsize=(12, 6),
                         color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
plt.xlabel('Participant')
plt.ylabel('Number of Trials')
plt.title('Winner Distribution by Participant')
plt.legend(title='Winner', labels=['COM', 'CHC', 'BBC', 'ICC'])
plt.tight_layout()
plt.savefig('fig6_individual_differences.png', dpi=300)
```

---

## **DATA COLLECTION OPTIMIZATIONS**

### **Optimization 1: Adaptive Session Length** ⭐⭐

**Current:** Fixed 9 blocks × 39 trials

**Enhancement:** Monitor fatigue in real-time, adapt accordingly

**Implementation:**
```python
# In experiment runner, after each block:
def check_fatigue_indicators(block_data):
    """
    Check if participant is fatiguing:
    - Fixation success rate dropping
    - Validation errors increasing
    - Many trial aborts
    """
    success_rate = block_data['fixation_achieved'].mean()

    if success_rate < 0.80:
        # Offer break
        show_message("Take a 5-minute break? [Y/N]")
        # If Y, extend break to 5 min
        # If N, continue

    if block_number == 6:  # After 2/3 of experiment
        show_message("You're 2/3 done! Take a longer break? [Y/N]")
```

**Impact:** Reduces drop-outs, improves data quality

---

### **Optimization 2: Practice Block** ⭐⭐⭐ (RECOMMENDED)

**Current:** Jump straight into data collection

**Enhancement:** Add 10-trial practice block before Part A Block 1

**Benefits:**
- Familiarizes participants with task
- Reduces learning effects in early data
- Allows calibration refinement

**Implementation:**
```python
# In experiment runner, before Block 1:
practice_trials = create_practice_trials(n=10)  # Random subset
run_practice_block(practice_trials, show_feedback=True)

# Don't analyze practice data
```

---

### **Optimization 3: Validation Quality Gates** ⭐⭐⭐ (CRITICAL)

**Current:** Calibration runs but quality not enforced

**Enhancement:** Reject poor calibrations automatically

**Implementation:**
```python
# In run_calibration_and_validation():
def enforce_validation_quality(validation_rms, validation_max_err):
    """
    Reject calibration if quality too poor.
    """
    RMS_THRESHOLD = 0.75  # degrees (stricter than 1.5°)
    MAX_ERR_THRESHOLD = 1.5  # degrees

    if validation_rms > RMS_THRESHOLD:
        show_message(f"Calibration quality insufficient (RMS={validation_rms:.2f}°)")
        show_message("Please recalibrate.")
        return False  # Force recalibration

    if validation_max_err > MAX_ERR_THRESHOLD:
        show_message(f"Maximum error too high ({validation_max_err:.2f}°)")
        show_message("Please recalibrate.")
        return False

    return True  # Accept calibration
```

**Impact:** Ensures all data meets quality threshold

---

## **ANALYSIS PIPELINE ENHANCEMENTS**

### **Enhancement 10: Automated Exclusion Criteria** ⭐⭐⭐

**Create pre-registered exclusion pipeline:**

```python
def apply_exclusion_criteria(data):
    """
    Pre-registered exclusion criteria for confirmatory analysis.
    """
    exclusions = {
        'trials': [],
        'participants': []
    }

    # TRIAL-LEVEL EXCLUSIONS
    # 1. Missing Fix2
    data = data[data['fix2_exists'] == True]
    exclusions['trials'].append(('missing_fix2', (~data['fix2_exists']).sum()))

    # 2. Fix2 duration < 50ms (blink or artifact)
    data = data[data['fix2_duration_ms'] >= 50]
    exclusions['trials'].append(('short_duration', (data['fix2_duration_ms'] < 50).sum()))

    # 3. Fix2 onset latency < 100ms (anticipatory saccade)
    data = data[data['fix2_onset_latency_ms'] >= 100]
    exclusions['trials'].append(('anticipatory', (data['fix2_onset_latency_ms'] < 100).sum()))

    # 4. Fix2 outside screen bounds (tracking loss)
    screen_w, screen_h = 3840, 2160
    data = data[
        (data['fix2_x_px'] >= 0) & (data['fix2_x_px'] <= screen_w) &
        (data['fix2_y_px'] >= 0) & (data['fix2_y_px'] <= screen_h)
    ]
    exclusions['trials'].append(('out_of_bounds', len(data[
        (data['fix2_x_px'] < 0) | (data['fix2_x_px'] > screen_w) |
        (data['fix2_y_px'] < 0) | (data['fix2_y_px'] > screen_h)
    ])))

    # PARTICIPANT-LEVEL EXCLUSIONS
    # 1. < 70% valid trials
    participant_validity = data.groupby('participant_id').size() / 702  # Expected trials
    low_validity = participant_validity[participant_validity < 0.70].index
    data = data[~data['participant_id'].isin(low_validity)]
    exclusions['participants'].append(('low_validity', list(low_validity)))

    # 2. Extreme outliers (> 3 SD from group mean on key metrics)
    # (e.g., mean distance to all centers)

    # Report exclusions
    print("EXCLUSION SUMMARY")
    print("="*60)
    print("Trial-level:")
    for reason, count in exclusions['trials']:
        print(f"  {reason}: {count} trials")
    print("\nParticipant-level:")
    for reason, pids in exclusions['participants']:
        print(f"  {reason}: {pids}")

    return data, exclusions
```

---

## **RECOMMENDATIONS PRIORITY LIST**

### **MUST DO (Before Next 20 Participants)**
1. ✅ **Switch to drift_correction method** (already implemented)
2. ✅ **Enforce validation quality gates** (RMS < 0.75°)
3. ✅ **Add practice block** (10 trials before Part A)
4. ✅ **Test polygon visualization tool** (verify no clipping)

### **SHOULD DO (During Data Collection)**
5. ⭐ **Record eye dominance** (30 seconds per participant)
6. ⭐ **Monitor fatigue indicators** (offer breaks if success rate drops)
7. ⭐ **Log validation RMS/max error** (manually if needed)

### **NICE TO HAVE (During Analysis)**
8. ⭐ **Compute Cohen's d effect sizes**
9. ⭐ **Test replicate consistency**
10. ⭐ **Add temporal dynamics analysis** (Fix1→Fix2→Fix3→Fix4)
11. ⭐ **Create spatial heatmaps**
12. ⭐ **Bayesian supplementary analysis**

---

## **ESTIMATED IMPACT ON PUBLICATION**

**Current design (without enhancements):**
- Target journals: JEMR, Attention Perception & Psychophysics, Vision Research
- Estimated acceptance rate: ~40-50%

**With high-priority enhancements:**
- Target journals: J Vision, Psychological Science, Cognition
- Estimated acceptance rate: ~60-70%

**With all enhancements:**
- Target journals: Nature Human Behaviour, PNAS, Current Biology
- Estimated acceptance rate: ~30-40% (but MUCH higher impact)

---

## **QUESTIONS TO CONSIDER**

1. **Do you want to add eye dominance testing?** (Takes 30 sec, high value)
2. **Should we enforce stricter validation criteria** (RMS < 0.75° instead of 1.5°)?
3. **Practice block before Part A?** (Recommended)
4. **Bayesian analysis in supplement?** (Optional but impressive)

Let me know which enhancements you want to implement, and I'll help you code them!

---

**Next Steps:**
1. Review this document
2. Decide which enhancements to implement
3. Test on 1 pilot participant
4. Roll out to full data collection
