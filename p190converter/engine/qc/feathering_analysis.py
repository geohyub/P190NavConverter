# -*- coding: utf-8 -*-
"""Comprehensive feathering analysis — physics-based cable dynamics.

Computes all observable and derived variables affecting cable feathering:
  1. Feathering angle from GPS (direct measurement)
  2. Cross-track displacement (Head-Tail cross-track component)
  3. Vessel speed from GPS trajectory
  4. Estimated cross-current speed and direction
  5. Cable tension proxy from vessel speed and cable properties
  6. Per-channel position corrections (linear vs feathering model)
  7. Alpha sensitivity analysis
  8. Turn detection (vessel COG rate of change)
  9. Temporal pattern analysis (tidal/drift cycles)
  10. Cable shape quality metrics

Physical constants from GeoEel Solid LH-16 brochure:
  - Cable diameter: 44.5 mm (0.0445 m)
  - Cable weight: ~1.56 kg/m (156 kg / 100m section)
  - Tow cable: 18.5 mm dia, Kevlar, 0.5 kg/m
  - Material: Solid polyurethane (neutrally buoyant in seawater)

Hydrodynamic constants (smooth cylinder cross-flow):
  - Drag coefficient Cd: 1.0-1.2 (Re ~10^3-10^4 for typical speeds)
  - Seawater density: 1025 kg/m^3

Cross-current estimation:
  At steady state, the feathering angle satisfies:
    tan(theta) = V_cross / V_vessel  (first approximation)
  More precisely, considering cable drag:
    F_cross = 0.5 * rho * Cd * D * V_cross^2 * L  (total cross force)
    F_along = 0.5 * rho * Cd * D * V_vessel^2 * L  (total along force)
    tan(theta_tail) = F_cross / T_head  (at free end)

  Since we measure the actual cable endpoints, the cross-current estimate
  is derived from the feathering angle and vessel speed.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ══════════════════════════════════════════════════════════════
# Physical constants — GeoEel Solid LH-16
# ══════════════════════════════════════════════════════════════
CABLE_DIAMETER_M = 0.0445           # 44.5 mm
CABLE_WEIGHT_PER_M = 1.56          # ~1.56 kg/m (approx neutrally buoyant)
TOW_CABLE_DIAMETER_M = 0.0185      # 18.5 mm Kevlar tow cable
TOW_CABLE_WEIGHT_PER_M = 0.5       # 0.5 kg/m
SEAWATER_DENSITY = 1025.0          # kg/m^3
DRAG_COEFF_CYLINDER = 1.1          # Cd for smooth cylinder (Re~10^3-10^4)
GRAVITY = 9.81                     # m/s^2


@dataclass
class FeatheringAnalysisResult:
    """Complete feathering analysis result for one survey line."""

    # ── Dimensions ──
    n_shots: int = 0
    n_channels: int = 0
    rx_interval: float = 1.0
    total_spread: float = 15.0

    # ── Per-shot arrays (length = n_shots) ──
    shot_indices: np.ndarray = field(default_factory=lambda: np.array([]))
    ffids: np.ndarray = field(default_factory=lambda: np.array([]))
    shot_times: np.ndarray = field(default_factory=lambda: np.array([]))

    # GPS positions per shot
    head_east: np.ndarray = field(default_factory=lambda: np.array([]))
    head_north: np.ndarray = field(default_factory=lambda: np.array([]))
    tail_east: np.ndarray = field(default_factory=lambda: np.array([]))
    tail_north: np.ndarray = field(default_factory=lambda: np.array([]))

    # Vessel dynamics
    vessel_cog: np.ndarray = field(default_factory=lambda: np.array([]))       # degrees
    vessel_speed: np.ndarray = field(default_factory=lambda: np.array([]))     # m/s
    vessel_speed_knots: np.ndarray = field(default_factory=lambda: np.array([]))
    cog_rate: np.ndarray = field(default_factory=lambda: np.array([]))         # deg/s

    # Cable geometry
    cable_heading: np.ndarray = field(default_factory=lambda: np.array([]))    # degrees
    cable_chord: np.ndarray = field(default_factory=lambda: np.array([]))      # meters
    feathering_angle: np.ndarray = field(default_factory=lambda: np.array([])) # degrees

    # Cross-track
    cross_track_disp: np.ndarray = field(default_factory=lambda: np.array([])) # meters
    along_track_disp: np.ndarray = field(default_factory=lambda: np.array([])) # meters

    # Estimated current
    current_speed: np.ndarray = field(default_factory=lambda: np.array([]))    # m/s
    current_direction: np.ndarray = field(default_factory=lambda: np.array([])) # degrees (from North)

    # Cable tension proxy
    tow_tension_estimate: np.ndarray = field(default_factory=lambda: np.array([]))  # Newtons

    # Turn detection
    is_turning: np.ndarray = field(default_factory=lambda: np.array([], dtype=bool))
    turn_threshold_deg_per_s: float = 2.0

    # ── Per-channel correction (n_channels array) ──
    channel_correction_mean: np.ndarray = field(default_factory=lambda: np.array([]))
    channel_correction_max: np.ndarray = field(default_factory=lambda: np.array([]))

    # ── Alpha sensitivity (dict: alpha -> mean_correction) ──
    alpha_sensitivity: Dict[float, float] = field(default_factory=dict)

    # ── Summary statistics ──
    stats: Dict[str, float] = field(default_factory=dict)


def compute_vessel_speed(
    east: np.ndarray,
    north: np.ndarray,
    times: np.ndarray,
    window: int = 3,
) -> np.ndarray:
    """Compute vessel speed from GPS position time series.

    Uses central difference with look-ahead/back window for stability.

    Args:
        east, north: Position arrays (meters)
        times: Time in seconds
        window: Smoothing window (shots)

    Returns:
        Speed array in m/s
    """
    n = len(east)
    speed = np.zeros(n)

    for i in range(n):
        j_back = max(0, i - window)
        j_fwd = min(n - 1, i + window)

        dx = float(east[j_fwd] - east[j_back])
        dy = float(north[j_fwd] - north[j_back])
        dt = float(times[j_fwd] - times[j_back])

        if dt > 0.01:
            dist = math.sqrt(dx * dx + dy * dy)
            speed[i] = dist / dt
        elif i > 0:
            speed[i] = speed[i - 1]

    return speed


def compute_cog_rate(
    cog: np.ndarray,
    times: np.ndarray,
    window: int = 3,
) -> np.ndarray:
    """Compute rate of change of COG (degrees per second).

    Used for turn detection. Large values indicate vessel is turning.
    """
    n = len(cog)
    rate = np.zeros(n)

    for i in range(n):
        j_back = max(0, i - window)
        j_fwd = min(n - 1, i + window)

        # Circular difference
        dcog = (cog[j_fwd] - cog[j_back] + 180) % 360 - 180
        dt = float(times[j_fwd] - times[j_back])

        if dt > 0.01:
            rate[i] = abs(dcog / dt)
        elif i > 0:
            rate[i] = rate[i - 1]

    return rate


def estimate_cross_current(
    feathering_deg: np.ndarray,
    vessel_speed: np.ndarray,
    vessel_cog: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Estimate cross-current speed and direction from feathering.

    Physics:
      tan(theta_feathering) ≈ V_cross / V_vessel (first-order)

    The current direction is perpendicular to vessel heading,
    in the direction of cable drift (sign of feathering angle).

    Positive feathering = cable drifts to starboard
      → current comes from port side → current direction = vessel_cog - 90
    Negative feathering = cable drifts to port
      → current comes from starboard → current direction = vessel_cog + 90

    Args:
        feathering_deg: Feathering angle (degrees, +starboard)
        vessel_speed: Vessel speed (m/s)
        vessel_cog: Vessel COG (degrees CW from North)

    Returns:
        (current_speed, current_direction)
        current_speed in m/s
        current_direction in degrees CW from North (direction current flows TO)
    """
    n = len(feathering_deg)
    current_speed = np.zeros(n)
    current_dir = np.zeros(n)

    for i in range(n):
        theta = math.radians(feathering_deg[i])
        v = vessel_speed[i]

        # Current speed from first-order approximation
        # Limit to reasonable range (avoid tan blow-up near ±90°)
        if abs(feathering_deg[i]) < 80.0 and v > 0.1:
            current_speed[i] = abs(v * math.tan(theta))
        else:
            current_speed[i] = 0.0

        # Current flows in the direction the cable drifts
        # Positive feathering (starboard drift): current from port
        if feathering_deg[i] > 0:
            # Current pushes cable to starboard
            # Current flows FROM port → TO starboard
            current_dir[i] = (vessel_cog[i] + 90) % 360
        else:
            # Current pushes cable to port
            current_dir[i] = (vessel_cog[i] - 90) % 360

    return current_speed, current_dir


