"""
CMS Risk Adjustment Domain Constants

This module contains constants used across the HCC risk adjustment system,
including dual eligibility codes, OREC/CREC values, and state-specific mappings.

References:
- CMS Rate Announcement and Call Letter
- Medicare Advantage Enrollment and Disenrollment Guidance
- X12 834 Implementation Guides
"""

from typing import Set, Dict

# =============================================================================
# DUAL ELIGIBILITY CODES
# =============================================================================
# CMS Dual Eligibility Status Codes (Medicare + Medicaid)
# Used in coefficient prefix selection (CNA_, CFA_, CPA_, etc.)

VALID_DUAL_CODES: Set[str] = {'00', '01', '02', '03', '04', '05', '06', '08'}

# Non-Dual Eligible
NON_DUAL_CODE: str = '00'

# Full Benefit Dual Eligible (receive both Medicare and full Medicaid benefits)
# Uses CFA_ (Community, Full Benefit Dual, Aged) or CFD_ (Disabled) prefixes
FULL_BENEFIT_DUAL_CODES: Set[str] = {
    '02',  # QMB Plus (Qualified Medicare Beneficiary Plus)
    '04',  # SLMB Plus (Specified Low-Income Medicare Beneficiary Plus)
    '08',  # Other Full Benefit Dual Eligible
}

# Partial Benefit Dual Eligible (Medicare + limited Medicaid)
# Uses CPA_ (Community, Partial Benefit Dual, Aged) or CPD_ (Disabled) prefixes
PARTIAL_BENEFIT_DUAL_CODES: Set[str] = {
    '01',  # QMB Only
    '03',  # SLMB Only
    '05',  # QDWI (Qualified Disabled and Working Individual)
    '06',  # QI (Qualifying Individual)
}

# =============================================================================
# OREC - Original Reason for Entitlement Code
# =============================================================================
# Determines if beneficiary has ESRD and affects coefficient prefix selection

VALID_OREC_VALUES: Set[str] = {'0', '1', '2', '3'}

OREC_DESCRIPTIONS: Dict[str, str] = {
    '0': 'Old Age and Survivors Insurance (OASI)',
    '1': 'Disability Insurance Benefits (DIB)',
    '2': 'ESRD - End-Stage Renal Disease',
    '3': 'DIB and ESRD',
}

# OREC codes indicating ESRD status (per CMS documentation)
OREC_ESRD_CODES: Set[str] = {'2', '3'}

# =============================================================================
# CREC - Current Reason for Entitlement Code
# =============================================================================
# Current entitlement status (may differ from OREC)

VALID_CREC_VALUES: Set[str] = {'0', '1', '2', '3'}

CREC_DESCRIPTIONS: Dict[str, str] = {
    '0': 'Old Age and Survivors Insurance (OASI)',
    '1': 'Disability Insurance Benefits (DIB)',
    '2': 'ESRD - End-Stage Renal Disease',
    '3': 'DIB and ESRD',
}

# CREC codes indicating ESRD status
CREC_ESRD_CODES: Set[str] = {'2', '3'}

# =============================================================================
# COEFFICIENT PREFIX GROUPS
# =============================================================================
# Used for prefix_override logic in model_demographics.py

# ESRD model prefixes
ESRD_PREFIXES: Set[str] = {'DI_', 'DNE_', 'GI_', 'GNE_', 'GFPA_', 'GFPN_', 'GNPA_', 'GNPN_'}

# CMS-HCC new enrollee prefixes
NEW_ENROLLEE_PREFIXES: Set[str] = {'NE_', 'SNPNE_', 'DNE_', 'GNE_'}

# CMS-HCC community prefixes
COMMUNITY_PREFIXES: Set[str] = {'CNA_', 'CND_', 'CFA_', 'CFD_', 'CPA_', 'CPD_'}

# Institutionalized prefixes
INSTITUTIONAL_PREFIXES: Set[str] = {'INS_', 'GI_'}

# Full Benefit Dual prefixes
FULL_BENEFIT_DUAL_PREFIXES: Set[str] = {'CFA_', 'CFD_', 'GFPA_', 'GFPN_'}

# Partial Benefit Dual prefixes
PARTIAL_BENEFIT_DUAL_PREFIXES: Set[str] = {'CPA_', 'CPD_'}

# Non-Dual prefixes
NON_DUAL_PREFIXES: Set[str] = {'CNA_', 'CND_', 'GNPA_', 'GNPN_'}

