from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime, date
from hccinfhir.datamodels import Demographics, EnrollmentData

TRANSACTION_TYPES = {
    "005010X220A1": "834",  # Benefit Enrollment and Maintenance
}

# California Medi-Cal Aid Codes mapping to dual eligibility status
MEDI_CAL_AID_CODES = {
    # Full Benefit Dual (QMB Plus, SLMB Plus)
    '4N': '02',  # QMB Plus - Aged
    '4P': '02',  # QMB Plus - Disabled
    '5B': '04',  # SLMB Plus - Aged
    '5D': '04',  # SLMB Plus - Disabled

    # Partial Benefit Dual (QMB Only, SLMB Only, QI)
    '4M': '01',  # QMB Only - Aged
    '4O': '01',  # QMB Only - Disabled
    '5A': '03',  # SLMB Only - Aged
    '5C': '03',  # SLMB Only - Disabled
    '5E': '06',  # QI - Aged
    '5F': '06',  # QI - Disabled
}

class MemberContext(BaseModel):
    """Tracks member-level data across segments within 834 transaction"""
    # Identifiers
    member_id: Optional[str] = None
    mbi: Optional[str] = None  # Medicare Beneficiary Identifier
    medicaid_id: Optional[str] = None

    # Demographics
    dob: Optional[str] = None
    sex: Optional[str] = None

    # Coverage Status
    maintenance_type: Optional[str] = None  # 001=Change, 021=Add, 024=Cancel, 025=Reinstate
    coverage_start_date: Optional[str] = None
    coverage_end_date: Optional[str] = None

    # Medicare/Medicaid Status
    has_medicare: bool = False
    has_medicaid: bool = False
    medicare_status_code: Optional[str] = None  # QMB, SLMB, QI, etc.
    medi_cal_aid_code: Optional[str] = None
    dual_elgbl_cd: Optional[str] = None

    # Risk Adjustment Fields
    orec: Optional[str] = None
    crec: Optional[str] = None
    snp: bool = False
    low_income: bool = False
    lti: bool = False

# Helper methods for EnrollmentData - added as standalone functions
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
    """Check if member will lose Medicaid within specified days

    Args:
        enrollment: EnrollmentData object
        within_days: Number of days to look ahead (default 90)

    Returns:
        True if Medicaid coverage ends within specified days
    """
    if not enrollment.coverage_end_date or not enrollment.has_medicaid:
        return False

    try:
        end_date = datetime.strptime(enrollment.coverage_end_date, "%Y-%m-%d").date()
        today = date.today()
        days_until_end = (end_date - today).days

        return 0 <= days_until_end <= within_days
    except (ValueError, AttributeError):
        return False

def is_medicaid_terminated(enrollment: EnrollmentData) -> bool:
    """Check if Medicaid coverage is being terminated (maintenance type 024)"""
    return enrollment.maintenance_type == '024'

def medicaid_status_summary(enrollment: EnrollmentData) -> Dict[str, any]:
    """Get summary of Medicaid coverage status for monitoring

    Args:
        enrollment: EnrollmentData object

    Returns:
        Dictionary with Medicaid status, dual eligibility, and loss indicators
    """
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

def parse_date(date_str: str) -> Optional[str]:
    """Convert 8-digit date string to ISO format YYYY-MM-DD"""
    if not isinstance(date_str, str) or len(date_str) != 8:
        return None
    try:
        year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
        if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, IndexError):
        return None

