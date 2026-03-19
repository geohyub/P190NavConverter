"""NPD Navigation Parser — NaviPac D-type / T-type format.

Adopted from Calibration parser pattern (parsers.py lines 879-1099):
- parse_npd_sources(): auto-detect position sources
- parse_npd(): parse with source selection (partial match)
- parse_npd_comparison(): dual-position NPD parsing

NPD Format Types:
  D-type (NaviPac Classic):
    D,Position: Source1: East,North,Lat,Long,Height,O,Position: Source2: ...
  T-type (EIVA NaviPac):
    YYYY:MM:DD:... vers:X.X file:... Type,Time,...Position: Source1: East,...
"""

import re
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


def _read_npd_lines(filepath: Union[str, Path]) -> List[str]:
    """Read NPD file with multi-encoding fallback."""
    path = Path(filepath)
    for enc in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot read NPD file with any encoding: {filepath}")


def _safe_float(val: str) -> float:
    """Safely convert string to float, return NaN on failure."""
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return np.nan


def _dms_to_dd(dms_str: str) -> float:
    """Convert DMS string (e.g. 035 05'25.70510\") to decimal degrees."""
    dms_str = dms_str.strip()
    if not dms_str:
        return np.nan

    # Pattern: DD MM'SS.SSS" or DD MM SS.SSS
    m = re.match(
        r"(-?\d+)[°\s]+(\d+)['\s]+([0-9.]+)[\"'\s]*([NSEW])?",
        dms_str,
    )
    if m:
        d, mi, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        dd = abs(d) + mi / 60.0 + s / 3600.0
        if d < 0 or (m.group(4) and m.group(4) in "SW"):
            dd = -dd
        return dd

    # Try simple float
    return _safe_float(dms_str)


def _parse_npd_header(header_line: str) -> Dict:
    """Parse NPD header line to extract format info and source definitions.

    Returns:
        {
            "format": "d_type" | "t_type",
            "header_date": str | None,
            "time_col": int,
            "sources": [
                {
                    "name": str,
                    "col_indices": {"east": int, "north": int,
                                    "lat": int, "lon": int, "height": int}
                }, ...
            ]
        }
    """
    result = {
        "format": "d_type",
        "header_date": None,
        "time_col": -1,
        "sources": [],
    }

    fields = [f.strip() for f in header_line.split(",")]

    # Detect T-type: look for "vers:" and "file:" patterns
    header_str = header_line.lower()
    if "vers:" in header_str and "file:" in header_str:
        result["format"] = "t_type"
        # Extract date from YYYY:MM:DD prefix
        date_m = re.match(r"(\d{4}):(\d{2}):(\d{2})", header_line)
        if date_m:
            result["header_date"] = (
                f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"
            )

    # Find time column
    for i, f in enumerate(fields):
        fl = f.lower()
        if fl in ("time", "d") or "time" in fl:
            result["time_col"] = i
            break

    # Find position sources: look for "Position: <name>: East" pattern
    # T-type NPD format: "Position: Head_Buoy: East" is one field,
    # followed by separate fields "North", "Lat", "Long", "Height", ...
    # Only "East" has the "Position:" prefix; subsequent coords are plain names.
    source_pattern = re.compile(
        r"Position:\s*(.+?):\s*(East|North|Lat|Long|Height)",
        re.IGNORECASE,
    )

    # Map standalone field names to coord keys
    standalone_map = {
        "east": "east", "north": "north",
        "lat": "lat", "long": "lon", "height": "height",
    }

    sources_dict = {}  # name -> col_indices (ordered dict preserves insertion)
    current_source = None  # track which source's subsequent fields belong to

    for i, f in enumerate(fields):
        m = source_pattern.match(f)
        if m:
            name = m.group(1).strip()
            coord_type = m.group(2).lower()
            coord_key = standalone_map.get(coord_type, coord_type)

            if name not in sources_dict:
                sources_dict[name] = {"east": -1, "north": -1,
                                      "lat": -1, "lon": -1, "height": -1}
            sources_dict[name][coord_key] = i
            current_source = name
        elif current_source is not None:
            # Check if this field is a standalone coord name (North, Lat, etc.)
            fl = f.lower().strip()
            if fl in standalone_map:
                coord_key = standalone_map[fl]
                if sources_dict[current_source][coord_key] == -1:
                    sources_dict[current_source][coord_key] = i
            elif fl in ("o", "d", "x", "kp", "dal", "dol"):
                # Known non-coord fields within a source block — skip
                pass
            else:
                # Unknown field after source block — end tracking
                current_source = None

    # Convert to list preserving order
    for name, cols in sources_dict.items():
        result["sources"].append({"name": name, "col_indices": cols})

    return result


