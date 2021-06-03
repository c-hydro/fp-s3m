"""
Class Features

Name:          driver_data_io_static
Author(s):     Francesco Avanzi (francesco.avanzi@cimafoundation.org), Fabio Delogu (fabio.delogu@cimafoundation.org)
Date:          '20210603'
Version:       '1.0.0'
"""

######################################################################################
# Library
import logging
import os
import numpy as np

from lib_data_io_ascii import read_data_grid, \
    create_data_grid, extract_data_grid
from lib_info_args import logger_name
from lib_utils_system import fill_tags2string
from lib_utils_gzip import unzip_filename
from lib_data_io_nc import read_data_nc
import matplotlib.pyplot as plt

# Logging
log_stream = logging.getLogger(logger_name)

# Debug
# import matplotlib.pylab as plt
######################################################################################


# -------------------------------------------------------------------------------------
# Class DriverStatic
class DriverStatic:

    # -------------------------------------------------------------------------------------
    # Initialize class
    def __init__(self, src_dict, dst_dict=None,
                 alg_ancillary=None, alg_template_tags=None,
                 flag_dst_data='Terrain',
                 flag_geo_x_dim='Longitude', flag_geo_y_dim='Latitude',
                 flag_static_source='source', flag_static_destination='destination',
                 flag_cleaning_static=True):

        self.flag_dst_data = flag_dst_data

        self.flag_static_source = flag_static_source
        self.flag_static_destination = flag_static_destination

        self.alg_ancillary = alg_ancillary

        self.alg_template_tags = alg_template_tags
        self.file_name_tag = 'file_name'
        self.folder_name_tag = 'folder_name'

        self.folder_name_dst = dst_dict[self.flag_dst_data][self.folder_name_tag]
        self.file_name_dst = dst_dict[self.flag_dst_data][self.file_name_tag]
        self.file_path_dst = os.path.join(self.folder_name_dst, self.file_name_dst)

        self.flag_cleaning_static = flag_cleaning_static

        self.dim_order_2d = [flag_geo_y_dim, flag_geo_x_dim]

        self.dim_order_x = flag_geo_x_dim
        self.dim_order_y = flag_geo_y_dim

    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to organize geographical data
    def organize_static(self, data_settings):

        # Info start
        log_stream.info(' ---> Organize static datasets ... ')

        # Data collection object
        data_collections = {self.flag_static_source: {}, self.flag_static_destination: {}}

        # Read source grids
        for grid, grid_key in data_settings['data']['static']['source'].items():

            if {'folder_name', 'file_name'} == set(list(grid_key.keys())):

                data_src = read_data_grid(
                    os.path.join(grid_key['folder_name'], grid_key['file_name']),
                    output_format='dictionary')
                grid_src = extract_data_grid(
                    data_src['values'],
                    data_src['longitude'], data_src['latitude'],
                    data_src['transform'], data_src['bbox'])
                data_collections[self.flag_static_source][grid] = grid_src

            elif {'xll', 'yll', 'res', 'nrows', 'ncols', 'nodata_value'} == set(list(grid_key.keys())):

                grid_src = {
                    'nrows': grid_key['nrows'], 'ncols': grid_key['ncols'],
                    'xllcorner': grid_key['xll'], 'yllcorner': grid_key['yll'],
                    'cellsize': grid_key['res'], 'data': np.nan,
                    'geo_x': (grid_key['xll'] + grid_key['res'] / 2) +
                             np.arange(grid_key['ncols']) * grid_key['res'],
                    'geo_y': np.flip((grid_key['yll'] + grid_key['res'] / 2) +
                                     np.arange(grid_key['nrows']) * grid_key['res']),
                    'nodata_value': grid_key['nodata_value']}

                data_collections[self.flag_static_source][grid] = grid_src

            else:
                log_stream.error('Grid keys in static input grids are not recognized!')
                raise NotImplementedError('Case not implemented yet, check JSON for static data source!')

        # Read static data destination
        file_path_terrain_dst = self.file_path_dst
        file_path_terrain_dst = fill_tags2string(file_path_terrain_dst,
                                                 data_settings['algorithm']['template'],
                                                 data_settings['algorithm']['ancillary'])

        if data_settings['data']['static']['destination']['Terrain']['file_compression']:
            file_name_zip = file_path_terrain_dst + '.gz'
            unzip_filename(file_name_zip, file_path_terrain_dst)

        if (data_settings['data']['static']['destination']['Terrain']['file_type'] == 'tiff') \
                or (data_settings['data']['static']['destination']['Terrain']['file_type'] == 'asc') \
                or (data_settings['data']['static']['destination']['Terrain']['file_type'] == 'txt'):

            terrain_data_dst = read_data_grid(file_path_terrain_dst, output_format='dictionary')
            terrain_grid_dst = extract_data_grid(terrain_data_dst['values'],
                                                 terrain_data_dst['longitude'], terrain_data_dst['latitude'],
                                                 terrain_data_dst['transform'], terrain_data_dst['bbox'])
            data_collections[self.flag_static_destination][self.flag_dst_data] = terrain_grid_dst

        elif data_settings['data']['static']['destination']['Terrain']['file_type'] == 'netcdf':

            data_dst = read_data_nc(
                file_path_terrain_dst, var_name='Terrain',
                var_coords=data_settings['data']['static']['destination']['Terrain']['file_coords'],
                dims_order=self.dim_order_2d, dim_name_geo_x=self.dim_order_x, dim_name_geo_y=self.dim_order_y)
            res = data_dst[self.dim_order_x].values[1] - data_dst[self.dim_order_x].values[0]
            resolution_round = data_settings['data']['static']['destination']['Terrain']['resolution_round']
            res = round(res, resolution_round)
            grid_dst = {'nrows': data_dst[self.dim_order_y].shape, 'ncols': data_dst[self.dim_order_x].shape,
                        'xllcorner': round(data_dst[self.dim_order_x].values[0] - res/2, resolution_round),
                        'yllcorner': round(data_dst[self.dim_order_y].values[-1] - res/2, resolution_round),
                        'cellsize': res, 'data': data_dst.values, 'geo_x': data_dst[self.dim_order_x].values,
                        'geo_y': data_dst[self.dim_order_y].values,
                        'nodata_value': data_settings['data']['static']['destination']['Terrain']['nodata_value']}
            data_collections[self.flag_static_destination][self.flag_dst_data] = grid_dst

        if data_settings['data']['static']['destination']['Terrain']['file_compression']:
            os.remove(file_path_terrain_dst)

        else:
            log_stream.error(' ===> File type "' +
                             data_settings['data']['static']['destination']['Terrain']['file_type']
                             + '"is not allowed.')
            raise NotImplementedError('Case not implemented yet')

        # Info end
        log_stream.info(' ---> Organize static datasets ... DONE')

        return data_collections
    # -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
