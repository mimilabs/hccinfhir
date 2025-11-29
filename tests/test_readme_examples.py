#!/usr/bin/env python3
"""
Test script to verify README examples work correctly.
Each test corresponds 1-to-1 with a README example.
"""

# =============================================================================
# QUICKSTART EXAMPLE (README lines 15-28)
# =============================================================================

def test_01_quickstart():
    """
    README: Quickstart section
    Tests the main quickstart example with diagnosis codes
    """
    print("\n=== Test 1: Quickstart ===")
    from hccinfhir import HCCInFHIR, Demographics

    # Initialize processor
    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    # Calculate from diagnosis codes
    demographics = Demographics(age=67, sex="F")
    diagnosis_codes = ["E11.9", "I10", "N18.3"]

    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)
    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ HCCs: {result.hcc_list}")

    assert result.risk_score > 0
    assert len(result.hcc_list) > 0
    print("✅ Test passed")


# =============================================================================
# HOW-TO GUIDE 1: Working with CMS Encounter Data (README lines 115-175)
# =============================================================================

def test_02_cms_encounter_data_837():
    """
    README: Working with CMS Encounter Data (837 Claims)
    Tests the complete 837 workflow from How-To Guide
    """
    print("\n=== Test 2: CMS Encounter Data (837 Claims) ===")
    from hccinfhir import HCCInFHIR, Demographics, get_837_sample
    from hccinfhir.extractor import extract_sld

    # Step 1: Configure processor
    # All data file parameters are optional and default to the latest 2026 valuesets
    processor = HCCInFHIR(
        model_name="CMS-HCC Model V28",
        filter_claims=True,  # Apply CMS filtering rules
    )

    # Step 2: Load 837 data (using sample instead of file)
    raw_837_data = get_837_sample(0)

    # Step 3: Extract service-level data
    service_data = extract_sld(raw_837_data, format="837")

    # Step 4: Define beneficiary demographics
    demographics = Demographics(
        age=72,
        sex="M",
        dual_elgbl_cd="00",      # Non-dual eligible
        orec="0",                # Original reason for entitlement
        crec="0",                # Current reason for entitlement
        orig_disabled=False,
        new_enrollee=False,
        esrd=False
    )

    # Step 5: Calculate risk score
    result = processor.run_from_service_data(service_data, demographics)

    # Step 6: Review results
    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ Active HCCs: {result.hcc_list}")
    print(f"✅ Disease Interactions: {list(result.interactions.keys())[:3]}")  # First 3

    assert result.risk_score > 0
    print("✅ Test passed")


# =============================================================================
# HOW-TO GUIDE 2: Processing X12 834 Enrollment (README lines 177-256)
# =============================================================================

def test_03_x12_834_enrollment():
    """
    README: Processing X12 834 Enrollment for Dual Eligibility
    Tests 834 enrollment parsing and dual eligibility detection
    """
    print("\n=== Test 3: X12 834 Enrollment ===")
    from hccinfhir import HCCInFHIR, get_834_sample
    from hccinfhir.extractor_834 import (
        extract_enrollment_834,
        enrollment_to_demographics,
        is_losing_medicaid,
        medicaid_status_summary
    )

    # Step 1: Parse X12 834 enrollment file
    x12_834_data = get_834_sample(1)
    enrollments = extract_enrollment_834(x12_834_data)

    # Step 2: Process each member
    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    print(f"✅ Parsed {len(enrollments)} enrollments")

    for enrollment in enrollments[:2]:  # Test first 2
        # Convert enrollment to Demographics for RAF calculation
        demographics = enrollment_to_demographics(enrollment)

        # Check if member is losing Medicaid coverage
        if is_losing_medicaid(enrollment, within_days=90):
            print(f"⚠️  ALERT: {enrollment.member_id} losing Medicaid!")

        # Get comprehensive Medicaid status
        status = medicaid_status_summary(enrollment)
        print(f"✅ Member: {enrollment.member_id}, Dual Status: {status['dual_status']}")

        assert demographics.age is not None
        assert demographics.sex in ['M', 'F']

    print("✅ Test passed")


# =============================================================================
# HOW-TO GUIDE 3: Processing Clearinghouse 837 Claims (README lines 258-297)
# =============================================================================

