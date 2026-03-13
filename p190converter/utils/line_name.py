"""Line name auto-detection from file names.

Extracts survey line names from common naming conventions:
  - M + digits: M1406, M035, M002
  - Line + separator + name: Line021-1, Line_M1211
  - Fallback: first alphanumeric token resembling a line identifier
"""

import re
from pathlib import Path
from typing import Optional

# Patterns in priority order
_PATTERNS = [
    # M + digits (M1406, M035, M002)
    re.compile(r"(M\d{2,})"),
    # LINE + separator + name (Line021-1, Line_M1211)
    re.compile(r"(Line[_\-]?[\w\-]+)", re.IGNORECASE),
    # L + digits (L1406)
    re.compile(r"(L\d{3,})"),
    # Generic: leading letter + 3+ digits
    re.compile(r"\b([A-Z]\d{3,})\b", re.IGNORECASE),
]


def detect_line_name(filepath: str) -> Optional[str]:
    """Extract line name from file path.

    Scans the file stem (name without extension) for known patterns.
    Returns the first match, or None if no pattern found.

    Args:
        filepath: Path to any input file (NPD, Track, RadExPro export, etc.)

    Returns:
        Detected line name string, or None
    """
    stem = Path(filepath).stem

    for pattern in _PATTERNS:
        match = pattern.search(stem)
        if match:
            return match.group(1)

    return None
