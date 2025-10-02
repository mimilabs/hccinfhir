"""
Tests for payment RAF calculation and prefix_override functionality.

This test suite covers:
1. Payment RAF calculation with MACI, normalization, and frailty
2. Prefix override functionality
3. ESRD new enrollee age categorization
4. CMS-HCC new enrollee vs ESRD new enrollee differences
"""

import pytest
from hccinfhir import HCCInFHIR, Demographics
from hccinfhir.model_calculate import calculate_raf
from hccinfhir.model_demographics import categorize_demographics


class TestPaymentRAF:
    """Test payment RAF calculations with MACI, norm_factor, and frailty_score."""

    def test_payment_raf_with_maci(self):
        """Test payment RAF calculation with MACI adjustment."""
        diagnosis_codes = ['E119', 'I509']  # Diabetes, Heart failure

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=67,
            sex='F',
            maci=0.057,  # 5.7% coding intensity adjustment
            norm_factor=1.0,
            frailty_score=0.0
        )

        # Payment RAF should be: risk_score * (1 - 0.057) / 1.0 + 0.0
        expected_payment = result.risk_score * 0.943
        assert abs(result.risk_score_payment - expected_payment) < 0.001
        assert result.risk_score_payment < result.risk_score  # Should be lower due to MACI

    def test_payment_raf_with_normalization(self):
        """Test payment RAF calculation with normalization factor."""
        diagnosis_codes = ['E119', 'I10']

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=70,
            sex='M',
            maci=0.0,
            norm_factor=1.015,  # 2026 normalization factor
            frailty_score=0.0
        )

        # Payment RAF should be: risk_score * 1.0 / 1.015 + 0.0
        expected_payment = result.risk_score / 1.015
        assert abs(result.risk_score_payment - expected_payment) < 0.001
        assert result.risk_score_payment < result.risk_score  # Should be lower due to normalization

    def test_payment_raf_with_frailty(self):
        """Test payment RAF calculation with frailty score."""
        diagnosis_codes = ['E119']

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=85,
            sex='F',
            maci=0.0,
            norm_factor=1.0,
            frailty_score=0.15  # Frailty adjustment
        )

        # Payment RAF should be: risk_score * 1.0 / 1.0 + 0.15
        expected_payment = result.risk_score + 0.15
        assert abs(result.risk_score_payment - expected_payment) < 0.001
        assert result.risk_score_payment > result.risk_score  # Should be higher due to frailty

    def test_payment_raf_with_all_adjustments(self):
        """Test payment RAF with all adjustments combined."""
        diagnosis_codes = ['E1165', 'I5030', 'N183']  # Complex patient

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=75,
            sex='M',
            maci=0.057,
            norm_factor=1.015,
            frailty_score=0.12
        )

        # Payment RAF should be: risk_score * (1 - 0.057) / 1.015 + 0.12
        expected_payment = result.risk_score * 0.943 / 1.015 + 0.12
        assert abs(result.risk_score_payment - expected_payment) < 0.001

    def test_payment_raf_via_hccinfhir_class(self):
        """Test payment RAF through HCCInFHIR class methods."""
        processor = HCCInFHIR(model_name="CMS-HCC Model V28")
        diagnosis_codes = ['E119', 'I10']
        demographics = Demographics(age=68, sex='F')

        result = processor.calculate_from_diagnosis(
            diagnosis_codes=diagnosis_codes,
            demographics=demographics,
            maci=0.05,
            norm_factor=1.01,
            frailty_score=0.1
        )

        expected_payment = result.risk_score * 0.95 / 1.01 + 0.1
        assert abs(result.risk_score_payment - expected_payment) < 0.001


