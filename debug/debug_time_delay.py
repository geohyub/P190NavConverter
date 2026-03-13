# -*- coding: utf-8 -*-
"""Debug: Investigate TIME DELAY between NPD GPS and Track shot times.

If there's a systematic time offset (e.g., NPD GPS is 0.5s behind shot trigger),
all CubicSpline interpolated positions will be shifted.

This script:
1. Tests Vessel_Ref + offset rotation with different time delays (-5s to +5s)
2. For each delay, re-interpolates GPS positions at shifted times
3. Applies offset rotation with front-tail heading
4. Finds the optimal time delay that minimizes distance to RadExPro SOU

Also separately tests: Head_Buoy direct with time delay (to reduce 25.7m gap)
"""
import sys, os, math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'

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


def build_splines(npd_file, source_name):
    """Parse NPD GPS source and build CubicSpline interpolators."""
    df = parse_npd(npd_file, source=source_name)
    df['time_sec'] = df['time_str'].apply(time_str_to_sec)
    df = df.dropna(subset=['time_sec']).sort_values('time_sec')
    df = df.drop_duplicates(subset='time_sec', keep='first')
    cs_e = CubicSpline(df['time_sec'].values, df['east'].values)
    cs_n = CubicSpline(df['time_sec'].values, df['north'].values)
    return cs_e, cs_n, df['time_sec'].values


def compute_heading_arrays(front_e, front_n, tail_e, tail_n):
    """Compute cable heading from front-tail GPS arrays."""
    n = len(front_e)
    headings = np.zeros(n)
    for i in range(n):
        dx = float(front_e[i] - tail_e[i])
        dy = float(front_n[i] - tail_n[i])
        headings[i] = math.degrees(math.atan2(dx, dy)) % 360
    return headings


print("=" * 80)
print("  TIME DELAY ANALYSIS")
print("=" * 80)

# ── Parse Track (shot times + SOU_X/SOU_Y as ground truth) ──
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
sou_x = track_data.df['sou_x'].values
sou_y = track_data.df['sou_y'].values
n_shots = len(shot_times)

# ── Build GPS splines ──
print("Building GPS interpolation splines...")
vessel_cs_e, vessel_cs_n, vessel_times = build_splines(NPD, 'Vessel Ref (Priority 1)')
head_cs_e, head_cs_n, head_times = build_splines(NPD, 'Head_Buoy')
tail_cs_e, tail_cs_n, tail_times = build_splines(NPD, 'Tail_Buoy')
cos_cs_e, cos_cs_n, cos_times = build_splines(NPD, 'COS_Sparker')

time_range = (max(vessel_times.min(), head_times.min(), tail_times.min()),
              min(vessel_times.max(), head_times.max(), tail_times.max()))
print(f"GPS time range: {time_range[0]:.0f}s - {time_range[1]:.0f}s")
print(f"Shot time range: {shot_times.min():.0f}s - {shot_times.max():.0f}s")
print(f"Shots: {n_shots}")

# ── Test 1: Head_Buoy direct with time delay ──
print("\n" + "=" * 80)
print("  TEST 1: Head_Buoy DIRECT with time delay")
print("=" * 80)

delays = np.arange(-5.0, 5.1, 0.25)  # -5s to +5s in 0.25s steps
head_results = []

for dt in delays:
    shifted_times = shot_times + dt
    he = head_cs_e(shifted_times)
    hn = head_cs_n(shifted_times)
    dists = np.sqrt((he - sou_x)**2 + (hn - sou_y)**2)
    head_results.append((dt, dists.mean(), dists.std()))

head_results = np.array(head_results)
best_idx = np.argmin(head_results[:, 1])
best_dt_head = head_results[best_idx, 0]
best_mean_head = head_results[best_idx, 1]

print(f"\n  Delay scan results (mean distance to RadExPro SOU):")
print(f"  {'Delay(s)':>8s}  {'Mean(m)':>8s}  {'Std(m)':>7s}")
for dt, mean, std in head_results[::4]:  # every 1s
    marker = " <-- BEST" if dt == best_dt_head else ""
    print(f"  {dt:+8.2f}  {mean:8.2f}  {std:7.2f}{marker}")

print(f"\n  BEST Head_Buoy delay: {best_dt_head:+.2f}s -> mean={best_mean_head:.2f}m")
print(f"  (vs no delay: {head_results[len(delays)//2, 1]:.2f}m)")

