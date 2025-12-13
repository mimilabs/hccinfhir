import pytest
from hccinfhir.extractor_834 import (
    extract_enrollment_834,
    enrollment_to_demographics,
    is_losing_medicaid,
    is_medicaid_terminated,
    medicaid_status_summary,
    parse_date,
    calculate_age,
    determine_dual_status,
    classify_dual_benefit_level,
    is_new_enrollee,
    MemberContext
)
from hccinfhir.constants import (
    map_medicare_status_to_dual_code,
    map_aid_code_to_dual_status,
    NON_DUAL_CODE
)
from hccinfhir.datamodels import EnrollmentData
from pathlib import Path

# Sample 834 test data
SAMPLE_834_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_01.txt"

def test_parse_date():
    """Test date parsing utility"""
    assert parse_date("20250108") == "2025-01-08"
    assert parse_date("19550315") == "1955-03-15"
    assert parse_date("invalid") is None
    assert parse_date("999999999") is None
    assert parse_date("") is None

def test_calculate_age():
    """Test age calculation"""
    # Test with reference date
    age = calculate_age("1955-03-15", "2025-01-08")
    assert age == 69

    age = calculate_age("1960-08-22", "2025-01-08")
    assert age == 64

    # Invalid date
    assert calculate_age("invalid") is None
    assert calculate_age(None) is None

def test_map_medicare_status_to_dual_code():
    """Test Medicare status code to dual eligibility mapping"""
    assert map_medicare_status_to_dual_code("QMB") == "01"
    assert map_medicare_status_to_dual_code("QMBPLUS") == "02"
    assert map_medicare_status_to_dual_code("QMB+") == "02"
    assert map_medicare_status_to_dual_code("SLMB") == "03"
    assert map_medicare_status_to_dual_code("SLMBPLUS") == "04"
    assert map_medicare_status_to_dual_code("SLMB+") == "04"
    assert map_medicare_status_to_dual_code("QI") == "06"
    assert map_medicare_status_to_dual_code("QDWI") == "05"
    assert map_medicare_status_to_dual_code("FBDE") == "08"
    assert map_medicare_status_to_dual_code("INVALID") == NON_DUAL_CODE  # Returns '00' for invalid
    assert map_medicare_status_to_dual_code(None) == NON_DUAL_CODE  # Returns '00' for None

def test_map_aid_code_to_dual_status():
    """Test California Medi-Cal aid code mapping"""
    # Full Benefit Dual codes
    assert map_aid_code_to_dual_status("4N") == "02"  # QMB Plus - Aged
    assert map_aid_code_to_dual_status("4P") == "02"  # QMB Plus - Disabled
    assert map_aid_code_to_dual_status("5B") == "04"  # SLMB Plus - Aged
    assert map_aid_code_to_dual_status("5D") == "04"  # SLMB Plus - Disabled

    # Partial Benefit Dual codes
    assert map_aid_code_to_dual_status("4M") == "01"  # QMB Only - Aged
    assert map_aid_code_to_dual_status("4O") == "01"  # QMB Only - Disabled
    assert map_aid_code_to_dual_status("5A") == "03"  # SLMB Only - Aged
    assert map_aid_code_to_dual_status("5C") == "03"  # SLMB Only - Disabled
    assert map_aid_code_to_dual_status("5E") == "06"  # QI - Aged
    assert map_aid_code_to_dual_status("5F") == "06"  # QI - Disabled

    assert map_aid_code_to_dual_status("XX") == NON_DUAL_CODE  # Returns '00' for invalid
    assert map_aid_code_to_dual_status(None) == NON_DUAL_CODE  # Returns '00' for None

def test_classify_dual_benefit_level():
    """Test Full vs Partial Benefit Dual classification"""
    # Full Benefit Dual
    is_fbd, is_pbd = classify_dual_benefit_level("02")
    assert is_fbd is True
    assert is_pbd is False

    is_fbd, is_pbd = classify_dual_benefit_level("04")
    assert is_fbd is True
    assert is_pbd is False

    is_fbd, is_pbd = classify_dual_benefit_level("08")
    assert is_fbd is True
    assert is_pbd is False

    # Partial Benefit Dual
    is_fbd, is_pbd = classify_dual_benefit_level("01")
    assert is_fbd is False
    assert is_pbd is True

    is_fbd, is_pbd = classify_dual_benefit_level("03")
    assert is_fbd is False
    assert is_pbd is True

    is_fbd, is_pbd = classify_dual_benefit_level("06")
    assert is_fbd is False
    assert is_pbd is True

    # Non-dual
    is_fbd, is_pbd = classify_dual_benefit_level("00")
    assert is_fbd is False
    assert is_pbd is False

