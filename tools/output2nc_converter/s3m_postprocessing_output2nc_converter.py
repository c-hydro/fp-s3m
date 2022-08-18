"""
S3M Postprocessing tools - output 2 netcdf file
__date__ = '20220811'
__version__ = '1.1.0'
__author__ =
        'Francesco Avanzi (francesco.avanzi@cimafoundation.org'
        'Andrea Libertino (andrea.libertino@cimafoundation.org',
        Fabio Delogu (fabio.delogu@cimafoundation.org)
__library__ = 's3m'
General command line:
### python s3m_postprocessing_output2nc_converter.py -settings_file s3m_postprocessing_output2nc_converter_example.json -time "YYYY-MM-DD HH:MM"
Version(s):
20220811 (1.1.0) --> Modified routine to export to netCDF for compatibility with QGIS and the NetCDF Climate and Forecast (CF)
Metadata Conventions
20220705 (1.0.0) --> First release.
"""
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Complete library
import logging
from os.path import join
from argparse import ArgumentParser
import pandas as pd
import xarray as xr
import numpy as np
import sys
import os
import matplotlib.pylab as plt
from time import time, strftime, gmtime
import matplotlib as mpl
from netCDF4 import Dataset,date2num
if os.environ.get('DISPLAY','') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
from shutil import copyfile

