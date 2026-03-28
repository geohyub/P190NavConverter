# -*- coding: utf-8 -*-
"""Debug heading: compare NPD GPS heading vs RadExPro receiver direction."""
if __name__ != "__main__":
    import pytest
    pytest.skip("Diagnostic script for local sample files.", allow_module_level=True)

import sys, os, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.geometry.gps_interpolation import (
    npd_time_to_seconds, interpolate_gps_at_times
)
from p190converter.engine.geometry.interpolation import compute_heading

TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
HEADER = r'E:\Software\P190_NavConverter\test_output\M1406_Header.txt'

# Parse Track
track = parse_track_file(TRACK)
print(f'Track: {track.n_shots} shots')

# Check if Track has DIRECTION column
import pandas as pd
track_raw = pd.read_csv(TRACK, sep='\t')
print(f'Track columns: {list(track_raw.columns)}')

# Parse NPD
df_head = parse_npd(NPD, source='Head_Buoy')
df_tail = parse_npd(NPD, source='Tail_Buoy')
head_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_head["time_str"]])
tail_times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df_tail["time_str"]])
shot_times = track.df["time_seconds"].values.astype(float)

# Interpolate GPS at first 5 shot times
he, hn = interpolate_gps_at_times(head_times, df_head["east"].values.astype(float),
                                   df_head["north"].values.astype(float), shot_times[:5])
te, tn = interpolate_gps_at_times(tail_times, df_tail["east"].values.astype(float),
                                   df_tail["north"].values.astype(float), shot_times[:5])

# Compute heading from NPD
print('\n=== NPD GPS Heading (first 5 shots) ===')
for i in range(5):
    heading = compute_heading(float(he[i]), float(hn[i]), float(te[i]), float(tn[i]))
    print(f'Shot {i}: Head=({he[i]:.1f}, {hn[i]:.1f}), '
          f'Tail=({te[i]:.1f}, {tn[i]:.1f}), Heading={heading:.1f} deg')

# Compute heading from Style B receiver direction
# Read M1406_Header.txt for first few shots
header_df = pd.read_csv(HEADER, sep='\t', nrows=32)  # 2 shots x 16 ch
print('\n=== RadExPro receiver direction (first 2 shots) ===')
for ffid in header_df['FFID'].unique()[:2]:
    sub = header_df[header_df['FFID'] == ffid]
    sx, sy = sub.iloc[0]['SOU_X'], sub.iloc[0]['SOU_Y']
    rx1_x, rx1_y = sub.iloc[0]['REC_X'], sub.iloc[0]['REC_Y']
    rx16_x, rx16_y = sub.iloc[-1]['REC_X'], sub.iloc[-1]['REC_Y']

    # RX1 relative to source
    dx_rx1 = rx1_x - sx
    dy_rx1 = rx1_y - sy

    # Cable direction: RX1 to RX16
    cable_dx = rx16_x - rx1_x
    cable_dy = rx16_y - rx1_y
    cable_bearing = math.degrees(math.atan2(cable_dx, cable_dy)) % 360

    # Ship heading = cable bearing + 180 (cable extends aft)
    ship_heading = (cable_bearing + 180) % 360

    print(f'FFID {ffid}: Source=({sx:.1f}, {sy:.1f})')
    print(f'  RX1=({rx1_x:.1f}, {rx1_y:.1f}), dE={dx_rx1:.2f}, dN={dy_rx1:.2f}')
    print(f'  Cable bearing: {cable_bearing:.1f} deg')
    print(f'  Implied ship heading: {ship_heading:.1f} deg')

# Compute heading from consecutive source positions
print('\n=== Heading from consecutive source positions ===')
for i in range(4):
    ffids = sorted(header_df['FFID'].unique())
    if i + 1 >= len(ffids):
        break
    sub1 = header_df[header_df['FFID'] == ffids[i]].iloc[0]
    sub2 = header_df[header_df['FFID'] == ffids[i+1]].iloc[0]
    dx = sub2['SOU_X'] - sub1['SOU_X']
    dy = sub2['SOU_Y'] - sub1['SOU_Y']
    bearing = math.degrees(math.atan2(dx, dy)) % 360
    print(f'  FFID {ffids[i]}->{ffids[i+1]}: dx={dx:.3f}, dy={dy:.3f}, bearing={bearing:.1f} deg')