def test_04_clearinghouse_837_claims():
    """
    README: Processing Clearinghouse 837 Claims
    Tests X12 837 claim processing workflow
    """
    print("\n=== Test 4: Clearinghouse 837 Claims ===")
    from hccinfhir import HCCInFHIR, Demographics, get_837_sample
    from hccinfhir.extractor import extract_sld

    # Step 1: Initialize processor
    processor = HCCInFHIR(
        model_name="CMS-HCC Model V28",
        filter_claims=True
    )

    # Step 2: Load 837 claim data
    x12_data = get_837_sample(1)

    # Step 3: Extract service-level data
    service_data = extract_sld(x12_data, format="837")

    # Step 4: Define demographics
    demographics = Demographics(age=65, sex="F", dual_elgbl_cd="00")

    # Step 5: Calculate RAF score
    result = processor.run_from_service_data(service_data, demographics)

    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ HCCs: {result.hcc_list}")

    assert result.risk_score > 0
    print("✅ Test passed")


# =============================================================================
# HOW-TO GUIDE 4: Using CMS BCDA API Data (README lines 299-338)
# =============================================================================

def test_05_cms_bcda_api_fhir():
    """
    README: Using CMS BCDA API Data (FHIR EOB)
    Tests FHIR EOB processing
    """
    print("\n=== Test 5: CMS BCDA API (FHIR EOB) ===")
    from hccinfhir import HCCInFHIR, Demographics, get_eob_sample

    # Step 1: Initialize processor
    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    # Step 2: Load FHIR EOB resources (using sample)
    eob = get_eob_sample(1)
    eob_list = [eob]  # processor.run() expects a list

    # Step 3: Define demographics
    demographics = Demographics(
        age=67,
        sex="F",
        dual_elgbl_cd="00",
        orec="0"
    )

    # Step 4: Calculate risk score
    result = processor.run(eob_list, demographics)

    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ HCCs: {result.hcc_list}")

    assert result.risk_score >= 0
    print("✅ Test passed")


# =============================================================================
# HOW-TO GUIDE 5: Direct Diagnosis Code Processing (README lines 340-382)
# =============================================================================

def test_06_direct_diagnosis_codes():
    """
    README: Direct Diagnosis Code Processing
    Tests calculating RAF from diagnosis codes only
    """
    print("\n=== Test 6: Direct Diagnosis Codes ===")
    from hccinfhir import HCCInFHIR, Demographics

    # Step 1: Initialize processor
    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    # Step 2: Prepare diagnosis codes
    diagnosis_codes = ["E11.9", "I10", "N18.3"]

    # Step 3: Define demographics
    demographics = Demographics(age=67, sex="F", dual_elgbl_cd="00")

    # Step 4: Calculate risk score
    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ HCCs: {result.hcc_list}")

    assert result.risk_score > 0
    assert len(result.hcc_list) > 0
    print("✅ Test passed")


# =============================================================================
# ADVANCED FEATURE 1: Payment RAF Adjustments (README lines 600-628)
# =============================================================================

def test_07_payment_raf_adjustments():
    """
    README: Payment RAF Adjustments
    Tests MACI, normalization factor, and frailty score
    """
    print("\n=== Test 7: Payment RAF Adjustments ===")
    from hccinfhir import HCCInFHIR, Demographics

    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    demographics = Demographics(age=67, sex="F", dual_elgbl_cd="00")
    diagnosis_codes = ["E11.9", "I10"]

    # Calculate with payment adjustments
    result = processor.calculate_from_diagnosis(
        diagnosis_codes,
        demographics,
        maci=0.059,         # MA Coding Intensity Adjustment
        norm_factor=1.015,  # Normalization factor
        frailty_score=0.0   # Frailty adjustment
    )

    print(f"✅ Base RAF Score: {result.risk_score:.3f}")
    print(f"✅ Payment RAF Score: {result.risk_score_payment:.3f}")

    adjustment_pct = ((result.risk_score_payment / result.risk_score - 1) * 100)
    print(f"✅ Adjustment: {adjustment_pct:+.1f}%")

    assert hasattr(result, 'risk_score_payment')
    print("✅ Test passed")


# =============================================================================
# ADVANCED FEATURE 2: Prefix Override (README lines 630-682)
# =============================================================================

def test_08_prefix_override():
    """
    README: Demographic Prefix Override
    Tests manual prefix override for ESRD patients
    """
    print("\n=== Test 8: Prefix Override ===")
    from hccinfhir import HCCInFHIR, Demographics

    processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")

    # ESRD patient with incorrect orec/crec codes
    demographics = Demographics(age=65, sex="F", orec="0", crec="0")
    diagnosis_codes = ["N18.6", "E11.22"]

    # Without override (uses wrong coefficients)
    result_auto = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

    # With override (force ESRD dialysis coefficients)
    result_override = processor.calculate_from_diagnosis(
        diagnosis_codes,
        demographics,
        prefix_override='DI_'
    )

    print(f"✅ Auto-detected RAF: {result_auto.risk_score:.3f}")
    print(f"✅ Override (DI_) RAF: {result_override.risk_score:.3f}")

    assert result_auto.risk_score != result_override.risk_score
    print("✅ Test passed")


