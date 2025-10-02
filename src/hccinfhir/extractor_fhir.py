from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import List, Optional, Literal, Dict
from datetime import date
from hccinfhir.datamodels import ServiceLevelData

SYSTEMS = {
    'diagnosis': {
        'icd10cm': 'http://hl7.org/fhir/sid/icd-10-cm',
        'icd10': 'http://hl7.org/fhir/sid/icd-10'
    },
    'procedures': {
        'hcpcs': 'https://bluebutton.cms.gov/resources/codesystem/hcpcs'
    },
    'identifiers': {
        'npi': 'http://hl7.org/fhir/sid/us-npi',
        'ndc': 'http://hl7.org/fhir/sid/ndc'
    },
    'context': {
        'specialty': 'https://bluebutton.cms.gov/resources/variables/prvdr_spclty',
        'role': 'http://hl7.org/fhir/us/carin-bb/CodeSystem/C4BBClaimCareTeamRole',
        'claim_type': 'https://bluebutton.cms.gov/resources/variables/nch_clm_type_cd',
        'facility': 'https://bluebutton.cms.gov/resources/variables/clm_fac_type_cd',
        'service': 'https://bluebutton.cms.gov/resources/variables/clm_srvc_clsfctn_type_cd',
        'place': 'https://bluebutton.cms.gov/resources/variables/line_place_of_srvc_cd'
    }
}

class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class Extension(BaseModel):
    url: str
    valueCoding: Optional[dict] = None

class ExtensionMixin(BaseModel):
    extension: Optional[List[Extension]] = None

    def get_extension_code(self, system_url: str) -> Optional[str]:
        """Extract code from extensions for a specific system URL"""
        if not self.extension:
            return None
        return next((
            ext.valueCoding.get('code')
            for ext in self.extension
            if ext.url == system_url and ext.valueCoding
        ), None)
    
class CodeableConcept(ExtensionMixin):
    coding: Optional[List[Coding]] = None

    def get_code(self, system: str) -> Optional[str]:
        """Extract code for a specific coding system"""
        if not self.coding:
            return None
        return next((c.code for c in self.coding if c and c.system == system and c.code), None)

