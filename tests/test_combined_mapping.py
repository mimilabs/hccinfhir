import pytest
from hccinfhir.model_dx_to_cc import apply_mapping
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.utils import load_dx_to_cc_mapping, load_hierarchies


def test_diabetes_hierarchy_chain_with_custom_files():
    """Test complete chain from diagnosis codes to final hierarchical CCs for diabetes"""
    # Type 1 diabetes with complications maps to HCC 17
    # Type 2 diabetes with complications maps to HCC 18
    # Diabetes without complications maps to HCC 19
    diagnoses = [
        "E1100",  # type 2 diabetes mellitus with hyperosmolarity without nonketotic hyperglycemic-hyperosmolar coma (NKHHC)
        "E1022",  # Type 1 diabetes with kidney complications
        "E1165",  # Type 2 diabetes with circulatory complications
        "E119"    # Type 2 diabetes without complications
    ]
    dx_to_cc_mapping = load_dx_to_cc_mapping('ra_dx_to_cc_2025.csv')
    hierarchies = load_hierarchies('ra_hierarchies_2025.csv')
    # First map dx to CCs
    cc_to_dx = apply_mapping(diagnoses, 
                             model_name="CMS-HCC Model V24",
                             dx_to_cc_mapping=dx_to_cc_mapping)
    ccs = set(cc_to_dx.keys())

    # Then apply hierarchies
    final_ccs = apply_hierarchies(ccs, 
                                  model_name="CMS-HCC Model V24",
                                  hierarchies=hierarchies)

    # Should only keep the highest severity CC (17)
    assert final_ccs == {"17"}

    dx_to_cc_mapping = load_dx_to_cc_mapping('ra_dx_to_cc_2026.csv')
    hierarchies = load_hierarchies('ra_hierarchies_2026.csv')

    cc_to_dx = apply_mapping(diagnoses, 
                             model_name="CMS-HCC Model V28",
                             dx_to_cc_mapping=dx_to_cc_mapping)
    ccs = set(cc_to_dx.keys())
    final_ccs = apply_hierarchies(ccs, 
                                  model_name="CMS-HCC Model V28",
                                  hierarchies=hierarchies)
    assert final_ccs == {"36"}