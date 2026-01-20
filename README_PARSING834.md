# X12 834 Parsing Architecture

This document describes the hierarchical structure and parsing logic for X12 834 Benefit Enrollment transactions in HCCInFHIR.

## Transaction Structure

```
X12 834 Benefit Enrollment Transaction
══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ INTERCHANGE ENVELOPE (ISA/IEA)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ ISA ─── Interchange Control Header                                          │
│         ├── ISA06: Sender ID ──────────────────────────► source             │
│         └── ISA09: Date (YYMMDD) ──────────────────────► report_date        │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ FUNCTIONAL GROUP (GS/GE)                                                │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ GS ─── Functional Group Header                                          │ │
│ │        ├── GS02: Sender Code ────────────────────────► source (fallback)│ │
│ │        ├── GS04: Date (YYYYMMDD) ────────────────────► report_date      │ │
│ │        └── GS08: Version ────────────────────────────► validation       │ │
│ │                                                                         │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ TRANSACTION SET (ST/SE) - Loop 0000                                 │ │ │
│ │ ├─────────────────────────────────────────────────────────────────────┤ │ │
│ │ │ ST*834 ─ Transaction Set Header                                     │ │ │
│ │ │                                                                     │ │ │
│ │ │ BGN ───── Beginning Segment                                         │ │ │
│ │ │           └── BGN02: Reference ID ─────────────────► source prefix  │ │ │
│ │ │                                                                     │ │ │
│ │ │ ┌─────────────────────────────────────────────────────────────────┐ │ │ │
│ │ │ │ SPONSOR/PAYER LOOP - Loop 1000A/1000B                           │ │ │ │
│ │ │ ├─────────────────────────────────────────────────────────────────┤ │ │ │
│ │ │ │ N1*IN ── Plan/Insurer Name                                      │ │ │ │
│ │ │ │          └── N102: Plan Name ────────────────────► SLA prefix   │ │ │ │
│ │ │ └─────────────────────────────────────────────────────────────────┘ │ │ │
│ │ │                                                                     │ │ │
│ │ │ ╔═════════════════════════════════════════════════════════════════╗ │ │ │
│ │ │ ║ MEMBER LOOP - Loop 2000 (repeats per member)                    ║ │ │ │
│ │ │ ╠═════════════════════════════════════════════════════════════════╣ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ INS ───── Member Level Detail (LOOP START TRIGGER)              ║ │ │ │
│ │ │ ║           ├── INS03: Maintenance Type ───────► maintenance_type ║ │ │ │
│ │ │ ║           │         (001=Change, 021=Add, 024=Cancel)           ║ │ │ │
│ │ │ ║           ├── INS04: Maintenance Reason ─► maintenance_reason   ║ │ │ │
│ │ │ ║           ├── INS05: Benefit Status ─────► benefit_status_code  ║ │ │ │
│ │ │ ║           └── INS11/12: Death Date ──────► death_date           ║ │ │ │
│ │ │ ║                       (when INS11=D8, INS12=YYYYMMDD)           ║ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ ┌───────────────────────────────────────────────────────────┐   ║ │ │ │
│ │ │ ║ │ REF SEGMENTS (multiple, various qualifiers)               │   ║ │ │ │
│ │ │ ║ ├───────────────────────────────────────────────────────────┤   ║ │ │ │
│ │ │ ║ │ REF*0F ── Subscriber Number ───────────────► member_id    │   ║ │ │ │
│ │ │ ║ │ REF*6P ── Medicare Beneficiary ID ─────────► mbi          │   ║ │ │ │
│ │ │ ║ │ REF*F6 ── Medicare HICN ───────────────────► hic          │   ║ │ │ │
│ │ │ ║ │ REF*1D ── Medicaid ID ─────────────────────► medicaid_id  │   ║ │ │ │
│ │ │ ║ │ REF*AB ── Medi-Cal Aid Code ───────────────► aid_code     │   ║ │ │ │
│ │ │ ║ │ REF*ABB ─ Medicare Status (QMB/SLMB/QI) ──► dual status   │   ║ │ │ │
│ │ │ ║ │ REF*F5 ── Dual Eligibility Code ───────────► dual_elgbl_cd│   ║ │ │ │
│ │ │ ║ │ REF*DY ── CREC Code ───────────────────────► crec         │   ║ │ │ │
│ │ │ ║ │ REF*EJ ── Low Income Flag ─────────────────► low_income   │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ CA DHCS Specific (composite values with semicolons):      │   ║ │ │ │
│ │ │ ║ │ REF*23 ── CIN;Card_Issue_Date ────► cin, card_issue_date  │   ║ │ │ │
│ │ │ ║ │ REF*3H ── County;AID;Case# ───────► county, aid, case_num │   ║ │ │ │
│ │ │ ║ │ REF*6O ── Address Flags ──────────► res_addr_flag, etc.   │   ║ │ │ │
│ │ │ ║ │ REF*DX ── Contract;Carrier;Start ─► fed_contract, carrier │   ║ │ │ │
│ │ │ ║ │ REF*17 ── FAME Dates (composite):                          │   ║ │ │ │
│ │ │ ║ │           ├── Pos 0: Redetermination ──► fame_redetermination│   ║ │ │ │
│ │ │ ║ │           └── Pos 1: Death Date ───────► fame_death_date    │   ║ │ │ │
│ │ │ ║ └───────────────────────────────────────────────────────────┘   ║ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ ┌───────────────────────────────────────────────────────────┐   ║ │ │ │
│ │ │ ║ │ MEMBER NAME LOOP - Loop 2100A                             │   ║ │ │ │
│ │ │ ║ ├───────────────────────────────────────────────────────────┤   ║ │ │ │
│ │ │ ║ │ NM1*IL ── Insured/Member Name                             │   ║ │ │ │
│ │ │ ║ │           ├── NM103: Last Name ────────────► last_name    │   ║ │ │ │
│ │ │ ║ │           ├── NM104: First Name ───────────► first_name   │   ║ │ │ │
│ │ │ ║ │           ├── NM105: Middle Name ──────────► middle_name  │   ║ │ │ │
│ │ │ ║ │           └── NM109: Member ID ────────────► member_id    │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ PER ───── Contact Information                             │   ║ │ │ │
│ │ │ ║ │           └── PER*TE: Phone ───────────────► phone        │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ N3 ────── Street Address                                  │   ║ │ │ │
│ │ │ ║ │           ├── N301: Address Line 1 ────────► address_1    │   ║ │ │ │
│ │ │ ║ │           └── N302: Address Line 2 ────────► address_2    │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ N4 ────── City/State/Zip                                  │   ║ │ │ │
│ │ │ ║ │           ├── N401: City ──────────────────► city         │   ║ │ │ │
│ │ │ ║ │           ├── N402: State ─────────────────► state        │   ║ │ │ │
│ │ │ ║ │           ├── N403: Zip ───────────────────► zip          │   ║ │ │ │
│ │ │ ║ │           └── N406*CY: County ─────────────► county_id    │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ DMG ───── Demographics                                    │   ║ │ │ │
│ │ │ ║ │           ├── DMG02: DOB (YYYYMMDD) ───────► dob          │   ║ │ │ │
│ │ │ ║ │           ├── DMG03: Sex (M/F) ────────────► sex          │   ║ │ │ │
│ │ │ ║ │           └── DMG05: Race Code ────────────► race (→name) │   ║ │ │ │
│ │ │ ║ │                                                           │   ║ │ │ │
│ │ │ ║ │ LUI ───── Language                                        │   ║ │ │ │
│ │ │ ║ │           └── LUI02: Language Code ────────► language     │   ║ │ │ │
│ │ │ ║ └───────────────────────────────────────────────────────────┘   ║ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ ┌───────────────────────────────────────────────────────────┐   ║ │ │ │
│ │ │ ║ │ MEMBER DATES - Loop 2100A (DTP segments)                  │   ║ │ │ │
│ │ │ ║ ├───────────────────────────────────────────────────────────┤   ║ │ │ │
│ │ │ ║ │ DTP*348 ─ Coverage Start Date ─────────► coverage_start   │   ║ │ │ │
│ │ │ ║ │ DTP*349 ─ Coverage End Date ───────────► coverage_end     │   ║ │ │ │
│ │ │ ║ │           (also derives medi_cal_eligibility_status)      │   ║ │ │ │
│ │ │ ║ │ DTP*338 ─ Medicare Effective Date ─────► has_medicare     │   ║ │ │ │
│ │ │ ║ │ DTP*435 ─ Death Date ──────────────────► death_date       │   ║ │ │ │
│ │ │ ║ └───────────────────────────────────────────────────────────┘   ║ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ ╔═══════════════════════════════════════════════════════════╗   ║ │ │ │
│ │ │ ║ ║ HEALTH COVERAGE LOOP - Loop 2300 (repeats per coverage)   ║   ║ │ │ │
│ │ │ ║ ║ (in_hd_loop = True when inside this loop)                 ║   ║ │ │ │
│ │ │ ║ ╠═══════════════════════════════════════════════════════════╣   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║ HD ────── Health Coverage (LOOP START TRIGGER)            ║   ║ │ │ │
│ │ │ ║ ║           ├── HD03: Insurance Line ────► coverage type    ║   ║ │ │ │
│ │ │ ║ ║           ├── HD04: Plan Description ──► hcp_code;status  ║   ║ │ │ │
│ │ │ ║ ║           │         (parsed for HCP code and status)      ║   ║ │ │ │
│ │ │ ║ ║           └── HD06: Insurance Type ────► coverage flags   ║   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║           Coverage Detection (keyword scanning):          ║   ║ │ │ │
│ │ │ ║ ║           • MEDICARE, MA, PART A/B/C/D ► has_medicare     ║   ║ │ │ │
│ │ │ ║ ║           • MEDICAID, MEDI-CAL, LTC ───► has_medicaid     ║   ║ │ │ │
│ │ │ ║ ║           • SNP, D-SNP, DSNP ──────────► snp=True         ║   ║ │ │ │
│ │ │ ║ ║           • LTC, NURSING HOME, SNF ────► lti=True         ║   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║ DTP*348 ─ HCP Coverage Start ──────────► hcp.start_date   ║   ║ │ │ │
│ │ │ ║ ║ DTP*349 ─ HCP Coverage End ────────────► hcp.end_date     ║   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║ REF*CE ── Aid Codes (in HD loop) ──────► hcp.aid_codes    ║   ║ │ │ │
│ │ │ ║ ║ REF*17 ── Client Reporting Cat ────────► client_report    ║   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║ AMT ───── Amount                                          ║   ║ │ │ │
│ │ │ ║ ║           ├── AMT01: Qualifier ────────► amount_qualifier ║   ║ │ │ │
│ │ │ ║ ║           └── AMT02: Amount ───────────► amount (float)   ║   ║ │ │ │
│ │ │ ║ ║                                                           ║   ║ │ │ │
│ │ │ ║ ║ ──► Each HD creates new HCPContext, saved to hcp_history  ║   ║ │ │ │
│ │ │ ║ ╚═══════════════════════════════════════════════════════════╝   ║ │ │ │
│ │ │ ║                                                                 ║ │ │ │
│ │ │ ║ ──► On next INS or end of file: finalize member                 ║ │ │ │
│ │ │ ║     • Calculate age from DOB                                    ║ │ │ │
│ │ │ ║     • Determine dual status (priority logic)                    ║ │ │ │
│ │ │ ║     • Check new enrollee status                                 ║ │ │ │
│ │ │ ║     • Build HCP history list                                    ║ │ │ │
│ │ │ ║     • Create EnrollmentData object                              ║ │ │ │
│ │ │ ╚═════════════════════════════════════════════════════════════════╝ │ │ │
│ │ │                                                                     │ │ │
│ │ │ SE ─── Transaction Set Trailer                                      │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │ GE ─── Functional Group Trailer                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ IEA ── Interchange Control Trailer                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Parsing State Machine

```
    ┌──────────────┐
    │    START     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐     ISA/GS      ┌──────────────┐
    │   HEADER     │────────────────►│  Parse       │
    │   PARSING    │                 │  source,     │
    └──────────────┘                 │  report_date │
           │                         └──────────────┘
           │ BGN/N1*IN
           ▼
    ┌──────────────┐
    │   PLAN       │ ◄─── Detect SLA prefix
    │   INFO       │
    └──────┬───────┘
           │
           │ INS (Member Loop Start)
           ▼
    ┌──────────────┐
    │   MEMBER     │ ◄─── Create new MemberContext
    │   CONTEXT    │      in_hd_loop = False
    └──────┬───────┘
           │
           │ REF/NM1/DMG/N3/N4/LUI/DTP/PER
           ▼
    ┌──────────────┐
    │   MEMBER     │ ◄─── Populate member fields
    │   DETAILS    │
    └──────┬───────┘
           │
           │ HD (Health Coverage Loop Start)
           ▼
    ┌──────────────┐
    │   HD LOOP    │ ◄─── in_hd_loop = True
    │   ACTIVE     │      Create HCPContext
    └──────┬───────┘
           │
           │ DTP/REF/AMT (within HD loop)
           ▼
    ┌──────────────┐
    │   HCP        │ ◄─── Populate current_hcp
    │   DETAILS    │
    └──────┬───────┘
           │
           │ Next HD or INS
           ▼
    ┌──────────────────────────────────────┐
    │  HD?  │  INS?  │  EOF?               │
    └───┬───┴───┬────┴───┬─────────────────┘
        │       │        │
        │       │        ▼
        │       │   ┌──────────────┐
        │       │   │  FINALIZE    │
        │       │   │  MEMBER      │───► EnrollmentData
        │       │   └──────────────┘
        │       │
        │       ▼
        │  ┌──────────────┐
        │  │  FINALIZE    │───► EnrollmentData
        │  │  + NEW       │
        │  │  MEMBER      │───► New MemberContext
        │  └──────────────┘
        │
        ▼
   ┌──────────────┐
   │  SAVE HCP    │───► Append to hcp_history
   │  + NEW HCP   │───► New HCPContext
   └──────────────┘
