from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Set, TypedDict, Union

# Define Model Name literal type
ModelName = Literal[
    "CMS-HCC Model V22",
    "CMS-HCC Model V24",
    "CMS-HCC Model V28",
    "CMS-HCC ESRD Model V21",
    "CMS-HCC ESRD Model V24",
    "RxHCC Model V08"
]

# Filename types: allow bundled filenames (with autocomplete) OR any custom string path
ProcFilteringFilename = Union[
    Literal[
        "ra_eligible_cpt_hcpcs_2023.csv",
        "ra_eligible_cpt_hcpcs_2024.csv",
        "ra_eligible_cpt_hcpcs_2025.csv",
        "ra_eligible_cpt_hcpcs_2026.csv"
    ],
    str  # Allow any custom file path
]

DxCCMappingFilename = Union[
    Literal[
        "ra_dx_to_cc_2025.csv",
        "ra_dx_to_cc_2026.csv"
    ],
    str
]

HierarchiesFilename = Union[
    Literal[
        "ra_hierarchies_2025.csv",
        "ra_hierarchies_2026.csv"
    ],
    str
]

IsChronicFilename = Union[
    Literal[
        "hcc_is_chronic.csv",
        "hcc_is_chronic_without_esrd_model.csv"
    ],
    str
]

CoefficientsFilename = Union[
    Literal[
        "ra_coefficients_2025.csv",
        "ra_coefficients_2026.csv"
    ],
    str
]

PrefixOverride = Literal[
    # CMS-HCC Community prefixes
    "CNA_",  # Community, Non-Dual, Aged
    "CND_",  # Community, Non-Dual, Disabled
    "CFA_",  # Community, Full Benefit Dual, Aged
    "CFD_",  # Community, Full Benefit Dual, Disabled
    "CPA_",  # Community, Partial Benefit Dual, Aged
    "CPD_",  # Community, Partial Benefit Dual, Disabled
    # CMS-HCC Institutional
    "INS_",  # Long-Term Institutionalized
    # CMS-HCC New Enrollee
    "NE_",   # New Enrollee
    "SNPNE_",  # Special Needs Plan New Enrollee
    # ESRD Dialysis
    "DI_",   # Dialysis
    "DNE_",  # Dialysis New Enrollee
    # ESRD Graft
    "GI_",   # Graft, Institutionalized
    "GNE_",  # Graft, New Enrollee
    "GFPA_", # Graft, Full Benefit Dual, Aged
    "GFPN_", # Graft, Full Benefit Dual, Non-Aged
    "GNPA_", # Graft, Non-Dual, Aged
    "GNPN_", # Graft, Non-Dual, Non-Aged
    # ESRD Transplant
    "TRANSPLANT_KIDNEY_ONLY_1M",  # 1 month post-transplant
    "TRANSPLANT_KIDNEY_ONLY_2M",  # 2 months post-transplant
    "TRANSPLANT_KIDNEY_ONLY_3M",  # 3 months post-transplant
    # RxHCC Community Enrollee
    "Rx_CE_LowAged_",     # Community Enrollee, Low Income, Aged
    "Rx_CE_LowNoAged_",   # Community Enrollee, Low Income, Non-Aged
    "Rx_CE_NoLowAged_",   # Community Enrollee, Not Low Income, Aged
    "Rx_CE_NoLowNoAged_", # Community Enrollee, Not Low Income, Non-Aged
    "Rx_CE_LTI_",         # Community Enrollee, Long-Term Institutionalized
    # RxHCC New Enrollee
    "Rx_NE_Lo_",   # New Enrollee, Low Income
    "Rx_NE_NoLo_", # New Enrollee, Not Low Income
    "Rx_NE_LTI_",  # New Enrollee, Long-Term Institutionalized
]