def test_is_new_enrollee():
    """Test new enrollee detection"""
    # Coverage started 2 months ago
    assert is_new_enrollee("2024-11-08", "2025-01-08") is True

    # Coverage started 3 months ago
    assert is_new_enrollee("2024-10-08", "2025-01-08") is True

    # Coverage started 4 months ago
    assert is_new_enrollee("2024-09-08", "2025-01-08") is False

    # Coverage started 1 year ago
    assert is_new_enrollee("2024-01-08", "2025-01-08") is False

    # No coverage date
    assert is_new_enrollee(None) is False

def test_extract_enrollment_834_sample():
    """Test extraction from sample 834 file"""
    if not SAMPLE_834_PATH.exists():
        pytest.skip("Sample 834 file not found")

    with open(SAMPLE_834_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)

    # Should have 5 members
    assert len(enrollments) == 5

    # Test Member 1: Maria Garcia - QMB Plus (Full Benefit Dual), D-SNP
    member1 = enrollments[0]
    assert member1.member_id == "MBR001"
    assert member1.mbi == "1A23BC456D7"
    assert member1.medicaid_id == "MC123456789"
    assert member1.dob == "1955-03-15"
    assert member1.age >= 69  # Age depends on current date
    assert member1.sex == "F"
    assert member1.has_medicare is True
    assert member1.has_medicaid is True
    assert member1.dual_elgbl_cd == "02"  # QMB Plus
    assert member1.is_full_benefit_dual is True
    assert member1.is_partial_benefit_dual is False
    assert member1.medicare_status_code == "QMBPLUS"
    assert member1.snp is True  # D-SNP detected
    assert member1.maintenance_type == "021"  # Addition

    # Test Member 2: Robert Johnson - QMB Only (Partial Benefit Dual) via aid code
    member2 = enrollments[1]
    assert member2.member_id == "MBR002"
    assert member2.mbi == "2B34CD567E8"
    assert member2.medicaid_id == "MC987654321"
    assert member2.sex == "M"
    assert member2.has_medicare is True
    assert member2.has_medicaid is True
    assert member2.dual_elgbl_cd == "01"  # QMB Only (from aid code 4M)
    assert member2.is_full_benefit_dual is False
    assert member2.is_partial_benefit_dual is True
    assert member2.medi_cal_aid_code == "4M"
    assert member2.maintenance_type == "001"  # Change

    # Test Member 3: Carmen Rodriguez - SLMB Plus, Losing Medicaid
    member3 = enrollments[2]
    assert member3.member_id == "MBR003"
    assert member3.mbi == "3C45DE678F9"
    assert member3.medicaid_id == "MC555666777"
    assert member3.sex == "F"
    assert member3.has_medicare is True
    assert member3.has_medicaid is True
    assert member3.dual_elgbl_cd == "04"  # SLMB Plus
    assert member3.is_full_benefit_dual is True
    assert member3.coverage_end_date == "2025-02-28"  # Coverage ending
    assert member3.maintenance_type == "024"  # Cancellation/Termination

    # Test Member 4: Thanh Nguyen - Medi-Cal Only (No Medicare)
    member4 = enrollments[3]
    assert member4.member_id == "MBR004"
    assert member4.medicaid_id == "MC111222333"
    assert member4.mbi is None  # No Medicare
    assert member4.sex == "M"
    assert member4.has_medicare is False
    assert member4.has_medicaid is True
    assert member4.dual_elgbl_cd == "00"  # Non-dual
    assert member4.is_full_benefit_dual is False
    assert member4.is_partial_benefit_dual is False
    assert member4.maintenance_type == "021"  # Addition

    # Test Member 5: John Smith - Medicare Only, New Enrollee
    member5 = enrollments[4]
    assert member5.member_id == "MBR005"
    assert member5.mbi == "5E67FG890H1"
    assert member5.medicaid_id is None  # No Medicaid
    assert member5.sex == "M"
    assert member5.has_medicare is True
    assert member5.has_medicaid is False
    assert member5.dual_elgbl_cd == "00"  # Non-dual
    assert member5.new_enrollee is True  # Coverage started 2025-09-01 (within 3 months)
    assert member5.maintenance_type == "021"  # Addition

