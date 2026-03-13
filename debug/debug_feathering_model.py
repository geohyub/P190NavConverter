# -*- coding: utf-8 -*-
"""Debug: Feathering interpolation model vs Linear interpolation.

Compares:
  1. Linear interpolation (current) - receivers on straight line
  2. Feathering model (quadratic, alpha=2.0) - curved cable correction
  3. Different alpha values sensitivity
"""
import sys, os, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.npd_parser import parse_npd
from p190converter.engine.parsers.track_parser import parse_track_file
from p190converter.engine.geometry.interpolation import (
    compute_heading,
    interpolate_receivers_linear,
    interpolate_receivers_feathering,
    compute_feathering_angle,
)
from p190converter.engine.geometry.gps_interpolation import (
    npd_time_to_seconds,
    interpolate_gps_at_times,
    compute_vessel_cog,
)
from p190converter.models.survey_config import MarineGeometry

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'


def build_gps_arrays(npd_file, source_name):
    df = parse_npd(npd_file, source=source_name)
    times = np.array([npd_time_to_seconds(t) if t else np.nan for t in df['time_str']])
    east = df['east'].values.astype(float)
    north = df['north'].values.astype(float)
    return times, east, north


print("=" * 80)
print("  FEATHERING INTERPOLATION MODEL ANALYSIS (Correction-Based)")
print("=" * 80)

# Parse Track
track_data = parse_track_file(TRACK)
shot_times = track_data.df['time_seconds'].values
n_shots = len(shot_times)
print(f"Track: {n_shots} shots")

# Parse NPD GPS
print("Parsing NPD GPS sources...")
front_t, front_e, front_n = build_gps_arrays(NPD, 'Head_Buoy')
tail_t, tail_e, tail_n = build_gps_arrays(NPD, 'Tail_Buoy')

# Interpolate at shot times
print("Interpolating GPS at shot times...")
fe_shots, fn_shots = interpolate_gps_at_times(front_t, front_e, front_n, shot_times, method="cubic")
te_shots, tn_shots = interpolate_gps_at_times(tail_t, tail_e, tail_n, shot_times, method="cubic")

# Vessel COG
print("Computing vessel COG from Head_Buoy trajectory...")
vessel_cog = compute_vessel_cog(fe_shots, fn_shots, window=5)

# Geometry (same as production)
rel_dx = (-1.2453) - 2.2547   # rx1 - source (RadExPro frame)
rel_dy = 69.7075 - 60.535
geom = MarineGeometry(
    source_dx=0, source_dy=0,
    rx1_dx=-rel_dx,   # PORT -> STBD
    rx1_dy=-rel_dy,   # AFT -> FWD
    n_channels=16,
    rx_interval=1.0,
    cable_depth=0.0,
    interp_method="feathering",
    feathering_alpha=2.0,
)

print(f"\nGeometry:")
print(f"  RX1 offset (STBD+/FWD+): dx={geom.rx1_dx:.4f}, dy={geom.rx1_dy:.4f}")
print(f"  Channels: {geom.n_channels}, Interval: {geom.rx_interval}m, Spread: {geom.total_spread}m")

# ========== Feathering angle analysis ==========
print("\n" + "=" * 80)
print("  FEATHERING ANGLE ANALYSIS")
print("=" * 80)

feathering_angles = np.zeros(n_shots)
cable_headings = np.zeros(n_shots)
for i in range(n_shots):
    cable_headings[i] = compute_heading(
        float(fe_shots[i]), float(fn_shots[i]),
        float(te_shots[i]), float(tn_shots[i]),
    )
    feathering_angles[i] = compute_feathering_angle(
        float(fe_shots[i]), float(fn_shots[i]),
        float(te_shots[i]), float(tn_shots[i]),
        float(vessel_cog[i]),
    )

print(f"  Vessel COG range: {vessel_cog.min():.1f} ~ {vessel_cog.max():.1f} deg")
print(f"  Cable heading (Head->Tail direction): {cable_headings.min():.1f} ~ {cable_headings.max():.1f} deg")
print(f"  Feathering angle (cable aft vs vessel aft):")
print(f"    Mean:   {np.mean(feathering_angles):+.2f} deg")
print(f"    Std:    {np.std(feathering_angles):.2f} deg")
print(f"    Min:    {np.min(feathering_angles):+.2f} deg")
print(f"    Max:    {np.max(feathering_angles):+.2f} deg")
print(f"    |Mean|: {np.mean(np.abs(feathering_angles)):.2f} deg")

