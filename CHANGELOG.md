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
