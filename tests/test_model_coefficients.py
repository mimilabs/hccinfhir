import pytest
from hccinfhir.model_coefficients import get_coefficent_prefix, apply_coefficients
from hccinfhir.model_demographics import categorize_demographics

def test_get_coefficient_prefix_cms_hcc_community():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    prefix = get_coefficent_prefix(demographics)
    assert prefix == "CNA_"

def test_get_coefficient_prefix_esrd_dialysis():
    demographics = categorize_demographics(
        age=45,
        sex='M',
        dual_elgbl_cd='00',
        orec='2',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    prefix = get_coefficent_prefix(demographics, model_name="CMS-HCC ESRD Model V24")
    assert prefix == "DI_"

def test_apply_coefficients():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )
    
    hcc_set = {"19", "47", "85"}
    interactions = {
        "D1": 1,
        "D2": 0,  # Should be excluded from result
    }
    
    # Create test coefficients
    test_coefficients = {
        ("cna_hcc19", "CMS-HCC Model V28"): 0.421,
        ("cna_hcc47", "CMS-HCC Model V28"): 0.368,
        ("cna_hcc85", "CMS-HCC Model V28"): 0.323,
        ("cna_d1", "CMS-HCC Model V28"): 0.118,
        ("cna_d2", "CMS-HCC Model V28"): 0.245,
    }
    
    result = apply_coefficients(
        demographics=demographics,
        hcc_set=hcc_set,
        interactions=interactions,
        model_name="CMS-HCC Model V28",
        coefficients=test_coefficients
    )

    expected = {
        "19": 0.421,
        "47": 0.368,
        "85": 0.323,
        "D1": 0.118
    }
    
    assert result == expected

def test_apply_coefficients_empty():
    demographics = categorize_demographics(
        age=70,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',
        crec='0',
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )

    result = apply_coefficients(
        demographics=demographics,
        hcc_set=set(),
        interactions={},
        model_name="CMS-HCC Model V28",
        coefficients={("cna_f70_74", "CMS-HCC Model V28"): 0.395}  # Mock coefficient
    )

    assert result == {'F70_74': 0.395}

def test_prefix_override():
    """Test that prefix_override parameter correctly overrides auto-detected prefix"""
    # Create ESRD patient with incorrect orec/crec (should NOT auto-detect as ESRD)
    demographics = categorize_demographics(
        age=65,
        sex='F',
        dual_elgbl_cd='00',
        orec='0',  # Not ESRD according to orec
        crec='0',  # Not ESRD according to crec
        version='V2',
        new_enrollee=False,
        snp=False,
        low_income=False
    )

    # Verify patient is NOT auto-detected as ESRD
    assert demographics.esrd == False

    # Without override, should use community prefix
    prefix_auto = get_coefficent_prefix(demographics, model_name="CMS-HCC ESRD Model V24")
    # Since esrd=False, it won't enter the ESRD logic and falls through to default

    # Test override with ESRD dialysis prefix
    hcc_set = {"134", "135"}  # ESRD-related HCCs
    interactions = {}

    # Create test coefficients for both prefixes
    test_coefficients = {
        ("cna_hcc134", "CMS-HCC ESRD Model V24"): 0.5,  # Community prefix
        ("cna_hcc135", "CMS-HCC ESRD Model V24"): 0.6,
        ("di_hcc134", "CMS-HCC ESRD Model V24"): 1.2,   # Dialysis prefix
        ("di_hcc135", "CMS-HCC ESRD Model V24"): 1.3,
        ("cna_f65_69", "CMS-HCC ESRD Model V24"): 0.4,
        ("di_f65_69", "CMS-HCC ESRD Model V24"): 0.8,
    }

    # Test WITH override - should use DI_ prefix
    result_with_override = apply_coefficients(
        demographics=demographics,
        hcc_set=hcc_set,
        interactions=interactions,
        model_name="CMS-HCC ESRD Model V24",
        coefficients=test_coefficients,
        prefix_override='DI_'
    )

    # Should use dialysis coefficients
    assert result_with_override.get("134") == 1.2
    assert result_with_override.get("135") == 1.3
