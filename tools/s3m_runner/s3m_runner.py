"""
S3M Runner Tool
__date__ = '20210615'
__version__ = '1.0.1'
__author__ =
        'Francesco Avanzi' (francesco.avanzi@cimafoundation.org',
        'Fabio Delogu' (fabio.delogu@cimafoundation.org'

__library__ = 's3m'

General command line:
python s3m_runner.py -settings_file "configuration.json" -time "2021-04-20 22:33" -domain "Lombardia"

Version(s):
20210614 (1.0.1)
20210607 (1.0.0) --> First release
"""
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Library
import logging
import os
import argparse
import pandas as pd
import time

from lib_utils_logging import set_logging_file
from lib_utils_time import set_time
from lib_data_io_json import read_file_settings
from lib_info_args import logger_name, time_format_algorithm
from lib_namelist import read_namelist_file, modify_namelist, write_namelist_file
from lib_utils_system import copy_file, fill_tags2string

# Logging
log_stream = logging.getLogger(logger_name)
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Algorithm information
project_name = 'S3M'
alg_name = 'TOOL S3M RUNNER'
alg_type = 'Model'
alg_version = '1.0.0'
alg_release = '2021-06-07'
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Script Main
def main():

    # -------------------------------------------------------------------------------------
    # Get algorithm settings
    alg_settings, alg_time, alg_domain = get_args()
    alg_time_timestamp = pd.to_datetime(alg_time)

    # Set algorithm settings
    data_settings = read_file_settings(alg_settings)

    # Replace domain info
    if alg_domain is not None:
        data_settings['algorithm']['ancillary']['domain_name'] = alg_domain

    # Set algorithm logging
    folder_tag = {'source_file_datetime_generic': alg_time_timestamp,
                'domain_name': data_settings['algorithm']['ancillary']['domain_name']}
    log_folder_name = data_settings['log']['folder_name']
    log_folder_name = fill_tags2string(log_folder_name, data_settings['algorithm']['template'], folder_tag)

    name_tag = {'domain_name': data_settings['algorithm']['ancillary']['domain_name']}
    file_name = data_settings['log']['file_name']
    file_name = fill_tags2string(file_name, data_settings['algorithm']['template'], name_tag)

    set_logging_file(
        logger_name=logger_name,
        logger_file=os.path.join(log_folder_name, file_name))
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Info algorithm
    log_stream.info(' ============================================================================ ')
    log_stream.info('[' + project_name + ' ' + alg_type + ' - ' + alg_name + ' (Version ' + alg_version +
                    ' - Release ' + alg_release + ')]')
    log_stream.info(' ==> START ... ')
    log_stream.info(' ')

    # Time algorithm information
    alg_time_start = time.time()
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Organize time run
    time_run, time_range, time_chunks = set_time(
        time_run_args=alg_time,
        time_run_file=data_settings['time']['time_run'],
        time_run_file_start=data_settings['time']['time_start'],
        time_run_file_end=data_settings['time']['time_end'],
        time_format=time_format_algorithm,
        time_period=data_settings['time']['time_period'],
        time_frequency=data_settings['time']['time_frequency'],
        time_rounding=data_settings['time']['time_rounding']
    )
    # -------------------------------------------------------------------------------------
    # Read default namelist
    filename_namelist_default = os.path.join(data_settings['data']['infofile']['source']['folder_name'],
                                             data_settings['data']['infofile']['source']['file_name'])
    namelist_default = read_namelist_file(filename_namelist_default)
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Change lines in namelist
    namelist_edited = modify_namelist(namelist_default, data_settings['S3M_Info'],
                                               data_settings['algorithm']['template'],
                                               data_settings['algorithm']['ancillary'],
                                               time_range, data_settings['time'])
    # -------------------------------------------------------------------------------------
    # Save edited namelist
    path_namelist_dst = os.path.join(data_settings['data']['infofile']['destination']['folder_name'],
                                         data_settings['data']['infofile']['destination']['file_name'])
    path_namelist_dst = fill_tags2string(path_namelist_dst, data_settings['algorithm']['template'], folder_tag)
    write_namelist_file(path_namelist_dst, namelist_edited, data_settings['algorithm']['template'],
                                               data_settings['algorithm']['ancillary'])

    # -------------------------------------------------------------------------------------
    # Run model
    path_exe = os.path.join(data_settings['data']['exe']['source']['folder_name'],
                            data_settings['data']['exe']['source']['file_name'])
    path_run = data_settings['data']['folder_run']
    path_run = fill_tags2string(path_run, data_settings['algorithm']['template'], folder_tag)
    os.chdir(path_run)
    os.system(path_exe + " " + path_namelist_dst)

    # -------------------------------------------------------------------------------------
    # Info algorithm
    alg_time_elapsed = round(time.time() - alg_time_start, 1)

    logging.info(' ')
    logging.info('[' + project_name + ' ' + alg_type + ' - ' + alg_name + ' (Version ' + alg_version +
                 ' - Release ' + alg_release + ')]')
    logging.info(' ==> TIME ELAPSED: ' + str(alg_time_elapsed) + ' seconds')
    logging.info(' ==> ... END')
    logging.info(' ==> Bye, Bye')
    logging.info(' ============================================================================ ')
    # -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to fill path names
def fill_script_settings(data_settings, domain):
    path_settings = {}

    for k, d in data_settings['path'].items():
        for k1, strValue in d.items():
            if isinstance(strValue, str):
                if '{' in strValue:
                    strValue = strValue.replace('{domain}', domain)
            path_settings[k1] = strValue

    return path_settings
# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Method to get script argument(s)
def get_args():
    parser_handle = argparse.ArgumentParser()
    parser_handle.add_argument('-settings_file', action="store", dest="alg_settings")
    parser_handle.add_argument('-time', action="store", dest="alg_time")
    parser_handle.add_argument('-domain', action="store", dest="alg_domain")
    parser_values = parser_handle.parse_args()

    if parser_values.alg_settings:
        alg_settings = parser_values.alg_settings
    else:
        alg_settings = 'configuration.json'

    if parser_values.alg_time:
        alg_time = parser_values.alg_time
    else:
        alg_time = None

    if parser_values.alg_domain:
        alg_domain = parser_values.alg_domain
    else:
        alg_time = None

    return alg_settings, alg_time, alg_domain

# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Method to set logging information
def set_logging(logger_file='log.txt', logger_format=None):
    if logger_format is None:
        logger_format = '%(asctime)s %(name)-12s %(levelname)-8s ' \
                        '%(filename)s:[%(lineno)-6s - %(funcName)20s()] %(message)s'

    # Remove old logging file
    if os.path.exists(logger_file):
        os.remove(logger_file)

    # Set level of root debugger
    logging.root.setLevel(logging.DEBUG)

    # Open logging basic configuration
    logging.basicConfig(level=logging.DEBUG, format=logger_format, filename=logger_file, filemode='w')

    # Set logger handle
    logger_handle_1 = logging.FileHandler(logger_file, 'w')
    logger_handle_2 = logging.StreamHandler()
    # Set logger level
    logger_handle_1.setLevel(logging.DEBUG)
    logger_handle_2.setLevel(logging.DEBUG)
    # Set logger formatter
    logger_formatter = logging.Formatter(logger_format)
    logger_handle_1.setFormatter(logger_formatter)
    logger_handle_2.setFormatter(logger_formatter)

    # Add handle to logging
    logging.getLogger('').addHandler(logger_handle_1)
    logging.getLogger('').addHandler(logger_handle_2)

# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Call script from external library
if __name__ == "__main__":
    main()
# -------------------------------------------------------------------------------------