# =============================================================================
# DEMOGRAPHIC CODES
# =============================================================================

VALID_SEX_CODES: Set[str] = {'M', 'F'}

# X12 834 Gender Code mappings
X12_SEX_CODE_MAPPING: Dict[str, str] = {
    'M': 'M',
    'F': 'F',
    '1': 'M',  # X12 numeric code
    '2': 'F',  # X12 numeric code
}

# =============================================================================
# X12 834 MAINTENANCE TYPE CODES
# =============================================================================
# INS03 - Maintenance Type Code

MAINTENANCE_TYPE_CHANGE: str = '001'
MAINTENANCE_TYPE_ADD: str = '021'
MAINTENANCE_TYPE_CANCEL: str = '024'
MAINTENANCE_TYPE_REINSTATE: str = '025'

MAINTENANCE_TYPE_DESCRIPTIONS: Dict[str, str] = {
    '001': 'Change',
    '021': 'Addition',
    '024': 'Cancellation/Termination',
    '025': 'Reinstatement',
}

# =============================================================================
# STATE-SPECIFIC MAPPINGS
# =============================================================================

# -----------------------------------------------------------------------------
# California DHCS Medi-Cal Aid Codes
# -----------------------------------------------------------------------------
# Maps California-specific aid codes to CMS dual eligibility codes
# Source: California DHCS 834 Implementation Guide

MEDI_CAL_AID_CODES: Dict[str, str] = {
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

# -----------------------------------------------------------------------------
# Medicare Status Code Mappings
# -----------------------------------------------------------------------------
# Maps Medicare status codes (from various sources) to CMS dual eligibility codes
# Used in X12 834 REF*ABB segment and other payer files

MEDICARE_STATUS_CODE_MAPPING: Dict[str, str] = {
    # QMB - Qualified Medicare Beneficiary
    'QMB': '01',         # QMB Only (Partial)
    'QMBONLY': '01',
    'QMBPLUS': '02',     # QMB Plus (Full Benefit)
    'QMB+': '02',

    # SLMB - Specified Low-Income Medicare Beneficiary
    'SLMB': '03',        # SLMB Only (Partial)
    'SLMBONLY': '03',
    'SLMBPLUS': '04',    # SLMB Plus (Full Benefit)
    'SLMB+': '04',

    # Other dual eligibility programs
    'QDWI': '05',        # Qualified Disabled and Working Individual
    'QI': '06',          # Qualifying Individual
    'QI1': '06',
    'FBDE': '08',        # Full Benefit Dual Eligible (Other)
    'OTHERFULL': '08',
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_full_benefit_dual(dual_code: str) -> bool:
    """Check if dual eligibility code is Full Benefit Dual"""
    return dual_code in FULL_BENEFIT_DUAL_CODES

def is_partial_benefit_dual(dual_code: str) -> bool:
    """Check if dual eligibility code is Partial Benefit Dual"""
    return dual_code in PARTIAL_BENEFIT_DUAL_CODES

def is_esrd_by_orec(orec: str) -> bool:
    """Check if OREC indicates ESRD status"""
    return orec in OREC_ESRD_CODES

def is_esrd_by_crec(crec: str) -> bool:
    """Check if CREC indicates ESRD status"""
    return crec in CREC_ESRD_CODES

def normalize_medicare_status_code(status: str) -> str:
    """Normalize Medicare status code (uppercase, no spaces/hyphens)"""
    if not status:
        return ''
    return status.upper().replace(' ', '').replace('-', '')

def map_medicare_status_to_dual_code(status: str) -> str:
    """Map Medicare status code to dual eligibility code

    Args:
        status: Medicare status code (e.g., 'QMB Plus', 'SLMB', 'QI')

    Returns:
        Dual eligibility code ('01'-'08') or '00' if not found
    """
    if not status:
        return NON_DUAL_CODE

    normalized = normalize_medicare_status_code(status)
    return MEDICARE_STATUS_CODE_MAPPING.get(normalized, NON_DUAL_CODE)

def map_aid_code_to_dual_status(aid_code: str) -> str:
    """Map California Medi-Cal aid code to dual eligibility code

    Args:
        aid_code: California aid code (e.g., '4N', '5B')

    Returns:
        Dual eligibility code ('01'-'08') or '00' if not found
    """
    if not aid_code:
        return NON_DUAL_CODE

    return MEDI_CAL_AID_CODES.get(aid_code, NON_DUAL_CODE)
