# -*- coding: utf-8 -*-
"""Debug: Why 25.7m difference between Style A and Style B source positions?

Hypothesis: Style A uses Head_Buoy GPS directly as source position,
but Head_Buoy is NOT the source — it's the cable head buoy.
The actual source (sparker) is at a different physical location.

This script:
1. Checks available NPD GPS sources
2. Compares Head_Buoy, COS_Sparker, Tail_Buoy positions
3. Analyzes the direction of A→B offset relative to heading
4. Tests if applying source offset from Head_Buoy fixes the gap
"""
import sys, os, math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd_sources, parse_npd
from p190converter.engine.qc.comparison import _parse_p190_records

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
STYLE_A = 'test_output/2/M1406_A_S_M1406_A.p190'
STYLE_B = 'test_output/2/M1406_B_S_M1406_B.p190'

# RadExPro Geometry (from test_style_a_v2.py)
SOURCE_DX = 2.2547     # Source cross-track (vessel frame, PORT+)
SOURCE_DY = 60.535     # Source along-track (vessel frame, AFT+)
RX1_DX = -1.2453       # RX1 cross-track
RX1_DY = 69.7075       # RX1 along-track

print("=" * 70)
print("  DEBUG: Style A vs B 25.7m Source Position Difference")
print("=" * 70)

# ── 1. NPD GPS Sources ──
print("\n[1] NPD GPS Sources")
sources = parse_npd_sources(NPD)
print(f"  Available: {sources}")

# Parse all sources
gps_data = {}
for src in sources:
    try:
        df = parse_npd(NPD, source=src)
        gps_data[src] = df
        print(f"  {src}: {len(df)} records, "
              f"E=[{df['east'].min():.1f}, {df['east'].max():.1f}], "
              f"N=[{df['north'].min():.1f}, {df['north'].max():.1f}]")
    except Exception as e:
        print(f"  {src}: ERROR - {e}")

# ── 2. GPS Source Inter-Distances ──
print("\n[2] GPS Source Inter-Distances (first 100 records)")
src_names = list(gps_data.keys())
for i in range(len(src_names)):
    for j in range(i+1, len(src_names)):
        a, b = src_names[i], src_names[j]
        df_a, df_b = gps_data[a], gps_data[b]
        n = min(len(df_a), len(df_b), 100)
        dists = np.sqrt(
            (df_a['east'].values[:n] - df_b['east'].values[:n])**2 +
            (df_a['north'].values[:n] - df_b['north'].values[:n])**2
        )
        print(f"  {a} <-> {b}: mean={dists.mean():.2f}m, std={dists.std():.2f}m")

# ── 3. P190 Source Positions ──
print("\n[3] P190 Source Position Analysis")
s_a, rx_a = _parse_p190_records(STYLE_A)
s_b, rx_b = _parse_p190_records(STYLE_B)

merged = pd.merge(s_a, s_b, on='ffid', suffixes=('_a', '_b'), how='inner')
merged['dx'] = merged['easting_a'] - merged['easting_b']
merged['dy'] = merged['northing_a'] - merged['northing_b']
merged['dist'] = np.sqrt(merged['dx']**2 + merged['dy']**2)

print(f"  Common shots: {len(merged)}")
print(f"  Source dist: mean={merged['dist'].mean():.2f}m, std={merged['dist'].std():.2f}m")
print(f"  dx (A-B): mean={merged['dx'].mean():.2f}m, std={merged['dx'].std():.2f}m")
print(f"  dy (A-B): mean={merged['dy'].mean():.2f}m, std={merged['dy'].std():.2f}m")

# ── 4. Direction of A→B Offset relative to cable heading ──
print("\n[4] Offset Direction Analysis (A=Head_Buoy, B=RadExPro SOU)")

# Get heading from Style A receiver spread
sample_ffids = sorted(rx_a.keys())[:500]  # first 500 shots
offset_bearings = []
cable_headings = []

for ffid in sample_ffids:
    row = merged[merged['ffid'] == ffid]
    if row.empty or ffid not in rx_a or len(rx_a[ffid]) < 2:
        continue

    # Cable heading from receiver spread (src → last_rx direction)
    src_x, src_y = row.iloc[0]['easting_a'], row.iloc[0]['northing_a']
    last_rx = rx_a[ffid][-1]
    cable_dx = last_rx[0] - src_x
    cable_dy = last_rx[1] - src_y
    cable_hdg = math.degrees(math.atan2(cable_dx, cable_dy)) % 360
    cable_headings.append(cable_hdg)

    # A→B offset bearing
    off_dx = row.iloc[0]['dx']  # easting_a - easting_b
    off_dy = row.iloc[0]['dy']  # northing_a - northing_b
    off_bearing = math.degrees(math.atan2(off_dx, off_dy)) % 360
    offset_bearings.append(off_bearing)

