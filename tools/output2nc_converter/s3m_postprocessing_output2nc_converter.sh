#!/bin/bash -e

#-----------------------------------------------------------------------------------------
# Script information
script_name='S3M - POSTPROCESSING - OUTPUT2NC CONVERTER'
script_version="1.0.0"
script_date='2022/07/05'

virtualenv_folder='/home/fp_virtualenv_python3/'
virtualenv_name='fp_virtualenv_python3_hyde_libraries'
script_folder='/home/s3m_output2nc_converter/'

# Execution example:
# python3 s3m_postprocessing_output2nc_converter.py -settings_file s3m_postprocessing_output2nc_converter.json -time "2020-11-02 12:00"
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Get file information
script_file='/home/fp-s3m/tools/s3m_output2nc_converter/s3m_postprocessing_output2nc_converter.py'
settings_file='/home/s3m_postprocessing_output2nc_converter.json'

# Get information (-u to get gmt time)
#time_now=$(date -u +"%Y-%m-%d %H:%M" -d "23:15 1 day ago")
time_now='2021-08-31 11:15' # DEBUG 
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Activate virtualenv
export PATH=$virtualenv_folder/bin:$PATH
source activate $virtualenv_name

# Add path to pythonpath
export PYTHONPATH="${PYTHONPATH}:$script_folder"
#-----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Info script start
echo " ==================================================================================="
echo " ==> "$script_name" (Version: "$script_version" Release_Date: "$script_date")"
echo " ==> START ..."
echo " ==> COMMAND LINE: " python3 $script_file -settings_file $settings_file -time $time_now

# Run python script (using setting and time)
python3 $script_file -settings_file $settings_file -time "$time_now"

# Info script end
echo " ==> "$script_name" (Version: "$script_version" Release_Date: "$script_date")"
echo " ==> ... END"
echo " ==> Bye, Bye"
echo " ==================================================================================="
# ----------------------------------------------------------------------------------------

