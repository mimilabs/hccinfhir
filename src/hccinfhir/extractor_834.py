"""
X12 834 Benefit Enrollment Parser for California DHCS Medi-Cal

Extracts enrollment and demographic data from 834 transactions with focus on:
- Risk adjustment fields (dual eligibility, OREC/CREC, SNP, LTI)
- CA DHCS FAME-specific fields
- HCP (Health Care Plan) coverage history
"""

from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
from datetime import datetime, date
from hccinfhir.datamodels import Demographics, EnrollmentData, HCPCoveragePeriod
from hccinfhir.constants import (
    VALID_DUAL_CODES,
    FULL_BENEFIT_DUAL_CODES,
    PARTIAL_BENEFIT_DUAL_CODES,
    VALID_CREC_VALUES,
    X12_SEX_CODE_MAPPING,
    NON_DUAL_CODE,
    map_medicare_status_to_dual_code,
    map_aid_code_to_dual_status,
)

# Constants
TRANSACTION_TYPES = {"005010X220A1": "834"}

LANGUAGE_CODES = {
    'SPA': 'Spanish', 'ENG': 'English', 'CHI': 'Chinese', 'VIE': 'Vietnamese',
    'KOR': 'Korean', 'TAG': 'Tagalog', 'ARM': 'Armenian', 'FAR': 'Farsi',
    'ARA': 'Arabic', 'RUS': 'Russian', 'JPN': 'Japanese', 'HIN': 'Hindi',
    'CAM': 'Cambodian', 'HMO': 'Hmong', 'LAO': 'Lao', 'THA': 'Thai',
}

MEDICARE_KEYWORDS = {'MEDICARE', 'MA', 'PART A', 'PART B', 'PART C', 'PART D', 'MEDICARE ADVANTAGE', 'MA-PD'}
MEDICAID_KEYWORDS = {'MEDICAID', 'MEDI-CAL', 'MEDI CAL', 'MEDIC-AID', 'LTC'}
SNP_KEYWORDS = {'SNP', 'SPECIAL NEEDS', 'D-SNP', 'DSNP', 'DUAL ELIGIBLE SNP'}
LTI_KEYWORDS = {'LTC', 'LONG TERM CARE', 'LONG-TERM CARE', 'NURSING HOME', 'SKILLED NURSING', 'SNF', 'INSTITUTIONALIZED'}


