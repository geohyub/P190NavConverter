# -*- coding: utf-8 -*-
"""Debug: Physical offset decomposition — WHY is Head_Buoy 25.7m from source?

The 25.7m gap decomposes into:
  1. RX1-to-Source geometric offset (known from RadExPro Marine Geometry)
  2. Head_Buoy-to-RX1 offset (unknown — depends on buoy tethering)

This script:
  1. Computes the known RX1↔Source offset from Marine Geometry
  2. Estimates the Head_Buoy↔RX1 offset from data
  3. Analyzes whether a fixed cable-frame correction can close the gap
  4. Tests if applying known RX1→Source offset to Head_Buoy helps
"""
import sys, os, math
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'

# RadExPro Marine Geometry (PORT+/AFT+ convention)
SOURCE_DX = 2.2547     # Source: 2.25m PORT of vessel ref
SOURCE_DY = 60.535     # Source: 60.5m AFT of vessel ref
RX1_DX = -1.2453       # RX1: 1.25m STARBOARD of vessel ref
RX1_DY = 69.7075       # RX1: 69.7m AFT of vessel ref


def time_str_to_sec(ts):
    try:
        parts = ts.split(':')
        if len(parts) >= 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        return float(ts)
    except:
        return np.nan


print("=" * 80)
print("  PHYSICAL OFFSET DECOMPOSITION")
print("=" * 80)

# ── 1. Known geometric offsets ──
print("\n[1] RadExPro Marine Geometry (vessel frame, PORT+/AFT+)")
print(f"  Source:  dx={SOURCE_DX:+.4f} PORT, dy={SOURCE_DY:+.4f} AFT")
print(f"  RX1:    dx={RX1_DX:+.4f} PORT, dy={RX1_DY:+.4f} AFT")
print(f"          (RX1_DX negative = {abs(RX1_DX):.4f}m STARBOARD)")

# Source → RX1 offset (in vessel frame)
src_to_rx1_dx = RX1_DX - SOURCE_DX   # -1.2453 - 2.2547 = -3.5 (STARBOARD)
src_to_rx1_dy = RX1_DY - SOURCE_DY   # 69.7075 - 60.535 = 9.1725 (AFT)
src_to_rx1_dist = math.sqrt(src_to_rx1_dx**2 + src_to_rx1_dy**2)

print(f"\n  Source → RX1 offset (vessel frame):")
print(f"    dx = {src_to_rx1_dx:+.4f} ({abs(src_to_rx1_dx):.2f}m {'STARBOARD' if src_to_rx1_dx < 0 else 'PORT'})")
print(f"    dy = {src_to_rx1_dy:+.4f} ({abs(src_to_rx1_dy):.2f}m AFT)")
print(f"    distance = {src_to_rx1_dist:.2f}m")
print(f"  → RX1은 Source보다 {src_to_rx1_dy:.2f}m 뒤(AFT)에 있고, "
      f"{abs(src_to_rx1_dx):.2f}m 우현(STBD)에 있음")

# In cable frame (Source → RX1 direction is roughly AFT along cable)
print(f"\n  케이블 방향 기준:")
print(f"    Source는 RX1보다 {abs(src_to_rx1_dy):.2f}m 앞(FORWARD)에 있음")
print(f"    Source는 RX1보다 {abs(src_to_rx1_dx):.2f}m 좌현(PORT)에 있음")

# ── 2. Parse GPS data ──
print("\n[2] GPS 데이터 파싱 중...")
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
sou_x = track_data.df['sou_x'].values  # RadExPro SOU (ground truth)
sou_y = track_data.df['sou_y'].values
n_shots = len(shot_times)

# Head_Buoy GPS
df_hb = parse_npd(NPD, source='Head_Buoy')
df_hb['time_sec'] = df_hb['time_str'].apply(time_str_to_sec)
df_hb = df_hb.dropna(subset=['time_sec']).sort_values('time_sec')
df_hb = df_hb.drop_duplicates(subset='time_sec', keep='first')
hb_cs_e = CubicSpline(df_hb['time_sec'].values, df_hb['east'].values)
hb_cs_n = CubicSpline(df_hb['time_sec'].values, df_hb['north'].values)
hb_e = hb_cs_e(shot_times)
hb_n = hb_cs_n(shot_times)

