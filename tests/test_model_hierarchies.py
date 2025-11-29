import pytest
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.defaults import hierarchies_default

def test_basic_hierarchy():
    """Test basic parent-child hierarchy removal"""
    # Example: Diabetes hierarchy where 17 > 18 > 19
    test_hierarchies = {
        ("17", "CMS-HCC Model V28"): {"18", "19"},
        ("18", "CMS-HCC Model V28"): {"19"}
    }

    # Test parent removes children
    cc_set = {"17", "18", "19"}
    result = apply_hierarchies(cc_set, "CMS-HCC Model V28", test_hierarchies)
    assert result == {"17"}

    # Test middle hierarchy
    cc_set = {"18", "19"}
    result = apply_hierarchies(cc_set, "CMS-HCC Model V28", test_hierarchies)
    assert result == {"18"}

def test_v28_special_rules():
    """Test V28-specific rules like CC 223 removal"""
    cc_set = {"223"}
    result = apply_hierarchies(cc_set, "CMS-HCC Model V28", {})
    assert "223" not in result

    # 223 should remain when other specified CCs exist
    cc_set = {"221", "223"}
    result = apply_hierarchies(cc_set, "CMS-HCC Model V28", {})
    assert "221" in result

def test_esrd_models():
    """Test ESRD model-specific rules"""
    # Test V21
    cc_set = {"134", "135"}
    result = apply_hierarchies(cc_set, "CMS-HCC ESRD Model V21", {})
    assert "134" not in result
    assert "135" in result

    # Test V24
    cc_set = {"134", "135", "136", "137"}
    result = apply_hierarchies(cc_set, "CMS-HCC ESRD Model V24", {})
    assert not {"134", "135", "136", "137"} & result

def test_multiple_hierarchies():
    """Test multiple hierarchies applied correctly"""
    test_hierarchies = {
        ("17", "CMS-HCC Model V28"): {"18", "19"},
        ("130", "CMS-HCC Model V28"): {"131", "132"}
    }

    cc_set = {"17", "18", "19", "130", "131", "132"}
    result = apply_hierarchies(cc_set, "CMS-HCC Model V28", test_hierarchies)
    assert result == {"17", "130"}

def test_input_immutability():
    """Test that input set is not modified"""
    test_hierarchies = {
        ("17", "CMS-HCC Model V28"): {"18", "19"}
    }

    cc_set = {"17", "18", "19"}
    original = cc_set.copy()
    _ = apply_hierarchies(cc_set, "CMS-HCC Model V28", test_hierarchies)
    assert cc_set == original

def test_empty_inputs():
    """Test edge cases with empty inputs"""
    assert apply_hierarchies(set(), "CMS-HCC Model V28", {}) == set()
    assert apply_hierarchies({"17"}, "CMS-HCC Model V28", {}) == {"17"}

def test_invalid_model():
    """Test behavior with invalid model version"""
    cc_set = {"17", "18"}
    result = apply_hierarchies(cc_set, "INVALID_MODEL", {})
    # Should still apply default hierarchies but no special rules
    assert "17" in result 