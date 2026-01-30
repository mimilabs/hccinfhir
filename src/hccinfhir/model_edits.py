from typing import Dict, Set, Tuple, Union, Optional, NamedTuple
from hccinfhir.datamodels import ModelName


class EditRule(NamedTuple):
    """Represents a single edit rule from ra_dx_edits.csv"""
    edit_type: str          # "sex" or "age"
    sex: Optional[str]      # For sex edits: "1" (male) or "2" (female)
    age_min: Optional[int]  # For age edits: minimum age (inclusive), None if not set
    age_max: Optional[int]  # For age edits: maximum age (inclusive), None if not set
    action: str             # "invalid" or "override"
    cc_override: Optional[str]  # CC to assign when action is "override"


def apply_edits(
    cc_to_dx: Dict[str, Set[str]],
    age: Union[int, float],
    sex: str,
    model_name: ModelName,
    edits_mapping: Dict[Tuple[str, ModelName], EditRule]
) -> Dict[str, Set[str]]:
    """
    Apply age/sex edits to CC mappings based on CMS edit rules.

    This implements the hardcoded edits from CMS SAS macro V28I0ED (and similar).
    Edits are applied AFTER initial ICD->CC mapping but BEFORE hierarchies.

    Edit types:
    - invalid: Remove the diagnosis (don't assign any CC)
    - override: Assign a different CC than the default mapping

    Args:
        cc_to_dx: Dictionary mapping CC codes to sets of diagnosis codes
        age: Patient's age
        sex: Patient's sex ('M', 'F', '1', or '2')
        model_name: HCC model name
        edits_mapping: Dictionary mapping (icd10, model_name) to EditRule

    Returns:
        Modified cc_to_dx dictionary with edits applied
    """
    # Normalize sex to CMS format ("1" = male, "2" = female)
    sex_normalized = sex
    if sex == 'M':
        sex_normalized = '1'
    elif sex == 'F':
        sex_normalized = '2'

    # Collect all diagnoses across all CCs for edit checking
    all_dx_to_cc: Dict[str, str] = {}
    for cc, dx_set in cc_to_dx.items():
        for dx in dx_set:
            all_dx_to_cc[dx] = cc

    # Track modifications
    dx_to_remove: Dict[str, str] = {}  # dx -> original cc (to remove)
    dx_to_override: Dict[str, Tuple[str, str]] = {}  # dx -> (original cc, new cc)

    for dx, original_cc in all_dx_to_cc.items():
        edit_key = (dx, model_name)
        if edit_key not in edits_mapping:
            continue

        rule = edits_mapping[edit_key]
        should_apply = False

        if rule.edit_type == "sex":
            # Sex-based edit: apply if patient sex matches the rule's sex
            if rule.sex == sex_normalized:
                should_apply = True

        elif rule.edit_type == "age":
            # Age-based edit: check age bounds
            # age_max set means "if age <= age_max" (e.g., age < 50 means age_max=49)
            # age_min set means "if age >= age_min" (e.g., age >= 2 means age_min=2)
            if rule.age_max is not None and age <= rule.age_max:
                should_apply = True
            elif rule.age_min is not None and age >= rule.age_min:
                should_apply = True

        if should_apply:
            if rule.action == "invalid":
                dx_to_remove[dx] = original_cc
            elif rule.action == "override" and rule.cc_override:
                dx_to_override[dx] = (original_cc, rule.cc_override)

    # Apply removals
    for dx, original_cc in dx_to_remove.items():
        if original_cc in cc_to_dx and dx in cc_to_dx[original_cc]:
            cc_to_dx[original_cc].discard(dx)
            # Remove CC entirely if no diagnoses left
            if not cc_to_dx[original_cc]:
                del cc_to_dx[original_cc]

    # Apply overrides
    for dx, (original_cc, new_cc) in dx_to_override.items():
        # Remove from original CC
        if original_cc in cc_to_dx and dx in cc_to_dx[original_cc]:
            cc_to_dx[original_cc].discard(dx)
            if not cc_to_dx[original_cc]:
                del cc_to_dx[original_cc]

        # Add to new CC
        if new_cc not in cc_to_dx:
            cc_to_dx[new_cc] = set()
        cc_to_dx[new_cc].add(dx)

    return cc_to_dx