class TestPrefixOverride:
    """Test prefix_override functionality for various scenarios."""

    def test_prefix_override_esrd_dialysis(self):
        """Test prefix override for ESRD dialysis patient."""
        diagnosis_codes = ['N186', 'E1122']  # ESRD, Diabetes with CKD

        # Without override - incorrect orec/crec
        result_no_override = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC ESRD Model V24",
            age=66,
            sex='F',
            orec='0',  # Wrong - should be '2' or '3' for ESRD
            crec='0'
        )

        # With override - force dialysis prefix
        result_with_override = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC ESRD Model V24",
            age=66,
            sex='F',
            orec='0',
            crec='0',
            prefix_override='DI_'
        )

        # Scores should be different due to different coefficient sets
        assert result_with_override.risk_score != result_no_override.risk_score

    def test_prefix_override_institutionalized(self):
        """Test prefix override for LTI (Long-Term Institutionalized) patient."""
        diagnosis_codes = ['F0390', 'I4891', 'N184']  # Dementia, AFib, CKD

        # Without override - community
        result_community = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=82,
            sex='F',
            lti=False
        )

        # With override - institutionalized
        result_lti = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=82,
            sex='F',
            lti=False,  # Will be overridden
            prefix_override='INS_'
        )

        # LTI coefficients are typically different
        assert result_lti.risk_score != result_community.risk_score

    def test_prefix_override_dual_eligible(self):
        """Test prefix override for dual eligible patient."""
        diagnosis_codes = ['E119', 'I10']

        # Force Full Benefit Dual, Aged
        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC Model V28",
            age=68,
            sex='F',
            dual_elgbl_cd='NA',  # Will be overridden
            prefix_override='CFA_'
        )

        assert result.risk_score > 0
        # Demographics should reflect FBD status
        assert result.demographics.fbd == True

    def test_categorize_demographics_with_prefix_override(self):
        """Test that categorize_demographics properly handles prefix_override."""
        # Test ESRD prefix sets esrd flag
        demo_esrd = categorize_demographics(
            age=66,
            sex='F',
            orec='0',
            prefix_override='DI_'
        )
        assert demo_esrd.esrd == True

        # Test INS prefix sets lti flag
        demo_lti = categorize_demographics(
            age=80,
            sex='M',
            prefix_override='INS_'
        )
        assert demo_lti.lti == True

        # Test dual eligible prefix sets flags
        demo_fbd = categorize_demographics(
            age=70,
            sex='F',
            dual_elgbl_cd='NA',
            prefix_override='CFA_'
        )
        assert demo_fbd.fbd == True
        assert demo_fbd.pbd == False


class TestESRDNewEnrolleeAgeCategorization:
    """Test age categorization differences between ESRD and CMS-HCC new enrollees."""

    def test_esrd_new_enrollee_grouped_ages(self):
        """Test that ESRD new enrollees use grouped 65_69 age category."""
        ages_65_to_69 = [65, 66, 67, 68, 69]

        for age in ages_65_to_69:
            demo = categorize_demographics(
                age=age,
                sex='F',
                orec='2',  # ESRD
                new_enrollee=True
            )
            # ESRD new enrollees should use grouped 65_69
            assert demo.category == 'NEF65_69', f"Age {age} should map to NEF65_69, got {demo.category}"

    def test_cms_hcc_new_enrollee_individual_ages(self):
        """Test that CMS-HCC new enrollees use individual age categories 65-69."""
        test_cases = [
            (65, 'NEF65'),
            (66, 'NEF66'),
            (67, 'NEF67'),
            (68, 'NEF68'),
            (69, 'NEF69')
        ]

        for age, expected_category in test_cases:
            demo = categorize_demographics(
                age=age,
                sex='F',
                orec='0',  # Not ESRD
                new_enrollee=True
            )
            assert demo.category == expected_category, f"Age {age} should map to {expected_category}, got {demo.category}"

    def test_esrd_dialysis_new_enrollee_calculation(self):
        """Test full RAF calculation for ESRD dialysis new enrollee."""
        diagnosis_codes = ['N186', 'E1122', 'I5030']

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC ESRD Model V24",
            age=66,
            sex='F',
            orec='2',  # ESRD
            new_enrollee=True
        )

        # Should use DNE_ prefix and NEF65_69 category
        assert result.demographics.esrd == True
        assert result.demographics.new_enrollee == True
        assert result.demographics.category == 'NEF65_69'
        print(result)
        assert result.risk_score > 0

    def test_esrd_dialysis_non_new_enrollee(self):
        """Test ESRD dialysis non-new enrollee for comparison."""
        diagnosis_codes = ['N186', 'E1122', 'I5030']

        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC ESRD Model V24",
            age=66,
            sex='F',
            orec='2',  # ESRD
            new_enrollee=False
        )

        # Should use DI_ prefix and F65_69 category
        assert result.demographics.esrd == True
        assert result.demographics.new_enrollee == False
        assert result.demographics.category == 'F65_69'
        assert result.risk_score > 0

    def test_prefix_override_with_esrd_new_enrollee(self):
        """Test prefix override forces correct ESRD categorization."""
        diagnosis_codes = ['N186']

        # Force DNE with bad orec/crec
        result = calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name="CMS-HCC ESRD Model V24",
            age=67,
            sex='M',
            orec='0',  # Wrong
            crec='0',  # Wrong
            prefix_override='DNE_'
        )

        # Should properly categorize despite bad orec/crec
        assert result.demographics.esrd == True
        assert result.demographics.new_enrollee == True
        assert result.demographics.category == 'NEM65_69'


