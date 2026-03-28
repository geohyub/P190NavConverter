"""QC report generation."""

from .validator import QCResult
from .comparison import ComparisonResult, format_comparison_report
from ...models.survey_config import SurveyConfig


def generate_qc_report(qc: QCResult, config: SurveyConfig) -> str:
    """Generate human-readable QC report.

    Args:
        qc: QCResult from validation
        config: SurveyConfig used for conversion

    Returns:
        Multi-line report text
    """
    status = "PASS" if qc.passed else "FAIL"

    lines = [
        "=" * 60,
        "P190 NavConverter — QC Report",
        "=" * 60,
        "",
        f"Line Name    : {config.line_name}",
        f"Style        : {config.style}",
        f"UTM Zone     : {config.crs.utm_zone}{config.crs.hemisphere}",
        f"EPSG         : {config.crs.epsg_code}",
        "",
        "--- Record Summary ---",
        f"H Records    : {qc.h_records}",
        f"S Records    : {qc.s_records} (shots)",
        f"R Records    : {qc.r_records}",
        f"Total Lines  : {qc.total_lines}",
        "",
        "--- Validation ---",
        f"Status       : {status}",
        f"80-col Errors: {qc.line_length_errors}",
        f"Invalid Recs : {qc.invalid_records}",
    ]

    if qc.issues:
        lines.append("")
        lines.append("--- Issues ---")
        for issue in qc.issues:
            lines.append(f"  * {issue}")

    if qc.s_records > 0 and qc.r_records > 0:
        r_per_shot = qc.r_records / qc.s_records
        ch_estimate = int(r_per_shot * 3)
        lines.append("")
        lines.append("--- Estimates ---")
        lines.append(f"R lines/shot : {r_per_shot:.1f}")
        lines.append(f"Channels est : ~{ch_estimate}")

    lines.extend(["", "=" * 60])
    return "\n".join(lines)


def generate_comparison_report(result: ComparisonResult) -> str:
    """Backward-compatible wrapper for comparison report export."""
    return format_comparison_report(result)
