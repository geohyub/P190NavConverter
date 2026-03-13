"""GPS staircase interpolation — smooth trajectory from discrete GPS updates.

NPD files record at ~3.6 Hz but GPS buoys update at ~0.5-1.5s. Between
updates, the same coordinates repeat (staircase). This module detects
actual GPS update points and interpolates smooth trajectories between them.

Also includes vessel COG (Course Over Ground) computation for feathering
model support.
"""

import math
import warnings
from typing import Optional, Tuple

import numpy as np

try:
    from scipy.interpolate import CubicSpline
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def npd_time_to_seconds(time_str: str) -> Optional[float]:
    """Convert NPD time string 'HH:MM:SS.fff' to total seconds.

    Args:
        time_str: Time string in HH:MM:SS or HH:MM:SS.fff format

    Returns:
        Total seconds since midnight, or None if parsing fails
    """
    try:
        parts = str(time_str).split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError, AttributeError):
        return None


def detect_gps_updates(
    east: np.ndarray,
    north: np.ndarray,
    min_change_m: float = 0.001,
) -> np.ndarray:
    """Detect indices where GPS actually updates (coordinates change).

    Args:
        east: Array of easting values
        north: Array of northing values
        min_change_m: Minimum coordinate change to count as update (meters)

    Returns:
        Boolean mask where True = actual GPS update point
    """
    n = len(east)
    if n == 0:
        return np.array([], dtype=bool)

    mask = np.zeros(n, dtype=bool)
    mask[0] = True    # always include first
    mask[-1] = True   # always include last

    if n < 2:
        return mask

    diff_e = np.abs(np.diff(east))
    diff_n = np.abs(np.diff(north))
    changed = (diff_e > min_change_m) | (diff_n > min_change_m)
    mask[1:] |= changed

    return mask


def interpolate_gps_track(
    times: np.ndarray,
    east: np.ndarray,
    north: np.ndarray,
    method: str = "cubic",
    min_change_m: float = 0.001,
) -> Tuple[np.ndarray, np.ndarray]:
    """Interpolate GPS track to remove staircase artifacts.

    1. Detect actual GPS update points (where coordinates change)
    2. Fit cubic spline (or linear) through update points only
    3. Evaluate at all original time points for smooth trajectory

    Args:
        times: Array of time values in seconds
        east: Array of easting values (may contain repeats)
        north: Array of northing values (may contain repeats)
        method: "cubic" (CubicSpline) or "linear" (np.interp)
        min_change_m: Minimum change to detect GPS update

    Returns:
        (smoothed_east, smoothed_north) arrays of same length as input
    """
    n = len(times)
    if n < 2:
        return east.copy(), north.copy()

    # Detect actual GPS update points
    mask = detect_gps_updates(east, north, min_change_m)
    n_updates = mask.sum()

    if n_updates < 2:
        return east.copy(), north.copy()

    update_times = times[mask]
    update_east = east[mask]
    update_north = north[mask]

    # Choose interpolation method
    if method == "cubic" and HAS_SCIPY and n_updates >= 4:
        cs_east = CubicSpline(update_times, update_east, bc_type="natural")
        cs_north = CubicSpline(update_times, update_north, bc_type="natural")
        smooth_east = cs_east(times)
        smooth_north = cs_north(times)
    else:
        # Linear fallback
        smooth_east = np.interp(times, update_times, update_east)
        smooth_north = np.interp(times, update_times, update_north)

    return smooth_east, smooth_north


