import pytest
from hccinfhir.model_calculate import calculate_raf

def test_basic_cms_hcc_calculation():
    diagnosis_codes = ['E119', 'I509']  # Diabetes without complications, Heart failure
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V24",
        age=67,
        sex='F'
    )
    assert isinstance(result.risk_score, float)
    assert result.risk_score > 0


def test_cms_hcc_with_interactions():
    diagnosis_codes = ['E1169', 'I509', 'J449']  # Diabetes with complications, Heart failure, COPD
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V24",
        age=72,
        sex='M'
    )
    assert isinstance(result.risk_score, float)
    assert len(result.coefficients) > 3  # Should have HCCs plus interactions

def test_cms_hcc_with_demographics():
    diagnosis_codes = ['C509']  # Breast cancer
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V24", 
        age=85,
        sex='F',
        dual_elgbl_cd='02',  # Full dual
        orec='1'  # Originally disabled
    )
    assert isinstance(result.risk_score, float)
    assert result.risk_score > 0

def test_cms_hcc_empty_dx():
    result = calculate_raf(
        diagnosis_codes=[],
        model_name="CMS-HCC Model V24",
        age=67,
        sex='M'
    )
    print(result)
    assert isinstance(result.risk_score, float)
    assert len(result.coefficients) > 0  # Should still have demographic factors

def test_cms_hcc_invalid_dx():
    result = calculate_raf(
        diagnosis_codes=['INVALID123'],
        model_name="CMS-HCC Model V24",
        age=70,
        sex='F'
    )
    print(result)
    assert isinstance(result.risk_score, float)
    assert len(result.coefficients) > 0  # Should still have demographic factors

def test_cms_hcc_chronic_dx():
    result = calculate_raf(
        diagnosis_codes=['C509', 'E119', 'F319', 'A419'],
        model_name="CMS-HCC Model V24",
        age=85,
        sex='F'
    )
    assert result.risk_score_chronic_only > 0
    assert result.risk_score_hcc - result.risk_score_chronic_only > 0
    result = calculate_raf(
        diagnosis_codes=['C509', 'E119', 'F319', 'A419'],
        model_name="CMS-HCC Model V28",
        age=85,
        sex='F'
    )
    assert result.risk_score_chronic_only > 0
    assert result.risk_score_hcc - result.risk_score_chronic_only > 0

def test_cms_hcc_new_enrollee():
    result = calculate_raf(
        diagnosis_codes=['E119'],
        model_name="CMS-HCC Model V24",
        age=65,
        sex='F',
        new_enrollee=True
    )
    assert isinstance(result.risk_score, float)
    assert len(result.coefficients) > 0

def test_cms_hcc_disabled():
    result = calculate_raf(
        diagnosis_codes=['F319', 'F200'],  # Bipolar disorder, Schizophrenia
        model_name="CMS-HCC Model V24",
        age=45,
        sex='M',
        orec='1'
    )
    assert isinstance(result.risk_score, float)
    assert result.risk_score > 0

def test_cms_hcc_institutional():
    result = calculate_raf(
        diagnosis_codes=['G309', 'L89159'],  # Alzheimer's, Pressure ulcer
        model_name="CMS-HCC Model V24",
        age=82,
        sex='F',
        crec='1'  # Institutional
    )
    assert isinstance(result.risk_score, float)
    assert result.risk_score > 0

def test_cms_hcc_snp():
    result = calculate_raf(
        diagnosis_codes=['E1169', 'I509'],
        model_name="CMS-HCC Model V24",
        age=72,
        sex='F',
        snp=True,
        low_income=True
    )
    assert isinstance(result.risk_score, float)
    assert result.risk_score > 0

def test_hf_hcc238_v28():  # Test for heart failure and specified heart arrhythmias interaction in V28
    diagnosis_codes = ['I509', 'I4891']  # Heart failure, Atrial fibrillation
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V28",
        age=70,
        sex='M',
    )
    assert isinstance(result.risk_score, float)
    assert result.coefficients['HF_HCC238_V28'] > 0  # Interaction should be present and have coefficient
    diagnosis_codes = ['I509', 'E119']  # Heart failure, Diabetes without complications
    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name="CMS-HCC Model V28",
        age=70,
        sex='M',
    )
    assert isinstance(result.risk_score, float)
    assert 'HF_HCC238_V28' not in result.interactions # No interaction should be 