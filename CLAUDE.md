# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information

**Current Version**: 0.1.5
**Package Name**: hccinfhir
**Description**: A Python library for calculating HCC (Hierarchical Condition Category) risk adjustment scores from healthcare claims data
**License**: Apache 2.0
**Python Requirements**: 3.9+

### What This Library Does

HCCInFHIR processes healthcare data to calculate Medicare risk adjustment scores used for payment calculations. It supports multiple input formats:

1. **FHIR ExplanationOfBenefit resources** - from CMS Blue Button 2.0 API
2. **X12 837 claim files** - from clearinghouses and encounter data
3. **X12 834 enrollment files** - for extracting dual eligibility and demographic data
4. **Direct diagnosis codes** - for quick calculations
5. **Service-level data** - standardized internal format

The library implements the official CMS-HCC risk adjustment methodology, including:
- Diagnosis code to HCC mapping
- Hierarchical condition category rules
- Demographic coefficients and interactions
- RAF (Risk Adjustment Factor) score calculations

## Development Commands

### Testing
```bash
hatch shell                    # Activate virtual environment
pip install -e .              # Install package in development mode
pytest tests/*                # Run all tests
pytest tests/test_filter.py   # Run specific test file
```

### Building and Publishing
```bash
hatch build                    # Build package
hatch publish                  # Publish to PyPI (maintainers only)
```

### Dependencies
- Install new dependencies by updating `pyproject.toml` dependencies
- Core dependency: `pydantic >= 2.10.3`
- Development dependency: `pytest`

## How Scripts and Modules Work

### Main Entry Points

#### 1. HCCInFHIR Class (`hccinfhir.py`)
The main processor class with three execution methods:

```python
from hccinfhir import HCCInFHIR, Demographics

# Initialize processor
processor = HCCInFHIR(
    filter_claims=True,  # Apply CMS filtering rules
    model_name="CMS-HCC Model V28",  # HCC model to use
    proc_filtering_filename="ra_eligible_cpt_hcpcs_2026.csv",  # CPT/HCPCS filtering
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv"  # Diagnosis mapping
)
```

**Method 1: `run()` - Process FHIR EOB Resources**
```python
# Input: List of FHIR ExplanationOfBenefit resources
eob_list = [{"resourceType": "ExplanationOfBenefit", ...}]
demographics = Demographics(age=67, sex="F")

result = processor.run(eob_list, demographics)
```

**Method 2: `run_from_service_data()` - Process Service-Level Data**
```python
# Input: Standardized ServiceLevelData objects
service_data = [ServiceLevelData(...)]
demographics = Demographics(age=67, sex="F")

result = processor.run_from_service_data(service_data, demographics)
```

**Method 3: `calculate_from_diagnosis()` - Direct Diagnosis Processing**
```python
# Input: List of diagnosis codes
diagnosis_codes = ["E11.9", "I10", "N18.3"]  # ICD-10 codes
demographics = Demographics(age=67, sex="F")

result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
```

#### Advanced: Demographic Prefix Override

All three methods support `prefix_override` parameter for cases where demographic auto-detection is incorrect:

```python
# ESRD patient with incorrect orec/crec codes (common data quality issue)
demographics = Demographics(age=65, sex="F", orec="0", crec="0")
diagnosis_codes = ["N18.6", "E11.22"]

# Force ESRD dialysis coefficients despite orec/crec being wrong
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='DI_'  # ESRD Dialysis prefix
)
```

**When to use prefix_override:**
- ESRD patients with orec='0'/crec='0' when they should be '2' or '3'
- Long-term institutionalized patients not properly flagged
- Dual-eligible status not correctly coded
- Any case where demographic categorization differs from administrative data

**Common prefix values:**
See "Coefficient Prefix Reference" section below for complete list.

### Core Processing Pipeline

#### Step 1: Data Extraction (`extractor.py`, `extractor_fhir.py`, `extractor_837.py`)

