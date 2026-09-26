import pandas as pd
from datetime import datetime
from common.utils import calculate_age, evaluate_age_rule

def get_bene_info_df(beneficiaries_df: pd.DataFrame, cutoff_date: datetime, DOB_format: str) -> pd.DataFrame:
    '''
    Extract beneficiary information and calculate age.
    '''
    expected_cols = ['ID', 'DOB', 'SEX', 'OREC', 'LTIMCAID', 'NEMCAID']
    for col in expected_cols:
        assert col in beneficiaries_df.columns, f"Column {col} is missing from person-level DataFrame"

    # Filter for beneficiaries with non-null IDs
    bene_info_df = beneficiaries_df[beneficiaries_df['ID'].notnull()].copy()
    # Get age from DOB as of cutoff date from config 
    bene_info_df['AGE'] = bene_info_df['DOB'].apply(lambda dob: calculate_age(datetime.strptime(str(dob), DOB_format).date(), cutoff_date))
    # Get disabled status
    bene_info_df['DISABL'] = bene_info_df.apply(
        lambda row: 1 if (row['AGE'] < 65 and row['OREC'] in [1, 2, 3]) else 0, axis=1
    )
    # Get originally disabled status
    bene_info_df['ORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['OREC'] == 1 and row['DISABL'] == 0) else 0, axis=1
    )
    bene_info_df['OriginallyDisabled_Female'] = bene_info_df.apply(
        lambda row: 1 if (row['SEX'] == 2 and row['ORIGDIS'] == 1) else 0, axis=1
    )
    bene_info_df['OriginallyDisabled_Male'] = bene_info_df.apply(
        lambda row: 1 if (row['SEX'] == 1 and row['ORIGDIS'] == 1) else 0, axis=1
    )
    bene_info_df['NE_ORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['AGE'] >= 65 and row['OREC'] == 1) else 0, axis=1
    )
    bene_info_df['NMCAID_NORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['NEMCAID'] == 0 and row['NE_ORIGDIS'] == 0) else 0, axis=1
    )
    bene_info_df['MCAID_NORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['NEMCAID'] == 1 and row['NE_ORIGDIS'] == 0) else 0, axis=1
    )
    bene_info_df['NMCAID_ORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['NEMCAID'] == 0 and row['NE_ORIGDIS'] == 1 and row['AGE'] >= 65) else 0, axis=1
    )
    bene_info_df['MCAID_ORIGDIS'] = bene_info_df.apply(
        lambda row: 1 if (row['NEMCAID'] == 1 and row['NE_ORIGDIS'] == 1 and row['AGE'] >= 65) else 0, axis=1
    )
    return bene_info_df

def get_bene_age_sex_init_vars() -> tuple[list, dict]: 
    '''
    Initialize age/sex variables
    '''
    age_ranges = [
        (0, 34), (35, 44), (45, 54), (55, 59), (60, 64),
        (65, 69), (70, 74), (75, 79), (80, 84), (85, 89), (90, 94), (95, None)
    ]
    
    age_sex_init_vars = {}
    for start, stop in age_ranges:
        for sex_char in ['F', 'M']:
            var_name = f'{sex_char}{start}_{stop if stop is not None else 'GT'}'
            age_sex_init_vars[var_name] = 0
    
    return age_ranges, age_sex_init_vars

def get_bene_age_sex_vars(bene_row: pd.Series, age_sex_init_vars: dict, age_ranges: list) -> pd.Series:
    '''
    For bene in bene_row, marks applicable age/sex categories in the initialized dict and returns
    bene row with age/sex vars added. 
    '''
    age = bene_row['AGE']
    sex = bene_row['SEX']
    
    sex_char = 'M' if sex == 1 else 'F' if sex == 2 else None
    if not sex_char:
        raise ValueError(
            f'Invalid sex value: {sex} for bene id {bene_row['ID']}')
    # Copy init vars for specified row
    age_sex_row = age_sex_init_vars.copy()
    
    for start, stop in age_ranges:
        if age >= start and (stop is None or age <= stop):
            col_name = f'{sex_char}{start}_{stop if stop is not None else 'GT'}'
            age_sex_row[col_name] = 1
            break

    return pd.Series({**bene_row, **age_sex_row})

def get_bene_ne_age_sex_init_vars() -> tuple[list, dict]:
    '''
    Returns initialized new enrollee age/sex variables. 
    '''
     # Define inclusive age ranges for new enrollee (NE) variables
    ne_age_ranges = [
        (0, 34), (35, 44), (45, 54), (55, 59), (60, 64), 
        (65, 65), (66, 66), (67, 67), (68, 68), (69, 69),
        (70, 74), (75, 79), (80, 84), (85, 89), (90, 94), (95, None) 
    ]
    
    # Initialize NE cols
    ne_age_sex_init_vars = {}
    for start, stop in ne_age_ranges:
        for sex_char in ['M', 'F']:
            var_name = f'NE{sex_char}{start}'
            if start != stop: 
                var_name = var_name + f'_{stop if stop is not None else 'GT'}'
            ne_age_sex_init_vars[var_name] = 0
                
    return ne_age_ranges, ne_age_sex_init_vars

