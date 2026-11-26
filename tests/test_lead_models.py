import pytest

from hccinfhir import Demographics, HCCInFHIR
from hccinfhir.constants import LEAD_CONCURRENT_MODEL, LEAD_PROSPECTIVE_MODEL
from hccinfhir.defaults import coefficients_default, hierarchies_default
from hccinfhir.model_interactions import create_hcc_counts


def _hierarchy_edges(model_name):
    return {
        (parent, child)
        for (parent, model), children in hierarchies_default.items()
        if model == model_name
        for child in children
    }


def test_lead_hierarchies_match_v28_exactly():
    v28_edges = _hierarchy_edges("CMS-HCC Model V28")
    assert len(v28_edges) == 149
    assert _hierarchy_edges(LEAD_CONCURRENT_MODEL) == v28_edges
    assert _hierarchy_edges(LEAD_PROSPECTIVE_MODEL) == v28_edges


def test_lead_coefficients_load_under_public_model_names():
    assert coefficients_default[("hcc38", LEAD_CONCURRENT_MODEL)] == pytest.approx(0.0244)
    assert coefficients_default[("cna_hcc38", LEAD_PROSPECTIVE_MODEL)] == pytest.approx(0.0)


def test_lead_prospective_uses_v28_mapping_and_segmented_coefficients():
    processor = HCCInFHIR(model_name=LEAD_PROSPECTIVE_MODEL)
    result = processor.calculate_from_diagnosis(
        ["E11.9"],
        Demographics(age=70, sex="M", dual_elgbl_cd="00"),
    )

    assert result.hcc_list == ["38"]
    assert result.risk_score == pytest.approx(0.6459)
    assert result.coefficients["M70_74"] == pytest.approx(0.6459)
    assert result.coefficients["38"] == pytest.approx(0.0)


def test_lead_concurrent_applies_unsegmented_and_model_input_coefficients():
    processor = HCCInFHIR(model_name=LEAD_CONCURRENT_MODEL)
    result = processor.calculate_from_diagnosis(
        ["E11.9"],
        Demographics(
            age=70,
            sex="M",
            lead_high_needs_start="Q3",
            lead_post_graft_4_9_month_fraction=0.5,
        ),
    )

    assert result.hcc_list == ["38"]
    assert result.coefficients["M70_74"] == pytest.approx(0.0537)
    assert result.coefficients["38"] == pytest.approx(0.0244)
    assert result.coefficients["HN_Q3"] == pytest.approx(0.3557)
    assert result.coefficients["GE65_PG49_FRAC"] == pytest.approx(0.2290 * 0.5)
    assert result.risk_score == pytest.approx(0.5483)


def test_lead_concurrent_age_interaction_and_hcc_count_bands():
    processor = HCCInFHIR(model_name=LEAD_CONCURRENT_MODEL)
    result = processor.calculate_from_diagnosis(["D57.00"], age=60, sex="F")

    assert result.hcc_list == ["107"]
    assert result.coefficients["HCC107_LT65"] == pytest.approx(0.3922)
    assert create_hcc_counts({str(i) for i in range(5)}, LEAD_CONCURRENT_MODEL) == {"D5": 1}
    assert create_hcc_counts({str(i) for i in range(15)}, LEAD_CONCURRENT_MODEL) == {"D15P": 1}


def test_lead_models_reuse_v28_age_and_sex_edits():
    processor = HCCInFHIR(model_name=LEAD_CONCURRENT_MODEL)
    result = processor.calculate_from_diagnosis(["D66"], age=70, sex="F")
    assert result.hcc_list == ["112"]
