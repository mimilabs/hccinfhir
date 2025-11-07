from typing import List, Optional, Dict
from pydantic import BaseModel
from hccinfhir.datamodels import ServiceLevelData

CLAIM_TYPES = {
    "005010X222A1": "837P",     # Professional
    "005010X223A2": "837I"      # Institutional
}

class HierarchyContext(BaseModel):
    """Tracks the current position in the 837 hierarchy"""
    billing_provider_npi: Optional[str] = None
    subscriber_patient_id: Optional[str] = None
    patient_patient_id: Optional[str] = None
    current_hl_level: Optional[str] = None
    current_hl_id: Optional[str] = None

class ClaimContext(BaseModel):
    """Claim-level data that resets for each CLM segment"""
    claim_id: Optional[str] = None
    dx_lookup: Dict[str, str] = {}
    facility_type: Optional[str] = None
    service_type: Optional[str] = None
    performing_provider_npi: Optional[str] = None
    provider_specialty: Optional[str] = None
    last_nm1_qualifier: Optional[str] = None

def parse_date(date_str: str) -> Optional[str]:
    """Convert 8-digit date string to ISO format YYYY-MM-DD"""
    if not isinstance(date_str, str) or len(date_str) != 8:
        return None
    try:
        year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
        if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return None

def parse_amount(amount_str: str) -> Optional[float]:
    """Convert string to float, return None if invalid"""
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return None

def get_segment_value(segment: List[str], 
                      index: int, 
                      default: Optional[str] = None) -> Optional[str]:
    """Safely get value from segment at given index"""
    return segment[index] if len(segment) > index else default

def parse_diagnosis_codes(segment: List[str]) -> Dict[str, str]:
    """Extract diagnosis codes from HI segment"""
    dx_lookup = {}
    for pos, element in enumerate(segment[1:], 1):
        if ':' not in element:
            continue
        qualifier, code = element.split(':')[:2]
        if qualifier in {'ABK', 'ABF', 'ABJ'}:  # ICD-10 qualifiers
            # ABK: Primary Diagnosis
            # ABF: Secondary Diagnosis
            # ABJ: Admitting Diagnosis
            # NOTE: In Risk Adjustment, we do not differentiate between primary and secondary diagnoses
            dx_lookup[str(pos)] = code
    return dx_lookup

def process_service_line(segments: List[List[str]], start_index: int) -> tuple[Optional[str], Optional[str]]:
    """Extract NDC and service date from service line segments"""
    ndc = None
    service_date = None
    
    for seg in segments[start_index:]:
        if seg[0] in ['LX', 'CLM', 'SE']:
            break
        if len(seg) > 3:
            if seg[0] == 'LIN' and seg[2] == 'N4':
                ndc = seg[3]
            elif (seg[0] == 'DTP' and 
                  seg[1] in {'472', '434'} and
                  seg[2].endswith('D8')):
                # 472: Service Date
                # 434: From Date in 837I
                # These are not included currently: 435: To Date in 837I, 096 Discharge Date            
                if seg[3]:
                    service_date = parse_date(seg[3][:8] if len(seg[3]) >= 8 else seg[3])
        if ndc and service_date:
            break
            
    return ndc, service_date

def split_into_claims(segments: List[List[str]]) -> List[List[List[str]]]:
    """Split segments into individual claims based on ST/SE boundaries.
    
    Each ST...SE block represents one complete claim.
    Returns a list of claim segment lists.
    """
    claims = []
    current_claim = []
    in_transaction = False
    st_control_number = None
    
    for segment in segments:
        if len(segment) < 1:
            continue
            
        seg_id = segment[0]
        
        if seg_id == 'ST':
            # Start new claim transaction
            if current_claim:  # Save previous claim if exists (shouldn't happen with valid X12)
                claims.append(current_claim)
            current_claim = [segment]
            in_transaction = True
            st_control_number = segment[2] if len(segment) > 2 else None
            
        elif seg_id == 'SE':
            # End current claim transaction
            if in_transaction:
                current_claim.append(segment)
                
                # Validate control numbers match (ST02 == SE02)
                se_control_number = segment[2] if len(segment) > 2 else None
                if st_control_number != se_control_number:
                    print(f"Warning: ST/SE control numbers don't match: {st_control_number} != {se_control_number}")
                
                claims.append(current_claim)
                current_claim = []
                in_transaction = False
                st_control_number = None
                
        elif in_transaction:
            # Add segment to current claim
            current_claim.append(segment)
    
    # Handle case where file doesn't end with SE (malformed)
    if current_claim:
        print("Warning: Unclosed transaction found (missing SE)")
        claims.append(current_claim)
    
    return claims