def parse_npd_sources(filepath: Union[str, Path]) -> List[str]:
    """Detect available position sources in NPD file.

    Args:
        filepath: Path to NPD navigation file

    Returns:
        List of source names (e.g. ["Head_Buoy", "Tail_Buoy", "DGPS_1"])
    """
    lines = _read_npd_lines(filepath)

    # Find first non-empty line (header)
    header_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            header_line = stripped
            break

    if not header_line:
        return []

    info = _parse_npd_header(header_line)
    return [s["name"] for s in info["sources"]]


def parse_npd(
    filepath: Union[str, Path],
    source: Union[str, int, None] = None,
) -> pd.DataFrame:
    """Parse NPD file and extract navigation data for a selected source.

    Args:
        filepath: Path to NPD navigation file
        source: Source selector:
            - None: first source (default)
            - int: source by 0-based index
            - str: partial, case-insensitive name match

    Returns:
        DataFrame with columns: time, time_str, east, north, lat, lon, height
    """
    lines = _read_npd_lines(filepath)

    # Find header line
    header_idx = -1
    for i, line in enumerate(lines):
        if line.strip():
            header_idx = i
            break

    if header_idx < 0:
        raise ValueError("Empty NPD file")

    info = _parse_npd_header(lines[header_idx])
    all_sources = info["sources"]

    if not all_sources:
        raise ValueError(
            "No position sources found in NPD header. "
            "Expected 'Position: <name>: East/North/...' columns."
        )

    # Select source
    if source is None:
        sel = all_sources[0]
    elif isinstance(source, int):
        if source < 0 or source >= len(all_sources):
            raise ValueError(
                f"Source index {source} out of range "
                f"(0-{len(all_sources)-1}). "
                f"Available: {[s['name'] for s in all_sources]}"
            )
        sel = all_sources[source]
    else:
        # Partial, case-insensitive match
        source_lower = source.lower()
        matches = [s for s in all_sources
                    if source_lower in s["name"].lower()]
        if not matches:
            raise ValueError(
                f"Source '{source}' not found. "
                f"Available: {[s['name'] for s in all_sources]}"
            )
        sel = matches[0]

    col_map = sel["col_indices"]
    time_col = info["time_col"]

    # Parse data lines
    records = []
    skipped_count = 0
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            continue

        parts = [p.strip() for p in stripped.split(",")]

        def _get(field):
            ci = col_map.get(field, -1)
            if 0 <= ci < len(parts):
                return parts[ci]
            return ""

        east_str = _get("east")
        north_str = _get("north")
        lat_str = _get("lat")
        lon_str = _get("lon")
        height_str = _get("height")

        e_val = _safe_float(east_str)
        n_val = _safe_float(north_str)

        # Skip invalid records
        if np.isnan(e_val) or np.isnan(n_val):
            skipped_count += 1
            continue

        # Time
        time_str = ""
        if 0 <= time_col < len(parts):
            time_str = parts[time_col]

        # Lat/Lon: try DMS first, then float
        lat_val = _dms_to_dd(lat_str) if lat_str else np.nan
        lon_val = _dms_to_dd(lon_str) if lon_str else np.nan

        records.append({
            "time_str": time_str,
            "east": e_val,
            "north": n_val,
            "lat": lat_val,
            "lon": lon_val,
            "height": _safe_float(height_str),
        })

    if skipped_count > 0:
        warnings.warn(
            f"NPD source '{sel['name']}': {skipped_count} record(s) skipped "
            f"(invalid East/North), {len(records)} valid"
        )

    if not records:
        raise ValueError(
            f"No valid navigation records found for source '{sel['name']}'"
        )

    df = pd.DataFrame(records)
    return df


def parse_npd_comparison(
    filepath: Union[str, Path],
) -> Dict:
    """Parse dual-position NPD file for comparison.

    Returns:
        {
            "source1": DataFrame,
            "source2": DataFrame,
            "source1_name": str,
            "source2_name": str,
            "combined": DataFrame,
        }
    """
    sources = parse_npd_sources(filepath)
    if len(sources) < 2:
        raise ValueError(
            f"Dual NPD requires at least 2 sources, found {len(sources)}: "
            f"{sources}"
        )

    df1 = parse_npd(filepath, source=0)
    df2 = parse_npd(filepath, source=1)

    # Build combined DataFrame with prefixed columns
    min_len = min(len(df1), len(df2))
    combined = pd.DataFrame()
    for col in ["east", "north", "lat", "lon", "height"]:
        combined[f"s1_{col}"] = df1[col].values[:min_len]
        combined[f"s2_{col}"] = df2[col].values[:min_len]

    if "time_str" in df1.columns:
        combined["time_str"] = df1["time_str"].values[:min_len]

    return {
        "source1": df1,
        "source2": df2,
        "source1_name": sources[0],
        "source2_name": sources[1],
        "combined": combined,
    }
