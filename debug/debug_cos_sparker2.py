# -*- coding: utf-8 -*-
"""Debug: COS_Sparker vs Head_Buoy vs Vessel_Ref+offset as source GPS.
Fixed: FFID 7-digit (Track) vs 6-digit (P190) matching via mod 1000000.
"""
import sys, os, math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.qc.comparison import _parse_p190_records
from p190converter.engine.geometry.interpolation import compute_heading

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
STYLE_B = 'test_output/2/M1406_B_S_M1406_B.p190'

SOURCE_DX = 2.2547
SOURCE_DY = 60.535

def time_str_to_sec(ts):
    try:
        parts = ts.split(':')
        if len(parts) >= 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        return float(ts)
    except:
        return np.nan

print("=" * 70)
print("  COS_Sparker vs Head_Buoy as Source GPS (fixed FFID matching)")
print("=" * 70)

# Parse track file
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
shot_ffids_full = track_data.df['ffid'].values.astype(int)
# P190 truncates to 6 digits
shot_ffids_p190 = shot_ffids_full % 1000000

# Parse Style B P190
s_b, _ = _parse_p190_records(STYLE_B)
b_dict = dict(zip(s_b['ffid'].values.astype(int),
                   zip(s_b['easting'].values, s_b['northing'].values)))

print(f"Track shots: {len(shot_ffids_full)}, P190 B shots: {len(s_b)}")
match_count = sum(1 for f in shot_ffids_p190 if f in b_dict)
print(f"FFID matches (track%1M in P190): {match_count}")

# ── Test each GPS source ──
results = {}
for gps_name in ['COS_Sparker', 'Head_Buoy', 'Tail_Buoy']:
    print(f"\n--- GPS: {gps_name} (direct, no offset) ---")
    df_gps = parse_npd(NPD, source=gps_name)
    df_gps['time_sec'] = df_gps['time_str'].apply(time_str_to_sec)
    df_gps = df_gps.dropna(subset=['time_sec']).sort_values('time_sec')
    df_gps = df_gps.drop_duplicates(subset='time_sec', keep='first')

    cs_e = CubicSpline(df_gps['time_sec'].values, df_gps['east'].values)
    cs_n = CubicSpline(df_gps['time_sec'].values, df_gps['north'].values)

    gps_e = cs_e(shot_times)
    gps_n = cs_n(shot_times)

    dists = []
    for i in range(len(shot_ffids_p190)):
        ffid = int(shot_ffids_p190[i])
        if ffid not in b_dict:
            continue
        b_e, b_n = b_dict[ffid]
        d = math.sqrt((float(gps_e[i]) - b_e)**2 + (float(gps_n[i]) - b_n)**2)
        dists.append(d)

    dists = np.array(dists)
    print(f"  Matched: {len(dists)}")
    print(f"  vs Style B: mean={dists.mean():.2f}m, std={dists.std():.2f}m, "
          f"max={dists.max():.2f}m, p95={np.percentile(dists, 95):.2f}m")
    results[gps_name] = dists.mean()

# ── Vessel_Ref + source offset (RadExPro method) ──
print(f"\n--- Vessel Ref + Source Offset ---")
df_vessel = parse_npd(NPD, source='Vessel Ref (Priority 1)')
df_vessel['time_sec'] = df_vessel['time_str'].apply(time_str_to_sec)
df_vessel = df_vessel.dropna(subset=['time_sec']).sort_values('time_sec')
df_vessel = df_vessel.drop_duplicates(subset='time_sec', keep='first')

cs_ve = CubicSpline(df_vessel['time_sec'].values, df_vessel['east'].values)
cs_vn = CubicSpline(df_vessel['time_sec'].values, df_vessel['north'].values)
vessel_e = cs_ve(shot_times)
vessel_n = cs_vn(shot_times)

# Ship heading from consecutive positions
headings_ship = np.zeros(len(shot_times))
for i in range(1, len(shot_times)):
    de = vessel_e[i] - vessel_e[i-1]
    dn = vessel_n[i] - vessel_n[i-1]
    headings_ship[i] = math.degrees(math.atan2(de, dn)) % 360
headings_ship[0] = headings_ship[1]

# Apply offset: PORT+ and AFT+ convention
# Port = (-cos(h), sin(h)), Aft = (-sin(h), -cos(h))
dists_vo = []
for i in range(len(shot_ffids_p190)):
    ffid = int(shot_ffids_p190[i])
    if ffid not in b_dict:
        continue

    h = math.radians(headings_ship[i])
    sin_h, cos_h = math.sin(h), math.cos(h)

    off_e = SOURCE_DX * (-cos_h) + SOURCE_DY * (-sin_h)
    off_n = SOURCE_DX * (sin_h)  + SOURCE_DY * (-cos_h)

    src_e = float(vessel_e[i]) + off_e
    src_n = float(vessel_n[i]) + off_n

    b_e, b_n = b_dict[ffid]
    d = math.sqrt((src_e - b_e)**2 + (src_n - b_n)**2)
    dists_vo.append(d)

dists_vo = np.array(dists_vo)
print(f"  Matched: {len(dists_vo)}")
print(f"  vs Style B: mean={dists_vo.mean():.2f}m, std={dists_vo.std():.2f}m, "
      f"max={dists_vo.max():.2f}m, p95={np.percentile(dists_vo, 95):.2f}m")
results['Vessel_Ref+offset'] = dists_vo.mean()

# ── COS_Sparker + source offset (if COS is at cable head, apply src offset) ──
print(f"\n--- COS_Sparker + Source Offset ---")
df_cos = parse_npd(NPD, source='COS_Sparker')
df_cos['time_sec'] = df_cos['time_str'].apply(time_str_to_sec)
df_cos = df_cos.dropna(subset=['time_sec']).sort_values('time_sec')
df_cos = df_cos.drop_duplicates(subset='time_sec', keep='first')

cs_ce = CubicSpline(df_cos['time_sec'].values, df_cos['east'].values)
cs_cn = CubicSpline(df_cos['time_sec'].values, df_cos['north'].values)
cos_e = cs_ce(shot_times)
cos_n = cs_cn(shot_times)

# Use ship heading for rotation
dists_co = []
for i in range(len(shot_ffids_p190)):
    ffid = int(shot_ffids_p190[i])
    if ffid not in b_dict:
        continue

    h = math.radians(headings_ship[i])
    sin_h, cos_h = math.sin(h), math.cos(h)

    off_e = SOURCE_DX * (-cos_h) + SOURCE_DY * (-sin_h)
    off_n = SOURCE_DX * (sin_h)  + SOURCE_DY * (-cos_h)

    src_e = float(cos_e[i]) + off_e
    src_n = float(cos_n[i]) + off_n

    b_e, b_n = b_dict[ffid]
    d = math.sqrt((src_e - b_e)**2 + (src_n - b_n)**2)
    dists_co.append(d)

dists_co = np.array(dists_co)
print(f"  vs Style B: mean={dists_co.mean():.2f}m, std={dists_co.std():.2f}m")
results['COS_Sparker+offset'] = dists_co.mean()

# ── Summary ──
print("\n" + "=" * 70)
print("  RANKING: Which source matches Style B best?")
print("=" * 70)
for name, val in sorted(results.items(), key=lambda x: x[1]):
    label = "<<<< BEST" if val == min(results.values()) else ""
    print(f"  {name:30s}  {val:8.2f}m  {label}")