# Tail_Buoy GPS
df_tb = parse_npd(NPD, source='Tail_Buoy')
df_tb['time_sec'] = df_tb['time_str'].apply(time_str_to_sec)
df_tb = df_tb.dropna(subset=['time_sec']).sort_values('time_sec')
df_tb = df_tb.drop_duplicates(subset='time_sec', keep='first')
tb_cs_e = CubicSpline(df_tb['time_sec'].values, df_tb['east'].values)
tb_cs_n = CubicSpline(df_tb['time_sec'].values, df_tb['north'].values)
tb_e = tb_cs_e(shot_times)
tb_n = tb_cs_n(shot_times)

print(f"  Head_Buoy: {len(df_hb)} records")
print(f"  Tail_Buoy: {len(df_tb)} records")

# ── 3. Decompose Head_Buoy → SOU offset in cable frame ──
print("\n[3] Head_Buoy → RadExPro SOU 오프셋 분해 (케이블 프레임)")

# Cable heading from Head_Buoy → Tail_Buoy
cable_headings = np.array([
    math.degrees(math.atan2(float(hb_e[i]-tb_e[i]), float(hb_n[i]-tb_n[i]))) % 360
    for i in range(n_shots)
])

# Head_Buoy → SOU in map frame
dx_map = hb_e - sou_x   # HB - SOU
dy_map = hb_n - sou_y

# Rotate to cable frame
along_cable = []   # forward positive
cross_cable = []   # starboard positive

for i in range(n_shots):
    h_rad = math.radians(cable_headings[i])
    sin_h = math.sin(h_rad)
    cos_h = math.cos(h_rad)

    # Along-cable (forward = toward Head_Buoy from Source)
    along = float(dx_map[i]) * sin_h + float(dy_map[i]) * cos_h
    # Cross-cable (starboard positive)
    cross = float(dx_map[i]) * cos_h - float(dy_map[i]) * sin_h

    along_cable.append(along)
    cross_cable.append(cross)

along_cable = np.array(along_cable)
cross_cable = np.array(cross_cable)

print(f"  Head_Buoy → SOU offset (케이블 프레임):")
print(f"    Along-cable (FWD+): mean={along_cable.mean():+.2f}m, std={along_cable.std():.2f}m")
print(f"    Cross-cable (STBD+): mean={cross_cable.mean():+.2f}m, std={cross_cable.std():.2f}m")
print(f"    Total distance: mean={np.sqrt(dx_map**2 + dy_map**2).mean():.2f}m")

if along_cable.mean() > 0:
    print(f"\n  → Head_Buoy는 Source보다 {along_cable.mean():.1f}m 앞(FORWARD)에 있음")
else:
    print(f"\n  → Head_Buoy는 Source보다 {abs(along_cable.mean()):.1f}m 뒤(AFT)에 있음")

if cross_cable.mean() > 0:
    print(f"  → Head_Buoy는 Source보다 {cross_cable.mean():.1f}m 우현(STBD)에 있음")
else:
    print(f"  → Head_Buoy는 Source보다 {abs(cross_cable.mean()):.1f}m 좌현(PORT)에 있음")

# ── 4. Break down the offset ──
print(f"\n[4] 오프셋 분해")
print(f"  Head_Buoy → SOU 전체:     along={along_cable.mean():+.2f}m, cross={cross_cable.mean():+.2f}m")
print(f"  RX1 → Source (기하학적):    along={-src_to_rx1_dy:+.2f}m, cross={-src_to_rx1_dx:+.2f}m")

# Head_Buoy → RX1 offset (estimated)
hb_to_rx1_along = along_cable.mean() - (-src_to_rx1_dy)  # HB→SOU - (RX1→SOU)
hb_to_rx1_cross = cross_cable.mean() - (-src_to_rx1_dx)
hb_to_rx1_dist = math.sqrt(hb_to_rx1_along**2 + hb_to_rx1_cross**2)

print(f"  Head_Buoy → RX1 (추정):    along={hb_to_rx1_along:+.2f}m, cross={hb_to_rx1_cross:+.2f}m")
print(f"                              distance={hb_to_rx1_dist:.2f}m")
print(f"\n  해석:")
print(f"    - RX1→Source 기하학적 거리: {src_to_rx1_dist:.2f}m (알려진 값)")
print(f"    - Head_Buoy→RX1 추정 거리: {hb_to_rx1_dist:.2f}m (데이터 추정)")
print(f"    - Head_Buoy→Source 전체:   {np.sqrt(dx_map**2 + dy_map**2).mean():.2f}m (관측값)")

# ── 5. Apply cable-frame correction ──
print(f"\n[5] 케이블 프레임 보정 적용 시 잔차")

mean_along = along_cable.mean()
mean_cross = cross_cable.mean()