def test_is_losing_medicaid():
    """Test Medicaid loss detection"""
    from datetime import date, timedelta

    # Create test enrollment with end date 61 days in the future
    future_date = date.today() + timedelta(days=61)
    future_date_str = future_date.strftime("%Y-%m-%d")

    enrollment = EnrollmentData(
        member_id="TEST001",
        has_medicaid=True,
        coverage_end_date=future_date_str
    )

    assert is_losing_medicaid(enrollment, 90) is True  # Within 90 days
    assert is_losing_medicaid(enrollment, 60) is False  # Outside 60 days

    # No end date
    enrollment2 = EnrollmentData(
        member_id="TEST002",
        has_medicaid=True,
        coverage_end_date=None
    )
    assert is_losing_medicaid(enrollment2, 90) is False

def test_is_medicaid_terminated():
    """Test Medicaid termination detection"""
    # Termination
    enrollment = EnrollmentData(
        member_id="TEST001",
        maintenance_type="024"
    )
    assert is_medicaid_terminated(enrollment) is True

    # Not termination
    enrollment2 = EnrollmentData(
        member_id="TEST002",
        maintenance_type="021"
    )
    assert is_medicaid_terminated(enrollment2) is False

def test_medicaid_status_summary():
    """Test Medicaid status summary generation"""
    enrollment = EnrollmentData(
        member_id="TEST001",
        has_medicaid=True,
        has_medicare=True,
        dual_elgbl_cd="02",
        is_full_benefit_dual=True,
        coverage_end_date="2025-03-01",
        maintenance_type="024"
    )

    summary = medicaid_status_summary(enrollment)

    assert summary['member_id'] == "TEST001"
    assert summary['has_medicaid'] is True
    assert summary['has_medicare'] is True
    assert summary['dual_status'] == "02"
    assert summary['is_full_benefit_dual'] is True
    assert summary['coverage_end_date'] == "2025-03-01"
    assert summary['is_termination'] is True
    assert 'losing_medicaid_30d' in summary
    assert 'losing_medicaid_60d' in summary
    assert 'losing_medicaid_90d' in summary

def test_enrollment_to_demographics():
    """Test conversion to Demographics model"""
    enrollment = EnrollmentData(
        member_id="TEST001",
        age=72,
        sex="F",
        dual_elgbl_cd="02",
        orec="0",
        crec="0",
        new_enrollee=False,
        snp=True,
        low_income=True,
        lti=False
    )

    demographics = enrollment_to_demographics(enrollment)

    assert demographics.age == 72
    assert demographics.sex == "F"
    assert demographics.dual_elgbl_cd == "02"
    assert demographics.orec == "0"
    assert demographics.crec == "0"
    assert demographics.new_enrollee is False
    assert demographics.snp is True
    assert demographics.low_income is True
    assert demographics.lti is False

def test_extract_enrollment_834_invalid():
    """Test error handling for invalid 834 data"""
    # Empty content
    with pytest.raises(ValueError, match="cannot be empty"):
        extract_enrollment_834("")

    # Invalid format
    with pytest.raises(ValueError, match="Invalid or unsupported 834"):
        extract_enrollment_834("INVALID*DATA*HERE~")

def test_determine_dual_status_priority():
    """Test dual status determination priority logic"""
    # Priority 1: Explicit dual_elgbl_cd
    member = MemberContext(
        dual_elgbl_cd="02",
        medi_cal_aid_code="4M",  # Would give "01"
        medicare_status_code="QMB"  # Would give "01"
    )
    assert determine_dual_status(member) == "02"

    # Priority 2: Aid code
    member = MemberContext(
        medi_cal_aid_code="4M",  # Gives "01"
        medicare_status_code="QMBPLUS"  # Would give "02"
    )
    assert determine_dual_status(member) == "01"

    # Priority 3: Medicare status
    member = MemberContext(
        medicare_status_code="QMBPLUS"
    )
    assert determine_dual_status(member) == "02"

    # Priority 4: Both coverages present
    member = MemberContext(
        has_medicare=True,
        has_medicaid=True
    )
    assert determine_dual_status(member) == "08"  # Default to Other Full Dual

    # Default: Non-dual
    member = MemberContext()
    assert determine_dual_status(member) == "00"


