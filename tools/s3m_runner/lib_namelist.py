"""
Library Features:

Name:          lib_namelist
Author(s):     Francesco Avanzi (francesco.avanzi@cimafoundation.org), Fabio Delogu (fabio.delogu@cimafoundation.org)
Date:          '20210607'
Version:       '3.0.0'
"""

#######################################################################################
# Library
import logging
import numpy as np

from lib_default_args import logger_name

from lib_utils_list import convert_list_2_string
from lib_utils_fortran import define_var_format
from lib_utils_system import fill_tags2string

import os
import pandas as pd

# Logging
log_stream = logging.getLogger(logger_name)

# Debug
# import matplotlib.pylab as plt
#######################################################################################

# --------------------------------------------------------------------------------
# Method to read namelist
def read_namelist_file(filename_namelist):

    if os.path.exists(filename_namelist):
        f = open(filename_namelist, "r")
        namelist_default = f.readlines()
    else:
        log_stream.error(' ===> Default namelist not found!')
        raise NotImplemented('Check filepath for filename_namelist')

    return namelist_default

# --------------------------------------------------------------------------------
# Method to write namelist
def write_namelist_file(filename_namelist, namelist, template, ancillary_info):

    # replace ancillary_info tags if present
    filename_namelist = fill_tags2string(filename_namelist, template, ancillary_info)

    folder, filename = os.path.split(filename_namelist)
    if os.path.exists(folder) is False:
        os.makedirs(folder)

    f = open(filename_namelist, "w")
    f.writelines(namelist)

# --------------------------------------------------------------------------------
# Method to modify namelist based on dictionary
def modify_namelist(namelist_default, data_settings_dict, template,
                    ancillary_info, time_range, settings_time, time_reverse=True):

    #manage rounding to midnight
    if 'round_to_previous_midnight' in settings_time.keys():
        if settings_time['round_to_previous_midnight']:

            timestamp_end = time_range[0]
            timestamp_start = time_range[-1].floor('D')
            time_range = pd.date_range(start=timestamp_start, end=timestamp_end, freq=settings_time['time_frequency'])
            if time_reverse:
                time_range = time_range[::-1]

    for group_tag, group_dict in data_settings_dict.items():
        for variable_name, variable_value in group_dict.items():

            #replace ancillary_info tags if present
            if isinstance(variable_value, str):
                variable_value = fill_tags2string(variable_value, template, ancillary_info)

            #handle simulation length
            if (variable_name == "iSimLength") & (variable_value is None):
                variable_value = time_range.size - 1

            #handle simulation start and end
            if (variable_name == "sTimeStart") & (variable_value is None):
                if "tag_sim_start_and_restart" in ancillary_info.keys():

                    tag_to_replace = {}
                    if time_reverse:
                        tag_to_replace[ancillary_info["tag_sim_start_and_restart"]] = time_range[-1]
                    else:
                        tag_to_replace[ancillary_info["tag_sim_start_and_restart"]] = time_range[0]
                    variable_value = '{' + ancillary_info["tag_sim_start_and_restart"] + '}'
                    variable_value = fill_tags2string(variable_value, template, tag_to_replace)

                else:
                    log_stream.error(' ===> tag_sim_start_and_restart not found in ancillary_info!')
                    raise NotImplemented('Check configuration file')

            if (variable_name == "sTimeRestart") & (variable_value is None):
                if "tag_sim_start_and_restart" in ancillary_info.keys():

                    tag_to_replace = {}
                    if time_reverse:
                        tag_to_replace[ancillary_info["tag_sim_start_and_restart"]] = time_range[-1] - pd.Timedelta(
                            hours=1)
                    else:
                        tag_to_replace[ancillary_info["tag_sim_start_and_restart"]] = time_range[0] - pd.Timedelta(
                            hours=1)

                    tag_to_replace[ancillary_info["tag_sim_start_and_restart"]] = time_range[-1] - pd.Timedelta(hours=1)
                    variable_value = '{' + ancillary_info["tag_sim_start_and_restart"] + '}'
                    variable_value = fill_tags2string(variable_value, template, tag_to_replace)

                else:
                    log_stream.error(' ===> tag_sim_start_and_restart not found in ancillary_info!')
                    raise NotImplemented('Check configuration file')

            #find line with variable_name
            index = [idx for idx, s in enumerate(namelist_default) if variable_name in s][0]
            if index >= 0:
                new_line = write_namelist_line(variable_name, variable_value)
                namelist_default[index] = new_line
            else:
                log_stream.error(' ===> ' + variable_name + ' not found in namelist!')
                raise NotImplemented('Check filename_namelist')

    return namelist_default

# --------------------------------------------------------------------------------
# Method to write line namelist
def write_namelist_line(variable_name, variable_value):

    # Check variable value type
    if isinstance(variable_value, str):
        variable_value_str = variable_value
        variable_value_str = '"' + variable_value_str + '"'
    elif isinstance(variable_value, int):
        variable_value_str = str(int(variable_value))
    elif isinstance(variable_value, float):
        variable_value_str = str(float(variable_value))
    elif isinstance(variable_value, list):
        variable_value_str = convert_list_2_string(variable_value, ',')
    else:
        variable_value_str = str(variable_value)

    # Line definition in Fortran style
    line = str(variable_name) + ' = ' + variable_value_str + '\n'
    return line

# --------------------------------------------------------------------------------



