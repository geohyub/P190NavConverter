"""Receiver position interpolation — Linear, Catenary, Spline, Feathering.

Heading-based rotation is always applied to convert vessel-relative offsets
to absolute map coordinates.

Linear Interpolation:
  - RadExPro standard method (pp.915-918)
  - Receivers equally spaced along cable direction
  - Suitable for 48ch UHR (~150m), error < 2m

Catenary Model:
  - Physics-based cable shape: T(s) = sqrt(W^2 + Bow_Pull^2)
  - For deep water / long streamers (>5km)

Spline:
  - Cubic spline through known positions
  - For irregular distributions / 3D regularization

Feathering Model:
  - Physics-based cross-current cable displacement
  - Uses Head_Buoy + Tail_Buoy GPS to determine actual cable path
  - Cross-track displacement: y(t) = y_total * t^alpha (alpha=2 for quadratic)
  - Near head (tow point): cable follows vessel heading (constrained)
  - Near tail (free end): maximum current-induced drift
  - Produces more realistic channel positions than straight-line methods
"""

import math
from typing import List, Optional, Tuple

import numpy as np

from ...models.shot_gather import ReceiverPosition, ShotGather
from ...models.survey_config import MarineGeometry
from .marine_geometry import OffsetDefinition


def compute_heading(
    front_x: float, front_y: float,
    tail_x: float, tail_y: float,
) -> float:
    """Compute ship heading from front/tail GPS positions.

    Args:
        front_x, front_y: Front GPS (Easting, Northing)
        tail_x, tail_y: Tail GPS (Easting, Northing)

    Returns:
        Heading in degrees (CW from North, 0-360)
    """
    dx = front_x - tail_x
    dy = front_y - tail_y
    heading = math.degrees(math.atan2(dx, dy)) % 360
    return heading


def interpolate_receivers_linear(
    source_x: float,
    source_y: float,
    heading_deg: float,
    geometry: MarineGeometry,
) -> List[ReceiverPosition]:
    """Interpolate receiver positions using linear method.

    Receivers are equally spaced along cable direction, starting from
    RX1 offset, extending in the along-track direction away from source.

    The RX1 offset and cable direction are rotated by ship heading.

    Args:
        source_x, source_y: Source position (Easting, Northing)
        heading_deg: Ship heading in degrees (CW from North)
        geometry: Marine geometry parameters

    Returns:
        List of ReceiverPosition objects
    """
    heading_rad = math.radians(heading_deg)

    # RX1 offset in vessel coordinates
    rx1_offset = OffsetDefinition(geometry.rx1_dx, geometry.rx1_dy)
    rx1_de, rx1_dn = rx1_offset.rotate(heading_rad)

    # RX1 absolute position
    rx1_x = source_x + rx1_de
    rx1_y = source_y + rx1_dn

    # Cable direction: along-track from source through receivers
    # Receivers extend aft (negative along-track) from RX1
    # Unit vector in cable direction (aft = -dy direction)
    cable_dx = -math.sin(heading_rad)  # aft direction easting
    cable_dy = -math.cos(heading_rad)  # aft direction northing

    receivers = []
    for i in range(geometry.n_channels):
        ch = i + 1
        # Distance from RX1 along cable
        dist = geometry.rx_interval * i
        rx_x = rx1_x + cable_dx * dist
        rx_y = rx1_y + cable_dy * dist

        receivers.append(ReceiverPosition(
            channel=ch,
            x=rx_x,
            y=rx_y,
            depth=geometry.cable_depth,
        ))

    return receivers


def interpolate_receivers_catenary(
    source_x: float,
    source_y: float,
    heading_deg: float,
    geometry: MarineGeometry,
    bow_pull: float = 50.0,
    cable_weight: float = 0.5,
) -> List[ReceiverPosition]:
    """Interpolate receivers using catenary cable model.

    Physics model: cable hangs under its own weight with bow-pull tension.
    y(x) = (T/W) * cosh(W*x/T) - T/W

    For 48ch UHR, the difference from linear is typically < 0.5m.

    Args:
        source_x, source_y: Source position
        heading_deg: Ship heading
        geometry: Marine geometry parameters
        bow_pull: Horizontal tension at tow point (N)
        cable_weight: Weight per unit length (N/m)

    Returns:
        List of ReceiverPosition objects
    """
    heading_rad = math.radians(heading_deg)

    # RX1 offset
    rx1_offset = OffsetDefinition(geometry.rx1_dx, geometry.rx1_dy)
    rx1_de, rx1_dn = rx1_offset.rotate(heading_rad)
    rx1_x = source_x + rx1_de
    rx1_y = source_y + rx1_dn

    # Cable direction (aft)
    cable_dx = -math.sin(heading_rad)
    cable_dy = -math.cos(heading_rad)

    # Catenary parameters
    T = math.sqrt(cable_weight**2 + bow_pull**2)
    ratio = T / cable_weight if cable_weight > 0 else 1e6

    receivers = []
    for i in range(geometry.n_channels):
        ch = i + 1
        dist_along = geometry.rx_interval * i

        # Catenary cross-track displacement
        if cable_weight > 0 and bow_pull > 0:
            x_cat = dist_along
            cross_disp = ratio * (math.cosh(cable_weight * x_cat / T) - 1)
        else:
            cross_disp = 0.0

        # Apply along-track + cross-track
        rx_x = rx1_x + cable_dx * dist_along + math.cos(heading_rad) * cross_disp
        rx_y = rx1_y + cable_dy * dist_along - math.sin(heading_rad) * cross_disp

        # Depth varies along catenary
        depth = geometry.cable_depth + cross_disp * 0.01  # Simplified

        receivers.append(ReceiverPosition(
            channel=ch, x=rx_x, y=rx_y, depth=depth,
        ))

    return receivers


