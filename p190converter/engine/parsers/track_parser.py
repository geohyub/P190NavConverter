"""RadExPro Track export TSV parser for Style A input."""

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd


@dataclass
class TrackData:
    """Parsed Track file data with one row per unique shot."""

    df: pd.DataFrame
    n_shots: int
    n_channels: int
    ffid_range: Tuple[int, int]
    time_range: Tuple[float, float]
    warnings: List[str] = field(default_factory=list)


REQUIRED_COLUMNS = ["FFID", "SOU_X", "SOU_Y", "DAY", "HOUR", "MINUTE", "SECOND"]
OPTIONAL_COLUMNS = ["TRACENO", "CHAN", "REC_X", "REC_Y", "DIRECTION"]
SHOT_IDENTITY_COLUMNS = ["SOU_X", "SOU_Y", "DAY", "HOUR", "MINUTE", "SECOND"]


def _find_conflicting_duplicate_ffids(df: pd.DataFrame) -> list[int]:
    """Return FFIDs whose duplicate rows disagree on shot-defining fields.

    Track exports often repeat FFIDs across channels. That is fine when the
    repeated rows describe the same shot/time/source position. It is *not*
    fine when duplicate FFIDs disagree on those core fields, because grouping
    with ``first()`` would silently pick one geometry story and hide the
    inconsistency.
    """
    if "FFID" not in df.columns:
        return []

    duplicate_mask = df.duplicated(subset=["FFID"], keep=False)
    if not duplicate_mask.any():
        return []

    conflicts: list[int] = []
    subset = df.loc[duplicate_mask, ["FFID", *SHOT_IDENTITY_COLUMNS]].copy()
    for ffid, group in subset.groupby("FFID", sort=True):
        signatures = group[SHOT_IDENTITY_COLUMNS].drop_duplicates()
        if len(signatures) > 1:
            conflicts.append(int(ffid))
    return conflicts


def parse_track_file(filepath: Union[str, Path]) -> TrackData:
    """Parse a tab-separated Track export."""

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Track file not found: {filepath}")

    df = pd.read_csv(filepath, sep="\t")

    col_map = {}
    for col in df.columns:
        col_map[col.strip().upper()] = col

    missing = [req for req in REQUIRED_COLUMNS if req not in col_map]
    if missing:
        found = list(col_map.keys())
        raise ValueError(
            "Track file is missing required columns: "
            f"{', '.join(missing)}\n"
            f"Required: {', '.join(REQUIRED_COLUMNS)}\n"
            f"Found: {', '.join(found)}"
        )

    warn_list = []
    known = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS)
    unrecognized = [key for key in col_map if key not in known]
    if unrecognized:
        msg = f"Unrecognized columns ignored: {', '.join(unrecognized)}"
        warnings.warn(msg)
        warn_list.append(msg)

    rename = {source: normalized for normalized, source in col_map.items()}
    df = df.rename(columns=rename)

    conflicts = _find_conflicting_duplicate_ffids(df)
    if conflicts:
        sample = ", ".join(str(ffid) for ffid in conflicts[:5])
        raise ValueError(
            "Conflicting duplicate FFID rows detected in Track file. "
            "A single FFID should not map to multiple shot times/source "
            f"positions. FFID(s): {sample}"
        )

    n_channels = 0
    if "CHAN" in df.columns:
        df["CHAN"] = pd.to_numeric(df["CHAN"], errors="coerce")
        channel_counts = (
            df.dropna(subset=["CHAN"])
            .groupby("FFID")["CHAN"]
            .nunique()
        )
        if not channel_counts.empty:
            n_channels = int(channel_counts.max())
            min_channels = int(channel_counts.min())
            if min_channels != n_channels:
                msg = (
                    "Track file channel count is not constant across FFIDs: "
                    f"{min_channels}-{n_channels}"
                )
                warnings.warn(msg)
                warn_list.append(msg)

    df_unique = df.groupby("FFID", sort=True).first().reset_index()

    df_unique["time_seconds"] = (
        df_unique["HOUR"].astype(float) * 3600
        + df_unique["MINUTE"].astype(float) * 60
        + df_unique["SECOND"].astype(float)
    )

    df_unique = df_unique.sort_values("time_seconds").reset_index(drop=True)

    diffs = df_unique["time_seconds"].diff()
    crossing = diffs < -43200
    if crossing.any():
        crossing_idx = crossing.idxmax()
        df_unique.loc[crossing_idx:, "time_seconds"] += 86400
        df_unique = df_unique.sort_values("time_seconds").reset_index(drop=True)
        msg = "Midnight crossing detected. Time rollover correction applied."
        warnings.warn(msg)
        warn_list.append(msg)

    out = pd.DataFrame({
        "ffid": df_unique["FFID"].astype(int),
        "sou_x": df_unique["SOU_X"].astype(float),
        "sou_y": df_unique["SOU_Y"].astype(float),
        "day": df_unique["DAY"].astype(int),
        "hour": df_unique["HOUR"].astype(int),
        "minute": df_unique["MINUTE"].astype(int),
        "second": df_unique["SECOND"].astype(float).astype(int),
        "time_seconds": df_unique["time_seconds"],
    })

    return TrackData(
        df=out,
        n_shots=len(out),
        n_channels=n_channels,
        ffid_range=(int(out["ffid"].min()), int(out["ffid"].max())),
        time_range=(float(out["time_seconds"].min()), float(out["time_seconds"].max())),
        warnings=warn_list,
    )
