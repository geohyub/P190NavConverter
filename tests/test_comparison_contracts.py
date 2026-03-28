"""Unit tests for comparison result compatibility and reporting."""

from __future__ import annotations

from pathlib import Path

from p190converter.engine.qc.comparison import (
    _parse_s_records,
    compare_p190_files,
)
from p190converter.engine.qc.report import generate_comparison_report


def _s_line(ffid: int, easting: float, northing: float) -> str:
    chars = [" "] * 80
    chars[0] = "S"
    chars[19:25] = list(f"{ffid:6d}")
    chars[46:55] = list(f"{easting:9.1f}")
    chars[55:64] = list(f"{northing:9.1f}")
    return "".join(chars) + "\n"


def _r_line(groups) -> str:
    chars = [" "] * 80
    chars[0] = "R"
    for idx, (channel, easting, northing) in enumerate(groups):
        start = 1 + idx * 26
        group = f"{channel:4d}{easting:9.1f}{northing:9.1f}{0.0:4.1f}"
        chars[start:start + 26] = list(group)
    return "".join(chars) + "\n"


def _write_sample_p190(path: Path, x_offset: float = 0.0) -> None:
    lines = [
        _s_line(1001, 500000.0 + x_offset, 3800000.0),
        _r_line(
            [
                (1, 500010.0 + x_offset, 3800002.0),
                (2, 500020.0 + x_offset, 3800004.0),
            ]
        ),
        _s_line(1002, 500100.0 + x_offset, 3800100.0),
        _r_line(
            [
                (1, 500110.0 + x_offset, 3800102.0),
                (2, 500120.0 + x_offset, 3800104.0),
            ]
        ),
    ]
    path.write_text("".join(lines), encoding="utf-8")


def test_comparison_result_exposes_legacy_aliases(tmp_path: Path):
    style_a = tmp_path / "style_a.p190"
    style_b = tmp_path / "style_b.p190"
    _write_sample_p190(style_a, x_offset=0.0)
    _write_sample_p190(style_b, x_offset=2.0)

    result = compare_p190_files(style_a, style_b)

    assert result.matched_shots == 2
    assert result.source_mean_diff == result.source_dist_mean
    assert result.receiver_mean_diff == result.rx_dist_mean
    assert result.source_diffs == [2.0, 2.0]
    assert result.grade == "EXCELLENT"
    assert result.worst_ffid == 1001
    channel_df = result.channel_deltas_for_ffid(1001)
    assert channel_df["channel"].tolist() == [1, 2]
    assert channel_df["dist"].tolist() == [2.0, 2.0]
    assert "source_x_a" in result.per_shot_df.columns
    assert "source_dist" in result.per_shot_df.columns


def test_generate_comparison_report_uses_comparison_contract(tmp_path: Path):
    style_a = tmp_path / "style_a.p190"
    style_b = tmp_path / "style_b.p190"
    _write_sample_p190(style_a, x_offset=0.0)
    _write_sample_p190(style_b, x_offset=4.0)

    result = compare_p190_files(style_a, style_b)
    report = generate_comparison_report(result)

    assert "Style A vs Style B Position Comparison" in report
    assert "Assessment: GOOD" in report
    assert "Receiver Position Difference" in report


def test_parse_s_records_returns_s_dataframe(tmp_path: Path):
    path = tmp_path / "sample.p190"
    _write_sample_p190(path, x_offset=0.0)

    df = _parse_s_records(path)

    assert list(df.columns) == ["ffid", "easting", "northing"]
    assert df["ffid"].tolist() == [1001, 1002]
