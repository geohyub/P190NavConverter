# -*- coding: utf-8 -*-
"""Style A with optimized settings: COS_Sparker as front GPS + estimated offset."""
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

TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'

track_data = parse_track_file(TRACK)
shot_times = track_data.df["time_seconds"].values.astype(float)
track_sou_x = track_data.df["sou_x"].values
track_sou_y = track_data.df["sou_y"].values

# Test different GPS source combinations
configs = [
    # (front_gps, tail_gps, source_dx, source_dy, label)
    ("Head_Buoy", "Tail_Buoy", 0.0, 0.0, "HeadBuoy+TailBuoy (offset=0)"),
    ("Head_Buoy", "Tail_Buoy", 15.08, -20.34, "HeadBuoy+TailBuoy (estimated offset)"),
    ("COS_Sparker", "Tail_Buoy", 0.0, 0.0, "COS_Sparker+TailBuoy (offset=0)"),
    ("COS_Sparker", "Head_Buoy", 0.0, 0.0, "COS_Sparker+HeadBuoy (offset=0)"),
    ("FrontB_F", "TaillB_F", 0.0, 0.0, "FrontB_F+TaillB_F (offset=0)"),
]

for front_name, tail_name, src_dx, src_dy, label in configs:
    try:
        df_front = parse_npd(NPD, source=front_name)
        df_tail = parse_npd(NPD, source=tail_name)

        front_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_front["time_str"]])
        tail_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_tail["time_str"]])

        fe, fn = interpolate_gps_at_times(
            front_times, df_front["east"].values.astype(float),
            df_front["north"].values.astype(float), shot_times
        )
        te, tn = interpolate_gps_at_times(
            tail_times, df_tail["east"].values.astype(float),
            df_tail["north"].values.astype(float), shot_times
        )

        # Compute source positions
        dists = []
        for i in range(len(shot_times)):
            heading = compute_heading(float(fe[i]), float(fn[i]),
                                      float(te[i]), float(tn[i]))
            h_rad = math.radians(heading)
            cos_h = math.cos(h_rad)
            sin_h = math.sin(h_rad)
            sx = fe[i] + src_dx * cos_h + src_dy * sin_h
            sy = fn[i] - src_dx * sin_h + src_dy * cos_h

            d = math.sqrt((sx - track_sou_x[i])**2 + (sy - track_sou_y[i])**2)
            dists.append(d)

        dists = np.array(dists)
        print(f"{label}")
        print(f"  Mean: {dists.mean():.2f}m, Std: {dists.std():.2f}m, "
              f"P95: {np.percentile(dists, 95):.2f}m, Max: {dists.max():.2f}m")

    except Exception as e:
        print(f"{label}: ERROR - {e}")
    print()