def estimate_tow_tension(
    vessel_speed: np.ndarray,
    cable_length,
    cable_diameter: float = CABLE_DIAMETER_M,
    cd: float = DRAG_COEFF_CYLINDER,
    rho: float = SEAWATER_DENSITY,
) -> np.ndarray:
    """Estimate cable tow tension from vessel speed.

    Simplified model: tow tension equals total drag force on cable
    (neglecting cable weight for neutrally-buoyant cable):

      T_tow = 0.5 * rho * Cd * D * V^2 * L

    cable_length can be a scalar (fixed) or per-shot array (cable_chord).
    Using actual cable chord (Head→Tail distance) gives more realistic results
    than just the receiver spread length.

    Args:
        vessel_speed: Vessel speed (m/s)
        cable_length: Cable length (m) — scalar or per-shot array (e.g. cable_chord)
        cable_diameter: Cable outer diameter (m)
        cd: Drag coefficient
        rho: Water density (kg/m^3)

    Returns:
        Tension estimate in Newtons (per-shot array)
    """
    # F_drag = 0.5 * rho * Cd * D * V^2 * L
    tension = 0.5 * rho * cd * cable_diameter * vessel_speed**2 * cable_length
    return tension


def run_feathering_analysis(
    head_east: np.ndarray,
    head_north: np.ndarray,
    tail_east: np.ndarray,
    tail_north: np.ndarray,
    vessel_cog: np.ndarray,
    shot_times: np.ndarray,
    ffids: np.ndarray,
    n_channels: int = 16,
    rx_interval: float = 1.0,
    feathering_alpha: float = 2.0,
    turn_threshold: float = 2.0,
) -> FeatheringAnalysisResult:
    """Run comprehensive feathering analysis.

    Args:
        head_east/north: Head buoy positions per shot (meters)
        tail_east/north: Tail buoy positions per shot
        vessel_cog: Vessel COG per shot (degrees CW from North)
        shot_times: Shot times in seconds
        ffids: FFID array
        n_channels: Number of receiver channels
        rx_interval: Channel spacing (meters)
        feathering_alpha: Power-law exponent for correction model
        turn_threshold: COG rate threshold for turn detection (deg/s)

    Returns:
        FeatheringAnalysisResult with all computed variables
    """
    n = len(head_east)
    total_spread = rx_interval * (n_channels - 1)

    result = FeatheringAnalysisResult(
        n_shots=n,
        n_channels=n_channels,
        rx_interval=rx_interval,
        total_spread=total_spread,
        shot_indices=np.arange(n),
        ffids=ffids.copy(),
        shot_times=shot_times.copy(),
        head_east=head_east.copy(),
        head_north=head_north.copy(),
        tail_east=tail_east.copy(),
        tail_north=tail_north.copy(),
        vessel_cog=vessel_cog.copy(),
        turn_threshold_deg_per_s=turn_threshold,
    )

    # ── 1. Cable geometry ──
    dt_e = tail_east - head_east
    dt_n = tail_north - head_north
    result.cable_chord = np.sqrt(dt_e**2 + dt_n**2)

    # Cable heading (Head → Tail = aft direction)
    result.cable_heading = np.array([
        math.degrees(math.atan2(float(dt_e[i]), float(dt_n[i]))) % 360
        for i in range(n)
    ])

    # ── 2. Feathering angle (cable aft vs vessel aft) ──
    vessel_aft = (vessel_cog + 180) % 360
    result.feathering_angle = np.array([
        (result.cable_heading[i] - vessel_aft[i] + 180) % 360 - 180
        for i in range(n)
    ])

    # ── 3. Cross-track and along-track decomposition ──
    result.cross_track_disp = np.zeros(n)
    result.along_track_disp = np.zeros(n)

    for i in range(n):
        vh_rad = math.radians(vessel_cog[i])
        # Cross-tow direction (+ starboard)
        cross_e = math.cos(vh_rad)
        cross_n = -math.sin(vh_rad)
        # Along-tow direction (+ forward = vessel heading)
        along_e = math.sin(vh_rad)
        along_n = math.cos(vh_rad)

        result.cross_track_disp[i] = dt_e[i] * cross_e + dt_n[i] * cross_n
        result.along_track_disp[i] = dt_e[i] * along_e + dt_n[i] * along_n

    # ── 4. Vessel speed ──
    result.vessel_speed = compute_vessel_speed(
        head_east, head_north, shot_times, window=5
    )
    result.vessel_speed_knots = result.vessel_speed * 1.94384  # m/s to knots

    # ── 5. COG rate of change (turn detection) ──
    result.cog_rate = compute_cog_rate(vessel_cog, shot_times, window=3)
    result.is_turning = result.cog_rate > turn_threshold

    # ── 6. Cross-current estimation ──
    result.current_speed, result.current_direction = estimate_cross_current(
        result.feathering_angle, result.vessel_speed, vessel_cog
    )

    # ── 7. Tow tension estimate ──
    # Use actual cable chord (Head→Tail distance) rather than just receiver spread.
    # Cable chord includes tow cable + active sections, giving realistic tension.
    result.tow_tension_estimate = estimate_tow_tension(
        result.vessel_speed,
        cable_length=result.cable_chord,  # per-shot chord distance
        cable_diameter=CABLE_DIAMETER_M,
    )

    # ── 8. Per-channel correction analysis ──
    _compute_channel_corrections(result, feathering_alpha)

    # ── 9. Alpha sensitivity ──
    _compute_alpha_sensitivity(result)

    # ── 10. Summary statistics ──
    _compute_summary_stats(result)

    return result