def interpolate_receivers_spline(
    source_x: float,
    source_y: float,
    heading_deg: float,
    geometry: MarineGeometry,
    known_positions: Optional[List[Tuple[float, float]]] = None,
) -> List[ReceiverPosition]:
    """Interpolate receivers using cubic spline.

    If known_positions are provided (e.g., from partial GPS data),
    spline interpolation is fitted through them. Otherwise, falls back
    to linear with spline smoothing for cable shape.

    Args:
        source_x, source_y: Source position
        heading_deg: Ship heading
        geometry: Marine geometry parameters
        known_positions: Optional list of (x, y) known receiver positions

    Returns:
        List of ReceiverPosition objects
    """
    if known_positions and len(known_positions) >= 3:
        from scipy.interpolate import CubicSpline

        # Use known positions as control points
        known = np.array(known_positions)
        t_known = np.linspace(0, 1, len(known))
        t_interp = np.linspace(0, 1, geometry.n_channels)

        cs_x = CubicSpline(t_known, known[:, 0])
        cs_y = CubicSpline(t_known, known[:, 1])

        receivers = []
        for i in range(geometry.n_channels):
            ch = i + 1
            rx_x = float(cs_x(t_interp[i]))
            rx_y = float(cs_y(t_interp[i]))
            receivers.append(ReceiverPosition(
                channel=ch, x=rx_x, y=rx_y,
                depth=geometry.cable_depth,
            ))
        return receivers

    # Fallback: linear interpolation
    return interpolate_receivers_linear(
        source_x, source_y, heading_deg, geometry,
    )


def interpolate_receivers_feathering(
    source_x: float,
    source_y: float,
    cable_heading_deg: float,
    geometry: MarineGeometry,
    head_x: float,
    head_y: float,
    tail_x: float,
    tail_y: float,
    vessel_heading_deg: Optional[float] = None,
    feathering_alpha: float = 2.0,
) -> List[ReceiverPosition]:
    """Feathering-aware receiver interpolation — correction-based approach.

    Starts with standard linear interpolation (receivers on a straight line
    along cable heading), then applies a cross-track correction to account
    for cable curvature caused by cross-currents.

    Physics model:
      The cable trails aft from the vessel. Cross-current displaces the cable
      perpendicular to the tow direction. Near the tow point (head buoy),
      the cable is constrained by tension; near the free end (tail buoy),
      it drifts maximally.

      Linear (straight-line):  cross(t) = C_total * t
      Quadratic (corrected):   cross(t) = C_total * t^alpha

      The CORRECTION applied to linear positions:
        delta_cross(t) = C_total * (t^alpha - t)

      This is 0 at t=0 (head) and t=1 (tail), and negative in between,
      moving receivers TOWARD the tow line (vessel heading axis).

      At t=0.5 with alpha=2: delta = C * (0.25 - 0.5) = -0.25 * C_total
      For C_total=10m: midpoint correction = 2.5m toward tow line.

    When vessel_heading_deg is not provided, falls back to linear interpolation.

    Args:
        source_x, source_y: Source position (Easting, Northing)
        cable_heading_deg: Cable heading from Head→Tail (degrees CW from North).
                           Note: compute_heading() returns direction from Tail
                           toward Head (=forward), so cable extends in the
                           opposite direction.
        geometry: Marine geometry with receiver offsets
        head_x, head_y: Head_Buoy GPS position
        tail_x, tail_y: Tail_Buoy GPS position
        vessel_heading_deg: Ship heading/COG (tow direction). Required to
                            compute cross-track feathering direction.
        feathering_alpha: Power-law exponent. 2.0=quadratic (default),
                          1.0=no correction, 3.0=cubic.

    Returns:
        List of ReceiverPosition for all channels
    """
    # ── No vessel heading → standard linear ──
    if vessel_heading_deg is None:
        return interpolate_receivers_linear(
            source_x, source_y, cable_heading_deg, geometry
        )

    # ── Step 1: Start with linear interpolation ──
    rx_linear = interpolate_receivers_linear(
        source_x, source_y, cable_heading_deg, geometry
    )

    # ── Step 2: Cable geometry ──
    dt_e = tail_x - head_x
    dt_n = tail_y - head_y
    cable_chord = math.sqrt(dt_e * dt_e + dt_n * dt_n)

    if cable_chord < 0.1:
        return rx_linear

    # Cable unit vector (Head → Tail, i.e. aft direction)
    cable_ux = dt_e / cable_chord
    cable_uy = dt_n / cable_chord

    # ── Step 3: Tow frame for cross-track direction ──
    vh_rad = math.radians(vessel_heading_deg)
    # Cross-tow direction (+ = starboard of vessel heading)
    cross_e = math.cos(vh_rad)
    cross_n = -math.sin(vh_rad)

    # Cross-track displacement of tail relative to head
    cross_total = dt_e * cross_e + dt_n * cross_n

    # If feathering is negligible (<0.1m cross-track), no correction needed
    if abs(cross_total) < 0.1:
        return rx_linear

    # ── Step 4: Apply correction to each receiver ──
    receivers = []

    for i in range(geometry.n_channels):
        ch = i + 1

        # Project receiver position onto cable axis (distance from head)
        rx_from_head_e = rx_linear[i].x - head_x
        rx_from_head_n = rx_linear[i].y - head_y
        dist_along_cable = rx_from_head_e * cable_ux + rx_from_head_n * cable_uy

        # Fractional position on cable [0=head, 1=tail]
        t = dist_along_cable / cable_chord
        t = max(0.0, min(1.5, t))  # allow slight extrapolation

        # Cross-track correction:
        #   Linear model:     cross = C_total * t
        #   Power-law model:  cross = C_total * t^alpha
        #   Correction:       delta = C_total * (t^alpha - t)
        delta_cross = cross_total * (t ** feathering_alpha - t)

        # Apply correction in cross-tow direction
        rx_x = rx_linear[i].x + delta_cross * cross_e
        rx_y = rx_linear[i].y + delta_cross * cross_n

        receivers.append(ReceiverPosition(
            channel=ch,
            x=rx_x,
            y=rx_y,
            depth=geometry.cable_depth,
        ))

    return receivers


