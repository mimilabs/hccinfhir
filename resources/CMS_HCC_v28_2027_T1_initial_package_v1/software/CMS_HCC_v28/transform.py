import pandas as pd
import logging
import os
import sys

# Add the software directory to sys.path
software_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'software'))
if software_path not in sys.path:
    sys.path.insert(0, software_path)
    
# Import software modules and configurables    
from common.CMS_HCC_utils import *
from CMS_HCC_v28.config import run_spec, main_filepaths
from common.utils import map_ccs_to_hccs, map_ccs_to_hccs, get_bene_hcc_counts

'''
Purpose: 
    Calculate risk scores for input beneficiaries given ICD10 diagnoses and CMS HCC model mapping criteria.
Requires:
    configured run_spec variable in ./software/CMS_HCC_v28/config.py with preferred settings
    user-defined person-level file saved in ./software/CMS_HCC_v28/data/input/user_defined/ as 'beneficiaries.csv'
    user-defined diagnosis file saved in ./software/CMS_HCC_v28/data/input/user_defined_data/ as 'diagnoses.csv'
Returns:
    person-level continued enrollee (CE) and new enrollee (NE) scores saved in 
    ./software/CMS_HCC_v28/data/output
    log saved in ./software/CMS_HCC_v28/logs
'''

def transform_bene_hcc(run_spec: dict, filepaths: dict):
    """
    Generate beneficiary HCC data and risk scores

    Parameters:
    - run_spec: Dictionary containing run specifications.
    - filepaths: Dictionary containing file paths for input and output files.
    """
    logging.basicConfig(filename=filepaths['log_output_filepath'], filemode='w', level=logging.DEBUG)
    
    try:
        logging.info('Loading data')
        beneficiaries_df = pd.read_csv(filepaths['beneficiaries_filepath'])
        diagnosis_df = pd.read_csv(filepaths['diagnoses_filepath'])
        mappings_df = pd.read_csv(filepaths['mappings_filepath'], low_memory=False)
        hcc_hierarchies_df = pd.read_csv(filepaths['hcc_hierarchies_filepath'])
        ce_coefficients_df = pd.read_csv(filepaths['ce_coefficients_filepath'])
        ne_coefficients_df = pd.read_csv(filepaths['ne_coefficients_filepath'])
        interactions_df = pd.read_csv(filepaths['interactions_filepath'])
        diagnosis_categories_df = pd.read_csv(filepaths['diagnosis_categories_filepath'])
        
        logging.info('Creating beneficiary info tables')
        bene_info_df = get_bene_info_df(beneficiaries_df, run_spec['cutoff_date'], run_spec['DOB_format'])
        
        logging.info('Creating age/sex variables')
        # get age sex initialized variables for continued and new enrollees
        age_ranges, age_sex_init_vars = get_bene_age_sex_init_vars()
        ne_age_ranges, ne_age_sex_init_vars = get_bene_ne_age_sex_init_vars()
        # Apply categorizations to bene df              
        bene_age_sex_df = bene_info_df.apply(get_bene_age_sex_vars, axis=1, args=(age_sex_init_vars, age_ranges))
        bene_ne_age_sex_df = bene_info_df.apply(get_ne_bene_age_sex_vars, axis=1, args=(ne_age_sex_init_vars, ne_age_ranges))
        
        # Get bene new enrollee interaction variables
        ne_age_sex_cols = list(ne_age_sex_init_vars.keys())
        ne_interaction_cols = ['NMCAID_NORIGDIS', 'MCAID_NORIGDIS', 'NMCAID_ORIGDIS', 'MCAID_ORIGDIS']
        ne_age_sex_interaction_cols = []
        for a_col in ne_age_sex_cols:
            for i_col in ne_interaction_cols:
                if i_col == 'NMCAID_ORIGDIS' or i_col == 'MCAID_ORIGDIS':
                    # only interact with age categories 65+
                    age_ceil = a_col[-2:]
                    if age_ceil != "GT": 
                        if int(age_ceil) < 65:
                            continue
                col = f'{i_col}_{a_col}'
                ne_age_sex_interaction_cols.append(col)
                
        bene_ne_df = bene_ne_age_sex_df.copy()
        bene_ne_df.loc[:, ne_age_sex_interaction_cols] = 0
        for a_col in ne_age_sex_cols:
            for i_col in ne_interaction_cols:
                if i_col == 'NMCAID_ORIGDIS' or i_col == 'MCAID_ORIGDIS':
                    age_ceil = a_col[-2:]
                    if age_ceil != "GT": 
                        if int(age_ceil) < 65:
                            continue
                col = f'{i_col}_{a_col}'
                bene_ne_df[col] = (bene_ne_df[a_col] * bene_ne_df[i_col]).astype(int)
        
        logging.info('Mapping ICD-10 diagnoses to CCs')
        # Initialize beneficiary CCs
        hierarchies_list = hcc_hierarchies_df['HCC'].unique().tolist()
        cc_cols = [hcc.replace('HCC', 'CC') for hcc in hierarchies_list]
        bene_info_cc_init_df = bene_age_sex_df.copy()
        bene_info_cc_init_df.loc[:, cc_cols] = 0
        
        # Get switch for MCE age edits 
        switch_edits = run_spec['switch_edits']
        # Get bene diagnosis CCs
        bene_info_cc_df = get_bene_diagnosis_ccs(
            bene_info_cc_init_df, diagnosis_df, mappings_df, switch_edits)

        # Recode CCs based on model version rules 
        condition_cols = ['CC221','CC222','CC224','CC225','CC226']
        ids_to_fix = bene_info_cc_init_df.loc[
            (bene_info_cc_init_df['CC223'] == 1) &
            (bene_info_cc_init_df[condition_cols] == 0).all(axis=1),
            'ID'
        ].unique()
        bene_info_cc_init_df.loc[bene_info_cc_init_df['ID'].isin(ids_to_fix), 'CC223'] = 0

        logging.info('Transforming CCs to HCCs')
        # Get bene HCCs
        bene_info_cc_hcc_df = map_ccs_to_hccs(bene_info_cc_df, hcc_hierarchies_df)
        
        logging.info('Adding diagnosis category variables')
        # Get diagnosis categories and initialize dataframe
        diagnosis_category_cols = diagnosis_categories_df['diag_category'].unique().tolist()
        bene_info_cc_hcc_diag_df = bene_info_cc_hcc_df.copy()
        bene_info_cc_hcc_diag_df.loc[:, diagnosis_category_cols] = 0
        # For each diagnosis category, check if bene has any HCCs in that category
        hcc_cols = diagnosis_categories_df.drop('diag_category', axis=1).columns.tolist()
        for _, diag_row in diagnosis_categories_df.iterrows():
            diag_category = diag_row['diag_category'].rstrip()
            hcc_cols_in_category = diag_row[hcc_cols].dropna().tolist()
            # For each beneficiary, check if any of the HCCs in this category are marked as 1
            for _, bene_row in bene_info_cc_hcc_diag_df.iterrows():
                bene_id = bene_row['ID']
                if bene_row[hcc_cols_in_category].sum() >= 1:
                    # Flag bene for diagnosis category
                    bene_info_cc_hcc_diag_df.loc[bene_info_cc_hcc_diag_df['ID'] == bene_id, diag_category] = 1

       
        logging.info('Creating HCC count variables for V28')
        count_vals = [1,2,3,4,5,6,7,8,9,10]
        count_cols = []
        for val in count_vals:
            count_col = f'D{val}' if val < 10 else 'D10P'
            count_cols.append(count_col)
        bene_info_cc_hcc_diag_df.loc[:, count_cols] = 0
        bene_info_cc_hcc_diag_df = get_bene_hcc_counts(count_vals, bene_info_cc_hcc_diag_df, hcc_prefix='HCC', count_col_prefix='D')
    
        logging.info('Getting interaction variables')
        # Get interaction variables and initIalize dataframe
        interactions_df['interaction'].dropna(inplace=True)
        interaction_cols = interactions_df['interaction'].unique().tolist()
        bene_info_cc_hcc_diag_df.loc[:, interaction_cols] = 0
        # For each interaction, check variable flags
        for _, interaction_row in interactions_df.iterrows():
            interaction_var = interaction_row['interaction']
            var_1 = interaction_row['var_1'].rstrip()
            var_2 = interaction_row['var_2'].rstrip()
            # For each beneficiary, create interaction variable by multiplying var_1 and var_2
            for _, bene_row in bene_info_cc_hcc_diag_df.iterrows():
                bene_id = bene_row['ID']
                val_1 = bene_row.get(var_1, 0)
                val_2 = bene_row.get(var_2, 0)
                interaction_value = val_1 * val_2
                bene_info_cc_hcc_diag_df.loc[bene_info_cc_hcc_diag_df['ID'] == bene_id, interaction_var] = interaction_value

        logging.info('Calculating CE Scores')
        # Initialize CE flag columns        
        coef_col_names = [
            ce_coefficients_df.columns[2], ce_coefficients_df.columns[3], ce_coefficients_df.columns[4],
            ce_coefficients_df.columns[5], ce_coefficients_df.columns[6], ce_coefficients_df.columns[7], 
            ce_coefficients_df.columns[8]
        ]
        score_col_names = []
        for col in coef_col_names:
            score_col_names.append(f'SCORE_{col}')
        ce_flags_df = bene_info_cc_hcc_diag_df.copy()
        ce_flags_df.loc[:, score_col_names] = 0
        ce_coefficients_df.dropna(subset=['Variable'], inplace=True)
        # Calculate scores
        for bene_id in bene_info_cc_hcc_diag_df['ID']:
            for coef_col in coef_col_names:
                score_col_name = f'SCORE_{coef_col}'
                ce_flags_df[score_col_name] = ce_flags_df[score_col_name].astype('float64')
                total_score = 0.0
                for _, coef_row in ce_coefficients_df.iterrows():
                    variable = coef_row['Variable']
                    coefficient = coef_row[coef_col]
                    if not pd.isna(coefficient):
                        bene_value = bene_info_cc_hcc_diag_df.loc[bene_info_cc_hcc_diag_df['ID'] == bene_id, variable].values[0]
                        total_score += float(bene_value * coefficient)
                ce_flags_df.loc[ce_flags_df['ID'] == bene_id, score_col_name] = total_score
        
        logging.info('Calculating NE Scores')
        # InitIalize NE flag columns
        ne_coef_1_col_name = ne_coefficients_df.columns[2]  # First model coefficient column
        ne_coef_2_col_name = ne_coefficients_df.columns[3]
        ne_coef_col_names = [ne_coef_1_col_name, ne_coef_2_col_name]
        ne_coefficients_df.dropna(subset=['Variable'], inplace=True)
        all_flags_df = ce_flags_df.copy()
        ne_score_col_names = []
        for col in ne_coef_col_names:
            ne_score_col_names.append(f'SCORE_{col}')
        all_flags_df.loc[:, ne_score_col_names] = 0
        # Add NE flags to bene_ne_df
        all_flags_df = pd.merge(all_flags_df, bene_ne_df[['ID'] + ne_age_sex_cols + ne_age_sex_interaction_cols], on='ID', how='left')
        # Calculate NE
        for bene_id in bene_ne_df['ID']:
            for coef_col in ne_coef_col_names:
                score_col_name = f'SCORE_{coef_col}'
                all_flags_df[score_col_name] = all_flags_df[score_col_name].astype('float64')
                total_score = 0.0
                for _, coef_row in ne_coefficients_df.iterrows():
                    variable = coef_row['Variable']
                    coefficient = coef_row[coef_col]
                    bene_value = bene_ne_df.loc[bene_ne_df['ID'] == bene_id, variable].values[0]
                    total_score += float(bene_value * coefficient)
                
                all_flags_df.loc[all_flags_df['ID'] == bene_id, score_col_name] = total_score
                
        # Round all scores to the 3rd decimal 
        all_score_cols = score_col_names + ne_score_col_names
        for col in all_score_cols:
            all_flags_df[col] = all_flags_df[col].round(3)
       
        logging.info(f'Writing scoring output to csv at {filepaths["score_output_filepath"]}')
        all_flags_df.to_csv(filepaths['score_output_filepath'], index=False)
        logging.info('Complete - exiting program')
        
        print('Transformation complete.')
        log_filepath = filepaths['log_output_filepath']
        print(f'log file saved to {log_filepath}')
        scores_output_filepath = filepaths['score_output_filepath']
        print(f'score output file saved to {scores_output_filepath}')
        
    except Exception as e:
        logging.error(f'Error occurred: {e}')
        print(f'Error occurred: {e}')
        raise e

def main():
    transform_bene_hcc(run_spec, main_filepaths)
     
if __name__ == "__main__":
    main()
        
        
        