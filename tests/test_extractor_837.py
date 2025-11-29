import pytest
import importlib.resources
from hccinfhir.extractor import extract_sld, extract_sld_list
from hccinfhir.extractor_837 import parse_date, parse_amount

def load_sample_837(casenum=0):
    with importlib.resources.open_text('hccinfhir.sample_files', 
                                     f'sample_837_{casenum}.txt') as f:
        return f.read()

# X12Parser Tests
def test_parse_date():
    assert parse_date("20230415") == "2023-04-15"
    assert parse_date("") is None
    assert parse_date("2023041") is None
    assert parse_date("abcdefgh") is None

def test_parse_amount():
    assert parse_amount("123.45") == 123.45
    assert parse_amount("0") == 0.0
    assert parse_amount("invalid") is None
    assert parse_amount("") is None

# Integration Tests
def test_extract_sld_basic():
    x12_data = load_sample_837(0)
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 5
    assert sld[0].linked_diagnosis_codes == ["F1120"]

def test_extract_sld_complete_claim():
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  NM1*IL*1*DOE*JOHN****MI*12345~
                  N3*123 MAIN ST~
                  N4*ANYTOWN*NY*12345~
                  DMG*D8*19400101*M~
                  CLM*ABC123*500*****11*Y*A*Y*Y**1~
                  HI*ABK:F1120~
                  NM1*82*1*SMITH*JANE****XX*1234567890~
                  PRV*PE*PXC*207RC0000X~
                  SV1*HC:99213:25:59*50*UN*1*11~
                  DTP*472*D8*20230415~
                  SE*15*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1
    assert sld[0].patient_id == "12345"
    assert sld[0].provider_specialty == "207RC0000X"
    assert sld[0].performing_provider_npi == "1234567890"
    assert sld[0].procedure_code == "99213"
    assert sld[0].modifiers == ["25", "59"]
    assert sld[0].service_date == "2023-04-15"

def test_extract_sld_empty_input():
    with pytest.raises(TypeError):
        extract_sld("", format="837")

def test_extract_sld_invalid_format():
    x12_data = load_sample_837(0)
    with pytest.raises(ValueError):
        extract_sld(x12_data, format="invalid")

def test_extract_sld_missing_required_segments():
    x12_data = """NM1*IL*1*DOE*JOHN****MI*12345~
                  CLM*12345*500~"""
    with pytest.raises(ValueError):
        extract_sld(x12_data, format="837")

def test_extract_sld_multiple_service_lines():
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  NM1*IL*1*DOE*JOHN****MI*12345~
                  N3*123 MAIN ST~
                  N4*ANYTOWN*NY*12345~
                  DMG*D8*19400101*M~
                  CLM*ABC123*500*****11*Y*A*Y*Y**1~
                  HI*ABK:F1120~
                  NM1*82*1*SMITH*JANE****XX*1234567890~
                  PRV*PE*PXC*207RC0000X~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11~
                  DTP*472*D8*20230415~
                  LX*2~
                  SV1*HC:99214*75*UN*1*11~
                  DTP*472*D8*20230415~
                  SE*19*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2
    assert sld[0].procedure_code == "99213"
    assert sld[1].procedure_code == "99214"


def test_extract_sld_list_837():
    x12_data_list = [
        load_sample_837(0),
        load_sample_837(1)
    ]
    slds = extract_sld_list(x12_data_list, format="837")
    assert len(slds) == 9

