# HCCInFHIR

[![PyPI version](https://badge.fury.io/py/hccinfhir.svg)](https://badge.fury.io/py/hccinfhir)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Python library for calculating HCC (Hierarchical Condition Category) risk adjustment scores from healthcare claims data. Supports multiple data sources including FHIR resources, X12 837 claims, X12 834 enrollment files, and direct diagnosis processing.

## 🚀 Quick Start

```bash
pip install hccinfhir
```

```python
from hccinfhir import HCCInFHIR, Demographics

# Initialize processor
processor = HCCInFHIR(model_name="CMS-HCC Model V28")

# Calculate from diagnosis codes
demographics = Demographics(age=67, sex="F")
diagnosis_codes = ["E11.9", "I10", "N18.3"]

result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
print(f"Risk Score: {result.risk_score}")
print(f"HCCs: {result.hcc_list}")
```

## 📋 Table of Contents

- [Key Features](#key-features)
- [Data Sources & Use Cases](#data-sources--use-cases)
- [Installation](#installation)
- [How-To Guides](#how-to-guides)
  - [Working with CMS Encounter Data (837 Claims)](#working-with-cms-encounter-data-837-claims)
  - [Processing X12 834 Enrollment for Dual Eligibility](#processing-x12-834-enrollment-for-dual-eligibility)
  - [Processing Clearinghouse 837 Claims](#processing-clearinghouse-837-claims)
  - [Using CMS BCDA API Data](#using-cms-bcda-api-data)
  - [Direct Diagnosis Code Processing](#direct-diagnosis-code-processing)
- [Configuration](#configuration)
  - [Supported HCC Models](#supported-hcc-models)
  - [Custom Data Files](#custom-data-files)
  - [Demographics Configuration](#demographics-configuration)
- [API Reference](#api-reference)
- [Advanced Features](#advanced-features)
  - [Payment RAF Adjustments](#payment-raf-adjustments)
  - [Demographic Prefix Override](#demographic-prefix-override)
  - [Custom File Path Resolution](#custom-file-path-resolution)
  - [Batch Processing](#batch-processing)
  - [Large-Scale Processing with Databricks](#large-scale-processing-with-databricks)
  - [Converting to Dictionaries](#converting-to-dictionaries)
- [Sample Data](#sample-data)
- [Testing](#testing)
- [License](#license)

## ✨ Key Features

- **Multiple Input Formats**: FHIR EOB, X12 837, X12 834, direct diagnosis codes
- **Comprehensive HCC Models**: Support for CMS-HCC V22/V24/V28, ESRD models, RxHCC
- **Dual Eligibility Detection**: X12 834 parser with California DHCS Medi-Cal support
- **CMS Compliance**: Built-in filtering rules for eligible services
- **Payment RAF Adjustments**: MACI, normalization factors, frailty scores
- **Data Quality Workarounds**: Demographic prefix override for incorrect source data
- **Custom Data Files**: Full support for custom coefficients, mappings, and hierarchies
- **Flexible File Resolution**: Absolute paths, relative paths, or bundled data files
- **Type-Safe**: Built on Pydantic with full type hints
- **Well-Tested**: 189 comprehensive tests covering all features

## 📊 Data Sources & Use Cases

### 1. **X12 837 Claims (Professional & Institutional)**
- **Input**: X12 837 5010 transaction files + demographics
- **Use Case**: Medicare Advantage encounter data, health plan claims processing
- **Features**: Service-level extraction, CMS filtering, diagnosis pointer resolution
- **Output**: Risk scores with detailed HCC mappings and interactions

### 2. **X12 834 Enrollment Files**
- **Input**: X12 834 benefit enrollment transactions
- **Use Case**: Extract dual eligibility status, detect Medicaid coverage loss
- **Features**: California DHCS aid code mapping, Medicare status codes, coverage tracking
- **Output**: Demographics with accurate dual eligibility for risk calculations

### 3. **FHIR ExplanationOfBenefit Resources**
- **Input**: FHIR EOB from CMS Blue Button 2.0 / BCDA API
- **Use Case**: Applications processing Medicare beneficiary data
- **Features**: FHIR-native extraction, standardized data model
- **Output**: Service-level analysis with risk adjustment calculations

### 4. **Direct Diagnosis Codes**
- **Input**: ICD-10 diagnosis codes + demographics
- **Use Case**: Quick validation, research, prospective risk scoring
- **Features**: No claims data needed, fast calculation
- **Output**: HCC mappings and risk scores

## 🛠️ Installation

### Basic Installation
```bash
pip install hccinfhir
```

### Development Installation
```bash
git clone https://github.com/yourusername/hccinfhir.git
cd hccinfhir
pip install -e .
```

### Requirements
- Python 3.9+
- Pydantic >= 2.10.3

## 📖 How-To Guides

### Working with CMS Encounter Data (837 Claims)

**Scenario**: You're a Medicare Advantage plan processing encounter data for CMS risk adjustment submissions.

```python
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.extractor import extract_sld

# Step 1: Configure processor
# All data file parameters are optional and default to the latest 2026 valuesets
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    filter_claims=True,  # Apply CMS filtering rules

    # Optional: Override with custom data files (omit to use bundled 2026 defaults)
    # proc_filtering_filename="ra_eligible_cpt_hcpcs_2026.csv",  # CPT/HCPCS codes
    # dx_cc_mapping_filename="ra_dx_to_cc_2026.csv",            # ICD-10 to HCC
    # hierarchies_filename="ra_hierarchies_2026.csv",            # HCC hierarchies
    # is_chronic_filename="hcc_is_chronic.csv",                  # Chronic flags
    # coefficients_filename="ra_coefficients_2026.csv"           # RAF coefficients
)

# Step 2: Load 837 data
with open("encounter_data.txt", "r") as f:
    raw_837_data = f.read()

# Step 3: Extract service-level data
service_data = extract_sld(raw_837_data, format="837")

# Step 4: Define beneficiary demographics
demographics = Demographics(
    age=72,
    sex="M",
    dual_elgbl_cd="00",      # Non-dual eligible
    orec="0",                # Original reason for entitlement
    crec="0",                # Current reason for entitlement
    orig_disabled=False,
    new_enrollee=False,
    esrd=False
)

# Step 5: Calculate risk score
result = processor.run_from_service_data(service_data, demographics)

# Step 6: Review results
print(f"Risk Score: {result.risk_score:.3f}")
print(f"Active HCCs: {result.hcc_list}")
print(f"Disease Interactions: {result.interactions}")
print(f"Diagnosis Mappings:")
for cc, dx_codes in result.cc_to_dx.items():
    print(f"  HCC {cc}: {', '.join(dx_codes)}")

# Export for CMS submission
encounter_summary = {
    "beneficiary_id": "12345",
    "risk_score": result.risk_score,
    "hcc_list": result.hcc_list,
    "model": "V28",
    "payment_year": 2026
}
```

### Processing X12 834 Enrollment for Dual Eligibility

**Scenario**: You need to extract dual eligibility status from enrollment files to ensure accurate risk scores. This is critical because dual-eligible beneficiaries can receive **30-50% higher RAF scores** due to different coefficient prefixes.

**Why This Matters**:
- Full Benefit Dual (QMB Plus, SLMB Plus): Uses `CFA_` prefix → ~50% higher RAF
- Partial Benefit Dual (QMB Only, SLMB Only, QI): Uses `CPA_` prefix → ~30% higher RAF
- Non-Dual: Uses `CNA_` prefix → baseline RAF

```python
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.extractor_834 import (
    extract_enrollment_834,
    enrollment_to_demographics,
    is_losing_medicaid,
    medicaid_status_summary
)

# Step 1: Parse X12 834 enrollment file
with open("enrollment_834.txt", "r") as f:
    x12_834_data = f.read()

enrollments = extract_enrollment_834(x12_834_data)

# Step 2: Process each member
processor = HCCInFHIR(model_name="CMS-HCC Model V28")

for enrollment in enrollments:
    # Convert enrollment to Demographics for RAF calculation
    demographics = enrollment_to_demographics(enrollment)

    print(f"\\n=== Member: {enrollment.member_id} ===")
    print(f"MBI: {enrollment.mbi}")
    print(f"Medicaid ID: {enrollment.medicaid_id}")
    print(f"Dual Status: {enrollment.dual_elgbl_cd}")
    print(f"Full Benefit Dual: {enrollment.is_full_benefit_dual}")
    print(f"Partial Benefit Dual: {enrollment.is_partial_benefit_dual}")

    # Step 3: Check for Medicaid coverage loss (critical for RAF projections)
    if is_losing_medicaid(enrollment, within_days=90):
        print(f"⚠️  ALERT: Member losing Medicaid coverage!")
        print(f"   Coverage ends: {enrollment.coverage_end_date}")
        print(f"   Expected RAF impact: -30% to -50%")

    # Step 4: Get comprehensive Medicaid status
    status = medicaid_status_summary(enrollment)
    print(f"\\nMedicaid Status Summary:")
    print(f"  Has Medicare: {status['has_medicare']}")
    print(f"  Has Medicaid: {status['has_medicaid']}")
    print(f"  Dual Status Code: {status['dual_status']}")
    print(f"  Full Benefit Dual: {status['is_full_benefit_dual']}")
    print(f"  Partial Benefit Dual: {status['is_partial_benefit_dual']}")
    print(f"  Coverage End: {status['coverage_end_date']}")

    # Step 5: Calculate RAF with accurate dual status
    diagnosis_codes = ["E11.9", "I10", "N18.3"]  # From claims
    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
    print(f"\\nRAF Score: {result.risk_score:.3f}")
```

**California DHCS Medi-Cal Aid Codes** (automatically mapped):
```python
# Full Benefit Dual Aid Codes → dual_elgbl_cd='02' or '04'
'4N', '4P'  # QMB Plus
'5B', '5D'  # SLMB Plus

# Partial Benefit Dual Aid Codes → dual_elgbl_cd='01', '03', or '06'
'4M', '4O'  # QMB Only
'5A', '5C'  # SLMB Only
'5E', '5F'  # QI (Qualifying Individual)
```

**Medicare Status Codes** (REF*ABB segment):
```python
'QMBPLUS', 'QMB+'    → '02' (Full Benefit)
'SLMBPLUS', 'SLMB+'  → '04' (Full Benefit)
'QMBONLY', 'QMB'     → '01' (Partial Benefit)
'SLMBONLY', 'SLMB'   → '03' (Partial Benefit)
'QI', 'QI1'          → '06' (Partial Benefit)
```

### Processing Clearinghouse 837 Claims

**Scenario**: Health plan receiving 837 files from clearinghouses for member risk scoring.

```python
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.extractor import extract_sld_list

# Configure processor
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    filter_claims=True
)

# Process multiple 837 files
claim_files = ["inst_claims.txt", "prof_claims.txt"]
all_service_data = []

for file_path in claim_files:
    with open(file_path, "r") as f:
        claims_data = f.read()
    service_data = extract_sld_list([claims_data], format="837")
    all_service_data.extend(service_data)

# Member demographics (from enrollment system or 834 file)
demographics = Demographics(
    age=45,
    sex="F",
    dual_elgbl_cd="02",    # Full benefit dual from 834
    orig_disabled=True,
    new_enrollee=False
)

# Calculate risk score
result = processor.run_from_service_data(all_service_data, demographics)

print(f"Member Risk Score: {result.risk_score:.3f}")
print(f"Active HCCs: {result.hcc_list}")
print(f"Total Services: {len(result.service_level_data)}")
```

### Using CMS BCDA API Data

**Scenario**: Building an application that processes Medicare beneficiary data from the BCDA API.

```python
from hccinfhir import HCCInFHIR, Demographics
import requests

# Configure for BCDA data
processor = HCCInFHIR(
    model_name="CMS-HCC Model V24",  # BCDA typically uses V24
    filter_claims=True,
    dx_cc_mapping_filename="ra_dx_to_cc_2025.csv"
)

# Fetch EOB data from BCDA
# headers = {"Authorization": f"Bearer {access_token}"}
# response = requests.get("https://sandbox.bcda.cms.gov/api/v2/Patient/$export", headers=headers)
# eob_resources = response.json()

# For demo, use sample data
from hccinfhir import get_eob_sample_list
eob_resources = get_eob_sample_list(limit=50)

# Demographics (extract from EOB or enrollment system)
demographics = Demographics(
    age=68,
    sex="M",
    dual_elgbl_cd="00",
    new_enrollee=False,
    esrd=False
)

# Process FHIR data
result = processor.run(eob_resources, demographics)

print(f"Beneficiary Risk Score: {result.risk_score:.3f}")
print(f"HCC Categories: {', '.join(result.hcc_list)}")
print(f"Service Period: {min(svc.service_date for svc in result.service_level_data if svc.service_date)} to {max(svc.service_date for svc in result.service_level_data if svc.service_date)}")
```

### Direct Diagnosis Code Processing

**Scenario**: Quick HCC mapping validation or research without claims data.

```python
from hccinfhir import HCCInFHIR, Demographics

processor = HCCInFHIR(model_name="CMS-HCC Model V28")

demographics = Demographics(
    age=75,
    sex="F",
    dual_elgbl_cd="02",  # Full benefit dual
    orig_disabled=False,
    new_enrollee=False
)

diagnosis_codes = [
    "E11.9",   # Type 2 diabetes
    "I10",     # Hypertension
    "N18.3",   # CKD stage 3
    "F32.9",   # Depression
    "M79.3"    # Panniculitis
]

result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

print("=== HCC Risk Analysis ===")
print(f"Risk Score: {result.risk_score:.3f}")
print(f"HCC Categories: {result.hcc_list}")
print(f"\\nDiagnosis Mappings:")
for cc, dx_list in result.cc_to_dx.items():
    print(f"  HCC {cc}: {', '.join(dx_list)}")
print(f"\\nApplied Coefficients:")
for coeff_name, value in result.coefficients.items():
    print(f"  {coeff_name}: {value:.3f}")
if result.interactions:
    print(f"\\nDisease Interactions:")
    for interaction, value in result.interactions.items():
        print(f"  {interaction}: {value:.3f}")
```

## ⚙️ Configuration

### Supported HCC Models

| Model Name | Model Years | Use Case | Supported |
|------------|-------------|----------|-----------|
| `"CMS-HCC Model V22"` | 2024-2025 | Community populations | ✅ |
| `"CMS-HCC Model V24"` | 2024-2026 | Community populations (current) | ✅ |
| `"CMS-HCC Model V28"` | 2025-2026 | Community populations (latest) | ✅ |
| `"CMS-HCC ESRD Model V21"` | 2024-2025 | ESRD populations | ✅ |
| `"CMS-HCC ESRD Model V24"` | 2025-2026 | ESRD populations | ✅ |
| `"RxHCC Model V08"` | 2024-2026 | Part D prescription drug | ✅ |

### Custom Data Files

The library includes bundled CMS reference data for 2025 and 2026. You can override **all 5 data files** with custom versions:

```python
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    filter_claims=True,

    # All files support absolute paths, relative paths, or bundled filenames
    # See "Custom File Path Resolution" in Advanced Features for details

    # 1. CPT/HCPCS Procedure Codes (for CMS filtering)
    proc_filtering_filename="ra_eligible_cpt_hcpcs_2026.csv",

    # 2. Diagnosis to HCC Mapping (ICD-10 → HCC)
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv",

    # 3. HCC Hierarchies (parent HCCs suppress child HCCs)
    hierarchies_filename="ra_hierarchies_2026.csv",

    # 4. Chronic Condition Flags
    is_chronic_filename="hcc_is_chronic.csv",

    # 5. RAF Coefficients (demographic + HCC + interaction coefficients)
    coefficients_filename="ra_coefficients_2026.csv"
)
```

> **💡 Tip**: For custom file paths (absolute, relative, or current directory), see [Custom File Path Resolution](#custom-file-path-resolution) in Advanced Features.

**File Format Requirements**:

1. **proc_filtering** (`ra_eligible_cpt_hcpcs_2026.csv`):
```csv
cpt_hcpcs_code
99213
99214
99215
```

2. **dx_cc_mapping** (`ra_dx_to_cc_2026.csv`):
```csv
diagnosis_code,cc,model_name
E119,38,CMS-HCC Model V28
I10,226,CMS-HCC Model V28
```

3. **hierarchies** (`ra_hierarchies_2026.csv`):
```csv
cc_parent,cc_child,model_domain,model_version,model_fullname
17,18,CMS-HCC,V28,CMS-HCC Model V28
17,19,CMS-HCC,V28,CMS-HCC Model V28
```

4. **is_chronic** (`hcc_is_chronic.csv`):
```csv
hcc,is_chronic,model_version,model_domain
1,True,V28,CMS-HCC
2,False,V28,CMS-HCC
```

5. **coefficients** (`ra_coefficients_2026.csv`):
```csv
coefficient,value,model_domain,model_version
cna_f70_74,0.395,CMS-HCC,V28
cna_hcc19,0.302,CMS-HCC,V28
```

> **📁 Reference**: See complete file formats and structure in the bundled data folder: [src/hccinfhir/data](https://github.com/mimilabs/hccinfhir/tree/main/src/hccinfhir/data)

### Demographics Configuration

```python
from hccinfhir import Demographics

demographics = Demographics(
    # Required fields
    age=67,                    # Age in years
    sex="F",                   # "M" or "F" (also accepts "1" or "2")

    # Dual eligibility (critical for payment accuracy)
    dual_elgbl_cd="00",        # "00"=Non-dual, "01"=Partial, "02"=Full
                               # "03"=Partial, "04"=Full, "05"=QDWI
                               # "06"=QI, "08"=Other full benefit dual

    # Medicare entitlement
    orec="0",                  # Original reason for entitlement
                               # "0"=Old age, "1"=Disability, "2"=ESRD, "3"=Both
    crec="0",                  # Current reason for entitlement

    # Status flags
    orig_disabled=False,       # Original disability (affects category)
    new_enrollee=False,        # New to Medicare (<12 months)
    esrd=False,                # End-Stage Renal Disease (auto-detected from orec/crec)

    # Optional fields
    snp=False,                 # Special Needs Plan
    low_income=False,          # Low-income subsidy (Part D)
    lti=False,                 # Long-term institutionalized
    graft_months=None,         # Months since kidney transplant (ESRD models)
    fbd=False,                 # Full benefit dual (auto-set from dual_elgbl_cd)
    pbd=False,                 # Partial benefit dual (auto-set)

    # Auto-calculated (can override)
    category="CNA"             # Beneficiary category (auto-calculated if omitted)
)
```

## 📚 API Reference

### Main Classes

#### `HCCInFHIR`
Main processor class for HCC risk adjustment calculations.

**Initialization**:
```python
HCCInFHIR(
    filter_claims: bool = True,
    model_name: ModelName = "CMS-HCC Model V28",
    proc_filtering_filename: str = "ra_eligible_cpt_hcpcs_2026.csv",
    dx_cc_mapping_filename: str = "ra_dx_to_cc_2026.csv",
    hierarchies_filename: str = "ra_hierarchies_2026.csv",
    is_chronic_filename: str = "hcc_is_chronic.csv",
    coefficients_filename: str = "ra_coefficients_2026.csv"
)
```

**Methods**:
- `run(eob_list, demographics, prefix_override=None, maci=0.0, norm_factor=1.0, frailty_score=0.0)`
  - Process FHIR ExplanationOfBenefit resources

- `run_from_service_data(service_data, demographics, prefix_override=None, maci=0.0, norm_factor=1.0, frailty_score=0.0)`
  - Process service-level data

- `calculate_from_diagnosis(diagnosis_codes, demographics, prefix_override=None, maci=0.0, norm_factor=1.0, frailty_score=0.0)`
  - Calculate from diagnosis codes only

#### `Demographics`
Patient demographic information for risk adjustment.

**Key Fields**:
- `age: int` - Patient age in years
- `sex: str` - Patient sex ("M"/"F" or "1"/"2")
- `dual_elgbl_cd: str` - Dual eligibility status (see configuration)
- `orec: str` - Original reason for Medicare entitlement
- `crec: str` - Current reason for Medicare entitlement
- `orig_disabled: bool` - Original disability status
- `new_enrollee: bool` - New enrollee flag
- `esrd: bool` - ESRD status (auto-calculated from orec/crec)
- `snp: bool` - Special Needs Plan
- `low_income: bool` - Low-income subsidy
- `lti: bool` - Long-term institutionalized
- `graft_months: Optional[int]` - Months since kidney transplant

#### `RAFResult`
Comprehensive risk adjustment calculation results.

**Fields**:
- `risk_score: float` - Final RAF score
- `risk_score_demographics: float` - Demographics-only component
- `risk_score_chronic_only: float` - Chronic conditions component (V24/V28)
- `risk_score_hcc: float` - HCC conditions component
- `risk_score_payment: float` - Final payment RAF with adjustments
- `hcc_list: List[str]` - Active HCC categories
- `cc_to_dx: Dict[str, Set[str]]` - HCCs mapped to diagnosis codes
- `coefficients: Dict[str, float]` - Applied coefficients
- `interactions: Dict[str, float]` - Disease interactions
- `demographics: Demographics` - Demographics used
- `model_name: str` - HCC model used
- `version: str` - Library version
- `diagnosis_codes: List[str]` - Input diagnosis codes
- `service_level_data: Optional[List[ServiceLevelData]]` - Service records

### Utility Functions

```python
from hccinfhir import (
    get_eob_sample,           # Get sample FHIR EOB
    get_837_sample,           # Get sample 837 claim
    get_834_sample,           # Get sample 834 enrollment
    get_eob_sample_list,      # Get multiple EOBs
    get_837_sample_list,      # Get multiple 837s
    list_available_samples,   # List all samples
)

from hccinfhir.extractor import (
    extract_sld,              # Extract from single resource
    extract_sld_list,         # Extract from multiple resources
)

from hccinfhir.extractor_834 import (
    extract_enrollment_834,       # Parse 834 enrollment file
    enrollment_to_demographics,   # Convert to Demographics
    is_losing_medicaid,           # Check Medicaid loss
    medicaid_status_summary,      # Get comprehensive status
)

from hccinfhir.filter import apply_filter  # Apply CMS filtering
from hccinfhir.model_calculate import calculate_raf  # Direct calculation
```

## 🔧 Advanced Features

### Payment RAF Adjustments

Apply CMS payment adjustments to RAF scores:

```python
from hccinfhir import HCCInFHIR, Demographics

processor = HCCInFHIR(model_name="CMS-HCC Model V28")
demographics = Demographics(age=70, sex="F")
diagnosis_codes = ["E11.9", "I50.22", "N18.3"]

# Apply payment adjustments
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    maci=0.059,         # MA Coding Intensity Adjustment (5.9% reduction for 2026)
    norm_factor=1.015,  # Normalization factor (1.5% for 2026)
    frailty_score=0.0   # Frailty adjustment (if applicable)
)

print(f"Base RAF Score: {result.risk_score:.3f}")
print(f"Payment RAF Score: {result.risk_score_payment:.3f}")
print(f"Payment Adjustment: {((result.risk_score_payment / result.risk_score) - 1) * 100:.1f}%")
```

**Common Adjustment Values**:
- **MACI** (MA Coding Intensity): 5.94% (2025), 5.90% (2026)
- **Normalization**: 1.022 (2025), 1.015 (2026)
- **Frailty**: 0.0 to 0.6 (when applicable)

### Demographic Prefix Override

**Problem**: Demographic data quality issues leading to incorrect RAF calculations.

**Solution**: Manually specify the coefficient prefix.

```python
from hccinfhir import HCCInFHIR, Demographics

# ESRD patient with incorrect orec/crec codes
processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")
demographics = Demographics(
    age=65,
    sex="F",
    orec="0",  # Should be '2' or '3', but data is wrong
    crec="0"
)
diagnosis_codes = ["N18.6", "E11.22", "I12.0"]

# Force ESRD dialysis coefficients
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='DI_'  # ESRD Dialysis prefix
)

print(f"RAF Score with override: {result.risk_score:.3f}")
```

**Common Prefix Values**:

CMS-HCC Models:
- `CNA_` - Community, Non-Dual, Aged
- `CND_` - Community, Non-Dual, Disabled
- `CFA_` - Community, Full Benefit Dual, Aged
- `CFD_` - Community, Full Benefit Dual, Disabled
- `CPA_` - Community, Partial Benefit Dual, Aged
- `CPD_` - Community, Partial Benefit Dual, Disabled
- `INS_` - Long-Term Institutionalized
- `NE_` - New Enrollee
- `SNPNE_` - SNP New Enrollee

ESRD Models:
- `DI_` - Dialysis
- `DNE_` - Dialysis New Enrollee
- `GI_`, `GNE_` - Graft variations

RxHCC Models:
- `Rx_CE_LowAged_` - Community, Low Income, Aged
- `Rx_CE_NoLowAged_` - Community, Not Low Income, Aged
- `Rx_NE_Lo_` - New Enrollee, Low Income

See [CLAUDE.md](./CLAUDE.md#coefficient-prefix-reference) for complete reference.

### Custom File Path Resolution

The library uses intelligent path resolution to locate data files with the following priority:

1. **Absolute path** - If you provide an absolute path, it uses that exact location
2. **Relative to current working directory** - Checks `./your_file.csv` or `./custom_data/your_file.csv`
3. **Bundled package data** - Falls back to built-in CMS reference files

This allows flexible deployment scenarios without changing code.

> **📁 Data File Reference**: See the bundled CMS reference files for format examples: [src/hccinfhir/data](https://github.com/mimilabs/hccinfhir/tree/main/src/hccinfhir/data)

#### Basic Examples

```python
from hccinfhir import HCCInFHIR

# Option 1: Use bundled data (default - no setup needed)
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv"  # ✅ Loads from package
)

# Option 2: Relative path from current directory
# Assumes: ./custom_data/my_dx_mapping.csv exists
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="custom_data/my_dx_mapping.csv"  # ✅ ./custom_data/
)

# Option 3: Absolute path (production deployments)
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="/var/data/cms/dx_mapping_2026.csv"  # ✅ Absolute
)

# Option 4: Mix bundled and custom files
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv",  # Bundled default
    coefficients_filename="custom_coefficients.csv"  # Custom from current dir
)
```

#### Real-World Scenarios

**Scenario 1: Development Environment**
```python
# Use bundled files for testing
processor = HCCInFHIR(model_name="CMS-HCC Model V28")
```

**Scenario 2: Custom Coefficients for Research**
```python
# Keep standard mappings, customize coefficients
# File: ./research/adjusted_coefficients.csv
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    coefficients_filename="research/adjusted_coefficients.csv"
)
```

**Scenario 3: Production with Centralized Data**
```python
# All custom files in shared network location
data_path = "/mnt/shared/cms_data/2026"
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    proc_filtering_filename=f"{data_path}/cpt_hcpcs.csv",
    dx_cc_mapping_filename=f"{data_path}/dx_to_cc.csv",
    hierarchies_filename=f"{data_path}/hierarchies.csv",
    is_chronic_filename=f"{data_path}/chronic_flags.csv",
    coefficients_filename=f"{data_path}/coefficients.csv"
)
```

**Scenario 4: Docker Container with Mounted Volume**
```python
# Files mounted at /app/data
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="/app/data/dx_to_cc_custom.csv",
    coefficients_filename="/app/data/coefficients_custom.csv"
    # Other files use bundled defaults
)
```

#### Error Handling

```python
from hccinfhir import HCCInFHIR

try:
    processor = HCCInFHIR(
        model_name="CMS-HCC Model V28",
        dx_cc_mapping_filename="nonexistent.csv"
    )
except FileNotFoundError as e:
    print(f"File not found: {e}")
    # Error shows all locations checked:
    # - Current directory: /path/to/cwd
    # - Package data: hccinfhir.data
```

### Batch Processing

```python
from hccinfhir import HCCInFHIR, Demographics

processor = HCCInFHIR(model_name="CMS-HCC Model V28")

# Process multiple beneficiaries
beneficiaries = [
    {"id": "001", "age": 67, "sex": "F", "dual": "00", "dx": ["E11.9", "I10"]},
    {"id": "002", "age": 45, "sex": "M", "dual": "02", "dx": ["N18.4", "F32.9"]},
    {"id": "003", "age": 78, "sex": "F", "dual": "01", "dx": ["F03.90", "I48.91"]},
]

results = []
for ben in beneficiaries:
    demographics = Demographics(
        age=ben["age"],
        sex=ben["sex"],
        dual_elgbl_cd=ben["dual"]
    )
    result = processor.calculate_from_diagnosis(ben["dx"], demographics)
    results.append({
        "beneficiary_id": ben["id"],
        "risk_score": result.risk_score,
        "risk_score_payment": result.risk_score_payment,
        "hcc_list": result.hcc_list
    })

# Export results
import json
with open("risk_scores.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Large-Scale Processing with Databricks

For processing millions of beneficiaries, use PySpark's `pandas_udf` for distributed computation. The hccinfhir logic is well-suited for batch operations with clear, simple transformations.

**Performance Benchmark**:

![Databricks Performance Chart](hccinfhir_pandas_udf_performance_chart.png)

*Tested with ACO data on Databricks Runtime 17.3 LTS, Worker: i3.4xlarge (122GB, 16 cores)*

The chart shows execution time varies based on condition complexity - members with more diagnoses require additional internal processing loops. While the relationship isn't perfectly linear, **1 million members can be processed in under 2 minutes** with this configuration.

```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, FloatType, ArrayType, StringType
from pyspark.sql import functions as F
from pyspark.sql.functions import pandas_udf
import pandas as pd

from hccinfhir import HCCInFHIR, Demographics

# Define the return schema
hcc_schema = StructType([
    StructField("risk_score", FloatType(), True),
    StructField("risk_score_demographics", FloatType(), True),
    StructField("risk_score_chronic_only", FloatType(), True),
    StructField("risk_score_hcc", FloatType(), True),
    StructField("hcc_list", ArrayType(StringType()), True)
])

# Initialize processor (will be serialized to each executor)
hcc_processor = HCCInFHIR(model_name="CMS-HCC Model V28")

# Create the pandas UDF
@pandas_udf(hcc_schema)
def calculate_hcc(
    age_series: pd.Series,
    sex_series: pd.Series,
    diagnosis_series: pd.Series
) -> pd.DataFrame:
    results = []

    for age, sex, diagnosis_codes in zip(age_series, sex_series, diagnosis_series):
        try:
            demographics = Demographics(age=int(age), sex=sex)

            # diagnosis_codes can be passed directly - accepts any iterable including numpy arrays
            result = hcc_processor.calculate_from_diagnosis(diagnosis_codes, demographics)

            results.append({
                'risk_score': float(result.risk_score),
                'risk_score_demographics': float(result.risk_score_demographics),
                'risk_score_chronic_only': float(result.risk_score_chronic_only),
                'risk_score_hcc': float(result.risk_score_hcc),
                'hcc_list': result.hcc_list
            })
        except Exception as e:
            # Log error and return nulls for failed rows
            print(f"ERROR processing row: {e}")
            results.append({
                'risk_score': None,
                'risk_score_demographics': None,
                'risk_score_chronic_only': None,
                'risk_score_hcc': None,
                'hcc_list': None
            })

    return pd.DataFrame(results)

# Apply the UDF to your DataFrame
# Assumes df has columns: age, patient_gender, diagnosis_codes (array of strings)
df = df.withColumn(
    "hcc_results",
    calculate_hcc(
        F.col("age"),
        F.col("patient_gender"),
        F.col("diagnosis_codes")
    )
)

# Expand the struct into separate columns
df = df.select(
    "*",
    F.col("hcc_results.risk_score").alias("risk_score"),
    F.col("hcc_results.risk_score_demographics").alias("risk_score_demographics"),
    F.col("hcc_results.risk_score_chronic_only").alias("risk_score_chronic_only"),
    F.col("hcc_results.risk_score_hcc").alias("risk_score_hcc"),
    F.col("hcc_results.hcc_list").alias("hcc_list")
).drop("hcc_results")
```

**Performance Tips**:
- **Repartition** your DataFrame before applying the UDF to balance workload across executors
- **Cache** the processor initialization by defining it at module level
- **Batch size**: pandas_udf processes data in batches; Spark handles optimal batch sizing automatically
- **Install hccinfhir** on all cluster nodes: `%pip install hccinfhir` in a notebook cell or add to cluster init script

**Extended Schema with Demographics**:

```python
# Include additional demographic parameters
@pandas_udf(hcc_schema)
def calculate_hcc_full(
    age_series: pd.Series,
    sex_series: pd.Series,
    dual_status_series: pd.Series,
    diagnosis_series: pd.Series
) -> pd.DataFrame:
    results = []

    for age, sex, dual_status, diagnosis_codes in zip(
        age_series, sex_series, dual_status_series, diagnosis_series
    ):
        try:
            demographics = Demographics(
                age=int(age),
                sex=sex,
                dual_elgbl_cd=dual_status if dual_status else "00"
            )
            result = hcc_processor.calculate_from_diagnosis(diagnosis_codes, demographics)

            results.append({
                'risk_score': float(result.risk_score),
                'risk_score_demographics': float(result.risk_score_demographics),
                'risk_score_chronic_only': float(result.risk_score_chronic_only),
                'risk_score_hcc': float(result.risk_score_hcc),
                'hcc_list': result.hcc_list
            })
        except Exception as e:
            results.append({
                'risk_score': None,
                'risk_score_demographics': None,
                'risk_score_chronic_only': None,
                'risk_score_hcc': None,
                'hcc_list': None
            })

    return pd.DataFrame(results)
```

### Converting to Dictionaries

All Pydantic models support dictionary conversion for JSON serialization, database storage, or legacy code:

```python
from hccinfhir import HCCInFHIR, Demographics

processor = HCCInFHIR(model_name="CMS-HCC Model V28")
demographics = Demographics(age=67, sex="F")
result = processor.calculate_from_diagnosis(["E11.9"], demographics)

# Convert to dictionary
result_dict = result.model_dump()
print(result_dict["risk_score"])  # Dictionary access

# JSON-safe conversion
result_json = result.model_dump(mode='json')

# Partial conversion
summary = result.model_dump(include={"risk_score", "hcc_list", "model_name"})

# Exclude large nested data
compact = result.model_dump(exclude={"service_level_data"})

# Convert to JSON string
json_string = result.model_dump_json()

# API response (FastAPI)
from fastapi import FastAPI
app = FastAPI()

@app.post("/calculate")
def calculate_risk(diagnosis_codes: list, demographics: dict):
    demo = Demographics(**demographics)
    result = processor.calculate_from_diagnosis(diagnosis_codes, demo)
    return result.model_dump(mode='json')  # Automatic JSON serialization
```

## 📝 Sample Data

Comprehensive sample data for testing and development:

```python
from hccinfhir import (
    get_eob_sample,
    get_837_sample,
    get_834_sample,
    list_available_samples
)

# FHIR EOB samples (3 individual + 200 batch)
eob = get_eob_sample(1)  # Cases 1, 2, 3 (returns single dict)
eob_list = get_eob_sample_list(limit=50)  # Returns list

# Usage: processor.run() expects a list, so wrap single EOB
result = processor.run([eob], demographics)  # Note: [eob] not eob

# X12 837 samples (13 different scenarios)
claim = get_837_sample(0)  # Cases 0-12 (returns string)
claims = get_837_sample_list([0, 1, 2])  # Returns list

# X12 834 enrollment samples (6 CA DHCS scenarios)
enrollment_834 = get_834_sample(1)  # Cases 1-6 available (returns string)

# List all available samples
info = list_available_samples()
print(f"EOB samples: {info['eob_case_numbers']}")
print(f"837 samples: {info['837_case_numbers']}")
print(f"834 samples: {info['834_case_numbers']}")
```

## 🧪 Testing

```bash
# Activate virtual environment
hatch shell

# Install in development mode
pip install -e .

# Run all tests (189 tests)
pytest tests/

# Run specific test file
pytest tests/test_model_calculate.py -v

# Run with coverage
pytest tests/ --cov=hccinfhir --cov-report=html
```

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE) for details.

## 📞 Support

- **Claude Code Documentation**: [CLAUDE.md](./CLAUDE.md) - Comprehensive developer guide
- **Issues**: [GitHub Issues](https://github.com/mimilabs/hccinfhir/issues)

## 👥 Contributors

We're grateful to all contributors who have helped improve this project:

- [@choyiny](https://github.com/choyiny) - Custom CSV input feature, file path improvements

**Want to contribute?** We're always looking for great minds to contribute to this project! Simply make a PR or open a ticket and we'll get connected.

---

**Made with ❤️ by the HCCInFHIR team**