def parse_837_claim_to_sld(segments: List[List[str]], claim_type: str) -> List[ServiceLevelData]:
    """Extract service level data from 837 Professional or Institutional claims

    Structure:
    Billing Provider (2000A)
    └── Subscriber (2000B)
        └── Patient (2000C) [if needed]
            └── Claim (2300)
                ├── Service Line 1 (2400)
                ├── Service Line 2 (2400)
                └── Service Line N (2400)
    
    Properly handles multiple loops at each hierarchy level:
    - Multiple Billing Providers (2000A)
    - Multiple Subscribers per Billing Provider (2000B)
    - Multiple Patients per Subscriber (2000C)
    - Multiple Claims per Patient/Subscriber (2300)
    - Multiple Service Lines per Claim (2400)
    """
    slds = []
    hierarchy = HierarchyContext()
    claim = ClaimContext()

    for i, segment in enumerate(segments):
        if len(segment) < 2:
            continue
            
        seg_id = segment[0]
        
        # ===== HIERARCHY LEVEL TRACKING (HL segments) =====
        if seg_id == 'HL' and len(segment) >= 4:
            hl_id = segment[1]
            parent_id = segment[2] if segment[2] else None
            level_code = segment[3]
            
            hierarchy.current_hl_id = hl_id
            hierarchy.current_hl_level = level_code
            
            if level_code == '20':  # New Billing Provider
                hierarchy.billing_provider_npi = None
                hierarchy.subscriber_patient_id = None
                hierarchy.patient_patient_id = None
                claim = ClaimContext()
                
            elif level_code == '22':  # New Subscriber
                hierarchy.subscriber_patient_id = None
                hierarchy.patient_patient_id = None
                claim = ClaimContext()
                
            elif level_code == '23':  # New Patient
                hierarchy.patient_patient_id = None
                claim = ClaimContext()

       # ===== NAME/IDENTIFICATION (NM1 segments) =====
        elif seg_id == 'NM1' and len(segment) > 1:
            qualifier = segment[1]
            claim.last_nm1_qualifier = qualifier
            
            # Billing Provider (2010AA in 2000A)
            if qualifier == '85' and len(segment) > 8 and segment[8] == 'XX':
                hierarchy.billing_provider_npi = get_segment_value(segment, 9)
                
            # Subscriber or Patient (2010BA in 2000B)
            elif qualifier == 'IL':
                patient_id = get_segment_value(segment, 9)
                if hierarchy.current_hl_level == '22':  # Subscriber level
                    hierarchy.subscriber_patient_id = patient_id
                    hierarchy.patient_patient_id = None
                elif hierarchy.current_hl_level == '23':  # Patient level
                    hierarchy.patient_patient_id = patient_id
                else:
                    # Fallback: assume subscriber
                    hierarchy.subscriber_patient_id = patient_id
                    
            # Patient (2010CA in 2000C)
            elif qualifier == 'QC':
                hierarchy.patient_patient_id = get_segment_value(segment, 9)
                
            # Performing/Rendering Provider (2310D in 2300)
            elif qualifier == '82' and len(segment) > 8 and segment[8] == 'XX':
                claim.performing_provider_npi = get_segment_value(segment, 9)
        
                
        # ===== PROVIDER SPECIALTY (PRV segment) =====
        elif seg_id == 'PRV' and len(segment) > 3 and segment[1] == 'PE':
            # Only apply if last NM1 was performing provider (82)
            if claim.last_nm1_qualifier == '82':
                claim.provider_specialty = get_segment_value(segment, 3)
           
        # ===== CLAIM LEVEL (CLM segment - starts 2300 loop) =====
        elif seg_id == 'CLM':
            claim = ClaimContext()
            claim.claim_id = segment[1] if len(segment) > 1 else None
            
            # Parse facility and service type for institutional claims
            if claim_type == "837I" and len(segment) > 5 and segment[5] and ':' in segment[5]:
                claim.facility_type = segment[5][0] if segment[5] else None
                claim.service_type = segment[5][1] if len(segment[5]) > 1 else None
        
        # ===== DIAGNOSIS CODES (HI segment) =====
        elif seg_id == 'HI':
            # In 837I, there can be multiple HI segments in the claim
            # Also, in 837I, diagnosis position does not matter
            # We will use continuous numbering for diagnosis codes
            # use the last dx_lookup position as the starting position, and update
            hi_segment = parse_diagnosis_codes(segment)
            # Re-index for multiple HI segments in same claim
            hi_segment_realigned = {
                str(int(pos) + len(claim.dx_lookup)): code
                for pos, code in hi_segment.items()
            }
            claim.dx_lookup.update(hi_segment_realigned)
            
        # Process Service Lines
        # 
        # SV1 (Professional Services):
        #   SV101 (Required) - Procedure Code Composite: HC qualifier + 5-digit HCPCS code, supports up to 4 HCPCS modifiers
        #   SV102 (Required) - Charge Amount: Format 99999999.99
        #   SV103 (Required) - Unit Type: F2 (International Unit) or UN (Units)
        #   SV104 (Required) - Unit Count: Format 9999.99 (decimals allowed)
        #   SV105 (Situational) - Place of Service Code: Required for First Steps claims
        #   SV107 (Situational) - Diagnosis Code Pointer: Links to HI segment in 2300 loop, valid values 1-8
        #
        # SV2 (Institutional Services):
        #   SV201 (Required) - Revenue Code: Facility-specific revenue code for service rendered
        #   SV202 (Required) - Procedure Code Composite: HC qualifier + 5-digit HCPCS code, supports up to 4 HCPCS modifiers
        #   SV203 (Required) - Charge Amount: Format 99999999.99
        #   SV204 (Required) - Unit Type: DA (Days) or UN (Units)
        #   SV205 (Required) - Unit Count: Format 9999999.999 (whole numbers only - fractional quantities not recognized)
        #   NOTE: Diagnosis Code Pointer is not supported for SV2
        #
        # ===== SERVICE LINE (SV1/SV2 segments - 2400 loop) =====
        elif seg_id in ['SV1', 'SV2']:
            linked_diagnoses = []
            
            if seg_id == 'SV1':
                # SV1 Professional Service
                proc_info = get_segment_value(segment, 1, '').split(':')
                procedure_code = proc_info[1] if len(proc_info) > 1 else None
                modifiers = proc_info[2:] if len(proc_info) > 2 else []
                quantity = parse_amount(get_segment_value(segment, 4))
                place_of_service = get_segment_value(segment, 5)
                
                # Get diagnosis pointers and resolve to actual codes
                dx_pointers = get_segment_value(segment, 7, '')
                linked_diagnoses = [
                    claim.dx_lookup[pointer]
                    for pointer in (dx_pointers.split(':') if dx_pointers else [])
                    if pointer in claim.dx_lookup
                ]
            else:
                # SV2 Institutional Service
                revenue_code = get_segment_value(segment, 1)
                proc_info = get_segment_value(segment, 2, '').split(':')
                procedure_code = proc_info[1] if len(proc_info) > 1 else None
                modifiers = proc_info[2:] if len(proc_info) > 2 else []
                quantity = parse_amount(get_segment_value(segment, 5))
                place_of_service = None
            
            # Get service line details (NDC, dates) - lookback from current segment index
            ndc, service_date = process_service_line(segments, i)
            
            # Determine effective patient ID (prefer patient level, fallback to subscriber)
            effective_patient_id = (
                hierarchy.patient_patient_id or 
                hierarchy.subscriber_patient_id
            )
            
            # Create service level data
            service_data = ServiceLevelData(
                claim_id=claim.claim_id,
                procedure_code=procedure_code,
                linked_diagnosis_codes=linked_diagnoses,
                claim_diagnosis_codes=list(claim.dx_lookup.values()),
                claim_type=claim_type,
                provider_specialty=claim.provider_specialty,
                performing_provider_npi=claim.performing_provider_npi,  # ✅ Correct field
                billing_provider_npi=hierarchy.billing_provider_npi,
                patient_id=effective_patient_id,
                facility_type=claim.facility_type,
                service_type=claim.service_type,
                service_date=service_date,
                place_of_service=place_of_service,
                quantity=quantity,
                modifiers=modifiers,
                ndc=ndc,
                allowed_amount=None
            )
            slds.append(service_data)
    
    return slds


def extract_sld_837(content: str) -> List[ServiceLevelData]:
   
    if not content:
        raise ValueError("Input X12 data cannot be empty")
    
    # Split content into segments
    segments = [seg.strip().split('*') 
                for seg in content.split('~') if seg.strip()]
    
    # Detect claim type from GS segment
    claim_type = None
    for segment in segments:
        if segment[0] == 'GS' and len(segment) > 8:
            claim_type = CLAIM_TYPES.get(segment[8])
            break
    
    if not claim_type:
        raise ValueError("Invalid or unsupported 837 format")
    
    split_segments = split_into_claims(segments)
    slds = []
    for claim_segments in split_segments:
        slds.extend(parse_837_claim_to_sld(claim_segments, claim_type))
    
    return slds
    