cable_hdg_mean = np.mean(cable_headings)
off_bearing_mean = np.mean(offset_bearings)
rel_bearing = ((off_bearing_mean - cable_hdg_mean + 180) % 360) - 180

print(f"  Cable heading (mean): {cable_hdg_mean:.1f} deg")
print(f"  A→B offset bearing:  {off_bearing_mean:.1f} deg")
print(f"  Relative (A→B vs cable): {rel_bearing:.1f} deg")

if abs(rel_bearing) < 30:
    print(f"  --> Offset is ALONG-CABLE direction (forward/aft)")
    print(f"      Head_Buoy is AHEAD of RadExPro source in cable direction")
elif abs(abs(rel_bearing) - 180) < 30:
    print(f"  --> Offset is ALONG-CABLE direction (RadExPro source is AHEAD)")
elif abs(abs(rel_bearing) - 90) < 30:
    print(f"  --> Offset is CROSS-CABLE (lateral)")
else:
    print(f"  --> Offset is at an oblique angle to cable")

# ── 5. RadExPro Geometry Analysis ──
print("\n[5] RadExPro Geometry Offsets (Vessel Frame)")
print(f"  Source:  dx={SOURCE_DX:+.4f} (PORT+), dy={SOURCE_DY:+.4f} (AFT+)")
print(f"  RX1:     dx={RX1_DX:+.4f} (PORT+), dy={RX1_DY:+.4f} (AFT+)")
src_to_rx1_dx = RX1_DX - SOURCE_DX
src_to_rx1_dy = RX1_DY - SOURCE_DY
src_to_rx1_dist = math.sqrt(src_to_rx1_dx**2 + src_to_rx1_dy**2)
print(f"  Source->RX1: dx={src_to_rx1_dx:+.4f}, dy={src_to_rx1_dy:+.4f}, "
      f"dist={src_to_rx1_dist:.2f}m")
print(f"  (RX1 is {src_to_rx1_dy:.2f}m AFT and {src_to_rx1_dx:.2f}m STBD of Source)")

# Where would Head_Buoy be relative to vessel?
# Head_Buoy is physically at the cable head — just ahead of RX1.
# If Head_Buoy ≈ cable head, it's roughly at RX1_dy (or slightly less) along-track.
# The offset from Head_Buoy to Source in along-track = Head_Buoy_dy - Source_dy
# If Head_Buoy is near RX1: offset ≈ 69.7 - 60.5 = 9.2m (Head_Buoy is 9.2m AFT of Source)

print(f"\n  If Head_Buoy ≈ cable head (near RX1):")
print(f"    Head_Buoy is {RX1_DY - SOURCE_DY:.2f}m AFT of Source (along-track)")
print(f"    Head_Buoy is {RX1_DX - SOURCE_DX:.2f}m STBD of Source (cross-track)")
print(f"    Vessel-frame offset: {src_to_rx1_dist:.2f}m")

# ── 6. Compare with actual observed offset ──
print("\n[6] Observed Offset vs Expected")
print(f"  Observed A→B mean distance: {merged['dist'].mean():.2f}m")
print(f"  Expected (Head_Buoy=near_RX1): {src_to_rx1_dist:.2f}m")
print(f"  Discrepancy: {merged['dist'].mean() - src_to_rx1_dist:.2f}m")

# The 25.7m is much larger than 9.8m, so Head_Buoy is NOT at RX1 position.
# Let's check: what distance would explain 25.7m?
# Style B source = ship_GPS + source_offset
# If COS_Sparker = GPS on the sparker source itself, then:
#   Style B SOU = COS_Sparker position (or ship GPS with offset)
#   Style A SOU = Head_Buoy GPS position
#   Difference = physical distance Head_Buoy to COS_Sparker
# This is consistent with ~25.7m if Head_Buoy is at the start of a 25m cable.

# ── 7. Test: Apply geometric offset to Head_Buoy to match source ──
print("\n[7] Can we correct Style A source by offsetting Head_Buoy?")

# The offset vector from A→B in map coordinates should correspond to
# the vector from Head_Buoy→Source rotated by cable heading.
# Since Head_Buoy is AFT of source and B is the source position,
# A→B points from Head_Buoy TOWARD source (forward along cable).

