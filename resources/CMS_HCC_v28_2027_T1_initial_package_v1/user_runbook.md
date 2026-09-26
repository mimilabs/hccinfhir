# User Run Steps 

## Prerequisites
Ensure that Python is installed. Ensure that Python has been installed properly by checking the version in the terminal or shell window, using the following command: 

```bash
python --version
```

It is recommended that a more recent version of Python is downloaded, specifically version 3.12 or higher. Otherwise, syntax errors may occur. 

Use pip to install the package dependencies in `./requirement.txt` from the base `./` project folder. Run the following command:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file includes version numbers for pandas and numpy, common Python data manipulation libraries. Depending on the version of Python installed, a different version of pandas may need to be installed. Pandas version 2.3.3, the version listed in the `requirements.txt` file, is generally compatible with Python version 3.12 or higher. 

## Software Configuration
The software folder contains code relevant to the specific CMS software package as well as common code used throughout CMS software packages. Within the designated software package folder `./software`, locate the `readme.md` file and follow steps to set program parameters in the `./software/<package_name>/config.py` file, where `<package_name>` is replaced by the relevant model folder name, and add input data to the `./software/<package_name>/data/input/user-defined/` folder. 

## Run Software
After the software configuration steps are complete, navigate to the base `./` directory and run the transform script using the following Python command, replacing `<package_name>` with the relevant model folder name:

``` bash
python ./software/<package_name>/transform.py
```

When the transform step is complete, locate the log for the program, written to `./software/<package_name>/logs/`. The log file will contain print statements for each completed step and any error information. If errors occur, first check that the user-defined input data is in the correct format. If all steps run without errors, locate the final output data table located in the `./software/<package_name>/data/output/` folder.