# ── Test 2: Vessel_Ref + offset rotation with time delay ──
print("\n" + "=" * 80)
print("  TEST 2: Vessel_Ref + source offset + front-tail heading + time delay")
print("=" * 80)

# Best rotation from previous test: PORT+/AFT+ with (-dx, +dy)
# In map coordinates:
#   de = (-SOURCE_DX) * (-cos_h) + SOURCE_DY * (-sin_h)
#   dn = (-SOURCE_DX) * sin_h + SOURCE_DY * (-cos_h)
# Simplified:
#   de = SOURCE_DX * cos_h - SOURCE_DY * sin_h
#   dn = -SOURCE_DX * sin_h - SOURCE_DY * cos_h

def compute_vessel_sou_with_delay(dt, sign_dx=1, sign_dy=1):
    """Compute source position = Vessel_Ref + rotated offset at shifted times."""
    shifted_times = shot_times + dt
    ve = vessel_cs_e(shifted_times)
    vn = vessel_cs_n(shifted_times)

    # Heading from Head_Buoy → Tail_Buoy (cable direction, NOT shifted)
    # Heading should be from unshifted times (represents physical cable orientation)
    he = head_cs_e(shifted_times)
    hn = head_cs_n(shifted_times)
    te = tail_cs_e(shifted_times)
    tn = tail_cs_n(shifted_times)
    headings = compute_heading_arrays(he, hn, te, tn)

    src_e = np.zeros(n_shots)
    src_n = np.zeros(n_shots)

    dx = sign_dx * SOURCE_DX
    dy = sign_dy * SOURCE_DY

    for i in range(n_shots):
        h = math.radians(headings[i])
        cos_h, sin_h = math.cos(h), math.sin(h)
        # STBD+/FWD+ convention (our OffsetDefinition.rotate)
        # de = dx * cos_h + dy * sin_h
        # dn = -dx * sin_h + dy * cos_h
        de = dx * cos_h + dy * sin_h
        dn = -dx * sin_h + dy * cos_h
        src_e[i] = float(ve[i]) + de
        src_n[i] = float(vn[i]) + dn

    dists = np.sqrt((src_e - sou_x)**2 + (src_n - sou_y)**2)
    return dists.mean(), dists.std()


# Test all sign combinations with delay scan
print(f"\n  Testing all sign combos with time delay scan...")
sign_combos = [
    ("+stbd +fwd", +1, +1),
    ("-stbd +fwd", -1, +1),
    ("+stbd -fwd", +1, -1),
    ("-stbd -fwd", -1, -1),
]

all_vessel_results = []
for sign_label, sx, sy in sign_combos:
    combo_results = []
    for dt in delays:
        mean_d, std_d = compute_vessel_sou_with_delay(dt, sx, sy)
        combo_results.append((dt, mean_d, std_d))

    combo_results = np.array(combo_results)
    best_idx = np.argmin(combo_results[:, 1])
    best_dt = combo_results[best_idx, 0]
    best_mean = combo_results[best_idx, 1]
    best_std = combo_results[best_idx, 2]

    all_vessel_results.append({
        'signs': sign_label,
        'sx': sx, 'sy': sy,
        'best_dt': best_dt,
        'best_mean': best_mean,
        'best_std': best_std,
        'results': combo_results,
    })

    print(f"  {sign_label:>14s}: best delay={best_dt:+.2f}s -> "
          f"mean={best_mean:.2f}m, std={best_std:.2f}m")

# Find overall best
best_vessel = min(all_vessel_results, key=lambda x: x['best_mean'])
print(f"\n  OVERALL BEST: {best_vessel['signs']} at dt={best_vessel['best_dt']:+.2f}s")
print(f"    Mean: {best_vessel['best_mean']:.2f}m, Std: {best_vessel['best_std']:.2f}m")

# ── Test 3: Fine-grained optimization for the best combo ──
print("\n" + "=" * 80)
print("  TEST 3: Fine-grained time delay optimization")
print("=" * 80)

# Fine scan around the best delay
def objective_vessel(dt):
    mean_d, _ = compute_vessel_sou_with_delay(
        dt, best_vessel['sx'], best_vessel['sy'])
    return mean_d

result_opt = minimize_scalar(
    objective_vessel,
    bounds=(best_vessel['best_dt'] - 2.0, best_vessel['best_dt'] + 2.0),
    method='bounded',
)