def compute_feathering_angle(
    head_x: float, head_y: float,
    tail_x: float, tail_y: float,
    vessel_heading_deg: float,
) -> float:
    """Compute feathering angle from cable endpoints and vessel heading.

    Feathering = angle between cable's aft direction and vessel's aft direction.
    The cable extends from Head_Buoy toward Tail_Buoy (aft from vessel).
    Positive = cable drifts to starboard. Negative = port.

    Args:
        head_x, head_y: Head_Buoy GPS position
        tail_x, tail_y: Tail_Buoy GPS position
        vessel_heading_deg: Vessel COG (degrees CW from North)

    Returns:
        Feathering angle in degrees (-180 to +180)
    """
    # Cable aft direction (Head → Tail)
    dt_e = tail_x - head_x
    dt_n = tail_y - head_y
    cable_aft_deg = math.degrees(math.atan2(dt_e, dt_n)) % 360

    # Vessel aft direction (opposite of heading)
    vessel_aft_deg = (vessel_heading_deg + 180) % 360

    # Feathering = difference (normalize to -180..+180)
    diff = (cable_aft_deg - vessel_aft_deg + 180) % 360 - 180
    return diff


def interpolate_receivers(
    source_x: float,
    source_y: float,
    heading_deg: float,
    geometry: MarineGeometry,
    **kwargs,
) -> List[ReceiverPosition]:
    """Dispatch to the appropriate interpolation method.

    Args:
        source_x, source_y: Source position
        heading_deg: Ship heading
        geometry: MarineGeometry with interp_method field

    Keyword Args (for feathering method):
        head_x, head_y: Head_Buoy GPS position
        tail_x, tail_y: Tail_Buoy GPS position
        vessel_heading_deg: Vessel COG for feathering computation

    Returns:
        List of ReceiverPosition objects
    """
    method = geometry.interp_method.lower()
    if method == "feathering":
        alpha = getattr(geometry, 'feathering_alpha', 2.0)
        return interpolate_receivers_feathering(
            source_x, source_y, heading_deg, geometry,
            head_x=kwargs.get('head_x', source_x),
            head_y=kwargs.get('head_y', source_y),
            tail_x=kwargs.get('tail_x', source_x),
            tail_y=kwargs.get('tail_y', source_y),
            vessel_heading_deg=kwargs.get('vessel_heading_deg'),
            feathering_alpha=alpha,
        )
    elif method == "catenary":
        return interpolate_receivers_catenary(
            source_x, source_y, heading_deg, geometry, **kwargs,
        )
    elif method == "spline":
        return interpolate_receivers_spline(
            source_x, source_y, heading_deg, geometry, **kwargs,
        )
    else:
        return interpolate_receivers_linear(
            source_x, source_y, heading_deg, geometry,
        )
