"""
Class Features

Name:          driver_data_io_dynamic
Author(s):     Francesco Avanzi (francesco.avanzi@cimafoundation.org), Fabio Delogu (fabio.delogu@cimafoundation.org)
Date:          '20220509'
Version:       '1.0.1'
"""

######################################################################################
# Library
import logging
import os
import numpy as np
import pandas as pd
import xarray as xr

from copy import deepcopy
from shutil import copyfile

from lib_data_io_binary import read_data_binary, search_geo_reference
from lib_data_io_tiff import read_data_tiff
from lib_data_io_nc import read_data_nc
from lib_data_io_mat import read_data_mat

from lib_utils_interp import active_var_interp, apply_var_interp
from lib_utils_io import read_obj, write_obj, create_dset, write_dset
from lib_utils_gzip import unzip_filename, zip_filename
from lib_utils_system import fill_tags2string, make_folder
from lib_info_args import logger_name, \
    time_format_algorithm, zip_extension
from lib_utils_quality import compute_SQA

# Logging
log_stream = logging.getLogger(logger_name)

# Debug
import matplotlib.pylab as plt
######################################################################################

# -------------------------------------------------------------------------------------
# Default definition(s)
var_fields_accepted = [
    "var_compute", "var_name", "var_scale_factor", "var_shift",
    "folder_name", "file_name", "file_compression", "file_type", "file_frequency"]
