"""DMS (Degrees-Minutes-Seconds) formatting for P190 columns.

P190 S Record format:
  Latitude:  DDMMSS.SS + N/S  (10 chars total)
  Longitude: DDDMMSS.SS + E/W (11 chars total)
"""

from typing import Tuple


def decimal_to_dms(decimal_deg: float) -> Tuple[int, int, float]:
    """Convert decimal degrees to (degrees, minutes, seconds).

    Args:
        decimal_deg: Angle in decimal degrees (can be negative)

    Returns:
        (degrees, minutes, seconds) — degrees always positive,
        seconds rounded to 2 decimal places with carry-over handling
    """
    total_sec = abs(decimal_deg) * 3600.0
    d = int(total_sec // 3600)
    remaining = total_sec - d * 3600
    m = int(remaining // 60)
    s = remaining - m * 60

    # Round seconds to output precision (2 decimal places) FIRST,
    # then cascade carry-over to avoid "60.00" in formatted output.
    s = round(s, 2)
    if s >= 60.0:
        s -= 60.0
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    return d, m, s


def format_latitude(lat: float) -> str:
    """Format latitude for P190 S Record.

    Returns:
        10-char string: DDMMSS.SSN/S
        Example: "352310.00N"
    """
    direction = "N" if lat >= 0 else "S"
    d, m, s = decimal_to_dms(lat)
    # DD(2) + MM(2) + SS.SS(5) + N/S(1) = 10 chars
    return f"{d:02d}{m:02d}{s:05.2f}{direction}"


def format_longitude(lon: float) -> str:
    """Format longitude for P190 S Record.

    Returns:
        11-char string: DDDMMSS.SSE/W
        Example: "1291735.92E"
    """
    direction = "E" if lon >= 0 else "W"
    d, m, s = decimal_to_dms(lon)
    # DDD(3) + MM(2) + SS.SS(5) + E/W(1) = 11 chars
    return f"{d:03d}{m:02d}{s:05.2f}{direction}"
