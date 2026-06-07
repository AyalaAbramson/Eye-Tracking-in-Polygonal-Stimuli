## **Analysis Plan \- CB experiment 2**  **1\. Data and Preprocessing**

### **1.1 Data sources**

* EyeLink EDF/ASC event stream per participant and per part.  
* Trial manifest (`stimulus_manifest.csv`) containing:  
  * polygon ID/case/replicate, category, image ID, cue position, trial type (image/empty), mini-block index, and trial order.  
* Polygon JSON files containing vertices for each polygon.  
* (Optional) A derived table of computed centers per polygon in screen coordinates (precomputed for reproducibility).

### **1.2 Synchronization and trial segmentation**

* Trials are segmented using EyeLink messages:  
  * `TRIALID` / trial UID  
  * `STIM_ON`, `STIM_OFF`  
  * `TRIAL_RESULT`  
* A trial is considered **valid for analysis** if:  
  * `TRIAL_RESULT = OK`  
  * stimulus epoch exists and has fixation events  
  * (for primary analyses) Fixation 2 exists within stimulus epoch.

### **1.3 Coordinate systems and units**

All computations are performed in **screen pixel coordinates** and then converted to degrees of visual angle where needed.

* Use the monitor geometry and viewing distance to compute px/deg.  
* Report all distance-based results in **degrees** (primary) and pixels (secondary for debugging).

### **1.4 Computation of candidate centers**

For each polygon (in its final on-screen placement and scaling used during the experiment), compute:

* CoM (area centroid)  
* BBC (bounding box center)  
* CHC (centroid of convex hull)  
* ICC (center of maximum inscribed circle)

These centers must be computed **once per polygon** and stored (e.g., `centers_by_polygon.csv`) to guarantee reproducibility.

---

## **2\. Fixation Definition and Primary Epoch**

### **2.1 Fixation extraction**

* Fixations are extracted from EyeLink fixation events (standard parsing).  
* Only fixations whose timestamps overlap with `[STIM_ON, STIM_OFF]` are considered “in-epoch”.

### **2.2 Primary dependent measure: Fixation 2**

**Fixation 2** is defined as the **second fixation after stimulus onset** within the stimulus epoch.

Operationally:

1. Identify the first fixation event whose start time is ≥ `STIM_ON` (Fixation 1).  
2. The next fixation event within the epoch is Fixation 2\.  
3. If Fixation 2 does not exist (e.g., no second fixation during 4s), the trial is excluded from primary analyses but retained for secondary reporting (missingness diagnostics).

### **2.3 Fixation location**

Use fixation **(x,y)** as reported by EyeLink (typically fixation centroid).  
(If you later decide to use first sample vs centroid vs median, preregister it here; otherwise keep centroid.)

---

## **3\. Derived Metrics (Per Trial)**

For each valid trial with Fixation 2:

### **3.1 Distances to candidate centers**

Compute Euclidean distance (in degrees) from Fixation 2 to each center:  
\[  
d\_{k} \= |\\mathbf{f}\_2 \- C\_k|, \\quad k \\in {\\text{CoM,BBC,CHC,ICC}}  
\]

### **3.2 Winner label (per trial)**

Define the **trial-wise winner** as:  
\[  
\\text{winner} \= \\arg\\min\_k d\_k  
\]  
Store both:

* winner identity (categorical)  
* winner margin: (\\Delta \= d\_{\\text{2nd best}} \- d\_{\\text{best}}) as a confidence proxy

### **3.3 Normalized distances (optional but recommended)**

To avoid “scale” artifacts across polygons, also compute:

* **rank** of each center by distance (1=closest,…,4=farthest)  
* optionally a within-trial z-score across centers:  
  \[  
  z\_k \= \\frac{d\_k \- \\bar{d}}{\\mathrm{sd}(d)}  
  \]  
  These are robust to global shifts.

---

## **4\. Exclusion Rules (Pre-registered)**

### **4.1 Trial-level exclusions**

Exclude a trial from primary analysis if:

* Trial aborted (`TRIAL_RESULT = ABORTED` or equivalent)  
* Fixation 2 does not exist within stimulus epoch  
* (Optional) tracking loss exceeds a threshold during stimulus epoch (to be specified)

### **4.2 Participant-level exclusions**

Exclude a participant from confirmatory analyses if:

* Valid Fixation-2 trials \< **X%** of planned trials (threshold to be finalized)  
* Repeated failure to complete calibration/validation across mini-blocks (threshold to be finalized)

### **4.3 Reporting**

Report:

* % aborted trials  
* % trials missing Fixation 2  
* valid trial counts per participant, per part, and per condition

---

## **5\. Confirmatory Analyses**

### **5.1 Primary confirmatory question: “single winning center”**

Two complementary confirmatory endpoints are recommended (you can preregister both):

#### **Endpoint A: Distance-based winner (continuous)**

Model distances directly.

