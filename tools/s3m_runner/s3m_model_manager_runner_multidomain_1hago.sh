#!/bin/bash -e

#-----------------------------------------------------------------------------------------
# Script information
script_name='S3M MODEL - REALTIME MULTIDOMAIN RUNNER'
script_version="1.0.0"
script_date='2021/06/07'

virtualenv_folder='/home/s3m/fp_virtualenv_python3/'
virtualenv_name='fp_virtualenv_python3_hyde_libraries'
script_folder='/home/s3m/s3m_runner/'

# Domain list
domain_name_list=("Valle_Aosta" "Piemonte")

# Most recent input file to look for in order to start
check_file_path_trunk='/home/s3m_domains/Sicilia/%Y/%m/%d/'
check_file_name='MeteoData_%Y%m%d%H%M.nc.gz'
searching_period_hour_obs=2

nclibrary_source='/home/fp_env_system' 

# Execution example:
# python3 s3m_runner.py -settings_file s3m_configuration_runner_realtime.json -time "2020-11-02 12:00" -domain "Lombardia"
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Get file information
script_file='/home/s3m_runner.py'
settings_algorithm='/home/s3m_configuration_runner_realtime.json'

# Get information (-u to get gmt time)
time_now=$(date -u +"%Y-%m-%d %H:00" -d "1 hour ago")
#time_now='2021-06-03 13:14' # DEBUG
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Activate virtualenv
export PATH=$virtualenv_folder/bin:$PATH
source activate $virtualenv_name

# Add path to pythonpath
export PYTHONPATH="${PYTHONPATH}:$script_folder"
#-----------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------
# Activate nc library
source $nclibrary_source

# ----------------------------------------------------------------------------------------
# Info script start
echo " ==================================================================================="
echo " ==> "$script_name" (Version: "$script_version" Release_Date: "$script_date")"
echo " ==> START ..."
echo " ===> EXECUTION ..."
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
	# Search obs latest filename
	echo " =====> SEARCH LATEST OBS FILENAME ..."
	for hour in $(seq 0 $searching_period_hour_obs); do

		# ----------------------------------------------------------------------------------------
		# Get time step
		time_step_obs=$(date -d "$time_now ${hour} hour ago" +'%Y-%m-%d %H:00')
		# ----------------------------------------------------------------------------------------

		# ----------------------------------------------------------------------------------------
		# Info time start
		echo " ======> TIME_STEP "$time_step_obs" ... "

		timestep_this_hour_file=$(date -u -d "$time_step_obs" +"%Y%m%d%H%M")
		timestep_this_hour_folder=$(date -u -d "$time_step_obs" +"%Y/%m/%d/")
		# ----------------------------------------------------------------------------------------

		# ----------------------------------------------------------------------------------------
		# Define dynamic folder(s)
		folder_name_obs_step=${check_file_path_trunk/'%Y/%m/%d/'/$timestep_this_hour_folder}
		file_name_obs_step=${check_file_name/'%Y%m%d%H%M'/$timestep_this_hour_file}
		# ----------------------------------------------------------------------------------------

		# ----------------------------------------------------------------------------------------
		# Search obs file name
		echo " =======> FILENAME ${file_name_obs_step} ... "
		# Create local folder
		if [ -f "${folder_name_obs_step}${file_name_obs_step}" ]; then
		    echo " =======> FILENAME ${file_name_obs_step} ... FOUND"
		    echo " ======> TIME_STEP "$time_step_obs" ... DONE"
		    time_step_obs_ref=$time_step_obs
		    file_name_obs_flag=true
		    break
		else
		    echo " =======> FILENAME ${file_name_obs_step} ... NOT FOUND"
		    echo " ======> TIME_STEP "$time_step_obs" ... FAILED"
		    file_name_obs_flag=false
		fi
		# ----------------------------------------------------------------------------------------

	done
	echo " =====> SEARCH LATEST OBS FILENAME ... DONE"
	echo " =====> COONDITION IS ... "$file_name_obs_flag" "
	# ----------------------------------------------------------------------------------------

if  $file_name_obs_flag ; then
  #-----------------------------------------------------------------------------------------
  # Iterate over domain list
  for domain_name_name in ${domain_name_list[@]}; do
    (

    # ----------------------------------------------------------------------------------------
    # Info domain name
    echo " ====> DOMAIN NAME "$domain_name_name" ... "

      #-----------------------------------------------------------------------------------------
      # Info start model run
      echo " =====> RUN S3m RUNNER [DOMAIN: $domain_name_name :: TIME: $time_now] ... "

      # Run python script
      python3 $script_file -settings_file $settings_algorithm -time "$time_now" -domain "$domain_name_name"
      #-----------------------------------------------------------------------------------------

    sleep 5

      ) &
  done

  # Wait processe(s)
  wait

else
  echo " =====> RUNNER NOT EXECUTED BECAUSE OF MISSING INPUT FILES!!"

fi
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Info script end
echo " ===> EXECUTION ... DONE"
echo " ==> "$script_name" (Version: "$script_version" Release_Date: "$script_date")"
echo " ==> Bye, Bye"
echo " ==================================================================================="
# ----------------------------------------------------------------------------------------



