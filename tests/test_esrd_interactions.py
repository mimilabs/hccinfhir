# tests/test_esrd_interactions.py
"""
Test cases for ESRD model interactions added in v0.1.6.

Tests cover:
- ESRD V21: GE65_DUR*, LT65_DUR* duration interactions
- ESRD V24: FGC/FGI interactions with ND_PBD and FBD stratification
- ESRD V24: PBD flag coefficients
- ESRD V24: LTI_GE65/LTI_LT65 graft institutional interactions
- V24/V28: LTIMCAID institutional interaction
- No-prefix coefficient lookups for ESRD duration coefficients
"""

import pytest
from hccinfhir.model_interactions import create_demographic_interactions, apply_interactions
from hccinfhir.model_coefficients import apply_coefficients
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.datamodels import Demographics


# =============================================================================
# ESRD V21 Duration Interactions
# =============================================================================

class TestESRDV21DurationInteractions:
    """Test ESRD V21 simple age-based duration interactions."""

    def test_v21_dur4_9_aged(self):
        """Aged patient with 6 months graft should get GE65_DUR4_9."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('GE65_DUR4_9') == 1
        assert 'LT65_DUR4_9' not in interactions
        assert 'GE65_DUR10PL' not in interactions

    def test_v21_dur4_9_nonaged(self):
        """Non-aged patient with 5 months graft should get LT65_DUR4_9."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=5,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('LT65_DUR4_9') == 1
        assert 'GE65_DUR4_9' not in interactions

    def test_v21_dur10pl_aged(self):
        """Aged patient with 15 months graft should get GE65_DUR10PL."""
        demographics = Demographics(
            age=72,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=15,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('GE65_DUR10PL') == 1
        assert 'LT65_DUR10PL' not in interactions
        assert 'GE65_DUR4_9' not in interactions

    def test_v21_dur10pl_nonaged(self):
        """Non-aged patient with 24 months graft should get LT65_DUR10PL."""
        demographics = Demographics(
            age=50,
            sex='M',
            category="M50_54",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=24,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('LT65_DUR10PL') == 1
        assert 'GE65_DUR10PL' not in interactions

    def test_v21_no_duration_under_4_months(self):
        """Patient with < 4 months graft should not get any duration interactions."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=3,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'GE65_DUR4_9' not in interactions
        assert 'LT65_DUR4_9' not in interactions
        assert 'GE65_DUR10PL' not in interactions
        assert 'LT65_DUR10PL' not in interactions


# =============================================================================
# ESRD V24 FGC/FGI Interactions - Non-Dual/Partial Benefit Dual (ND_PBD)
# =============================================================================

class TestESRDV24FGCInteractionsNDPBD:
    """Test ESRD V24 FGC (Community) interactions for ND_PBD."""

    def test_fgc_dur4_9_nd_pbd_aged(self):
        """Aged community patient (not LTI, not FBD) with 6 months graft."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGC_GE65_DUR4_9_ND_PBD') == 1
        assert 'FGC_LT65_DUR4_9_ND_PBD' not in interactions
        assert 'FGI_GE65_DUR4_9_ND_PBD' not in interactions

    def test_fgc_dur10pl_nd_pbd_nonaged(self):
        """Non-aged community patient with 12 months graft."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=12,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGC_LT65_DUR10PL_ND_PBD') == 1
        assert 'FGC_GE65_DUR10PL_ND_PBD' not in interactions


class TestESRDV24FGIInteractionsNDPBD:
    """Test ESRD V24 FGI (Institutional) interactions for ND_PBD."""

    def test_fgi_dur4_9_nd_pbd_aged_lti(self):
        """Aged LTI patient (not FBD) with 6 months graft should get FGI."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=True,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGI_GE65_DUR4_9_ND_PBD') == 1
        assert 'FGC_GE65_DUR4_9_ND_PBD' not in interactions

    def test_fgi_dur10pl_nd_pbd_nonaged_lti(self):
        """Non-aged LTI patient with 15 months graft."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=True,
            graft_months=15,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGI_LT65_DUR10PL_ND_PBD') == 1
        assert 'FGC_LT65_DUR10PL_ND_PBD' not in interactions


# =============================================================================
# ESRD V24 FGC/FGI Interactions - Full Benefit Dual (FBD)
# =============================================================================

class TestESRDV24FGCInteractionsFBD:
    """Test ESRD V24 FGC (Community) interactions for FBD."""

    def test_fgc_dur4_9_fbd_aged(self):
        """Aged FBD community patient with 6 months graft."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=False,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGC_GE65_DUR4_9_FBD') == 1
        assert 'FGC_LT65_DUR4_9_FBD' not in interactions
        # Should NOT have ND_PBD variants
        assert 'FGC_GE65_DUR4_9_ND_PBD' not in interactions

    def test_fgc_dur10pl_fbd_nonaged(self):
        """Non-aged FBD community patient with 12 months graft."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=True,
            pbd=False,
            lti=False,
            graft_months=12,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGC_LT65_DUR10PL_FBD') == 1
        assert 'FGC_GE65_DUR10PL_FBD' not in interactions


class TestESRDV24FGIInteractionsFBD:
    """Test ESRD V24 FGI (Institutional) interactions for FBD."""

    def test_fgi_dur4_9_fbd_aged_lti(self):
        """Aged FBD LTI patient with 6 months graft should get FGI_FBD."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=True,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGI_GE65_DUR4_9_FBD') == 1
        assert 'FGC_GE65_DUR4_9_FBD' not in interactions

    def test_fgi_dur10pl_fbd_nonaged_lti(self):
        """Non-aged FBD LTI patient with 15 months graft."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=True,
            pbd=False,
            lti=True,
            graft_months=15,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGI_LT65_DUR10PL_FBD') == 1
        assert 'FGC_LT65_DUR10PL_FBD' not in interactions


# =============================================================================
# ESRD V24 PBD Flag Coefficients
# =============================================================================

class TestESRDV24PBDFlags:
    """Test ESRD V24 PBD (Partial Benefit Dual) flag interactions."""

    def test_pbd_flag_aged_community(self):
        """PBD aged community patient should get PBD flag."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=True,
            lti=False,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGC_PBD_GE65_flag') == 1
        assert 'FGC_PBD_LT65_flag' not in interactions
        assert 'FGI_PBD_GE65_flag' not in interactions

    def test_pbd_flag_nonaged_lti(self):
        """PBD non-aged LTI patient should get FGI PBD flag."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=True,
            lti=True,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('FGI_PBD_LT65_flag') == 1
        assert 'FGC_PBD_LT65_flag' not in interactions

    def test_no_pbd_flag_for_fbd(self):
        """FBD patient should NOT get PBD flag."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=False,
            graft_months=6,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'FGC_PBD_GE65_flag' not in interactions
        assert 'FGC_PBD_LT65_flag' not in interactions


# =============================================================================
# ESRD V24 LTI_GE65/LTI_LT65 Graft Institutional Interactions
# =============================================================================

class TestESRDV24LTIInteractions:
    """Test ESRD V24 LTI_GE65/LTI_LT65 interactions for Graft Institutional."""

    def test_lti_ge65(self):
        """Aged LTI patient should get LTI_GE65."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=True,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('LTI_GE65') == 1
        assert 'LTI_LT65' not in interactions
        # Also should have LTI_Aged (looked up with DI_ prefix)
        assert interactions.get('LTI_Aged') == 1

    def test_lti_lt65(self):
        """Non-aged LTI patient should get LTI_LT65."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=True,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('LTI_LT65') == 1
        assert 'LTI_GE65' not in interactions
        # Also should have LTI_NonAged
        assert interactions.get('LTI_NonAged') == 1

    def test_no_lti_for_community(self):
        """Non-LTI patient should NOT get LTI interactions."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'LTI_GE65' not in interactions
        assert 'LTI_LT65' not in interactions
        assert 'LTI_Aged' not in interactions
        assert 'LTI_NonAged' not in interactions


# =============================================================================
# ESRD V21 Originally ESRD and MCAID Interactions
# =============================================================================

class TestESRDV21OriginallyESRD:
    """Test Originally_ESRD interactions for ESRD V21 and V24."""

    def test_originally_esrd_female_aged(self):
        """Aged female with OREC='2' (originally ESRD) should get Originally_ESRD_Female."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            orec='2',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('Originally_ESRD_Female') == 1
        assert 'Originally_ESRD_Male' not in interactions

    def test_originally_esrd_male_aged(self):
        """Aged male with OREC='3' should get Originally_ESRD_Male."""
        demographics = Demographics(
            age=70,
            sex='M',
            category="M70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            orec='3',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('Originally_ESRD_Male') == 1
        assert 'Originally_ESRD_Female' not in interactions

    def test_no_originally_esrd_for_nonaged(self):
        """Non-aged should NOT get Originally_ESRD interactions."""
        demographics = Demographics(
            age=55,
            sex='F',
            category="F55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=False,
            lti=False,
            orec='2',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'Originally_ESRD_Female' not in interactions
        assert 'Originally_ESRD_Male' not in interactions

    def test_no_originally_esrd_without_orec(self):
        """Aged without OREC='2' or '3' should NOT get Originally_ESRD."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            orec='0',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'Originally_ESRD_Female' not in interactions


class TestESRDV21MCAIDInteractions:
    """Test MCAID × sex × age interactions for ESRD V21."""

    def test_mcaid_female_aged(self):
        """Aged female with Medicaid should get MCAID_Female_Aged."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=False,
            dual_elgbl_cd='02',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('MCAID_Female_Aged') == 1
        assert 'MCAID_Female_NonAged' not in interactions
        assert 'MCAID_Male_Aged' not in interactions

    def test_mcaid_male_nonaged(self):
        """Non-aged male with Medicaid should get MCAID_Male_NonAged."""
        demographics = Demographics(
            age=55,
            sex='M',
            category="M55_59",
            disabled=True,
            orig_disabled=False,
            non_aged=True,
            fbd=False,
            pbd=True,
            lti=False,
            dual_elgbl_cd='01',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('MCAID_Male_NonAged') == 1
        assert 'MCAID_Male_Aged' not in interactions

    def test_no_mcaid_without_medicaid(self):
        """Non-Medicaid patient should NOT get MCAID interactions."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            dual_elgbl_cd='00',
            esrd=True
        )
        interactions = create_demographic_interactions(demographics)

        assert 'MCAID_Female_Aged' not in interactions
        assert 'MCAID_Female_NonAged' not in interactions
        assert 'MCAID_Male_Aged' not in interactions
        assert 'MCAID_Male_NonAged' not in interactions


# =============================================================================
# V24/V28 LTIMCAID Institutional Interaction
# =============================================================================

class TestLTIMCAIDInteraction:
    """Test LTIMCAID interaction for CMS-HCC V24/V28 Institutional model."""

    def test_ltimcaid_present(self):
        """LTI patient with Medicaid should get LTIMCAID."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=True,
            dual_elgbl_cd='02'  # Full dual
        )
        interactions = create_demographic_interactions(demographics)

        assert interactions.get('LTIMCAID') == 1

    def test_ltimcaid_absent_no_medicaid(self):
        """LTI patient without Medicaid should NOT get LTIMCAID."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=True,
            dual_elgbl_cd='00'  # Not dual
        )
        interactions = create_demographic_interactions(demographics)

        assert 'LTIMCAID' not in interactions

    def test_ltimcaid_absent_no_lti(self):
        """Non-LTI patient with Medicaid should NOT get LTIMCAID."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=False,
            dual_elgbl_cd='02'
        )
        interactions = create_demographic_interactions(demographics)

        assert 'LTIMCAID' not in interactions


# =============================================================================
# No-Prefix Coefficient Lookups
# =============================================================================

class TestNoPrefixCoefficientLookup:
    """Test no-prefix coefficient lookups for ESRD duration coefficients."""

    def test_fgc_no_prefix_lookup(self):
        """FGC coefficients should be looked up without prefix."""
        demographics = categorize_demographics(
            age=70,
            sex='F',
            dual_elgbl_cd='00',
            orec='2',
            version='V2',
            new_enrollee=False,
            snp=False,
            low_income=False,
            graft_months=6
        )

        # FGC coefficients stored without prefix
        test_coefficients = {
            ("fgc_ge65_dur4_9_nd_pbd", "CMS-HCC ESRD Model V24"): 2.529,
            ("fgc_lt65_dur4_9_nd_pbd", "CMS-HCC ESRD Model V24"): 3.123,
        }

        interactions = {'FGC_GE65_DUR4_9_ND_PBD': 1}

        result = apply_coefficients(
            demographics=demographics,
            hcc_set=set(),
            interactions=interactions,
            model_name="CMS-HCC ESRD Model V24",
            coefficients=test_coefficients
        )

        assert result.get('FGC_GE65_DUR4_9_ND_PBD') == 2.529

    def test_fgi_no_prefix_lookup(self):
        """FGI coefficients should be looked up without prefix."""
        demographics = categorize_demographics(
            age=70,
            sex='F',
            dual_elgbl_cd='00',
            orec='2',
            version='V2',
            new_enrollee=False,
            snp=False,
            low_income=False,
            graft_months=6,
            lti=True
        )

        test_coefficients = {
            ("fgi_ge65_dur4_9_nd_pbd", "CMS-HCC ESRD Model V24"): 1.845,
        }

        interactions = {'FGI_GE65_DUR4_9_ND_PBD': 1}

        result = apply_coefficients(
            demographics=demographics,
            hcc_set=set(),
            interactions=interactions,
            model_name="CMS-HCC ESRD Model V24",
            coefficients=test_coefficients
        )

        assert result.get('FGI_GE65_DUR4_9_ND_PBD') == 1.845

    def test_v21_duration_no_prefix_lookup(self):
        """V21 GE65_DUR/LT65_DUR coefficients should be looked up without prefix."""
        demographics = categorize_demographics(
            age=70,
            sex='F',
            dual_elgbl_cd='00',
            orec='2',
            version='V2',
            new_enrollee=False,
            snp=False,
            low_income=False,
            graft_months=6
        )

        test_coefficients = {
            ("ge65_dur4_9", "CMS-HCC ESRD Model V21"): 2.562,
            ("lt65_dur4_9", "CMS-HCC ESRD Model V21"): 3.045,
        }

        interactions = {'GE65_DUR4_9': 1}

        result = apply_coefficients(
            demographics=demographics,
            hcc_set=set(),
            interactions=interactions,
            model_name="CMS-HCC ESRD Model V21",
            coefficients=test_coefficients
        )

        assert result.get('GE65_DUR4_9') == 2.562

    def test_lti_ge65_no_prefix_lookup(self):
        """LTI_GE65/LTI_LT65 coefficients should be looked up without prefix."""
        demographics = categorize_demographics(
            age=70,
            sex='F',
            dual_elgbl_cd='00',
            orec='2',
            version='V2',
            new_enrollee=False,
            snp=False,
            low_income=False,
            lti=True
        )

        test_coefficients = {
            ("lti_ge65", "CMS-HCC ESRD Model V24"): 0.955,
            ("lti_lt65", "CMS-HCC ESRD Model V24"): 2.146,
        }

        interactions = {'LTI_GE65': 1}

        result = apply_coefficients(
            demographics=demographics,
            hcc_set=set(),
            interactions=interactions,
            model_name="CMS-HCC ESRD Model V24",
            coefficients=test_coefficients
        )

        assert result.get('LTI_GE65') == 0.955


# =============================================================================
# Integration Tests
# =============================================================================

class TestESRDIntegration:
    """Integration tests for ESRD interactions through apply_interactions."""

    def test_esrd_v24_full_flow_nd_pbd(self):
        """Test full interaction flow for ESRD V24 ND_PBD patient."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=False,
            pbd=False,
            lti=False,
            graft_months=6,
            esrd=True
        )

        interactions = apply_interactions(
            demographics,
            hcc_set={'85'},
            model_name="CMS-HCC ESRD Model V24"
        )

        # Should have V21 and V24 FGC interactions
        assert 'GE65_DUR4_9' in interactions
        assert 'FGC_GE65_DUR4_9_ND_PBD' in interactions
        # Should NOT have FBD or FGI variants
        assert 'FGC_GE65_DUR4_9_FBD' not in interactions
        assert 'FGI_GE65_DUR4_9_ND_PBD' not in interactions

    def test_esrd_v24_full_flow_fbd_lti(self):
        """Test full interaction flow for ESRD V24 FBD LTI patient."""
        demographics = Demographics(
            age=70,
            sex='F',
            category="F70_74",
            disabled=False,
            orig_disabled=False,
            non_aged=False,
            fbd=True,
            pbd=False,
            lti=True,
            graft_months=6,
            esrd=True,
            dual_elgbl_cd='02'
        )

        interactions = apply_interactions(
            demographics,
            hcc_set={'85'},
            model_name="CMS-HCC ESRD Model V24"
        )

        # Should have FGI_FBD interactions (not FGC since LTI)
        assert 'FGI_GE65_DUR4_9_FBD' in interactions
        assert 'FGC_GE65_DUR4_9_FBD' not in interactions
        # Should have LTI interactions
        assert 'LTI_GE65' in interactions
        assert 'LTI_Aged' in interactions
        # Should have LTIMCAID
        assert 'LTIMCAID' in interactions