def _compute_channel_corrections(
    result: FeatheringAnalysisResult,
    alpha: float,
):
    """Compute per-channel position corrections (linear → feathering)."""
    n = result.n_shots
    n_ch = result.n_channels

    # For each shot, compute the correction magnitude at each channel
    per_channel = np.zeros((n, n_ch))

    for i in range(n):
        chord = result.cable_chord[i]
        if chord < 0.1:
            continue

        cross_total = result.cross_track_disp[i]
        if abs(cross_total) < 0.1:
            continue

        # Approximate t values for each channel
        # Receivers start near head buoy and extend along cable
        # t ≈ (receiver distance from head) / cable_chord
        for ch in range(n_ch):
            # Rough estimate: rx_interval * ch / cable_chord
            dist_from_head = result.rx_interval * ch  # simplified
            t = dist_from_head / chord
            t = max(0.0, min(1.5, t))

            # Correction magnitude
            delta = abs(cross_total * (t ** alpha - t))
            per_channel[i, ch] = delta

    result.channel_correction_mean = per_channel.mean(axis=0)
    result.channel_correction_max = per_channel.max(axis=0)


def _compute_alpha_sensitivity(result: FeatheringAnalysisResult):
    """Compute mean correction for different alpha values."""
    alphas = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

    for alpha in alphas:
        corrections = []
        for i in range(result.n_shots):
            chord = result.cable_chord[i]
            if chord < 0.1:
                corrections.append(0.0)
                continue

            cross_total = result.cross_track_disp[i]
            if abs(cross_total) < 0.1:
                corrections.append(0.0)
                continue

            shot_corr = []
            for ch in range(result.n_channels):
                dist = result.rx_interval * ch
                t = dist / chord
                t = max(0.0, min(1.5, t))
                delta = abs(cross_total * (t ** alpha - t))
                shot_corr.append(delta)

            corrections.append(np.mean(shot_corr))

        result.alpha_sensitivity[alpha] = float(np.mean(corrections))


