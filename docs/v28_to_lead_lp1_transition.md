# From CMS-HCC V28 to LEAD Prospective V1

This article explains how scores behave when a beneficiary moves from the standard
CMS-HCC V28 model to the **CMMI-HCC Prospective Model V1** used by the Long-term
Enhanced Accountable Care Organization Design (LEAD) Model. In `hccinfhir`, the
models are selected with `cms-v28` and `lead-p-v1`.

> **Scope:** LP1 is for LEAD beneficiaries who are not High Needs and are in the
> community population. This is not an analysis of LEAD Concurrent V2 (`lead-c-v2`),
> institutional policy adjustments, new enrollees, or ESRD scoring.

## Executive takeaways

- **The clinical classification does not change.** LP1 uses the V28 ICD-10-CM
  mapping, 115 payment HCCs, age/sex edits, and the same 60-parent/149-edge
  hierarchy. The same diagnoses produce the same active HCC list.
- **The score can change substantially.** LP1 was separately calibrated for the
  LEAD non-High Needs population. Its demographic, HCC, and interaction coefficients
  are not a rescaling of V28.
- **The direction is not uniform.** In common non-dual aged examples below, the
  demographic floor rises and several common HCC coefficients rise, but diabetes and
  moderate CKD increments fall to zero. A six-condition example scores 15% lower.
- **Segment matters.** In an illustrative prevalence-weighted mock study, mean score
  changes range from +0.6% to +19.2% across the six community segments.
- **Raw score movement is not benchmark impact.** CMMI says the recalibrated model is
  applied to both historical base years and performance years. Relative change over
  time matters more than a one-time difference between model scores.

## What stays the same—and what changes

| Component | CMS-HCC V28 | LEAD Prospective V1 |
|---|---|---|
| ICD-10-CM → HCC mapping | V28 | Same V28 mapping |
| Payment HCCs | 115 | Same 115 HCCs |
| Hierarchies | 60 parents / 149 edges | Exact same edges |
| Community segments | CNA, CND, CFA, CFD, CPA, CPD | Same six segments |
| Other segments | Institutional and new-enrollee coefficients included | Not included in LP1 coefficient tables |
| HCC-count variables | D1–D10P structure; nonzero uplift begins at D5 | Excluded from the LP1 specification |
| Disease interactions | Six V28 disease interactions plus five disabled-condition interactions | Six V28 disease interactions; no five additional disabled-condition terms |
| Coefficient rows in bundled data | 1,237 across community, institutional, and new-enrollee segments | 801 across six community segments |

The practical consequence is important: **migration is a scoring change, not a
recoding change**. If an implementation produces different HCCs under LP1 and V28
for the same beneficiary, that is an implementation defect rather than intended
model behavior.

## Common HCCs: coefficient changes are condition-specific

The chart below compares raw HCC coefficients in the community non-dual aged (CNA)
segment for the 12 most prevalent V28 payment HCCs with reported sample sizes in the
2024 CMS Risk Adjustment Report to Congress.

![CNA coefficients for common HCCs under V28 and LP1](assets/v28-to-lp1-common-hcc-coefficients.svg)

Several patterns stand out:

- HCC 238 (specified arrhythmias) rises from **0.2990 to 0.4001**.
- HCC 127 (mild/unspecified dementia) rises from **0.3410 to 0.5648**.
- HCC 93 (rheumatoid/inflammatory disorders) rises from **0.6170 to 0.7676**.
- HCC 213 (cardiorespiratory failure/shock) falls from **0.3700 to 0.2199**.
- HCCs 37 and 38 (diabetes) fall from **0.1660 to 0** in CNA.
- HCC 329 (moderate CKD, except stage 3B) falls from **0.1270 to 0** in CNA.

Those zero HCC increments do not mean LP1 ignores the beneficiary. LP1 can place
more weight in the age/sex base and in other conditions or interactions. The
coefficients are also segment-specific; the CNA examples should not be copied to a
disabled or dual segment.

## Concrete beneficiary examples

