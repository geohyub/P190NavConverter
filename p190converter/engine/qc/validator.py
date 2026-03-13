"""P190 output validation."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class QCResult:
    """QC validation result."""
    total_lines: int = 0
    h_records: int = 0
    s_records: int = 0
    r_records: int = 0
    line_length_errors: int = 0
    invalid_records: int = 0
    issues: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.line_length_errors == 0 and self.invalid_records == 0


def validate_p190(filepath: str) -> QCResult:
    """Validate a P190 file for format compliance.

    Checks:
    - All lines are exactly 80 characters
    - Record types are H, S, R, or X
    - S/R record counts are consistent
    """
    result = QCResult()

    with open(filepath, "r", encoding="ascii") as f:
        lines = f.readlines()

    s_count = 0
    r_count_per_shot = []
    current_r_count = 0

    for i, line in enumerate(lines, 1):
        line = line.rstrip("\n").rstrip("\r")
        result.total_lines += 1

        if len(line) != 80:
            result.line_length_errors += 1
            if result.line_length_errors <= 5:
                result.issues.append(
                    f"Line {i}: length={len(line)}, expected 80"
                )

        if not line:
            continue

        rec_type = line[0]
        if rec_type == "H":
            result.h_records += 1
        elif rec_type == "S":
            result.s_records += 1
            if s_count > 0 and current_r_count > 0:
                r_count_per_shot.append(current_r_count)
            current_r_count = 0
            s_count += 1
        elif rec_type == "R":
            result.r_records += 1
            current_r_count += 1
        elif rec_type == "X":
            pass  # Format guide line
        else:
            result.invalid_records += 1
            result.issues.append(
                f"Line {i}: invalid record type '{rec_type}'"
            )

    # Last shot's R records
    if current_r_count > 0:
        r_count_per_shot.append(current_r_count)

    # Check R record consistency
    if r_count_per_shot:
        unique_counts = set(r_count_per_shot)
        if len(unique_counts) > 1:
            result.issues.append(
                f"Inconsistent R records per shot: {unique_counts}"
            )

    return result
