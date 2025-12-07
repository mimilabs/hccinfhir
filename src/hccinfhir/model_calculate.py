from typing import List, Union, Dict, Tuple, Set, Optional
from hccinfhir.datamodels import ModelName, RAFResult, PrefixOverride, HCCDetail
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.model_dx_to_cc import apply_mapping
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.model_coefficients import apply_coefficients
from hccinfhir.model_interactions import apply_interactions
from hccinfhir.defaults import dx_to_cc_default, hierarchies_default, is_chronic_default, coefficients_default, labels_default

def calculate_raf(diagnosis_codes: List[str],
                  model_name: ModelName = "CMS-HCC Model V28",
                  age: Union[int, float] = 65,
                  sex: str = 'F',
                  dual_elgbl_cd: str = 'NA',
                  orec: str = '0',
                  crec: str = '0',
                  new_enrollee: bool = False,
                  snp: bool = False,
                  low_income: bool = False,
                  lti: bool = False,
                  graft_months: int =  None,
                  dx_to_cc_mapping: Dict[Tuple[str, ModelName], Set[str]] = dx_to_cc_default,
                  is_chronic_mapping: Dict[Tuple[str, ModelName], bool] = is_chronic_default,
                  hierarchies_mapping: Dict[Tuple[str, ModelName], Set[str]] = hierarchies_default,
                  coefficients_mapping: Dict[Tuple[str, ModelName], float] = coefficients_default,
                  labels_mapping: Dict[Tuple[str, ModelName], str] = labels_default,
                  prefix_override: Optional[PrefixOverride] = None,
                  maci: float = 0.0,
                  norm_factor: float = 1.0,
                  frailty_score: float = 0.0) -> RAFResult:
    """
    Calculate Risk Adjustment Factor (RAF) based on diagnosis codes and demographic information.

    Args:
        diagnosis_codes: List of ICD-10 diagnosis codes.
        model_name: Name of the HCC model to use.
        age: Patient's age.
        sex: Patient's sex ('M' or 'F').
        dual_elgbl_cd: Dual eligibility code.
        orec: Original reason for entitlement code.
        crec: Current reason for entitlement code.
        new_enrollee: Whether the patient is a new enrollee.
        snp: Special Needs Plan indicator.
        low_income: Low income subsidy indicator.
        lti: Long-term institutional status indicator.
        graft_months: Number of months since transplant.
        dx_to_cc_mapping: Mapping of diagnosis codes to condition categories; defaults to packaged 2026 mappings.
        is_chronic_mapping: Mapping of HCCs to a chronic flag for the selected model; defaults to packaged mappings.
        hierarchies_mapping: Mapping of parent HCCs to child HCCs for hierarchical rules; defaults to packaged 2026 mappings.
        coefficients_mapping: Mapping of coefficient names to values; defaults to packaged 2026 mappings.
        labels_mapping: Mapping of (cc, model_name) to human-readable HCC labels; defaults to packaged 2026 mappings.
        prefix_override: Optional prefix to override auto-detected demographic prefix.
            Use when demographic categorization from orec/crec is incorrect.
            Common values: 'DI_' (ESRD Dialysis), 'DNE_' (ESRD Dialysis New Enrollee),
            'INS_' (Institutionalized), 'CFA_' (Community Full Dual Aged), etc.
        maci: Medicare Advantage coding intensity adjustment applied to payment score.
        norm_factor: Normalization factor applied to payment score.
        frailty_score: Frailty adjustment added to payment score.

    Returns:
        RAFResult with the calculated risk scores, intermediate inputs, and metadata for the model run.

    Raises:
        ValueError: If input parameters are invalid
    """
    # Input validation
    if not isinstance(age, (int, float)) or age < 0:
        raise ValueError("Age must be a non-negative number")
    
    if sex not in ['M', 'F', '1', '2']:
        raise ValueError("Sex must be 'M' or 'F' or '1' or '2'")

    version = 'V2'
    if 'RxHCC' in model_name:
        version = 'V4'
    elif 'HHS-HCC' in model_name: # not implemented yet
        version = 'V6'
    
    demographics = categorize_demographics(age,
                                           sex,
                                           dual_elgbl_cd,
                                           orec,
                                           crec,
                                           version,
                                           new_enrollee,
                                           snp,
                                           low_income,
                                           lti,
                                           graft_months,
                                           prefix_override=prefix_override)
    
    cc_to_dx = apply_mapping(diagnosis_codes,
                             model_name,
                             dx_to_cc_mapping=dx_to_cc_mapping)
    hcc_set = set(cc_to_dx.keys())
    hcc_set = apply_hierarchies(hcc_set, model_name, hierarchies_mapping)
    interactions = apply_interactions(demographics, hcc_set, model_name)
    coefficients = apply_coefficients(demographics, hcc_set, interactions, model_name,
                                     coefficients_mapping, prefix_override=prefix_override)

    hcc_chronic = set()
    interactions_chronic = {}
    for hcc in hcc_set:
        if is_chronic_mapping.get((hcc, model_name), False):
            hcc_chronic.add(hcc)
        interactions_chronic = apply_interactions(demographics, hcc_chronic, model_name)

    demographic_interactions = {}
    for key, value in interactions.items():
        if key.startswith('NMCAID_'):
            demographic_interactions[key] = value
        elif key.startswith('MCAID_'):
            demographic_interactions[key] = value
        elif key.startswith('LTI_'):
            demographic_interactions[key] = value
        elif key.startswith('OriginallyDisabled_'):
            demographic_interactions[key] = value

    coefficients_demographics = apply_coefficients(demographics,
                                                   set(),
                                                   demographic_interactions,
                                                   model_name,
                                                   coefficients_mapping,
                                                   prefix_override=prefix_override)
    coefficients_chronic_only = apply_coefficients(demographics,
                                                   hcc_chronic,
                                                   interactions_chronic,
                                                   model_name,
                                                   coefficients_mapping,
                                                   prefix_override=prefix_override)
    
    # Calculate risk scores
    #print(f"Coefficients: {coefficients}")
    risk_score = sum(coefficients.values())
    #print(f"Risk Score: {risk_score}")
    risk_score_demographics = sum(coefficients_demographics.values())
    risk_score_chronic_only = sum(coefficients_chronic_only.values()) - risk_score_demographics
    risk_score_hcc = risk_score - risk_score_demographics
    risk_score_payment = risk_score * (1 - maci) / norm_factor + frailty_score

    # Build HCC details with labels and chronic status
    hcc_details = []
    for hcc in hcc_set:
        label = labels_mapping.get((hcc, model_name))
        is_chronic = is_chronic_mapping.get((hcc, model_name), False)
        coef = coefficients.get(hcc)
        hcc_details.append(HCCDetail(
            hcc=hcc,
            label=label,
            is_chronic=is_chronic,
            coefficient=coef
        ))

    return RAFResult(
        risk_score=risk_score,
        risk_score_demographics=risk_score_demographics,
        risk_score_chronic_only=risk_score_chronic_only,
        risk_score_hcc=risk_score_hcc,
        risk_score_payment=risk_score_payment,
        hcc_list=list(hcc_set),
        hcc_details=hcc_details,
        cc_to_dx=cc_to_dx,
        coefficients=coefficients,
        interactions=interactions,
        demographics=demographics,
        model_name=model_name,
        version=version,
        diagnosis_codes=diagnosis_codes,
    )



