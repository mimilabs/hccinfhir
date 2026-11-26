import pytest

from hccinfhir import Demographics, HCCInFHIR, LeadConcurrentInputs, calculate_raf
from hccinfhir.constants import LEAD_CONCURRENT_MODEL, LEAD_PROSPECTIVE_MODEL
from hccinfhir.constants import MODEL_ALIASES, normalize_model_name
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
    assert sum(model == LEAD_CONCURRENT_MODEL for _, model in coefficients_default) == 165
    assert sum(model == LEAD_PROSPECTIVE_MODEL for _, model in coefficients_default) == 801
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


@pytest.mark.parametrize(
    "age,dual,orec,expected",
    [
        (72, "00", "0", 0.6459),  # CNA
        (60, "00", "1", 0.4454),  # CND
        (72, "02", "0", 0.6809),  # CFA
        (60, "02", "1", 0.5663),  # CFD
        (72, "01", "0", 0.4863),  # CPA
        (60, "01", "1", 0.4914),  # CPD
    ],
)
def test_lead_prospective_supports_all_six_community_segments(age, dual, orec, expected):
    result = HCCInFHIR(model_name="lead-p-v1").calculate_from_diagnosis(
        [], age=age, sex="M", dual_elgbl_cd=dual, orec=orec
    )
    assert result.risk_score == pytest.approx(expected)


def test_lead_prospective_excludes_hcc_count_variables():
    assert create_hcc_counts({"37", "224", "327"}, LEAD_PROSPECTIVE_MODEL) == {}


def test_lead_concurrent_applies_unsegmented_and_model_input_coefficients():
    processor = HCCInFHIR(model_name=LEAD_CONCURRENT_MODEL)
    result = processor.calculate_from_diagnosis(
        ["E11.9"],
        Demographics(age=70, sex="M"),
        model_inputs=LeadConcurrentInputs(
            high_needs_start="Q3",
            post_graft_4_9_month_fraction=0.5,
        ),
    )

    assert result.hcc_list == ["38"]
    assert result.coefficients["M70_74"] == pytest.approx(0.0537)
    assert result.coefficients["38"] == pytest.approx(0.0244)
    assert result.coefficients["HN_Q3"] == pytest.approx(0.3557)
    assert result.coefficients["GE65_PG49_FRAC"] == pytest.approx(0.2290 * 0.5)
    assert result.risk_score == pytest.approx(0.5483)
    assert result.model_inputs.high_needs_start == "Q3"


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


def test_model_inputs_reject_incompatible_model():
    processor = HCCInFHIR(model_name=LEAD_PROSPECTIVE_MODEL)
    with pytest.raises(ValueError, match="model_inputs are not supported"):
        processor.calculate_from_diagnosis(
            ["E11.9"],
            age=70,
            sex="M",
            model_inputs=LeadConcurrentInputs(high_needs_start="Q3"),
        )


def test_lead_fraction_inputs_are_validated():
    with pytest.raises(ValueError):
        LeadConcurrentInputs(post_graft_4_9_month_fraction=1.1)


@pytest.mark.parametrize(
    "period,expected",
    [("JAN1", 0.0552), ("Q2", 0.2506), ("Q3", 0.3557), ("Q4", 0.2511)],
)
def test_all_lead_high_needs_periods(period, expected):
    result = calculate_raf(
        [], model_name="lead-c-v2", age=70, sex="M",
        model_inputs=LeadConcurrentInputs(high_needs_start=period),
    )
    assert result.coefficients[f"HN_{period}"] == pytest.approx(expected)


@pytest.mark.parametrize("age,expected", [(60, 0.1737), (70, 0.2290)])
def test_lead_post_graft_fraction_uses_age_specific_coefficient(age, expected):
    result = calculate_raf(
        [], model_name="lead-c-v2", age=age, sex="M",
        model_inputs=LeadConcurrentInputs(post_graft_4_9_month_fraction=0.5),
    )
    age_prefix = "LT65" if age < 65 else "GE65"
    assert result.coefficients[f"{age_prefix}_PG49_FRAC"] == pytest.approx(expected * 0.5)


@pytest.mark.parametrize("method", ["run", "run_from_service_data"])
def test_model_inputs_propagate_through_public_collection_methods(method):
    processor = HCCInFHIR(model_name="lead-c-v2")
    result = getattr(processor, method)(
        [], Demographics(age=70, sex="M"),
        model_inputs=LeadConcurrentInputs(high_needs_start="Q2"),
    )
    assert result.coefficients["HN_Q2"] == pytest.approx(0.2506)
    assert result.model_inputs.high_needs_start == "Q2"


@pytest.mark.parametrize("alias,canonical", MODEL_ALIASES.items())
def test_model_aliases_normalize_to_canonical_names(alias, canonical):
    assert normalize_model_name(alias) == canonical


def test_lead_alias_is_accepted_end_to_end_and_result_is_canonical():
    processor = HCCInFHIR(model_name="lead-c-v2")
    result = processor.calculate_from_diagnosis(["E11.9"], age=70, sex="M")
    assert result.model_name == LEAD_CONCURRENT_MODEL


def test_invalid_model_alias_has_actionable_error():
    with pytest.raises(ValueError, match="Unsupported model_name"):
        HCCInFHIR(model_name="lead-v2")
