# -*- coding: utf-8 -*-
"""Debug: Find the CORRECT offset rotation convention by brute-force testing.

Tests ALL possible combinations of:
  1. GPS source: Vessel_Ref, COS_Sparker, Head_Buoy
  2. Heading source: consecutive vessel GPS, front→tail cable GPS
  3. Offset sign convention: 4 combinations of (±dx, ±dy)
  4. Rotation formula: STBD+/FWD+ vs PORT+/AFT+

Compares each combination against Style B SOU_X/SOU_Y (RadExPro export).
"""
import sys, os, math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.parsers.radex_parser import parse_radex_export

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
RADEX_EXPORT = 'test_output/M1406_Header.txt'

# RadExPro Geometry (PORT+, AFT+ convention)
SOURCE_DX = 2.2547     # cross-track PORT+
SOURCE_DY = 60.535     # along-track AFT+

def time_str_to_sec(ts):
    try:
        parts = ts.split(':')
        if len(parts) >= 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        return float(ts)
    except:
        return np.nan

def rotate_stbd_fwd(dx, dy, h_rad):
    """STARBOARD+/FORWARD+ convention (our internal).
    delta_e = dx * cos(h) + dy * sin(h)
    delta_n = -dx * sin(h) + dy * cos(h)
    """
    cos_h, sin_h = math.cos(h_rad), math.sin(h_rad)
    de = dx * cos_h + dy * sin_h
    dn = -dx * sin_h + dy * cos_h
    return de, dn

def rotate_port_aft(dx, dy, h_rad):
    """PORT+/AFT+ convention (RadExPro labels).
    PORT direction = (-cos(h), sin(h))
    AFT direction  = (-sin(h), -cos(h))
    """
    cos_h, sin_h = math.cos(h_rad), math.sin(h_rad)
    de = dx * (-cos_h) + dy * (-sin_h)
    dn = dx * (sin_h)  + dy * (-cos_h)
    return de, dn

print("=" * 80)
print("  COMPREHENSIVE OFFSET CONVENTION TEST")
print("=" * 80)

# ── 1. Parse Track file (for shot times and FFIDs) ──
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
shot_ffids_full = track_data.df['ffid'].values.astype(int)
shot_ffids_p190 = shot_ffids_full % 1000000
n_shots = len(shot_ffids_full)

# ── 2. Parse RadExPro export (Style B ground truth) ──
radex_collection = parse_radex_export(RADEX_EXPORT)
radex_sou = {}  # {ffid: (sou_x, sou_y)}
for shot in radex_collection.shots:
    radex_sou[shot.ffid % 1000000] = (shot.source_x, shot.source_y)

print(f"\nTrack shots: {n_shots}")
print(f"RadExPro shots: {len(radex_sou)}")

# Map track index to RadExPro SOU for matching
match_indices = []
for i in range(n_shots):
    ffid = int(shot_ffids_p190[i])
    if ffid in radex_sou:
        match_indices.append(i)

print(f"Matched shots: {len(match_indices)}")

# ── 3. Parse all GPS sources from NPD ──
gps_sources = {}
for src_name in ['Vessel Ref (Priority 1)', 'COS_Sparker', 'Head_Buoy', 'Tail_Buoy']:
    try:
        df_gps = parse_npd(NPD, source=src_name)
        df_gps['time_sec'] = df_gps['time_str'].apply(time_str_to_sec)
        df_gps = df_gps.dropna(subset=['time_sec']).sort_values('time_sec')
        df_gps = df_gps.drop_duplicates(subset='time_sec', keep='first')

        cs_e = CubicSpline(df_gps['time_sec'].values, df_gps['east'].values)
        cs_n = CubicSpline(df_gps['time_sec'].values, df_gps['north'].values)

        e_at_shots = cs_e(shot_times)
        n_at_shots = cs_n(shot_times)

        gps_sources[src_name] = (e_at_shots, n_at_shots)
        print(f"  {src_name}: {len(df_gps)} records -> interpolated at {n_shots} shot times")
    except Exception as e:
        print(f"  {src_name}: ERROR - {e}")

# ── 4. Compute headings ──
headings = {}

# 4a. Consecutive Vessel Ref heading
if 'Vessel Ref (Priority 1)' in gps_sources:
    ve, vn = gps_sources['Vessel Ref (Priority 1)']
    h_vessel = np.zeros(n_shots)
    for i in range(1, n_shots):
        de = ve[i] - ve[i-1]
        dn = vn[i] - vn[i-1]
        h_vessel[i] = math.degrees(math.atan2(de, dn)) % 360
    h_vessel[0] = h_vessel[1]
    headings['vessel_consec'] = h_vessel

