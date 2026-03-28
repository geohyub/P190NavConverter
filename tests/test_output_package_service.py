"""Tests for output-package discovery and inline preview helpers."""

from __future__ import annotations

from pathlib import Path

from desktop.services.output_package_service import (
    build_output_package_entries,
    derive_output_package_paths,
    discover_output_package_entries,
    read_artifact_preview,
    render_output_package_manifest,
    summarize_artifact_inventory,
)


def test_build_output_package_entries_and_manifest(tmp_path: Path):
    output = tmp_path / "Line_S_Line.p190"
    report = tmp_path / "Line_S_Line_QC_Report.txt"
    geometry = tmp_path / "Line_S_Line_RadEx_Geometry.tsv"
    ffid_map = tmp_path / "Line_S_Line_FFID_Map.tsv"

    output.write_text("SAMPLE P190\n", encoding="utf-8")
    report.write_text("QC OK\n", encoding="utf-8")
    geometry.write_text("ffid\tsou_x\tsou_y\n", encoding="utf-8")
    ffid_map.write_text("orig_ffid\tp190_point\n", encoding="utf-8")

    artifacts = build_output_package_entries(
        str(output),
        report_path=str(report),
        track_plot_path="",
    )
    manifest = render_output_package_manifest(artifacts)

    assert any(artifact.key == "p190" for artifact in artifacts)
    assert any(artifact.key == "geometry_tsv" for artifact in artifacts)
    assert "Line_S_Line.p190" in manifest
    assert "Line_S_Line_FFID_Map.tsv" in manifest


def test_read_artifact_preview_returns_text_excerpt(tmp_path: Path):
    output = tmp_path / "Line_S_Line.p190"
    output.write_text(
        "H" * 80 + "\n" + "S" * 80 + "\n" + "R" * 80 + "\n",
        encoding="utf-8",
    )

    artifact = next(
        artifact
        for artifact in build_output_package_entries(str(output))
        if artifact.key == "p190"
    )

    preview = read_artifact_preview(artifact, max_lines=2)

    assert "P190" in preview
    assert "Path:" in preview
    assert "H" * 20 in preview


def test_summarize_artifact_inventory_reports_ready_and_missing(tmp_path: Path):
    output = tmp_path / "Line_S_Line.p190"
    output.write_text("SAMPLE P190\n", encoding="utf-8")

    artifacts = build_output_package_entries(str(output))
    summary = summarize_artifact_inventory(artifacts)

    assert "Package coverage:" in summary
    assert "ready" in summary
    assert "not generated yet" in summary


def test_discover_output_package_entries_uses_standard_sidecar_names(tmp_path: Path):
    output = tmp_path / "Line_S_Line.p190"
    output.write_text("SAMPLE P190\n", encoding="utf-8")

    derived = derive_output_package_paths(str(output))
    artifacts = discover_output_package_entries(str(output))
    artifact_keys = {artifact.key for artifact in artifacts}

    assert derived["report_path"].endswith("_QC_Report.txt")
    assert derived["track_plot_path"].endswith("_Track_Plot.png")
    assert "report" in artifact_keys
    assert "track_plot" in artifact_keys
