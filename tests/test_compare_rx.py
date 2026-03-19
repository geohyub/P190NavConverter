# -*- coding: utf-8 -*-
"""Compare R records between Style A v2 and Style B."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

A = r'E:\Software\P190_NavConverter\test_output\M1406_A_S_M1406_A.p190'
B = r'E:\Software\P190_NavConverter\test_output\M1406_S_M1406.p190'

def parse_shot_data(filepath, max_shots=None):
    """Parse S and R records, returning list of (ffid, source_xy, {ch: (x,y)})."""
    shots = []
    current_ffid = None
    current_source = None
    current_rx = {}

    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            line = line.rstrip().ljust(80)
            if line[0] == 'S':
                # Save previous shot
                if current_ffid is not None:
                    shots.append((current_ffid, current_source, current_rx))
                    if max_shots and len(shots) >= max_shots:
                        break

                ffid = int(line[19:25].strip())
                east = float(line[46:55].strip())
                north = float(line[55:64].strip())
                current_ffid = ffid
                current_source = (east, north)
                current_rx = {}

            elif line[0] == 'R':
                for g in range(3):
                    start = 1 + g * 26
                    chunk = line[start:start+26]
                    ch_str = chunk[0:4].strip()
                    if not ch_str:
                        break
                    try:
                        ch = int(ch_str)
                        e = float(chunk[4:13].strip())
                        n = float(chunk[13:22].strip())
                        current_rx[ch] = (e, n)
                    except (ValueError, IndexError):
                        pass

    if current_ffid is not None:
        shots.append((current_ffid, current_source, current_rx))

    return shots

print('Parsing Style A...')
shots_a = parse_shot_data(A, max_shots=100)
print(f'  Parsed {len(shots_a)} shots')

print('Parsing Style B...')
shots_b = parse_shot_data(B, max_shots=100)
print(f'  Parsed {len(shots_b)} shots')

# Match by FFID
a_dict = {s[0]: s for s in shots_a}
b_dict = {s[0]: s for s in shots_b}
common = sorted(set(a_dict) & set(b_dict))

print(f'\nCommon shots (first 100): {len(common)}')

# Compare
all_src_dists = []
all_rx_dists = []
per_ch_dists = {ch: [] for ch in range(1, 17)}

for ffid in common:
    _, src_a, rx_a = a_dict[ffid]
    _, src_b, rx_b = b_dict[ffid]

    sd = np.sqrt((src_a[0]-src_b[0])**2 + (src_a[1]-src_b[1])**2)
    all_src_dists.append(sd)

    for ch in range(1, 17):
        if ch in rx_a and ch in rx_b:
            rd = np.sqrt((rx_a[ch][0]-rx_b[ch][0])**2 + (rx_a[ch][1]-rx_b[ch][1])**2)
            all_rx_dists.append(rd)
            per_ch_dists[ch].append(rd)

all_src_dists = np.array(all_src_dists)
all_rx_dists = np.array(all_rx_dists)

print(f'\n=== Source Position ===')
print(f'  Mean: {all_src_dists.mean():.3f}m')

print(f'\n=== Receiver Positions (all channels) ===')
print(f'  Mean: {all_rx_dists.mean():.3f}m')
print(f'  Std:  {all_rx_dists.std():.3f}m')
print(f'  P95:  {np.percentile(all_rx_dists, 95):.3f}m')
print(f'  Max:  {all_rx_dists.max():.3f}m')

print(f'\n=== Per-Channel Mean Distance ===')
for ch in range(1, 17):
    if per_ch_dists[ch]:
        d = np.array(per_ch_dists[ch])
        print(f'  CH{ch:>2d}: mean={d.mean():.3f}m, max={d.max():.3f}m')

# Detail: first 3 shots
print(f'\n=== First 3 shots detail ===')
for ffid in common[:3]:
    _, src_a, rx_a = a_dict[ffid]
    _, src_b, rx_b = b_dict[ffid]
    sd = np.sqrt((src_a[0]-src_b[0])**2 + (src_a[1]-src_b[1])**2)
    print(f'\nFFID {ffid}:')
    print(f'  Source A: ({src_a[0]:.1f}, {src_a[1]:.1f})')
    print(f'  Source B: ({src_b[0]:.1f}, {src_b[1]:.1f})  dist={sd:.3f}m')
    for ch in [1, 2, 8, 16]:
        if ch in rx_a and ch in rx_b:
            rd = np.sqrt((rx_a[ch][0]-rx_b[ch][0])**2 + (rx_a[ch][1]-rx_b[ch][1])**2)
            print(f'  RX{ch:>2d} A: ({rx_a[ch][0]:.1f}, {rx_a[ch][1]:.1f})  '
                  f'B: ({rx_b[ch][0]:.1f}, {rx_b[ch][1]:.1f})  dist={rd:.3f}m')
