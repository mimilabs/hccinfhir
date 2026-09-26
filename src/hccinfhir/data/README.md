# Data Files — Provenance & Regeneration

Maintainer-facing notes for the CMS reference CSVs in this directory. These files
are **generated from the [mimilabs](https://mimilabs.ai) `mimi_ws_1` catalog**, not
hand-maintained. This doc records the source tables, the regeneration SQL, and the
conventions the loader code depends on.

> User-facing docs (how to *use* the library) live in the top-level `README.md`.
> This file is about how to *rebuild the data*.

## Source tables

| CSV pattern | mimilabs source table |
|---|---|
| `ra_dx_to_cc_*.csv` | `mimi_ws_1.cmspayment.ra_dx_to_cc_mapping` |
| `ra_eligible_cpt_hcpcs_*.csv` | `mimi_ws_1.cmspayment.ra_eligible_cpt_hcpcs` |

`ra_dx_edits.csv` has a different source — see [Diagnosis edits](#diagnosis-edits-ra_dx_editscsv)
below. Other files (`ra_hierarchies_*.csv`, `ra_coefficients_*.csv`,
`hcc_is_chronic.csv`) are **not** covered here yet.

## Diagnosis edits (`ra_dx_edits.csv`)

Age/sex edits applied to ICD-10→CC mappings **after** the base mapping and
**before** hierarchies (see `model_edits.py`). Unlike the mapping/CPT files, these
are **not** in mimilabs — they live only in the CMS model software packages.

**Sources:** (1) the mandatory ("RTI") edit blocks of the CMS SAS edit macros (2026
midyear-final packages), staged in `resources/sas_edit_macros/`; and (2) the V28
package's resolved `MCE_AGE_CONDITION` column, for the `mce_age` rows (see below).

| Macro | model_name(s) produced |
|---|---|
| `V28I0ED3.TXT` | CMS-HCC Model V28 |
| `V22I0ED4.TXT` | CMS-HCC Model V22 |
| `V24I0ED3.TXT` | CMS-HCC Model V24 **and** CMS-HCC ESRD Model V24 |
| `V21I0ED4.TXT` | CMS-HCC ESRD Model V21 |
| `R08I0ED1.TXT` | RxHCC Model V08 — *no mandatory edits* (none emitted) |

**Regenerate:** `python resources/sas_edit_macros/build_ra_dx_edits.py`

**Key facts / gotchas:**
- **Edits differ by model.** The same code can map to a different CC, or be
  invalidated vs. reassigned, depending on the model (e.g. D66 female → CC112 in
  V28 but CC48 in V22/V24; J41x under-18 is *invalid* in V28 but *reassigned to
  CC112* in V22/V24). Never share edit rows across models.
- **No standalone CMS-HCC V24 (community) package** was available; its edits come
  from `V24I0ED3.TXT` (shipped in the ESRD V24 package), which is the CMS-HCC V24
  edit macro and applies to both the community and ESRD V24 models.
- **MCE edits ARE included** as `edit_type='mce_age'` rows (V28 only), gated at
  runtime by the `switch_edits` parameter (default `True`, matching CMS). Source: the
  V28 package's resolved `MCE_AGE_CONDITION` column (the SAS `%IF &SEDITS` block only
  references the named format `IAGEHYBCY25MCE`, which doesn't ship as text). That MCE
  format is shared by V22/V24/ESRD V21/V24 (so the rules apply there too for shared
  codes); RxHCC V08 uses a different variant and is not covered.
- **Bounded ranges** (e.g. F3481 valid only ages 6–18) are encoded with *both*
  `age_min` and `age_max` set; `apply_edits`' OR-logic fires "outside [lo,hi]",
  which is exactly the invalidate-outside-range semantics these edits need.
- Base file is authoritative source for the edits, but is **model-year-tied** to
  the packages used (2026 midyear-final here). Re-validate when adopting a new
  model year, and add other models only when their CMS packages are available.

## Naming convention (read this first)

**Current convention: repo `_YYYY.csv` corresponds to mimilabs `year = YYYY`.**

⚠️ Files created before this convention are offset by one year — e.g. the original
`ra_dx_to_cc_2026.csv` and `ra_eligible_cpt_hcpcs_2026.csv` were actually built from
mimilabs `year = 2025` / vintage `2025-01-01`. When regenerating, pull the mimilabs
`year` that matches the target filename, per the convention above.

In `ra_dx_to_cc_mapping`, use the `year` column as the model/performance year and pin
`mimi_src_file_date` to the matching `YYYY-01-01` vintage so a later refresh vintage
doesn't silently mix in. In `ra_eligible_cpt_hcpcs` there is **no** `year` column —
`mimi_src_file_date` is the only time axis, so a `YYYY-01-01` vintage maps to the
`_YYYY.csv` file.

## Format contract (the loaders depend on these)

- **dx → cc** (`ra_dx_to_cc_*.csv`): header `diagnosis_code,cc,model_name`.
  ICD-10 codes are stored **without dots** (`A0103`, not `A01.03`). `cc` is a
  categorical string label — never numeric.
- **CPT/HCPCS** (`ra_eligible_cpt_hcpcs_*.csv`): single column `cpt_hcpcs_code`.
  Codes are **strings** — leading zeros (`00520`) and alpha codes (`C7544`) must be
  preserved; do not cast to integer.

## Regeneration SQL

Replace `<YEAR>` / `<YYYY-01-01>` with the target. Each query already matches the
column names, ordering, and string handling the CSVs expect.

### dx → cc mapping

```sql
SELECT DISTINCT
       REPLACE(TRIM(diagnosis_code), '.', '') AS diagnosis_code,
       TRIM(cc)                               AS cc,
       model_name
FROM mimi_ws_1.cmspayment.ra_dx_to_cc_mapping
WHERE year = <YEAR>
  AND mimi_src_file_date = DATE '<YYYY-01-01>'   -- pin vintage == year
ORDER BY model_name, diagnosis_code;
```

### eligible CPT/HCPCS

```sql
SELECT DISTINCT TRIM(cpt_hcpcs_code) AS cpt_hcpcs_code
FROM mimi_ws_1.cmspayment.ra_eligible_cpt_hcpcs
WHERE mimi_src_file_date = DATE '<YYYY-01-01>'
  AND is_included = 'yes'
ORDER BY cpt_hcpcs_code;
```

## Model coverage by year (dx → cc)

CMS retires models over time, so the model set per file shrinks. Verify before
regenerating — a "missing" model is usually CMS no longer publishing it, not a bug.

| Model | 2025 | 2026 | 2027 |
|---|:-:|:-:|:-:|
| CMS-HCC ESRD V21 | ✓ | ✓ | ✓ |
| CMS-HCC ESRD V24 | ✓ | ✓ | ✓ |
| CMS-HCC V22 | ✓ | ✓ | ✓ |
| CMS-HCC V24 | ✓ | ✓ | — |
| CMS-HCC V28 | ✓ | ✓ | ✓ |
| RxHCC V05 | ✓ | — | — |
| RxHCC V08 | ✓ | ✓ | ✓ |

Notes:
- **RxHCC V05** is dropped from `year = 2026` onward.
- **CMS-HCC V24** is dropped from `year = 2027` onward.
- **CPT/HCPCS**: the latest published vintage is `2026-01-01` (~6,792 codes). There is
  **no 2027 eligibility vintage yet** — a `ra_eligible_cpt_hcpcs_2027.csv` would just
  reuse the `2026-01-01` data until CMS/mimilabs publishes one.

## To verify what's available before regenerating

```sql
-- dx → cc: which years, vintages, and models exist
SELECT mimi_src_file_date, year,
       CONCAT_WS(' | ', SORT_ARRAY(COLLECT_SET(model_name))) AS models
FROM mimi_ws_1.cmspayment.ra_dx_to_cc_mapping
GROUP BY mimi_src_file_date, year
ORDER BY mimi_src_file_date DESC, year DESC;

-- CPT/HCPCS: which vintages exist and code counts
SELECT mimi_src_file_date, COUNT(DISTINCT cpt_hcpcs_code) AS n_codes
FROM mimi_ws_1.cmspayment.ra_eligible_cpt_hcpcs
GROUP BY mimi_src_file_date
ORDER BY mimi_src_file_date DESC;
```
