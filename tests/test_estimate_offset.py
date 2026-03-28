# -*- coding: utf-8 -*-
"""Estimate optimal source offset from Track reference data.

Since Track SOU_X/Y = actual source position, and Style A uses
Head_Buoy + offset rotation, we can back-calculate the optimal
source_dx/dy that minimizes position error.

source_x = head_e + source_dx * cos(h) + source_dy * sin(h)
source_y = head_n - source_dx * sin(h) + source_dy * cos(h)

Inverse: given (offset_x, offset_y) in absolute coords and heading h:
  source_dx = offset_x * cos(h) + offset_y * (-sin(h))  ... wait

Actually from the forward equations:
  offset_x = source_dx * cos(h) + source_dy * sin(h)
  offset_y = -source_dx * sin(h) + source_dy * cos(h)

Inversion (rotation by -h):
  source_dx = offset_x * cos(h) - offset_y * sin(h)  ... NO

Let me use proper matrix inversion:
  R = [[cos(h), sin(h)], [-sin(h), cos(h)]]
  R^-1 = [[cos(h), -sin(h)], [sin(h), cos(h)]]

  [source_dx, source_dy] = R^-1 @ [offset_x, offset_y]
  source_dx = offset_x * cos(h) + offset_y * sin(h)   ... wait no.

The inverse of R = [[c, s], [-s, c]] is R^T = [[c, -s], [s, c]].
So:
  source_dx = offset_x * cos(h) + offset_y * (-sin(h))
  source_dy = offset_x * sin(h) + offset_y * cos(h)

Wait, let me be very explicit:
  R = [[cos, sin], [-sin, cos]]
  R^-1 = R^T = [[cos, -sin], [sin, cos]]

  source_dx = cos(h) * offset_x + (-sin(h)) * offset_y
  source_dy = sin(h) * offset_x + cos(h) * offset_y
"""
if __name__ != "__main__":
    import pytest
    pytest.skip("Diagnostic script for local sample files.", allow_module_level=True)

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.geometry.gps_interpolation import (
    npd_time_to_seconds, interpolate_gps_at_times
)
from p190converter.engine.geometry.interpolation import compute_heading

# Paths
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'

# 1. Load data
track_data = parse_track_file(TRACK)
df_front = parse_npd(NPD, source='Head_Buoy')
df_tail = parse_npd(NPD, source='Tail_Buoy')

# 2. Interpolate GPS at shot times
front_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_front["time_str"]])
shot_times = track_data.df["time_seconds"].values.astype(float)

front_e, front_n = interpolate_gps_at_times(
    front_times, df_front["east"].values.astype(float),
    df_front["north"].values.astype(float), shot_times
)
tail_e, tail_n = interpolate_gps_at_times(
    np.array([npd_time_to_seconds(t) if t else np.nan for t in df_tail["time_str"]]),
    df_tail["east"].values.astype(float),
    df_tail["north"].values.astype(float), shot_times
)

# 3. Compute heading and back-calculate offset
track_sou_x = track_data.df["sou_x"].values
track_sou_y = track_data.df["sou_y"].values

est_dx_list = []
est_dy_list = []

for i in range(len(shot_times)):
    heading = compute_heading(float(front_e[i]), float(front_n[i]),
                              float(tail_e[i]), float(tail_n[i]))
    h_rad = math.radians(heading)
    cos_h = math.cos(h_rad)
    sin_h = math.sin(h_rad)

    # Absolute offset = Track SOU - Head_Buoy GPS
    offset_x = track_sou_x[i] - front_e[i]
    offset_y = track_sou_y[i] - front_n[i]

    # Back-calculate ship-relative offset
    # R = [[cos, sin], [-sin, cos]], R^-1 = [[cos, -sin], [sin, cos]]
    src_dx = cos_h * offset_x + (-sin_h) * offset_y
    src_dy = sin_h * offset_x + cos_h * offset_y

    est_dx_list.append(src_dx)
    est_dy_list.append(src_dy)

est_dx = np.array(est_dx_list)
est_dy = np.array(est_dy_list)

print("=== Estimated Source Offset (ship-relative coordinates) ===")
print(f"source_dx (cross-track, +starboard):")
print(f"  Mean: {est_dx.mean():.2f} m, Std: {est_dx.std():.2f} m")
print(f"  Median: {np.median(est_dx):.2f} m")
print(f"source_dy (along-track, +bow):")
print(f"  Mean: {est_dy.mean():.2f} m, Std: {est_dy.std():.2f} m")
print(f"  Median: {np.median(est_dy):.2f} m")

# 4. Also check what "COS_Sparker" GPS gives
print("\n=== Trying COS_Sparker as front GPS ===")
try:
    df_sparker = parse_npd(NPD, source='COS_Sparker')
    sparker_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_sparker["time_str"]])
    sparker_e, sparker_n = interpolate_gps_at_times(
        sparker_times, df_sparker["east"].values.astype(float),
        df_sparker["north"].values.astype(float), shot_times
    )

    # Direct difference: COS_Sparker - Track SOU
    diff_e = sparker_e - track_sou_x
    diff_n = sparker_n - track_sou_y
    diff_dist = np.sqrt(diff_e**2 + diff_n**2)

    print(f"COS_Sparker vs Track SOU distance:")
    print(f"  Mean: {diff_dist.mean():.2f} m")
    print(f"  Std: {diff_dist.std():.2f} m")
    print(f"  P95: {np.percentile(diff_dist, 95):.2f} m")
    print(f"  Max: {diff_dist.max():.2f} m")
except Exception as e:
    print(f"  Error: {e}")

# 5. Check all available sources
print("\n=== All NPD Sources vs Track SOU ===")
from p190converter.engine.parsers.npd_parser import parse_npd_sources
sources = parse_npd_sources(NPD)
for src_name in sources:
    try:
        df_src = parse_npd(NPD, source=src_name)
        src_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_src["time_str"]])
        src_e, src_n = interpolate_gps_at_times(
            src_times, df_src["east"].values.astype(float),
            df_src["north"].values.astype(float), shot_times
        )
        diff = np.sqrt((src_e - track_sou_x)**2 + (src_n - track_sou_y)**2)
        print(f"  {src_name:20s}: mean={diff.mean():.2f}m, std={diff.std():.2f}m, p95={np.percentile(diff, 95):.2f}m")
    except Exception as e:
        print(f"  {src_name:20s}: ERROR - {e}")
