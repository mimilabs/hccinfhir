"""
HCCInFHIR - HCC Algorithm for FHIR Resources

A Python library for processing FHIR EOB resources and calculating HCC risk scores.
"""

# Main classes
from .hccinfhir import HCCInFHIR
from .extractor import extract_sld, extract_sld_list
from .filter import apply_filter
from .model_calculate import calculate_raf
from .datamodels import Demographics, ServiceLevelData, RAFResult, ModelName

# Sample data functions
from .samples import (
    SampleData,
    get_eob_sample,
    get_eob_sample_list,
    get_837_sample,
    get_837_sample_list,
    list_available_samples
)

__version__ = "0.1.5"
__author__ = "Yubin Park"
__email__ = "yubin.park@mimilabs.ai"

__all__ = [
    # Main classes
    "HCCInFHIR",
    "extract_sld",
    "extract_sld_list", 
    "apply_filter",
    "calculate_raf",
    "Demographics",
    "ServiceLevelData",
    "RAFResult",
    "ModelName",
    
    # Sample data
    "SampleData",
    "get_eob_sample",
    "get_eob_sample_list",
    "get_837_sample",
    "get_837_sample_list",
    "list_available_samples"
]