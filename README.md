# HCCInFHIR

[![PyPI version](https://badge.fury.io/py/hccinfhir.svg)](https://badge.fury.io/py/hccinfhir)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A Python library for calculating HCC (Hierarchical Condition Category) risk adjustment scores from healthcare claims data. Supports multiple data sources including FHIR resources, X12 837 claims, and CMS encounter data.

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

- [Data Sources & Use Cases](#data-sources--use-cases)
- [Installation](#installation)
- [How-To Guides](#how-to-guides)
  - [Working with CMS Encounter Data (EDRs)](#working-with-cms-encounter-data-edrs)
  - [Processing 837 Claims from Clearinghouses](#processing-837-claims-from-clearinghouses)
  - [Using CMS BCDA API Data](#using-cms-bcda-api-data)
  - [Direct Diagnosis Code Processing](#direct-diagnosis-code-processing)
- [Model Configuration](#model-configuration)
- [API Reference](#api-reference)
- [Sample Data](#sample-data)
- [Advanced Usage](#advanced-usage)

## 📊 Data Sources & Use Cases

HCCInFHIR supports three primary data sources for HCC risk adjustment calculations:

### 1. **CMS Encounter Data Records (EDRs)**
- **Input**: X12 837 5010 transaction files (text format) + demographic data from payers
- **Use Case**: Medicare Advantage plans processing encounter data for CMS submissions
- **Output**: Risk scores with detailed HCC mappings and interactions

### 2. **Clearinghouse 837 Claims**
- **Input**: X12 837 5010 institutional/professional claim files + patient demographics
- **Use Case**: Health plans and providers calculating risk scores from claims data
- **Output**: Service-level analysis with filtering and risk score calculations

### 3. **CMS BCDA API Data**
- **Input**: FHIR ExplanationOfBenefit resources from Blue Button 2.0 API
- **Use Case**: Applications processing Medicare beneficiary data via BCDA
- **Output**: Standardized risk adjustment calculations from FHIR resources

### 4. **Direct Diagnosis Processing**
- **Input**: Diagnosis codes + demographics
- **Use Case**: Quick risk score validation or research applications
- **Output**: HCC mappings and risk scores without claims context

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

### Working with CMS Encounter Data (EDRs)

**Scenario**: You're a Medicare Advantage plan processing encounter data for CMS risk adjustment.

**What you need**:
- X12 837 envelope files from your claims system
- Demographic data (age, sex, eligibility status) for each beneficiary
- Knowledge of your plan's model year and HCC model version

```python
from hccinfhir import HCCInFHIR, Demographics, get_837_sample
from hccinfhir.extractor import extract_sld

# Step 1: Configure processor for your model year and version
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",           # CMS model version
    filter_claims=True,                       # Apply CMS filtering rules
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv",
    proc_filtering_filename="ra_eligible_cpt_hcpcs_2026.csv"
)

# Step 2: Load your 837 data
with open("encounter_data.txt", "r") as f:
    raw_837_data = f.read()

# Step 3: Extract service-level data
service_data = extract_sld(raw_837_data, format="837")

# Step 4: Define beneficiary demographics
demographics = Demographics(
    age=72,
    sex="M",
    dual_elgbl_cd="00",     # Dual eligibility status
    orig_disabled=False,     # Original disability status
    new_enrollee=False,      # New enrollee flag
    esrd=False              # ESRD status
)

# Step 5: Calculate risk score
result = processor.run_from_service_data(service_data, demographics)

# Step 6: Review results
print(f"Beneficiary Risk Score: {result.risk_score}")
print(f"Active HCCs: {result.hcc_list}")
print(f"Disease Interactions: {result.interactions}")

# Export results for CMS submission
encounter_summary = {
    "beneficiary_id": "example_id",
    "risk_score": result.risk_score,
    "hcc_list": result.hcc_list,
    "model_version": "V28",
    "payment_year": 2026
}
```

### Processing 837 Claims from Clearinghouses

**Scenario**: You're a health plan receiving 837 files from clearinghouses and need to calculate member risk scores.

```python
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.extractor import extract_sld_list

# Configure for institutional and professional claims
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    filter_claims=True,    # Enable CMS filtering
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv"
)

# Process multiple 837 files
claim_files = ["inst_claims.txt", "prof_claims.txt"]
all_service_data = []

for file_path in claim_files:
    with open(file_path, "r") as f:
        claims_data = f.read()
    
    # Extract service data from each file
    service_data = extract_sld_list([claims_data], format="837")
    all_service_data.extend(service_data)

# Member demographics (typically from your enrollment system)
member_demographics = Demographics(
    age=45,
    sex="F",
    dual_elgbl_cd="02",    # Partial dual eligible
    orig_disabled=True,     # Originally disabled
    new_enrollee=False
)

# Calculate comprehensive risk score
result = processor.run_from_service_data(all_service_data, member_demographics)

# Analyze by service type
professional_services = [svc for svc in result.service_level_data if svc.claim_type == "71"]
institutional_services = [svc for svc in result.service_level_data if svc.claim_type == "72"]

print(f"Member Risk Score: {result.risk_score}")
print(f"Professional Claims: {len(professional_services)}")
print(f"Institutional Claims: {len(institutional_services)}")
```

### Using CMS BCDA API Data

**Scenario**: You're building an application that processes Medicare beneficiary data from the BCDA API.

```python
from hccinfhir import HCCInFHIR, Demographics, get_eob_sample_list
from hccinfhir.extractor import extract_sld_list
import requests

# Configure processor for BCDA data
processor = HCCInFHIR(
    model_name="CMS-HCC Model V24",    # BCDA typically uses V24
    filter_claims=True,
    dx_cc_mapping_filename="ra_dx_to_cc_2025.csv"
)

# Fetch EOB data from BCDA (example using sample data)
eob_resources = get_eob_sample_list(limit=50)  # Replace with actual BCDA API call

# Extract service-level data from FHIR resources
service_data = extract_sld_list(eob_resources, format="fhir")

# BCDA provides beneficiary demographics in the EOB
# Extract demographics from the first EOB resource
first_eob = eob_resources[0]
beneficiary_ref = first_eob.get("patient", {}).get("reference", "")

# You would typically look up demographics from your system
demographics = Demographics(
    age=68,
    sex="M",
    dual_elgbl_cd="00",
    new_enrollee=False,
    esrd=False
)

# Process FHIR data
result = processor.run(eob_resources, demographics)

# BCDA-specific analysis
print(f"Beneficiary: {beneficiary_ref}")
print(f"Risk Score: {result.risk_score}")
print(f"Data Source: BCDA API")
print(f"HCC Categories: {', '.join(map(str, result.hcc_list))}")

# Examine service utilization patterns
service_dates = [svc.service_date for svc in result.service_level_data if svc.service_date]
if service_dates:
    print(f"Service Period: {min(service_dates)} to {max(service_dates)}")
```

### Direct Diagnosis Code Processing

**Scenario**: You need to quickly validate HCC mappings or calculate risk scores for research purposes.

```python
from hccinfhir import HCCInFHIR, Demographics

# Simple setup for diagnosis-only processing
processor = HCCInFHIR(model_name="CMS-HCC Model V28")

# Define patient population
demographics = Demographics(
    age=75,
    sex="F",
    dual_elgbl_cd="02",  # Dual eligible
    orig_disabled=False,
    new_enrollee=False,
    esrd=False
)

# Diagnosis codes from clinical encounter
diagnosis_codes = [
    "E11.9",   # Type 2 diabetes without complications
    "I10",     # Essential hypertension  
    "N18.3",   # Chronic kidney disease, stage 3
    "F32.9",   # Major depressive disorder
    "M79.3"    # Panniculitis
]

# Calculate risk score
result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

# Detailed analysis
print("=== HCC Risk Analysis ===")
print(f"Risk Score: {result.risk_score:.3f}")
print(f"HCC Categories: {result.hcc_list}")

# Show diagnosis to HCC mappings
print("\nDiagnosis Mappings:")
for cc, dx_list in result.cc_to_dx.items():
    print(f"  CC {cc}: {', '.join(dx_list)}")

# Show applied coefficients
print(f"\nApplied Coefficients: {len(result.coefficients)}")
for coeff_name, value in result.coefficients.items():
    print(f"  {coeff_name}: {value}")

# Check for interactions
if result.interactions:
    print(f"\nDisease Interactions: {len(result.interactions)}")
    for interaction, value in result.interactions.items():
        print(f"  {interaction}: {value}")
```

## ⚙️ Model Configuration

### Supported HCC Models

| Model Name | Model Years | Use Case |
|------------|-------------|----------|
| `"CMS-HCC Model V22"` | 2024-2025 | Community populations |
| `"CMS-HCC Model V24"` | 2024-2026 | Community populations (current) |
| `"CMS-HCC Model V28"` | 2025-2026 | Community populations (latest) |
| `"CMS-HCC ESRD Model V21"` | 2024-2025 | ESRD populations |
| `"CMS-HCC ESRD Model V24"` | 2025-2026 | ESRD populations |
| `"RxHCC Model V08"` | 2024-2026 | Part D prescription drug coverage |

### Configuration Parameters

```python
processor = HCCInFHIR(
    # Core model settings
    model_name="CMS-HCC Model V28",              # Required: HCC model version
    
    # Filtering options
    filter_claims=True,                          # Apply CMS filtering rules
    
    # Custom data files (optional)
    dx_cc_mapping_filename="ra_dx_to_cc_2026.csv",           # Diagnosis to CC mapping
    proc_filtering_filename="ra_eligible_cpt_hcpcs_2026.csv", # Procedure code filtering
)
```

### Demographics Configuration

```python
from hccinfhir import Demographics

demographics = Demographics(
    # Required fields
    age=67,                    # Age in years
    sex="F",                   # "M" or "F"
    
    # CMS-specific fields
    dual_elgbl_cd="00",        # Dual eligibility: "00"=Non-dual, "01"=Partial, "02"=Full
    orig_disabled=False,        # Original reason for Medicare entitlement was disability
    new_enrollee=False,        # New Medicare enrollee (< 12 months)
    esrd=False,                # End-Stage Renal Disease status
    
    # Optional fields
    snp=False,                 # Special Needs Plan member
    low_income=False,          # Low-income subsidy
    graft_months=None,         # Months since kidney transplant (for ESRD models)
    category="CNA"             # Beneficiary category (auto-calculated if not provided)
)
```

### Data File Specifications

The library includes CMS reference data files for 2025 and 2026. You can override with custom files:

```python
# Use custom mapping files
processor = HCCInFHIR(
    model_name="CMS-HCC Model V28",
    dx_cc_mapping_filename="custom_dx_mapping.csv",      # Format: diagnosis_code,cc,model_name
    proc_filtering_filename="custom_procedures.csv"      # Format: cpt_hcpcs_code
)
```

## 📚 API Reference

### Main Classes

#### `HCCInFHIR`
Main processor class for HCC calculations.

**Methods**:
- `run(eob_list, demographics)` - Process FHIR ExplanationOfBenefit resources
- `run_from_service_data(service_data, demographics)` - Process service-level data
- `calculate_from_diagnosis(diagnosis_codes, demographics)` - Calculate from diagnosis codes only

#### `Demographics`
Patient demographic information for risk adjustment.

**Fields**:
- `age: int` - Patient age in years
- `sex: str` - Patient sex ("M" or "F")  
- `dual_elgbl_cd: str` - Dual eligibility code
- `orig_disabled: bool` - Original disability status
- `new_enrollee: bool` - New enrollee flag
- `esrd: bool` - ESRD status

#### `RAFResult`
Risk adjustment calculation results.

**Fields**:
- `risk_score: float` - Final RAF score
- `risk_score_demographics: float` - Demographics-only risk score
- `risk_score_chronic_only: float` - Chronic conditions risk score
- `risk_score_hcc: float` - HCC conditions risk score
- `hcc_list: List[str]` - List of active HCC categories
- `cc_to_dx: Dict[str, Set[str]]` - Condition categories mapped to diagnosis codes
- `coefficients: Dict[str, float]` - Applied model coefficients
- `interactions: Dict[str, float]` - Disease interaction coefficients
- `demographics: Demographics` - Patient demographics used in calculation
- `model_name: ModelName` - HCC model used for calculation
- `version: str` - Library version
- `diagnosis_codes: List[str]` - Input diagnosis codes
- `service_level_data: Optional[List[ServiceLevelData]]` - Processed service records (when applicable)

### Utility Functions

```python
from hccinfhir import (
    get_eob_sample,           # Get sample FHIR EOB data
    get_837_sample,           # Get sample 837 claim data
    list_available_samples,   # List all available sample data
    extract_sld,              # Extract service-level data from single resource
    extract_sld_list,         # Extract service-level data from multiple resources
    apply_filter              # Apply CMS filtering rules to service data
)
```

## 📝 Sample Data

The library includes comprehensive sample data for testing and development:

```python
from hccinfhir import get_eob_sample, get_837_sample, list_available_samples

# FHIR ExplanationOfBenefit samples
eob_data = get_eob_sample(1)                    # Individual EOB (cases 1, 2, 3)
eob_list = get_eob_sample_list(limit=10)        # Up to 200 EOB resources

# X12 837 claim samples  
claim_data = get_837_sample(0)                  # Individual 837 claim (cases 0-12)
claim_list = get_837_sample_list([0, 1, 2])    # Multiple 837 claims

# Sample information
sample_info = list_available_samples()
print(f"Available EOB samples: {len(sample_info['eob_case_numbers'])}")
print(f"Available 837 samples: {len(sample_info['837_case_numbers'])}")
```

## 🔧 Advanced Usage

### Converting to Dictionary Format

If you need to work with regular Python dictionaries (e.g., for JSON serialization, database storage, or legacy code compatibility), you can easily convert Pydantic models using built-in methods:

```python
from hccinfhir import HCCInFHIR, Demographics

processor = HCCInFHIR(model_name="CMS-HCC Model V28")
demographics = Demographics(age=67, sex="F")
diagnosis_codes = ["E11.9", "I10"]

# Get Pydantic model result
result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
print(f"Risk Score: {result.risk_score}")  # Pydantic attribute access

# Convert to dictionary
result_dict = result.model_dump()
print(f"Risk Score: {result_dict['risk_score']}")  # Dictionary access

# Convert with different modes
result_json_compatible = result.model_dump(mode='json')  # JSON-serializable types
result_python_types = result.model_dump(mode='python')   # Python native types (default)

# Convert only specific fields
partial_dict = result.model_dump(include={'risk_score', 'hcc_list', 'demographics'})

# Convert excluding certain fields  
summary_dict = result.model_dump(exclude={'service_level_data', 'interactions'})

# Convert to JSON string directly
json_string = result.model_dump_json()  # Returns JSON string
```

#### Working with Nested Models

```python
# Demographics also support dictionary conversion
demographics_dict = result.demographics.model_dump()
print(demographics_dict)
# Output: {'age': 67, 'sex': 'F', 'dual_elgbl_cd': '00', ...}

# Service data conversion (list of Pydantic models)
if result.service_level_data:
    service_dicts = [svc.model_dump() for svc in result.service_level_data]
```

#### Common Use Cases

**1. API Responses:**
```python
# FastAPI automatically handles Pydantic models, but for other frameworks:
@app.route('/calculate')
def calculate_risk():
    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
    return jsonify(result.model_dump(mode='json'))  # JSON-safe types
```

**2. Database Storage:**
```python
# Store in database
result_data = result.model_dump(exclude={'service_level_data'})  # Exclude large nested data
db.risks.insert_one(result_data)
```

**3. Legacy Code Integration:**
```python
# Working with existing code that expects dictionaries
def legacy_function(risk_data):
    return risk_data['risk_score'] * risk_data['demographics']['age']

# Easy conversion
result_dict = result.model_dump()
legacy_result = legacy_function(result_dict)
```

**4. Custom Serialization:**
```python
# Custom formatting for specific needs
export_data = result.model_dump(
    include={'risk_score', 'hcc_list', 'model_name'},
    mode='json'
)
```

### Overriding Demographic Categorization

**Problem**: Sometimes demographic data has quality issues (e.g., ESRD patients with incorrect `orec`/`crec` codes), leading to wrong risk score calculations.

**Solution**: Use the `prefix_override` parameter to manually specify the coefficient prefix.

#### Common Use Case: ESRD Patients with Incorrect OREC/CREC

```python
from hccinfhir import HCCInFHIR, Demographics

# ESRD dialysis patient, but source data has wrong orec/crec codes
processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")

demographics = Demographics(
    age=65,
    sex="F",
    orec="0",  # Should be '2' or '3' for ESRD, but data is incorrect
    crec="0"   # Should be '2' or '3' for ESRD, but data is incorrect
)

diagnosis_codes = ["N18.6", "E11.22", "I12.0"]  # ESRD + diabetes + hypertensive CKD

# Force ESRD dialysis coefficients despite incorrect orec/crec
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='DI_'  # DI_ = ESRD Dialysis
)

print(f"Risk Score with override: {result.risk_score}")
```

#### Other Common Scenarios

```python
# Long-term institutionalized patient not properly flagged
processor = HCCInFHIR(model_name="CMS-HCC Model V28")
demographics = Demographics(age=78, sex="M")
diagnosis_codes = ["F03.90", "I48.91", "N18.4"]

result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='INS_'  # INS_ = Institutionalized
)

# New enrollee with missing flag
result = processor.calculate_from_diagnosis(
    diagnosis_codes,
    demographics,
    prefix_override='NE_'  # NE_ = New Enrollee
)
```

#### Common Prefix Values

**CMS-HCC Models (V22, V24, V28):**
- `CNA_` - Community, Non-Dual, Aged (65+)
- `CND_` - Community, Non-Dual, Disabled (<65)
- `CFA_` - Community, Full Benefit Dual, Aged
- `CFD_` - Community, Full Benefit Dual, Disabled
- `CPA_` - Community, Partial Benefit Dual, Aged
- `CPD_` - Community, Partial Benefit Dual, Disabled
- `INS_` - Long-Term Institutionalized
- `NE_` - New Enrollee
- `SNPNE_` - Special Needs Plan New Enrollee

**ESRD Models (V21, V24):**
- `DI_` - Dialysis (standard)
- `DNE_` - Dialysis New Enrollee
- `GI_` - Graft, Institutionalized
- `GNE_` - Graft, New Enrollee
- `GFPA_`, `GFPN_`, `GNPA_`, `GNPN_` - Graft with various dual/age combinations

**RxHCC Model (V08):**
- `Rx_CE_LowAged_` - Community, Low Income, Aged
- `Rx_CE_NoLowAged_` - Community, Not Low Income, Aged
- `Rx_NE_Lo_` - New Enrollee, Low Income
- `Rx_CE_LTI_` - Community, Long-Term Institutionalized

See [CLAUDE.md](./CLAUDE.md#coefficient-prefix-reference) for complete prefix reference.

### Custom Filtering Rules

```python
from hccinfhir.filter import apply_filter

# Apply custom filtering to service data
filtered_data = apply_filter(
    service_data,
    include_inpatient=True,
    include_outpatient=True,
    eligible_cpt_hcpcs_file="custom_procedures.csv"
)
```

### Batch Processing

```python
# Process multiple beneficiaries efficiently
results = []
for beneficiary_data in beneficiary_list:
    demographics = Demographics(**beneficiary_data['demographics'])
    service_data = beneficiary_data['service_data']
    
    result = processor.run_from_service_data(service_data, demographics)
    results.append({
        'beneficiary_id': beneficiary_data['id'],
        'risk_score': result.risk_score,
        'hcc_list': result.hcc_list
    })
```

### Error Handling

```python
from hccinfhir.exceptions import ValidationError, ModelNotFoundError

try:
    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
except ValidationError as e:
    print(f"Data validation error: {e}")
except ModelNotFoundError as e:
    print(f"Model configuration error: {e}")
```

### Custom Valuesets

Users can generate custom and more specific valuesets using the mimilabs data lakehouse.

For example, the valuesets in the package are created as follows:

`ra_dx_to_cc_mapping_2026.csv`
```sql
WITH latest_years AS (
  SELECT 
    model_name,
    MAX(year) as latest_year
  FROM mimi_ws_1.cmspayment.ra_dx_to_cc_mapping 
  WHERE model_type = 'Initial'
    AND year <= 2026  -- Don't go beyond 2026
  GROUP BY model_name
)
SELECT 
  r.diagnosis_code, 
  r.cc, 
  r.model_name
FROM mimi_ws_1.cmspayment.ra_dx_to_cc_mapping r
INNER JOIN latest_years l 
  ON r.model_name = l.model_name 
  AND r.year = l.latest_year
WHERE r.model_type = 'Initial'
ORDER BY r.model_name, r.diagnosis_code;
```

`ra_hierarchies_2026.csv`
```sql
WITH latest_dates AS (
  SELECT 
    model_domain,
    model_version,
    model_fullname,
    MAX(eff_last_date) as latest_eff_last_date
  FROM mimi_ws_1.cmspayment.ra_hierarchies 
  GROUP BY model_domain, model_version, model_fullname
)
SELECT 
  r.cc_parent, 
  r.cc_child, 
  r.model_domain, 
  r.model_version, 
  r.model_fullname
FROM mimi_ws_1.cmspayment.ra_hierarchies r
INNER JOIN latest_dates l 
  ON r.model_domain = l.model_domain 
  AND r.model_version = l.model_version
  AND r.model_fullname = l.model_fullname
  AND r.eff_last_date = l.latest_eff_last_date
ORDER BY r.model_domain, r.model_version, r.model_fullname, r.cc_parent, r.cc_child;
```


`ra_coefficients_2026.csv`
```sql
WITH preferred_records AS (
  SELECT 
    model_domain,
    model_version,
    MAX(eff_last_date) as latest_eff_last_date
  FROM mimi_ws_1.cmspayment.ra_coefficients
  GROUP BY model_domain, model_version
)
SELECT 
  r.coefficient,
  r.value, 
  r.model_domain, 
  r.model_version
FROM mimi_ws_1.cmspayment.ra_coefficients r
INNER JOIN preferred_records p
  ON r.model_domain = p.model_domain 
  AND r.model_version = p.model_version
  AND r.eff_last_date = p.latest_eff_last_date
ORDER BY r.model_domain, r.model_version, r.coefficient;
```   

`ra_eligible_cpt_hcpcs_2026.csv`
```sql
SELECT DISTINCT cpt_hcpcs_code
FROM mimi_ws_1.cmspayment.ra_eligible_cpt_hcpcs
WHERE is_included = 'yes' AND YEAR(mimi_src_file_date) = 2025;
```

`hcc_is_chronic.csv`
```sql
SELECT hcc, is_chronic, model_version, model_domain
FROM cmspayment.ra_report_to_congress
WHERE mimi_src_file_name = '2024riskadjustmentinma-rtc.pdf'
```

## 🧪 Testing

```bash
$ hatch shell
$ pip install -e .
$ pytest tests/*
```

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📞 Support

- **Documentation**: [https://hccinfhir.readthedocs.io](https://hccinfhir.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/yourusername/hccinfhir/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/hccinfhir/discussions)

---

**Made with ❤️ by the HCCInFHIR team**