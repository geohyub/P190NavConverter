# -*- coding: utf-8 -*-
"""Unit tests for DMS (Degrees-Minutes-Seconds) formatter."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from p190converter.engine.crs.dms_formatter import (
    decimal_to_dms,
    format_latitude,
    format_longitude,
)


def test_decimal_to_dms_positive():
    d, m, s = decimal_to_dms(35.386111)
    assert d == 35
    assert m == 23
    assert abs(s - 10.0) < 0.01


def test_decimal_to_dms_negative():
    d, m, s = decimal_to_dms(-129.293311)
    assert d == 129
    assert m == 17
    assert abs(s - 35.92) < 0.01


def test_decimal_to_dms_zero():
    d, m, s = decimal_to_dms(0.0)
    assert d == 0 and m == 0 and s == 0.0


def test_decimal_to_dms_carryover_seconds():
    """When seconds round to 60.00, must carry over to minutes."""
    # 10 degrees, 59 minutes, 59.999 seconds -> should become 11 deg 0 min 0.00 sec
    dd = 10 + 59 / 60 + 59.999 / 3600
    d, m, s = decimal_to_dms(dd)
    assert s < 60.0, f"Seconds must not be >= 60, got {s}"
    assert d == 11
    assert m == 0
    assert abs(s - 0.0) < 0.01


def test_decimal_to_dms_carryover_minutes():
    """When minutes overflow, degrees must increment."""
    # 89 degrees, 59 minutes, 59.999 seconds
    dd = 89 + 59 / 60 + 59.999 / 3600
    d, m, s = decimal_to_dms(dd)
    assert m < 60, f"Minutes must not be >= 60, got {m}"
    assert d == 90


def test_format_latitude_north():
    result = format_latitude(35.386111)
    assert len(result) == 10, f"Latitude must be 10 chars, got {len(result)}"
    assert result.endswith("N")
    assert result[:2] == "35"


def test_format_latitude_south():
    result = format_latitude(-12.5)
    assert len(result) == 10
    assert result.endswith("S")
    assert result[:2] == "12"


def test_format_latitude_zero():
    result = format_latitude(0.0)
    assert len(result) == 10
    assert result.endswith("N")


def test_format_longitude_east():
    result = format_longitude(129.293311)
    assert len(result) == 11, f"Longitude must be 11 chars, got {len(result)}"
    assert result.endswith("E")
    assert result[:3] == "129"


def test_format_longitude_west():
    result = format_longitude(-73.5)
    assert len(result) == 11
    assert result.endswith("W")


def test_format_longitude_zero():
    result = format_longitude(0.0)
    assert len(result) == 11
    assert result.endswith("E")


def test_format_longitude_antimeridian():
    """Longitude at 180 degrees."""
    result = format_longitude(180.0)
    assert len(result) == 11
    assert result[:3] == "180"


def test_format_latitude_near_pole():
    """Latitude near 90 degrees."""
    result = format_latitude(89.9999)
    assert len(result) == 10
    assert result.endswith("N")


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
