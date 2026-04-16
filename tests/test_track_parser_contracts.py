from __future__ import annotations

from pathlib import Path

import pytest

from p190converter.engine.parsers.track_parser import parse_track_file


def test_parse_track_file_rejects_conflicting_duplicate_ffids(tmp_path: Path):
    track_path = tmp_path / "conflicting_track.txt"
    track_path.write_text(
        "\n".join(
            [
                "FFID\tCHAN\tSOU_X\tSOU_Y\tDAY\tHOUR\tMINUTE\tSECOND",
                "1001\t1\t500000.0\t3800000.0\t166\t9\t30\t0",
                "1001\t2\t500050.0\t3800000.0\t166\t9\t30\t0",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Conflicting duplicate FFID"):
        parse_track_file(track_path)


def test_parse_track_file_keeps_identical_channel_duplicates(tmp_path: Path):
    track_path = tmp_path / "valid_track.txt"
    track_path.write_text(
        "\n".join(
            [
                "FFID\tCHAN\tSOU_X\tSOU_Y\tDAY\tHOUR\tMINUTE\tSECOND",
                "1001\t1\t500000.0\t3800000.0\t166\t9\t30\t0",
                "1001\t2\t500000.0\t3800000.0\t166\t9\t30\t0",
            ]
        ),
        encoding="utf-8",
    )

    result = parse_track_file(track_path)

    assert result.n_shots == 1
    assert result.n_channels == 2
    assert result.df["ffid"].tolist() == [1001]