from lib_postprocessing_output2nc_converter_data_io_json import read_file_json
from lib_postprocessing_output2nc_converter_utils_time import set_time
from lib_postprocessing_output2nc_converter_info_args import time_format_algorithm
from lib_postprocessing_output2nc_converter_geo import read_file_raster
from lib_postprocessing_output2nc_converter_io_generic import fill_tags2string, unzip_filename
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Algorithm information
alg_project = 'S3M'
alg_name = 'S3M Postprocessing tools - Output 2 NetCDF converter '
alg_version = '1.1.0'
alg_release = '2022-08-11'
alg_type = 'DataDynamic'
time_format = '%Y-%m-%d %H:%M'
# -------------------------------------------------------------------------------------
# Script Main
def main():

    # -------------------------------------------------------------------------------------
    # Get algorithm settings
    [file_script, file_settings, time_arg] = get_args()

    # Set algorithm settings
    data_settings = read_file_json(file_settings)

    # Set algorithm logging
    os.makedirs(data_settings['data']['log']['folder'], exist_ok=True)
    set_logging(logger_file=join(data_settings['data']['log']['folder'], data_settings['data']['log']['filename']))
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Info algorithm
    logging.info('[' + alg_project + ' ' + alg_type + ' - ' + alg_name + ' (Version ' + alg_version + ')]')
    logging.info('[' + alg_project + '] Execution Time: ' + strftime("%Y-%m-%d %H:%M", gmtime()) + ' GMT')
    logging.info('[' + alg_project + '] Reference Time: ' + time_arg + ' GMT')
    logging.info('[' + alg_project + '] Start Program ... ')
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Time algorithm information
    start_time = time()

    # Organize time run
    time_run, time_range, time_chunks = set_time(
        time_run_args=time_arg,
        time_run_file=data_settings['time']['time_run'],
        time_run_file_start=data_settings['time']['time_start'],
        time_run_file_end=data_settings['time']['time_end'],
        time_format=time_format_algorithm,
        time_period=data_settings['time']['time_period'],
        time_frequency=data_settings['time']['time_frequency'],
        time_rounding=data_settings['time']['time_rounding'],
        time_reverse=data_settings['time']['time_reverse']
    )
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    #Load input grid
    logging.info(' --> Load input domain data ... ')
    da_domain_in, wide_domain_in, high_domain_in, proj_domain_in, transform_domain_in, \
    bounding_box_domain_in, no_data_domain_in, crs_domain_in =\
        read_file_raster(data_settings['data']['input']['input_grid'])
    logging.info(' --> Load input domain data ... DONE')
    lat_in = da_domain_in[da_domain_in.dims[0]].data
    lon_in = da_domain_in[da_domain_in.dims[1]].data

    # -------------------------------------------------------------------------------------
    #Load output grid
    logging.info(' --> Load output domain data ... ')
    da_domain_out, wide_domain_out, high_domain_out, proj_domain_out, transform_domain_out, \
    bounding_box_domain_out, no_data_domain_out, crs_domain_out = \
        read_file_raster(data_settings['data']['outcome']['output_grid'])
    logging.info(' --> Load output domain data ... DONE')
    lat_out = da_domain_out[da_domain_out.dims[0]].data
    lon_out = da_domain_out[da_domain_out.dims[1]].data
    lons_out, lats_out  = np.meshgrid(lon_out, lat_out)

    # -------------------------------------------------------------------------------------
    # Iterate over time steps
    not_available_run = 0
    for time_step in time_range:

        if data_settings['time']['time_frequency'] == 'M':

            logging.info(' --> Preparing output nc file for month ... ' + str(time_step.month))
            #get beginning of the month
            time_step_start = time_step.replace(day=1)
            time_step_end = time_step
            logging.info(' --> Month start ... ' + time_step_start.strftime("%Y-%m-%d"))
            logging.info(' --> Month end ... ' + time_step_end.strftime("%Y-%m-%d"))

            #generate DateTimeIndex of all sub-timesteps
            time_period_this_month = \
                pd.date_range(start=time_step_start, end=time_step_end, freq='D')
            logging.info(' --> Number of days ... ' + str(time_period_this_month.size))

            #create target ndarray
            size_domain_in = (lat_in.__len__(), lon_in.__len__())
            data_this_month = np.empty((time_period_this_month.__len__(), size_domain_in[0], size_domain_in[1]))
            data_this_month[:] = np.nan

            #now load maps
            for time_i, time_file in enumerate(time_period_this_month):

                #create path to map
                path_file = os.path.join(data_settings['data']['input']['folder'],
                                         data_settings['data']['input']['filename'])
                tag_filled = {'source_gridded_sub_path_time': time_file,
                          'source_gridded_datetime_daily': time_file,
                              'variable_name': data_settings['data']['input']['variable_name']}
                path_file = fill_tags2string(path_file, data_settings['algorithm']['template'], tag_filled)
                logging.info(' --> Extracting map ... ' + path_file)

                if os.path.exists(path_file):

                    logging.info(' --> Map found!')
                    # copy to tmp
                    var_file_path, var_file_name = os.path.split(path_file)
                    var_file_name_tmp = 'tmp_' + var_file_name
                    path_file_tmp = os.path.join(var_file_path, var_file_name_tmp)
                    copyfile(path_file, path_file_tmp)
                    path_file = path_file_tmp
                    logging.info(' --> Temporary copy created ... ' + path_file)

                    # unzip if needed
                    if data_settings['data']['input']['file_compression']:
                        path_file_unzipped = os.path.splitext(path_file)[0]
                        if os.path.exists(path_file):
                            unzip_filename(path_file, path_file_unzipped)
                            path_file = path_file_unzipped
                            logging.info(" --> Unzipped " + path_file)
                        else:
                            logging.warning(' --> WARNING! output ' + path_file + ' not found!')

                    # load
                    if data_settings['data']['input']['file_type'] == 'tif':

                        da_this_day, wide_this_day, high_this_day, proj_this_day, transform_this_day, \
                        bounding_box_this_day, no_data_this_day, crs_this_day = \
                            read_file_raster(path_file)
                        lat_this_day = da_this_day[da_this_day.dims[0]].data
                        lon_this_day = da_this_day[da_this_day.dims[1]].data
                        logging.info(' --> Map loaded!')

                        # plt.figure()
                        # plt.imshow(da_this_day.values)
                        # plt.show()
                        # plt.close()

                    else:
                        raise IOError('Input file format currently not supported')

                    # reindex ndarray using output grid
                    da_this_day = xr.DataArray(da_this_day,
                                               dims=['lat', 'lon'],
                                               coords={'lat': lat_this_day, 'lon': lon_this_day})
                    da_this_day_reindexed = da_this_day.reindex({'lat': lat_out, 'lon': lon_out},
                                                                method='nearest')

                    # include in target ndarray
                    data_this_month[time_i, :, :] = np.flipud(da_this_day_reindexed)
                    #this flipud is needed for compatibility w/ QGIS

                    # we remove tmp file
                    os.remove(path_file_tmp)  # which is also path_file

                else:
                    logging.warning(' --> WARNING! output ' + path_file + ' not found!')
                    not_available_run = not_available_run + 1


            #create nc file
            path_file_out = os.path.join(data_settings['data']['outcome']['folder'],
                                         data_settings['data']['outcome']['filename'])
            tag_filled = {'source_gridded_sub_path_time': time_step,
                          'outcome_datetime_monthly': time_step,
                          'variable_name': data_settings['data']['input']['variable_name']}
            path_file_out = fill_tags2string(path_file_out, data_settings['algorithm']['template'], tag_filled)
            ds = Dataset(path_file_out, 'w', format='NETCDF4')

            #define dimensions
            Dim_Lat = ds.createDimension('Latitude', lat_out.__len__())
            Dim_Lon = ds.createDimension('Longitude', lon_out.__len__())
            Dim_time = ds.createDimension('time', time_period_this_month.__len__())
            Dim_crs = ds.createDimension('crs', 1)

            # create crs variable
            crs = ds.createVariable("crs", "c", ("crs",))
            crs.spatial_ref = proj_domain_out
            crs.inverse_flattening = data_settings['crs']['inverse_flattening']
            crs.longitude_of_prime_meridian = data_settings['crs']['longitude_of_prime_meridian']
            crs.grid_mapping_name = data_settings['crs']['grid_mapping_name']
            crs.semi_major_axis = data_settings['crs']['semi_major_axis']
            crs.code = data_settings['crs']['code']
            crs.false_easting = data_settings['crs']['false_easting']
            crs.false_northing = data_settings['crs']['false_northing']

            #create lat lon variables
            Longitude = ds.createVariable("Longitude", "d", ("Longitude",), zlib=True)
            Longitude[:] = lon_out
            Longitude.long_name = 'Easting'
            Longitude.standard_name = 'Easting'
            Longitude.units = 'degrees'
            Longitude.scale_factor = 1

            Latitude = ds.createVariable("Latitude", "d", ("Latitude",), zlib=True)
            Latitude[:] = np.flipud(lat_out) # this flipud is needed for compatibility w/ QGIS
            Latitude.long_name = 'Northing'
            Latitude.standard_name = 'Northing'
            Latitude.units = 'degrees'
            Latitude.scale_factor = 1

            #create time variable
            Time = ds.createVariable("Time", "d", ("time",))
            Time.units = "days since " + time_period_this_month[0].strftime("%Y-%m-%d %H:%M:%S")
            Time.calendar = "proleptic_gregorian"
            time_period_this_month_pydatetime = time_period_this_month.to_pydatetime()
            Time[:] = date2num(time_period_this_month_pydatetime, Time.units)

            #write global attributes
            ds.institution = data_settings['global_attributes']['institution']
            ds.source = data_settings['global_attributes']['source']
            ds.reference = data_settings['global_attributes']['reference']
            ds.featureType = data_settings['global_attributes']['featureType']
            ds.Conventions = data_settings['global_attributes']['Conventions']
            ds.keywords = data_settings['global_attributes']['keywords']
            ds.summary = data_settings['global_attributes']['summary']
            ds.title = data_settings['global_attributes']['title']
            ds.acknowledgment = data_settings['global_attributes']['acknowledgment']
            ds.comment = data_settings['global_attributes']['comment']
            ds.creator_name = data_settings['global_attributes']['creator_name']
            ds.creator_url = data_settings['global_attributes']['creator_url']
            ds.creator_email = data_settings['global_attributes']['creator_email']
            ds.geospatial_lat_min = data_settings['global_attributes']['geospatial_lat_min']
            ds.geospatial_lat_max = data_settings['global_attributes']['geospatial_lat_max']
            ds.geospatial_lon_min = data_settings['global_attributes']['geospatial_lon_min']
            ds.geospatial_lon_max = data_settings['global_attributes']['geospatial_lon_max']
            ds.history = data_settings['global_attributes']['history']
            ds.license = data_settings['global_attributes']['license']
            ds.naming_authority = data_settings['global_attributes']['naming_authority']
            ds.project = data_settings['global_attributes']['project']
            ds.publisher_name = data_settings['global_attributes']['publisher_name']
            ds.publisher_url = data_settings['global_attributes']['publisher_url']
            ds.publisher_email = data_settings['global_attributes']['publisher_email']

            #save matrix with data now
            Data = ds.createVariable(data_settings['data']['input']['variable_name'], "d", ("time", "Latitude", "Longitude",), \
                                     zlib=True, fill_value=data_settings['data']['input']['fill_value'])
            Data[:] = data_this_month
            Data.grid_mapping = 'crs'
            Data.coordinates = 'latitude longitude'
            Data.long_name = data_settings['data']['input']['variable_long_name']
            Data.standard_name = data_settings['data']['input']['variable_standard_name']
            Data.units = data_settings['data']['input']['variable_unit']
            Data.scale_factor = data_settings['data']['input']['variable_scale_factor']

            ds.close()
            print()

        else:
            raise IOError('Time frequency not supported. Please use monthly time frequency')

