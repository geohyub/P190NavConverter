# -*- coding: utf-8 -*-
"""Debug: Would using COS_Sparker as front GPS fix the gap?

Compare:
  1. COS_Sparker NPD @ shot times vs Style B SOU
  2. Head_Buoy NPD @ shot times vs Style B SOU (current = 25.7m gap)
  3. Vessel_Ref + source offset vs Style B SOU
"""
import sys, os, math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.qc.comparison import _parse_p190_records

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
STYLE_B = 'test_output/2/M1406_B_S_M1406_B.p190'

# RadExPro Source geometry (vessel frame)
SOURCE_DX = 2.2547    # PORT+
SOURCE_DY = 60.535    # AFT+

print("=" * 70)
print("  COS_Sparker vs Head_Buoy as Source GPS")
print("=" * 70)

# Parse track file (shot times)
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
shot_ffids = track_data.df['ffid'].values.astype(int)

# Parse Style B P190
s_b, _ = _parse_p190_records(STYLE_B)
b_dict = dict(zip(s_b['ffid'].values, zip(s_b['easting'].values, s_b['northing'].values)))

# Parse NPD sources
for gps_name in ['COS_Sparker', 'Head_Buoy', 'Vessel Ref (Priority 1)']:
    print(f"\n--- GPS Source: {gps_name} ---")
    df_gps = parse_npd(NPD, source=gps_name)

    # Parse NPD time to seconds
    # NPD time format: HH:MM:SS.SSS
    def time_to_seconds(ts):
        try:
            parts = ts.split(':')
            if len(parts) >= 3:
                h, m = int(parts[0]), int(parts[1])
                s = float(parts[2])
                return h * 3600 + m * 60 + s
            return float(ts)
        except:
            return np.nan

    df_gps['time_sec'] = df_gps['time_str'].apply(time_to_seconds)
    df_gps = df_gps.dropna(subset=['time_sec']).sort_values('time_sec')

    # Remove duplicates
    df_gps = df_gps.drop_duplicates(subset='time_sec', keep='first')

    print(f"  Records: {len(df_gps)}")
    print(f"  Time range: {df_gps['time_sec'].min():.0f} - {df_gps['time_sec'].max():.0f}s")

    # Interpolate GPS at shot times
    valid_mask = (shot_times >= df_gps['time_sec'].min()) & (shot_times <= df_gps['time_sec'].max())

    try:
        cs_e = CubicSpline(df_gps['time_sec'].values, df_gps['east'].values)
        cs_n = CubicSpline(df_gps['time_sec'].values, df_gps['north'].values)

        gps_e_at_shots = cs_e(shot_times)
        gps_n_at_shots = cs_n(shot_times)
    except Exception as e:
        print(f"  Interpolation failed: {e}")
        continue

    # Compare with Style B
    dists = []
    for i in range(len(shot_ffids)):
        ffid = int(shot_ffids[i])
        if ffid not in b_dict or not valid_mask[i]:
            continue

        b_e, b_n = b_dict[ffid]
        gps_e = float(gps_e_at_shots[i])
        gps_n = float(gps_n_at_shots[i])

        dist = math.sqrt((gps_e - b_e)**2 + (gps_n - b_n)**2)
        dists.append(dist)

    if dists:
        dists = np.array(dists)
        print(f"  vs Style B SOU: mean={dists.mean():.2f}m, "
              f"std={dists.std():.2f}m, max={dists.max():.2f}m, "
              f"p95={np.percentile(dists, 95):.2f}m")

# ── Also test: Vessel_Ref + source_offset vs Style B ──
print(f"\n--- Vessel Ref + Source Offset (dx={SOURCE_DX}, dy={SOURCE_DY}) ---")
df_vessel = parse_npd(NPD, source='Vessel Ref (Priority 1)')
df_vessel['time_sec'] = df_vessel['time_str'].apply(time_to_seconds)
df_vessel = df_vessel.dropna(subset=['time_sec']).sort_values('time_sec').drop_duplicates(subset='time_sec')

# Also need heading for offset rotation: use Vessel→COS_Sparker direction as proxy
df_cos = parse_npd(NPD, source='COS_Sparker')
df_cos['time_sec'] = df_cos['time_str'].apply(time_to_seconds)
df_cos = df_cos.dropna(subset=['time_sec']).sort_values('time_sec').drop_duplicates(subset='time_sec')

# Interpolate both at shot times
cs_ve = CubicSpline(df_vessel['time_sec'].values, df_vessel['east'].values)
cs_vn = CubicSpline(df_vessel['time_sec'].values, df_vessel['north'].values)

# Compute heading from consecutive vessel positions
vessel_e = cs_ve(shot_times)
vessel_n = cs_vn(shot_times)

# Vessel heading from consecutive positions
headings = []
for i in range(1, len(shot_times)):
    de = vessel_e[i] - vessel_e[i-1]
    dn = vessel_n[i] - vessel_n[i-1]
    h = math.degrees(math.atan2(de, dn)) % 360
    headings.append(h)
headings = [headings[0]] + headings  # duplicate first

# Apply source offset with heading rotation
# RadExPro convention: dx=PORT+, dy=AFT+
# In map: source_east = vessel_east + dx*cos(h) - dy*sin(h) [PORT+ = left of heading]
# Actually need to think about this:
# heading = angle from North CW
# PORT direction = heading - 90
# AFT direction = heading + 180
# So: port_vector = (-sin(h), -cos(h))? No...
# Forward = (sin(h), cos(h)), Starboard = (cos(h), -sin(h))
# PORT = -Starboard = (-cos(h), sin(h))
# AFT = -Forward = (-sin(h), -cos(h))
# offset_map = dx * PORT + dy * AFT
# offset_east  = dx * (-cos(h)) + dy * (-sin(h))
# offset_north = dx * (sin(h))  + dy * (-cos(h))

dists_offset = []
for i in range(len(shot_ffids)):
    ffid = int(shot_ffids[i])
    if ffid not in b_dict:
        continue

    h = math.radians(headings[i])
    sin_h, cos_h = math.sin(h), math.cos(h)

    # Apply RadExPro offset (PORT+, AFT+)
    off_e = SOURCE_DX * (-cos_h) + SOURCE_DY * (-sin_h)
    off_n = SOURCE_DX * (sin_h)  + SOURCE_DY * (-cos_h)

    src_e = float(vessel_e[i]) + off_e
    src_n = float(vessel_n[i]) + off_n

    b_e, b_n = b_dict[ffid]
    dist = math.sqrt((src_e - b_e)**2 + (src_n - b_n)**2)
    dists_offset.append(dist)

if dists_offset:
    dists_offset = np.array(dists_offset)
    print(f"  vs Style B SOU: mean={dists_offset.mean():.2f}m, "
          f"std={dists_offset.std():.2f}m, max={dists_offset.max():.2f}m, "
          f"p95={np.percentile(dists_offset, 95):.2f}m")

print("\n" + "=" * 70)
print("  SUMMARY: Which GPS source best matches Style B?")
print("=" * 70)
