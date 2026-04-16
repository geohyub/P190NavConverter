# -*- coding: utf-8 -*-
"""Unit tests for NPD Navigation Parser."""
import sys
import os
import tempfile
import warnings
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from p190converter.engine.parsers.npd_parser import (
    _dms_to_dd,
    _safe_float,
    _parse_npd_header,
    parse_npd_sources,
    parse_npd,
)


# ── _dms_to_dd ──

def test_dms_to_dd_standard():
    """035 05'25.70510" -> ~35.0904736"""
    result = _dms_to_dd('035 05\'25.70510"')
    assert abs(result - 35.09047) < 0.001


def test_dms_to_dd_negative():
    result = _dms_to_dd('-035 05\'25.70"')
    assert result < 0


def test_dms_to_dd_with_hemisphere_S():
    result = _dms_to_dd('035 05\'25.70"S')
    assert result < 0


def test_dms_to_dd_empty():
    import numpy as np
    assert np.isnan(_dms_to_dd(""))


def test_dms_to_dd_plain_float():
    result = _dms_to_dd("35.5")
    assert abs(result - 35.5) < 0.001


# ── _safe_float ──

def test_safe_float_valid():
    assert _safe_float("123.456") == 123.456


def test_safe_float_invalid():
    import numpy as np
    assert np.isnan(_safe_float("abc"))


def test_safe_float_whitespace():
    assert _safe_float("  42.0  ") == 42.0


# ── _parse_npd_header ──

def test_parse_header_d_type():
    header = "D,Position: GPS1: East,North,Lat,Long,Height,O,Position: GPS2: East,North,Lat,Long,Height"
    info = _parse_npd_header(header)
    assert info["format"] == "d_type"
    assert len(info["sources"]) == 2
    assert info["sources"][0]["name"] == "GPS1"
    assert info["sources"][1]["name"] == "GPS2"


def test_parse_header_finds_east_col():
    header = "D,Position: Head_Buoy: East,North,Lat,Long,Height"
    info = _parse_npd_header(header)
    src = info["sources"][0]
    assert src["col_indices"]["east"] >= 0
    assert src["col_indices"]["north"] >= 0


# ── parse_npd_sources / parse_npd (file-based) ──

def _write_npd_file(content):
    """Write temp NPD file and return path."""
    fd, path = tempfile.mkstemp(suffix=".NPD")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_parse_npd_sources_basic():
    content = (
        "D,Position: Head_Buoy: East,North,Lat,Long,Height,O,"
        "Position: Tail_Buoy: East,North,Lat,Long,Height\n"
        "12:00:00.000,500000.0,3900000.0,35.0,129.0,0.0,O,"
        "500001.0,3900001.0,35.0001,129.0001,0.0\n"
    )
    path = _write_npd_file(content)
    try:
        sources = parse_npd_sources(path)
        assert "Head_Buoy" in sources
        assert "Tail_Buoy" in sources
    finally:
        os.unlink(path)


def test_parse_npd_basic():
    content = (
        "D,Position: GPS1: East,North,Lat,Long,Height\n"
        "12:00:00.000,500000.0,3900000.0,35.0,129.0,0.0\n"
        "12:00:01.000,500001.0,3900001.0,35.0001,129.0001,0.0\n"
    )
    path = _write_npd_file(content)
    try:
        df = parse_npd(path)
        assert len(df) == 2
        assert "east" in df.columns
        assert "north" in df.columns
        assert abs(df["east"].iloc[0] - 500000.0) < 0.01
    finally:
        os.unlink(path)


def test_parse_npd_skip_invalid_warns():
    """Invalid east/north should be skipped with a warning."""
    content = (
        "D,Position: GPS1: East,North,Lat,Long,Height\n"
        "12:00:00.000,500000.0,3900000.0,35.0,129.0,0.0\n"
        "12:00:01.000,INVALID,3900001.0,35.0,129.0,0.0\n"
        "12:00:02.000,500002.0,3900002.0,35.0,129.0,0.0\n"
    )
    path = _write_npd_file(content)
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            df = parse_npd(path)
            assert len(df) == 2, "Invalid record should be skipped"
            skip_warns = [x for x in w if "skipped" in str(x.message).lower()]
            assert len(skip_warns) >= 1, "Should warn about skipped records"
    finally:
        os.unlink(path)


def test_parse_npd_source_by_name():
    content = (
        "D,Position: Head_Buoy: East,North,Lat,Long,Height,O,"
        "Position: Tail_Buoy: East,North,Lat,Long,Height\n"
        "12:00:00.000,500000.0,3900000.0,35.0,129.0,0.0,O,"
        "600000.0,4000000.0,36.0,130.0,0.0\n"
    )
    path = _write_npd_file(content)
    try:
        df = parse_npd(path, source="Tail")
        assert abs(df["east"].iloc[0] - 600000.0) < 0.01
    finally:
        os.unlink(path)


def test_parse_npd_ambiguous_source_match_raises():
    content = (
        "D,Position: Head_Buoy: East,North,Lat,Long,Height,O,"
        "Position: Tail_Buoy: East,North,Lat,Long,Height\n"
        "12:00:00.000,500000.0,3900000.0,35.0,129.0,0.0,O,"
        "600000.0,4000000.0,36.0,130.0,0.0\n"
    )
    path = _write_npd_file(content)
    try:
        with pytest.raises(ValueError):
            parse_npd(path, source="Buoy")
    finally:
        os.unlink(path)


def test_parse_npd_empty_file_raises():
    path = _write_npd_file("")
    try:
        raised = False
        try:
            parse_npd(path)
        except ValueError:
            raised = True
        assert raised, "Empty file should raise ValueError"
    finally:
        os.unlink(path)


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
