"""S Record (Source/Shotpoint) formatter for P190.

80-column fixed-width format based on UKOOA P1/90 standard:
  Col  1     : "S"
  Col  2-16  : Line name (15 chars, left-justified)
  Col 17     : Vessel ID (1 char)
  Col 18     : Source ID (1 char)
  Col 19     : Spare
  Col 20-25  : Point number / FFID (6 chars, right-justified integer)
  Col 26-35  : Latitude  DDMMSS.SSN/S (10 chars)
  Col 36-46  : Longitude DDDMMSS.SSE/W (11 chars)
  Col 47-55  : Map Grid Easting (F9.1)
  Col 56-64  : Map Grid Northing (F9.1)
  Col 65-70  : Depth (F6.1 or blank)
  Col 71-73  : Julian Day (I3)
  Col 74-79  : Time HHMMSS (6 chars)
  Col 80     : Spare
"""

from ..crs.dms_formatter import format_latitude, format_longitude
from ...models.shot_gather import ShotGather


def format_point_number(ffid: int) -> str:
    """Format the 6-character point-number field exactly as written to P190."""
    point_str = f"{ffid:6d}"
    if len(point_str) > 6:
        point_str = point_str[-6:]
    return point_str


def point_number_value(ffid: int) -> int:
    """Return the numeric value stored in the truncated P190 point field."""
    return int(format_point_number(ffid).strip() or "0")


def format_s_record(shot: ShotGather, vessel_id: str = "1",
                    source_id: str = "1") -> str:
    """Format a single shot as an 80-char S record line.

    Args:
        shot: ShotGather with source position and lat/lon populated
        vessel_id: Single character vessel ID
        source_id: Single character source ID

    Returns:
        80-character S record string
    """
    line_name = shot.line_name[:15].ljust(15)

    # Point number (FFID) — 6 chars right-justified
    point_str = format_point_number(shot.ffid)

    # Lat/Lon
    if shot.source_lat is not None and shot.source_lon is not None:
        lat_str = format_latitude(shot.source_lat)
        lon_str = format_longitude(shot.source_lon)
    else:
        lat_str = " " * 10
        lon_str = " " * 11

    # Easting/Northing — F9.1
    easting_str = f"{shot.source_x:9.1f}"
    northing_str = f"{shot.source_y:9.1f}"

    # Depth — F6.1 or blank
    if shot.source_depth > 0:
        depth_str = f"{shot.source_depth:6.1f}"
    else:
        depth_str = " " * 6

    # Julian day — I3
    day_str = f"{shot.day:3d}" if shot.day > 0 else "   "

    # Time — HHMMSS
    time_str = shot.time_str

    # Assemble: S(1) + line(15) + vessel(1) + source(1) + spare(1) + point(6)
    #         + lat(10) + lon(11) + easting(9) + northing(9) + depth(6)
    #         + day(3) + time(6) + spare(1)
    record = (
        "S"                         # Col 1
        + line_name                 # Col 2-16
        + vessel_id[0]              # Col 17
        + source_id[0]              # Col 18
        + " "                       # Col 19 (spare)
        + point_str                 # Col 20-25
        + lat_str                   # Col 26-35
        + lon_str                   # Col 36-46
        + easting_str               # Col 47-55
        + northing_str              # Col 56-64
        + depth_str                 # Col 65-70
        + day_str                   # Col 71-73
        + time_str                  # Col 74-79
        + " "                       # Col 80
    )

    assert len(record) == 80, f"S record length {len(record)} != 80"
    return record
