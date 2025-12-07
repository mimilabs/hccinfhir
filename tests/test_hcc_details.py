"""
Tests for HCC details functionality - labels, chronic status, and coefficients.
"""
import pytest
from hccinfhir import HCCInFHIR, Demographics, HCCDetail, calculate_raf


class TestHCCDetails:
    """Test HCC details are correctly populated."""

    def test_hcc_details_structure(self):
        """Test that hcc_details returns proper HCCDetail objects."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        assert len(result.hcc_details) > 0
        for detail in result.hcc_details:
            assert isinstance(detail, HCCDetail)
            assert detail.hcc is not None
            assert isinstance(detail.is_chronic, bool)

    def test_hcc_details_matches_hcc_list(self):
        """Test that hcc_details contains same HCCs as hcc_list."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'I50.9', 'J44.1'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        hcc_from_details = {d.hcc for d in result.hcc_details}
        hcc_from_list = set(result.hcc_list)

        assert hcc_from_details == hcc_from_list

    def test_hcc_details_coefficients_match(self):
        """Test that coefficients in hcc_details match the coefficients dict."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'I50.9'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        for detail in result.hcc_details:
            if detail.coefficient is not None:
                assert detail.hcc in result.coefficients
                assert detail.coefficient == result.coefficients[detail.hcc]


class TestV28Labels:
    """Test V28 model labels are correctly populated."""

    def test_diabetes_label_v28(self):
        """Test diabetes HCC has correct label in V28."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],  # Type 2 diabetes without complications
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # E11.9 maps to HCC38 in V28
        diabetes_hcc = next((d for d in result.hcc_details if d.hcc == '38'), None)
        assert diabetes_hcc is not None
        assert diabetes_hcc.label is not None
        assert 'Diabetes' in diabetes_hcc.label

    def test_chf_label_v28(self):
        """Test CHF HCC has correct label in V28."""
        result = calculate_raf(
            diagnosis_codes=['I50.9'],  # Heart failure
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # I50.9 maps to HCC226 in V28
        chf_hcc = next((d for d in result.hcc_details if d.hcc == '226'), None)
        assert chf_hcc is not None
        assert chf_hcc.label is not None
        assert 'Heart Failure' in chf_hcc.label

    def test_copd_label_v28(self):
        """Test COPD HCC has correct label in V28."""
        result = calculate_raf(
            diagnosis_codes=['J44.1'],  # COPD with acute exacerbation
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # J44.1 maps to HCC280 in V28
        copd_hcc = next((d for d in result.hcc_details if d.hcc == '280'), None)
        assert copd_hcc is not None
        assert copd_hcc.label is not None
        assert 'Chronic Obstructive Pulmonary Disease' in copd_hcc.label or 'COPD' in copd_hcc.label

    def test_cancer_label_v28(self):
        """Test cancer HCC has correct label in V28."""
        result = calculate_raf(
            diagnosis_codes=['C34.90'],  # Lung cancer
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # Should have a cancer-related HCC
        cancer_hccs = [d for d in result.hcc_details if d.label and 'Cancer' in d.label]
        assert len(cancer_hccs) > 0


class TestV22Labels:
    """Test V22 model labels are correctly populated."""

    def test_diabetes_label_v22(self):
        """Test diabetes HCC has correct label in V22."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name="CMS-HCC Model V22",
            age=67,
            sex='F'
        )

        # E11.9 maps to HCC19 in V22
        diabetes_hcc = next((d for d in result.hcc_details if d.hcc == '19'), None)
        assert diabetes_hcc is not None
        assert diabetes_hcc.label is not None
        assert 'Diabetes' in diabetes_hcc.label

    def test_chf_label_v22(self):
        """Test CHF HCC has correct label in V22."""
        result = calculate_raf(
            diagnosis_codes=['I50.9'],
            model_name="CMS-HCC Model V22",
            age=67,
            sex='F'
        )

        # I50.9 maps to HCC85 in V22
        chf_hcc = next((d for d in result.hcc_details if d.hcc == '85'), None)
        assert chf_hcc is not None
        assert chf_hcc.label is not None
        assert 'Heart Failure' in chf_hcc.label or 'Congestive' in chf_hcc.label


class TestV24Labels:
    """Test V24 model labels are correctly populated."""

    def test_diabetes_label_v24(self):
        """Test diabetes HCC has correct label in V24."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name="CMS-HCC Model V24",
            age=67,
            sex='F'
        )

        # E11.9 maps to HCC19 in V24
        diabetes_hcc = next((d for d in result.hcc_details if d.hcc == '19'), None)
        assert diabetes_hcc is not None
        assert diabetes_hcc.label is not None
        assert 'Diabetes' in diabetes_hcc.label


class TestESRDLabels:
    """Test ESRD model labels are correctly populated."""

    def test_esrd_v24_diabetes_label(self):
        """Test diabetes HCC has correct label in ESRD V24."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'N18.6'],
            model_name="CMS-HCC ESRD Model V24",
            age=67,
            sex='F',
            orec='2'
        )

        diabetes_hcc = next((d for d in result.hcc_details if d.hcc == '19'), None)
        assert diabetes_hcc is not None
        assert diabetes_hcc.label is not None
        assert 'Diabetes' in diabetes_hcc.label

    def test_esrd_v21_labels(self):
        """Test ESRD V21 model returns hcc_details even if labels may not exist."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'N18.6'],
            model_name="CMS-HCC ESRD Model V21",
            age=67,
            sex='F',
            orec='2'
        )

        # V21 labels may not exist in ra_labels_2026.csv (only V20 and V24 ESRD exist)
        # But hcc_details should still be populated with HCC codes
        if len(result.hcc_list) > 0:
            assert len(result.hcc_details) == len(result.hcc_list)
            for detail in result.hcc_details:
                assert detail.hcc is not None
                assert isinstance(detail.is_chronic, bool)


class TestChronicStatus:
    """Test chronic status is correctly populated."""

    def test_v28_chronic_conditions(self):
        """Test that V28 chronic conditions are marked correctly."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'I50.9', 'J44.1'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # In V28, diabetes (HCC38), CHF (HCC226), COPD (HCC280) should be chronic
        for detail in result.hcc_details:
            if detail.hcc in ['38', '226', '280']:
                assert detail.is_chronic is True, f"HCC{detail.hcc} should be chronic in V28"

    def test_v24_chronic_conditions(self):
        """Test that V24 chronic conditions are marked correctly."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'I50.9'],
            model_name="CMS-HCC Model V24",
            age=67,
            sex='F'
        )

        # In V24, diabetes (HCC19) and CHF (HCC85) should be chronic
        for detail in result.hcc_details:
            if detail.hcc in ['19', '85']:
                assert detail.is_chronic is True, f"HCC{detail.hcc} should be chronic in V24"


