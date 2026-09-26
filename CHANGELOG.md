# CHANGELOG v0.4.0 — CMS-HCC V28 validation, MCE edits, 2026/2027 data

## Summary

A validation-and-data release focused on CMS-HCC **V28** (the payment model for
2026–2027). hccinfhir's V28 output was verified **numerically identical** to the
official CMS V28 reference engine (mapping, edits, hierarchies, categories,
interactions, coefficients — exact score parity across community/institutional
segments and a pediatric case). Along the way: refreshed 2026 reference data,
added 2027 data, ported the multi-model and MCE diagnosis edits, and fixed an
age-0 bug.

**Backward compatibility:** No API breaks — every new parameter has a default and
no signatures/return types changed. Scores *can* change on upgrade (see
[Upgrade notes](#upgrade-notes-scores-may-change)); the changes are corrections and,
for V28, strictly additive.

## New features

- **`switch_edits` parameter** on `calculate_raf` and `HCCInFHIR` (default `True`,
  matching the CMS default) — toggles the MCE (Medicare Code Editor) age-validity
  edits. Set `False` to reproduce pre-0.4.0 behavior exactly.
- **MCE age-validity edits** ported for V28 (303 codes) as `mce_age` rows in
  `ra_dx_edits.csv`.
- **Multi-model diagnosis edits** — `ra_dx_edits.csv` now covers V22, V24, ESRD V21,
  and ESRD V24 (previously V28-only), rebuilt from the CMS SAS edit macros.
- **2027 reference data** added as opt-in options: `ra_dx_to_cc_2027.csv`,
  `ra_eligible_cpt_hcpcs_2027.csv` (registered in the filename type literals).
- **Docs & tooling:** `docs/cms_v28_comparison.md` (CMS-vs-hccinfhir comparison,
  when-to-use guidance, findings), `resources/parity_harness/run_parity.py`
  (reproducible numeric parity), and `src/hccinfhir/data/README.md` (data provenance
  + regeneration).

## Data updates

- **`ra_dx_to_cc_2026.csv` refreshed** from mimilabs. The prior file was mislabeled
  (it held the CMS *2025* model-year mappings); it now holds 2026. For V28 the change
  is **purely additive** — 134 newer ICD-10 codes gained mappings, **0 existing
  mappings changed or removed**.
- **`ra_eligible_cpt_hcpcs_2026.csv` refreshed** (6,748 → 6,792 codes).

## Fixes

- **Age-0 categorization** — `categorize_demographics(age=0, …)` raised `ValueError`
  on the community/continued path (reachable for ESRD-model infants). Now categorizes
  to the `0_34` band. This only *removes* a crash.
- **`filter.py` default** CPT file aligned `2025 → 2026` (was a year behind the rest
  of the defaults).

## Upgrade notes (scores may change)

All changes are corrections; no code changes are required to keep running. Numeric
output can move in these cases:

- **V28 (default):** strictly additive — a beneficiary's RAF is unchanged unless they
  carry one of the 134 newly-mapped ICD-10 codes, in which case it can only *increase*.
  No existing mapping changed.
- **V22 / V24 / ESRD:** now apply their CMS age/sex edits (e.g. hemophilia D66/D67 in
  females → CC48). Affects only beneficiaries with those specific diagnoses.
- **MCE (on by default):** invalidates codes outside their MCE-valid age range. **Zero
  impact for beneficiaries age ≥ 15** (the entire aged population and nearly all
  disabled); affects only pediatric/edge cases. Set `switch_edits=False` to disable.

If you keep golden/regression baselines on scores, re-baseline on upgrade. For
bit-identical pre-0.4.0 output: `switch_edits=False` plus
`dx_cc_mapping_filename="ra_dx_to_cc_2025.csv"`.

---

# CHANGELOG v0.2.7 - Bug Fixes and Interaction Improvements

## Summary

This release fixes critical bugs in RxHCC coefficient lookups and interaction categorization, with contributions from the community.

## Bug Fixes

### 1. RxHCC Coefficient Lookup Fix

**File:** `src/hccinfhir/model_coefficients.py`

**Problem:** RxHCC Model V08 disease coefficients were not being loaded. The code constructed lookup keys with `HCC` prefix (e.g., `rx_ce_nolowaged_hcc31`) but coefficient files use `RXHCC` prefix (e.g., `Rx_CE_NoLowAged_RXHCC31`).

**Impact:** All RxHCC disease scores were returning 0.

**Fix:** Added model-specific key construction:
```python
# For RxHCC models, use RXHCC prefix instead of HCC
if 'RxHCC' in model_name:
    key = (f"{prefix}RXHCC{hcc}".lower(), model_name)
else:
    key = (f"{prefix}HCC{hcc}".lower(), model_name)
```

**Contributor:** @anchalkatoch05 (PR #8)

### 2. LTIMCAID Demographic Categorization Fix

**File:** `src/hccinfhir/model_calculate.py`

**Problem:** The `LTIMCAID` interaction (LTI × Medicaid) was being included in `risk_score_hcc` instead of `risk_score_demographics`, causing incorrect RAF score breakdowns.

**Fix:** Added routing for `LTIMCAID` to `demographic_interactions`:
```python
elif key == 'LTIMCAID':
    demographic_interactions[key] = value
```

**Contributor:** @shackbarth (PR #9 - cherry-picked)

### 3. Substance Use Interaction Key Typo

**File:** `src/hccinfhir/model_interactions.py`

**Problem:** Interaction key `gSubstanceAbuse_gPsych` did not match coefficient files which use `gSubstanceUseDisorder_gPsych` (V24) or `gSubstanceAbuse_gPsychiatric` (V22).

**Fix:** Corrected key to `gSubstanceUseDisorder_gPsych`.

**Contributor:** @shackbarth (PR #10 - merged)

## Verification

| Model | Before | After |
|-------|--------|-------|
| RxHCC V08 (E11.9) | HCC RAF: 0.0 | HCC RAF: 0.247 |
| CMS-HCC V28 LTI+MCAID | Demographic RAF: 0.965 | Demographic RAF: 1.095 |

## Contributors

Thank you to our community contributors:
- **@shackbarth** - LTIMCAID routing fix, substance use key typo fix
- **@anchalkatoch05** - RxHCC coefficient lookup fix

---

# CHANGELOG v0.2.6 - ESRD Model Interactions Enhancement

## Summary

This change adds ESRD Functioning Graft duration interactions ("transplant bumps") and related LTI/LTIMCAID interactions, integrating a contributor's code with additional enhancements for completeness.

## Files Changed

### 1. `src/hccinfhir/model_interactions.py`

**Integrated into `create_demographic_interactions()`:**

| Feature | Description | Models |
|---------|-------------|--------|
| `LTIMCAID` | LTI × Medicaid interaction | V24, V28 Institutional |
| `LTI_Aged` / `LTI_NonAged` | LTI age interactions (prefix lookup) | ESRD V24 Dialysis |
| `LTI_GE65` / `LTI_LT65` | LTI age interactions (no-prefix lookup) | ESRD V24 Graft Institutional |
| `Originally_ESRD_Female` / `Originally_ESRD_Male` | Originally entitled due to ESRD | ESRD V21, V24 Dialysis |
| `MCAID_Female_Aged` / `MCAID_Female_NonAged` | Medicaid × sex × age | ESRD V21 Dialysis, Graft |
| `MCAID_Male_Aged` / `MCAID_Male_NonAged` | Medicaid × sex × age | ESRD V21 Dialysis, Graft |
| `GE65_DUR4_9` / `LT65_DUR4_9` | 4-9 month duration bumps | ESRD V21 |
| `GE65_DUR10PL` / `LT65_DUR10PL` | 10+ month duration bumps | ESRD V21 |
| `FGC_*_DUR4_9_ND_PBD` | Community 4-9 month, Non-Dual/Partial Dual | ESRD V24 |
| `FGC_*_DUR10PL_ND_PBD` | Community 10+ month, Non-Dual/Partial Dual | ESRD V24 |
| `FGI_*_DUR4_9_ND_PBD` | Institutional 4-9 month, Non-Dual/Partial Dual | ESRD V24 |
| `FGI_*_DUR10PL_ND_PBD` | Institutional 10+ month, Non-Dual/Partial Dual | ESRD V24 |
| `FGC_*_DUR4_9_FBD` | Community 4-9 month, Full Benefit Dual | ESRD V24 |
| `FGC_*_DUR10PL_FBD` | Community 10+ month, Full Benefit Dual | ESRD V24 |
| `FGI_*_DUR4_9_FBD` | Institutional 4-9 month, Full Benefit Dual | ESRD V24 |
| `FGI_*_DUR10PL_FBD` | Institutional 10+ month, Full Benefit Dual | ESRD V24 |
| `FGC_PBD_*_flag` | PBD flag for Community | ESRD V24 |
| `FGI_PBD_*_flag` | PBD flag for Institutional | ESRD V24 |

**Removed:** `create_model_demographic_interactions()` function - logic merged into `create_demographic_interactions()` for model-agnostic approach.

**Removed from `apply_interactions()`:** Call to `create_model_demographic_interactions()` (no longer needed).

### 2. `src/hccinfhir/model_coefficients.py`

**Added no-prefix coefficient lookup** (lines 121-131):

```python
# No-prefix lookup for ESRD duration coefficients stored without prefix
if (interaction_key.startswith('FGC') or
    interaction_key.startswith('FGI') or
    interaction_key.startswith('GE65_DUR') or
    interaction_key.startswith('LT65_DUR') or
    interaction_key in ('LTI_GE65', 'LTI_LT65')):
    key = (interaction_key.lower(), model_name)
    if key in coefficients:
        value = coefficients[key]
        output[interaction_key] = value
```

## Contributor's Original Code vs Final Implementation

### What Contributor Provided

1. `create_model_demographic_interactions()` function with:
   - LTIMCAID for V24/V28
   - FGC interactions for ND_PBD (V24)
   - FGI interactions for ND_PBD (V24)
   - FGC interactions for FBD (V24) - **missing FGI**

2. FGC/FGI no-prefix lookup in `apply_coefficients()`

### Enhancements Added

| Enhancement | Reason |
|-------------|--------|
| **FGI coefficients for FBD** | Contributor only had FGC_*_FBD; SAS shows FGI_*_FBD also needed |
| **PBD flag coefficients** | SAS shows FGC_PBD_*_flag and FGI_PBD_*_flag for Partial Dual |
| **LTI_GE65/LTI_LT65** | ESRD V24 Graft Institutional uses these (stored without prefix) |
| **ESRD V21 duration** | GE65_DUR*, LT65_DUR* for backward compatibility |
| **Originally_ESRD_Female/Male** | ESRD V21, V24 Dialysis - for originally ESRD entitled beneficiaries |
| **MCAID_Female/Male_Aged/NonAged** | ESRD V21 - V21 uses MCAID (general), V24 uses FBDual/PBDual |
| **Model-agnostic design** | Merged into single function; coefficient lookup filters by model |

## SAS Reference Files Used

- `E2125P1M.TXT` - ESRD V21 model (GE65_DUR*, MCAID)
- `E2425T1M.TXT` - ESRD V24 model (FGC_*, FGI_*, PBD flags, LTI_GE65/LT65)
- `V2423P2M.TXT` - CMS-HCC V24 model (LTIMCAID)
- `V2825T1M.TXT` - CMS-HCC V28 model (LTIMCAID)

## Test Coverage

Added `tests/test_esrd_interactions.py` with 35 test cases:

- ESRD V21 duration interactions (5 tests)
- ESRD V24 FGC interactions for ND_PBD (2 tests)
- ESRD V24 FGI interactions for ND_PBD (2 tests)
- ESRD V24 FGC interactions for FBD (2 tests)
- ESRD V24 FGI interactions for FBD (2 tests)
- ESRD V24 PBD flags (3 tests)
- ESRD V24 LTI_GE65/LTI_LT65 (3 tests)
- ESRD V21 Originally_ESRD (4 tests)
- ESRD V21 MCAID interactions (3 tests)
- V24/V28 LTIMCAID (3 tests)
- No-prefix coefficient lookups (4 tests)
- Integration tests (2 tests)

## Coefficient Lookup Pattern

| Interaction Type | Lookup Pattern | Example |
|------------------|----------------|---------|
| LTI_Aged/LTI_NonAged | With prefix | `DI_LTI_Aged` |
| LTI_GE65/LTI_LT65 | No prefix | `LTI_GE65` |
| FGC_*/FGI_* | No prefix | `FGC_GE65_DUR4_9_ND_PBD` |
| GE65_DUR*/LT65_DUR* | No prefix | `GE65_DUR4_9` |
| Originally_ESRD_* | With prefix | `DI_Originally_ESRD_Female` |
| MCAID_Female/Male_* | With prefix | `DI_MCAID_Female_Aged`, `GC_MCAID_Male_NonAged` |
| LTIMCAID | With prefix | `INS_LTIMCAID` |