# Cross-track magnitude
cross_totals = np.zeros(n_shots)
for i in range(n_shots):
    vh_rad = math.radians(vessel_cog[i])
    cross_e = math.cos(vh_rad)
    cross_n = -math.sin(vh_rad)
    dt_e = float(te_shots[i] - fe_shots[i])
    dt_n = float(tn_shots[i] - fn_shots[i])
    cross_totals[i] = dt_e * cross_e + dt_n * cross_n

print(f"\n  Cross-track displacement (tail vs head):")
print(f"    Mean: {np.mean(cross_totals):+.2f}m")
print(f"    Std:  {np.std(cross_totals):.2f}m")
print(f"    Min:  {np.min(cross_totals):+.2f}m")
print(f"    Max:  {np.max(cross_totals):+.2f}m")

# ========== Linear vs Feathering comparison ==========
print("\n" + "=" * 80)
print("  LINEAR vs FEATHERING MODEL COMPARISON (alpha=2.0)")
print("=" * 80)

per_channel_diffs = np.zeros((n_shots, geom.n_channels))

for i in range(n_shots):
    fe, fn = float(fe_shots[i]), float(fn_shots[i])
    te, tn = float(te_shots[i]), float(tn_shots[i])
    heading = cable_headings[i]

    rx_lin = interpolate_receivers_linear(fe, fn, heading, geom)
    rx_fea = interpolate_receivers_feathering(
        fe, fn, heading, geom,
        head_x=fe, head_y=fn, tail_x=te, tail_y=tn,
        vessel_heading_deg=float(vessel_cog[i]),
        feathering_alpha=2.0,
    )

    for j in range(geom.n_channels):
        dx = rx_fea[j].x - rx_lin[j].x
        dy = rx_fea[j].y - rx_lin[j].y
        per_channel_diffs[i, j] = math.sqrt(dx*dx + dy*dy)

mean_diffs = per_channel_diffs.mean(axis=0)
max_diffs = per_channel_diffs.max(axis=0)

print(f"\n  Position difference per channel (Linear -> Feathering correction):")
print(f"  {'Channel':>8s}  {'Mean(m)':>8s}  {'Max(m)':>8s}")
print(f"  {'-'*30}")
for ch in range(geom.n_channels):
    print(f"  {ch+1:>8d}  {mean_diffs[ch]:8.3f}  {max_diffs[ch]:8.3f}")

print(f"\n  Overall:")
print(f"    Mean all channels:  {per_channel_diffs.mean():.3f}m")
print(f"    Max all channels:   {per_channel_diffs.max():.3f}m")
print(f"    RX1 mean:           {mean_diffs[0]:.3f}m")
print(f"    RX16 mean:          {mean_diffs[-1]:.3f}m")
print(f"    RX1-RX16 gradient:  {abs(mean_diffs[-1] - mean_diffs[0]):.3f}m")

# ========== Alpha sensitivity ==========
print("\n" + "=" * 80)
print("  ALPHA SENSITIVITY ANALYSIS")
print("=" * 80)

alphas = [1.0, 1.5, 2.0, 2.5, 3.0]
for alpha in alphas:
    diffs = np.zeros(n_shots)
    for i in range(n_shots):
        fe, fn = float(fe_shots[i]), float(fn_shots[i])
        te, tn = float(te_shots[i]), float(tn_shots[i])
        heading = cable_headings[i]

        rx_lin = interpolate_receivers_linear(fe, fn, heading, geom)
        rx_fea = interpolate_receivers_feathering(
            fe, fn, heading, geom,
            head_x=fe, head_y=fn, tail_x=te, tail_y=tn,
            vessel_heading_deg=float(vessel_cog[i]),
            feathering_alpha=alpha,
        )

        shot_d = []
        for j in range(geom.n_channels):
            dx = rx_fea[j].x - rx_lin[j].x
            dy = rx_fea[j].y - rx_lin[j].y
            shot_d.append(math.sqrt(dx*dx + dy*dy))
        diffs[i] = np.mean(shot_d)

    note = " (=linear, zero correction)" if alpha == 1.0 else ""
    print(f"  alpha={alpha:.1f}: mean correction={diffs.mean():.3f}m, "
          f"max={diffs.max():.3f}m{note}")

