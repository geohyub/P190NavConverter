# -*- coding: utf-8 -*-
"""Regression tests for GPS interpolation safety checks."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from p190converter.engine.geometry.gps_interpolation import interpolate_gps_at_times


def test_interpolate_gps_at_times_raises_on_out_of_range_query():
    npd_times = np.array([0.0, 10.0, 20.0], dtype=float)
    npd_east = np.array([100.0, 110.0, 120.0], dtype=float)
    npd_north = np.array([200.0, 210.0, 220.0], dtype=float)
    query_times = np.array([-1.0, 5.0, 25.0], dtype=float)

    with pytest.raises(ValueError, match="outside NPD range"):
        interpolate_gps_at_times(npd_times, npd_east, npd_north, query_times)