def _compute_summary_stats(result: FeatheringAnalysisResult):
    """Compute summary statistics dictionary."""
    # Mask out turns for clean statistics
    clean = ~result.is_turning
    n_clean = clean.sum()
    n_turning = result.is_turning.sum()

    if n_clean > 0:
        fa_clean = result.feathering_angle[clean]
        ct_clean = result.cross_track_disp[clean]
        vs_clean = result.vessel_speed_knots[clean]
        cs_clean = result.current_speed[clean]
        tt_clean = result.tow_tension_estimate[clean]
    else:
        fa_clean = result.feathering_angle
        ct_clean = result.cross_track_disp
        vs_clean = result.vessel_speed_knots
        cs_clean = result.current_speed
        tt_clean = result.tow_tension_estimate

    result.stats = {
        # Counts
        "n_shots_total": result.n_shots,
        "n_shots_clean": int(n_clean),
        "n_shots_turning": int(n_turning),
        "turn_pct": float(n_turning / result.n_shots * 100) if result.n_shots > 0 else 0,

        # Feathering angle (clean shots only)
        "feathering_mean": float(np.mean(fa_clean)),
        "feathering_abs_mean": float(np.mean(np.abs(fa_clean))),
        "feathering_std": float(np.std(fa_clean)),
        "feathering_min": float(np.min(fa_clean)),
        "feathering_max": float(np.max(fa_clean)),

        # Cross-track displacement
        "cross_track_mean": float(np.mean(ct_clean)),
        "cross_track_abs_mean": float(np.mean(np.abs(ct_clean))),
        "cross_track_std": float(np.std(ct_clean)),
        "cross_track_min": float(np.min(ct_clean)),
        "cross_track_max": float(np.max(ct_clean)),

        # Vessel speed
        "vessel_speed_mean_knots": float(np.mean(vs_clean)),
        "vessel_speed_std_knots": float(np.std(vs_clean)),
        "vessel_speed_min_knots": float(np.min(vs_clean)),
        "vessel_speed_max_knots": float(np.max(vs_clean)),

        # Estimated cross-current
        "current_speed_mean": float(np.mean(cs_clean)),
        "current_speed_max": float(np.max(cs_clean)),
        "current_speed_mean_knots": float(np.mean(cs_clean) * 1.94384),

        # Tow tension
        "tension_mean_N": float(np.mean(tt_clean)),
        "tension_max_N": float(np.max(tt_clean)),

        # Cable geometry
        "cable_chord_mean": float(np.mean(result.cable_chord)),
        "cable_chord_std": float(np.std(result.cable_chord)),

        # Per-channel correction (alpha=2.0)
        "correction_mean_all": float(result.channel_correction_mean.mean()),
        "correction_max_all": float(result.channel_correction_max.max()),
        "correction_rx1_mean": float(result.channel_correction_mean[0])
            if len(result.channel_correction_mean) > 0 else 0.0,
        "correction_rxN_mean": float(result.channel_correction_mean[-1])
            if len(result.channel_correction_mean) > 0 else 0.0,

        # Physical constants used
        "cable_diameter_mm": CABLE_DIAMETER_M * 1000,
        "cable_cd": DRAG_COEFF_CYLINDER,
        "water_density": SEAWATER_DENSITY,
    }