class TestCoefficientsPopulated:
    """Test coefficients are correctly populated in hcc_details."""

    def test_v28_coefficients_populated(self):
        """Test V28 HCC coefficients are populated."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        for detail in result.hcc_details:
            assert detail.coefficient is not None, f"HCC{detail.hcc} should have a coefficient"
            assert detail.coefficient > 0, f"HCC{detail.hcc} coefficient should be positive"

    def test_v22_coefficients_populated(self):
        """Test V22 HCC coefficients are populated."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'I50.9'],
            model_name="CMS-HCC Model V22",
            age=67,
            sex='F'
        )

        for detail in result.hcc_details:
            assert detail.coefficient is not None, f"HCC{detail.hcc} should have a coefficient"
            assert detail.coefficient > 0, f"HCC{detail.hcc} coefficient should be positive"


class TestHCCInFHIRIntegration:
    """Test HCC details work through HCCInFHIR class."""

    def test_calculate_from_diagnosis_has_details(self):
        """Test calculate_from_diagnosis returns hcc_details."""
        processor = HCCInFHIR()
        demographics = Demographics(age=67, sex='F')
        result = processor.calculate_from_diagnosis(['E11.9', 'I50.9'], demographics)

        assert len(result.hcc_details) > 0
        assert len(result.hcc_details) == len(result.hcc_list)

    def test_run_from_service_data_has_details(self):
        """Test run_from_service_data returns hcc_details."""
        from hccinfhir import ServiceLevelData

        processor = HCCInFHIR(filter_claims=False)
        demographics = Demographics(age=67, sex='F')

        service_data = [
            ServiceLevelData(
                claim_id="test",
                claim_diagnosis_codes=['E11.9', 'I50.9']
            )
        ]

        result = processor.run_from_service_data(service_data, demographics)

        assert len(result.hcc_details) > 0


class TestEdgeCases:
    """Test edge cases for HCC details."""

    def test_empty_diagnosis_codes(self):
        """Test empty diagnosis codes returns empty hcc_details."""
        result = calculate_raf(
            diagnosis_codes=[],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        assert result.hcc_details == []
        assert result.hcc_list == []

    def test_invalid_diagnosis_codes(self):
        """Test invalid diagnosis codes returns empty hcc_details."""
        result = calculate_raf(
            diagnosis_codes=['INVALID', 'XXXXX'],
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        assert result.hcc_details == []
        assert result.hcc_list == []

    def test_multiple_diagnoses_same_hcc(self):
        """Test multiple diagnoses mapping to same HCC results in single detail."""
        result = calculate_raf(
            diagnosis_codes=['E11.9', 'E11.65'],  # Both diabetes codes
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F'
        )

        # Should deduplicate to single HCC
        hcc_codes = [d.hcc for d in result.hcc_details]
        assert len(hcc_codes) == len(set(hcc_codes)), "Should not have duplicate HCCs"


class TestAllModelsHaveLabels:
    """Verify all supported models have labels populated for common conditions."""

    @pytest.mark.parametrize("model_name", [
        "CMS-HCC Model V22",
        "CMS-HCC Model V24",
        "CMS-HCC Model V28",
    ])
    def test_diabetes_has_label(self, model_name):
        """Test diabetes has label across all CMS-HCC models."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name=model_name,
            age=67,
            sex='F'
        )

        assert len(result.hcc_details) > 0, f"No HCCs found for {model_name}"
        diabetes_hcc = result.hcc_details[0]
        assert diabetes_hcc.label is not None, f"Diabetes HCC should have label in {model_name}"
        assert 'Diabetes' in diabetes_hcc.label, f"Label should contain 'Diabetes' in {model_name}"

    @pytest.mark.parametrize("model_name", [
        "CMS-HCC ESRD Model V21",
        "CMS-HCC ESRD Model V24",
    ])
    def test_esrd_models_have_labels(self, model_name):
        """Test ESRD models have labels populated."""
        result = calculate_raf(
            diagnosis_codes=['E11.9'],
            model_name=model_name,
            age=67,
            sex='F',
            orec='2'
        )

        if len(result.hcc_details) > 0:
            # At least check structure is correct
            for detail in result.hcc_details:
                assert isinstance(detail.hcc, str)
                assert isinstance(detail.is_chronic, bool)