#   # -------------------------------------------------------------------------------------
    #Info algorithm
    time_elapsed = round(time() - start_time, 1)

    if not_available_run > 0:
        logging.info(' ')
        logging.info(' ==> ' + alg_name + ' (Version: ' + alg_version + ' Release_Date: ' + alg_release + ')')
        logging.info(' ==> TIME ELAPSED: ' + str(time_elapsed) + ' seconds')
        logging.info(' ==> SOME RESULTS ARE MISSING!')
        logging.info(' ==> Bye, Bye')
        logging.info(' ============================================================================ ')
        sys.exit(1)
        # -------------------------------------------------------------------------------------

    else:
        logging.info(' ')
        logging.info(' ==> ' + alg_name + ' (Version: ' + alg_version + ' Release_Date: ' + alg_release + ')')
        logging.info(' ==> TIME ELAPSED: ' + str(time_elapsed) + ' seconds')
        logging.info(' ==> ... END')
        logging.info(' ==> Bye, Bye')
        logging.info(' ============================================================================ ')
        sys.exit(0)
        # -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to get script argument(s)
def get_args():

    parser_handle = ArgumentParser()
    parser_handle.add_argument('-settings_file', action="store", dest="alg_settings")
    parser_handle.add_argument('-time', action="store", dest="alg_time")
    parser_values = parser_handle.parse_args()

    alg_script = parser_handle.prog

    if parser_values.alg_settings:
        alg_settings = parser_values.alg_settings
    else:
        alg_settings = 'configuration.json'

    if parser_values.alg_time:
        alg_time = parser_values.alg_time
    else:
        alg_time = None

    return alg_script, alg_settings, alg_time

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
    logging.root.setLevel(logging.INFO)

    # Open logging basic configuration
    logging.basicConfig(level=logging.INFO, format=logger_format, filename=logger_file, filemode='w')

    # Set logger handle
    logger_handle_1 = logging.FileHandler(logger_file, 'w')
    logger_handle_2 = logging.StreamHandler()
    # Set logger level
    logger_handle_1.setLevel(logging.INFO)
    logger_handle_2.setLevel(logging.INFO)
    # Set logger formatter
    logger_formatter = logging.Formatter(logger_format)
    logger_handle_1.setFormatter(logger_formatter)
    logger_handle_2.setFormatter(logger_formatter)
    # Add handle to logging
    logging.getLogger('').addHandler(logger_handle_1)
    logging.getLogger('').addHandler(logger_handle_2)


# -------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Call script from external library
if __name__ == "__main__":
    main()
# ----------------------------------------------------------------------------