These examples hold the beneficiary constant at **male, age 72, community non-dual**
and supply the same already-hierarchized V28 HCCs to both models.

| Example | HCCs | V28 | LP1 | Change |
|---|---:|---:|---:|---:|
| No payment HCCs | — | 0.396 | 0.646 | +63.1% |
| Diabetes with chronic complications | 37 | 0.562 | 0.646 | +14.9% |
| Morbid obesity | 48 | 0.582 | 0.880 | +51.2% |
| Specified heart arrhythmia | 238 | 0.695 | 1.046 | +50.5% |
| Acute-on-chronic heart failure | 224 | 0.756 | 0.977 | +29.2% |
| Diabetes + heart failure | 37, 224 | 1.034 | 1.091 | +5.5% |
| Heart failure + stage 4 CKD | 224, 327 | 1.446 | 1.311 | −9.3% |
| Six-condition profile | 37, 48, 224, 238, 280, 327 | 2.785 | 2.367 | −15.0% |

![Representative V28 and LP1 scores](assets/v28-to-lp1-example-scores.svg)

The table illustrates why a single conversion factor will not work:

1. The LP1 demographic base for this persona is 0.6459 versus 0.3960 in V28.
2. LP1's CNA coefficient for HCC 37 is zero, so the diabetes-only case remains at
   the LP1 demographic score.
3. Interactions can offset condition-level reductions. Diabetes plus heart failure
   is only 5.5% higher even though the single-condition examples rise more.
4. V28 adds an HCC-count coefficient at five or more active HCCs; LP1 deliberately
   excludes count variables. That contributes to the lower six-condition result.

These are risk-score comparisons, not predictions of paid dollars or benchmark
changes.

## A prevalence-weighted mock population

To explore population behavior without beneficiary-level claims, we built a small,
fully reproducible simulation using the V28 HCC marginal sample sizes in Mimilabs'
copy of the 2024 CMS Risk Adjustment Report to Congress.

### Data and assumptions

| Item | Mock-study choice |
|---|---|
| Source population | CMS 2024 Report-to-Congress V28 sample: 28,248,982 beneficiaries |
| HCC inputs | 115 payment HCC rows; 112 have explicit sample sizes |
| HCC generation | Independent Bernoulli draw using each reported marginal prevalence |
| Hierarchies | V28/LP1 hierarchy applied after each draw |
| Profiles | 10,000 identical HCC draws scored in each segment |
| Sex | 50% female / 50% male |
| Representative ages | 72 for aged segments; 60 for disabled segments |
| Illustrative mix | CNA 50%, CND 10%, CFA 15%, CFD 5%, CPA 15%, CPD 5% |
| Random seed | 20261126 |

Three grouped payment rows—HCC 125, HCC 126, and HCC 328—have blank standalone
sample sizes in the source table and are not independently drawn. Related HCC 127
and HCC 329 rows remain in the simulation. This is one reason the study should be
read directionally rather than as an estimate.

### Results

| Segment | Population | Mean V28 | Mean LP1 | Change |
|---|---|---:|---:|---:|
| CNA | Non-dual aged | 0.986 | 1.176 | +19.2% |
| CND | Non-dual disabled | 0.983 | 1.105 | +12.3% |
| CFA | Full-dual aged | 1.246 | 1.312 | +5.3% |
| CFD | Full-dual disabled | 1.173 | 1.180 | +0.6% |
| CPA | Partial-dual aged | 0.999 | 1.036 | +3.7% |
| CPD | Partial-dual disabled | 0.974 | 1.044 | +7.2% |
| Illustrative mix | Assumed weights above | 1.036 | 1.162 | +12.2% |

![Mock population V28 and LP1 mean scores by segment](assets/v28-to-lp1-mock-population.svg)

The useful signal is not the +12.2% mixed-population result—it depends directly on
invented segment weights. The useful signal is the **spread across segments**. LP1
redistributes modeled risk differently across eligibility groups even when every
segment receives the same HCC prevalence draws.

## What to expect in a real transition analysis