# 4b. Front → Tail cable heading (Head_Buoy → Tail_Buoy)
if 'Head_Buoy' in gps_sources and 'Tail_Buoy' in gps_sources:
    fe, fn = gps_sources['Head_Buoy']
    te, tn = gps_sources['Tail_Buoy']
    h_cable = np.array([
        math.degrees(math.atan2(float(fe[i]-te[i]), float(fn[i]-tn[i]))) % 360
        for i in range(n_shots)
    ])
    headings['front_tail'] = h_cable

# 4c. Consecutive COS_Sparker heading
if 'COS_Sparker' in gps_sources:
    ce, cn = gps_sources['COS_Sparker']
    h_cos = np.zeros(n_shots)
    for i in range(1, n_shots):
        de = ce[i] - ce[i-1]
        dn = cn[i] - cn[i-1]
        h_cos[i] = math.degrees(math.atan2(de, dn)) % 360
    h_cos[0] = h_cos[1]
    headings['cos_consec'] = h_cos

print(f"\nHeading sources: {list(headings.keys())}")

# ── 5. Test ALL combinations ──
print("\n" + "=" * 80)
print("  TESTING ALL COMBINATIONS: GPS + Heading + Convention + Signs")
print("=" * 80)

results = []

# Test direct GPS (no offset)
for gps_name, (ge, gn) in gps_sources.items():
    dists = []
    for i in match_indices:
        ffid = int(shot_ffids_p190[i])
        rx, ry = radex_sou[ffid]
        d = math.sqrt((float(ge[i]) - rx)**2 + (float(gn[i]) - ry)**2)
        dists.append(d)
    dists = np.array(dists)
    results.append({
        'gps': gps_name, 'heading': 'N/A', 'convention': 'direct',
        'dx_sign': 'N/A', 'dy_sign': 'N/A',
        'mean': dists.mean(), 'std': dists.std(),
        'p95': np.percentile(dists, 95), 'max': dists.max(),
    })
    print(f"  DIRECT {gps_name:25s}: mean={dists.mean():.2f}m, "
          f"std={dists.std():.2f}m, p95={np.percentile(dists, 95):.2f}m")

# Test GPS + offset rotations
sign_combos = [
    ('+dx +dy', SOURCE_DX, SOURCE_DY),
    ('-dx +dy', -SOURCE_DX, SOURCE_DY),
    ('+dx -dy', SOURCE_DX, -SOURCE_DY),
    ('-dx -dy', -SOURCE_DX, -SOURCE_DY),
]

rotation_funcs = [
    ('STBD+/FWD+', rotate_stbd_fwd),
    ('PORT+/AFT+', rotate_port_aft),
]

for gps_name, (ge, gn) in gps_sources.items():
    for h_name, h_vals in headings.items():
        for rot_name, rot_func in rotation_funcs:
            for sign_label, test_dx, test_dy in sign_combos:
                dists = []
                for i in match_indices:
                    ffid = int(shot_ffids_p190[i])
                    rx, ry = radex_sou[ffid]
                    h_rad = math.radians(h_vals[i])
                    de, dn = rot_func(test_dx, test_dy, h_rad)
                    src_e = float(ge[i]) + de
                    src_n = float(gn[i]) + dn
                    d = math.sqrt((src_e - rx)**2 + (src_n - ry)**2)
                    dists.append(d)

                dists = np.array(dists)
                results.append({
                    'gps': gps_name, 'heading': h_name,
                    'convention': rot_name, 'dx_sign': sign_label,
                    'dy_sign': '',
                    'mean': dists.mean(), 'std': dists.std(),
                    'p95': np.percentile(dists, 95), 'max': dists.max(),
                })

# ── 6. Sort and display results ──
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('mean')

print("\n" + "=" * 80)
print("  TOP 20 COMBINATIONS (sorted by mean distance to RadExPro SOU)")
print("=" * 80)
print(f"{'#':>3} {'GPS':>20} {'Heading':>14} {'Convention':>12} "
      f"{'Signs':>10} {'Mean':>8} {'Std':>7} {'P95':>8} {'Max':>8}")
print("-" * 100)

