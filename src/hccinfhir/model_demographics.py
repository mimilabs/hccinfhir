from typing import Union, Optional
from hccinfhir.datamodels import Demographics, PrefixOverride
from hccinfhir.constants import (
    FULL_BENEFIT_DUAL_CODES,
    PARTIAL_BENEFIT_DUAL_CODES,
    OREC_ESRD_CODES,
    CREC_ESRD_CODES,
    ESRD_PREFIXES,
    NEW_ENROLLEE_PREFIXES,
    COMMUNITY_PREFIXES,
    INSTITUTIONAL_PREFIXES,
    FULL_BENEFIT_DUAL_PREFIXES,
    PARTIAL_BENEFIT_DUAL_PREFIXES,
    NON_DUAL_PREFIXES,
)
    
def categorize_demographics(age: Union[int, float],
                       sex: str,
                       dual_elgbl_cd: str = None,
                       orec: str = None,
                       crec: str = None,
                       version: str = 'V2',
                       new_enrollee: bool = False,
                       snp: bool = False,
                       low_income: bool = False,
                       lti: bool = False,
                       graft_months: int = None,
                       prefix_override: Optional[PrefixOverride] = None
                       ) -> Demographics:
    """
    Categorize a beneficiary's demographics into risk adjustment categories.

    This function takes demographic information about a beneficiary and returns a Demographics
    object containing derived fields used in risk adjustment models.

    Args:
        age: Beneficiary age (integer or float, will be floored to integer)
        sex: Beneficiary sex ('M'/'F' or '1'/'2')
        dual_elgbl_cd: Dual eligibility code ('00'-'10')
        orec: Original reason for entitlement code ('0'-'3')
        crec: Current reason for entitlement code ('0'-'3')
        version: Version of categorization to use ('V2', 'V4', 'V6')
        new_enrollee: Whether beneficiary is a new enrollee
        snp: Whether beneficiary is in a Special Needs Plan
        low_income: Whether beneficiary is low income (RxHCC only)
        lti: Whether beneficiary is long-term institutionalized
        graft_months: Number of months since transplant (ESRD only)
        prefix_override: Optional prefix to override demographic detection
            (e.g., 'DI_', 'DNE_', 'INS_', 'CFA_', etc.)

    Returns:
        Demographics object containing derived fields like age/sex category,
        disability status, dual status flags, etc.

    Raises:
        ValueError: If age is negative or non-numeric, or if sex is invalid
    """
    
    if not isinstance(age, (int, float)):
        raise ValueError("Age must be a number")
    
    if age < 0:
        raise ValueError("Age must be non-negative")
        
    # Convert to integer using floor
    age = int(age)
    non_aged = age <= 64

    # Standardize sex input
    if sex in ('M', '1'):
        std_sex = '1'  # For V2/V4
        v6_sex = 'M'   # For V6
    elif sex in ('F', '2'):
        std_sex = '2'  # For V2/V4
        v6_sex = 'F'   # For V6
    else:
        raise ValueError("Sex must be 'M', 'F', '1', or '2'")
    
    # Determine if person is disabled or originally disabled
    # SAS code:
    # DISABL = (&AGEF < 65 & &OREC ne "0");
    # ORIGDS  = (&OREC = '1')*(DISABL = 0);
    # The vairable names can be misleading. 
    # disabled is true if the person is disabled and the age is less than 65
    # - basically, the person is in Medicare due to disability not due to age
    # orig_disabled is true if the person started Medicare due to disability, but now aged in
    # - basically, the person is in Medicare due to age (not disability anymore)
    disabled = age < 65 and (orec is not None and orec != "0")
    orig_disabled = (orec is not None and orec == '1') and not disabled

    # Reference: https://resdac.org/cms-data/variables/medicare-medicaid-dual-eligibility-code-january
    is_fbd = dual_elgbl_cd in FULL_BENEFIT_DUAL_CODES
    is_pbd = dual_elgbl_cd in PARTIAL_BENEFIT_DUAL_CODES

    # ESRD detection from OREC/CREC (CMS official codes: 2=ESRD, 3=DIB+ESRD)
    esrd_orec = orec in OREC_ESRD_CODES
    esrd_crec = crec in CREC_ESRD_CODES if crec else False
    esrd = esrd_orec or esrd_crec

    # Override demographics based on prefix_override
    if prefix_override:
        # Set esrd flag
        if prefix_override in ESRD_PREFIXES:
            esrd = True

        # Set new_enrollee flag
        if prefix_override in NEW_ENROLLEE_PREFIXES:
            new_enrollee = True
        elif prefix_override in COMMUNITY_PREFIXES or prefix_override in INSTITUTIONAL_PREFIXES:
            new_enrollee = False

        # Set dual eligibility flags based on prefix
        if prefix_override in FULL_BENEFIT_DUAL_PREFIXES:
            is_fbd = True
            is_pbd = False
        elif prefix_override in PARTIAL_BENEFIT_DUAL_PREFIXES:
            is_fbd = False
            is_pbd = True
        elif prefix_override in NON_DUAL_PREFIXES:
            is_fbd = False
            is_pbd = False

        # Set lti flag based on prefix
        if prefix_override in INSTITUTIONAL_PREFIXES:
            lti = True

    result_dict = {
        'version': version,
        'non_aged': non_aged,
        'orig_disabled': orig_disabled,
        'disabled': disabled,
        'age': age,
        'sex': std_sex if version in ('V2', 'V4') else v6_sex,
        'dual_elgbl_cd': dual_elgbl_cd,
        'orec': orec,
        'crec': crec,
        'new_enrollee': new_enrollee,
        'snp': snp,
        'fbd': is_fbd,
        'pbd': is_pbd,
        'esrd': esrd,
        'lti': lti,
        'graft_months': graft_months,
        'low_income': low_income
    }

    # V6 Logic (ACA Population)
    if version == 'V6':
        age_ranges = [
            (0, 0, '0_0'),
            (1, 1, '1_1'),
            (2, 4, '2_4'),
            (5, 9, '5_9'),
            (10, 14, '10_14'),
            (15, 20, '15_20'),
            (21, 24, '21_24'),
            (25, 29, '25_29'),
            (30, 34, '30_34'),
            (35, 39, '35_39'),
            (40, 44, '40_44'),
            (45, 49, '45_49'),
            (50, 54, '50_54'),
            (55, 59, '55_59'),
            (60, float('inf'), '60_GT')
        ]
        
        for low, high, label in age_ranges:
            if low <= age <= high:
                result_dict['category'] = f"{v6_sex}AGE_LAST_{label}"
                return Demographics(**result_dict)
    
    # V2/V4 Logic (Medicare Population)
    elif version in ('V2', 'V4'):
        if orec is None or orec == '':
            orec = '0' # Default to 0 if OREC is None

        # Determine prefix based on new_enrollee status
        if new_enrollee:
            prefix = 'NEF' if std_sex == '2' else 'NEM'
        else:
            prefix = 'F' if std_sex == '2' else 'M'

        # CMS-HCC new enrollee logic with detailed 65-69 categories
        if new_enrollee and not esrd:
            if age <= 34:
                category = f'{prefix}0_34'
            elif 34 < age <= 44:
                category = f'{prefix}35_44'
            elif 44 < age <= 54:
                category = f'{prefix}45_54'
            elif 54 < age <= 59:
                category = f'{prefix}55_59'
            elif (59 < age <= 63) or (age == 64 and orec != '0'):
                category = f'{prefix}60_64'
            elif (age == 64 and orec == '0') or age == 65:
                category = f'{prefix}65'
            elif age == 66:
                category = f'{prefix}66'
            elif age == 67:
                category = f'{prefix}67'
            elif age == 68:
                category = f'{prefix}68'
            elif age == 69:
                category = f'{prefix}69'
            elif 69 < age <= 74:
                category = f'{prefix}70_74'
            elif 74 < age <= 79:
                category = f'{prefix}75_79'
            elif 79 < age <= 84:
                category = f'{prefix}80_84'
            elif 84 < age <= 89:
                category = f'{prefix}85_89'
            elif 89 < age <= 94:
                category = f'{prefix}90_94'
            else:
                category = f'{prefix}95_GT'

        # Standard logic with grouped 65_69 (for non-new-enrollee OR ESRD)
        else:
            age_ranges = [
                (0, 34, '0_34'),
                (34, 44, '35_44'),
                (44, 54, '45_54'),
                (54, 59, '55_59'),
                (59, 64, '60_64'),
                (64, 69, '65_69'),
                (69, 74, '70_74'),
                (74, 79, '75_79'),
                (79, 84, '80_84'),
                (84, 89, '85_89'),
                (89, 94, '90_94'),
                (94, float('inf'), '95_GT')
            ]

            for low, high, suffix in age_ranges:
                if low < age <= high:
                    category = f'{prefix}{suffix}'
                    break
            else:
                raise ValueError(f"Unable to categorize age: {age}")
        
        result_dict['category'] = category
        return Demographics(**result_dict)
    
    else:
        raise ValueError("Version must be 'V2', 'V4', or 'V6'")