def test_extract_sld_institutional_claim():
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER       *ZZ*RECEIVER        *240209*1230*^*00501*000000001*0*P*:~
                GS*HC*SUBMITTER*RECEIVER*20240209*1230*1*X*005010X223A2~
                ST*837*0001*005010X223A2~
                BHT*0019*00*123*20240209*1230*CH~
                NM1*41*2*SUBMITTING PROVIDER*****46*123456789~
                PER*IC*CONTACT NAME*TE*5551234567~
                NM1*40*2*RECEIVER NAME*****46*987654321~
                HL*1**20*1~
                NM1*85*2*BILLING PROVIDER*****XX*1234567890~
                N3*123 MAIN STREET~
                N4*ANYTOWN*CA*12345~
                REF*EI*123456789~
                HL*2*1*22*1~
                SBR*P*18*******MC~
                NM1*IL*1*DOE*JOHN****MI*123456789A~
                N3*456 OAK STREET~
                N4*ANYTOWN*CA*12345~
                DMG*D8*19500101*M~
                HL*3*2*23*0~
                PAT*19~
                NM1*QC*1*DOE*JOHN~
                N3*456 OAK STREET~
                N4*ANYTOWN*CA*12345~
                CLM*12345*500***11:A:1*Y*A*Y*Y~
                DTP*434*D8*20240201~
                DTP*435*D8*20240203~
                REF*EA*PATIENT MRN~
                HI*ABK:R69.0~
                NM1*71*1*ATTENDING*DOCTOR****XX*1234567890~
                PRV*AT*PXC*207R00000X~
                SBR*P*18*******MC~
                AMT*F5*500~
                NM1*PR*2*MEDICARE*****PI*12345~
                N3*789 PINE STREET~
                N4*ANYWHERE*CA*54321~
                REF*2U*123456789~
                LX*1~
                SV2*0450*HC:99284*500*UN*1~
                DTP*472*D8*20240201~
                SE*39*0001~
                GE*1*1~
                IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1
    assert sld[0].patient_id == "123456789A"
    assert sld[0].service_date == "2024-02-01"
    assert sld[0].facility_type == "1"
    assert sld[0].service_type == "1"


# ===== HIERARCHY AND ISOLATION TESTS =====
# Tests for complex X12 837 scenarios: multiple claims, subscribers, dependencies

def test_multiple_claims_diagnosis_isolation():
    """Test that diagnosis codes don't bleed between claims for same subscriber"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119*ABF:E1165~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11**1:2~
                  CLM*CLAIM002*300~
                  HI*ABK:I10~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11**1~
                  SE*15*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # First claim should have E119 and E1165
    assert set(sld[0].claim_diagnosis_codes) == {"E119", "E1165"}
    assert set(sld[0].linked_diagnosis_codes) == {"E119", "E1165"}

    # Second claim should ONLY have I10, not E119/E1165
    assert sld[1].claim_diagnosis_codes == ["I10"]
    assert sld[1].linked_diagnosis_codes == ["I10"]
    assert "E119" not in sld[1].claim_diagnosis_codes
    assert "E1165" not in sld[1].claim_diagnosis_codes


def test_multiple_subscribers_isolation():
    """Test that data doesn't bleed between different subscribers"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  HL*3*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*SMITH*BOB****MI*SUB789~
                  CLM*CLAIM002*300~
                  HI*ABK:I10~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11***1~
                  SE*18*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # First subscriber
    assert sld[0].patient_id == "SUB123"
    assert sld[0].claim_diagnosis_codes == ["E119"]
    assert sld[0].billing_provider_npi == "1111111111"

    # Second subscriber - should have different patient ID and diagnosis
    assert sld[1].patient_id == "SUB789"
    assert sld[1].claim_diagnosis_codes == ["I10"]
    assert "E119" not in sld[1].claim_diagnosis_codes
    assert sld[1].billing_provider_npi == "1111111111"  # Same billing provider


def test_subscriber_with_dependent_patient():
    """Test subscriber (2000B) with dependent patient (2000C)"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*1~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  HL*3*2*23*0~
                  PAT*19~
                  NM1*QC*1*DOE*JANE****MI*PAT456~
                  CLM*CLAIM002*300~
                  HI*ABK:Z7901~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11***1~
                  SE*19*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # Subscriber's claim
    assert sld[0].patient_id == "SUB123"
    assert sld[0].claim_diagnosis_codes == ["E119"]

    # Dependent's claim - should use patient level ID
    assert sld[1].patient_id == "PAT456"
    assert sld[1].claim_diagnosis_codes == ["Z7901"]
    assert "E119" not in sld[1].claim_diagnosis_codes


def test_performing_provider_reset_between_claims():
    """Test that performing provider and specialty reset between claims"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  NM1*82*1*SMITH*JANE****XX*2222222222~
                  PRV*PE*PXC*207Q00000X~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  CLM*CLAIM002*300~
                  HI*ABK:I10~
                  NM1*82*1*JONES*BOB****XX*3333333333~
                  PRV*PE*PXC*208D00000X~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11***1~
                  SE*19*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # First claim
    assert sld[0].performing_provider_npi == "2222222222"
    assert sld[0].provider_specialty == "207Q00000X"

    # Second claim - should have different provider
    assert sld[1].performing_provider_npi == "3333333333"
    assert sld[1].provider_specialty == "208D00000X"


