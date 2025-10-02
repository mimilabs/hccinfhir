import pytest
from hccinfhir.hccinfhir import HCCInFHIR
from hccinfhir.datamodels import Demographics, ServiceLevelData, RAFResult
import importlib.resources
import json
from pydantic_core import ValidationError
from hccinfhir import get_837_sample, extract_sld

@pytest.fixture
def sample_demographics():
    return {
        "age": 70,
        "sex": "M",
        "dual_elgbl_cd": "00",
        "orig_disabled": False,
        "new_enrollee": False,
        "esrd": False,
        "snp": False,
        "low_income": False,
        "graft_months": None,
        "category": "CNA"
    }

@pytest.fixture
def sample_eob():
    output = []
    with importlib.resources.open_text('hccinfhir.sample_files', 
                                      f'sample_eob_200.ndjson') as f:
        for line in f:
            eob_data = json.loads(line)
            output.append(eob_data)
    return output

@pytest.fixture
def sample_service_data():
    return [
        {
            "claim_id": "1",
            "claim_type": "professional",
            "claim_diagnosis_codes": ["E119"],
            "procedure_code": "99213",
            "service_date": "2023-01-01"
        },
        {
            "claim_id": "2",
            "claim_type": "professional",
            "claim_diagnosis_codes": ["E119"],
            "procedure_code": "0398T",
            "service_date": "2023-01-02"
        }
    ]