**Extract from FHIR:**
```python
from hccinfhir.extractor import extract_sld, extract_sld_list

# Single EOB
eob = {"resourceType": "ExplanationOfBenefit", ...}
service_data = extract_sld(eob)

# Multiple EOBs
eob_list = [eob1, eob2, eob3]
service_data_list = extract_sld_list(eob_list)
```

**Extract from X12 837:**
```python
from hccinfhir.extractor_837 import extract_sld_from_837

# X12 837 claim text
x12_text = "ISA*00*          *00*          *ZZ*..."
service_data = extract_sld_from_837(x12_text)
```

**Extract from X12 834 (Enrollment/Demographics):**
```python
from hccinfhir.extractor_834 import (
    extract_enrollment_834,
    enrollment_to_demographics,
    is_losing_medicaid,
    medicaid_status_summary
)

# X12 834 enrollment file
x12_text = "ISA*00*          *00*          *ZZ*..."
enrollments = extract_enrollment_834(x12_text)

# Get member demographics for risk calculation
for enrollment in enrollments:
    demographics = enrollment_to_demographics(enrollment)

    # Check if member is losing Medicaid coverage
    if is_losing_medicaid(enrollment, within_days=90):
        print(f"Alert: {enrollment.member_id} losing Medicaid soon!")

    # Get comprehensive Medicaid status
    status = medicaid_status_summary(enrollment)
    print(f"Dual Status: {status['dual_status']}")
    print(f"Full Benefit Dual: {status['is_full_benefit_dual']}")
```

#### Step 2: Filtering (`filter.py`)
```python
from hccinfhir.filter import apply_filter
from hccinfhir.utils import load_proc_filtering

# Load CPT/HCPCS codes for filtering
professional_cpt = load_proc_filtering("ra_eligible_cpt_hcpcs_2026.csv")

# Apply CMS filtering rules
filtered_data = apply_filter(service_data_list, professional_cpt)
```

#### Step 3: Risk Calculation (`model_calculate.py`)
```python
from hccinfhir.model_calculate import calculate_raf

result = calculate_raf(
    diagnosis_codes=["E11.9", "I10"],
    model_name="CMS-HCC Model V28",
    age=67,
    sex="F",
    dual_elgbl_cd="N",
    orec="0",
    # ... other demographics
)
```

### Individual Model Components

#### Demographics Processing (`model_demographics.py`)
```python
from hccinfhir.model_demographics import get_demographic_coefficients

coeffs = get_demographic_coefficients(
    age=67, sex="F", dual_elgbl_cd="N",
    model_name="CMS-HCC Model V28"
)
```

#### Diagnosis to HCC Mapping (`model_dx_to_cc.py`)
```python
from hccinfhir.model_dx_to_cc import get_dx_to_cc_list

# Map diagnosis codes to HCCs
hcc_list = get_dx_to_cc_list(
    diagnosis_codes=["E11.9", "I10"],
    dx_to_cc_mapping=dx_mapping_data
)
```

#### Hierarchy Processing (`model_hierarchies.py`)
```python
from hccinfhir.model_hierarchies import apply_hierarchies

# Apply HCC hierarchical rules
final_hccs = apply_hierarchies(
    hcc_list=["HCC18", "HCC85"],
    model_name="CMS-HCC Model V28"
)
```

### Sample Data Usage

#### Working with Sample Data (`samples.py`)
```python
from hccinfhir import get_eob_sample, get_eob_sample_list, get_837_sample, get_834_sample

# Get FHIR EOB samples
eob = get_eob_sample(1)  # Individual sample (cases 1, 2, or 3)
eob_list = get_eob_sample_list(limit=200)  # Up to 200 samples

# Get X12 837 samples
x12_text = get_837_sample(0)  # Professional claim (cases 0-12)

# Get X12 834 sample
x12_834 = get_834_sample(1)  # Enrollment data (case 1)

# Process sample data
processor = HCCInFHIR()
demographics = Demographics(age=67, sex="F")
result = processor.run([eob], demographics)  # Note: wrap single EOB in list
```

