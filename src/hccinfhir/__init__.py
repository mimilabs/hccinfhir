"""
HCCInFHIR - HCC Algorithm for FHIR Resources

A Python library for processing FHIR EOB resources and calculating HCC risk scores.
"""

# Main classes
from .hccinfhir import HCCInFHIR
from .extractor import extract_sld, extract_sld_list
from .filter import apply_filter
from .model_calculate import calculate_raf
from .datamodels import (
    Demographics, ServiceLevelData, RAFResult, ModelName, HCCDetail,
    PaymentData, PaymentDetail, RemittanceEntry
)
from .extractor_820 import extract_payment_820

# Sample data functions
from .samples import (
    SampleData,
    get_eob_sample,
    get_eob_sample_list,
    get_837_sample,
    get_837_sample_list,
    get_834_sample,
    get_820_sample,
    list_available_samples
)

__version__ = "0.3.1"
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
    "HCCDetail",

    # 820 payment parser
    "extract_payment_820",
    "PaymentData",
    "PaymentDetail",
    "RemittanceEntry",

    # Sample data
    "SampleData",
    "get_eob_sample",
    "get_eob_sample_list",
    "get_837_sample",
    "get_837_sample_list",
    "get_834_sample",
    "get_820_sample",
    "list_available_samples"
]