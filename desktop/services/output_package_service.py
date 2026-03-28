"""Helpers for browsing generated output-package artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {".p190", ".txt", ".tsv", ".csv", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


@dataclass
class OutputArtifact:
    """One generated artifact in the output package."""

    key: str
    label: str
    path: Path
    note: str
    kind: str

    @property
    def exists(self) -> bool:
        return self.path.exists()


def build_output_package_entries(
    output_path: str,
    report_path: str = "",
    track_plot_path: str = "",
) -> list[OutputArtifact]:
    """Return known package artifacts derived from the main output path."""
    if not output_path:
        return []

    output = Path(output_path)
    base = output.with_suffix("")
    raw_entries = [
        ("p190", "P190", output, "Main fixed-width P190 export"),
        ("report", "QC Report", Path(report_path), "Structural validation report")
        if report_path else None,
        (
            "geometry_tsv",
            "Geometry TSV",
            Path(f"{base}_RadEx_Geometry.tsv"),
            "Full-precision SOU/REC sidecar",
        ),
        (
            "geometry_aligned",
            "Aligned TXT",
            Path(f"{base}_RadEx_Geometry_Aligned.txt"),
            "Readable aligned geometry sidecar",
        ),
        (
            "ffid_map",
            "FFID Map",
            Path(f"{base}_FFID_Map.tsv"),
            "Original FFID to P190 point-number crosswalk",
        ),
        (
            "feathering_report",
            "Feathering Report",
            Path(f"{base}_Feathering_Report.txt"),
            "Style A feathering summary",
        ),
        (
            "feathering_plot",
            "Feathering Plot",
            Path(f"{base}_Feathering_Overview.png"),
            "Feathering overview visualization",
        ),
        (
            "track_plot",
            "Track Plot",
            Path(track_plot_path),
            "Converted source/receiver geometry plot",
        ) if track_plot_path else None,
    ]

    artifacts: list[OutputArtifact] = []
    for item in raw_entries:
        if item is None:
            continue
        key, label, path, note = item
        suffix = path.suffix.lower()
        if suffix in TEXT_EXTENSIONS:
            kind = "text"
        elif suffix in IMAGE_EXTENSIONS:
            kind = "image"
        else:
            kind = "other"
        artifacts.append(
            OutputArtifact(
                key=key,
                label=label,
                path=path,
                note=note,
                kind=kind,
            )
        )
    return artifacts


def derive_output_package_paths(output_path: str) -> dict[str, str]:
    """Infer conventional sidecar paths from the main output path."""
    if not output_path:
        return {"report_path": "", "track_plot_path": ""}

    output = Path(output_path)
    return {
        "report_path": str(output.with_name(output.stem + "_QC_Report.txt")),
        "track_plot_path": str(output.with_name(output.stem + "_Track_Plot.png")),
    }


def discover_output_package_entries(output_path: str) -> list[OutputArtifact]:
    """Build known package entries using the standard naming convention."""
    paths = derive_output_package_paths(output_path)
    return build_output_package_entries(
        output_path,
        report_path=paths["report_path"],
        track_plot_path=paths["track_plot_path"],
    )


def render_output_package_manifest(artifacts: list[OutputArtifact]) -> str:
    """Render a readable package manifest."""
    lines = []
    for artifact in artifacts:
        if artifact.exists:
            size_kb = artifact.path.stat().st_size / 1024
            lines.append(
                f"[OK] {artifact.path.name:<34} {size_kb:7.1f} KB  {artifact.note}"
            )
        else:
            lines.append(
                f"[--] {artifact.path.name:<34} {'':>7}      Not generated in this run"
            )
    return "\n".join(lines) if lines else "No generated files found yet."


def summarize_artifact_inventory(artifacts: list[OutputArtifact]) -> str:
    """Summarize how many known artifacts are ready for review."""
    if not artifacts:
        return "No output package has been generated yet."

    ready = sum(1 for artifact in artifacts if artifact.exists)
    missing = len(artifacts) - ready
    if missing == 0:
        return f"Package coverage: all {ready} known artifacts are ready for review."
    return (
        f"Package coverage: {ready} ready, {missing} not generated yet. "
        "Missing artifacts remain selectable so you can confirm what this run did not produce."
    )


def read_artifact_preview(
    artifact: OutputArtifact,
    *,
    max_lines: int = 18,
    max_chars: int = 3200,
) -> str:
    """Return a compact preview suitable for a text area."""
    if not artifact.exists:
        return (
            f"{artifact.label}\n"
            f"{artifact.note}\n\n"
            "This file has not been generated yet for the current output package."
        )

    size_kb = artifact.path.stat().st_size / 1024
    header = [
        f"{artifact.label}",
        f"Path: {artifact.path}",
        f"Size: {size_kb:.1f} KB",
        f"Meaning: {artifact.note}",
        "",
    ]

    if artifact.kind == "text":
        try:
            content = artifact.path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return "\n".join(header + [f"Preview unavailable: {exc}"])

        lines = content.splitlines()
        excerpt = "\n".join(lines[:max_lines])
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars].rstrip() + "\n..."
        if len(lines) > max_lines:
            excerpt += "\n..."
        return "\n".join(header + [excerpt or "(empty file)"])

    if artifact.kind == "image":
        return "\n".join(
            header
            + [
                "Binary image artifact.",
                "Use the dedicated View button or open the folder to inspect the full image.",
            ]
        )

    return "\n".join(
        header
        + ["Binary artifact preview is not shown inline. Open the folder to inspect it."]
    )
