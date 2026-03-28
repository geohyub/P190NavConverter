"""Small explanation helpers for the desktop UX."""

from __future__ import annotations

from pathlib import Path


SOURCE_POSITION_OPTIONS = [
    ("front_gps", "Front GPS (measured source)"),
    ("track_sou", "Track SOU_X/Y (RadExPro-aligned)"),
]

SOURCE_POSITION_DESCRIPTIONS = {
    "front_gps": (
        "Anchors each shot to the selected Front GPS position. "
        "Use this when the exported P190 should follow the measured nav."
    ),
    "track_sou": (
        "Anchors each shot to Track SOU_X/SOU_Y. "
        "Use this when Style A should match the RadExPro-calculated source position."
    ),
}

INTERP_METHOD_DESCRIPTIONS = {
    "linear": (
        "Standard equal-spacing geometry. Best default for short 2D/UHR spreads "
        "and closest to ordinary RadExPro geometry output."
    ),
    "catenary": (
        "Physics-oriented cable curve. More useful for long streamers or deep-water "
        "tow cases than short UHR spreads."
    ),
    "spline": (
        "Smooth curve through control positions. Useful when you need a softer shape "
        "than strict linear spacing."
    ),
    "feathering": (
        "Uses Head/Tail GPS + vessel COG to bend the receiver line with cross-current. "
        "Best when current-driven cable drift matters."
    ),
}