### Utility Functions

#### Data Loading (`utils.py`)
```python
from hccinfhir.utils import load_proc_filtering, load_dx_to_cc_mapping

# Load filtering data
cpt_codes = load_proc_filtering("ra_eligible_cpt_hcpcs_2026.csv")

# Load diagnosis mapping
dx_mapping = load_dx_to_cc_mapping("ra_dx_to_cc_2026.csv")
```

### Execution Patterns

#### Pattern 1: End-to-End FHIR Processing
```python
# Complete workflow from FHIR to RAF score
processor = HCCInFHIR(model_name="CMS-HCC Model V28")
eob_list = get_eob_sample_list(limit=200)
demographics = Demographics(age=67, sex="F", dual_elgbl_cd="00")

result = processor.run(eob_list, demographics)
print(f"RAF Score: {result.risk_score}")
print(f"HCCs: {result.hcc_list}")
```

#### Pattern 2: Step-by-Step Processing
```python
# Manual control over each step
from hccinfhir.extractor import extract_sld_list
from hccinfhir.filter import apply_filter
from hccinfhir.model_calculate import calculate_raf

# Step 1: Extract
service_data = extract_sld_list(eob_list)

# Step 2: Filter
filtered_data = apply_filter(service_data, professional_cpt)

# Step 3: Calculate
diagnosis_codes = list({code for sld in filtered_data for code in sld.claim_diagnosis_codes})
result = calculate_raf(diagnosis_codes, "CMS-HCC Model V28", age=67, sex="F")
```

#### Pattern 3: Batch Processing Multiple Patients
```python
# Process multiple patients
patients = [
    {"eobs": eob_list_1, "demographics": Demographics(age=65, sex="M")},
    {"eobs": eob_list_2, "demographics": Demographics(age=72, sex="F")},
]

processor = HCCInFHIR()
results = []

for patient in patients:
    result = processor.run(patient["eobs"], patient["demographics"])
    results.append({
        "patient_id": patient.get("id"),
        "risk_score": result.risk_score,
        "hccs": result.hcc_list
    })
```

## 834 Enrollment Parser - Medicaid Dual Eligibility Tracking

### Overview

The 834 parser (`extractor_834.py`) extracts enrollment and demographic data from X12 834 Benefit Enrollment transactions, with a specific focus on **California DHCS Medi-Cal** dual eligibility status. This is critical for risk adjustment because dual-eligible beneficiaries receive different coefficient prefixes, resulting in significant RAF score differences.

### Why Medicaid Dual Status Matters for Risk Scores

**Impact Example:**
```python
# 72-year-old female with diabetes (E11.9 → HCC19)

# Non-Dual (Medi-Cal only or Medicare only)
demographics = Demographics(age=72, sex='F', dual_elgbl_cd='00')
# Uses prefix: CNA_ (Community, Non-Dual, Aged)
# RAF Score: ~1.2

# Full Benefit Dual (QMB Plus, SLMB Plus)
demographics = Demographics(age=72, sex='F', dual_elgbl_cd='02')
# Uses prefix: CFA_ (Community, Full Benefit Dual, Aged)
# RAF Score: ~1.8  (50% higher!)

# Partial Benefit Dual (QMB Only, SLMB Only, QI)
demographics = Demographics(age=72, sex='F', dual_elgbl_cd='01')
# Uses prefix: CPA_ (Community, Partial Benefit Dual, Aged)
# RAF Score: ~1.4
```

### What the 834 Parser Extracts

#### Critical Fields for Risk Adjustment:
1. **dual_elgbl_cd** - Dual eligibility status ('00','01'-'08')
   - '01' = QMB Only (Partial Benefit)
   - '02' = QMB Plus (Full Benefit)
   - '03' = SLMB Only (Partial Benefit)
   - '04' = SLMB Plus (Full Benefit)
   - '05' = QDWI
   - '06' = QI (Qualifying Individual)
   - '08' = Other Full Benefit Dual