corrected_dists = []
for i in range(n_shots):
    h_rad = math.radians(cable_headings[i])
    sin_h = math.sin(h_rad)
    cos_h = math.cos(h_rad)

    # Apply correction: subtract the mean cable-frame offset
    corr_e = -mean_along * sin_h - mean_cross * cos_h
    corr_n = -mean_along * cos_h + mean_cross * sin_h

    corrected_e = float(hb_e[i]) + corr_e
    corrected_n = float(hb_n[i]) + corr_n

    d = math.sqrt((corrected_e - sou_x[i])**2 + (corrected_n - sou_y[i])**2)
    corrected_dists.append(d)

corrected_dists = np.array(corrected_dists)
print(f"  보정 전: mean={np.sqrt(dx_map**2 + dy_map**2).mean():.2f}m")
print(f"  보정 후: mean={corrected_dists.mean():.2f}m, std={corrected_dists.std():.2f}m, "
      f"p95={np.percentile(corrected_dists, 95):.2f}m, max={corrected_dists.max():.2f}m")
print(f"  개선:    {np.sqrt(dx_map**2 + dy_map**2).mean():.2f}m -> {corrected_dists.mean():.2f}m "
      f"({(1 - corrected_dists.mean()/np.sqrt(dx_map**2 + dy_map**2).mean())*100:.0f}% 개선)")

# ── 6. What if we use the KNOWN Source→RX1 offset instead? ──
print(f"\n[6] Head_Buoy ~= RX1 가정하고, 알려진 RX1→Source 오프셋만 적용")

# If Head_Buoy ~= RX1, then:
# Source = Head_Buoy + rotate(RX1_to_Source, heading)
# RX1→Source in PORT+/AFT+: dx = -(src_to_rx1_dx) = +3.5 PORT
#                            dy = -(src_to_rx1_dy) = -9.1725 AFT = 9.1725 FWD
# Convert to STBD+/FWD+: dx=-3.5, dy=+9.1725
known_src_dx_stbd = -3.5000    # PORT 3.5m = STBD -3.5m
known_src_dy_fwd = 9.1725      # FORWARD 9.17m

known_corr_dists = []
for i in range(n_shots):
    h_rad = math.radians(cable_headings[i])
    cos_h = math.cos(h_rad)
    sin_h = math.sin(h_rad)

    # OffsetDefinition.rotate: STBD+/FWD+
    de = known_src_dx_stbd * cos_h + known_src_dy_fwd * sin_h
    dn = -known_src_dx_stbd * sin_h + known_src_dy_fwd * cos_h

    src_e = float(hb_e[i]) + de
    src_n = float(hb_n[i]) + dn

    d = math.sqrt((src_e - sou_x[i])**2 + (src_n - sou_y[i])**2)
    known_corr_dists.append(d)

known_corr_dists = np.array(known_corr_dists)
print(f"  RX1→Source offset: dx={known_src_dx_stbd:+.2f} STBD, dy={known_src_dy_fwd:+.2f} FWD")
print(f"  보정 후: mean={known_corr_dists.mean():.2f}m, std={known_corr_dists.std():.2f}m")
print(f"  개선:    {np.sqrt(dx_map**2 + dy_map**2).mean():.2f}m -> {known_corr_dists.mean():.2f}m")