**Model A1 (main): linear mixed-effects on distance**  
Outcome: (d\_k) (distance in degrees)

Fixed effects:

* `center` (CoM/BBC/CHC/ICC) — primary predictor  
* `trial_type` (image vs empty) — control  
* `case_type` (all-far / pair / isolated / baseline) — control/interpretation  
* `category` — for robustness tests  
* interactions: `center × case_type`, `center × category` (preregistered)

Random effects (minimum):

* random intercepts for participant  
* random intercepts for polygon (or polygon ID nested in case)  
* random intercepts for image (for image trials)  
  Optional:  
* random slopes for `center` by participant (if stable)

Primary test:

* omnibus effect of `center` (center differences in mean distance)  
* planned pairwise contrasts: CoM vs BBC, CoM vs CHC, CoM vs ICC, etc. (Holm-corrected)

Interpretation:

* the center with lowest estimated marginal mean distance is the winner  
* require consistency across conditions (see 5.3)

#### **Endpoint B: Winner probability (categorical)**

Model probability that each center is closest.

**Model B1: multinomial mixed model** (or logistic in one-vs-rest form)  
Outcome: winner label

Predictors and random effects parallel to A1.

Primary test:

* whether one center has significantly higher win probability than others overall

This endpoint is intuitive and robust, but distance-based is typically more sensitive.

### **5.2 Robustness across categories (core claim)**

Goal: support the statement “winner is not explained by category”.

Confirmatory test:

* `center × category` interaction in Model A1 (and/or B1)  
* Acceptance criterion (conceptual):  
  * winner remains the same across categories (directionally consistent)  
  * any interaction effects are small relative to main center effect

Additionally, compute category-stratified summaries:

* per category: winner center, win probability, and mean distance ranking

### **5.3 Robustness across separation-tree cases**

Confirmatory tests:

* compare winner identity across:  
  * All-far  
  * Pair-separation  
  * Isolated-center  
* require that the inferred winner does not depend critically on a single case type

Deliverables:

* per case type: mean distances and win probabilities  
* within each case type: replicate consistency (see 5.4)

### **5.4 Replicate consistency (shape-specific artifact control)**

Within each non-baseline case, you have 3 polygon instantiations.  
Confirmatory check:

* compute winner per replicate polygon and assess agreement  
* include `polygon_id` random intercept in mixed models to soak shape idiosyncrasy  
* report heterogeneity across replicates (variance component)

---

## **6\. Secondary and Diagnostic Analyses**

### **6.1 Empty vs image trials**

Test whether the winner differs between:

* image trials (masked natural images)  
* empty trials (geometry-only)

Model:

* `center × trial_type` interaction (in A1/B1)

Interpretation:

* if geometry truly drives the effect, winner should persist in empty trials and remain stable in images

### **6.2 Time-on-task / fatigue**

Pre-registered covariates:

* `mini_block_index` (1..9)  
* `trial_in_block` (1..39)

Test:

* `center × mini_block_index` interaction  
* ensure winner is stable over time and not a fatigue artifact

### **6.3 Cue-position effects**

Since cue is balanced, include:

* `cue_pos_id` as covariate or random effect  
* test whether cue affects the winner (should not)

### **6.4 Sensitivity analyses**

Repeat primary analyses with:

* Fixation 1 and Fixation 3 (exploratory)  
* alternative fixation inclusion rules (e.g., excluding trials with extremely short Fix2 duration, threshold to be specified)

---

## **7\. Multiple Comparisons and Decision Criteria**

### **7.1 Multiplicity control**

* For pairwise center comparisons, use **Holm–Bonferroni** correction.  
* For multiple models/endpoints, clearly label:  
  * confirmatory (pre-registered primary)  
  * secondary (exploratory)

### **7.2 Declaring a “single winner”**

Declare a single winner if all of the following hold:

1. In the primary distance-based model, one center has the lowest estimated mean distance and is significantly better than each alternative center (Holm-corrected).  
2. Winner is consistent across:  
   * trial types (image vs empty) or at minimum not reversed  
   * categories (no reversal; interaction does not change winner)  
   * separation-tree case types (no reversal)  
3. Winner is not driven by a single replicate polygon (replicate agreement \+ random-effect stability).

(If you prefer a weaker/stronger criterion, lock it here.)

---

## **8\. Reporting Outputs (what will appear in the paper)**

Minimum set:

* Table: mean distance (deg) to each center with CIs, overall and per case type  
* Figure: win probability per center (overall; by category; by case type)  
* Replicate plot: per polygon replicate, winner distribution / distance ranks  
* Data quality: abort rates, missing Fix2, recalibrations per mini-block

---

## **9\. Reproducibility**

* Release:  
  * manifests  
  * polygon JSONs  
  * computed center coordinates per polygon  
  * analysis scripts and environment spec  
* All analysis uses manifest trial IDs as the single source of truth.