def interpolate_gps_at_times(
    npd_times: np.ndarray,
    npd_east: np.ndarray,
    npd_north: np.ndarray,
    query_times: np.ndarray,
    method: str = "cubic",
    min_change_m: float = 0.001,
) -> Tuple[np.ndarray, np.ndarray]:
    """Interpolate GPS positions at specific query times.

    First removes staircase from NPD data, then evaluates the smooth
    trajectory at the requested query times (Track shot times).

    Args:
        npd_times: NPD time array in seconds (may contain None/NaN)
        npd_east: NPD easting array
        npd_north: NPD northing array
        query_times: Times at which to evaluate (Track shot times)
        method: Interpolation method ("cubic" or "linear")
        min_change_m: Minimum coordinate change threshold

    Returns:
        (east_at_query, north_at_query) interpolated positions
    """
    # Filter out invalid time entries
    valid = np.isfinite(npd_times) & np.isfinite(npd_east) & np.isfinite(npd_north)
    t = npd_times[valid].copy()
    e = npd_east[valid].copy()
    n = npd_north[valid].copy()

    if len(t) < 2:
        raise ValueError("Too few valid NPD records for interpolation")

    # Handle midnight crossing: if time decreases significantly, add 86400
    diffs = np.diff(t)
    midnight_jumps = np.where(diffs < -43200)[0]  # >12h jump backward = midnight
    if len(midnight_jumps) > 0:
        for idx in midnight_jumps:
            t[idx + 1:] += 86400

    # Also handle query_times: if they fall before NPD start, they might
    # be next-day times that need +86400
    q_times = query_times.copy()
    npd_start = t[0]
    npd_end = t[-1]
    # Check if query times don't overlap with NPD range — likely next day
    if q_times.max() < npd_start and npd_start > q_times.mean():
        q_times = q_times + 86400

    # Detect GPS updates and build smooth trajectory
    mask = detect_gps_updates(e, n, min_change_m)
    n_updates = mask.sum()

    if n_updates < 2:
        warnings.warn("Too few GPS updates detected, using raw positions")
        update_t = t
        update_e = e
        update_n = n
    else:
        update_t = t[mask]
        update_e = e[mask]
        update_n = n[mask]

    # Ensure strictly increasing times (remove duplicates and backward steps)
    if len(update_t) > 1:
        keep = [0]
        for i in range(1, len(update_t)):
            if update_t[i] > update_t[keep[-1]]:
                keep.append(i)
        keep = np.array(keep)
        update_t = update_t[keep]
        update_e = update_e[keep]
        update_n = update_n[keep]

    # Check query times vs NPD range
    t_min, t_max = update_t[0], update_t[-1]
    out_of_range = (q_times < t_min) | (q_times > t_max)
    if out_of_range.any():
        n_out = out_of_range.sum()
        warnings.warn(
            f"{n_out} query times outside NPD range "
            f"[{t_min:.1f}, {t_max:.1f}] — will be clamped"
        )

    # Clamp query times to NPD range
    q_clamped = np.clip(q_times, t_min, t_max)

    # Interpolate
    if method == "cubic" and HAS_SCIPY and len(update_t) >= 4:
        cs_east = CubicSpline(update_t, update_e, bc_type="natural")
        cs_north = CubicSpline(update_t, update_n, bc_type="natural")
        east_out = cs_east(q_clamped)
        north_out = cs_north(q_clamped)
    else:
        east_out = np.interp(q_clamped, update_t, update_e)
        north_out = np.interp(q_clamped, update_t, update_n)

    return east_out, north_out


def compute_vessel_cog(
    east_array: np.ndarray,
    north_array: np.ndarray,
    window: int = 5,
) -> np.ndarray:
    """Compute vessel COG (Course Over Ground) from GPS position time series.

    Uses a look-back window of `window` shots for stable direction estimation.
    For the feathering interpolation model, vessel COG represents the tow
    direction, which is the reference for computing cross-current cable drift.

    The COG is estimated from the displacement between positions separated by
    `window` shots, which provides better stability than consecutive-shot
    differences (especially with GPS staircase artifacts).

    Args:
        east_array: Easting positions per shot (interpolated at shot times)
        north_array: Northing positions per shot
        window: Number of shots to look back for COG estimate.
                Larger window = smoother but less responsive.
                Default 5 is suitable for ~0.5s shot interval.

    Returns:
        Array of COG values (degrees CW from North, 0-360), same length as input
    """
    n = len(east_array)
    if n == 0:
        return np.array([])

    cog = np.zeros(n)

    for i in range(n):
        # Look back by `window` shots (or to start if not enough shots)
        j = max(0, i - window)
        dx = float(east_array[i] - east_array[j])
        dy = float(north_array[i] - north_array[j])
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0.01:  # minimum movement threshold (1cm)
            cog[i] = math.degrees(math.atan2(dx, dy)) % 360
        elif i > 0:
            cog[i] = cog[i - 1]  # carry forward last valid COG
        # else: first shot with no movement → 0.0 (will be overwritten)

    # Forward-fill any initial zeros (first few shots may have no COG)
    if n > 1 and cog[0] == 0.0:
        for i in range(n):
            if cog[i] != 0.0:
                cog[:i] = cog[i]
                break

    return cog
