# tests/test_model_interactions.py

import pytest
from hccinfhir.model_interactions import (
    has_any_hcc,
    create_demographic_interactions,
    create_dual_interactions,
    create_hcc_counts,
    get_diagnostic_categories,
    create_disease_interactions,
    apply_interactions
)
from hccinfhir.datamodels import Demographics    

@pytest.fixture
def sample_demographics():
    return Demographics(
        age=65,
        sex='F',
        category="F65",
        disabled=False,
        orig_disabled=False,
        non_aged=False,
        fbd=True,
        pbd=False,
        lti=False
    )

def test_has_any_hcc():
    hcc_list = ['17', '18', '19']
    hcc_set = {'18', '20', '21'}
    assert has_any_hcc(hcc_list, hcc_set) == 1
    
    hcc_set = {'20', '21', '22'}
    assert has_any_hcc(hcc_list, hcc_set) == 0

def test_create_demographic_interactions(sample_demographics):
    interactions = create_demographic_interactions(sample_demographics)
    
    assert 'OriginallyDisabled_Female' not in interactions
    assert 'OriginallyDisabled_Male' not in interactions
    assert 'LTI_Aged' not in interactions
    assert 'LTI_NonAged' not in interactions

def test_create_dual_interactions(sample_demographics):
    interactions = create_dual_interactions(sample_demographics)
    
    assert interactions['FBDual_Female_Aged'] == 1
    assert interactions['FBDual_Female_NonAged'] == 0
    assert interactions['FBDual_Male_Aged'] == 0
    assert interactions['FBDual_Male_NonAged'] == 0
    
    # PBDual interactions should not exist since pbd=False
    assert 'PBDual_Female_Aged' not in interactions

def test_create_hcc_counts():
    hcc_set = {'17', '18', '19'}
    counts = create_hcc_counts(hcc_set)
    
    assert counts['D3'] == 1
    assert 'D2' not in counts
    assert 'D10P' not in counts

def test_get_diagnostic_categories():
    hcc_set = {'17', '18', '19', '85'}
    cats = get_diagnostic_categories("CMS-HCC Model V24", hcc_set)
    
    assert cats['DIABETES'] == 1
    assert cats['CHF'] == 1
    assert cats['CANCER'] == 0

def test_create_disease_interactions():
    hcc_set = {'17', '85'}
    demographics = Demographics(
        age=65,
        sex='F',
        category="F65",
        disabled=True,
        orig_disabled=False,
        non_aged=False,
        fbd=False,
        pbd=False,
        lti=False
    )
    
    diagnostic_cats = get_diagnostic_categories("CMS-HCC Model V24", hcc_set)
    
    interactions = create_disease_interactions(
        "CMS-HCC Model V24",
        diagnostic_cats,
        demographics,
        hcc_set
    )
    
    assert interactions['DISABLED_HCC85'] == 1
    assert interactions['DIABETES_CHF'] == 1

def test_apply_interactions():
    demographics = Demographics(
        age=65,
        sex='F',
        category="F65",
        disabled=False,
        orig_disabled=False,
        non_aged=False,
        fbd=True,
        pbd=False,
        lti=False
    )
    hcc_set = {'17', '18', '85'}
    
    interactions = apply_interactions(demographics, hcc_set, "CMS-HCC Model V24")
    
    assert interactions['FBDual_Female_Aged'] == 1
    assert interactions['D3'] == 1
    assert 'DIABETES_CHF' in interactions

def test_empty_hcc_set():
    demographics = Demographics(
        age=65,
        sex='F',
        category="F65",
        disabled=False,
        orig_disabled=False,
        non_aged=False,
        fbd=True,
        pbd=False,
        lti=False
    )
    hcc_set = set()
    
    interactions = apply_interactions(demographics, hcc_set)
    
    assert all(count == 0 for name, count in interactions.items() if name.startswith('D'))
