import os 
from datetime import datetime

'''
Purpose: Define CMS HCC configurable and program-defined parameters.
Requires: User input for software specifications.
'''

'''
====================================================================
USER-DEFINED PARAMETERS
User must configure the following parameters to meet software needs
Please note the values provided are examples and must match the user's specifications.

run_spec: dictionary defining software run specifications with variables for any user-defined parameters
    
    switch_edits: indicates the use of MCE (Medicare Code Editor) age criteria when performing the ICD-10 mappings
    
    DOB_format: indicates the date of birth format in the user-defined beneficiaries file, such that the string is a type of format
                recognized by the python datetime library, ie. an example of "%Y%m%d" would be 19500121, and 
                an example of "%m/%d/%Y" would be 1/21/1950
====================================================================
'''
run_spec = {
    'switch_edits': True, # set to True to apply MCE age conditions during ICD-10 to CC mappings, False to not apply
    'DOB_format': "%m/%d/%Y" # set according the the DOB provided in the user-defined beneficiaries input file
} 


''' 
====================================================================
DO NOT EDIT ANY REMAINING PARAMETERS
====================================================================
'''

'''
RTI PROGRAM-DEFINED PARAMETERS: user does not need to modify the following parameters
'''
model_name = "CMS_HCC"
model_sub_version = 'v28'
model_folder_name = f"{model_name}_{model_sub_version}"
base_folder = 'software'
package_sub_version = "T1"

# Define cutoff date for age calculations as February 1 of the payment year
is_initial_software = True
payment_year = 2027
cutoff_date = datetime(payment_year, 2, 1)
run_spec['cutoff_date'] = cutoff_date

# Define filepaths for user input 
user_data_basepath = f'./{base_folder}/{model_folder_name}/data/input/user_defined/'
person_level_input_filename = 'beneficiaries.csv'
diagnoses_input_filename = 'diagnoses.csv'
beneficiaries_filepath = os.path.join(user_data_basepath, person_level_input_filename)
diagnoses_filepath = os.path.join(user_data_basepath, diagnoses_input_filename)

# Define filepaths for internal data
internal_data_basepath = f'./{base_folder}/{model_folder_name}/data/input/internal/'

mappings_filepath = os.path.join(internal_data_basepath, f'ICD10_CC_mappings_{model_name}_{payment_year}_{model_sub_version}{"_initial" if is_initial_software else ''}.csv')
hcc_hierarchies_filepath = os.path.join(internal_data_basepath, f'{model_sub_version.upper()}_HCC_Hierarchies.csv')
ce_relative_factors_filepath = os.path.join(internal_data_basepath, f'{model_sub_version.upper()}_CE_Relative_Factors.csv')
ne_relative_factors_filepath = os.path.join(internal_data_basepath, f'{model_sub_version.upper()}_NE_Relative_Factors.csv')
diagnosis_categories_filepath = os.path.join(internal_data_basepath, f'{model_sub_version.upper()}_Diagnosis_Categories.csv')
interactions_filepath = os.path.join(internal_data_basepath, f'{model_sub_version.upper()}_Interactions.csv')

# Output file paths
output_basepath = f'./{base_folder}/{model_folder_name}/data/output/'
score_output_filepath = os.path.join(output_basepath, f'{model_name}_{model_sub_version}_{payment_year}_{package_sub_version}_{'initial_' if is_initial_software else ''}scores.csv')
log_output_filepath = os.path.join(f'./{base_folder}/{model_folder_name}/logs',
                                   f'{model_name}_{model_sub_version}_{payment_year}_{package_sub_version}_{'initial_' if is_initial_software else ''}software_log.txt')

# Define main filepaths df
main_filepaths = {
    'beneficiaries_filepath': beneficiaries_filepath,
    'diagnoses_filepath': diagnoses_filepath,
    'mappings_filepath': mappings_filepath,
    'hcc_hierarchies_filepath': hcc_hierarchies_filepath,
    'ce_coefficients_filepath': ce_relative_factors_filepath,
    'ne_coefficients_filepath': ne_relative_factors_filepath,
    'diagnosis_categories_filepath': diagnosis_categories_filepath,
    'interactions_filepath': interactions_filepath,
    'score_output_filepath': score_output_filepath,
    'log_output_filepath': log_output_filepath
}