class HCPContext(BaseModel):
    """Single HD loop (HCP coverage period)"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    hcp_code: Optional[str] = None
    hcp_status: Optional[str] = None
    aid_codes: Optional[str] = None


class MemberContext(BaseModel):
    """Tracks member-level data across segments within 834 transaction"""
    # Identifiers
    member_id: Optional[str] = None
    mbi: Optional[str] = None
    medicaid_id: Optional[str] = None
    hic: Optional[str] = None

    # Name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

    # Demographics
    dob: Optional[str] = None
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

    # Coverage Status
    maintenance_type: Optional[str] = None
    maintenance_reason_code: Optional[str] = None
    benefit_status_code: Optional[str] = None
    coverage_start_date: Optional[str] = None
    coverage_end_date: Optional[str] = None

    # Medicare/Medicaid Status
    has_medicare: bool = False
    has_medicaid: bool = False
    medicare_status_code: Optional[str] = None
    medi_cal_aid_code: Optional[str] = None
    dual_elgbl_cd: Optional[str] = None

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
    cin_check_digit: Optional[str] = None

    # Risk Adjustment Fields
    orec: Optional[str] = None
    crec: Optional[str] = None
    snp: bool = False
    low_income: bool = False
    lti: bool = False

    # HCP Info
    hcp_code: Optional[str] = None
    hcp_status: Optional[str] = None
    amount: Optional[str] = None

    # HCP History
    hcp_history: List[HCPContext] = []
    current_hcp: Optional[HCPContext] = None


# ============================================================================
# Utility Functions
# ============================================================================

def get_segment_value(segment: List[str], index: int, default: Optional[str] = None) -> Optional[str]:
    """Safely get value from segment at given index"""
    if len(segment) > index and segment[index]:
        return segment[index]
    return default


def parse_date(date_str: str) -> Optional[str]:
    """Convert 8-digit date string (YYYYMMDD) to ISO format (YYYY-MM-DD)"""
    if not date_str or len(date_str) < 8:
        return None
    try:
        year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
        if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        pass
    return None


def parse_yymmdd(date_str: str) -> Optional[str]:
    """Convert 6-digit date (YYMMDD) to ISO format"""
    if not date_str or len(date_str) < 6:
        return None
    try:
        yy = int(date_str[:2])
        year = 2000 + yy if yy < 50 else 1900 + yy
        return f"{year}-{date_str[2:4]}-{date_str[4:6]}"
    except (ValueError, IndexError):
        return None


def strip_leading_zeros(value: str) -> str:
    """Strip leading zeros but keep at least one character"""
    return value.lstrip('0') or value


def get_composite_part(value: str, index: int) -> Optional[str]:
    """Get part from semicolon-delimited composite value (0-indexed)"""
    if not value:
        return None
    parts = value.split(';')
    if len(parts) > index and parts[index]:
        return parts[index]
    return None


def calculate_age(dob: str, reference_date: Optional[str] = None) -> Optional[int]:
    """Calculate age from DOB in YYYY-MM-DD format"""
    if not dob:
        return None
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else date.today()
        age = ref_date.year - birth_date.year
        if (ref_date.month, ref_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    except (ValueError, AttributeError):
        return None


def is_new_enrollee(coverage_start_date: Optional[str], reference_date: Optional[str] = None) -> bool:
    """Determine if member is new enrollee (<= 3 months since coverage start)"""
    if not coverage_start_date:
        return False
    try:
        start_date = datetime.strptime(coverage_start_date, "%Y-%m-%d").date()
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else date.today()
        months_diff = (ref_date.year - start_date.year) * 12 + (ref_date.month - start_date.month)
        return months_diff <= 3
    except (ValueError, AttributeError):
        return False


def contains_any_keyword(text: str, keywords: set) -> bool:
    """Check if text contains any of the keywords"""
    text_upper = text.upper()
    return any(kw in text_upper for kw in keywords)


# ============================================================================
# Dual Eligibility Logic
# ============================================================================

def determine_dual_status(member: MemberContext) -> str:
    """Derive dual eligibility code from available data

    Priority: explicit code > aid code mapping > medicare status > both coverages > default
    """
    if member.dual_elgbl_cd in VALID_DUAL_CODES:
        return member.dual_elgbl_cd

    if member.medi_cal_aid_code:
        dual_code = map_aid_code_to_dual_status(member.medi_cal_aid_code)
        if dual_code != NON_DUAL_CODE:
            return dual_code

    if member.medicare_status_code:
        dual_code = map_medicare_status_to_dual_code(member.medicare_status_code)
        if dual_code != NON_DUAL_CODE:
            return dual_code

    if member.has_medicare and (member.has_medicaid or member.medicaid_id):
        return '08'  # Other Full Dual

    return NON_DUAL_CODE


def classify_dual_benefit_level(dual_code: str) -> Tuple[bool, bool]:
    """Return (is_full_benefit_dual, is_partial_benefit_dual)"""
    return dual_code in FULL_BENEFIT_DUAL_CODES, dual_code in PARTIAL_BENEFIT_DUAL_CODES


# ============================================================================
# REF Segment Parsers (CA DHCS specific composites)
# ============================================================================

def parse_ref_23(value: str, member: MemberContext) -> None:
    """REF*23: Cin_Check_Digit;Fame_Card_Issue_Date;;..."""
    member.cin_check_digit = get_composite_part(value, 0)
    card_date = get_composite_part(value, 1)
    if card_date and len(card_date) >= 8:
        member.fame_card_issue_date = card_date[:8]


def parse_ref_3h(value: str, member: MemberContext) -> None:
    """REF*3H: County;AID_Code;Case_Number;;..."""
    member.fame_county_id = get_composite_part(value, 0)
    aid_code = get_composite_part(value, 1)
    if aid_code and not member.medi_cal_aid_code:
        member.medi_cal_aid_code = aid_code
    member.case_number = get_composite_part(value, 2)


def parse_ref_6o(value: str, member: MemberContext) -> None:
    """REF*6O: ?;RES-ADDR-FLAG;REAS-ADD-IND;?;RES-ZIP-DELIV-CODE;?"""
    member.res_addr_flag = get_composite_part(value, 1)
    member.reas_add_ind = get_composite_part(value, 2)
    zip_code = get_composite_part(value, 4)
    if zip_code:
        member.res_zip_deliv_code = strip_leading_zeros(zip_code)


def parse_ref_dx(value: str, member: MemberContext) -> None:
    """REF*DX: Fed_Contract_Number;Carrier_Code;Policy_Start;..."""
    member.fed_contract_number = get_composite_part(value, 0)
    carrier = get_composite_part(value, 1)
    if carrier:
        member.carrier_code = strip_leading_zeros(carrier)
    policy_start = get_composite_part(value, 2)
    if policy_start and len(policy_start) >= 8:
        member.coverage_start_date = policy_start[:8]


def parse_ref_17(value: str, member: MemberContext) -> None:
    """REF*17: YYYYMM;;... (FAME redetermination date)"""
    yyyymm = get_composite_part(value, 0)
    if yyyymm and len(yyyymm) >= 6:
        member.fame_redetermination_date = f"{yyyymm[:4]}-{yyyymm[4:6]}-01"


# ============================================================================
# Public API Functions
# ============================================================================

def enrollment_to_demographics(enrollment: EnrollmentData) -> Demographics:
    """Convert EnrollmentData to Demographics model for risk calculation"""
    return Demographics(
        age=enrollment.age or 0,
        sex=enrollment.sex or 'M',
        dual_elgbl_cd=enrollment.dual_elgbl_cd,
        orec=enrollment.orec or '',
        crec=enrollment.crec or '',
        new_enrollee=enrollment.new_enrollee,
        snp=enrollment.snp,
        low_income=enrollment.low_income,
        lti=enrollment.lti
    )


def is_losing_medicaid(enrollment: EnrollmentData, within_days: int = 90) -> bool:
    """Check if member will lose Medicaid within specified days"""
    if not enrollment.coverage_end_date or not enrollment.has_medicaid:
        return False
    try:
        end_date = datetime.strptime(enrollment.coverage_end_date, "%Y-%m-%d").date()
        days_until_end = (end_date - date.today()).days
        return 0 <= days_until_end <= within_days
    except (ValueError, AttributeError):
        return False


def is_medicaid_terminated(enrollment: EnrollmentData) -> bool:
    """Check if Medicaid coverage is being terminated (maintenance type 024)"""
    return enrollment.maintenance_type == '024'


def medicaid_status_summary(enrollment: EnrollmentData) -> Dict:
    """Get summary of Medicaid coverage status for monitoring"""
    return {
        'member_id': enrollment.member_id,
        'has_medicaid': enrollment.has_medicaid,
        'has_medicare': enrollment.has_medicare,
        'dual_status': enrollment.dual_elgbl_cd,
        'is_full_benefit_dual': enrollment.is_full_benefit_dual,
        'is_partial_benefit_dual': enrollment.is_partial_benefit_dual,
        'coverage_end_date': enrollment.coverage_end_date,
        'is_termination': is_medicaid_terminated(enrollment),
        'losing_medicaid_30d': is_losing_medicaid(enrollment, 30),
        'losing_medicaid_60d': is_losing_medicaid(enrollment, 60),
        'losing_medicaid_90d': is_losing_medicaid(enrollment, 90)
    }


# ============================================================================
# Main Parsing Logic
# ============================================================================

def _process_ref_segment(qualifier: str, value: str, member: MemberContext, in_hd_loop: bool) -> None:
    """Process REF segment based on qualifier"""
    # HD-loop specific
    if in_hd_loop and member.current_hcp and qualifier == 'CE':
        member.current_hcp.aid_codes = value
        # Also set primary_aid_code from position 0 if not already set
        if not member.primary_aid_code:
            member.primary_aid_code = get_composite_part(value, 0)
        return

    # Member identifiers
    if qualifier == '0F' and not member.member_id:
        member.member_id = value
    elif qualifier == 'ZZ' and not member.member_id:
        member.member_id = value
    elif qualifier == '6P':
        member.mbi = value
        member.has_medicare = True
    elif qualifier == 'F6':
        member.hic = value
        if not member.mbi:
            member.mbi = value
        member.has_medicare = True
    elif qualifier == '1D':
        parts = [p for p in value.split(';') if p]
        member.medicaid_id = parts[-1] if parts else value
        member.has_medicaid = True
    elif qualifier == '23':
        parse_ref_23(value, member)
        member.has_medicaid = True
    # California Medi-Cal
    elif qualifier == 'ABB':
        member.medicare_status_code = value
    elif qualifier == 'AB':
        member.medi_cal_aid_code = value
    # CA DHCS custom
    elif qualifier == '3H':
        parse_ref_3h(value, member)
    elif qualifier == '6O':
        parse_ref_6o(value, member)
    elif qualifier == 'RB':
        member.primary_aid_code = value
    elif qualifier == 'CE' and not member.primary_aid_code:
        # Fallback: get primary_aid_code from REF*CE position 0 if not set by REF*RB
        member.primary_aid_code = get_composite_part(value, 0)
    elif qualifier == 'ZX' and not member.fame_county_id:
        member.fame_county_id = value
    elif qualifier == '17':
        if in_hd_loop:
            member.client_reporting_cat = value
        else:
            parse_ref_17(value, member)
    elif qualifier == 'DX':
        parse_ref_dx(value, member)
    # Dual eligibility
    elif qualifier == 'F5' and value in VALID_DUAL_CODES:
        member.dual_elgbl_cd = value
    elif qualifier == 'DY' and value in VALID_CREC_VALUES:
        member.crec = value
    elif qualifier == 'EJ':
        member.low_income = value.upper() in ('Y', 'YES', '1', 'TRUE')


def _process_hd_segment(segment: List[str], member: MemberContext) -> None:
    """Process HD (Health Coverage) segment"""
    # Save previous HCP context
    if member.current_hcp:
        member.hcp_history.append(member.current_hcp)

    member.current_hcp = HCPContext()

    # Parse HCP code and status from HD04
    plan_desc = get_segment_value(segment, 4, '')
    if plan_desc and ';' in plan_desc:
        parts = plan_desc.split(';')
        if parts[0]:
            hcp_code = strip_leading_zeros(parts[0])
            member.current_hcp.hcp_code = hcp_code
            if not member.hcp_code:
                member.hcp_code = hcp_code
        if len(parts) > 1 and parts[1]:
            hcp_status = strip_leading_zeros(parts[1])
            member.current_hcp.hcp_status = hcp_status
            if not member.hcp_status:
                member.hcp_status = hcp_status

    # Detect coverage types from combined fields
    insurance_line = get_segment_value(segment, 3, '')
    insurance_type = get_segment_value(segment, 6, '')
    combined = f"{insurance_line} {plan_desc} {insurance_type}"

    if contains_any_keyword(combined, MEDICARE_KEYWORDS):
        member.has_medicare = True
    if contains_any_keyword(combined, MEDICAID_KEYWORDS):
        member.has_medicaid = True
    if contains_any_keyword(combined, SNP_KEYWORDS):
        member.snp = True
        if any(kw in combined.upper() for kw in ('D-SNP', 'DSNP', 'DUAL')):
            member.has_medicare = True
            member.has_medicaid = True
    if contains_any_keyword(combined, LTI_KEYWORDS):
        member.lti = True


def _finalize_member(member: MemberContext, source: str, report_date: str) -> EnrollmentData:
    """Convert MemberContext to EnrollmentData"""
    if member.current_hcp:
        member.hcp_history.append(member.current_hcp)
        member.current_hcp = None

    age = calculate_age(member.dob)
    dual_code = determine_dual_status(member)
    is_fbd, is_pbd = classify_dual_benefit_level(dual_code)
    new_enrollee = is_new_enrollee(member.coverage_start_date)

    hcp_history = [
        HCPCoveragePeriod(
            start_date=hcp.start_date, end_date=hcp.end_date,
            hcp_code=hcp.hcp_code, hcp_status=hcp.hcp_status, aid_codes=hcp.aid_codes
        )
        for hcp in member.hcp_history
    ]

    return EnrollmentData(
        source=source, report_date=report_date,
        member_id=member.member_id, mbi=member.mbi, medicaid_id=member.medicaid_id,
        hic=member.hic, cin_check_digit=member.cin_check_digit,
        first_name=member.first_name, last_name=member.last_name, middle_name=member.middle_name,
        dob=member.dob, age=age, sex=member.sex, race=member.race,
        language=member.language, death_date=member.death_date,
        address_1=member.address_1, address_2=member.address_2,
        city=member.city, state=member.state, zip=member.zip, phone=member.phone,
        maintenance_type=member.maintenance_type,
        maintenance_reason_code=member.maintenance_reason_code,
        benefit_status_code=member.benefit_status_code,
        coverage_start_date=member.coverage_start_date,
        coverage_end_date=member.coverage_end_date,
        has_medicare=member.has_medicare, has_medicaid=member.has_medicaid,
        dual_elgbl_cd=dual_code, is_full_benefit_dual=is_fbd, is_partial_benefit_dual=is_pbd,
        medicare_status_code=member.medicare_status_code,
        medi_cal_aid_code=member.medi_cal_aid_code,
        fame_county_id=member.fame_county_id, case_number=member.case_number,
        fame_card_issue_date=member.fame_card_issue_date,
        fame_redetermination_date=member.fame_redetermination_date,
        fame_death_date=member.fame_death_date, primary_aid_code=member.primary_aid_code,
        carrier_code=member.carrier_code, fed_contract_number=member.fed_contract_number,
        client_reporting_cat=member.client_reporting_cat,
        res_addr_flag=member.res_addr_flag, reas_add_ind=member.reas_add_ind,
        res_zip_deliv_code=member.res_zip_deliv_code,
        orec=member.orec, crec=member.crec, snp=member.snp,
        low_income=member.low_income, lti=member.lti, new_enrollee=new_enrollee,
        hcp_code=member.hcp_code, hcp_status=member.hcp_status, amount=member.amount,
        hcp_history=hcp_history
    )


def parse_834_enrollment(segments: List[List[str]], source: str = None, report_date: str = None) -> List[EnrollmentData]:
    """Extract enrollment data from 834 transaction segments"""
    enrollments = []
    member = MemberContext()
    in_hd_loop = False

    for segment in segments:
        if len(segment) < 2:
            continue

        seg_id = segment[0]

        # BGN - Source identifier
        if seg_id == 'BGN' and len(segment) >= 3:
            bgn_ref = get_segment_value(segment, 2)
            if bgn_ref and '-' in bgn_ref:
                parts = bgn_ref.split('-')
                if len(parts) >= 2:
                    source = f"{parts[0]}-{parts[1]}"
                    if 'south la' in bgn_ref.lower():
                        source = f"SLA-{source}"

        # N1*IN - Plan name (for SLA prefix)
        elif seg_id == 'N1' and get_segment_value(segment, 1) == 'IN':
            plan_name = get_segment_value(segment, 2, '')
            if 'South LA' in plan_name and source and not source.startswith('SLA-'):
                source = f"SLA-{source}"

        # INS - Start of member loop
        elif seg_id == 'INS' and len(segment) >= 3:
            if member.member_id or member.has_medicare or member.has_medicaid:
                enrollments.append(_finalize_member(member, source, report_date))
            member = MemberContext()
            in_hd_loop = False
            member.maintenance_type = get_segment_value(segment, 3)
            member.maintenance_reason_code = get_segment_value(segment, 4)
            member.benefit_status_code = get_segment_value(segment, 5)

        # REF - Reference identifiers
        elif seg_id == 'REF' and len(segment) >= 3:
            value = get_segment_value(segment, 2)
            if value:
                _process_ref_segment(segment[1], value, member, in_hd_loop)

        # NM1*IL - Member name
        elif seg_id == 'NM1' and get_segment_value(segment, 1) == 'IL':
            member.last_name = get_segment_value(segment, 3)
            member.first_name = get_segment_value(segment, 4)
            member.middle_name = get_segment_value(segment, 5)
            if len(segment) > 9:
                id_val = get_segment_value(segment, 9)
                if id_val and not member.member_id:
                    member.member_id = id_val

        # PER - Contact (phone)
        elif seg_id == 'PER':
            for i, val in enumerate(segment):
                if val == 'TE' and i + 1 < len(segment):
                    member.phone = segment[i + 1]
                    break

        # N3 - Address
        elif seg_id == 'N3':
            member.address_1 = get_segment_value(segment, 1)
            member.address_2 = get_segment_value(segment, 2)

        # N4 - City/State/Zip
        elif seg_id == 'N4' and len(segment) >= 4:
            city = get_segment_value(segment, 1)
            state = get_segment_value(segment, 2)
            # Strip state suffix from city if embedded
            if city and state and city.upper().endswith(' ' + state.upper()):
                city = city[:-len(state)-1].strip()
            member.city = city.lower() if city else None
            member.state = state.lower() if state else None
            member.zip = get_segment_value(segment, 3)
            # County code
            if len(segment) > 6 and segment[5] == 'CY' and not member.fame_county_id:
                member.fame_county_id = get_segment_value(segment, 6)

        # LUI - Language
        elif seg_id == 'LUI' and len(segment) >= 3:
            lang_code = get_segment_value(segment, 2)
            if lang_code:
                member.language = LANGUAGE_CODES.get(lang_code.upper(), lang_code)

        # DMG - Demographics
        elif seg_id == 'DMG' and len(segment) >= 3:
            dob_str = get_segment_value(segment, 2)
            if dob_str:
                member.dob = parse_date(dob_str)
            sex = get_segment_value(segment, 3)
            if sex in X12_SEX_CODE_MAPPING:
                member.sex = X12_SEX_CODE_MAPPING[sex]
            member.race = get_segment_value(segment, 5)
            death_str = get_segment_value(segment, 6)
            if death_str and len(death_str) >= 8:
                member.death_date = parse_date(death_str[:8])

        # DTP - Dates
        elif seg_id == 'DTP' and len(segment) >= 4:
            qualifier = segment[1]
            fmt = segment[2]
            date_val = get_segment_value(segment, 3)
            if date_val and fmt.endswith('D8'):
                parsed = parse_date(date_val[:8] if len(date_val) >= 8 else date_val)
                if parsed:
                    if in_hd_loop and member.current_hcp:
                        if qualifier == '348':
                            member.current_hcp.start_date = parsed
                            # Also set member-level coverage_start_date
                            if not member.coverage_start_date:
                                member.coverage_start_date = parsed
                        elif qualifier == '349':
                            member.current_hcp.end_date = parsed
                            # Also set member-level coverage_end_date
                            if not member.coverage_end_date:
                                member.coverage_end_date = parsed
                    else:
                        if qualifier == '348' and not member.coverage_start_date:
                            member.coverage_start_date = parsed
                        elif qualifier == '349' and not member.coverage_end_date:
                            member.coverage_end_date = parsed
                        elif qualifier == '338':
                            if not member.coverage_start_date:
                                member.coverage_start_date = parsed
                            member.has_medicare = True
                        elif qualifier == '435':
                            member.death_date = parsed
                            member.fame_death_date = parsed

        # HD - Health coverage
        elif seg_id == 'HD' and len(segment) >= 4:
            _process_hd_segment(segment, member)
            in_hd_loop = True

        # AMT - Amount
        elif seg_id == 'AMT' and len(segment) >= 3:
            member.amount = get_segment_value(segment, 2)

    # Finalize last member
    if member.member_id or member.has_medicare or member.has_medicaid:
        enrollments.append(_finalize_member(member, source, report_date))

    return enrollments


def extract_enrollment_834(content: str) -> List[EnrollmentData]:
    """Main entry point for 834 parsing

    Args:
        content: Raw X12 834 transaction file content

    Returns:
        List of EnrollmentData objects

    Raises:
        ValueError: If content is empty or invalid format
    """
    if not content:
        raise ValueError("Input X12 834 data cannot be empty")

    segments = [seg.strip().split('*') for seg in content.split('~') if seg.strip()]
    if not segments:
        raise ValueError("No valid segments found in 834 data")

    # Validate 834 structure - must have ISA or ST*834 segment
    segment_ids = {seg[0] for seg in segments if seg}
    has_isa = 'ISA' in segment_ids
    has_st_834 = any(
        seg[0] == 'ST' and len(seg) > 1 and seg[1] == '834'
        for seg in segments
    )
    if not has_isa and not has_st_834:
        raise ValueError("Invalid or unsupported 834 format")

    # Extract header info
    source = None
    report_date = None

    for segment in segments:
        seg_id = segment[0]

        if seg_id == 'ISA' and len(segment) > 9:
            source = get_segment_value(segment, 6)
            if source:
                source = source.strip()
            isa_date = get_segment_value(segment, 9)
            if isa_date:
                report_date = parse_yymmdd(isa_date)

        elif seg_id == 'GS' and len(segment) > 4:
            if not source:
                source = get_segment_value(segment, 2)
            gs_date = get_segment_value(segment, 4)
            if gs_date and len(gs_date) >= 8:
                report_date = f"{gs_date[:4]}-{gs_date[4:6]}-{gs_date[6:8]}"
            if len(segment) > 8 and segment[8] not in TRANSACTION_TYPES:
                raise ValueError("Invalid or unsupported 834 format")
            break

    return parse_834_enrollment(segments, source, report_date)
