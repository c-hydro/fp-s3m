"""
S3M Postprocessing tools - Mosaic outputs
__date__ = '20211029'
__version__ = '1.0.0'
__author__ =
        'Francesco Avanzi (francesco.avanzi@cimafoundation.org'
        'Andrea Libertino (andrea.libertino@cimafoundation.org',
        Fabio Delogu (fabio.delogu@cimafoundation.org)
__library__ = 's3m'
General command line:
### python s3m_postprocessing_merger.py -settings_file s3m_postprocessing_merger.json -time "YYYY-MM-DD HH:MM"
Version(s):
20211029 (1.0.0) --> First release
"""
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Complete library
import logging
import gzip
from os.path import join
from argparse import ArgumentParser
import pandas as pd
import xarray as xr
import numpy as np
import sys
import os
import matplotlib.pylab as plt
from time import time, strftime, gmtime
import netCDF4
import matplotlib as mpl
if os.environ.get('DISPLAY','') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')
import rasterio as rio
from shutil import copyfile

from lib_postprocessing_merger_data_io_json import read_file_json
from lib_postprocessing_merger_utils_time import set_time
from lib_postprocessing_merger_info_args import logger_name, time_format_algorithm
from lib_postprocessing_merger_geo import read_file_raster
from lib_postprocessing_merger_io_generic import fill_tags2string, unzip_filename
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Algorithm information
alg_project = 'S3M'
alg_name = 'S3M Postprocessing tools - Mosaic outputs '
alg_version = '1.0.0'
alg_release = '2021-10-29'
alg_type = 'DataDynamic'
# Algorithm parameter(s)
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
    #Load output grid
    logging.info(' --> Load output domain data ... ')
    da_domain, wide_domain, high_domain, proj_domain, transform_domain, \
    bounding_box_domain, no_data_domain, crs_domain = read_file_raster(data_settings['data']['outcome']['output_grid'])
    logging.info(' --> Load output domain data ... DONE')
    lat_out = da_domain[da_domain.dims[0]].data
    lon_out = da_domain[da_domain.dims[1]].data

    # -------------------------------------------------------------------------------------
    # Iterate over time steps
    for time_step in time_range:

        logging.info(" --> Set up domain list")
        list_domain = data_settings['data']['input']['domains']

        #Loop on output layers
        for layer_i, layer in enumerate(data_settings['data']['input']['layers']):

            #initialize output layer
            logging.info(" --> Initializing output layer for time " +  time_step.strftime("%Y-%m-%d %H:%M") + " : " + layer)
            layer_out = (np.ones([len(lat_out), len(lon_out)]) * -9999).astype(np.float32)
            logging.info(" --> Initializing output layer for time " +  time_step.strftime("%Y-%m-%d %H:%M") + " : " + layer + " DONE")

            #initialize output folder
            output_dir = os.path.join(data_settings['data']['outcome']['folder'],
                                data_settings['data']['outcome']['filename'])
            tag_filled = {'layer': str(layer),
                          'outcome_sub_path_time': time_step,
                          'outcome_datetime': time_step}
            tag_filled['layer'] = tag_filled['layer'].replace("_", "")
            output_dir = fill_tags2string(output_dir, data_settings['algorithm']['template'], tag_filled)
            os.makedirs(os.path.dirname(output_dir), exist_ok=True)
            logging.info(" --> Created output dir " + output_dir)

            #check if daily_summary is needed and, if so, create list of timestamps
            if data_settings['data']['input']['daily_summary'][layer_i]:
                time_step_summary = pd.date_range(start=time_step.floor('D'), end=time_step, \
                                                  freq=data_settings['data']['input']['freq_summary'])
            else:
                time_step_summary = pd.DatetimeIndex([time_step])

            # Loop through domains
            not_available_run = 0
            for domain in list_domain:
                logging.info(" ---> Compute domain :" + domain)

                #Load domain info to preallocate arrays
                path_domain = data_settings['data']['input']['grid_path']
                tag_filled = {'domain': domain}
                path_domain = fill_tags2string(path_domain, data_settings['algorithm']['template'], tag_filled)
                if path_domain.endswith('.gz'):
                    path_domain_nc = os.path.splitext(path_domain)[0]
                    unzip_filename(path_domain, path_domain_nc)
                    logging.info(' --> Unzipped file ' + path_domain)
                else:
                    path_domain_nc = path_domain
                domain_grid = xr.open_dataset(path_domain_nc)
                lat_in = np.flipud(domain_grid[data_settings['data']['input']['grid_lat']].values[:,0])
                lon_in = (domain_grid[data_settings['data']['input']['grid_lon']].values[0,:])
                dem_in = np.flipud(domain_grid[data_settings['data']['input']['grid_dem']].values)
                dem_in[dem_in<0]= np.nan
                logging.info(' --> Loaded domain data from ' + path_domain_nc)

                # plt.figure()
                # plt.imshow(dem_in)
                # plt.savefig('debug_dem.png')
                # plt.close()

                size_domain = (lat_in.__len__(), lon_in.__len__())
                if time_step_summary.__len__() > 1:
                    data_this_layer = np.empty((size_domain[0], size_domain[1], time_step_summary.__len__()))
                else:
                    data_this_layer = np.empty((size_domain[0], size_domain[1]))
                data_this_layer[:] = np.nan

                if path_domain.endswith('.gz'):
                    os.remove(path_domain_nc)
                    logging.info(' --> Removed file ' + path_domain_nc)

                #load layers
                for time_i, time_file in enumerate(time_step_summary):
                    path_file = os.path.join(data_settings['data']['input']['folder'],data_settings['data']['input']['filename'])
                    tag_filled = {'layer': str(layer),
                                  'domain': domain,
                                  'source_gridded_sub_path_time': time_file,
                                  'source_gridded_datetime': time_file}
                    path_file = fill_tags2string(path_file, data_settings['algorithm']['template'], tag_filled)
                    logging.info(" --> Loading " + layer + " from " + path_file + " for domain " + domain + "time: " + time_file.strftime("%Y-%m-%d %H:%M"))

                    #we copy to tmp
                    var_file_path, var_file_name = os.path.split(path_file)
                    var_file_name_tmp = 'tmp_' + var_file_name
                    path_file_tmp = os.path.join(var_file_path, var_file_name_tmp)
                    if os.path.exists(path_file):
                        copyfile(path_file, path_file_tmp)
                    path_file = path_file_tmp

                    if path_file.endswith('.gz'):
                        path_file_nc = os.path.splitext(path_file)[0]
                        if os.path.exists(path_file):
                            unzip_filename(path_file, path_file_nc)
                            logging.info(" --> Unzipped " + path_file)
                        else:
                            logging.warning(' --> WARNING! output GZ for domain ' + domain + \
                                            'and time ' + time_file.strftime("%Y-%m-%d %H:%M") + ' not found!')
                            not_available_run = not_available_run + 1
                    else:
                        path_file_nc = path_file

                    if os.path.exists(path_file_nc):
                        data = xr.open_dataset(path_file_nc)
                        data_this_layer_and_time = np.flipud(data[layer].values)
                        data_this_layer_and_time[np.isnan(dem_in)]=np.nan
                        logging.info(
                            " --> Loaded " + layer + " from " + path_file + " for domain " + domain + "time: " + time_file.strftime(
                                "%Y-%m-%d %H:%M"))

                        if data_settings['data']['input']['mask_layer'] is not None:
                            mask = np.flipud(data[data_settings['data']['input']['mask_layer']].values)
                            data_this_layer_and_time[mask <= 0] = np.nan
                            logging.info(
                                " --> Applied mask to " + layer + " from " + path_file + " for domain " + domain + "time: " + time_file.strftime(
                                    "%Y-%m-%d %H:%M"))

                        # plt.figure()
                        # plt.imshow(data_this_layer_and_time)
                        # plt.savefig('data_this_layer_and_time.png')
                        # plt.close()
                        #
                        # plt.figure()
                        # plt.imshow(mask)
                        # plt.savefig('mask.png')
                        # plt.close()

                        if time_step_summary.__len__() > 1:
                            data_this_layer[:, :, time_i] = data_this_layer_and_time
                        else:
                            data_this_layer = data_this_layer_and_time

                        if path_file.endswith('.gz'):
                            os.remove(path_file_nc)
                            logging.info(
                                " --> Removed file " + path_file_nc)

                        #we remove tmp file
                        os.remove(path_file_tmp) #which is also path_file

                    else:
                        logging.warning(' --> WARNING! output NC for domain ' + domain + \
                                        'and time ' + time_file.strftime("%Y-%m-%d %H:%M") + ' not found!')
                        not_available_run = not_available_run + 1

                #Apply aggregation if needed
                if data_settings['data']['input']['daily_summary'][layer_i]:
                    if data_settings['data']['input']['summary_type'][layer_i] == 'avg':
                        data_this_layer = np.nanmean(data_this_layer, axis=2)
                    elif data_settings['data']['input']['summary_type'][layer_i] == 'sum':
                        data_this_layer = np.nansum(data_this_layer, axis=2)
                    else:
                        logging.error(' ===> daily_summary option for layer ' + str(layer) + 'is not supported! Please choose avg or sum.')
                        raise ValueError('Daily_summary option for layer ' + str(layer) + 'is not supported! Please choose avg or sum.')
                    logging.info(
                    " --> Applied aggreation to " + layer + " for domain " + domain)

                # plt.figure()
                # plt.imshow(data_this_layer)
                # plt.savefig('debug_data_final.png')
                # plt.close()

                # we apply scale factor
                data_this_layer = np.where(np.isnan(data_this_layer), data_this_layer,
                                         data_this_layer * data_settings['data']['input']['scale_factor_output'][layer_i])

                #We reindex this domain layer using the output grid
                data_this_layer_in = \
                    xr.DataArray(data_this_layer,
                                 dims=['lat', 'lon'],
                                 coords={'lat': lat_in, 'lon': lon_in})
                data_this_layer_out = data_this_layer_in.reindex({'lat': lat_out, 'lon': lon_out}, method='nearest')
                layer_out = np.where(np.isnan(data_this_layer_out.values), layer_out, data_this_layer_out)
                logging.info(
                    " --> Remapped " + layer + " for domain " + domain + " on target grid")

                # plt.figure()
                # plt.imshow(data_this_layer_in.values)
                # plt.savefig('data_this_layer_in.png')
                # plt.close()
                #
                # plt.figure()
                # plt.imshow(data_this_layer_out.values)
                # plt.savefig('data_this_layer_out.png')
                # plt.close()
                #
                # plt.figure()
                # plt.imshow(layer_out)
                # plt.savefig('layer_out.png')
                # plt.close()

            # Write outputs
            # plt.figure()
            # plt.imshow(layer_out)
            # plt.colorbar()
            # plt.savefig('layer_out_final.png')
            # plt.close()


            #save output
            logging.info(" --> Write output for layer:" + layer + ' and time ' + time_step.strftime("%Y-%m-%d %H:%M"))
            layer_out = layer_out.astype(np.float32)
            with rio.open(output_dir, 'w', height=len(lat_out), width=len(lon_out), count=1, dtype='float32',
                               crs='+proj=latlong', transform=transform_domain, driver='GTiff', nodata=-9999) as out:
                out.write(layer_out, 1)
                logging.info(
                    " --> Saved " + layer + "to " + output_dir)
                if data_settings['algorithm']['flags']['compress_output']:
                     os.system('gzip -f ' + output_dir)

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