for idx, row in results_df.head(20).iterrows():
    rank = results_df.index.get_loc(idx) + 1
    print(f"{rank:3d} {row['gps']:>20s} {row['heading']:>14s} "
          f"{row['convention']:>12s} {row['dx_sign']:>10s} "
          f"{row['mean']:8.2f} {row['std']:7.2f} {row['p95']:8.2f} {row['max']:8.2f}")

# ── 7. Best result analysis ──
best = results_df.iloc[0]
print("\n" + "=" * 80)
print("  BEST MATCH")
print("=" * 80)
print(f"  GPS source:    {best['gps']}")
print(f"  Heading:       {best['heading']}")
print(f"  Convention:    {best['convention']}")
print(f"  DX/DY signs:   {best['dx_sign']}")
print(f"  Mean distance: {best['mean']:.3f}m")
print(f"  Std:           {best['std']:.3f}m")
print(f"  P95:           {best['p95']:.3f}m")
print(f"  Max:           {best['max']:.3f}m")

# ── 8. Verify: extract a few specific shots for spot-check ──
print("\n" + "=" * 80)
print("  SPOT-CHECK: First 5 matched shots")
print("=" * 80)

# Get the best combination parameters
best_gps = gps_sources.get(best['gps'])
best_h = headings.get(best['heading']) if best['heading'] != 'N/A' else None

if best_gps and best['convention'] != 'direct':
    ge, gn = best_gps
    # Find the right rotation function and signs
    for rot_name, rot_func in rotation_funcs:
        if rot_name == best['convention']:
            break
    for sign_label, test_dx, test_dy in sign_combos:
        if sign_label == best['dx_sign']:
            break

    for count, i in enumerate(match_indices[:5]):
        ffid = int(shot_ffids_p190[i])
        rx, ry = radex_sou[ffid]
        h_rad = math.radians(best_h[i]) if best_h is not None else 0
        de, dn = rot_func(test_dx, test_dy, h_rad)
        src_e = float(ge[i]) + de
        src_n = float(gn[i]) + dn
        d = math.sqrt((src_e - rx)**2 + (src_n - ry)**2)
        print(f"  FFID {ffid}: GPS=({float(ge[i]):.2f}, {float(gn[i]):.2f}), "
              f"offset=({de:.2f}, {dn:.2f}), "
              f"computed=({src_e:.2f}, {src_n:.2f}), "
              f"RadExPro=({rx:.2f}, {ry:.2f}), dist={d:.2f}m")
elif best_gps and best['convention'] == 'direct':
    ge, gn = best_gps
    for count, i in enumerate(match_indices[:5]):
        ffid = int(shot_ffids_p190[i])
        rx, ry = radex_sou[ffid]
        d = math.sqrt((float(ge[i]) - rx)**2 + (float(gn[i]) - ry)**2)
        print(f"  FFID {ffid}: GPS=({float(ge[i]):.2f}, {float(gn[i]):.2f}), "
              f"RadExPro=({rx:.2f}, {ry:.2f}), dist={d:.2f}m")

# ── 9. What about Track SOU_X/SOU_Y? ──
print("\n" + "=" * 80)
print("  BONUS: Track file SOU_X/SOU_Y vs RadExPro SOU_X/SOU_Y")
print("=" * 80)
if 'sou_x' in track_data.df.columns and 'sou_y' in track_data.df.columns:
    track_dists = []
    for i in match_indices:
        ffid = int(shot_ffids_p190[i])
        rx, ry = radex_sou[ffid]
        tx = float(track_data.df.iloc[i]['sou_x'])
        ty = float(track_data.df.iloc[i]['sou_y'])
        d = math.sqrt((tx - rx)**2 + (ty - ry)**2)
        track_dists.append(d)
    track_dists = np.array(track_dists)
    print(f"  Track SOU vs RadExPro SOU: mean={track_dists.mean():.3f}m, "
          f"std={track_dists.std():.3f}m, max={track_dists.max():.3f}m")
    if track_dists.mean() < 0.01:
        print(f"  >>> Track file SOU_X/SOU_Y IS the same as RadExPro export! <<<")
    elif track_dists.mean() < 1.0:
        print(f"  >>> Track file SOU_X/SOU_Y is very close to RadExPro export")
else:
    print(f"  Track columns: {list(track_data.df.columns)}")
    # Check if SOU_X exists with different name
    for col in track_data.df.columns:
        if 'sou' in col.lower() or 'source' in col.lower():
            print(f"  Found relevant column: {col}")

print("\n" + "=" * 80)
print("  DONE")
print("=" * 80)