def calculate_age(dob: str, reference_date: Optional[str] = None) -> Optional[int]:
    """Calculate age from DOB in YYYY-MM-DD format"""
    if not dob:
        return None
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
        if reference_date:
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        else:
            ref_date = date.today()

        age = ref_date.year - birth_date.year
        if (ref_date.month, ref_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    except (ValueError, AttributeError):
        return None

def get_segment_value(segment: List[str], index: int, default: Optional[str] = None) -> Optional[str]:
    """Safely get value from segment at given index"""
    try:
        if len(segment) > index and segment[index]:
            return segment[index]
    except (IndexError, TypeError):
        pass
    return default

def map_medicare_status_to_dual_code(status: Optional[str]) -> Optional[str]:
    """Map Medicare status codes to dual eligibility codes

    California Medi-Cal uses these status codes:
    - QMB = Qualified Medicare Beneficiary
    - QMBPLUS = QMB Plus (Full Benefit)
    - SLMB = Specified Low-Income Medicare Beneficiary
    - SLMBPLUS = SLMB Plus (Full Benefit)
    - QI = Qualifying Individual
    - QDWI = Qualified Disabled Working Individual
    """
    if not status:
        return None

    status_upper = status.upper().replace(' ', '').replace('-', '')

    mapping = {
        'QMB': '01',         # QMB Only (Partial)
        'QMBONLY': '01',
        'QMBPLUS': '02',     # QMB Plus (Full Benefit)
        'QMB+': '02',
        'SLMB': '03',        # SLMB Only (Partial)
        'SLMBONLY': '03',
        'SLMBPLUS': '04',    # SLMB Plus (Full Benefit)
        'SLMB+': '04',
        'QDWI': '05',
        'QI': '06',
        'QI1': '06',
        'FBDE': '08',        # Full Benefit Dual Eligible (Other)
        'OTHERFULL': '08',
    }

    return mapping.get(status_upper)

def map_aid_code_to_dual_status(aid_code: Optional[str]) -> Optional[str]:
    """Map California Medi-Cal aid code to dual eligibility status"""
    if not aid_code:
        return None
    return MEDI_CAL_AID_CODES.get(aid_code)

def determine_dual_status(member: MemberContext) -> str:
    """Intelligently derive dual eligibility code from available data

    Priority order:
    1. Explicit dual_elgbl_cd from REF segment
    2. California Medi-Cal aid code mapping
    3. Medicare status code (QMB, SLMB, etc.)
    4. Presence of both Medicare and Medicaid coverage
    5. Default to non-dual ('00')
    """
    # Priority 1: Explicit dual_elgbl_cd
    if member.dual_elgbl_cd and member.dual_elgbl_cd in ['01','02','03','04','05','06','08']:
        return member.dual_elgbl_cd

    # Priority 2: California aid code mapping
    if member.medi_cal_aid_code:
        dual_code = map_aid_code_to_dual_status(member.medi_cal_aid_code)
        if dual_code:
            return dual_code

    # Priority 3: Medicare status code
    if member.medicare_status_code:
        dual_code = map_medicare_status_to_dual_code(member.medicare_status_code)
        if dual_code:
            return dual_code

    # Priority 4: Both Medicare and Medicaid coverage present
    if member.has_medicare and (member.has_medicaid or member.medicaid_id):
        # Conservative: assign '08' (Other Full Dual) to ensure dual coefficients
        return '08'

    # Default: Non-dual
    return '00'

def classify_dual_benefit_level(dual_code: str) -> tuple[bool, bool]:
    """Classify as Full Benefit Dual (FBD) or Partial Benefit Dual (PBD)

    Full Benefit Dual codes: 02, 04, 08
    - Uses CFA_ (Community, Full Benefit Dual, Aged) prefix
    - Uses CFD_ (Community, Full Benefit Dual, Disabled) prefix

    Partial Benefit Dual codes: 01, 03, 05, 06
    - Uses CPA_ (Community, Partial Benefit Dual, Aged) prefix
    - Uses CPD_ (Community, Partial Benefit Dual, Disabled) prefix
    """
    full_benefit_codes = {'02', '04', '08'}
    partial_benefit_codes = {'01', '03', '05', '06'}

    is_fbd = dual_code in full_benefit_codes
    is_pbd = dual_code in partial_benefit_codes

    return is_fbd, is_pbd

def is_new_enrollee(coverage_start_date: Optional[str], reference_date: Optional[str] = None) -> bool:
    """Determine if member is new enrollee (<= 3 months since coverage start)"""
    if not coverage_start_date:
        return False

    try:
        start_date = datetime.strptime(coverage_start_date, "%Y-%m-%d").date()
        if reference_date:
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        else:
            ref_date = date.today()

        # Calculate months difference
        months_diff = (ref_date.year - start_date.year) * 12 + (ref_date.month - start_date.month)

        return months_diff <= 3
    except (ValueError, AttributeError):
        return False

def parse_834_enrollment(segments: List[List[str]]) -> List[EnrollmentData]:
    """Extract enrollment and demographic data from 834 transaction

    California DHCS Medi-Cal 834 Structure:
    Loop 2000 - Member Level
        INS - Member Level Detail (subscriber/dependent, maintenance type)
        REF - Member Identifiers (0F, 1L, F6, 6P, ZZ, AB, ABB)
        DTP - Date Time Periods (303, 348, 349, 338)
        NM1 - Member Name (IL qualifier)
        DMG - Demographics (DOB, Sex) ***CRITICAL***
        HD  - Health Coverage ***CRITICAL FOR DUAL STATUS***
    """
    enrollments = []
    member = MemberContext()

    for i, segment in enumerate(segments):
        if len(segment) < 2:
            continue

        seg_id = segment[0]

        # ===== INS - Member Level Detail (Start of 2000 loop) =====
        if seg_id == 'INS' and len(segment) >= 3:
            # Save previous member before starting new one
            if member.member_id or member.has_medicare or member.has_medicaid:
                enrollments.append(create_enrollment_data(member))

            # Start new member
            member = MemberContext()

            # INS03 - Maintenance Type Code
            member.maintenance_type = get_segment_value(segment, 3)
            # 001=Change, 021=Addition, 024=Cancellation/Term, 025=Reinstatement

        # ===== REF - Reference Identifiers =====
        elif seg_id == 'REF' and len(segment) >= 3:
            qualifier = segment[1]
            value = segment[2] if len(segment) > 2 else None

            if not value:
                continue

            # Standard REF qualifiers
            if qualifier == '0F':  # Subscriber Number
                if not member.member_id:
                    member.member_id = value
            elif qualifier == 'ZZ':  # Mutually Defined (often member ID or MBI)
                if not member.member_id:
                    member.member_id = value

            # Medicare Identifiers
            elif qualifier == '6P':  # Medicare MBI (new identifier)
                member.mbi = value
                member.has_medicare = True
            elif qualifier == 'F6':  # Medicare HICN (legacy) or MBI
                if not member.mbi:
                    member.mbi = value
                member.has_medicare = True

            # Medicaid Identifiers
            elif qualifier == '1D':  # Medicaid/Recipient ID
                member.medicaid_id = value
                member.has_medicaid = True
            elif qualifier == '23':  # Medicaid Recipient ID (alternative)
                if not member.medicaid_id:
                    member.medicaid_id = value
                member.has_medicaid = True

            # California Medi-Cal Specific
            elif qualifier == 'ABB':  # Medicare Status Code (QMB, SLMB, QI, etc.)
                member.medicare_status_code = value
            elif qualifier == 'AB':  # Aid Code (California specific)
                member.medi_cal_aid_code = value

            # Custom dual eligibility indicators
            elif qualifier == 'F5':  # Dual Eligibility Code (custom)
                if value in ['01','02','03','04','05','06','08']:
                    member.dual_elgbl_cd = value
            elif qualifier == 'DX':  # OREC (custom)
                if value in ['0','1','2','3']:
                    member.orec = value
            elif qualifier == 'DY':  # CREC (custom)
                if value in ['0','1','2','3']:
                    member.crec = value
            elif qualifier == 'EJ':  # Low Income Subsidy indicator
                member.low_income = (value.upper() in ['Y', 'YES', '1', 'TRUE'])

        # ===== NM1 - Member Name =====
        elif seg_id == 'NM1' and len(segment) >= 4:
            qualifier = segment[1]

            if qualifier == 'IL':  # Insured or Subscriber
                # NM109 = Identification Code (Member ID)
                if len(segment) > 9:
                    id_value = get_segment_value(segment, 9)
                    if id_value and not member.member_id:
                        member.member_id = id_value

        # ===== DMG - Demographics ***CRITICAL SEGMENT*** =====
        elif seg_id == 'DMG' and len(segment) >= 3:
            # DMG02 = Date of Birth
            dob_str = get_segment_value(segment, 2)
            if dob_str:
                member.dob = parse_date(dob_str)

            # DMG03 = Gender Code
            sex = get_segment_value(segment, 3)
            if sex in ['M', 'F', '1', '2']:
                member.sex = 'M' if sex in ['M', '1'] else 'F'

        # ===== DTP - Date Time Periods =====
        elif seg_id == 'DTP' and len(segment) >= 4:
            date_qualifier = segment[1]
            date_format = segment[2]
            date_value = segment[3] if len(segment) > 3 else None

            if not date_value or not date_format.endswith('D8'):
                continue

            parsed_date = parse_date(date_value[:8] if len(date_value) >= 8 else date_value)

            if not parsed_date:
                continue

            # Date qualifiers
            if date_qualifier == '348':  # Benefit Begin Date
                member.coverage_start_date = parsed_date
            elif date_qualifier == '349':  # Benefit End Date
                member.coverage_end_date = parsed_date
            elif date_qualifier == '338':  # Medicare Part A/B Effective Date
                if not member.coverage_start_date:
                    member.coverage_start_date = parsed_date
                member.has_medicare = True

        # ===== HD - Health Coverage ***CRITICAL FOR DUAL STATUS*** =====
        elif seg_id == 'HD' and len(segment) >= 4:
            # HD03 = Insurance Line Code
            insurance_line = get_segment_value(segment, 3, '').upper()

            # HD04 = Plan Coverage Description
            plan_desc = get_segment_value(segment, 4, '').upper()

            # HD06 = Insurance Type Code
            insurance_type = get_segment_value(segment, 6, '').upper()

            # Combine all fields for pattern matching
            combined = f"{insurance_line} {plan_desc} {insurance_type}"

            # Detect Medicare coverage
            if any(keyword in combined for keyword in [
                'MEDICARE', 'MA', 'PART A', 'PART B', 'PART C', 'PART D',
                'MEDICARE ADVANTAGE', 'MA-PD'
            ]):
                member.has_medicare = True

            # Detect Medicaid/Medi-Cal coverage
            if any(keyword in combined for keyword in [
                'MEDICAID', 'MEDI-CAL', 'MEDI CAL', 'MEDIC-AID'
            ]):
                member.has_medicaid = True

            # Detect SNP (Special Needs Plan)
            if any(keyword in combined for keyword in [
                'SNP', 'SPECIAL NEEDS', 'D-SNP', 'DSNP', 'DUAL ELIGIBLE SNP'
            ]):
                member.snp = True
                # If it's a D-SNP, they are definitely dual eligible
                if 'D-SNP' in combined or 'DSNP' in combined or 'DUAL' in combined:
                    member.has_medicare = True
                    member.has_medicaid = True

    # Don't forget last member
    if member.member_id or member.has_medicare or member.has_medicaid:
        enrollments.append(create_enrollment_data(member))

    return enrollments

def create_enrollment_data(member: MemberContext) -> EnrollmentData:
    """Convert MemberContext to EnrollmentData with risk adjustment fields"""

    # Calculate age
    age = calculate_age(member.dob) if member.dob else None

    # Determine dual eligibility status
    dual_code = determine_dual_status(member)

    # Classify FBD vs PBD
    is_fbd, is_pbd = classify_dual_benefit_level(dual_code)

    # Determine new enrollee status
    new_enrollee = is_new_enrollee(member.coverage_start_date)

    return EnrollmentData(
        # Identifiers
        member_id=member.member_id,
        mbi=member.mbi,
        medicaid_id=member.medicaid_id,

        # Demographics
        dob=member.dob,
        age=age,
        sex=member.sex,

        # Coverage tracking
        maintenance_type=member.maintenance_type,
        coverage_start_date=member.coverage_start_date,
        coverage_end_date=member.coverage_end_date,

        # Dual Eligibility
        has_medicare=member.has_medicare,
        has_medicaid=member.has_medicaid,
        dual_elgbl_cd=dual_code,
        is_full_benefit_dual=is_fbd,
        is_partial_benefit_dual=is_pbd,
        medicare_status_code=member.medicare_status_code,
        medi_cal_aid_code=member.medi_cal_aid_code,

        # Risk Adjustment
        orec=member.orec,
        crec=member.crec,
        snp=member.snp,
        low_income=member.low_income,
        lti=member.lti,
        new_enrollee=new_enrollee
    )

def extract_enrollment_834(content: str) -> List[EnrollmentData]:
    """Main entry point for 834 parsing

    Args:
        content: Raw X12 834 transaction file content

    Returns:
        List of EnrollmentData objects with demographic and dual eligibility info

    Raises:
        ValueError: If content is empty or invalid 834 format
    """
    if not content:
        raise ValueError("Input X12 834 data cannot be empty")

    # Split content into segments
    segments = [seg.strip().split('*')
                for seg in content.split('~') if seg.strip()]

    if not segments:
        raise ValueError("No valid segments found in 834 data")

    # Validate transaction type from GS segment
    transaction_type = None
    for segment in segments:
        if segment[0] == 'GS' and len(segment) > 8:
            transaction_type = TRANSACTION_TYPES.get(segment[8])
            break

    if not transaction_type:
        raise ValueError("Invalid or unsupported 834 format (missing GS segment or wrong version)")

    return parse_834_enrollment(segments)