# ========== Example shot ==========
print("\n" + "=" * 80)
print("  EXAMPLE SHOT (largest feathering)")
print("=" * 80)

max_idx = np.argmax(np.abs(cross_totals))
i = max_idx
fe, fn = float(fe_shots[i]), float(fn_shots[i])
te, tn = float(te_shots[i]), float(tn_shots[i])
heading = cable_headings[i]

print(f"\n  Shot #{i} (FFID: {track_data.df.iloc[i]['ffid']})")
print(f"  Head_Buoy: ({fe:.2f}, {fn:.2f})")
print(f"  Tail_Buoy: ({te:.2f}, {tn:.2f})")
print(f"  Cable heading: {heading:.1f} deg")
print(f"  Vessel COG: {vessel_cog[i]:.1f} deg")
print(f"  Feathering: {feathering_angles[i]:+.2f} deg")
print(f"  Cross-track total: {cross_totals[i]:+.2f}m")

chord = math.sqrt((te-fe)**2 + (tn-fn)**2)
print(f"  Cable chord: {chord:.1f}m")

rx_lin = interpolate_receivers_linear(fe, fn, heading, geom)
rx_f20 = interpolate_receivers_feathering(
    fe, fn, heading, geom,
    head_x=fe, head_y=fn, tail_x=te, tail_y=tn,
    vessel_heading_deg=float(vessel_cog[i]),
    feathering_alpha=2.0,
)

# Check t values for receivers
vh_rad = math.radians(vessel_cog[i])
cable_ux = (te - fe) / chord
cable_uy = (tn - fn) / chord

print(f"\n  {'CH':>4s}  {'t (frac)':>8s}  {'Lin E':>10s}  {'Lin N':>12s}  "
      f"{'Fea E':>10s}  {'Fea N':>12s}  {'Diff(m)':>8s}")
print(f"  {'-'*75}")
for j in range(geom.n_channels):
    lx, ly = rx_lin[j].x, rx_lin[j].y
    fx, fy = rx_f20[j].x, rx_f20[j].y
    d = math.sqrt((fx-lx)**2 + (fy-ly)**2)
    # Compute t
    dist = (lx - fe) * cable_ux + (ly - fn) * cable_uy
    t = dist / chord
    print(f"  {j+1:>4d}  {t:8.3f}  {lx:10.2f}  {ly:12.2f}  {fx:10.2f}  {fy:12.2f}  {d:8.3f}")

# ========== Summary ==========
print("\n" + "=" * 80)
print("  SUMMARY")
print("=" * 80)
print(f"""
  Feathering model analysis (correction-based, alpha=2.0):

  1. Feathering angle distribution:
     Mean |{np.mean(np.abs(feathering_angles)):.2f}| deg, Max |{np.max(np.abs(feathering_angles)):.2f}| deg
     Cross-track: mean {np.mean(np.abs(cross_totals)):.2f}m, max {np.max(np.abs(cross_totals)):.2f}m

  2. Linear vs Quadratic correction:
     Mean:    {per_channel_diffs.mean():.3f}m
     Max:     {per_channel_diffs.max():.3f}m
     RX1-RX16 gradient: {abs(mean_diffs[-1] - mean_diffs[0]):.3f}m

  3. Physics interpretation:
     - Correction = C_total * (t^2 - t) at each receiver
     - Moves receivers TOWARD the tow line (vessel heading axis)
     - Maximum correction at cable midpoint
     - Zero correction at head (t=0) and tail (t=1)

  4. Confidence:
     - Feathering angle: measured from GPS -> high (~1 deg)
     - Cable curvature (alpha): theoretical -> medium (1.5~2.5)
     - Per-channel position: interpolation -> GPS limited (~1m)
""")
