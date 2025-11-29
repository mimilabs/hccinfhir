import pytest
from hccinfhir.model_dx_to_cc import get_cc, apply_mapping
from hccinfhir.defaults import dx_to_cc_default

# Test mapping dictionary with multiple CCs per diagnosis
TEST_DX_TO_CC = {
    ("E119", "CMS-HCC Model V28"): {"19", "20"},
    ("I5022", "CMS-HCC Model V28"): {"85"},
    ("E119", "CMS-HCC Model V24"): {"17"},  # Different model version
}

def test_get_cc():
    # Test successful mapping with multiple CCs
    assert get_cc("E119", "CMS-HCC Model V28", TEST_DX_TO_CC) == {"19", "20"}
    assert get_cc("E11.9", "CMS-HCC Model V28", TEST_DX_TO_CC) == None
    assert get_cc("I5022", "CMS-HCC Model V28", TEST_DX_TO_CC) == {"85"}

    # Test non-existent diagnosis code
    assert get_cc("Z99.99", "CMS-HCC Model V28", TEST_DX_TO_CC) is None

    # Test different model version
    assert get_cc("E119", "CMS-HCC Model V24", TEST_DX_TO_CC) == {"17"}

def test_apply_mapping():
    diagnoses = ["E11.9", "I50.22", "Z99.99"]
    expected = {
        "19": {"E119"},
        "20": {"E119"},
        "85": {"I5022"}
    }

    # Test successful mapping
    result = apply_mapping(diagnoses, "CMS-HCC Model V28", TEST_DX_TO_CC)
    assert result == expected

    # Test empty list
    assert apply_mapping([], "CMS-HCC Model V28", TEST_DX_TO_CC) == {}

    # Test list with no valid mappings
    assert apply_mapping(["Z99.99"], "CMS-HCC Model V28", TEST_DX_TO_CC) == {}

def test_default_mapping():
    """Test cases using the default dx_to_cc mapping"""
    # Test that common diabetes code maps correctly
    result = get_cc("E119", "CMS-HCC Model V28", dx_to_cc_default)
    assert isinstance(result, set)
    assert "38" in result

    # Test batch mapping with default dx_to_cc_mapping
    diagnoses = ["E103213", "I5022", "Z9999"]
    result = apply_mapping(diagnoses, "CMS-HCC Model V28", dx_to_cc_default)
    assert "37" in result  # Check CC exists as key
    assert "E103213" in result["37"]  # Check diagnosis exists in CC's list

    # Test different model version
    assert get_cc("E119", "CMS-HCC ESRD Model V21", dx_to_cc_default) is not None
    assert "19" in get_cc("E119", "CMS-HCC Model V24", dx_to_cc_default)
    
