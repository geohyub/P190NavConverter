# -*- coding: utf-8 -*-
"""Compare Style A v2 vs Style B P190 outputs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from p190converter.engine.qc.comparison import compare_p190_files

A = r'E:\Software\P190_NavConverter\test_output\M1406_A_S_M1406_A.p190'
B = r'E:\Software\P190_NavConverter\test_output\M1406_S_M1406.p190'

result = compare_p190_files(A, B)
print(f'Common shots: {result.n_common_shots}')
print(f'Source distance - Mean: {result.source_dist_mean:.2f}m')
print(f'Source distance - Std:  {result.source_dist_std:.2f}m')
print(f'Source distance - P95:  {result.source_dist_p95:.2f}m')
print(f'Source distance - Max:  {result.source_dist_max:.2f}m')

# Grade
mean = result.source_dist_mean
if mean < 1:
    grade = 'EXCELLENT'
elif mean < 3:
    grade = 'GOOD'
elif mean < 5:
    grade = 'ACCEPTABLE'
else:
    grade = 'NEEDS REVIEW'
print(f'Grade: {grade}')

# First 5 shots detail
df = result.per_shot_df.head(5)
print(f'\nFirst 5 shots:')
for _, r in df.iterrows():
    print(f'  FFID {int(r["ffid"]):>7d}: '
          f'A=({r["source_x_a"]:.1f}, {r["source_y_a"]:.1f}) '
          f'B=({r["source_x_b"]:.1f}, {r["source_y_b"]:.1f}) '
          f'dist={r["source_dist"]:.2f}m')

# Now compare R records for first shot
print('\n--- R record comparison (first shot) ---')
with open(A) as f:
    a_lines = f.readlines()
with open(B) as f:
    b_lines = f.readlines()

a_s = [l for l in a_lines if l.startswith('S')]
b_s = [l for l in b_lines if l.startswith('S')]
a_r = [l for l in a_lines if l.startswith('R')]
b_r = [l for l in b_lines if l.startswith('R')]

# R records per shot
rps_a = len(a_r) // len(a_s) if a_s else 0
rps_b = len(b_r) // len(b_s) if b_s else 0

print(f'Style A: {len(a_s)} S, {len(a_r)} R ({rps_a} R/shot)')
print(f'Style B: {len(b_s)} S, {len(b_r)} R ({rps_b} R/shot)')

# Parse first shot R records to compare RX positions
def parse_r_receivers(r_lines_subset):
    """Parse receiver positions from R record lines."""
    receivers = {}
    for line in r_lines_subset:
        # 3 groups per R line, each 26 chars starting at col 2
        for g in range(3):
            start = 1 + g * 26  # 0-indexed
            if start + 26 > len(line.rstrip()):
                break
            chunk = line[start:start+26]
            ch_str = chunk[0:4].strip()
            if not ch_str:
                break
            ch = int(ch_str)
            e_str = chunk[4:13].strip()
            n_str = chunk[13:22].strip()
            if e_str and n_str:
                receivers[ch] = (float(e_str), float(n_str))
    return receivers

a_rx = parse_r_receivers(a_r[:rps_a])
b_rx = parse_r_receivers(b_r[:rps_b])

print(f'\nRX comparison (first shot):')
common_ch = sorted(set(a_rx) & set(b_rx))
dists = []
for ch in common_ch:
    ax, ay = a_rx[ch]
    bx, by = b_rx[ch]
    d = np.sqrt((ax-bx)**2 + (ay-by)**2)
    dists.append(d)
    if ch <= 3 or ch == common_ch[-1]:
        print(f'  CH{ch:>3d}: A=({ax:.1f},{ay:.1f}) B=({bx:.1f},{by:.1f}) dist={d:.2f}m')

if dists:
    dists = np.array(dists)
    print(f'\nRX distance stats:')
    print(f'  Mean: {dists.mean():.2f}m, Std: {dists.std():.2f}m, Max: {dists.max():.2f}m')
