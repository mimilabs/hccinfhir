"""
Regression tests for the multi-model age/sex diagnosis edits in ra_dx_edits.csv.

These edits are ported from the CMS SAS edit macros (V28I0ED3, V22I0ED4,
V24I0ED3, V21I0ED4). The edits differ across model versions, so the same
diagnosis can land on different CCs (or be invalidated) depending on the model.
See resources/sas_edit_macros/ for the source macros and builder.
"""
from hccinfhir.model_calculate import calculate_raf

COMMUNITY = dict(dual_elgbl_cd='00', orec='0')


def _hccs(dx, model, **kw):
    args = {**COMMUNITY, **kw}
    return set(calculate_raf([dx], model, **args).hcc_list)


def test_d66_sex_edit_targets_differ_by_model():
    # D66 (hemophilia) female -> different CC per model; male keeps base CC.
    assert _hccs('D66', 'CMS-HCC Model V22', age=70, sex='F') == {'48'}
    assert _hccs('D66', 'CMS-HCC Model V24', age=70, sex='F') == {'48'}
    assert _hccs('D66', 'CMS-HCC Model V28', age=70, sex='F') == {'112'}
    # Male: no sex edit fires -> base mapping
    assert _hccs('D66', 'CMS-HCC Model V22', age=70, sex='M') == {'46'}
    assert _hccs('D66', 'CMS-HCC Model V28', age=70, sex='M') == {'111'}


def test_j410_under18_invalid_v28_but_reassigned_v22():
    # J410 chronic bronchitis, age < 18: V28 invalidates; V22/V24 reassign to CC112.
    assert _hccs('J410', 'CMS-HCC Model V28', age=10, sex='M', orec='1', dual_elgbl_cd='00') == set()
    assert _hccs('J410', 'CMS-HCC Model V22', age=10, sex='M', orec='1', dual_elgbl_cd='00') == {'112'}
    # Adult: no age<18 edit -> base CC retained (differs by model numbering)
    assert _hccs('J410', 'CMS-HCC Model V28', age=70, sex='M') == {'280'}
    assert _hccs('J410', 'CMS-HCC Model V22', age=70, sex='M') == {'111'}


def test_f3481_bounded_range_v22():
    # F3481 valid only ages 6-18 in V22/V24/ESRD; invalid outside that range.
    assert _hccs('F3481', 'CMS-HCC Model V22', age=70, sex='M') == set()      # adult -> invalid
    assert _hccs('F3481', 'CMS-HCC Model V22', age=12, sex='M', orec='1') == {'58'}  # in range -> mapped
    # F3481 is not a V28 diagnosis (no base mapping, no edit) -> empty at any age
    assert _hccs('F3481', 'CMS-HCC Model V28', age=12, sex='M', orec='1') == set()
    assert _hccs('F3481', 'CMS-HCC Model V28', age=70, sex='M') == set()


def test_breast_cancer_age_split_v28_only():
    # C50011 age < 50 -> CC22 (V28 override); age >= 50 -> base CC23.
    assert _hccs('C50011', 'CMS-HCC Model V28', age=40, sex='F') == {'22'}
    assert _hccs('C50011', 'CMS-HCC Model V28', age=60, sex='F') == {'23'}


def _hccs_sw(dx, model, switch_edits, **kw):
    args = {**COMMUNITY, **kw}
    return set(calculate_raf([dx], model, switch_edits=switch_edits, **args).hcc_list)


def test_mce_age_edit_gated_by_switch_edits():
    # C9150 (leukemia) is MCE-valid only age >= 15.
    # Default (switch_edits=True): invalidated below 15; kept at/above 15.
    assert _hccs('C9150', 'CMS-HCC Model V28', age=10, sex='M', orec='1') == set()
    assert _hccs('C9150', 'CMS-HCC Model V28', age=40, sex='M', orec='1') == {'19'}
    # switch_edits=False disables MCE -> code retained even below 15.
    assert _hccs_sw('C9150', 'CMS-HCC Model V28', False, age=10, sex='M', orec='1') == {'19'}


def test_mce_bounded_range():
    # C58 is MCE-valid only 9 <= age <= 64; invalid outside that range.
    assert _hccs('C58', 'CMS-HCC Model V28', age=40, sex='M', orec='1') == {'22'}   # in range
    assert _hccs('C58', 'CMS-HCC Model V28', age=70, sex='M', orec='1') == set()    # > 64
    assert _hccs('C58', 'CMS-HCC Model V28', age=5,  sex='M', orec='1') == set()    # < 9
    assert _hccs_sw('C58', 'CMS-HCC Model V28', False, age=70, sex='M', orec='1') == {'22'}