opt_dt = result_opt.x
opt_mean, opt_std = compute_vessel_sou_with_delay(
    opt_dt, best_vessel['sx'], best_vessel['sy'])

print(f"  Optimal delay: {opt_dt:+.4f}s")
print(f"  Optimal mean distance: {opt_mean:.3f}m")
print(f"  Optimal std: {opt_std:.3f}m")

# Fine scan for Head_Buoy too
def objective_head(dt):
    shifted = shot_times + dt
    he = head_cs_e(shifted)
    hn = head_cs_n(shifted)
    return np.sqrt((he - sou_x)**2 + (hn - sou_y)**2).mean()

result_head_opt = minimize_scalar(
    objective_head,
    bounds=(best_dt_head - 2.0, best_dt_head + 2.0),
    method='bounded',
)
opt_dt_head = result_head_opt.x
opt_mean_head = result_head_opt.fun

print(f"\n  Head_Buoy optimal delay: {opt_dt_head:+.4f}s")
print(f"  Head_Buoy optimal mean: {opt_mean_head:.3f}m")

# ── Test 4: COS_Sparker with time delay ──
print("\n" + "=" * 80)
print("  TEST 4: COS_Sparker direct with time delay")
print("=" * 80)

def objective_cos(dt):
    shifted = shot_times + dt
    ce = cos_cs_e(shifted)
    cn = cos_cs_n(shifted)
    return np.sqrt((ce - sou_x)**2 + (cn - sou_y)**2).mean()

cos_results = []
for dt in delays:
    mean_d = objective_cos(dt)
    cos_results.append((dt, mean_d))

cos_results = np.array(cos_results)
best_idx = np.argmin(cos_results[:, 1])
best_dt_cos = cos_results[best_idx, 0]
best_mean_cos = cos_results[best_idx, 1]

result_cos_opt = minimize_scalar(
    objective_cos,
    bounds=(best_dt_cos - 2.0, best_dt_cos + 2.0),
    method='bounded',
)
opt_dt_cos = result_cos_opt.x
opt_mean_cos = result_cos_opt.fun

print(f"  Best COS_Sparker delay: {opt_dt_cos:+.4f}s")
print(f"  Best COS_Sparker mean: {opt_mean_cos:.3f}m")
print(f"  (vs no delay: {objective_cos(0):.3f}m)")

# ── Summary ──
print("\n" + "=" * 80)
print("  FINAL SUMMARY")
print("=" * 80)
print(f"  {'Method':>35s}  {'Delay(s)':>8s}  {'Mean(m)':>8s}  {'Notes'}")
print(f"  {'-'*70}")
print(f"  {'Head_Buoy (no delay)':>35s}  {0:+8.2f}  {objective_head(0):8.2f}  현재 구현")
print(f"  {'Head_Buoy (optimal delay)':>35s}  {opt_dt_head:+8.4f}  {opt_mean_head:8.3f}  시간 보정")
print(f"  {'COS_Sparker (no delay)':>35s}  {0:+8.2f}  {objective_cos(0):8.2f}  직접 GPS")
print(f"  {'COS_Sparker (optimal delay)':>35s}  {opt_dt_cos:+8.4f}  {opt_mean_cos:8.3f}  시간 보정")
print(f"  {'Vessel+offset (best, no delay)':>35s}  {0:+8.2f}  "
      f"{compute_vessel_sou_with_delay(0, best_vessel['sx'], best_vessel['sy'])[0]:8.2f}  오프셋 회전")
print(f"  {'Vessel+offset (best+delay)':>35s}  {opt_dt:+8.4f}  {opt_mean:8.3f}  최적")
print(f"  {'Track SOU_X/SOU_Y':>35s}  {'N/A':>8s}  {0.000:8.3f}  RadExPro 동일")

print(f"\n  결론:")
if opt_mean < 1.0:
    print(f"  → Vessel_Ref + 오프셋 + 시간보정({opt_dt:+.2f}s)으로 {opt_mean:.3f}m 매칭 가능!")
elif opt_mean_cos < opt_mean:
    print(f"  → COS_Sparker + 시간보정({opt_dt_cos:+.2f}s)이 가장 좋은 독립 GPS ({opt_mean_cos:.3f}m)")
else:
    print(f"  → Vessel_Ref + 오프셋이 최적 ({opt_mean:.3f}m), 잔차는 GPS 해상도 한계")