# ── 7. Sensitivity: How stable is the cable-frame offset over time? ──
print(f"\n[7] 케이블 프레임 오프셋 안정성 (시간별)")
n_bins = 10
bin_size = n_shots // n_bins
print(f"  {'시간 범위':>20s}  {'Along(m)':>10s}  {'Cross(m)':>10s}  {'알고 STD':>10s}")
for b in range(n_bins):
    start = b * bin_size
    end = min(start + bin_size, n_shots)
    chunk_along = along_cable[start:end]
    chunk_cross = cross_cable[start:end]
    t_start = shot_times[start]
    t_end = shot_times[end-1]
    h_start = int(t_start // 3600)
    m_start = int((t_start % 3600) // 60)
    h_end = int(t_end // 3600)
    m_end = int((t_end % 3600) // 60)
    print(f"  {h_start:02d}:{m_start:02d}-{h_end:02d}:{m_end:02d}         "
          f"{chunk_along.mean():+10.2f}  {chunk_cross.mean():+10.2f}  "
          f"{chunk_along.std():10.2f}")

print(f"\n  전체 Along STD: {along_cable.std():.2f}m, Cross STD: {cross_cable.std():.2f}m")

# ── 8. GPS staircase 분석 ──
print(f"\n[8] NPD GPS 계단 효과 분석")
# Check how many unique positions Head_Buoy has
hb_times = df_hb['time_sec'].values
hb_east_raw = df_hb['east'].values
unique_e = len(np.unique(hb_east_raw))
total_e = len(hb_east_raw)

# Time between unique position changes
diffs = np.diff(hb_east_raw)
change_idx = np.where(diffs != 0)[0]
if len(change_idx) > 1:
    time_between_changes = np.diff(hb_times[change_idx])
    mean_update_interval = time_between_changes.mean()
else:
    mean_update_interval = 0

print(f"  Head_Buoy GPS:")
print(f"    총 레코드: {total_e}")
print(f"    고유 위치(East): {unique_e} ({unique_e/total_e*100:.1f}%)")
print(f"    위치 변경 간격: mean={mean_update_interval:.2f}s")

# Same for Vessel Ref
df_vr = parse_npd(NPD, source='Vessel Ref (Priority 1)')
df_vr['time_sec'] = df_vr['time_str'].apply(time_str_to_sec)
df_vr = df_vr.dropna(subset=['time_sec']).sort_values('time_sec')
df_vr = df_vr.drop_duplicates(subset='time_sec', keep='first')
vr_e_raw = df_vr['east'].values
vr_times = df_vr['time_sec'].values
unique_vr = len(np.unique(vr_e_raw))
diffs_vr = np.diff(vr_e_raw)
change_idx_vr = np.where(diffs_vr != 0)[0]
if len(change_idx_vr) > 1:
    time_between_vr = np.diff(vr_times[change_idx_vr])
    mean_vr_interval = time_between_vr.mean()
else:
    mean_vr_interval = 0

print(f"\n  Vessel Ref GPS:")
print(f"    총 레코드: {len(df_vr)}")
print(f"    고유 위치(East): {unique_vr} ({unique_vr/len(df_vr)*100:.1f}%)")
print(f"    위치 변경 간격: mean={mean_vr_interval:.2f}s")

# Speed estimate
if len(change_idx) > 10:
    # Vessel speed from Head_Buoy
    speed_samples = []
    for j in range(min(1000, len(change_idx)-1)):
        i0, i1 = change_idx[j], change_idx[j+1]
        de = hb_east_raw[i1] - hb_east_raw[i0]
        dn = df_hb['north'].values[i1] - df_hb['north'].values[i0]
        dt = hb_times[i1] - hb_times[i0]
        if dt > 0:
            speed = math.sqrt(de**2 + dn**2) / dt
            speed_samples.append(speed)
    if speed_samples:
        mean_speed = np.mean(speed_samples)
        print(f"\n  추정 선속: {mean_speed:.2f} m/s ({mean_speed*1.94384:.1f} knots)")
        print(f"  GPS 업데이트 간격 {mean_update_interval:.1f}s 동안 이동 거리: "
              f"{mean_speed * mean_update_interval:.1f}m")
        print(f"  → CubicSpline 보간 최대 오차 추정: {mean_speed * mean_update_interval / 2:.1f}m")

print("\n" + "=" * 80)
print("  최종 분석")
print("=" * 80)
print(f"""
  25.7m 차이의 구성:
  ┌─────────────────────────────────────────────────────────┐
  │ Head_Buoy GPS안테나 → Source 물리적 위치               │
  │                                                         │
  │  1. Head_Buoy → RX1(케이블 헤드):  ~{hb_to_rx1_dist:.1f}m              │
  │     (부이 테더링 + GPS 안테나 위치)                     │
  │                                                         │
  │  2. RX1 → Source (기하학적):        ~{src_to_rx1_dist:.1f}m              │
  │     (RadExPro Marine Geometry로부터 알려진 값)          │
  │                                                         │
  │  3. GPS 해상도/보간 오차:           ~{corrected_dists.mean():.1f}m              │
  │     (계단 효과 + CubicSpline 잔차)                     │
  │                                                         │
  │  합계: ~{np.sqrt(dx_map**2 + dy_map**2).mean():.1f}m                                         │
  └─────────────────────────────────────────────────────────┘

  케이블 프레임 보정 시: {np.sqrt(dx_map**2 + dy_map**2).mean():.1f}m → {corrected_dists.mean():.1f}m ({(1 - corrected_dists.mean()/np.sqrt(dx_map**2 + dy_map**2).mean())*100:.0f}% 개선)
  알려진 RX1→Source만 적용: {np.sqrt(dx_map**2 + dy_map**2).mean():.1f}m → {known_corr_dists.mean():.1f}m
""")