# =============================================================================
# ADVANCED FEATURE 3: Batch Processing (README lines 788-821)
# =============================================================================

def test_09_batch_processing():
    """
    README: Batch Processing
    Tests processing multiple patients
    """
    print("\n=== Test 9: Batch Processing ===")
    from hccinfhir import HCCInFHIR, Demographics, get_eob_sample

    processor = HCCInFHIR(model_name="CMS-HCC Model V28")

    # Multiple patients
    patients = [
        {
            "patient_id": "PAT001",
            "eobs": [get_eob_sample(1)],
            "demographics": Demographics(age=65, sex="M")
        },
        {
            "patient_id": "PAT002",
            "eobs": [get_eob_sample(2)],
            "demographics": Demographics(age=72, sex="F")
        }
    ]

    results = []
    for patient in patients:
        result = processor.run(patient["eobs"], patient["demographics"])
        results.append({
            "patient_id": patient["patient_id"],
            "risk_score": result.risk_score,
            "hccs": result.hcc_list
        })

    print(f"✅ Processed {len(results)} patients")
    for r in results:
        print(f"   {r['patient_id']}: RAF={r['risk_score']:.3f}, HCCs={len(r['hccs'])}")

    assert len(results) == 2
    print("✅ Test passed")


# =============================================================================
# SAMPLE DATA EXAMPLES (README lines 861-892)
# =============================================================================

def test_10_sample_data_functions():
    """
    README: Sample Data section
    Tests all sample data loading functions
    """
    print("\n=== Test 10: Sample Data Functions ===")
    from hccinfhir import (
        HCCInFHIR,
        Demographics,
        get_eob_sample,
        get_837_sample,
        get_834_sample,
        get_eob_sample_list,
        list_available_samples
    )

    processor = HCCInFHIR(model_name="CMS-HCC Model V28")
    demographics = Demographics(age=67, sex="F")

    # FHIR EOB samples (3 individual + 200 batch)
    eob = get_eob_sample(1)  # Cases 1, 2, 3 (returns single dict)
    eob_list = get_eob_sample_list(limit=50)  # Returns list

    # Usage: processor.run() expects a list, so wrap single EOB
    result = processor.run([eob], demographics)  # Note: [eob] not eob
    print(f"✅ EOB processed: RAF={result.risk_score:.3f}")

    # X12 837 samples (13 different scenarios)
    claim = get_837_sample(0)  # Cases 0-12 (returns string)
    print(f"✅ 837 loaded: {len(claim)} chars")

    # X12 834 enrollment samples
    enrollment_834 = get_834_sample(1)  # Currently only case 1 available (returns string)
    print(f"✅ 834 loaded: {len(enrollment_834)} chars")

    # List all available samples
    info = list_available_samples()
    print(f"✅ EOB samples: {info['eob_case_numbers']}")
    print(f"✅ 837 samples: {len(info['837_case_numbers'])} cases")
    print(f"✅ 834 samples: {info['834_case_numbers']}")

    assert len(eob_list) == 50
    assert len(info['837_case_numbers']) == 13
    print("✅ Test passed")


# =============================================================================
# API REFERENCE: Demographics (README lines 534-548)
# =============================================================================

def test_11_demographics_api():
    """
    README: Demographics API Reference
    Tests Demographics class initialization
    """
    print("\n=== Test 11: Demographics API ===")
    from hccinfhir import Demographics

    demographics = Demographics(
        # Required fields
        age=67,                    # Age in years
        sex="F",                   # "M" or "F"

        # Dual eligibility
        dual_elgbl_cd="00",        # "00"=Non-dual, "01"=Partial, "02"=Full

        # Medicare entitlement
        orec="0",                  # Original reason for entitlement
        crec="0",                  # Current reason for entitlement

        # Status flags
        orig_disabled=False,
        new_enrollee=False,
        esrd=False,

        # Optional fields
        snp=False,
        lti=False,
        low_income=False,
        graft_months=None
    )

    print(f"✅ Demographics created: age={demographics.age}, sex={demographics.sex}")
    assert demographics.age == 67
    assert demographics.sex == "F"
    print("✅ Test passed")


