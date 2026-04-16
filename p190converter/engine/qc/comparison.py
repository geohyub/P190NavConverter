"""Style A vs Style B P190 comparison utility.

Compares source and receiver positions from two P190 files (same line,
different conversion methods) to quantify interpolation accuracy.
Matches shots by FFID (truncated to 6-digit P190 format) and computes
position differences for sources and per-channel receivers.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


ASSESSMENT_BANDS = (
    (
        "EXCELLENT",
        3.0,
        "Source positions align very closely. Current source basis and offsets look stable.",
    ),
    (
        "GOOD",
        5.0,
        "Difference is small for most delivery/QC uses. Review only if a tighter reference match is required.",
    ),
    (
        "ACCEPTABLE",
        10.0,
        "Comparison is usable, but the source basis, CRS, or offset setup should be reviewed before delivery.",
    ),
    (
        "POOR",
        float("inf"),
        "Differences are large. Check source basis, GPS selection, CRS, and geometry settings before delivery.",
    ),
)


def _assessment_from_mean(mean_dist: float) -> tuple[str, str]:
    """Return comparison grade and explanation from source mean difference."""
    for grade, limit, note in ASSESSMENT_BANDS:
        if mean_dist < limit:
            return grade, note
    return ASSESSMENT_BANDS[-1][0], ASSESSMENT_BANDS[-1][2]


@dataclass
class ComparisonResult:
    """Result of comparing two P190 files."""
    # Source statistics
    n_common_shots: int
    source_dist_mean: float     # Mean source position difference (m)
    source_dist_max: float      # Max source position difference (m)
    source_dist_p95: float      # 95th percentile (m)
    source_dist_std: float      # Standard deviation (m)
    per_shot_df: pd.DataFrame   # Per-shot detail: ffid, dx, dy, dist

    # Receiver statistics (optional, populated when R records exist)
    n_channels: int = 0
    rx_dist_mean: float = 0.0
    rx_dist_max: float = 0.0
    per_channel_df: Optional[pd.DataFrame] = None  # channel, mean_dist, max_dist

    # Heading / spread direction
    heading_diff_mean: float = 0.0       # Mean heading difference (degrees)
    spread_dir_a: float = 0.0            # Style A mean spread direction (degrees)
    spread_dir_b: float = 0.0            # Style B mean spread direction (degrees)

    # Position data for plotting {ffid: {"src_a": (x,y), "src_b": (x,y),
    #   "rx_a": [(x,y),...], "rx_b": [(x,y),...], "heading_a": deg, "heading_b": deg}}
    positions: Dict = field(default_factory=dict)

    @property
    def matched_shots(self) -> int:
        """Backward-compatible alias used by older UI/tests."""
        return self.n_common_shots

    @property
    def source_mean_diff(self) -> float:
        return self.source_dist_mean

    @property
    def source_max_diff(self) -> float:
        return self.source_dist_max

    @property
    def receiver_mean_diff(self) -> float:
        return self.rx_dist_mean

    @property
    def source_diffs(self) -> List[float]:
        if self.per_shot_df is None or self.per_shot_df.empty:
            return []
        if "source_dist" in self.per_shot_df.columns:
            return self.per_shot_df["source_dist"].tolist()
        return self.per_shot_df["dist"].tolist()

    @property
    def grade(self) -> str:
        return _assessment_from_mean(self.source_dist_mean)[0]

    @property
    def assessment_note(self) -> str:
        return _assessment_from_mean(self.source_dist_mean)[1]

    @property
    def has_receivers(self) -> bool:
        return self.n_channels > 0 and self.per_channel_df is not None

    def worst_shots(self, count: int = 5) -> pd.DataFrame:
        """Return the shots with the largest source differences."""
        if self.per_shot_df is None or self.per_shot_df.empty:
            return pd.DataFrame(columns=["ffid", "source_dist", "dx", "dy"])
        dist_col = "source_dist" if "source_dist" in self.per_shot_df.columns else "dist"
        return (
            self.per_shot_df.sort_values(dist_col, ascending=False)
            .head(count)
            .reset_index(drop=True)
        )

    @property
    def worst_ffid(self) -> int | None:
        """Return the FFID with the largest source difference."""
        worst = self.worst_shots(1)
        if worst.empty:
            return None
        return int(worst.iloc[0]["ffid"])

    def channel_deltas_for_ffid(self, ffid: int) -> pd.DataFrame:
        """Return per-channel delta details for a selected shot."""
        pos = self.positions.get(ffid)
        if not pos:
            return pd.DataFrame(columns=["channel", "dx", "dy", "dist"])

        rx_a = pos.get("rx_a", [])
        rx_b = pos.get("rx_b", [])
        if not rx_a or not rx_b:
            return pd.DataFrame(columns=["channel", "dx", "dy", "dist"])

        rows = []
        for channel, (ra, rb) in enumerate(zip(rx_a, rx_b), start=1):
            dx = ra[0] - rb[0]
            dy = ra[1] - rb[1]
            rows.append(
                {
                    "channel": channel,
                    "dx": dx,
                    "dy": dy,
                    "dist": math.hypot(dx, dy),
                }
            )
        return pd.DataFrame(rows)


def _parse_p190_records(filepath: Union[str, Path]) -> Tuple[pd.DataFrame, Dict]:
    """Extract source + receiver positions from P190 S and R records.

    S Record layout (0-indexed):
      [0]     : 'S'
      [19:25] : FFID (6 chars)
      [46:55] : Easting (F9.1)
      [55:64] : Northing (F9.1)

    R Record layout (0-indexed):
      [0]     : 'R'
      No FFID — follows preceding S record.
      3 receiver groups per line, each 26 chars:
        CH#(I4) + Easting(F9.1) + Northing(F9.1) + Depth(F4.1)
      Group 1: [1:27], Group 2: [27:53], Group 3: [53:79]
      [79]    : Streamer ID

    Returns:
        (s_df, rx_dict)
        s_df: DataFrame with columns: ffid, easting, northing
        rx_dict: {ffid: [(easting, northing), ...]} ordered by channel
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"P190 file not found: {filepath}")

    s_records = []
    rx_dict: Dict[int, List[Tuple[float, float]]] = {}
    current_ffid = None
    current_source: Tuple[float, float] | None = None
    current_rx: List[Tuple[float, float]] = []
    seen_sources: Dict[int, Tuple[float, float]] = {}
    seen_rx: Dict[int, List[Tuple[float, float]]] = {}

    def finalize_current_shot() -> None:
        nonlocal current_ffid, current_source, current_rx
        if current_ffid is None or current_source is None:
            return

        previous = seen_sources.get(current_ffid)
        if previous is None:
            seen_sources[current_ffid] = current_source
            seen_rx[current_ffid] = list(current_rx)
            s_records.append({
                "ffid": current_ffid,
                "easting": current_source[0],
                "northing": current_source[1],
            })
            rx_dict[current_ffid] = list(current_rx)
            return

        same_source = (
            math.isclose(previous[0], current_source[0], abs_tol=0.05)
            and math.isclose(previous[1], current_source[1], abs_tol=0.05)
        )
        if not same_source:
            raise ValueError(
                "Duplicate S record FFID with conflicting source "
                f"coordinates detected: {current_ffid}"
            )

        if seen_rx[current_ffid] != current_rx:
            raise ValueError(
                "Duplicate S record FFID with conflicting receiver "
                f"geometry detected: {current_ffid}"
            )

        current_ffid = None
        current_source = None
        current_rx = []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            padded = line.rstrip().ljust(80)

            if line.startswith("S"):
                finalize_current_shot()
                try:
                    ffid = int(padded[19:25].strip())
                    easting = float(padded[46:55].strip())
                    northing = float(padded[55:64].strip())
                except (ValueError, IndexError):
                    current_ffid = None
                    current_source = None
                    current_rx = []
                    continue

                current_ffid = ffid
                current_source = (easting, northing)
                current_rx = []

            elif line.startswith("R") and current_ffid is not None:
                try:
                    # 3 groups per line, each 26 chars starting at offset 1
                    for j in range(3):
                        grp_start = 1 + j * 26
                        grp = padded[grp_start:grp_start + 26]

                        ch_str = grp[0:4].strip()
                        e_str = grp[4:13].strip()
                        n_str = grp[13:22].strip()

                        if ch_str and e_str and n_str:
                            current_rx.append(
                                (float(e_str), float(n_str))
                            )
                except (ValueError, IndexError):
                    continue

            elif not line.startswith("R"):
                # Non-R, non-S line resets current FFID tracking
                if not line.startswith("H"):
                    finalize_current_shot()
                    current_ffid = None
                    current_source = None
                    current_rx = []

    finalize_current_shot()

    s_df = pd.DataFrame(s_records)
    return s_df, rx_dict


