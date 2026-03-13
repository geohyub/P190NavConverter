"""R Record (Receiver Group) formatter for P190.

80-column fixed-width format. 3 receiver groups per line:
  Col  1     : "R"
  Col  2-27  : Group 1 — CH#(I4) + Easting(F9.1) + Northing(F9.1) + Depth(F4.1)
  Col 28-53  : Group 2 (same format)
  Col 54-79  : Group 3 (same format)
  Col 80     : Streamer/Cable ID (1 char)

Each group = 26 chars:
  - Channel number:  4 chars (I4, right-justified)
  - Easting:         9 chars (F9.1)
  - Northing:        9 chars (F9.1)
  - Depth:           4 chars (F4.1)
"""

import math
from typing import List

from ...models.shot_gather import ReceiverPosition, ShotGather


def _format_receiver_group(rx: ReceiverPosition) -> str:
    """Format a single receiver as a 26-char group.

    Returns:
        26-character string: CH#(4) + E(9) + N(9) + D(4)
    """
    ch_str = f"{rx.channel:4d}"
    e_str = f"{rx.x:9.1f}"
    n_str = f"{rx.y:9.1f}"

    if rx.depth > 0:
        d_str = f"{rx.depth:4.1f}"
    else:
        d_str = "    "

    group = ch_str + e_str + n_str + d_str
    assert len(group) == 26, f"Group length {len(group)} != 26"
    return group


def format_r_records(shot: ShotGather, streamer_id: str = "1") -> List[str]:
    """Format all receivers for a shot as R record lines.

    3 receivers per line. 48 channels = 16 R lines.

    Args:
        shot: ShotGather with populated receivers
        streamer_id: Single character streamer/cable ID

    Returns:
        List of 80-character R record strings
    """
    lines = []
    receivers = shot.receivers
    n = len(receivers)

    # Process 3 receivers per line
    for i in range(0, n, 3):
        groups = []
        for j in range(3):
            idx = i + j
            if idx < n:
                groups.append(_format_receiver_group(receivers[idx]))
            else:
                # Pad empty group with spaces (26 chars)
                groups.append(" " * 26)

        record = "R" + "".join(groups) + streamer_id[0]
        assert len(record) == 80, f"R record length {len(record)} != 80"
        lines.append(record)

    return lines