class HCCDetail(BaseModel):
    """
    Detailed information about an HCC category.

    Attributes:
        hcc: HCC code (e.g., "18", "85")
        label: Human-readable description (e.g., "Diabetes with Chronic Complications")
        is_chronic: Whether this HCC is considered a chronic condition
        coefficient: The coefficient value applied for this HCC in the RAF calculation
    """
    hcc: str = Field(..., description="HCC code (e.g., '18', '85')")
    label: Optional[str] = Field(None, description="Human-readable HCC description")
    is_chronic: bool = Field(False, description="Whether this HCC is a chronic condition")
    coefficient: Optional[float] = Field(None, description="Coefficient value for this HCC")


class ServiceLevelData(BaseModel):
    """
    Represents standardized service-level data extracted from healthcare claims.
    
    Attributes:
        claim_id: Unique identifier for the claim
        procedure_code: Healthcare Common Procedure Coding System (HCPCS) code
        ndc: National Drug Code
        linked_diagnosis_codes: ICD-10 diagnosis codes linked to this service
        claim_diagnosis_codes: All diagnosis codes on the claim
        claim_type: Type of claim (e.g., NCH Claim Type Code, or 837I, 837P)
        provider_specialty: Provider taxonomy or specialty code
        performing_provider_npi: National Provider Identifier for performing provider
        billing_provider_npi: National Provider Identifier for billing provider
        patient_id: Unique identifier for the patient
        facility_type: Type of facility where service was rendered
        service_type: Type of service provided (facility type + service type = Type of Bill)
        service_date: Date service was performed (YYYY-MM-DD)
        place_of_service: Place of service code
        quantity: Number of units provided
        quantity_unit: Unit of measure for quantity
        modifiers: List of procedure code modifiers
        allowed_amount: Allowed amount for the service
    """
    claim_id: Optional[str] = None
    procedure_code: Optional[str] = None
    ndc: Optional[str] = None
    linked_diagnosis_codes: List[str] = []
    claim_diagnosis_codes: List[str] = []
    claim_type: Optional[str] = None
    provider_specialty: Optional[str] = None
    performing_provider_npi: Optional[str] = None
    billing_provider_npi: Optional[str] = None
    patient_id: Optional[str] = None
    facility_type: Optional[str] = None
    service_type: Optional[str] = None
    service_date: Optional[str] = None
    place_of_service: Optional[str] = None
    quantity: Optional[float] = None
    modifiers: List[str] = []
    allowed_amount: Optional[float] = None

class Demographics(BaseModel):
    """
    Response model for demographic categorization
    """
    age: Union[int, float] = Field(..., description="[required] Beneficiary age")
    sex: Literal['M', 'F', '1', '2'] = Field(..., description="[required] Beneficiary sex")
    dual_elgbl_cd: Optional[Literal[None, '', 'NA', '99', '00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10']] = Field('NA', description="Dual status code")
    orec: Optional[Literal[None, '', '0', '1', '2', '3']] = Field('', description="Original reason for entitlement")
    crec: Optional[Literal[None, '', '0', '1', '2', '3']] = Field('', description="Current reason for entitlement")
    new_enrollee: Optional[bool] = Field(False, description="True if beneficiary is a new enrollee")
    snp: Optional[bool] = Field(False, description="True if beneficiary is in SNP")
    version: Optional[str] = Field("V2", description="Version of categorization used (V2, V4, V6)")
    low_income: Optional[bool] = Field(False, description="True if beneficiary is in low income; RxHCC only")
    graft_months: Optional[int] = Field(None, description="Number of months since transplant; ESRD Model only")
    category: Optional[str] = Field(None, description="[derived] Age-sex category code")
    non_aged: Optional[bool] = Field(False, description="[derived] True if age <= 64")
    orig_disabled: Optional[bool] = Field(False, description="[derived] True if originally disabled (OREC='1' and not currently disabled)")
    disabled: Optional[bool] = Field(False, description="[derived] True if currently disabled (age < 65 and OREC != '0')")
    esrd: Optional[bool] = Field(False, description="[derived] True if ESRD (ESRD Model)")
    lti: Optional[bool] = Field(False, description="[derived] True if LTI (LTI Model)") 
    fbd: Optional[bool] = Field(False, description="[derived] True if FBD (FBD Model)") 
    pbd: Optional[bool] = Field(False, description="[derived] True if PBD (PBD Model)")


