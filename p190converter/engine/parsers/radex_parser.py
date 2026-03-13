"""RadExPro header export TSV parser (Style B input).

Parses tab-separated files exported from RadExPro's Marine Geometry
with columns: FFID, SOU_X, SOU_Y, CHAN, REC_X, REC_Y, DAY, HOUR, MINUTE, SECOND
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd

from ...models.shot_gather import (
    ReceiverPosition,
    ShotGather,
    ShotGatherCollection,
)


def parse_radex_export(filepath: str) -> ShotGatherCollection:
    """Parse RadExPro header export TSV into ShotGatherCollection.

    Args:
        filepath: Path to tab-separated file with columns:
            FFID, SOU_X, SOU_Y, CHAN, REC_X, REC_Y, DAY, HOUR, MINUTE, SECOND

    Returns:
        ShotGatherCollection with all shots and receivers
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    df = pd.read_csv(filepath, sep="\t")

    # Normalize column names
    col_map = {}
    for col in df.columns:
        key = col.strip().upper()
        col_map[key] = col

    required = ["FFID", "SOU_X", "SOU_Y", "CHAN", "REC_X", "REC_Y"]
    for req in required:
        if req not in col_map:
            raise ValueError(f"Missing required column: {req}")

    # Rename to standard names
    rename = {col_map[k]: k for k in col_map}
    df = df.rename(columns=rename)

    # Group by FFID
    shots: List[ShotGather] = []
    n_channels = 0

    for ffid, group in df.groupby("FFID", sort=True):
        group = group.sort_values("CHAN")

        row0 = group.iloc[0]
        shot = ShotGather(
            ffid=int(ffid),
            source_x=float(row0["SOU_X"]),
            source_y=float(row0["SOU_Y"]),
        )

        # Time columns (optional)
        if "DAY" in df.columns:
            shot.day = int(row0["DAY"])
        if "HOUR" in df.columns:
            shot.hour = int(row0["HOUR"])
        if "MINUTE" in df.columns:
            shot.minute = int(row0["MINUTE"])
        if "SECOND" in df.columns:
            shot.second = int(row0["SECOND"])

        # Receivers
        for _, r in group.iterrows():
            shot.receivers.append(ReceiverPosition(
                channel=int(r["CHAN"]),
                x=float(r["REC_X"]),
                y=float(r["REC_Y"]),
            ))

        n_channels = max(n_channels, len(shot.receivers))
        shots.append(shot)

    collection = ShotGatherCollection(
        shots=shots,
        n_channels=n_channels,
    )
    return collection