2. **Demographics** - age, sex, DOB
3. **OREC/CREC** - For ESRD detection
4. **SNP** - Special Needs Plan enrollment
5. **New Enrollee** - Coverage start date < 3 months

#### Critical Fields for Medicaid Loss Detection:
6. **coverage_end_date** - When Medicaid coverage terminates
7. **maintenance_type** - '024' = Cancellation/Termination
8. **has_medicaid** / **has_medicare** - Coverage indicators

### Basic Usage

```python
from hccinfhir.extractor_834 import extract_enrollment_834, enrollment_to_demographics

# Load 834 file
with open('dhcs_834_file.txt', 'r') as f:
    content = f.read()

# Parse enrollments
enrollments = extract_enrollment_834(content)

# Process each member
for enrollment in enrollments:
    print(f"Member: {enrollment.member_id}")
    print(f"MBI: {enrollment.mbi}")
    print(f"Medicaid ID: {enrollment.medicaid_id}")
    print(f"Dual Status: {enrollment.dual_elgbl_cd}")
    print(f"Full Benefit Dual: {enrollment.is_full_benefit_dual}")
    print(f"Partial Benefit Dual: {enrollment.is_partial_benefit_dual}")

    # Convert to Demographics for RAF calculation
    demographics = enrollment_to_demographics(enrollment)
```

### Medicaid Loss Detection

**Use Case:** Detect when members will lose Medicaid coverage, causing dual-eligible status to end and RAF scores to drop.

```python
from hccinfhir.extractor_834 import (
    extract_enrollment_834,
    is_losing_medicaid,
    is_medicaid_terminated,
    medicaid_status_summary
)

enrollments = extract_enrollment_834(content)

for enrollment in enrollments:
    # Check if losing Medicaid within 90 days
    if is_losing_medicaid(enrollment, within_days=90):
        print(f"⚠️  ALERT: {enrollment.member_id} losing Medicaid!")
        print(f"   Coverage ends: {enrollment.coverage_end_date}")
        print(f"   Current dual status: {enrollment.dual_elgbl_cd}")
        print(f"   Expected RAF impact: -30% to -50%")

    # Check if Medicaid is being terminated
    if is_medicaid_terminated(enrollment):
        print(f"⚠️  TERMINATION: {enrollment.member_id} Medicaid canceled")

    # Get comprehensive status summary
    status = medicaid_status_summary(enrollment)
    print(f"Status Summary: {status}")
    # Returns:
    # {
    #   'member_id': 'MBR001',
    #   'has_medicaid': True,
    #   'has_medicare': True,
    #   'dual_status': '02',
    #   'is_full_benefit_dual': True,
    #   'is_partial_benefit_dual': False,
    #   'coverage_end_date': '2025-12-31',
    #   'is_termination': False,
    #   'losing_medicaid_30d': False,
    #   'losing_medicaid_60d': False,
    #   'losing_medicaid_90d': False
    # }
```

### California DHCS Medi-Cal Specific Features

The parser is optimized for California DHCS 834 files with these state-specific mappings:

#### Aid Code Mapping (REF*AB segment)
```python
# Full Benefit Dual codes
'4N': '02'  # QMB Plus - Aged
'4P': '02'  # QMB Plus - Disabled
'5B': '04'  # SLMB Plus - Aged
'5D': '04'  # SLMB Plus - Disabled

# Partial Benefit Dual codes
'4M': '01'  # QMB Only - Aged
'4O': '01'  # QMB Only - Disabled
'5A': '03'  # SLMB Only - Aged
'5C': '03'  # SLMB Only - Disabled
'5E': '06'  # QI - Aged
'5F': '06'  # QI - Disabled
```

