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
3. **Direct diagnosis codes** - for quick calculations
4. **Service-level data** - standardized internal format

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
from hccinfhir import get_eob_sample, get_837_sample

# Get FHIR EOB sample
eob = get_eob_sample("sample_01")  # Individual sample
eob_list = get_eob_sample("sample_200")  # 200-record dataset

# Get X12 837 sample
x12_text = get_837_sample("sample_01")  # Professional claim
x12_text = get_837_sample("sample_inst_01")  # Institutional claim

# Process sample data
processor = HCCInFHIR()
demographics = Demographics(age=67, sex="F")
result = processor.run([eob], demographics)
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
eob_list = get_eob_sample("sample_200")
demographics = Demographics(age=67, sex="F", dual_elgbl_cd="N")

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