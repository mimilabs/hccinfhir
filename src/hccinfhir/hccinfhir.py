from typing import List, Dict, Any, Union, Optional
from hccinfhir.extractor import extract_sld_list
from hccinfhir.filter import apply_filter
from hccinfhir.model_calculate import calculate_raf
from hccinfhir.datamodels import Demographics, ServiceLevelData, RAFResult, ModelName, ProcFilteringFilename, DxCCMappingFilename, PrefixOverride
from hccinfhir.utils import load_proc_filtering, load_dx_to_cc_mapping

class HCCInFHIR:
    """
    Main class for processing FHIR EOB resources into HCC risk scores.
    
    This class integrates the extraction, filtering, and calculation components
    of the hccinfhir library.
    """
    
    def __init__(self, 
                 filter_claims: bool = True, 
                 model_name: ModelName = "CMS-HCC Model V28",
                 proc_filtering_filename: ProcFilteringFilename = "ra_eligible_cpt_hcpcs_2026.csv",
                 dx_cc_mapping_filename: DxCCMappingFilename = "ra_dx_to_cc_2026.csv"):
        """
        Initialize the HCCInFHIR processor.
        
        Args:
            filter_claims: Whether to apply filtering rules to claims. Default is True.
            model_name: The name of the model to use for the calculation. Default is "CMS-HCC Model V28".
            proc_filtering_filename: The filename of the professional cpt filtering file. Default is "ra_eligible_cpt_hcpcs_2026.csv".
            dx_cc_mapping_filename: The filename of the dx to cc mapping file. Default is "ra_dx_to_cc_2026.csv".
        """
        self.filter_claims = filter_claims
        self.model_name = model_name
        self.proc_filtering_filename = proc_filtering_filename
        self.dx_cc_mapping_filename = dx_cc_mapping_filename
        self.professional_cpt = load_proc_filtering(proc_filtering_filename)
        self.dx_to_cc_mapping = load_dx_to_cc_mapping(dx_cc_mapping_filename)


    def _ensure_demographics(self, demographics: Union[Demographics, Dict[str, Any]]) -> Demographics:
        """Convert demographics dict to Demographics object if needed."""
        if not isinstance(demographics, Demographics):
            return Demographics(**demographics)
        return demographics
    
    def _calculate_raf_from_demographics_and_dx_codes(self, diagnosis_codes: List[str],
                                                      demographics: Demographics,
                                                      prefix_override: Optional[PrefixOverride] = None,
                                                      maci: float = 0.0,
                                                      norm_factor: float = 1.0,
                                                      frailty_score: float = 0.0) -> RAFResult:
        """Calculate RAF score using demographics data."""
        return calculate_raf(
            diagnosis_codes=diagnosis_codes,
            model_name=self.model_name,
            age=demographics.age,
            sex=demographics.sex,
            dual_elgbl_cd=demographics.dual_elgbl_cd,
            orec=demographics.orec,
            crec=demographics.crec,
            new_enrollee=demographics.new_enrollee,
            snp=demographics.snp,
            low_income=demographics.low_income,
            lti=demographics.lti,
            graft_months=demographics.graft_months,
            dx_to_cc_mapping=self.dx_to_cc_mapping,
            prefix_override=prefix_override,
            maci=maci,
            norm_factor=norm_factor,
            frailty_score=frailty_score
        )

    def _get_unique_diagnosis_codes(self, service_data: List[ServiceLevelData]) -> List[str]:
        """Extract unique diagnosis codes from service level data."""
        return list({code for sld in service_data for code in sld.claim_diagnosis_codes})

    def run(self, eob_list: List[Dict[str, Any]],
            demographics: Union[Demographics, Dict[str, Any]],
            prefix_override: Optional[PrefixOverride] = None,
            maci: float = 0.0,
            norm_factor: float = 1.0,
            frailty_score: float = 0.0) -> RAFResult:
        """Process EOB resources and calculate RAF scores.

        Args:
            eob_list: List of EOB resources
            demographics: Demographics information
            prefix_override: Optional prefix to override auto-detected demographic prefix.
                Use when demographic categorization is incorrect (e.g., ESRD patients with orec=0).
            maci: Major Adjustment to Coding Intensity (0.0-1.0, default 0.0)
            norm_factor: Normalization factor (default 1.0)
            frailty_score: Frailty adjustment score (default 0.0)

        Returns:
            RAFResult object containing calculated scores and processed data
        """
        if not isinstance(eob_list, list):
            raise ValueError("eob_list must be a list; if no eob, pass empty list")
        
        demographics = self._ensure_demographics(demographics)
        
        # Extract and filter service level data
        sld_list = extract_sld_list(eob_list)

        if self.filter_claims:
            sld_list = apply_filter(sld_list, professional_cpt=self.professional_cpt)

        # Calculate RAF score
        unique_dx_codes = self._get_unique_diagnosis_codes(sld_list)
        raf_result = self._calculate_raf_from_demographics_and_dx_codes(
            unique_dx_codes, demographics, prefix_override, maci, norm_factor, frailty_score
        )

        # Create new result with service data included
        return raf_result.model_copy(update={'service_level_data': sld_list})
    
    def run_from_service_data(self, service_data: List[Union[ServiceLevelData, Dict[str, Any]]],
                             demographics: Union[Demographics, Dict[str, Any]],
                             prefix_override: Optional[PrefixOverride] = None,
                             maci: float = 0.0,
                             norm_factor: float = 1.0,
                             frailty_score: float = 0.0) -> RAFResult:
        """Process service-level data and calculate RAF scores.

        Args:
            service_data: List of ServiceLevelData objects or dictionaries
            demographics: Demographics information
            prefix_override: Optional prefix to override auto-detected demographic prefix.
                Use when demographic categorization is incorrect (e.g., ESRD patients with orec=0).
            maci: Major Adjustment to Coding Intensity (0.0-1.0, default 0.0)
            norm_factor: Normalization factor (default 1.0)
            frailty_score: Frailty adjustment score (default 0.0)

        Returns:
            RAFResult object containing calculated scores and processed data
        """
        demographics = self._ensure_demographics(demographics)
        
        if not isinstance(service_data, list):
            raise ValueError("Service data must be a list of service records")
                
        # Standardize service data with better error handling
        standardized_data = []
        for idx, item in enumerate(service_data):
            try:
                if isinstance(item, dict):
                    standardized_data.append(ServiceLevelData(**item))
                elif isinstance(item, ServiceLevelData):
                    standardized_data.append(item)
                else:
                    raise TypeError(f"Service data item must be a dictionary or ServiceLevelData object")
            except (KeyError, TypeError, ValueError) as e:
                raise ValueError(
                    f"Invalid service data at index {idx}: {str(e)}. "
                    "Required fields: claim_type, claim_diagnosis_codes, procedure_code, service_date"
                )
        
        if self.filter_claims:
            standardized_data = apply_filter(standardized_data,
                                             professional_cpt=self.professional_cpt)


        # Calculate RAF score
        unique_dx_codes = self._get_unique_diagnosis_codes(standardized_data)
        raf_result = self._calculate_raf_from_demographics_and_dx_codes(
            unique_dx_codes, demographics, prefix_override, maci, norm_factor, frailty_score
        )

        # Create new result with service data included
        return raf_result.model_copy(update={'service_level_data': standardized_data})
        
    def calculate_from_diagnosis(self, diagnosis_codes: List[str],
                               demographics: Union[Demographics, Dict[str, Any]],
                               prefix_override: Optional[PrefixOverride] = None,
                               maci: float = 0.0,
                               norm_factor: float = 1.0,
                               frailty_score: float = 0.0) -> RAFResult:
        """Calculate RAF scores from a list of diagnosis codes.

        Args:
            diagnosis_codes: List of diagnosis codes
            demographics: Demographics information
            prefix_override: Optional prefix to override auto-detected demographic prefix.
                Use when demographic categorization is incorrect (e.g., ESRD patients with orec=0).
            maci: Major Adjustment to Coding Intensity (0.0-1.0, default 0.0)
            norm_factor: Normalization factor (default 1.0)
            frailty_score: Frailty adjustment score (default 0.0)

        Raises:
            ValueError: If diagnosis_codes is empty or not a list
        """
        if not isinstance(diagnosis_codes, list):
            raise ValueError("diagnosis_codes must be a list")
        
        demographics = self._ensure_demographics(demographics)
        raf_result = self._calculate_raf_from_demographics_and_dx_codes(
            diagnosis_codes, demographics, prefix_override, maci, norm_factor, frailty_score
        )
        return raf_result