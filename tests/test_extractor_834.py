import pytest
from hccinfhir.extractor_834 import (
    extract_enrollment_834,
    enrollment_to_demographics,
    is_losing_medicaid,
    is_medicaid_terminated,
    medicaid_status_summary,
    parse_date,
    calculate_age,
    map_medicare_status_to_dual_code,
    map_aid_code_to_dual_status,
    determine_dual_status,
    classify_dual_benefit_level,
    is_new_enrollee,
    MemberContext
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
    assert map_medicare_status_to_dual_code("INVALID") is None
    assert map_medicare_status_to_dual_code(None) is None

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

    assert map_aid_code_to_dual_status("XX") is None
    assert map_aid_code_to_dual_status(None) is None

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
