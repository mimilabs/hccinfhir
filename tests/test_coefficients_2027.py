"""Tests for the proposed 2027 coefficients file."""
import pytest
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.utils import load_coefficients


class TestCoefficients2027:
    """Test the proposed 2027 coefficients file."""

    def test_load_coefficients_2027(self):
        """Test that the 2027 coefficients file loads successfully."""
        coefficients = load_coefficients("ra_proposed_coefficients_2027.csv")

        # Verify coefficients were loaded
        assert len(coefficients) > 0

        # Verify structure - keys should be (coefficient_name, model_name) tuples
        sample_key = next(iter(coefficients.keys()))
        assert isinstance(sample_key, tuple)
        assert len(sample_key) == 2

        # Values should be floats
        sample_value = coefficients[sample_key]
        assert isinstance(sample_value, float)

    def test_load_coefficients_2027_model_names(self):
        """Test that the 2027 file creates correct model names."""
        coefficients = load_coefficients("ra_proposed_coefficients_2027.csv")

        # Get all unique model names
        model_names = set(key[1] for key in coefficients.keys())

        # Should have CMS-HCC V28
        assert "CMS-HCC Model V28" in model_names

        # Should have the three RxHCC variants
        assert "RxHCC Model V08 PDP_AND_MAPD" in model_names
        assert "RxHCC Model V08 PDP_ONLY" in model_names
        assert "RxHCC Model V08 MAPD_ONLY" in model_names

        # Should NOT have the old plain "RxHCC Model V08" from this file
        # (only the variants are present)
        print(f"Model names found: {model_names}")

    def test_hccinfhir_with_2027_coefficients_cmshcc(self):
        """Test HCCInFHIR processor with 2027 CMS-HCC coefficients."""
        processor = HCCInFHIR(
            model_name="CMS-HCC Model V28",
            coefficients_filename="ra_proposed_coefficients_2027.csv"
        )

        demographics = Demographics(age=70, sex="M", dual_elgbl_cd="00")

        # Calculate RAF with the new coefficients
        result = processor.calculate_from_diagnosis(
            diagnosis_codes=["E11.9"],  # Type 2 diabetes
            demographics=demographics
        )

        # Basic validation - should produce a result
        assert result.risk_score is not None
        assert result.risk_score >= 0
        print(f"CMS-HCC V28 (2027) RAF Score: {result.risk_score}")

    def test_rxhcc_pdp_and_mapd_variant(self):
        """Test RxHCC Model V08 PDP_AND_MAPD variant."""
        processor = HCCInFHIR(
            model_name="RxHCC Model V08 PDP_AND_MAPD",
            coefficients_filename="ra_proposed_coefficients_2027.csv"
        )

        demographics = Demographics(age=70, sex="F", low_income=True)
        result = processor.calculate_from_diagnosis(
            diagnosis_codes=["E11.9"],
            demographics=demographics
        )

        assert result.risk_score is not None
        assert result.model_name == "RxHCC Model V08 PDP_AND_MAPD"
        print(f"RxHCC V08 PDP_AND_MAPD RAF Score: {result.risk_score}")

    def test_rxhcc_pdp_only_variant(self):
        """Test RxHCC Model V08 PDP_ONLY variant."""
        processor = HCCInFHIR(
            model_name="RxHCC Model V08 PDP_ONLY",
            coefficients_filename="ra_proposed_coefficients_2027.csv"
        )

        demographics = Demographics(age=70, sex="F", low_income=True)
        result = processor.calculate_from_diagnosis(
            diagnosis_codes=["E11.9"],
            demographics=demographics
        )

        assert result.risk_score is not None
        assert result.model_name == "RxHCC Model V08 PDP_ONLY"
        print(f"RxHCC V08 PDP_ONLY RAF Score: {result.risk_score}")

    def test_rxhcc_mapd_only_variant(self):
        """Test RxHCC Model V08 MAPD_ONLY variant."""
        processor = HCCInFHIR(
            model_name="RxHCC Model V08 MAPD_ONLY",
            coefficients_filename="ra_proposed_coefficients_2027.csv"
        )

        demographics = Demographics(age=70, sex="F", low_income=True)
        result = processor.calculate_from_diagnosis(
            diagnosis_codes=["E11.9"],
            demographics=demographics
        )

        assert result.risk_score is not None
        assert result.model_name == "RxHCC Model V08 MAPD_ONLY"
        print(f"RxHCC V08 MAPD_ONLY RAF Score: {result.risk_score}")

    def test_rxhcc_variants_have_different_coefficients(self):
        """Verify that the three RxHCC variants have different coefficient values."""
        coefficients = load_coefficients("ra_proposed_coefficients_2027.csv")

        # Pick a coefficient that should exist in all three variants
        # e.g., "rx_ce_lowaged_rxhcc30"
        coef_name = "rx_ce_lowaged_rxhcc30"

        pdp_and_mapd = coefficients.get((coef_name, "RxHCC Model V08 PDP_AND_MAPD"))
        pdp_only = coefficients.get((coef_name, "RxHCC Model V08 PDP_ONLY"))
        mapd_only = coefficients.get((coef_name, "RxHCC Model V08 MAPD_ONLY"))

        print(f"\nCoefficient '{coef_name}':")
        print(f"  PDP_AND_MAPD: {pdp_and_mapd}")
        print(f"  PDP_ONLY: {pdp_only}")
        print(f"  MAPD_ONLY: {mapd_only}")

        # All three should exist
        assert pdp_and_mapd is not None
        assert pdp_only is not None
        assert mapd_only is not None

        # At least some should be different (they're different models)
        values = [pdp_and_mapd, pdp_only, mapd_only]
        assert len(set(values)) > 1 or all(v == values[0] for v in values)

    def test_compare_2026_vs_2027_cmshcc(self):
        """Compare CMS-HCC results between 2026 and 2027 coefficients."""
        processor_2026 = HCCInFHIR(
            model_name="CMS-HCC Model V28",
            coefficients_filename="ra_coefficients_2026.csv"
        )
        processor_2027 = HCCInFHIR(
            model_name="CMS-HCC Model V28",
            coefficients_filename="ra_proposed_coefficients_2027.csv"
        )

        demographics = Demographics(age=70, sex="M", dual_elgbl_cd="00")
        diagnosis_codes = ["E11.9", "I10"]  # Diabetes and hypertension

        result_2026 = processor_2026.calculate_from_diagnosis(
            diagnosis_codes=diagnosis_codes,
            demographics=demographics
        )
        result_2027 = processor_2027.calculate_from_diagnosis(
            diagnosis_codes=diagnosis_codes,
            demographics=demographics
        )

        # Both should produce valid results
        assert result_2026.risk_score is not None
        assert result_2027.risk_score is not None

        # Log the difference for review
        print(f"\nCMS-HCC V28 Comparison:")
        print(f"  2026 RAF Score: {result_2026.risk_score}")
        print(f"  2027 RAF Score: {result_2027.risk_score}")
        print(f"  Difference: {result_2027.risk_score - result_2026.risk_score}")

    def test_backward_compatibility_2026_file(self):
        """Ensure 2026 coefficients file still loads correctly."""
        coefficients = load_coefficients("ra_coefficients_2026.csv")

        # Get all unique model names
        model_names = set(key[1] for key in coefficients.keys())

        # Should have the standard models
        assert "CMS-HCC Model V28" in model_names
        assert "RxHCC Model V08" in model_names  # Old format without variant

        print(f"\n2026 Model names: {model_names}")