#### Medicare Status Code Mapping (REF*ABB segment)
```python
'QMB' / 'QMBONLY': '01'      # Partial Benefit
'QMBPLUS' / 'QMB+': '02'     # Full Benefit
'SLMB' / 'SLMBONLY': '03'    # Partial Benefit
'SLMBPLUS' / 'SLMB+': '04'   # Full Benefit
'QI' / 'QI1': '06'           # Partial Benefit
'QDWI': '05'                 # Partial Benefit
```

### Key 834 Segments Parsed

```
Loop 2000 - Member Level
    INS - Member Level Detail
        INS03 - Maintenance Type (001=Change, 021=Add, 024=Cancel)

    REF - Reference Identifiers
        REF*0F - Subscriber Number
        REF*6P - Medicare Beneficiary Identifier (MBI)
        REF*1D - Medicaid ID
        REF*AB - California Medi-Cal Aid Code
        REF*ABB - Medicare Status Code (QMB, SLMB, etc.)

    NM1*IL - Member Name & ID

    DMG - Demographics (DOB, Sex) ***CRITICAL***

    DTP - Date Time Periods
        DTP*348 - Coverage Begin Date
        DTP*349 - Coverage End Date ***CRITICAL for loss detection***
        DTP*338 - Medicare Part A/B Effective Date

    HD - Health Coverage ***CRITICAL for dual status***
        Detects Medicare, Medicaid, D-SNP keywords
```

### Dual Status Determination Priority

The parser uses intelligent logic to determine dual eligibility:

1. **Priority 1**: Explicit dual_elgbl_cd from REF*F5 (custom)
2. **Priority 2**: California aid code (REF*AB) mapping
3. **Priority 3**: Medicare status code (REF*ABB) mapping
4. **Priority 4**: Both Medicare AND Medicaid coverage present → defaults to '08' (Other Full Dual)
5. **Default**: '00' (Non-dual)

### Integration with Risk Calculation

```python
from hccinfhir import HCCInFHIR
from hccinfhir.extractor_834 import extract_enrollment_834, enrollment_to_demographics
from hccinfhir.extractor_837 import extract_sld_837

# Parse enrollment data
enrollments_834 = extract_enrollment_834(content_834)

# Parse claims data
service_data_837 = extract_sld_837(content_837)

# Match member and calculate RAF
processor = HCCInFHIR()

for enrollment in enrollments_834:
    # Get demographics from 834
    demographics = enrollment_to_demographics(enrollment)

    # Filter claims for this member
    member_claims = [sld for sld in service_data_837 if sld.patient_id == enrollment.member_id]

    # Calculate RAF score
    result = processor.run_from_service_data(member_claims, demographics)

    print(f"Member: {enrollment.member_id}")
    print(f"Dual Status: {enrollment.dual_elgbl_cd}")
    print(f"RAF Score: {result.risk_score}")
```

### Sample Data

Sample 834 file available at: `src/hccinfhir/sample_files/sample_834_01.txt`

Includes 5 test scenarios:
1. QMB Plus (Full Benefit Dual) with D-SNP
2. QMB Only (Partial Benefit Dual) via aid code
3. SLMB Plus with coverage ending (Medicaid loss scenario)
4. Medi-Cal only (no Medicare)
5. Medicare only (new enrollee)

```python
from hccinfhir import get_834_sample

# Get sample 834
content_834 = get_834_sample(1)
enrollments = extract_enrollment_834(content_834)
```

## Architecture Overview

This is a Python library for extracting and processing healthcare data to calculate HCC (Hierarchical Condition Category) risk adjustment scores. The architecture follows a modular pipeline approach:

### Core Data Flow
1. **Input**: FHIR ExplanationOfBenefit resources OR X12 837 claims OR service-level data
2. **Extraction**: Convert input data to standardized Service Level Data (SLD) format
3. **Filtering**: Apply CMS filtering rules for eligible services
4. **Calculation**: Map diagnosis codes to HCCs and calculate RAF scores

### Key Components