class TestHCCInFHIR:
    def test_initialization(self):
        processor = HCCInFHIR()
        assert processor.filter_claims is True
        
        processor = HCCInFHIR(filter_claims=False)
        assert processor.filter_claims is False

    def test_ensure_demographics(self):
        processor = HCCInFHIR()
        demo_dict = {
            "age": 70,
            "sex": "M",
            "dual_elgbl_cd": "00",
            "orig_disabled": False,
            "new_enrollee": False,
            "esrd": False,
            "category": "CNA"
        }
        
        # Test with dictionary
        result = processor._ensure_demographics(demo_dict)
        assert isinstance(result, Demographics)
        assert result.age == 70
        assert result.sex == "M"
        assert result.dual_elgbl_cd == "00"
        assert result.category == "CNA"
        assert result.non_aged == False
        assert result.orig_disabled == False
        assert result.disabled == False
        assert result.esrd == False
        assert result.snp == False
        assert result.low_income == False
        
        # Test with Demographics object
        demo_obj = Demographics(**demo_dict)
        result = processor._ensure_demographics(demo_obj)
        assert isinstance(result, Demographics)

    def test_run_with_eob(self, sample_demographics, sample_eob):
        processor = HCCInFHIR()
        
        result = processor.run(sample_eob, sample_demographics)
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'hcc_list')
        assert hasattr(result, 'service_level_data')
        assert isinstance(result.service_level_data, list)
        
        # Verify service level data processing
        print(result.service_level_data)
        sld = result.service_level_data[0]
        assert isinstance(sld, ServiceLevelData)


    def test_run_from_service_data(self, sample_demographics, sample_service_data):
        processor = HCCInFHIR()
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'hcc_list')
        assert hasattr(result, 'service_level_data')
        # Verify service data processing
        sld = result.service_level_data[0]
        assert isinstance(sld, ServiceLevelData)
        assert "E119" in sld.claim_diagnosis_codes

        sld_lst = [claim.model_dump(mode='json') 
            for claim in extract_sld(get_837_sample(1), format='837')]
        sld_lst += [{
            "procedure_code": "Q4205",
            "claim_diagnosis_codes": ["E11.9", "I10", "A227"],
            "claim_type": "71",
            "service_date": "2024-01-15"
        }]
        result = processor.run_from_service_data(sld_lst, sample_demographics)
        assert len(result.service_level_data) != len(sld_lst)


    def test_calculate_from_diagnosis(self, sample_demographics):
        processor = HCCInFHIR()
        diagnosis_codes = ["E119"]  # Type 2 diabetes without complications
        
        result = processor.calculate_from_diagnosis(diagnosis_codes, sample_demographics)
        
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'hcc_list')
        assert hasattr(result, 'demographics')

    def test_filtering_behavior(self, sample_demographics, sample_service_data):
        # Test with filtering enabled
        processor_with_filter = HCCInFHIR(filter_claims=True)
        result_filtered = processor_with_filter.run_from_service_data(
            sample_service_data, sample_demographics
        )
        
        # Test with filtering disabled
        processor_without_filter = HCCInFHIR(filter_claims=False)
        result_unfiltered = processor_without_filter.run_from_service_data(
            sample_service_data, sample_demographics
        )
        
        # Results might be the same in this case, but verify they're dictionaries
        assert hasattr(result_filtered, 'risk_score')
        assert hasattr(result_unfiltered, 'risk_score')

    def test_filtering_behavior_with_custom_files(self, sample_demographics, sample_service_data):
        
        processor = HCCInFHIR(filter_claims=True, 
                             proc_filtering_filename='ra_eligible_cpt_hcpcs_2025.csv',
                             dx_cc_mapping_filename='ra_dx_to_cc_2025.csv')
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        print(result.service_level_data)
        assert len(result.service_level_data) == 1

        processor = HCCInFHIR(filter_claims=False, 
                             proc_filtering_filename='ra_eligible_cpt_hcpcs_2023.csv',
                             dx_cc_mapping_filename='ra_dx_to_cc_2025.csv')
        result = processor.run_from_service_data(sample_service_data, sample_demographics)
        print(result)
        assert len(result.service_level_data) == 2



    def test_error_handling(self):
        processor = HCCInFHIR()
        
        # Test with invalid demographics
        with pytest.raises(ValidationError, match="2 validation errors for Demographics"):
            processor.run([], {"invalid": "data"})
        
        # Test with non-list service data
        with pytest.raises(ValueError, match="Service data must be a list"):
            processor.run_from_service_data("not a list", {
                "age": 70,
                "sex": "M",
                "dual_elgbl_cd": "00",
                "orig_disabled": False,
                "new_enrollee": False,
                "esrd": False,
                "category": "CNA"
            })

    def test_model_realcases(self):

        # Test empty EOB list with minimal demographics
        processor = HCCInFHIR()
        result = processor.run([], {"age": 70, "sex": "M", "dual_elgbl_cd": "00"})

        assert result.risk_score == 0.396
        assert result.hcc_list == []
        
        # Test with custom configuration
        hcc_processor = HCCInFHIR(
            filter_claims=True,                                    # Enable claim filtering
            model_name="CMS-HCC Model V28",                       # Choose HCC model version
            proc_filtering_filename="ra_eligible_cpt_hcpcs_2025.csv",  # CPT/HCPCS filtering rules
            dx_cc_mapping_filename="ra_dx_to_cc_2025.csv"         # Diagnosis to CC mapping
        )

        # Define beneficiary demographics
        demographics = {
            "age": 67,
            "sex": "F"
        }

        # Test with sample EOB list (would need fixture)
        sample_eob_list = []  # This would be populated from fixture in real test
        raf_result = hcc_processor.run(sample_eob_list, demographics)
 
        assert hasattr(raf_result, 'risk_score')
        assert hasattr(raf_result, 'risk_score_demographics')
        assert hasattr(raf_result, 'risk_score_hcc')
        assert hasattr(raf_result, 'hcc_list')

    def test_prefix_override_esrd_patient(self):
        """Test prefix_override for ESRD patient with incorrect orec/crec"""
        processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")

        # ESRD patient but orec/crec don't indicate ESRD (common data issue)
        demographics = Demographics(
            age=65,
            sex="F",
            orec="0",  # Should be '2' or '3' for ESRD, but data is wrong
            crec="0",  # Should be '2' or '3' for ESRD, but data is wrong
        )

        # Diagnosis codes for ESRD patient
        diagnosis_codes = ["N18.6", "E11.22", "I12.0"]  # ESRD, diabetes with CKD, hypertensive CKD

        # Without prefix_override - would use wrong coefficients
        result_without_override = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

        # With prefix_override - forces ESRD dialysis coefficients
        result_with_override = processor.calculate_from_diagnosis(
            diagnosis_codes,
            demographics,
            prefix_override='DI_'
        )

        # Scores should be different - ESRD dialysis has different coefficients
        assert result_without_override.risk_score != result_with_override.risk_score

        # Both should have same HCCs
        assert set(result_without_override.hcc_list) == set(result_with_override.hcc_list)