def test_claim_without_performing_provider():
    """Test claim with no performing provider specified"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  SE*12*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1

    assert sld[0].performing_provider_npi is None
    assert sld[0].provider_specialty is None
    assert sld[0].billing_provider_npi == "1111111111"


def test_multiple_billing_providers():
    """Test multiple billing providers in same transaction"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC A*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  HL*3**20*1~
                  NM1*85*2*BILLING CLINIC B*****XX*9999999999~
                  HL*4*3*22*0~
                  SBR*P*18~
                  NM1*IL*1*SMITH*BOB****MI*SUB789~
                  CLM*CLAIM002*300~
                  HI*ABK:I10~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11***1~
                  SE*19*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # First billing provider
    assert sld[0].billing_provider_npi == "1111111111"
    assert sld[0].patient_id == "SUB123"

    # Second billing provider
    assert sld[1].billing_provider_npi == "9999999999"
    assert sld[1].patient_id == "SUB789"


def test_multiple_hi_segments_in_claim():
    """Test multiple HI segments in same claim (common in 837I)"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119*ABF:E1165~
                  HI*ABF:I10*ABF:J449~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11~
                  SE*13*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1

    # Should have all 4 diagnoses from both HI segments
    assert len(sld[0].claim_diagnosis_codes) == 4
    assert set(sld[0].claim_diagnosis_codes) == {"E119", "E1165", "I10", "J449"}


def test_diagnosis_pointer_resolution():
    """Test that diagnosis pointers correctly resolve to actual codes"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119*ABF:E1165*ABF:I10*ABF:J449~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11**1:3~
                  LX*2~
                  SV1*HC:99214*75*UN*1*11**2:4~
                  SE*14*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # First service line - pointers 1 and 3
    assert set(sld[0].linked_diagnosis_codes) == {"E119", "I10"}

    # Second service line - pointers 2 and 4
    assert set(sld[1].linked_diagnosis_codes) == {"E1165", "J449"}

    # Both should have all claim diagnoses
    assert len(sld[0].claim_diagnosis_codes) == 4
    assert len(sld[1].claim_diagnosis_codes) == 4


