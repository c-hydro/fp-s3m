#!/bin/bash -e

#-----------------------------------------------------------------------------------------
# Script information
script_name='S3M - POSTPROCESSING - MERGER'
script_version="1.0.0"
script_date='2021/10/29'

virtualenv_folder=''
virtualenv_name=''
script_folder=''

# Execution example:
# python3 s3m_postprocessing_merger.py -settings_file s3m_postprocessing_merger.json -time "2020-11-02 12:00"
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Get file information
script_file=''
settings_file=''

# Get information (-u to get gmt time)
#time_now=$(date -u +"%Y-%m-%d %H:%M" -d "23:15 1 day ago")
time_now='2021-10-20 23:15' # DEBUG 
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