time_format_reference = '%Y-%m-%d'
# -------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------
# Class DriverDynamic
class DriverDynamic:

    # -------------------------------------------------------------------------------------
    # Initialize class
    def __init__(self, time_reference, time_period,
                 src_dict, anc_dict=None, dst_dict=None,
                 static_data_collection=None, interp_method='nearest',
                 alg_ancillary=None, alg_template_tags=None,
                 tag_terrain_data='Terrain', tag_grid_data='Grid',
                 tag_static_source='source', tag_static_destination='destination',
                 tag_dynamic_source='source', tag_dynamic_destination='destination',
                 flag_cleaning_dynamic_ancillary=True, flag_cleaning_dynamic_data=True, flag_cleaning_dynamic_tmp=True):

        self.time_str = time_reference.strftime(time_format_reference)
        self.time_period = time_period

        self.src_dict = src_dict
        self.anc_dict = anc_dict
        self.dst_dict = dst_dict

        self.tag_terrain_data = tag_terrain_data
        self.tag_grid_data = tag_grid_data

        self.tag_static_source = tag_static_source
        self.tag_static_destination = tag_static_destination
        self.tag_dynamic_source = tag_dynamic_source
        self.tag_dynamic_destination = tag_dynamic_destination

        self.alg_ancillary = alg_ancillary
        self.alg_template_tags = alg_template_tags

        self.static_data_src = static_data_collection[self.tag_static_source]
        self.static_data_dst = static_data_collection[self.tag_static_destination]

        self.var_compute_tag = 'var_compute'
        self.var_name_tag = 'var_name'
        self.var_scale_factor_tag = 'var_scale_factor'
        self.var_shift_tag = 'var_shift'
        self.file_name_tag = 'file_name'
        self.folder_name_tag = 'folder_name'
        self.file_compression_tag = 'file_compression'
        self.file_geo_reference_tag = 'file_geo_reference'
        self.file_type_tag = 'file_type'
        self.file_coords_tag = 'file_coords'
        self.file_frequency_tag = 'file_frequency'
        self.domain_tag = 'domain_name'
        self.var_compute_quality_tag = 'compute_quality'
        self.var_decimal_digits_tag = 'decimal_digits'

        self.alg_template_list = list(self.alg_template_tags.keys())
        self.var_name_obj = self.define_var_name(src_dict)
        self.file_path_obj_src = self.define_file_name_struct(self.src_dict, self.var_name_obj, self.time_period)
        self.file_path_obj_dst = self.define_file_name_struct(self.dst_dict, 'all', self.time_period)['all']
        self.file_path_obj_anc = self.define_file_name_struct(self.anc_dict, 'all', self.time_period)['all']

        self.flag_cleaning_dynamic_ancillary = flag_cleaning_dynamic_ancillary
        self.flag_cleaning_dynamic_data = flag_cleaning_dynamic_data
        self.flag_cleaning_dynamic_tmp = flag_cleaning_dynamic_tmp

        self.coord_name_geo_x = 'longitude'
        self.coord_name_geo_y = 'latitude'
        self.coord_name_time = 'time'
        self.dim_name_geo_x = 'longitude'
        self.dim_name_geo_y = 'latitude'
        self.dim_name_time = 'time'

        self.dims_order_2d = [self.dim_name_geo_y, self.dim_name_geo_x]
        self.dims_order_3d = [self.dim_name_geo_y, self.dim_name_geo_x, self.dim_name_time]

        self.geo_da_dst = self.set_geo_reference()

        self.interp_method = interp_method

        self.nc_compression_level = 9
        self.nc_type_file = 'NETCDF4'
        self.nc_type_engine = 'netcdf4'

        self.SQA_ground_and_snow = self.alg_ancillary['SQA_ground_and_snow']
        self.domain = self.alg_ancillary['domain_name']

        # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to set geographical reference
    def set_geo_reference(self):

        geo_ref_name = self.dst_dict[self.file_geo_reference_tag]
        geo_ref_collections = self.static_data_dst[geo_ref_name]

        geo_ref_data = geo_ref_collections['data']
        geo_ref_coord_x = geo_ref_collections['geo_x']
        geo_ref_coord_y = geo_ref_collections['geo_y']

        geo_ref_nrows = geo_ref_collections['nrows']
        geo_ref_ncols = geo_ref_collections['ncols']
        geo_ref_xll_corner = geo_ref_collections['xllcorner']
        geo_ref_yll_corner = geo_ref_collections['yllcorner']
        geo_ref_cellsize = geo_ref_collections['cellsize']
        geo_ref_nodata = geo_ref_collections['nodata_value']

        geo_ref_coord_x_2d, geo_ref_coord_y_2d = np.meshgrid(geo_ref_coord_x, geo_ref_coord_y)

        geo_y_upper = geo_ref_coord_y_2d[0, 0]
        geo_y_lower = geo_ref_coord_y_2d[-1, 0]
        if geo_y_lower > geo_y_upper:
            geo_ref_coord_y_2d = np.flipud(geo_ref_coord_y_2d)
            geo_ref_data = np.flipud(geo_ref_data)

        geo_da = xr.DataArray(
            geo_ref_data, name=geo_ref_name, dims=self.dims_order_2d,
            coords={self.coord_name_geo_x: (self.dim_name_geo_x, geo_ref_coord_x_2d[0, :]),
                    self.coord_name_geo_y: (self.dim_name_geo_y, geo_ref_coord_y_2d[:, 0])})

        geo_da.attrs = {'ncols': geo_ref_ncols, 'nrows': geo_ref_nrows,
                        'nodata_value': geo_ref_nodata,
                        'xllcorner': geo_ref_xll_corner, 'yllcorner': geo_ref_yll_corner,
                        'cellsize': geo_ref_cellsize}

        return geo_da
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to set geographical attributes
    @staticmethod
    def set_geo_attributes(dict_info, tag_data='data', tag_geo_x='geo_x', tag_geo_y='geo_y'):

        if tag_data in list(dict_info.keys()):
            data_values = dict_info[tag_data]
        else:
            log_stream.error(' ===> Tag "' + tag_data + '" is not available. Values are not found')
            raise IOError('Check your static datasets')
        if tag_geo_x in list(dict_info.keys()):
            data_geo_x = dict_info[tag_geo_x]
        else:
            log_stream.error(' ===> Tag "' + tag_geo_x + '" is not available. Values are not found')
            raise IOError('Check your static datasets')
        if tag_geo_y in list(dict_info.keys()):
            data_geo_y = dict_info[tag_geo_y]
        else:
            log_stream.error(' ===> Tag "' + tag_geo_y + '" is not available. Values are not found')
            raise IOError('Check your static datasets')

        data_attrs = deepcopy(dict_info)
        [data_attrs.pop(key) for key in [tag_data, tag_geo_x, tag_geo_y]]

        return data_values, data_geo_x, data_geo_y, data_attrs
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to define unzipped filename(s)
    @staticmethod
    def define_file_name_unzip(file_path_zip, file_extension_zip=None):

        if file_extension_zip is None:
            file_extension_zip = zip_extension

        if file_path_zip.endswith(file_extension_zip):
            file_path_tmp, file_extension_tmp = os.path.splitext(file_path_zip)

            if file_extension_tmp.replace('.', '') == file_extension_zip.replace('.', ''):
                file_path_unzip = file_path_tmp
            else:
                log_stream.error(' ===> File zip extension was not expected in format "' + file_extension_tmp
                                 + '"; expected format was "' + file_extension_zip + '"')
                raise IOError('Check your settings file or change expected zip extension')
        else:
            log_stream.error(' ===> File zip ended with a unexpected zip extension "' + file_extension_tmp
                             + '"; expected format was "' + file_extension_zip + '"')
            raise IOError('Check your settings file or change expected zip extension')

        return file_path_unzip
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to define zipped filename(s)
    @staticmethod
    def define_file_name_zip(file_path_unzip, file_extension_zip=None):

        if file_extension_zip is None:
            file_extension_zip = zip_extension

        file_extension_zip = file_extension_zip.replace('.', '')

        if not file_path_unzip.endswith(file_extension_zip):
            file_path_zip = '.'.join([file_path_unzip, file_extension_zip])
        elif file_path_unzip.endswith(file_extension_zip):
            file_path_zip = file_path_unzip

        return file_path_zip
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to define filename(s) struct
    def define_file_name_struct(self, var_dict, var_list, time_period):

        alg_template_tags = self.alg_template_tags

        if not isinstance(var_list, list):
            var_list = [var_list]

        file_path_dict = {}
        for var_name in var_list:

            if var_name in list(var_dict.keys()):
                folder_name_step = var_dict[var_name][self.folder_name_tag]
                file_name_step = var_dict[var_name][self.file_name_tag]
            else:
                folder_name_step = var_dict[self.folder_name_tag]
                file_name_step = var_dict[self.file_name_tag]

            file_path_step = os.path.join(folder_name_step, file_name_step)

            file_path_list = []
            for time_step in time_period:
                alg_template_filled = {}
                for alg_template_step in self.alg_template_list:
                    alg_template_filled[alg_template_step] = time_step

                # replace domain name if present
                if self.domain_tag in alg_template_tags:
                    if self.domain_tag in self.alg_ancillary:
                        alg_template_filled[self.domain_tag] = self.alg_ancillary[self.domain_tag]

                file_path_list.append(fill_tags2string(file_path_step, alg_template_tags, alg_template_filled))

            file_path_dict[var_name] = file_path_list

        return file_path_dict

    # -------------------------------------------------------------------------------------
    # Method to define variable names
    @staticmethod
    def define_var_name(data_dict, data_fields_excluded=None):

        if data_fields_excluded is None:
            data_fields_excluded = ['__comment__', '_comment_', 'comment','']

        var_list_tmp = list(data_dict.keys())
        var_list_def = [var_name for var_name in var_list_tmp if var_name not in data_fields_excluded]

        return var_list_def
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to extract variable field(s)
    def extract_var_fields(self, var_dict):

        var_compute = var_dict[self.var_compute_tag]
        var_name = var_dict[self.var_name_tag]
        var_scale_factor = var_dict[self.var_scale_factor_tag]
        var_shift = var_dict[self.var_shift_tag]
        file_compression = var_dict[self.file_compression_tag]
        file_geo_reference = var_dict[self.file_geo_reference_tag]
        file_type = var_dict[self.file_type_tag]
        file_coords = var_dict[self.file_coords_tag]
        file_freq = var_dict[self.file_frequency_tag]
        compute_quality = var_dict[self.var_compute_quality_tag]
        var_decimal_digits = var_dict[self.var_decimal_digits_tag]

        return var_compute, var_name, var_scale_factor, var_shift, \
               file_compression, file_geo_reference, file_type, file_coords, file_freq, compute_quality, \
               var_decimal_digits
    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to clean dynamic tmp
    def clean_dynamic_tmp(self):

        flag_cleaning_tmp = self.flag_cleaning_dynamic_tmp
        file_path_anc = self.file_path_obj_anc

        if flag_cleaning_tmp:
            for file_path_step in file_path_anc:
                if os.path.exists(file_path_step):
                    os.remove(file_path_step)

    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to dump dynamic data
    def dump_dynamic_data(self):

        time_str = self.time_str
        time_period = self.time_period

        dst_dict = self.dst_dict

        file_path_obj_anc = self.file_path_obj_anc
        file_path_obj_dst = self.file_path_obj_dst

        flag_cleaning_dynamic = self.flag_cleaning_dynamic_data

        log_stream.info(' ---> Dump dynamic datasets [' + time_str + '] ... ')

        for time_step, file_path_anc, file_path_dst in zip(time_period, file_path_obj_anc, file_path_obj_dst):

            log_stream.info(' -----> Time "' + time_step.strftime(time_format_algorithm) + '" ... ')
            file_path_zip = self.define_file_name_zip(file_path_dst)

            if flag_cleaning_dynamic:
                if os.path.exists(file_path_dst):
                    os.remove(file_path_dst)
                if os.path.exists(file_path_zip):
                    os.remove(file_path_zip)

            if os.path.exists(file_path_anc):

                dset_obj = read_obj(file_path_anc)

                folder_name_dst, file_name_dst = os.path.split(file_path_dst)
                if not os.path.exists(folder_name_dst):
                    make_folder(folder_name_dst)

                log_stream.info(' ------> Save filename "' + file_name_dst + '" ... ')

                if not (os.path.exists(file_path_dst) or os.path.exists(file_path_zip)):

                    # Squeeze time dimensions (if equal == 1) --> continuum expects 2d variables in forcing variables
                    if self.dim_name_time in list(dset_obj.dims):
                        time_array = dset_obj[self.dim_name_time].values
                        if time_array.shape[0] == 1:
                            dset_obj = dset_obj.squeeze(self.dim_name_time)
                            dset_obj = dset_obj.drop(self.dim_name_time)

                    write_dset(file_path_dst, dset_obj,
                               dset_engine=self.nc_type_engine, dset_format=self.nc_type_file,
                               dset_compression=self.nc_compression_level, fill_data=-9999.0, dset_type='float32')

                    log_stream.info(' ------> Save filename "' + file_name_dst + '" ... DONE')

                    log_stream.info(' ------> Zip filename "' + file_name_dst + '" ... ')
                    if dst_dict[self.file_compression_tag]:

                        zip_filename(file_path_dst, file_path_zip)

                        if os.path.exists(file_path_zip) and (file_path_zip != file_name_dst):
                            os.remove(file_path_dst)
                        log_stream.info(' ------> Zip filename "' + file_name_dst + '" ... DONE')
                    else:
                        log_stream.info(' ------> Zip filename "' + file_name_dst + '" ... SKIPPED. Zip not activated')
                else:
                    log_stream.info(' ------> Save filename "' + file_name_dst +
                                    '" ... SKIPPED. Filename previously saved')

                log_stream.info(' -----> Time "' + time_step.strftime(time_format_algorithm) + '" ... DONE')

            else:
                log_stream.info(' -----> Time "' + time_step.strftime(time_format_algorithm) +
                                '" ... SKIPPED. Datasets not available')

        log_stream.info(' ---> Dump dynamic datasets [' + time_str + '] ... DONE')

    # -------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------
    # Method to organize dynamic data
    def organize_dynamic_data(self):

        time_str = self.time_str
        time_period = self.time_period

        geo_da_dst = self.geo_da_dst

        src_dict = self.src_dict

        var_name_obj = self.var_name_obj
        file_path_obj_src = self.file_path_obj_src
        file_path_obj_anc = self.file_path_obj_anc

        flag_cleaning_ancillary = self.flag_cleaning_dynamic_ancillary

        log_stream.info(' ---> Organize dynamic datasets [' + time_str + '] ... ')

        # Check if ancillary file already exists
        file_check_list = []
        for file_path_tmp in file_path_obj_anc:
            if os.path.exists(file_path_tmp):
                if flag_cleaning_ancillary:
                    os.remove(file_path_tmp)
                    file_check_list.append(False)
                else:
                    file_check_list.append(True)
            else:
                file_check_list.append(False)
        file_check = all(file_check_list)

        # If statement on ancillary availability
        if not file_check:

            dset_collection = {}
            for var_name in var_name_obj:

                log_stream.info(' ----> Variable "' + var_name + '" ... ')

                var_compute, var_tag, var_scale_factor, var_shift, file_compression, \
                    file_geo_reference, file_type, file_coords, file_freq, compute_quality, var_decimal_digits \
                    = self.extract_var_fields(src_dict[var_name])
                var_file_path_src = file_path_obj_src[var_name]

                if var_compute:

                    var_geo_data = None
                    for var_time, var_file_path_in in zip(time_period, var_file_path_src):

                        log_stream.info(' -----> Time "' + var_time.strftime(time_format_algorithm) + '" ... ')

                        if os.path.exists(var_file_path_in):

                            #copy to tmp
                            var_file_path, var_file_name = os.path.split(var_file_path_in)
                            var_file_path_in_tempcopy = self.domain + '_' + var_file_name
                            copyfile(var_file_path_in, os.path.join(var_file_path, var_file_path_in_tempcopy))
                            var_file_path_in = os.path.join(var_file_path, var_file_path_in_tempcopy)

                            if file_compression:
                                var_file_path_out = self.define_file_name_unzip(var_file_path_in)
                                unzip_filename(var_file_path_in, var_file_path_out)
                            else:
                                var_file_path_out = deepcopy(var_file_path_in)

                            if file_type == 'binary':

                                if var_geo_data is None:
                                    log_stream.info(' ------> Select geo reference for binary datasets ... ')

                                    var_geo_name = search_geo_reference(var_file_path_out, self.static_data_src,
                                                                        tag_geo_reference=file_geo_reference)
                                    log_stream.info(' -------> Geo reference name: ' + var_geo_name)
                                    var_geo_data, var_geo_x, var_geo_y, var_geo_attrs = \
                                        self.set_geo_attributes(self.static_data_src[var_geo_name])
                                    log_stream.info(' ------> Select geo reference for binary datasets ... DONE')

                                var_da_src = read_data_binary(
                                    var_file_path_out, var_geo_x, var_geo_y, var_geo_attrs,
                                    var_scale_factor=var_scale_factor, var_time=var_time, var_name=var_name,
                                    coord_name_geo_x=self.coord_name_geo_x, coord_name_geo_y=self.coord_name_geo_y,
                                    coord_name_time=self.coord_name_time,
                                    dim_name_geo_x=self.dim_name_geo_x, dim_name_geo_y=self.dim_name_geo_y,
                                    dim_name_time=self.dim_name_time,
                                    dims_order=self.dims_order_3d)

                            elif file_type == 'netcdf':

                                if var_geo_data is None:
                                    log_stream.info(' ------> Select geo reference for netcdf datasets ... ')
                                    var_geo_data, var_geo_x, var_geo_y, var_geo_attrs = \
                                        self.set_geo_attributes(self.static_data_src[file_geo_reference])
                                    log_stream.info(' ------> Select geo reference for netcdf datasets ... DONE')

                                var_da_src = read_data_nc(
                                    var_file_path_out, var_geo_x, var_geo_y, var_geo_attrs,  var_coords=file_coords,
                                    var_scale_factor=var_scale_factor, var_name=var_tag, var_time=var_time,
                                    coord_name_geo_x=self.coord_name_geo_x, coord_name_geo_y=self.coord_name_geo_y,
                                    coord_name_time=self.coord_name_time,
                                    dim_name_geo_x=self.dim_name_geo_x, dim_name_geo_y=self.dim_name_geo_y,
                                    dim_name_time=self.dim_name_time,
                                    dims_order=self.dims_order_3d)

                            elif file_type == 'tiff' or file_type == 'asc':

                                var_da_src = read_data_tiff(
                                    var_file_path_out,
                                    var_scale_factor=var_scale_factor, var_name=var_tag, var_time=var_time,
                                    coord_name_geo_x=self.coord_name_geo_x, coord_name_geo_y=self.coord_name_geo_y,
                                    coord_name_time=self.coord_name_time,
                                    dim_name_geo_x=self.dim_name_geo_x, dim_name_geo_y=self.dim_name_geo_y,
                                    dim_name_time=self.dim_name_time,
                                    dims_order=self.dims_order_3d,
                                    decimal_round_data=2, decimal_round_geo=7)

                            elif file_type == 'mat':

                                var_da_src = read_data_mat(
                                    var_file_path_out,
                                    var_scale_factor=var_scale_factor, var_name=var_tag, var_time=var_time,
                                    coord_name_geo_x=self.coord_name_geo_x, coord_name_geo_y=self.coord_name_geo_y,
                                    coord_name_time=self.coord_name_time,
                                    dim_name_geo_x=self.dim_name_geo_x, dim_name_geo_y=self.dim_name_geo_y,
                                    dim_name_time=self.dim_name_time,
                                    dims_order=self.dims_order_3d,
                                    decimal_round_data=2, decimal_round_geo=7, src_dict=src_dict[var_name])

                            else:
                                log_stream.info(' -----> Time "' + var_time.strftime(time_format_algorithm) + '" ... FAILED')
                                log_stream.error(' ===> File type "' + file_type + '"is not allowed.')
                                raise NotImplementedError('Case not implemented yet')

                            # Delete (if needed the uncompressed file(s)
                            if var_file_path_in != var_file_path_out:
                                if os.path.exists(var_file_path_out):
                                    os.remove(var_file_path_out)

                            # Delete temporary file
                            os.remove(var_file_path_in)

                            # Apply scale factor and shift to values
                            if var_shift is not None:
                                var_da_src.values=var_da_src.values + var_shift
                            if var_scale_factor is not None:
                                var_da_src.values=var_da_src.values / var_scale_factor

                            #if var_shift is not None:
                             #   var_da_src=var_da_src + var_shift
                            #if var_scale_factor is not None:
                             #   var_da_src=var_da_src / var_scale_factor


                            # Organize destination dataset
                            if var_da_src is not None:

                                # Active (if needed) interpolation method to the variable source data-array
                                active_interp = active_var_interp(var_da_src.attrs, geo_da_dst.attrs)

                                # Apply the interpolation method to the variable source data-array
                                if active_interp:
                                    var_da_dst = apply_var_interp(
                                        var_da_src, geo_da_dst,
                                        var_name=var_name,
                                        dim_name_geo_x=self.dim_name_geo_x, dim_name_geo_y=self.dim_name_geo_y,
                                        coord_name_geo_x=self.coord_name_geo_x, coord_name_geo_y=self.coord_name_geo_y,
                                        interp_method=self.interp_method)
                                else:
                                    if var_tag != var_name:
                                        var_da_dst = deepcopy(var_da_src)
                                        var_da_dst.name = var_name
                                    else:
                                        var_da_dst = deepcopy(var_da_src)

                                # Mask the variable destination data-array
                                var_nodata = None
                                if 'nodata_value' in list(var_da_dst.attrs.keys()):
                                    var_nodata = var_da_dst.attrs['nodata_value']
                                geo_nodata = None
                                if 'nodata_value' in list(geo_da_dst.attrs.keys()):
                                    geo_nodata = geo_da_dst.attrs['nodata_value']

                                if (geo_nodata is not None) and (var_nodata is not None):
                                    var_da_masked = var_da_dst.where(
                                        (geo_da_dst.values[:, :, np.newaxis] != geo_nodata) &
                                        (var_da_dst != var_nodata))
                                else:
                                    var_da_masked = deepcopy(var_da_dst)

                                #Sanity check to remove nans
                                var_da_masked.values = \
                                    np.where(np.isnan(var_da_masked.values), var_nodata, var_da_masked.values)

                                #Round
                                var_da_masked.values = np.round(var_da_masked.values, var_decimal_digits)

                                # plt.figure(1)
                                # plt.imshow(var_da_dst.values[:, :, 0])
                                # plt.colorbar()
                                # plt.figure(2)
                                # plt.imshow(var_da_src.values[:, :, 0])
                                # plt.colorbar()
                                # plt.figure(3)
                                # plt.imshow(var_da_masked.values[:, :, 0])
                                # plt.colorbar()
                                # plt.show()
                                # plt.figure(4)
                                # plt.imshow(geo_da_dst.values)
                                # plt.colorbar()
                                # plt.show()

                                # Organize data in a common datasets
                                var_dset_masked = create_dset(var_data_time=var_time,
                                                              var_data_name=var_name, var_data_values=var_da_masked,
                                                              var_data_attrs=None,
                                                              var_geo_1d=False,
                                                              file_attributes=geo_da_dst.attrs,
                                                              var_geo_name='terrain',
                                                              var_geo_values=geo_da_dst.values,
                                                              var_geo_x=geo_da_dst['longitude'].values,
                                                              var_geo_y=geo_da_dst['latitude'].values,
                                                              var_geo_attrs=None)

                                # Organize data in merged datasets
                                if var_time not in list(dset_collection.keys()):
                                    dset_collection[var_time] = var_dset_masked
                                else:
                                    var_dset_tmp = deepcopy(dset_collection[var_time])
                                    var_dset_tmp = var_dset_tmp.merge(var_dset_masked, join='right')
                                    dset_collection[var_time] = var_dset_tmp

                                #Compute SQA if needed
                                if compute_quality:

                                    log_stream.info(' ----> Variable "' + var_name + '" ... computing quality ')

                                    SQA = compute_SQA(var_da_masked.values, geo_da_dst.values,
                                                      self.SQA_ground_and_snow)
                                    SQA_dset = create_dset(var_data_time=var_time,
                                                                  var_data_name='SQA', var_data_values=SQA,
                                                                  var_data_attrs=None,
                                                                  var_geo_1d=False,
                                                                  file_attributes=geo_da_dst.attrs,
                                                                  var_geo_name='terrain',
                                                                  var_geo_values=geo_da_dst.values,
                                                                  var_geo_x=geo_da_dst['longitude'].values,
                                                                  var_geo_y=geo_da_dst['latitude'].values,
                                                                  var_geo_attrs=None)
                                    var_dset_tmp = deepcopy(dset_collection[var_time])
                                    var_dset_tmp = var_dset_tmp.merge(SQA_dset, join='right')
                                    dset_collection[var_time] = var_dset_tmp

                                log_stream.info(' -----> Time "' + var_time.strftime(time_format_algorithm) + '" ... DONE')

                            else:
                                log_stream.info(' -----> Time "' + var_time.strftime(time_format_algorithm) +
                                                '" ... Datasets is not defined')

                        else:
                            var_da_src = None
                            log_stream.info(' -----> Time "' + var_time.strftime(time_format_algorithm) +
                                            '" ... Datasets is not defined')

                    log_stream.info(' ----> Variable "' + var_name + '" ... DONE')

                else:
                    log_stream.info(' ----> Variable "' + var_name + '" ... SKIPPED. Compute flag not activated.')

            # Save ancillary datasets
            for file_path_anc, (dset_time, dset_anc) in zip(file_path_obj_anc, dset_collection.items()):

                folder_name_anc, file_name_anc = os.path.split(file_path_anc)
                if not os.path.exists(folder_name_anc):
                    make_folder(folder_name_anc)

                write_obj(file_path_anc, dset_anc)

            log_stream.info(' ---> Organize dynamic datasets [' + time_str + '] ... DONE')
        else:
            log_stream.info(' ---> Organize dynamic datasets [' +
                            time_str + '] ... SKIPPED. All datasets are previously computed')

    # -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