# ============================================================================
# Tests for CA DHCS PACE Sample Files (sample_834_02 through sample_834_06)
# ============================================================================

SAMPLE_834_02_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_02.txt"
SAMPLE_834_03_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_03.txt"
SAMPLE_834_04_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_04.txt"
SAMPLE_834_05_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_05.txt"
SAMPLE_834_06_PATH = Path(__file__).parent.parent / "src" / "hccinfhir" / "sample_files" / "sample_834_06.txt"


def test_sample_834_02_ca_dhcs_pace():
    """Test CA DHCS PACE enrollment - basic fields"""
    if not SAMPLE_834_02_PATH.exists():
        pytest.skip("Sample 834_02 file not found")

    with open(SAMPLE_834_02_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)
    assert len(enrollments) == 1

    member = enrollments[0]

    # Source and report date
    assert member.source == "DHCS834-DA"
    assert member.report_date == "2025-01-24"

    # Member identifiers (randomized in sample)
    assert member.member_id == "randomParticipantID"

    # Demographics
    assert member.first_name == "randomFirstName"
    assert member.last_name == "randomLastName"
    assert member.middle_name == "A"
    assert member.sex == "F"

    # Address
    assert member.city == "los angeles"
    assert member.state == "ca"
    assert member.zip == "90019"

    # CA DHCS FAME specific fields
    assert member.fame_county_id == "19"  # LA County
    assert member.medi_cal_aid_code == "10"
    assert member.case_number == "randomCaseNum1"
    assert member.cin_check_digit == "4"
    assert member.fame_card_issue_date == "20200101"

    # REF*6O fields
    assert member.res_addr_flag == "W"
    assert member.reas_add_ind == "Y"
    assert member.res_zip_deliv_code == "60"

    # Maintenance codes
    assert member.maintenance_type == "001"
    assert member.maintenance_reason_code == "AI"
    assert member.benefit_status_code == "A"

    # HCP history
    assert len(member.hcp_history) >= 1
    hcp = member.hcp_history[0]
    assert hcp.start_date == "2025-01-01"
    assert hcp.end_date == "2025-01-31"

    # HCP code and status
    assert member.hcp_code == "10"
    assert member.hcp_status == "51"

    # Language
    assert member.language == "Spanish"


def test_sample_834_03_south_la_pace():
    """Test CA DHCS South LA PACE enrollment - SLA prefix"""
    if not SAMPLE_834_03_PATH.exists():
        pytest.skip("Sample 834_03 file not found")

    with open(SAMPLE_834_03_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)
    assert len(enrollments) == 1

    member = enrollments[0]

    # Source should have SLA prefix for South LA
    assert member.source == "SLA-DHCS834-DA"
    assert member.report_date == "2025-08-12"

    # CA DHCS fields
    assert member.fame_county_id == "19"
    assert member.medi_cal_aid_code == "60"
    assert member.case_number == "randomCaseNum2"
    assert member.cin_check_digit == "2"

    # REF*DX fields (contract info)
    assert member.fed_contract_number == "H9999"
    assert member.carrier_code == "6"
    assert member.coverage_start_date == "20250201"

    # HCP for PACE plan
    assert member.hcp_code == "957"
    assert member.hcp_status == "1"

    # HCP history dates
    assert len(member.hcp_history) >= 1
    assert member.hcp_history[0].start_date == "2025-08-01"
    assert member.hcp_history[0].end_date == "2025-08-31"


def test_sample_834_04_with_race_code():
    """Test CA DHCS enrollment with race code"""
    if not SAMPLE_834_04_PATH.exists():
        pytest.skip("Sample 834_04 file not found")

    with open(SAMPLE_834_04_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)
    assert len(enrollments) == 1

    member = enrollments[0]

    # Source with SLA prefix
    assert member.source == "SLA-DHCS834-DA"

    # Race code (raw format)
    assert member.race == ":RET:2054-5"  # Black/African American code

    # FAME redetermination date
    assert member.fame_redetermination_date == "2026-05-01"

    # Different aid code
    assert member.medi_cal_aid_code == "16"

    # Client reporting category
    assert member.client_reporting_cat is not None


