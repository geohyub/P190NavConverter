"""H Record (Header) formatter for P190.

Each H record is exactly 80 characters, padded with spaces.
Format: H + 4-digit code + content (padded to 80 chars total)
"""

from typing import Dict, List

from ...models.survey_config import HRecordConfig


def format_h_records(config: HRecordConfig) -> List[str]:
    """Format all H records as 80-char lines.

    Returns:
        List of 80-character H record strings
    """
    lines = []
    for code in sorted(config.records.keys()):
        content = config.records[code]
        # H + code(4) + space + content = pad to 80
        line = f"{code} {content}"
        line = line.ljust(80)[:80]
        lines.append(line)
    return lines