class Period(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None

    def get_service_date(self) -> Optional[str]:
        """Return the most specific date available"""
        return self.end.isoformat() if self.end else self.start.isoformat() if self.start else None

class Diagnosis(BaseModel):
    sequence: int
    diagnosisCodeableConcept: CodeableConcept

class CareTeamMember(BaseModel):
    role: CodeableConcept
    qualification: Optional[CodeableConcept] = None
    provider: Optional[dict] = None

class EoBItem(BaseModel):
    productOrService: Optional[CodeableConcept] = Field(None, validation_alias=AliasChoices('service', 'productOrService'))
    quantity: Optional[dict] = None
    diagnosisSequence: Optional[List[int]] = None
    servicedPeriod: Optional[Period] = None
    locationCodeableConcept: Optional[CodeableConcept] = None
    modifier: Optional[List[CodeableConcept]] = None
    adjudication: Optional[List[dict]] = None

class Facility(ExtensionMixin):
    pass

class ExplanationOfBenefit(ExtensionMixin):
    model_config = ConfigDict(frozen=True)
    resourceType: Literal["ExplanationOfBenefit"] = "ExplanationOfBenefit"
    id: Optional[str] = None
    type: Optional[CodeableConcept] = None
    diagnosis: Optional[List[Diagnosis]] = []
    item: Optional[List[EoBItem]] = []
    careTeam: Optional[List[CareTeamMember]] = []
    billablePeriod: Optional[Period] = None
    patient: Optional[dict] = None
    facility: Optional[Facility] = None
    contained: Optional[List[dict]] = None

    def get_diagnosis_codes(self) -> Dict[int, str]:
        """Extract all diagnosis codes with their sequences"""
        dx_codes = {}
        for dx in self.diagnosis or []:
            code = (dx.diagnosisCodeableConcept.get_code(SYSTEMS['diagnosis']['icd10cm']) or 
                   dx.diagnosisCodeableConcept.get_code(SYSTEMS['diagnosis']['icd10']))
            if code:
                dx_codes[dx.sequence] = code
        return dx_codes

    def get_rendering_provider(self) -> Optional[CareTeamMember]:
        """Get the rendering provider from the care team"""
        return next((
            m for m in self.careTeam or []
            if m.role.get_code(SYSTEMS['context']['role']) in {'performing', 'rendering'}
        ), None)

    def get_billing_npi(self) -> Optional[str]:
        """Extract billing provider NPI from contained resources"""
        return next((
            i.get('value') 
            for c in (self.contained or [])
            for i in c.get('identifier', [])
            if i.get('system') == SYSTEMS['identifiers']['npi']
        ), None)

def extract_sld_fhir(eob_data: dict) -> List[ServiceLevelData]:
    try:
        eob = ExplanationOfBenefit.model_validate(eob_data)
        dx_lookup = eob.get_diagnosis_codes()
        rendering_provider = eob.get_rendering_provider()
        
        common_data = {
            'claim_id': eob.id,
            'claim_type': eob.type.get_code(SYSTEMS['context']['claim_type']) if eob.type else None,
            'provider_specialty': (rendering_provider.qualification.get_code(SYSTEMS['context']['specialty']) 
                                 if rendering_provider and rendering_provider.qualification else None),
            'performing_provider_npi': (rendering_provider.provider.get('identifier', {}).get('value') 
                                      if rendering_provider else None),
            'patient_id': eob.patient.get('reference', '').split('/')[-1] if eob.patient else None,
            'facility_type': (eob.facility.get_extension_code(SYSTEMS['context']['facility'])
                            if eob.facility else None),
            'service_type': (eob.type.get_extension_code(SYSTEMS['context']['service']) or
                           eob.type.get_code(SYSTEMS['context']['service']) if eob.type else None),
            'billing_provider_npi': eob.get_billing_npi()
        }

        results = []
        for item in eob.item or []:
            if not item.productOrService:
                continue

            service_data = {
                **common_data,
                'procedure_code': item.productOrService.get_code(SYSTEMS['procedures']['hcpcs']),
                'ndc': (item.productOrService.get_code(SYSTEMS['identifiers']['ndc']) or
                       item.productOrService.get_extension_code(SYSTEMS['identifiers']['ndc'])),
                'quantity': item.quantity.get('value') if item.quantity else None,
                'linked_diagnosis_codes': [dx_lookup[seq] for seq in (item.diagnosisSequence or []) if seq in dx_lookup],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': (item.servicedPeriod.get_service_date() if item.servicedPeriod else
                               eob.billablePeriod.get_service_date() if eob.billablePeriod else None),
                'place_of_service': item.locationCodeableConcept.get_code(SYSTEMS['context']['place'])
                                  if item.locationCodeableConcept else None,
                'modifiers': [code for m in (item.modifier or [])
                              if m and (code := m.get_code(SYSTEMS['procedures']['hcpcs'])) is not None],
                'allowed_amount': next((adj.get('amount', {}).get('value')
                                      for adj in (item.adjudication or [])
                                      if any(c.get('code') == 'eligible'
                                           for c in adj.get('category', {}).get('coding', []))), None)
            }

            if service_data['procedure_code'] or service_data['ndc']:
                results.append(service_data)

        if not results:
            results.append({
                **common_data,
                'linked_diagnosis_codes': [],
                'claim_diagnosis_codes': list(dx_lookup.values()),
                'service_date': eob.billablePeriod.get_service_date() if eob.billablePeriod else None,
                'procedure_code': None,
                'ndc': None,
                'quantity': None,
                'place_of_service': None,
                'modifiers': [],
                'allowed_amount': None
            })

        return [ServiceLevelData.model_validate(r) for r in results]

    except ValueError as e:
        raise ValueError(f"Error processing EOB: {str(e)}")