# Compute required offset in cable-relative frame:
# For each shot, rotate the A→B vector by -heading to get cable-frame offset
cable_offsets_dx = []
cable_offsets_dy = []

for i, ffid in enumerate(sample_ffids[:500]):
    row = merged[merged['ffid'] == ffid]
    if row.empty or i >= len(cable_headings):
        continue

    dx_map = float(row.iloc[0]['dx'])  # A-B in map frame
    dy_map = float(row.iloc[0]['dy'])
    heading_rad = math.radians(cable_headings[i])

    # Rotate from map to cable frame (heading = angle from North)
    # cable_forward = (sin(h), cos(h)), cable_right = (cos(h), -sin(h))
    cos_h = math.cos(heading_rad)
    sin_h = math.sin(heading_rad)

    # Along-cable (forward positive): project onto (sin_h, cos_h)
    along = dx_map * sin_h + dy_map * cos_h
    # Cross-cable (starboard positive): project onto (cos_h, -sin_h)
    cross = dx_map * cos_h - dy_map * sin_h

    cable_offsets_dx.append(cross)
    cable_offsets_dy.append(along)

mean_cross = np.mean(cable_offsets_dx)
mean_along = np.mean(cable_offsets_dy)
std_cross = np.std(cable_offsets_dx)
std_along = np.std(cable_offsets_dy)

print(f"  A→B offset in cable frame:")
print(f"    Along-cable (A→B): {mean_along:+.2f}m (std={std_along:.2f}m)")
print(f"    Cross-cable (A→B): {mean_cross:+.2f}m (std={std_cross:.2f}m)")
print(f"    Total: {math.sqrt(mean_along**2 + mean_cross**2):.2f}m")

if mean_along > 0:
    print(f"    --> Head_Buoy is {abs(mean_along):.1f}m AFT of true source (cable direction)")
    print(f"    --> To fix: shift Head_Buoy FORWARD by {abs(mean_along):.1f}m along cable")
else:
    print(f"    --> Head_Buoy is {abs(mean_along):.1f}m FORWARD of true source")
    print(f"    --> To fix: shift Head_Buoy AFT by {abs(mean_along):.1f}m along cable")

print(f"\n  Cross-cable: {abs(mean_cross):.1f}m "
      f"({'STBD' if mean_cross > 0 else 'PORT'} of true source)")

# ── 8. If we apply this correction, what's the residual? ──
print("\n[8] Estimated Residual After Correction")
residuals = []
for i, ffid in enumerate(sample_ffids[:500]):
    row = merged[merged['ffid'] == ffid]
    if row.empty or i >= len(cable_headings):
        continue

    heading_rad = math.radians(cable_headings[i])
    sin_h, cos_h = math.sin(heading_rad), math.cos(heading_rad)

    # Corrected source = Head_Buoy + offset in map coordinates
    correction_e = -mean_along * sin_h - mean_cross * cos_h
    correction_n = -mean_along * cos_h + mean_cross * sin_h

    corrected_dx = float(row.iloc[0]['dx']) + correction_e
    corrected_dy = float(row.iloc[0]['dy']) + correction_n
    residual = math.sqrt(corrected_dx**2 + corrected_dy**2)
    residuals.append(residual)

print(f"  Residual after correction:")
print(f"    Mean: {np.mean(residuals):.2f}m")
print(f"    Std:  {np.std(residuals):.2f}m")
print(f"    Max:  {np.max(residuals):.2f}m")
print(f"    P95:  {np.percentile(residuals, 95):.2f}m")

improvement = merged['dist'].mean() - np.mean(residuals)
print(f"\n  Improvement: {merged['dist'].mean():.2f}m -> {np.mean(residuals):.2f}m "
      f"({improvement:.1f}m reduction, {improvement/merged['dist'].mean()*100:.0f}%)")

# ── 9. Alternative: Use COS_Sparker GPS instead of Head_Buoy ──
if 'COS_Sparker' in gps_data:
    print("\n[9] Alternative: Use COS_Sparker GPS directly as source")
    cos_df = gps_data['COS_Sparker']
    # The COS_Sparker GPS is mounted on/near the sparker source
    # It should be very close to the Style B source position
    # (since RadExPro uses COS_Sparker + offset = SOU)
    print(f"  COS_Sparker records: {len(cos_df)}")
    print(f"  If COS_Sparker IS the source GPS, it should match Style B closely")
    print(f"  This would eliminate the 25.7m gap entirely")

print("\n" + "=" * 70)
print("  CONCLUSION")
print("=" * 70)
