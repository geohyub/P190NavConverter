# -*- coding: utf-8 -*-
"""Compare Style A P190 source positions vs Track file reference positions.

Track 파일의 SOU_X/Y는 RadExPro가 기록한 실제 소스 위치.
Style A P190의 소스 위치는 GPS 보간 + offset 회전으로 계산한 값.
이 둘의 차이가 Style A 보간의 정확도를 나타냄.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.qc.comparison import _parse_s_records

# Paths
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
P190_A = r'D:\Geoview_Junhyub\2025\자산관리\소프트웨어\P190_NavConverter\test_output\M1406_Test_S_M1406_Test.p190'

# 1. Load Track reference
track_data = parse_track_file(TRACK)
df_track = track_data.df[["ffid", "sou_x", "sou_y"]].copy()
# Truncate FFID to 6 digits (P190 format)
df_track["ffid6"] = df_track["ffid"].astype(int) % 1000000

print(f"Track: {len(df_track)} shots, FFID {df_track['ffid'].min()}-{df_track['ffid'].max()}")
print(f"Track FFID (6-digit): {df_track['ffid6'].min()}-{df_track['ffid6'].max()}")

# 2. Load Style A P190
df_a = _parse_s_records(P190_A)
print(f"Style A P190: {len(df_a)} S records, FFID {df_a['ffid'].min()}-{df_a['ffid'].max()}")

# 3. Merge on 6-digit FFID
merged = pd.merge(
    df_a, df_track,
    left_on="ffid", right_on="ffid6",
    how="inner",
)
print(f"\nMatched shots: {len(merged)}")

# 4. Compute differences
merged["dx"] = merged["easting"] - merged["sou_x"]
merged["dy"] = merged["northing"] - merged["sou_y"]
merged["dist"] = np.sqrt(merged["dx"]**2 + merged["dy"]**2)

print(f"\n=== Source Position Difference (Style A vs Track Reference) ===")
print(f"Mean:    {merged['dist'].mean():.2f} m")
print(f"Std:     {merged['dist'].std():.2f} m")
print(f"Median:  {merged['dist'].median():.2f} m")
print(f"P95:     {np.percentile(merged['dist'], 95):.2f} m")
print(f"Max:     {merged['dist'].max():.2f} m")
print(f"Min:     {merged['dist'].min():.2f} m")

print(f"\n=== Component Differences ===")
print(f"dX mean: {merged['dx'].mean():.2f} m  (std: {merged['dx'].std():.2f})")
print(f"dY mean: {merged['dy'].mean():.2f} m  (std: {merged['dy'].std():.2f})")

# 5. Grade assessment
mean_dist = merged['dist'].mean()
if mean_dist < 3.0:
    grade = "EXCELLENT"
elif mean_dist < 5.0:
    grade = "GOOD"
elif mean_dist < 10.0:
    grade = "ACCEPTABLE"
else:
    grade = "NEEDS REVIEW"
print(f"\nGrade: {grade} (mean={mean_dist:.2f}m)")

# 6. Show a few samples
print(f"\n=== Sample Shots ===")
sample_idx = np.linspace(0, len(merged)-1, 5, dtype=int)
for idx in sample_idx:
    row = merged.iloc[idx]
    print(f"  FFID {int(row['ffid_x']):>7d}: "
          f"A=({row['easting']:.1f}, {row['northing']:.1f})  "
          f"Track=({row['sou_x']:.1f}, {row['sou_y']:.1f})  "
          f"diff={row['dist']:.2f}m")