def generate_feathering_report(result: FeatheringAnalysisResult) -> str:
    """Generate comprehensive feathering analysis text report."""
    s = result.stats
    lines = []

    lines.append("=" * 72)
    lines.append("  FEATHERING ANALYSIS REPORT")
    lines.append("  Cable Model: GeoEel Solid LH-16 (D=44.5mm, polyurethane)")
    lines.append("=" * 72)

    # ── Section 1: Survey Overview ──
    lines.append("\n  1. SURVEY OVERVIEW")
    lines.append("  " + "-" * 40)
    lines.append(f"     Total shots:      {s['n_shots_total']:,}")
    lines.append(f"     Clean shots:      {s['n_shots_clean']:,}")
    lines.append(f"     Turning shots:    {s['n_shots_turning']:,} ({s['turn_pct']:.1f}%)")
    lines.append(f"     Channels:         {result.n_channels}")
    lines.append(f"     Group interval:   {result.rx_interval:.3f} m")
    lines.append(f"     Total spread:     {result.total_spread:.1f} m")

    # ── Section 2: Vessel Dynamics ──
    lines.append("\n  2. VESSEL DYNAMICS")
    lines.append("  " + "-" * 40)
    lines.append(f"     Speed (mean):     {s['vessel_speed_mean_knots']:.2f} knots")
    lines.append(f"     Speed (range):    {s['vessel_speed_min_knots']:.2f} ~ "
                 f"{s['vessel_speed_max_knots']:.2f} knots")
    lines.append(f"     Speed (std):      {s['vessel_speed_std_knots']:.2f} knots")

    # ── Section 3: Feathering Angle ──
    lines.append("\n  3. FEATHERING ANGLE (clean shots, excl. turns)")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean:             {s['feathering_mean']:+.2f} deg")
    lines.append(f"     |Mean|:           {s['feathering_abs_mean']:.2f} deg")
    lines.append(f"     Std:              {s['feathering_std']:.2f} deg")
    lines.append(f"     Min:              {s['feathering_min']:+.2f} deg")
    lines.append(f"     Max:              {s['feathering_max']:+.2f} deg")

    # Interpretation
    abs_mean = s['feathering_abs_mean']
    if abs_mean < 5:
        assessment = "MINIMAL - 직선에 가까움, 보정 효과 작음"
    elif abs_mean < 15:
        assessment = "MODERATE - 일반적 수준, 보정 필요"
    elif abs_mean < 30:
        assessment = "SIGNIFICANT - 강한 조류, 보정 효과 큼"
    else:
        assessment = "SEVERE - 매우 강한 조류 또는 데이터 점검 필요"
    lines.append(f"     Assessment:       {assessment}")

    # ── Section 4: Cross-track Displacement ──
    lines.append("\n  4. CROSS-TRACK DISPLACEMENT (Tail vs Head)")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean:             {s['cross_track_mean']:+.2f} m")
    lines.append(f"     |Mean|:           {s['cross_track_abs_mean']:.2f} m")
    lines.append(f"     Min:              {s['cross_track_min']:+.2f} m")
    lines.append(f"     Max:              {s['cross_track_max']:+.2f} m")
    lines.append(f"     Std:              {s['cross_track_std']:.2f} m")

    drift_dir = "STARBOARD" if s['cross_track_mean'] > 0 else "PORT"
    lines.append(f"     Dominant drift:   {drift_dir}")

    # ── Section 5: Estimated Cross-Current ──
    lines.append("\n  5. ESTIMATED CROSS-CURRENT")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean speed:       {s['current_speed_mean']:.3f} m/s "
                 f"({s['current_speed_mean_knots']:.2f} knots)")
    lines.append(f"     Max speed:        {s['current_speed_max']:.3f} m/s")
    lines.append("     Note: First-order approximation from tan(feathering)")
    lines.append("           Actual current may differ due to cable dynamics")

    # ── Section 6: Cable Tension ──
    lines.append("\n  6. TOW TENSION ESTIMATE")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean tension:     {s['tension_mean_N']:.1f} N "
                 f"({s['tension_mean_N']/GRAVITY:.2f} kgf)")
    lines.append(f"     Max tension:      {s['tension_max_N']:.1f} N "
                 f"({s['tension_max_N']/GRAVITY:.2f} kgf)")
    lines.append(f"     Cable diameter:   {s['cable_diameter_mm']:.1f} mm")
    lines.append(f"     Drag coeff (Cd):  {s['cable_cd']:.1f}")
    lines.append("     Note: Simplified drag model F = 0.5*rho*Cd*D*V^2*L")
    lines.append("           Low tension confirms UHR cables are")
    lines.append("           susceptible to cross-current displacement")

    # ── Section 7: Per-Channel Correction ──
    lines.append("\n  7. PER-CHANNEL POSITION CORRECTION (alpha=2.0)")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean (all ch):    {s['correction_mean_all']:.3f} m")
    lines.append(f"     Max  (all ch):    {s['correction_max_all']:.3f} m")
    lines.append(f"     RX1  (mean):      {s['correction_rx1_mean']:.3f} m")
    lines.append(f"     RX{result.n_channels}  (mean):      "
                 f"{s['correction_rxN_mean']:.3f} m")

    lines.append(f"\n     {'CH':>6s}  {'Mean(m)':>8s}  {'Max(m)':>8s}")
    lines.append(f"     {'-'*28}")
    for ch in range(result.n_channels):
        lines.append(
            f"     {ch+1:>6d}  "
            f"{result.channel_correction_mean[ch]:8.3f}  "
            f"{result.channel_correction_max[ch]:8.3f}"
        )

    # ── Section 8: Alpha Sensitivity ──
    lines.append("\n  8. ALPHA SENSITIVITY")
    lines.append("  " + "-" * 40)
    lines.append(f"     {'alpha':>8s}  {'Mean Correction(m)':>18s}  {'Note':>20s}")
    lines.append(f"     {'-'*50}")
    for alpha, corr in sorted(result.alpha_sensitivity.items()):
        note = ""
        if alpha == 1.0:
            note = "(=linear, no correction)"
        elif alpha == 2.0:
            note = "(quadratic, default)"
        lines.append(f"     {alpha:8.1f}  {corr:18.3f}  {note}")

    # ── Section 9: Physical Variables Summary ──
    lines.append("\n  9. PHYSICAL VARIABLES AFFECTING FEATHERING")
    lines.append("  " + "-" * 40)
    lines.append("     Variable                  Measured/Estimated  Impact")
    lines.append("     " + "-" * 60)
    lines.append(f"     Cross-current             {s['current_speed_mean']:.3f} m/s"
                 f"             PRIMARY")
    lines.append(f"     Vessel speed              {s['vessel_speed_mean_knots']:.2f} knots"
                 f"             HIGH")
    lines.append(f"     Tow tension               {s['tension_mean_N']:.1f} N"
                 f"                HIGH")
    lines.append(f"     Cable diameter             {s['cable_diameter_mm']:.1f} mm"
                 f"              MEDIUM")
    lines.append(f"     Cable spread               {result.total_spread:.1f} m"
                 f"              MEDIUM")
    lines.append(f"     Feathering angle          {s['feathering_abs_mean']:.1f} deg"
                 f"              RESULT")
    lines.append("     Cable weight              ~neutrally buoyant     LOW")
    lines.append("     Water depth               not measured           INDIRECT")
    lines.append("     Tidal cycle               see time series        VARIABLE")

    # ── Section 10: Cable chord ──
    lines.append(f"\n  10. CABLE CHORD (Head-Tail distance)")
    lines.append("  " + "-" * 40)
    lines.append(f"     Mean:             {s['cable_chord_mean']:.1f} m")
    lines.append(f"     Std:              {s['cable_chord_std']:.2f} m")
    nominal = result.total_spread
    stretch = s['cable_chord_mean'] - nominal
    lines.append(f"     Nominal spread:   {nominal:.1f} m")
    lines.append(f"     Mean stretch:     {stretch:+.1f} m")

    lines.append("\n" + "=" * 72)

    return "\n".join(lines)