```

## Dual Eligibility Determination Priority

The parser uses intelligent logic to determine dual eligibility status with the following priority:

```
    1. REF*F5 (explicit dual_elgbl_cd)
           │
           ▼ if not found
    2. REF*AB (Medi-Cal Aid Code mapping)
       │   4N,4P → '02' (QMB Plus)
       │   4M,4O → '01' (QMB Only)
       │   5B,5D → '04' (SLMB Plus)
       │   5A,5C → '03' (SLMB Only)
       │   5E,5F → '06' (QI)
           │
           ▼ if not found
    3. REF*ABB (Medicare Status Code mapping)
       │   QMB/QMBONLY → '01'
       │   QMBPLUS/QMB+ → '02'
       │   SLMB/SLMBONLY → '03'
       │   SLMBPLUS/SLMB+ → '04'
       │   QI/QI1 → '06'
       │   QDWI → '05'
           │
           ▼ if not found
    4. Both Medicare AND Medicaid coverage detected
       │   → '08' (Other Full Dual)
           │
           ▼ if not found
    5. Default: '00' (Non-Dual)
```

## Key Data Transformations

### Date Normalization

All dates are normalized to ISO format (YYYY-MM-DD):

| Input Format | Example | Output |
|--------------|---------|--------|
| YYYYMMDD | `20250115` | `2025-01-15` |
| YYMMDD | `250115` | `2025-01-15` |

### Race Code Translation

Race codes from DMG05 are translated using CDC Race and Ethnicity codes:

| Input | Output |
|-------|--------|
| `:RET:2135-2` | `Hispanic or Latino` |
| `:RET:2054-5` | `Black or African American` |
| `2106-3` | `White` |

### Amount Conversion

AMT segment values are converted to numeric:

| Segment | Fields Extracted |
|---------|------------------|
| `AMT*R*1237~` | `amount_qualifier='R'`, `amount=1237.0` |

## Output: EnrollmentData

The parser produces `EnrollmentData` objects with:

- **Identifiers**: member_id, mbi, medicaid_id, hic
- **Demographics**: dob, age, sex, race, language, death_date
- **Address**: address_1, address_2, city, state, zip, phone
- **Coverage**: coverage_start_date, coverage_end_date, maintenance_type, medi_cal_eligibility_status
- **Dual Status**: dual_elgbl_cd, is_full_benefit_dual, is_partial_benefit_dual
- **Risk Adjustment**: orec, crec, snp, low_income, lti, new_enrollee
- **CA DHCS**: fame_county_id, case_number, medi_cal_aid_code, primary_aid_code, fame_death_date, fame_redetermination_date
- **HCP History**: List of coverage periods with dates and aid codes

## Derived Fields

Some fields are derived at finalization time:

| Field | Source | Logic |
|-------|--------|-------|
| `age` | `dob` | Calculated from date of birth |
| `new_enrollee` | `coverage_start_date` | True if <= 3 months since start |
| `medi_cal_eligibility_status` | `coverage_end_date`, `report_date` | "Active" if coverage extends through report month, "Terminated" if ended before |
| `is_full_benefit_dual` | `dual_elgbl_cd` | True if code in {'02', '04', '08'} |
| `is_partial_benefit_dual` | `dual_elgbl_cd` | True if code in {'01', '03', '05', '06'} |

## Death Date Sources

Death date can come from multiple sources with the following priority:

| Source | Field | Notes |
|--------|-------|-------|
| INS11/INS12 | `death_date` | Primary source when INS11='D8' |
| DTP*435 | `death_date` | Secondary source, overwrites INS if present |
| REF*17 position 1 | `fame_death_date` | FAME system recorded date (separate field) |

## Related Documentation

- [Main README](./README.md) - Library overview and usage
- [CLAUDE.md](./CLAUDE.md) - Developer guide with code examples
- [Source Code](./src/hccinfhir/extractor_834.py) - Implementation details