def _parse_s_records(filepath: Union[str, Path]) -> pd.DataFrame:
    """Backward-compatible helper that returns only parsed S records."""
    s_df, _ = _parse_p190_records(filepath)
    return s_df


def _compute_spread_direction(src_x, src_y, rx_list):
    """Compute spread direction from source to last receiver (degrees from north)."""
    if not rx_list:
        return 0.0
    last_rx = rx_list[-1]
    dx = last_rx[0] - src_x
    dy = last_rx[1] - src_y
    angle = math.degrees(math.atan2(dx, dy)) % 360
    return angle


def _compute_heading(src_x, src_y, rx_list):
    """Compute heading from source to first receiver (degrees from north)."""
    if not rx_list:
        return 0.0
    first_rx = rx_list[0]
    dx = first_rx[0] - src_x
    dy = first_rx[1] - src_y
    angle = math.degrees(math.atan2(dx, dy)) % 360
    return angle


def compare_p190_files(
    style_a_path: Union[str, Path],
    style_b_path: Union[str, Path],
) -> ComparisonResult:
    """Compare source and receiver positions between two P190 files.

    Matches shots by FFID (6-digit). Computes Euclidean distances and
    directional analysis for both sources and receivers.

    Args:
        style_a_path: Path to Style A P190 file
        style_b_path: Path to Style B P190 file

    Returns:
        ComparisonResult with statistics, per-shot/channel details, and position data
    """
    s_a, rx_a = _parse_p190_records(style_a_path)
    s_b, rx_b = _parse_p190_records(style_b_path)

    if s_a.empty or s_b.empty:
        raise ValueError("One or both P190 files contain no S records")

    # Merge sources on FFID
    merged = pd.merge(
        s_a, s_b,
        on="ffid",
        suffixes=("_a", "_b"),
        how="inner",
    )

    if merged.empty:
        raise ValueError(
            f"No common FFIDs found. "
            f"Style A: {len(s_a)} shots (FFID {s_a['ffid'].min()}-{s_a['ffid'].max()}), "
            f"Style B: {len(s_b)} shots (FFID {s_b['ffid'].min()}-{s_b['ffid'].max()})"
        )

    # Source differences
    merged["dx"] = merged["easting_a"] - merged["easting_b"]
    merged["dy"] = merged["northing_a"] - merged["northing_b"]
    merged["dist"] = np.sqrt(merged["dx"] ** 2 + merged["dy"] ** 2)
    per_shot = merged[
        [
            "ffid",
            "easting_a",
            "northing_a",
            "easting_b",
            "northing_b",
            "dx",
            "dy",
            "dist",
        ]
    ].copy()
    per_shot = per_shot.rename(
        columns={
            "easting_a": "source_x_a",
            "northing_a": "source_y_a",
            "easting_b": "source_x_b",
            "northing_b": "source_y_b",
            "dist": "source_dist",
        }
    )
    per_shot["dist"] = per_shot["source_dist"]

    # -- Receiver comparison --
    n_channels = 0
    rx_dist_mean = 0.0
    rx_dist_max = 0.0
    per_channel_df = None
    heading_diffs = []
    spread_dirs_a = []
    spread_dirs_b = []
    positions = {}

    common_ffids = merged["ffid"].tolist()
    ffids_with_rx = [f for f in common_ffids if f in rx_a and f in rx_b]

    if ffids_with_rx:
        # Determine channel count from first common shot
        n_channels = min(len(rx_a[ffids_with_rx[0]]),
                         len(rx_b[ffids_with_rx[0]]))

        # Per-channel distance accumulation
        channel_dists = {ch: [] for ch in range(n_channels)}

        for ffid in ffids_with_rx:
            rxs_a = rx_a[ffid]
            rxs_b = rx_b[ffid]
            n_ch = min(len(rxs_a), len(rxs_b), n_channels)

            # Source positions for this FFID
            row = merged[merged["ffid"] == ffid].iloc[0]
            src_a = (row["easting_a"], row["northing_a"])
            src_b = (row["easting_b"], row["northing_b"])

            # Heading and spread direction
            h_a = _compute_heading(src_a[0], src_a[1], rxs_a)
            h_b = _compute_heading(src_b[0], src_b[1], rxs_b)
            sd_a = _compute_spread_direction(src_a[0], src_a[1], rxs_a)
            sd_b = _compute_spread_direction(src_b[0], src_b[1], rxs_b)

            # Circular difference
            h_diff = (h_a - h_b + 180) % 360 - 180
            heading_diffs.append(h_diff)
            spread_dirs_a.append(sd_a)
            spread_dirs_b.append(sd_b)

            # Per-channel distances
            for ch in range(n_ch):
                dx = rxs_a[ch][0] - rxs_b[ch][0]
                dy = rxs_a[ch][1] - rxs_b[ch][1]
                channel_dists[ch].append(math.sqrt(dx * dx + dy * dy))

            # Store position data for plotting
            positions[ffid] = {
                "src_a": src_a,
                "src_b": src_b,
                "rx_a": rxs_a[:n_ch],
                "rx_b": rxs_b[:n_ch],
                "heading_a": h_a,
                "heading_b": h_b,
                "spread_dir_a": sd_a,
                "spread_dir_b": sd_b,
            }

        # Per-channel statistics
        ch_stats = []
        all_rx_dists = []
        for ch in range(n_channels):
            dists = channel_dists[ch]
            if dists:
                ch_stats.append({
                    "channel": ch + 1,
                    "mean_dist": np.mean(dists),
                    "max_dist": np.max(dists),
                    "std_dist": np.std(dists),
                })
                all_rx_dists.extend(dists)

        per_channel_df = pd.DataFrame(ch_stats) if ch_stats else None

        if all_rx_dists:
            rx_dist_mean = float(np.mean(all_rx_dists))
            rx_dist_max = float(np.max(all_rx_dists))

    # Mean heading/spread
    heading_diff_mean = float(np.mean(heading_diffs)) if heading_diffs else 0.0
    spread_dir_a_mean = float(np.mean(spread_dirs_a)) if spread_dirs_a else 0.0
    spread_dir_b_mean = float(np.mean(spread_dirs_b)) if spread_dirs_b else 0.0

    return ComparisonResult(
        n_common_shots=len(merged),
        source_dist_mean=float(merged["dist"].mean()),
        source_dist_max=float(merged["dist"].max()),
        source_dist_p95=float(np.percentile(merged["dist"], 95)),
        source_dist_std=float(merged["dist"].std(ddof=0)),
        per_shot_df=per_shot,
        n_channels=n_channels,
        rx_dist_mean=rx_dist_mean,
        rx_dist_max=rx_dist_max,
        per_channel_df=per_channel_df,
        heading_diff_mean=heading_diff_mean,
        spread_dir_a=spread_dir_a_mean,
        spread_dir_b=spread_dir_b_mean,
        positions=positions,
    )


