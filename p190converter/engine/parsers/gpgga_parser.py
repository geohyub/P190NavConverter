"""GPGGA (NMEA) Parser — Auxiliary GPS navigation parser.

Parses $GPGGA sentences from navigation log files.
Used as a supplementary data source for Style A conversion.
"""

import re
from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd


def _nmea_to_dd(value: str, direction: str) -> float:
    """Convert NMEA coordinate (DDMM.MMMMM) to decimal degrees.

    Args:
        value: NMEA coordinate string (e.g. "3416.39462360")
        direction: N/S/E/W
    """
    try:
        val = float(value)
    except (ValueError, TypeError):
        return np.nan

    if val == 0:
        return np.nan

    # Determine degrees digits: 2 for lat, 3 for lon
    if direction in ("E", "W"):
        deg = int(val / 100)
        minutes = val - deg * 100
    else:
        deg = int(val / 100)
        minutes = val - deg * 100

    dd = deg + minutes / 60.0
    if direction in ("S", "W"):
        dd = -dd
    return dd


def parse_gpgga(filepath: Union[str, Path]) -> pd.DataFrame:
    """Parse GPGGA navigation file.

    Supports formats:
      - Raw NMEA: $GPGGA,HHMMSS.SS,lat,N,lon,E,...
      - NaviPac export: File: NNN, $GPGGA,..., HH:MM:SS.SS

    Args:
        filepath: Path to navigation file

    Returns:
        DataFrame with columns: time_str, lat, lon, altitude,
                                n_satellites, hdop, quality
    """
    path = Path(filepath)

    # Multi-encoding read
    lines = []
    for enc in ("utf-8", "cp949", "latin-1"):
        try:
            lines = path.read_text(encoding=enc).splitlines()
            break
        except UnicodeDecodeError:
            continue

    if not lines:
        raise ValueError(f"Cannot read GPGGA file: {filepath}")

    records = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Find $GPGGA in line
        idx = stripped.find("$GPGGA")
        if idx < 0:
            continue

        # Extract GPGGA sentence
        gpgga_part = stripped[idx:]
        fields = gpgga_part.split(",")

        if len(fields) < 15:
            continue

        try:
            # Field indices (0-based from $GPGGA):
            # 1: time, 2: lat, 3: N/S, 4: lon, 5: E/W
            # 6: quality, 7: n_sats, 8: hdop, 9: altitude
            time_str = fields[1]
            lat = _nmea_to_dd(fields[2], fields[3])
            lon = _nmea_to_dd(fields[4], fields[5])
            quality = int(fields[6]) if fields[6] else 0
            n_sats = int(fields[7]) if fields[7] else 0
            hdop = float(fields[8]) if fields[8] else np.nan
            altitude = float(fields[9]) if fields[9] else np.nan

            # Skip invalid fixes
            if quality == 0 or np.isnan(lat) or np.isnan(lon):
                continue

            # Format time string
            if len(time_str) >= 6:
                t_fmt = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            else:
                t_fmt = time_str

            records.append({
                "time_str": t_fmt,
                "lat": lat,
                "lon": lon,
                "altitude": altitude,
                "n_satellites": n_sats,
                "hdop": hdop,
                "quality": quality,
            })

        except (ValueError, IndexError):
            continue

    if not records:
        raise ValueError(f"No valid GPGGA records found in {filepath}")

    return pd.DataFrame(records)