class RAFResult(BaseModel):
    """Risk adjustment calculation results"""
    risk_score: float = Field(..., description="Final RAF score")
    risk_score_demographics: float = Field(..., description="Demographics-only risk score")
    risk_score_chronic_only: float = Field(..., description="Chronic conditions risk score")
    risk_score_hcc: float = Field(..., description="HCC conditions risk score")
    risk_score_payment: float = Field(..., description="Payment RAF score (adjusted for MACI, normalization, and frailty)")
    hcc_list: List[str] = Field(default_factory=list, description="List of active HCC categories")
    hcc_details: List[HCCDetail] = Field(default_factory=list, description="Detailed HCC information with labels and chronic status")
    cc_to_dx: Dict[str, Set[str]] = Field(default_factory=dict, description="Condition categories mapped to diagnosis codes")
    coefficients: Dict[str, float] = Field(default_factory=dict, description="Applied model coefficients")
    interactions: Dict[str, float] = Field(default_factory=dict, description="Disease interaction coefficients")
    demographics: Demographics = Field(..., description="Patient demographics used in calculation")
    model_name: ModelName = Field(..., description="HCC model used for calculation")
    version: str = Field(..., description="Library version")
    diagnosis_codes: List[str] = Field(default_factory=list, description="Input diagnosis codes")
    service_level_data: Optional[List[ServiceLevelData]] = Field(default=None, description="Processed service records")
    
    model_config = {"extra": "forbid", "validate_assignment": True}

