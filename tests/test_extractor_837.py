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