def test_institutional_multiple_service_lines():
    """Test institutional claim (837I) with multiple service lines"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER       *ZZ*RECEIVER        *240209*1230*^*00501*000000001*0*P*:~
                GS*HC*SUBMITTER*RECEIVER*20240209*1230*1*X*005010X223A2~
                ST*837*0001*005010X223A2~
                BHT*0019*00*123*20240209*1230*CH~
                NM1*41*2*SUBMITTING PROVIDER*****46*123456789~
                PER*IC*CONTACT NAME*TE*5551234567~
                NM1*40*2*RECEIVER NAME*****46*987654321~
                HL*1**20*1~
                NM1*85*2*BILLING PROVIDER*****XX*1234567890~
                HL*2*1*22*0~
                SBR*P*18*******MC~
                NM1*IL*1*DOE*JOHN****MI*123456789A~
                CLM*12345*1000***11:A:1*Y*A*Y*Y~
                HI*ABK:R690~
                LX*1~
                SV2*0450*HC:99284*500*UN*1~
                DTP*472*D8*20240201~
                LX*2~
                SV2*0730*HC:99285*500*UN*1~
                DTP*472*D8*20240202~
                SE*19*0001~
                GE*1*1~
                IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 2

    # Both service lines should have same patient and diagnosis
    assert sld[0].patient_id == "123456789A"
    assert sld[1].patient_id == "123456789A"
    assert sld[0].claim_diagnosis_codes == ["R690"]
    assert sld[1].claim_diagnosis_codes == ["R690"]

    # Different procedures and dates
    assert sld[0].procedure_code == "99284"
    assert sld[1].procedure_code == "99285"
    assert sld[0].service_date == "2024-02-01"
    assert sld[1].service_date == "2024-02-02"

    # Facility type should be set
    assert sld[0].facility_type == "1"
    assert sld[0].service_type == "1"


def test_complex_family_hierarchy():
    """Test complex scenario: subscriber with multiple dependents, multiple claims each"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*1~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  CLM*CLAIM002*300~
                  HI*ABK:I10~
                  LX*1~
                  SV1*HC:99214*75*UN*1*11***1~
                  HL*3*2*23*0~
                  PAT*19~
                  NM1*QC*1*DOE*JANE****MI*PAT456~
                  CLM*CLAIM003*200~
                  HI*ABK:Z7901~
                  LX*1~
                  SV1*HC:99203*100*UN*1*11***1~
                  CLM*CLAIM004*250~
                  HI*ABK:J060~
                  LX*1~
                  SV1*HC:99204*125*UN*1*11***1~
                  HL*4*2*23*0~
                  PAT*19~
                  NM1*QC*1*DOE*JIMMY****MI*PAT789~
                  CLM*CLAIM005*150~
                  HI*ABK:R51~
                  LX*1~
                  SV1*HC:99202*75*UN*1*11***1~
                  SE*30*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 5

    # Subscriber's claims (CLAIM001, CLAIM002)
    assert sld[0].patient_id == "SUB123"
    assert sld[0].claim_diagnosis_codes == ["E119"]
    assert sld[1].patient_id == "SUB123"
    assert sld[1].claim_diagnosis_codes == ["I10"]

    # First dependent's claims (CLAIM003, CLAIM004)
    assert sld[2].patient_id == "PAT456"
    assert sld[2].claim_diagnosis_codes == ["Z7901"]
    assert sld[3].patient_id == "PAT456"
    assert sld[3].claim_diagnosis_codes == ["J060"]

    # Second dependent's claim (CLAIM005)
    assert sld[4].patient_id == "PAT789"
    assert sld[4].claim_diagnosis_codes == ["R51"]

    # All should have same billing provider
    assert all(s.billing_provider_npi == "1111111111" for s in sld)


def test_prv_segment_without_nm1():
    """Test that PRV segment without preceding NM1*82 doesn't set specialty"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  PRV*PE*PXC*207Q00000X~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11***1~
                  SE*13*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1

    # PRV after NM1*85 should NOT set provider_specialty
    # (last_nm1_qualifier was '85', not '82')
    assert sld[0].provider_specialty is None


def test_service_line_without_diagnosis_pointer():
    """Test service line without diagnosis pointer (all claim dx should be available)"""
    x12_data = """ISA*00*          *00*          *ZZ*SUBMITTER ID  *ZZ*RECEIVER ID   *230415*1430*^*00501*000000001*0*P*:~
                  GS*HC*SUBMITTER ID*RECEIVER ID*20230415*1430*1*X*005010X222A1~
                  ST*837*0001*005010X222A1~
                  BHT*0019*00*123*20230415*1430*CH~
                  NM1*41*2*SUBMIT CLINIC*****46*12345~
                  PER*IC*CONTACT NAME*TE*5555551234~
                  HL*1**20*1~
                  NM1*85*2*BILLING CLINIC*****XX*1111111111~
                  HL*2*1*22*0~
                  SBR*P*18~
                  NM1*IL*1*DOE*JOHN****MI*SUB123~
                  CLM*CLAIM001*500~
                  HI*ABK:E119*ABF:E1165*ABF:I10~
                  LX*1~
                  SV1*HC:99213*50*UN*1*11~
                  SE*12*0001~
                  GE*1*1~
                  IEA*1*000000001~"""
    sld = extract_sld(x12_data, format="837")
    assert len(sld) == 1

    # No diagnosis pointers, so linked_diagnoses should be empty
    assert sld[0].linked_diagnosis_codes == []

    # But all claim diagnoses should still be available
    assert len(sld[0].claim_diagnosis_codes) == 3
    assert set(sld[0].claim_diagnosis_codes) == {"E119", "E1165", "I10"}