class TestNewEnrolleeEdgeCases:
    """Test edge cases for new enrollee calculations."""

    def test_age_64_disabled_new_enrollee(self):
        """Test age 64 disabled new enrollee (should use 60_64 bucket)."""
        demo = categorize_demographics(
            age=64,
            sex='F',
            orec='1',  # Disabled
            new_enrollee=True
        )
        assert demo.category == 'NEF60_64'

    def test_age_64_non_disabled_new_enrollee(self):
        """Test age 64 non-disabled new enrollee (should use 65 bucket)."""
        demo = categorize_demographics(
            age=64,
            sex='F',
            orec='0',  # Not disabled
            new_enrollee=True
        )
        assert demo.category == 'NEF65'

    def test_age_95_plus_new_enrollee(self):
        """Test very elderly new enrollee uses 95_GT bucket."""
        demo = categorize_demographics(
            age=98,
            sex='M',
            new_enrollee=True
        )
        assert demo.category == 'NEM95_GT'

    def test_young_disabled_new_enrollee(self):
        """Test young disabled new enrollee."""
        demo = categorize_demographics(
            age=25,
            sex='M',
            orec='1',
            new_enrollee=True
        )
        assert demo.category == 'NEM0_34'
        assert demo.disabled == True


class TestIntegrationPaymentAndPrefix:
    """Integration tests combining payment RAF and prefix override."""

    def test_esrd_patient_with_payment_adjustments(self):
        """Test ESRD patient with full payment RAF calculation."""
        processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")
        diagnosis_codes = ['N186', 'E1165', 'I5030']
        demographics = Demographics(age=68, sex='F', orec='0', crec='0')

        result = processor.calculate_from_diagnosis(
            diagnosis_codes=diagnosis_codes,
            demographics=demographics,
            prefix_override='DI_',  # Force dialysis
            maci=0.057,
            norm_factor=1.015,
            frailty_score=0.08
        )

        # Verify demographics were overridden
        assert result.demographics.esrd == True

        # Verify payment calculation
        expected_payment = result.risk_score * 0.943 / 1.015 + 0.08
        assert abs(result.risk_score_payment - expected_payment) < 0.001

    def test_lti_patient_with_payment_adjustments(self):
        """Test LTI patient with payment RAF."""
        processor = HCCInFHIR(model_name="CMS-HCC Model V28")
        diagnosis_codes = ['F0390', 'I4891']
        demographics = Demographics(age=85, sex='F', lti=False)

        result = processor.calculate_from_diagnosis(
            diagnosis_codes=diagnosis_codes,
            demographics=demographics,
            prefix_override='INS_',  # Force institutionalized
            maci=0.05,
            norm_factor=1.0,
            frailty_score=0.20  # High frailty
        )

        # Verify LTI was set
        assert result.demographics.lti == True

        # Verify payment with high frailty
        expected_payment = result.risk_score * 0.95 + 0.20
        assert abs(result.risk_score_payment - expected_payment) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