def _safe_int(value, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def describe_coord_decimals(value) -> tuple[str, bool]:
    """Explain what the RadEx sidecar precision setting affects."""
    decimals = _safe_int(value)
    if decimals is None:
        return "Enter an integer from 0 to 8 for the RadEx sidecar precision.", False
    if not 0 <= decimals <= 8:
        return "RadEx sidecar precision must stay between 0 and 8 decimals.", False

    resolution = 10 ** (-decimals) if decimals > 0 else 1
    resolution_text = f"{resolution:.{decimals}f} m" if decimals > 0 else "1 m"
    return (
        "Applies only to `_RadEx_Geometry.tsv` and `_RadEx_Geometry_Aligned.txt`. "
        f"{decimals} decimals means a displayed resolution of {resolution_text}. "
        "The `.p190` file still follows the format limit of 0.1 m grid precision.",
        True,
    )


def build_conversion_story(style: str, input_vals: dict) -> str:
    """Return a compact live summary of what the current settings mean."""
    decimals = _safe_int(input_vals.get("radex_coord_decimals", 5), 5)
    line_name = input_vals.get("line_name", "").strip() or "(line name not set)"

    if style == "A":
        front = input_vals.get("front_gps", "").strip() or "(front GPS not selected)"
        tail = input_vals.get("tail_gps", "").strip() or "(tail GPS not selected)"
        source_mode = input_vals.get("source_position_mode", "front_gps")
        source_desc = SOURCE_POSITION_DESCRIPTIONS.get(
            source_mode, SOURCE_POSITION_DESCRIPTIONS["front_gps"]
        )
        return "\n".join(
            [
                f"Style A flow: Track timing/FFID + NPD GPS + geometry -> `{line_name}.p190`.",
                f"Source basis: {source_desc}",
                f"GPS pair: Front `{front}` / Tail `{tail}` for heading and feathering-ready interpolation.",
                (
                    f"Export package: `.p190`, `_QC_Report.txt`, "
                    f"`_RadEx_Geometry.tsv` ({decimals} decimals), "
                    "`_RadEx_Geometry_Aligned.txt`, `_FFID_Map.tsv`."
                ),
                "Use the RadEx geometry sidecar when exact SOU/REC coordinates or original FFID tracing matters more than strict P190 compatibility.",
            ]
        )

    return "\n".join(
        [
            f"Style B flow: RadExPro header export -> `{line_name}.p190` with the same shot/receiver geometry that was already exported by RadExPro.",
            (
                f"Export package: `.p190`, `_QC_Report.txt`, "
                f"`_RadEx_Geometry.tsv` ({decimals} decimals), "
                "`_RadEx_Geometry_Aligned.txt`, `_FFID_Map.tsv`."
            ),
            "The `.p190` file is the standard fixed-width delivery file. The RadEx sidecars preserve full-precision SOU/REC coordinates for ASCII re-import and troubleshooting.",
        ]
    )


def build_crs_impact_story(crs_config) -> str:
    """Summarize what the selected CRS controls."""
    label = crs_config.display_name or f"EPSG:{crs_config.epsg_code}"
    zone_text = (
        f"{crs_config.utm_zone}{crs_config.hemisphere}"
        if getattr(crs_config, "is_utm", False)
        else "custom projected CRS"
    )
    return "\n".join(
        [
            f"Current CRS: {label}",
            (
                "This CRS is used to convert source UTM coordinates into the latitude/longitude "
                "written into every P190 S record."
            ),
            (
                f"It also describes the projected grid metadata recorded in the header. "
                f"Selected zone / frame: {zone_text}, datum `{crs_config.datum_name}`."
            ),
        ]
    )


def build_geometry_story(geometry) -> str:
    """Summarize offset meaning and interpolation behavior."""
    rel_dx = geometry.rx1_dx - geometry.source_dx
    rel_dy = geometry.rx1_dy - geometry.source_dy
    spread = geometry.total_spread
    method_desc = INTERP_METHOD_DESCRIPTIONS.get(
        geometry.interp_method.lower(), INTERP_METHOD_DESCRIPTIONS["linear"]
    )

    lines = [
        (
            f"Entered offsets are vessel-frame positions. Source=({geometry.source_dx:.2f}, {geometry.source_dy:.2f}) m, "
            f"RX1=({geometry.rx1_dx:.2f}, {geometry.rx1_dy:.2f}) m."
        ),
        (
            f"Derived first-receiver position relative to source: "
            f"({rel_dx:.2f}, {rel_dy:.2f}) m before receiver interpolation."
        ),
        (
            f"Receiver layout: {geometry.n_channels} channels x {geometry.rx_interval:.3f} m = "
            f"{spread:.1f} m spread, cable depth {geometry.cable_depth:.1f} m."
        ),
        f"Interpolation: {method_desc}",
    ]
    if geometry.interp_method.lower() == "feathering":
        lines.append(
            f"Feathering alpha={geometry.feathering_alpha:.2f}. Larger alpha pushes more of the cross-current correction toward the tail end of the spread."
        )
    return "\n".join(lines)


def build_export_package_story(
    output_path: str,
    style: str,
    radex_coord_decimals,
    source_position_mode: str = "front_gps",
    warnings: list[str] | None = None,
) -> str:
    """Describe the exported files and the trust/compatibility tradeoffs."""
    decimals = _safe_int(radex_coord_decimals, 5)
    base = Path(output_path).with_suffix("")
    source_desc = SOURCE_POSITION_DESCRIPTIONS.get(
        source_position_mode, SOURCE_POSITION_DESCRIPTIONS["front_gps"]
    )

    lines = [
        (
            f"{base.name}.p190: Standard UKOOA P1/90 export. Best for delivery or direct P190 import, "
            "but point numbers are limited to 6 digits and projected grid coordinates are rounded to 0.1 m."
        ),
        (
            f"{base.name}_RadEx_Geometry.tsv: Full-precision SOU/REC sidecar "
            f"({decimals} decimals). Use this when exact geometry or large FFID preservation matters."
        ),
        (
            f"{base.name}_RadEx_Geometry_Aligned.txt: Same sidecar content in a fixed-width readable layout for quick visual inspection."
        ),
        (
            f"{base.name}_FFID_Map.tsv: Original FFID -> P190 point number crosswalk. "
            "Use this whenever truncation or collisions are suspected."
        ),
    ]
    if style == "A":
        lines.append(
            f"Style A basis for this run: {source_desc}"
        )
        lines.append(
            "If feathering analysis completes, companion feathering report/overview files are written to the same folder."
        )

    if warnings:
        lines.append("")
        lines.append("Warnings from this run:")
        for warning in warnings[:4]:
            lines.append(f"- {warning}")

    return "\n".join(lines)
