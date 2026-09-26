import pytest
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.datamodels import Demographics

def test_basic_v6_categorization():
    """Test basic V6 (ACA) categorization"""
    result = categorize_demographics(35, 'M', version='V6')
    assert isinstance(result, Demographics)
    assert result.category == 'MAGE_LAST_35_39'
    assert result.version == 'V6'
    assert result.non_aged is True
    assert result.disabled is False
    assert result.orig_disabled is False

def test_basic_v2_categorization():
    """Test basic V2 (Medicare) categorization"""
    result = categorize_demographics(75, 'F', orec='0', version='V2')
    assert result.category == 'F75_79'
    assert result.version == 'V2'
    assert result.non_aged is False
    assert result.disabled is False
    assert result.orig_disabled is False

def test_input_validation():
    """Test input validation"""
    with pytest.raises(ValueError, match="Age must be a number"):
        categorize_demographics("35", 'M', version='V6')
    
    with pytest.raises(ValueError, match="Age must be non-negative"):
        categorize_demographics(-5, 'M', version='V6')
    
    with pytest.raises(ValueError, match="Sex must be"):
        categorize_demographics(35, 'X', version='V6')
    
    with pytest.raises(ValueError, match="Version must be"):
        categorize_demographics(35, 'M', version='V3')
    

def test_sex_normalization():
    """Test that different sex formats are normalized correctly"""
    v6_male = categorize_demographics(35, 'M', version='V6')
    v6_male_num = categorize_demographics(35, '1', version='V6')
    assert v6_male.category == v6_male_num.category

    v6_female = categorize_demographics(35, 'F', version='V6')
    v6_female_num = categorize_demographics(35, '2', version='V6')
    assert v6_female.category == v6_female_num.category

def test_disability_flags():
    """Test disability and original disability flags"""
    # Currently disabled
    result = categorize_demographics(45, 'M', orec='1', version='V2')
    assert result.disabled is True
    assert result.orig_disabled is False

    # Originally disabled, now aged
    result = categorize_demographics(70, 'M', orec='1', version='V2')
    assert result.disabled is False
    assert result.orig_disabled is True

    # Neither disabled
    result = categorize_demographics(70, 'M', orec='0', version='V2')
    assert result.disabled is False
    assert result.orig_disabled is False

def test_age_boundaries():
    """Test edge cases for age ranges"""
    # Test V6 boundaries
    assert categorize_demographics(0, 'M', version='V6').category == 'MAGE_LAST_0_0'
    assert categorize_demographics(1, 'M', version='V6').category == 'MAGE_LAST_1_1'
    assert categorize_demographics(60, 'M', version='V6').category == 'MAGE_LAST_60_GT'
    assert categorize_demographics(99, 'M', version='V6').category == 'MAGE_LAST_60_GT'

    # Test V2 boundaries
    assert categorize_demographics(0, 'M', orec='0', version='V2').category == 'M0_34'
    assert categorize_demographics(0, 'F', orec='2', version='V2').category == 'F0_34'  # ESRD infant
    assert categorize_demographics(34, 'M', orec='0', version='V2').category == 'M0_34'
    assert categorize_demographics(35, 'M', orec='0', version='V2').category == 'M35_44'
    assert categorize_demographics(95, 'M', orec='0', version='V2').category == 'M95_GT'

def test_dual_eligibility_flags():
    """Test dual eligibility categorization"""
    # Full benefit dual
    result = categorize_demographics(65, 'M', dual_elgbl_cd='02', orec='0')
    assert result.fbd is True
    assert result.pbd is False

    # Partial benefit dual
    result = categorize_demographics(65, 'M', dual_elgbl_cd='01', orec='0')
    assert result.fbd is False
    assert result.pbd is True

    # Non-dual
    result = categorize_demographics(65, 'M', dual_elgbl_cd='00', orec='0')
    assert result.fbd is False
    assert result.pbd is False

def test_esrd_flags():
    """Test ESRD (End Stage Renal Disease) detection"""

    # Test with null OREC/CREC
    result = categorize_demographics(65, 'M', version='V6')
    assert result.esrd is False

    # Test with null CREC only
    result = categorize_demographics(65, 'M', orec='0')
    assert result.esrd is False

    # Test with null OREC only 
    result = categorize_demographics(65, 'M', crec='0', version='V6')
    assert result.esrd is False
    # ESRD from OREC
    result = categorize_demographics(65, 'M', orec='2')
    assert result.esrd is True

    # ESRD from CREC
    result = categorize_demographics(65, 'M', orec='0', crec='2')
    assert result.esrd is True

    # No ESRD
    result = categorize_demographics(65, 'M', orec='0', crec='0')
    assert result.esrd is False

def test_additional_flags():
    """Test new enrollee and SNP flags"""
    result = categorize_demographics(65.1, 'M', orec='0', new_enrollee=True, snp=True)
    assert result.new_enrollee is True
    assert result.snp is True

    result = categorize_demographics(65, 'M', orec='0')
    assert result.new_enrollee is False
    assert result.snp is False 