1. **HCC prevalence should be stable between the two runs.** Mapping and hierarchy
   parity makes this a valuable quality-control check.
2. **The score distribution will re-center by segment.** Always stratify CNA, CND,
   CFA, CFD, CPA, and CPD before examining an overall average.
3. **Condition mix will matter more than average HCC count alone.** Some common HCCs
   gain weight while others lose it, and LP1 removes the explicit count uplift.
4. **Interaction cohorts deserve separate review.** Diabetes–heart failure,
   heart failure–kidney, heart failure–chronic lung, chronic lung–cardiorespiratory
   failure, heart failure–HCC 238, and disabled substance-use–psychiatric combinations
   can behave differently from sums of isolated HCCs.
5. **Do not infer benchmark or revenue impact from a cross-sectional RAF ratio.** A
   proper study must rescore the same ACO population in historical base and
   performance periods, then apply LEAD eligibility and benchmark policy.

## Running both models in `hccinfhir`

```python
from hccinfhir import Demographics, HCCInFHIR

demographics = Demographics(age=72, sex="M", dual_elgbl_cd="00")
diagnoses = ["E11.22", "I50.23", "N18.4"]

v28 = HCCInFHIR(model_name="cms-v28")
lp1 = HCCInFHIR(model_name="lead-p-v1")

v28_result = v28.calculate_from_diagnosis(diagnoses, demographics)
lp1_result = lp1.calculate_from_diagnosis(diagnoses, demographics)

assert set(v28_result.hcc_list) == set(lp1_result.hcc_list)
print(v28_result.risk_score, lp1_result.risk_score)
```

LP1 does not require `model_inputs`; those are currently specific to LEAD Concurrent
V2.

## Limitations

This mock study is intentionally simple:

- Marginal HCC prevalence does not preserve real comorbidity correlations.
- Fixed representative ages and a 50/50 sex split are not population estimates.
- Segment weights are illustrative and are not sourced from CMS or CMMI.
- It omits coding changes, eligibility churn, new enrollees, institutional policy,
  ESRD, normalization, frailty, and ACO benchmark mechanics.
- Report-to-Congress counts are aggregate and cannot reproduce beneficiary-level HCC
  combinations.
- Scores from separately calibrated models should not be interpreted as dollars or
  as a causal estimate of program impact.

Use actual beneficiary-level diagnoses, demographics, eligibility, and longitudinal
base/performance periods for an implementation or financial-impact study.

## Sources and reproducibility

- CMMI, *Long-term Enhanced Accountable Care Organization Design (LEAD) Model Risk
  Adjustment Overview*, version 1.1, September 2026: LP1 coefficients (pp. 12–43),
  hierarchy exclusions (pp. 44–45), and model notes (pp. 47–49).
- CMS, [Risk Adjustment Report to Congress](https://www.cms.gov/medicare/health-plans/medicareadvtgspecratestats/risk-adjustors-items/reporttocongress),
  2024 report, staged in Mimilabs as
  `mimi_ws_1.cmspayment.ra_report_to_congress`.
- [Prevalence snapshot](data/v28_report_to_congress_prevalence_2024.csv)
- [Example outputs](data/v28_to_lp1_common_examples.csv)
- [Common-HCC coefficient comparison](data/v28_to_lp1_common_hcc_coefficients.csv)
- [Mock-population results](data/v28_to_lp1_mock_population.csv)
- [Reproduction script](analysis/build_v28_to_lp1_study.py)

The prevalence extract is produced with:

```sql
SELECT CAST(REGEXP_REPLACE(hcc, 'HCC', '') AS INT) AS hcc,
       hcc_label,
       is_chronic,
       CAST(sample_size AS BIGINT) AS sample_size,
       sample_size / 28248982.0 AS prevalence
FROM mimi_ws_1.cmspayment.ra_report_to_congress
WHERE model_version = 'V28'
  AND model_year = 2024
  AND model_domain = 'CMS-HCC'
  AND is_in_payment_model = 'Y'
ORDER BY CAST(REGEXP_REPLACE(hcc, 'HCC', '') AS INT);
```
