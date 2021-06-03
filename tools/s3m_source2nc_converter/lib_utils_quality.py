"""
Library Features:

Name:          lib_utils_quality
Author(s):     Francesco Avanzi (francesco.avanzi@cimafoundation.org), Fabio Delogu (fabio.delogu@cimafoundation.org)
Date:          '20210517'
Version:       '1.0.0'
"""

# -------------------------------------------------------------------------------------
# Libraries
import logging

import os
import pickle
import json
import tempfile

import pandas as pd
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

from copy import deepcopy

from lib_info_args import logger_name

# Logging
log_stream = logging.getLogger(logger_name)

# Debug
# import matplotlib.pylab as plt
# -------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# Method to compute quality
def compute_SQA(data_array, data_array_geo,
                    list_flags_valid = None):

    data_array = data_array[:,:,0]
    log_stream.warning(' ===> data_array flattened to 2d array in compute_SQA')

    # set list_flags_valid to default is it's None
    if list_flags_valid is None:
        list_flags_valid = [0, 1]
        log_stream.warning(' ===> list_flags_valid for quality computation set to default')

    # mask based on geo
    mask = data_array_geo > 0

    # count list_flags_valid
    count_all = 0
    for flags in list_flags_valid:

        count_this_flag =  np.count_nonzero((data_array == flags) & mask)
        count_all = count_all + count_this_flag

    # count valid pixels
    count_valid = np.count_nonzero(mask)

    SQA_scalar = count_all/count_valid
    SQA_map = np.zeros(data_array.shape) + SQA_scalar

    # plt.figure(1)
    # plt.imshow(data_array_geo)
    # plt.colorbar()
    # plt.figure(2)
    # plt.imshow(mask)
    # plt.figure(3)
    # plt.imshow(data_array)
    # plt.colorbar()
    # plt.show()

    return SQA_map


# -------------------------------------------------------------------------------------