def format_comparison_report(result: ComparisonResult) -> str:
    """Format comparison result as human-readable text report."""
    grade, note = _assessment_from_mean(result.source_dist_mean)
    lines = [
        "=" * 60,
        "Style A vs Style B Position Comparison",
        "=" * 60,
        f"Common shots matched: {result.n_common_shots:,}",
        "",
        "Source Position Difference (meters):",
        f"  Mean: {result.source_dist_mean:.2f} m",
        f"  Std:  {result.source_dist_std:.2f} m",
        f"  P95:  {result.source_dist_p95:.2f} m",
        f"  Max:  {result.source_dist_max:.2f} m",
    ]

    # Receiver stats
    if result.n_channels > 0:
        lines.extend([
            "",
            f"Receiver Position Difference ({result.n_channels} channels):",
            f"  Mean: {result.rx_dist_mean:.2f} m",
            f"  Max:  {result.rx_dist_max:.2f} m",
        ])
    else:
        lines.extend([
            "",
            "Receiver Position Difference:",
            "  Not available because one or both files do not contain comparable R records.",
        ])

    # Heading / Spread
    if result.heading_diff_mean != 0.0:
        lines.extend([
            "",
            "Directional Analysis:",
            f"  Heading diff (A-B):  {result.heading_diff_mean:.1f} deg",
            f"  Spread dir A (mean): {result.spread_dir_a:.1f} deg",
            f"  Spread dir B (mean): {result.spread_dir_b:.1f} deg",
            f"  Feathering angle:    {abs(result.heading_diff_mean):.1f} deg",
        ])

    lines.extend([
        "",
        f"Assessment: {grade}",
        note,
        "=" * 60,
    ])

    return "\n".join(lines)
