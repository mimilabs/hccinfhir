"""
Central location for all default data file loading.

This module loads all default data files at import time and provides them
to the public API functions (calculate_raf) and tests. Internal model_*
modules should not load their own defaults - they should receive data
as explicit parameters.

Default files are for the 2026 model year.
"""
from typing import Dict, Set, Tuple
from hccinfhir.datamodels import ModelName
from hccinfhir.utils import (
    load_dx_to_cc_mapping,
    load_hierarchies,
    load_is_chronic,
    load_coefficients,
    load_proc_filtering,
    load_labels
)

# Load all default data files once at module import time
# These are used by:
# - calculate_raf() function for direct usage
# - HCCInFHIR class (though it can override with custom files)
# - Tests that need default data

dx_to_cc_default: Dict[Tuple[str, ModelName], Set[str]] = load_dx_to_cc_mapping('ra_dx_to_cc_2026.csv')
hierarchies_default: Dict[Tuple[str, ModelName], Set[str]] = load_hierarchies('ra_hierarchies_2026.csv')
is_chronic_default: Dict[Tuple[str, ModelName], bool] = load_is_chronic('hcc_is_chronic.csv')
coefficients_default: Dict[Tuple[str, ModelName], float] = load_coefficients('ra_coefficients_2026.csv')
proc_filtering_default: Set[str] = load_proc_filtering('ra_eligible_cpt_hcpcs_2026.csv')
labels_default: Dict[Tuple[str, ModelName], str] = load_labels('ra_labels_2026.csv')