def get_ne_bene_age_sex_vars(bene_row: pd.Series, ne_age_sex_init_vars: dict, ne_age_ranges: list) -> pd.Series:
    '''
    For bene in bene_row, marks applicable age/sex categories in the initialized dict and returns
    bene row with new enrollee age/sex vars added. 
    '''
    age = int(bene_row['AGE'])  
    sex = int(bene_row['SEX'])
    orec = int(bene_row['OREC'])
    
    # Make copy for specified row 
    ne_age_sex_row = ne_age_sex_init_vars.copy()
    
    # Determine age/sex variables
    sex_char = 'M' if sex == 1 else 'F' if sex == 2 else None
    label = None
    if sex_char:
        for start, stop in ne_age_ranges:
            if age == 64:
                if start == 60 and stop == 64 and orec != 0: 
                    label = f'NE{sex_char}60_64'
                if start == 65 and stop == 65 and orec == 0: 
                    label = f'NE{sex_char}65'
            elif age >= start and (stop is None or age <= stop): 
                label =  f'NE{sex_char}{start}'
                if start != stop: 
                    label = label + f'_{stop if stop is not None else 'GT'}'
            if not label is None:
                ne_age_sex_row[label] = 1
                break            
            
    return pd.Series({**bene_row, **ne_age_sex_row})

def get_bene_diagnosis_ccs(bene_info_cc_init_df, diagnoses_df, mappings_df, switch_edits):
    '''
    Takes cc_ids from hierarchy df and compares bene diagnoses with mapping conditions to determine cc eligibility.
    '''
    # Create dataframe to track bene info, ICD10 diagnosis, and diagnosis condition criteria
    bene_diagnosis_df = pd.merge(bene_info_cc_init_df[["ID", "AGE", "SEX"]], diagnoses_df, on="ID", how="left")
    
    # Create an empty dataframe to capture valid diagnosis ICD 10 code mapping to one or more CC codes 
    bene_diagnosis_cc_df = pd.DataFrame(columns=['ID', 'ICD10', 'MODEL_CC'])
    # Note ^ this may have repeat ID/CC values, but we want to track what ICD-10 codes are mapping
    
    # Get list of CC ids
    cc_ids_list = [col for col in bene_info_cc_init_df.columns.tolist() if col.startswith('CC')]
    # Check conditions to get a valid ID, ICD10, CC pair 
    for _, bene_diagnosis_row in bene_diagnosis_df.iterrows():
        bene_diagnosis_icd_10 = bene_diagnosis_row['ICD10']
        # Get all mappings for the ICD10
        mapping_rows = mappings_df[mappings_df["ICD10"] == bene_diagnosis_icd_10]
        for _, mapping_row in mapping_rows.iterrows():
            model_cc = int(mapping_row['CC'])
            cc_col_name = f'CC{str(model_cc)}'
            
            # check conditions if applicable
            bene_id = bene_diagnosis_row['ID']
            bene_age = bene_diagnosis_row["AGE"]
            bene_sex = bene_diagnosis_row["SEX"]
            age_edit_condition = mapping_row['AGE_EDIT_CONDITION']
            sex_edit_condition = mapping_row['SEX_EDIT_CONDITION']
                    
            # Check MCE edits if switch is on, re configurable in config.py
            if switch_edits:
                # Apply conditions to bene
                mce_age_condition = mapping_row['MCE_AGE_CONDITION'] 
                if (pd.notnull(mce_age_condition) and evaluate_age_rule(mce_age_condition, bene_age) == True) or pd.isnull(mce_age_condition):
                    # Apply age edits
                    if (pd.notnull(age_edit_condition) and evaluate_age_rule(age_edit_condition, bene_age) == True) or pd.isnull(age_edit_condition):
                         if ((pd.notnull(sex_edit_condition) and (sex_edit_condition) == bene_sex)) or pd.isnull(sex_edit_condition):
                            # Diagnosis is valid
                            bene_diagnosis_cc_df = pd.concat(
                                [bene_diagnosis_cc_df, pd.DataFrame([{
                                    'ID': bene_id, 'ICD10': bene_diagnosis_icd_10, 'MODEL_CC': model_cc
                                }])],
                                ignore_index=True
                            )
                            # Add to bene diagnosis cc df if CC is in relevant hierarchies list
                            if cc_col_name in cc_ids_list:
                                bene_info_cc_init_df.loc[bene_info_cc_init_df['ID'] == bene_id, cc_col_name] = 1
                                
            else: 
                # If MCE edits are off, just check age/sex edits
                if (pd.notnull(age_edit_condition) and evaluate_age_rule(age_edit_condition, bene_age) == True) or pd.isnull(age_edit_condition):
                    if ((pd.notnull(sex_edit_condition) and (sex_edit_condition == bene_sex)) or pd.isnull(sex_edit_condition)):
                        # Diagnosis is valid
                        bene_diagnosis_cc_df = pd.concat(
                            [bene_diagnosis_cc_df, pd.DataFrame([{
                                'ID': bene_id, 'ICD10': bene_diagnosis_icd_10, 'MODEL_CC': model_cc
                            }])],
                            ignore_index=True
                        )
                        # Add to bene diagnosis cc df if CC is in relevant hierarchies list
                        if model_cc in cc_ids_list:
                            bene_info_cc_init_df.loc[bene_info_cc_init_df['ID'] == bene_id, cc_col_name] = 1      

    return bene_info_cc_init_df       