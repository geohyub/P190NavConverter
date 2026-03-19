# -*- coding: utf-8 -*-
"""Unit tests for R Record (Receiver Group) formatter."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from p190converter.engine.writer.r_record import _format_receiver_group, format_r_records
from p190converter.models.shot_gather import ReceiverPosition, ShotGather


def _make_rx(ch, x, y, depth=0.0):
    return ReceiverPosition(channel=ch, x=x, y=y, depth=depth)


def test_single_group_length():
    rx = _make_rx(1, 500000.1, 3900000.2, depth=3.5)
    group = _format_receiver_group(rx)
    assert len(group) == 26, f"Group length {len(group)} != 26"


def test_single_group_content():
    rx = _make_rx(12, 500000.1, 3900000.2, depth=3.5)
    group = _format_receiver_group(rx)
    # Channel: right-justified 4 chars
    assert group[:4].strip() == "12"
    # Easting: 9 chars
    assert group[4:13].strip() == "500000.1"
    # Northing: 9 chars
    assert group[13:22].strip() == "3900000.2"
    # Depth: 4 chars
    assert group[22:26].strip() == "3.5"


def test_group_zero_depth_is_blank():
    rx = _make_rx(1, 500000.0, 3900000.0, depth=0.0)
    group = _format_receiver_group(rx)
    assert group[22:26] == "    ", "Zero depth should be blank"


def test_r_record_line_length():
    """Each R record line must be exactly 80 characters."""
    shot = ShotGather(
        ffid=1, source_x=500000.0, source_y=3900000.0,
        receivers=[_make_rx(i + 1, 500000.0 + i * 3.125, 3900000.0) for i in range(6)],
    )
    lines = format_r_records(shot, streamer_id="1")
    for i, line in enumerate(lines):
        assert len(line) == 80, f"R record line {i} length {len(line)} != 80"


def test_r_record_3_per_line():
    """3 receivers per R line. 6 channels = 2 lines."""
    shot = ShotGather(
        ffid=1, source_x=0.0, source_y=0.0,
        receivers=[_make_rx(i + 1, float(i), 0.0) for i in range(6)],
    )
    lines = format_r_records(shot)
    assert len(lines) == 2, f"6 channels should produce 2 R lines, got {len(lines)}"


def test_r_record_not_multiple_of_3():
    """5 channels = 2 lines (3 + 2), last group padded with spaces."""
    shot = ShotGather(
        ffid=1, source_x=0.0, source_y=0.0,
        receivers=[_make_rx(i + 1, float(i), 0.0) for i in range(5)],
    )
    lines = format_r_records(shot)
    assert len(lines) == 2
    # Last line: 2 real groups + 1 blank group
    last = lines[-1]
    assert len(last) == 80
    # 3rd group (cols 54-79) should be all spaces
    assert last[53:79] == " " * 26


def test_r_record_single_channel():
    """1 channel = 1 line, 2 blank groups."""
    shot = ShotGather(
        ffid=1, source_x=0.0, source_y=0.0,
        receivers=[_make_rx(1, 100.0, 200.0)],
    )
    lines = format_r_records(shot)
    assert len(lines) == 1
    assert len(lines[0]) == 80


def test_r_record_starts_with_R():
    shot = ShotGather(
        ffid=1, source_x=0.0, source_y=0.0,
        receivers=[_make_rx(1, 100.0, 200.0)],
    )
    lines = format_r_records(shot)
    assert lines[0][0] == "R"


def test_r_record_streamer_id():
    shot = ShotGather(
        ffid=1, source_x=0.0, source_y=0.0,
        receivers=[_make_rx(1, 100.0, 200.0)],
    )
    lines = format_r_records(shot, streamer_id="2")
    assert lines[0][79] == "2", "Streamer ID should be at column 80"


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