#### Main Processor (`hccinfhir.py`)
- **HCCInFHIR class**: Main entry point integrating all components
- Three processing methods:
  - `run()`: Process FHIR EOB resources
  - `run_from_service_data()`: Process standardized service data
  - `calculate_from_diagnosis()`: Direct diagnosis code processing

#### Data Extraction
- **Extractor module** (`extractor.py`): Unified interface for data extraction
- **FHIR Extractor** (`extractor_fhir.py`): Processes FHIR resources using Pydantic models
- **837 Extractor** (`extractor_837.py`): Parses X12 837 claim data

#### Data Models (`datamodels.py`)
- **ServiceLevelData**: Standardized format for healthcare service data
- **Demographics**: Patient demographic information for risk calculation
- **RAFResult**: Complete risk score calculation results
- Uses Pydantic for validation and type safety

#### Risk Calculation Engine
- **Model modules** (`model_*.py`): Implement CMS HCC calculation logic
  - `model_calculate.py`: Main RAF calculation orchestrator
  - `model_demographics.py`: Demographics processing
  - `model_dx_to_cc.py`: Diagnosis to condition category mapping
  - `model_hierarchies.py`: HCC hierarchical rules
  - `model_interactions.py`: Interaction calculations
  - `model_coefficients.py`: Risk score coefficients

#### Filtering (`filter.py`)
- Applies CMS filtering rules based on CPT/HCPCS codes
- Separates inpatient/outpatient and professional service requirements

### Data Files
Located in `src/hccinfhir/data/`:
- **Diagnosis Mapping**: `ra_dx_to_cc_*.csv` - ICD-10 to condition category mapping
- **Hierarchies**: `ra_hierarchies_*.csv` - HCC hierarchical relationships
- **Coefficients**: `ra_coefficients_*.csv` - Risk score coefficients
- **Filtering**: `ra_eligible_cpt_hcpcs_*.csv` - Eligible procedure codes
- **Chronic Conditions**: `hcc_is_chronic.csv` - Chronic condition flags

### Sample Data System
- Comprehensive sample data in `src/hccinfhir/samples/`
- **EOB samples**: 3 individual cases + 200 sample dataset
- **837 samples**: 12 different claim scenarios
- Access via `get_eob_sample()`, `get_837_sample()`, etc.

## Model Support

### Supported HCC Models
- CMS-HCC Model V22, V24, V28
- CMS-HCC ESRD Model V21, V24
- RxHCC Model V08

### Model Years
- 2025 and 2026 model year data files included
- Default configuration uses 2026 model year

## Common Development Tasks

### Adding New HCC Models
1. Add model name to `ModelName` literal type in `datamodels.py`
2. Add corresponding data files to `src/hccinfhir/data/`
3. Update loading functions in respective model modules

### Testing New Features
- Use sample data functions: `get_eob_sample()`, `get_837_sample()`
- Test with different demographics using `Demographics` model
- Validate using `pytest tests/test_*.py` files

### Working with Data Files
- CSV files use standard format with headers
- Loading handled by utility functions in respective modules
- Files are included in package build via `pyproject.toml` configuration

## Coefficient Prefix Reference

The library uses demographic prefixes to select appropriate risk adjustment coefficients. Prefixes are automatically derived from patient demographics (age, sex, orec, crec, dual status, etc.), but can be manually overridden using the `prefix_override` parameter.

### CMS-HCC Models (V22, V24, V28)

#### Community Beneficiaries
- **`CNA_`** - Community, Non-Dual, Aged (65+)
- **`CND_`** - Community, Non-Dual, Disabled (<65)
- **`CFA_`** - Community, Full Benefit Dual, Aged (65+)
- **`CFD_`** - Community, Full Benefit Dual, Disabled (<65)
- **`CPA_`** - Community, Partial Benefit Dual, Aged (65+)
- **`CPD_`** - Community, Partial Benefit Dual, Disabled (<65)