class HCPCoveragePeriod(BaseModel):
    """A single HCP (Health Care Plan) coverage period from HD loop"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    hcp_code: Optional[str] = None
    hcp_status: Optional[str] = None
    aid_codes: Optional[str] = None  # REF*CE composite


class EnrollmentData(BaseModel):
    """
    Enrollment and demographic data extracted from 834 transactions.

    Focus: Extract data needed for risk adjustment and Medicaid coverage tracking.
    Supports California DHCS Medi-Cal 834 format with FAME fields.

    Attributes:
        # Header Info
        source: Interchange sender ID (ISA06)
        report_date: Transaction date (GS04)

        # Identifiers
        member_id: Unique identifier for the member (REF*0F)
        mbi: Medicare Beneficiary Identifier (REF*6P)
        medicaid_id: Medicaid/Medi-Cal ID number (REF*23)
        hic: Medicare HICN (REF*F6)
        cin: Client Index Number from REF*3H
        cin_check_digit: CIN check digit from REF*3H

        # Name
        first_name: Member first name (NM104)
        last_name: Member last name (NM103)
        middle_name: Member middle name (NM105)

        # Demographics
        dob: Date of birth (YYYY-MM-DD)
        age: Calculated age
        sex: Member sex (M/F)
        race: Race/ethnicity code (DMG05)
        language: Preferred language (LUI02)
        death_date: Date of death if applicable

        # Address
        address_1: Street address line 1 (N301)
        address_2: Street address line 2 (N302)
        city: City (N401)
        state: State code (N402)
        zip: Postal code (N403)
        phone: Phone number (PER04)

        # Coverage tracking
        maintenance_type: 001=Change, 021=Add, 024=Cancel, 025=Reinstate (INS03)
        maintenance_reason_code: Maintenance reason (INS04)
        benefit_status_code: A=Active, C=COBRA, etc. (INS05)
        coverage_start_date: Coverage effective date
        coverage_end_date: Coverage termination date

        # Medicaid/Medicare Status
        has_medicare: Member has Medicare coverage
        has_medicaid: Member has Medicaid coverage
        dual_elgbl_cd: Dual eligibility status code ('00','01'-'08')
        is_full_benefit_dual: Full Benefit Dual (uses CFA_/CFD_ prefix)
        is_partial_benefit_dual: Partial Benefit Dual (uses CPA_/CPD_ prefix)
        medicare_status_code: QMB, SLMB, QI, QDWI, etc.
        medi_cal_aid_code: California Medi-Cal aid code
        medi_cal_eligibility_status: Medi-Cal eligibility status from REF*6O

        # CA DHCS / FAME Specific
        fame_county_id: FAME county ID (REF*ZX or N4*CY)
        case_number: Case number (REF*1L)
        fame_card_issue_date: FAME card issue date
        fame_redetermination_date: FAME redetermination date (REF*17)
        fame_death_date: FAME death date
        primary_aid_code: Primary AID code (REF*RB)
        carrier_code: Carrier code
        fed_contract_number: Federal contract number
        client_reporting_cat: Client reporting category
        res_addr_flag: Residential address flag from REF*6O
        reas_add_ind: Reason address indicator from REF*6O
        res_zip_deliv_code: Residential zip delivery code

        # Risk Adjustment Fields
        orec: Original Reason for Entitlement Code
        crec: Current Reason for Entitlement Code
        snp: Special Needs Plan enrollment
        low_income: Low Income Subsidy (Part D)
        lti: Long-Term Institutionalized
        new_enrollee: New enrollee status (<= 3 months)

        # HCP (Health Care Plan) Info
        hcp_code: Current HCP code (HD04 first part)
        hcp_status: Current HCP status (HD04 second part)
        amount_qualifier: AMT qualifier code (e.g., 'D' = premium, 'C1' = copay)
        amount: Premium or cost share amount (numeric)

        # HCP History (multiple coverage periods)
        hcp_history: List of historical HCP coverage periods
    """
    # Header Info
    source: Optional[str] = None
    report_date: Optional[str] = None

    # Identifiers
    member_id: Optional[str] = None
    mbi: Optional[str] = None
    medicaid_id: Optional[str] = None
    hic: Optional[str] = None
    cin: Optional[str] = None
    cin_check_digit: Optional[str] = None

    # Name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

    # Demographics
    dob: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    race: Optional[str] = None
    language: Optional[str] = None
    death_date: Optional[str] = None

    # Address
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None

    # Coverage tracking
    maintenance_type: Optional[str] = None
    maintenance_reason_code: Optional[str] = None
    benefit_status_code: Optional[str] = None
    coverage_start_date: Optional[str] = None
    coverage_end_date: Optional[str] = None

    # Medicaid/Medicare Status
    has_medicare: bool = False
    has_medicaid: bool = False
    dual_elgbl_cd: Optional[str] = None
    is_full_benefit_dual: bool = False
    is_partial_benefit_dual: bool = False
    medicare_status_code: Optional[str] = None
    medi_cal_aid_code: Optional[str] = None
    medi_cal_eligibility_status: Optional[str] = None

    # CA DHCS / FAME Specific
    fame_county_id: Optional[str] = None
    case_number: Optional[str] = None
    fame_card_issue_date: Optional[str] = None
    fame_redetermination_date: Optional[str] = None
    fame_death_date: Optional[str] = None
    primary_aid_code: Optional[str] = None
    carrier_code: Optional[str] = None
    fed_contract_number: Optional[str] = None
    client_reporting_cat: Optional[str] = None
    res_addr_flag: Optional[str] = None
    reas_add_ind: Optional[str] = None
    res_zip_deliv_code: Optional[str] = None

    # Risk Adjustment Fields
    orec: Optional[str] = None
    crec: Optional[str] = None
    snp: bool = False
    low_income: bool = False
    lti: bool = False
    new_enrollee: bool = False

    # HCP Info
    hcp_code: Optional[str] = None
    hcp_status: Optional[str] = None
    amount_qualifier: Optional[str] = None
    amount: Optional[float] = None

    # HCP History
    hcp_history: List[HCPCoveragePeriod] = []