def test_sample_834_05_with_amount():
    """Test CA DHCS enrollment with AMT segment"""
    if not SAMPLE_834_05_PATH.exists():
        pytest.skip("Sample 834_05 file not found")

    with open(SAMPLE_834_05_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)
    assert len(enrollments) == 1

    member = enrollments[0]

    # Source with SLA prefix
    assert member.source == "SLA-DHCS834-DA"

    # Amount field from AMT segment
    assert member.amount == "1237"

    # Race code (raw format)
    assert member.race == ":RET:2135-2"  # Hispanic code

    # HCP status with letter
    assert member.hcp_status == "P4"

    # Different aid code
    assert member.medi_cal_aid_code == "17"


def test_sample_834_06_multi_member():
    """Test CA DHCS enrollment with multiple members"""
    if not SAMPLE_834_06_PATH.exists():
        pytest.skip("Sample 834_06 file not found")

    with open(SAMPLE_834_06_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)

    # Should have 2 members
    assert len(enrollments) == 2

    # Member 1
    member1 = enrollments[0]
    assert member1.source == "DHCS834-DA"
    assert member1.member_id == "randomMemberId"
    assert member1.first_name == "randomFName1"
    assert member1.last_name == "randomLName1"
    assert member1.sex == "F"
    assert member1.medi_cal_aid_code == "60"
    assert member1.case_number == "randomCaseNum1"
    assert member1.race == ":RET:2054-5"

    # Member 2
    member2 = enrollments[1]
    assert member2.member_id == "randomMemberId2"
    assert member2.first_name == "randomFName2"
    assert member2.last_name == "randomLName2"
    assert member2.middle_name == "M"
    assert member2.sex == "M"
    assert member2.medi_cal_aid_code == "10"
    assert member2.case_number == "randomCaseNum2"
    assert member2.race == ":RET:2135-2"

    # Both should have same source and report date
    assert member1.source == member2.source
    assert member1.report_date == member2.report_date


def test_all_ca_dhcs_samples_parse():
    """Test that all CA DHCS sample files parse without errors"""
    sample_paths = [
        SAMPLE_834_02_PATH,
        SAMPLE_834_03_PATH,
        SAMPLE_834_04_PATH,
        SAMPLE_834_05_PATH,
        SAMPLE_834_06_PATH,
    ]

    for path in sample_paths:
        if not path.exists():
            pytest.skip(f"Sample file {path.name} not found")

        with open(path, 'r') as f:
            content = f.read()

        # Should not raise any exceptions
        enrollments = extract_enrollment_834(content)

        # Should have at least one enrollment
        assert len(enrollments) >= 1, f"No enrollments parsed from {path.name}"

        # Each enrollment should have basic required fields
        for e in enrollments:
            assert e.member_id is not None, f"member_id missing in {path.name}"
            assert e.source is not None, f"source missing in {path.name}"


def test_hcp_history_parsing():
    """Test that HCP history is correctly parsed from HD loops"""
    if not SAMPLE_834_06_PATH.exists():
        pytest.skip("Sample 834_06 file not found")

    with open(SAMPLE_834_06_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)

    # Member 1 should have HCP history
    member1 = enrollments[0]
    assert member1.hcp_history is not None
    assert len(member1.hcp_history) >= 1

    # Check HCP history entry
    hcp = member1.hcp_history[0]
    assert hcp.start_date is not None
    assert hcp.end_date is not None
    assert hcp.hcp_code is not None


def test_enrollment_to_demographics_ca_dhcs():
    """Test conversion to Demographics for CA DHCS enrollments"""
    if not SAMPLE_834_03_PATH.exists():
        pytest.skip("Sample 834_03 file not found")

    with open(SAMPLE_834_03_PATH, 'r') as f:
        content = f.read()

    enrollments = extract_enrollment_834(content)
    member = enrollments[0]

    # Convert to Demographics
    demographics = enrollment_to_demographics(member)

    # Should have basic demographics
    assert demographics.sex == "F"
    # dual_elgbl_cd should be set (even if "00" for non-dual)
    assert demographics.dual_elgbl_cd is not None