# =============================================================================
# API REFERENCE: RAFResult (README lines 551-568)
# =============================================================================

def test_12_raf_result_api():
    """
    README: RAFResult API Reference
    Tests all RAFResult fields are present
    """
    print("\n=== Test 12: RAFResult API ===")
    from hccinfhir import HCCInFHIR, Demographics

    processor = HCCInFHIR(model_name="CMS-HCC Model V28")
    demographics = Demographics(age=67, sex="F", dual_elgbl_cd="00")
    diagnosis_codes = ["E11.9", "I50.22", "N18.3"]

    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

    # Verify all documented fields exist
    fields = [
        'risk_score',
        'risk_score_demographics',
        'risk_score_chronic_only',
        'risk_score_hcc',
        'risk_score_payment',
        'hcc_list',
        'cc_to_dx',
        'coefficients',
        'interactions',
        'demographics',
        'model_name',
        'version',
        'diagnosis_codes',
        'service_level_data'
    ]

    for field in fields:
        assert hasattr(result, field), f"Missing field: {field}"
        print(f"✅ {field}: present")

    print("✅ Test passed")


# =============================================================================
# DUAL ELIGIBILITY IMPACT EXAMPLE (README lines 512-548)
# =============================================================================

def test_13_dual_eligibility_impact():
    """
    README: Dual Eligibility Impact
    Tests the difference between non-dual and full-benefit dual RAF scores
    """
    print("\n=== Test 13: Dual Eligibility Impact ===")
    from hccinfhir import HCCInFHIR, Demographics

    processor = HCCInFHIR(model_name="CMS-HCC Model V28")
    diagnosis_codes = ["E11.9", "I10"]

    # Non-dual eligible
    demographics_non_dual = Demographics(age=72, sex="F", dual_elgbl_cd="00")
    result_non_dual = processor.calculate_from_diagnosis(diagnosis_codes, demographics_non_dual)

    # Full benefit dual eligible
    demographics_full_dual = Demographics(age=72, sex="F", dual_elgbl_cd="02")
    result_full_dual = processor.calculate_from_diagnosis(diagnosis_codes, demographics_full_dual)

    print(f"✅ Non-Dual RAF: {result_non_dual.risk_score:.3f}")
    print(f"✅ Full Dual RAF: {result_full_dual.risk_score:.3f}")

    diff_pct = ((result_full_dual.risk_score / result_non_dual.risk_score - 1) * 100)
    print(f"✅ Difference: {diff_pct:.1f}%")

    assert result_full_dual.risk_score != result_non_dual.risk_score
    print("✅ Test passed")


# =============================================================================
# ESRD MODEL EXAMPLE (README lines 344-378)
# =============================================================================

def test_14_esrd_model():
    """
    README: ESRD Model Example
    Tests ESRD model calculation
    """
    print("\n=== Test 14: ESRD Model ===")
    from hccinfhir import HCCInFHIR, Demographics

    processor = HCCInFHIR(model_name="CMS-HCC ESRD Model V24")

    demographics = Demographics(
        age=65,
        sex="M",
        orec="2",  # ESRD
        crec="2"
    )

    diagnosis_codes = ["N18.6", "E11.22", "I12.0"]

    result = processor.calculate_from_diagnosis(diagnosis_codes, demographics)

    print(f"✅ Risk Score: {result.risk_score:.3f}")
    print(f"✅ HCCs: {result.hcc_list}")

    assert result.risk_score > 0
    print("✅ Test passed")


# =============================================================================
# TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all README example tests in order"""
    print("=" * 70)
    print("README EXAMPLES TEST SUITE")
    print("Each test corresponds 1-to-1 with a README example")
    print("=" * 70)

    tests = [
        test_01_quickstart,
        test_02_cms_encounter_data_837,
        test_03_x12_834_enrollment,
        test_04_clearinghouse_837_claims,
        test_05_cms_bcda_api_fhir,
        test_06_direct_diagnosis_codes,
        test_07_payment_raf_adjustments,
        test_08_prefix_override,
        test_09_batch_processing,
        test_10_sample_data_functions,
        test_11_demographics_api,
        test_12_raf_result_api,
        test_13_dual_eligibility_impact,
        test_14_esrd_model,
    ]

    passed = 0
    failed = 0
    failed_tests = []

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            failed_tests.append(test.__name__)

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed_tests:
        print(f"Failed tests: {', '.join(failed_tests)}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
