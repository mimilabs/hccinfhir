import re
from datetime import datetime
import pandas as pd

def calculate_age(birthdate: datetime, cutoff_date: datetime):
    """
    Calculate age as of the cutoff_date.
    Args:
        birthdate (datetime): The person's birth date.
        cutoff_date (datetime): The date to calculate age as of.
    Returns:
        int: Age in years.
    """
    years = cutoff_date.year - birthdate.year
    # If birthdate has not occurred yet in the cutoff year, subtract one year
    if cutoff_date.month < birthdate.month:
        years -= 1
    elif cutoff_date.month == birthdate.month and cutoff_date.day < birthdate.day:
        years -= 1
    return years

def normalize_expression(expr: str):
    '''
    Extracts minimal necessary info from an age condition formatted as an inequality string.
    '''
    expr = expr.strip().lower()

    # Replace 'age 50+' → 'age >= 50'
    expr = re.sub(r'age\s*(\d+)\s*\+', r'age >= \1', expr)
    # Replace '=' with '==', but not '>=' or '<='
    expr = re.sub(r'(?<![<>!])=', '==', expr)
    # Ensure spacing around operators
    expr = re.sub(r'([<>=!]=?)', r' \1 ', expr)
    # Remove multiple spaces
    expr = re.sub(r'\s+', ' ', expr)

    return expr.strip()

def evaluate_age_rule(expr: str, age: int):
    '''
    Evaluates a condition in the form of an inequality string on the age.
    Returns true if age satisfies the condition, otherwise false. 
    '''
    try:
        normalized_expr = normalize_expression(expr)
        return eval(normalized_expr, {"__builtins__": {}}, {"age": age})
    except Exception as e:
        raise ValueError(f"Error evaluating '{expr}' with age={age}: {e}")
    
def safe_int(x):
    if pd.isna(x):
        return None
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None
            
def cc_to_col(cc):
    '''
    Returns col value where the CC value is read as a float and returned in format
    '''
    cc = str(cc).replace('_', '.')
    try:
        f = float(cc)
    except (ValueError, TypeError):
        return cc
    if f.is_integer():
        return str(int(f))
    # avoid scientific notation, trim trailing zeros and trailing dot
    return ('%f' % f).rstrip('0').rstrip('.').replace('.', '_')
    
def map_ccs_to_hccs(bene_ccs_df, hcc_hierarchies_df, hcc_prefix: str = ''):
    '''
    Takes df with at least cols for bene ID and CC cols. 
    Assumes hcc_hierarchies_df has column 'HCC' followed by any exclusion columns.
    Returns returns original df with CCs transformed to HCCs.
    '''
    # Initialize table with HCCs
    bene_hccs_init_df = bene_ccs_df.copy()
    hcc_col_prefix = hcc_prefix + "HCC"
    cc_col_prefix = hcc_prefix + "CC"
    cc_cols = [c for c in bene_ccs_df.columns if c.startswith(cc_col_prefix)]
    bene_hccs_init_df = bene_hccs_init_df.rename(
        columns={col: col.replace(cc_col_prefix, hcc_col_prefix, 1) for col in cc_cols}
    )
    hcc_cols = [c for c in bene_hccs_init_df.columns if c.startswith(hcc_col_prefix)]
        
    # Apply exclusions
    exclusion_cols = hcc_hierarchies_df.columns.drop(hcc_col_prefix).tolist()
    
    # Make a copy so that indexes can be located in the init df and zeros are applied in final df
    bene_hccs_final_df = bene_hccs_init_df.copy()
    
    for _, hierarchy_row in hcc_hierarchies_df.iterrows(): 
        hcc_val = hierarchy_row[hcc_col_prefix]
        # Standardize HCC naming 
        hcc_val = str(hcc_val).replace(hcc_col_prefix, '')
        hcc_col = f"{hcc_col_prefix}{cc_to_col(hcc_val)}"
        # Assign exclusions
        if hcc_col in hcc_cols:
            for exclusion_col in exclusion_cols: 
                exclusion_val = hierarchy_row[exclusion_col]
                if  str(exclusion_val).startswith(hcc_col_prefix):
                    exclusion_val = exclusion_val.replace(hcc_col_prefix, '')
                if not pd.isna(exclusion_val):   # Check for valid exclusion
                    hcc_exclusion_col = f"{hcc_col_prefix}{cc_to_col(exclusion_val)}"
                    if hcc_exclusion_col in hcc_cols:
                        # Collect exclusions from  init df so exclusions aren't prematurely zeroed out
                        row_exclusion_indexes = bene_hccs_init_df.loc[
                            (bene_hccs_init_df[hcc_exclusion_col] == 1) & (bene_hccs_init_df[hcc_col] == 1)
                            ].index.tolist()
                        for row_index in row_exclusion_indexes: 
                            bene_hccs_final_df.loc[row_index, hcc_exclusion_col] = 0


    # Add CCs to HCCs
    common_keys = [c for c in bene_ccs_df.columns if c in bene_hccs_final_df.columns]

    # regular left merge (preserves left row order)
    bene_info_cc_hcc_df = pd.merge(bene_ccs_df, bene_hccs_final_df, on=common_keys,
                    how='left', sort=False)
        
    return bene_info_cc_hcc_df

def get_bene_hcc_counts(hcc_count_vals: list[int], bene_hccs_df, hcc_prefix: str = "HCC", count_col_prefix: str = "HCC_COUNT"): 
    '''
    For each bene row in df, count number of HCCs present and create count cols that indicate whether the 
    count is equal to a provided value of interest
    '''
    bene_hcc_counts_df = pd.DataFrame(bene_hccs_df.copy())
    hcc_cols = [col for col in bene_hcc_counts_df.columns if col.startswith(hcc_prefix)]
    total_cnt_col_name = f'{hcc_prefix}_pymt'
    bene_hcc_counts_df[total_cnt_col_name] = bene_hcc_counts_df[hcc_cols].sum(axis=1)
    for count_val in hcc_count_vals: 
        count_col_name = f'{count_col_prefix}{count_val}'
        # account for greater than values for the desired counts
        if count_val == 10:
            count_col_name = count_col_name + 'P'
            bene_hcc_counts_df[count_col_name] = (bene_hcc_counts_df[hcc_cols].sum(axis=1) >= count_val).astype(int)
        else: 
            bene_hcc_counts_df[count_col_name] = (bene_hcc_counts_df[hcc_cols].sum(axis=1) == count_val).astype(int)
    return pd.DataFrame(bene_hcc_counts_df)
