# Purpose 
This program creates CMS HCC risk factor scores for a set of beneficiaries with ICD-10 diagnoses. 

# Output
Scoring output contains all continued enrollee and new enrollee flags and variables for each person regardless of enrollment status, leaving the user to decide which variables are relevant for each person. 

# User Run Steps
1. Follow steps 1 and 2 in the user_runbook.md to ensure that all requirements are installed.

2. Edit user-defined parameters in the run_spec variable within the config.py file, located in the ./software/CMS_HCC_v28 folder. The file has variables initialized such that the user is only expected to change the value of the following variables within the run_spec dictionary.

•	switch_edits – a Boolean value indicating the use of MCE (Medicare Code Editor) age criteria when performing the ICD-10 mappings, see run_spec (a dictionary with keys indicating switch values) to indicate True or False
•	DOB_format: indicates the date of birth format in the user-defined beneficiaries file, such that the string is a type of format recognized by the python datetime library, ie. an example of "%Y%m%d" would be 19500121, and an example of "%m/%d/%Y" would be 1/21/1950

3. Navigate to the local ./data/input/user_defined folder and add data to the following files (empty files have been provided):

beneficiaries.csv – includes demographic and enrollment information with the following variables
•	ID – unique identifier, string or numeric (will programmatically be converted to a string for consistency)
•	DOB – string value in format specified in the run_spec in the config.py file
•	SEX – integer value coded 1 for male and 2 for female
•	OREC – integer value coded as 0 (old age or OASI), 1 (disability or DIB), 2 (ESRD), or 3 (both DIB and ESRD)
•	LTIMCAID – indicator variable for Medicaid enrollment (in the payment year)
•	NEMCAID – indicator variable for Medicaid enrollment (in the payment year) for New Enrollees 

diagnoses.csv – a diagnosis file with at least one record per beneficiary, includes the following variables 
•	ID – unique identifier, must be consistent with beneficiaries.csv
•	ICD10 – string value with no special characters, user may include all diagnoses or limit the codes to those used by the model
NOTE: ICD10 codes should be to the greatest level of available specificity. Diagnoses should be included only from acceptable sources.

4. Run the program from the the base folder (the folder that contains the software folder, not the inside the software folder) using the following command: 
            python ./software/CMS_HCC_v28/transform.py

When the transform step is complete, locate the log for the program (./software/CMS_HCC_v28/logs). The log file will contain print statements for each completed step and any error information. If errors occur, first check that the user-defined input data is in the correct format. If all steps run without errors, locate the final output data table located in the ./software/CMS_HCC_v28/data/output folder.