#### Institutionalized Beneficiaries
- **`INS_`** - Long-Term Institutionalized (nursing home >90 days)

#### New Enrollees
- **`NE_`** - New Enrollee (standard)
- **`SNPNE_`** - Special Needs Plan New Enrollee

### CMS-HCC ESRD Models (V21, V24)

#### Dialysis Beneficiaries
- **`DI_`** - Dialysis (standard)
- **`DNE_`** - Dialysis New Enrollee

#### Functioning Graft Beneficiaries
- **`GI_`** - Graft, Institutionalized
- **`GNE_`** - Graft, New Enrollee
- **`GFPA_`** - Graft, Full Benefit Dual, Aged (65+)
- **`GFPN_`** - Graft, Full Benefit Dual, Non-Aged (<65)
- **`GNPA_`** - Graft, Non-Dual, Aged (65+)
- **`GNPN_`** - Graft, Non-Dual, Non-Aged (<65)

#### Transplant Beneficiaries
- **`TRANSPLANT_KIDNEY_ONLY_1M`** - 1 month post-transplant
- **`TRANSPLANT_KIDNEY_ONLY_2M`** - 2 months post-transplant
- **`TRANSPLANT_KIDNEY_ONLY_3M`** - 3 months post-transplant

### RxHCC Model (V08)

#### Community Enrollees
- **`Rx_CE_LowAged_`** - Community, Low Income, Aged (65+)
- **`Rx_CE_LowNoAged_`** - Community, Low Income, Non-Aged (<65)
- **`Rx_CE_NoLowAged_`** - Community, Not Low Income, Aged (65+)
- **`Rx_CE_NoLowNoAged_`** - Community, Not Low Income, Non-Aged (<65)

#### Long-Term Institutionalized
- **`Rx_CE_LTI_`** - Community Enrollee, Long-Term Institutionalized

#### New Enrollees
- **`Rx_NE_Lo_`** - New Enrollee, Low Income
- **`Rx_NE_NoLo_`** - New Enrollee, Not Low Income
- **`Rx_NE_LTI_`** - New Enrollee, Long-Term Institutionalized

### Using prefix_override

```python
from hccinfhir import HCCInFHIR, Demographics

# Example 1: ESRD patient with bad orec/crec data
processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")
demographics = Demographics(age=65, sex="F", orec="0", crec="0")  # Wrong codes
diagnosis_codes = ["N18.6", "E11.22", "I12.0"]

# Override to force ESRD dialysis coefficients
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='DI_'
)

# Example 2: Institutionalized patient not properly flagged
processor = HCCInFHIR(model_name="CMS-HCC Model V28")
demographics = Demographics(age=78, sex="M")  # Should be LTI
diagnosis_codes = ["F03.90", "I48.91", "N18.4"]

# Override to use institutionalized coefficients
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='INS_'
)
```

### How Demographics Auto-Detection Works

The library automatically derives the prefix from:
1. **ESRD status**: Determined from `orec` ∈ {'2', '3', '6'} or `crec` ∈ {'2', '3'}
2. **Age category**: Aged (65+) vs Non-Aged/Disabled (<65)
3. **Dual eligibility**: Full Benefit Dual (`dual_elgbl_cd` ∈ {'02', '04', '08'}), Partial Benefit Dual ({'01', '03', '05', '06'}), or Non-Dual
4. **Institutional status**: Long-term institutionalized flag
5. **New enrollee status**: First year in Medicare Advantage
6. **Special Needs Plan**: SNP enrollment flag

**Common Data Quality Issues:**
- **ESRD patients with orec='0'/crec='0'**: Should be '2' or '3', but source data may be incorrect
- **Missing LTI flags**: Nursing home residents not properly flagged in claims data
- **Incorrect dual codes**: Dual eligibility status may not be updated timely
- **Transplant status**: `graft_months` may be missing or incorrect

When these issues occur, use `prefix_override` to ensure correct coefficient selection.