"""Regression tests for RxHCC V08 and 2027 plan-specific variants."""

import pytest

from hccinfhir import Demographics, HCCInFHIR, calculate_raf
from hccinfhir.defaults import hierarchies_default, labels_default


RXHCC_2027_VARIANTS = [
    ("RxHCC Model V08 PDP_AND_MAPD", 0.329, 0.944, 2.755),
    ("RxHCC Model V08 PDP_ONLY", 0.442, 0.953, 0.965),
    ("RxHCC Model V08 MAPD_ONLY", 0.418, 0.852, 1.715),
]


class TestRxHCCV08:
    """Verify RxHCC V08 mapping, hierarchies, labels, and NonAged interactions."""

    def test_hierarchies_loaded_under_v08_model_name(self):
        assert ("30", "RxHCC Model V08") in hierarchies_default
        assert "31" in hierarchies_default[("30", "RxHCC Model V08")]

    def test_labels_loaded_under_v08_model_name_without_rxhcc_prefix(self):
        assert labels_default.get(("1", "RxHCC Model V08")) == "HIV/AIDS"
        assert labels_default.get(("30", "RxHCC Model V08")) is not None
        assert labels_default.get(("31", "RxHCC Model V08")) is not None

    def test_rxhcc_v08_applies_hierarchies_and_populates_labels(self):
        # E11.22 -> RxHCC 30 (parent), E11.9 -> RxHCC 31 (child of 30)
        result = calculate_raf(
            diagnosis_codes=["E11.22", "E11.9"],
            model_name="RxHCC Model V08",
            age=70,
            sex="F",
            low_income=True,
        )

        assert result.hcc_list == ["30"]
        assert "31" not in result.coefficients
        assert result.coefficients["30"] == pytest.approx(1.058)
        assert result.risk_score == pytest.approx(0.034 + 1.058)

        assert len(result.hcc_details) == 1
        assert result.hcc_details[0].hcc == "30"
        assert result.hcc_details[0].label is not None
        assert "Diabetes" in result.hcc_details[0].label

    @pytest.mark.parametrize(
        "model_name,coef_31,coef_30,_coef_nonaged_1", RXHCC_2027_VARIANTS
    )
    def test_rxhcc_2027_variants_map_diagnoses_and_apply_hierarchies(
        self, model_name, coef_31, coef_30, _coef_nonaged_1
    ):
        processor = HCCInFHIR(
            model_name=model_name,
            coefficients_filename="ra_proposed_coefficients_2027.csv",
        )
        demographics = Demographics(age=70, sex="F", low_income=True)

        single = processor.calculate_from_diagnosis(["E11.9"], demographics)
        assert single.hcc_list == ["31"]
        assert single.cc_to_dx == {"31": {"E119"}}
        assert single.coefficients["31"] == pytest.approx(coef_31)
        assert single.hcc_details[0].label is not None

        hierarchical = processor.calculate_from_diagnosis(
            ["E11.22", "E11.9"], demographics
        )
        assert hierarchical.hcc_list == ["30"]
        assert "31" not in hierarchical.coefficients
        assert hierarchical.coefficients["30"] == pytest.approx(coef_30)

    @pytest.mark.parametrize(
        "model_name,_coef_31,_coef_30,coef_nonaged_1", RXHCC_2027_VARIANTS
    )
    def test_rxhcc_2027_variants_apply_nonaged_interactions(
        self, model_name, _coef_31, _coef_30, coef_nonaged_1
    ):
        processor = HCCInFHIR(
            model_name=model_name,
            coefficients_filename="ra_proposed_coefficients_2027.csv",
        )
        demographics = Demographics(age=50, sex="F", lti=True, orec="1")
        result = processor.calculate_from_diagnosis(["B20"], demographics)

        assert result.hcc_list == ["1"]
        assert result.interactions.get("NonAged_RXHCC1") == 1
        assert result.coefficients["NonAged_RXHCC1"] == pytest.approx(coef_nonaged_1)
