"""Track plot and QC visualization.

Generates publication-quality track plots from P190 data with:
- Source track line with start/end markers
- Optional receiver spread overlay
- Scale bar and North arrow
- Dark theme matching GUI design
- Style A vs B comparison visualization
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for file output
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from ...models.shot_gather import ShotGatherCollection
from .comparison import ComparisonResult


# Dark theme colors
BG_COLOR = "#0a0e17"
TRACK_COLOR = "#06b6d4"
SOURCE_COLOR = "#ef4444"
RX_COLOR = "#3b82f6"
TEXT_COLOR = "#f1f5f9"
GRID_COLOR = "#1e293b"
SCALE_COLOR = "#94a3b8"


def generate_track_plot(
    collection: ShotGatherCollection,
    output_path: str,
    title: Optional[str] = None,
    show_receivers: bool = False,
    shot_interval: int = 10,
    dpi: int = 150,
    figsize: tuple = (12, 8),
) -> str:
    """Generate track plot image from ShotGatherCollection.

    Args:
        collection: Shot gather collection with source/receiver positions
        output_path: Path to save plot image (.png)
        title: Plot title (default: line name)
        show_receivers: Overlay receiver spread for sampled shots
        shot_interval: Show receiver spread every N shots
        dpi: Output resolution
        figsize: Figure size in inches

    Returns:
        Output image path
    """
    shots = collection.shots
    if not shots:
        raise ValueError("No shots to plot")

    fig, ax = plt.subplots(figsize=figsize, facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Style axes
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.3, linewidth=0.5)

    # Track data
    src_x = [s.source_x for s in shots]
    src_y = [s.source_y for s in shots]

    # Plot track
    ax.plot(src_x, src_y, '-', color=TRACK_COLOR,
            linewidth=1.2, alpha=0.8, zorder=2)

    # Start/End markers
    ax.plot(src_x[0], src_y[0], '*', color="#10b981",
            markersize=15, zorder=5, label="Start")
    ax.plot(src_x[-1], src_y[-1], 's', color="#f59e0b",
            markersize=10, zorder=5, label="End")

    # Receiver spread overlay
    if show_receivers:
        for i in range(0, len(shots), shot_interval):
            shot = shots[i]
            if shot.receivers:
                rx_x = [r.x for r in shot.receivers]
                rx_y = [r.y for r in shot.receivers]
                ax.plot(rx_x, rx_y, '.', color=RX_COLOR,
                        markersize=1, alpha=0.4, zorder=3)

    # Title
    plot_title = title or f"Track Plot - {collection.line_name}"
    ax.set_title(plot_title, color=TEXT_COLOR, fontsize=14, pad=12)
    ax.set_xlabel("Easting (m)", fontsize=10)
    ax.set_ylabel("Northing (m)", fontsize=10)

    # Legend
    ax.legend(fontsize=9, loc="upper left",
              facecolor=BG_COLOR, edgecolor=GRID_COLOR,
              labelcolor=TEXT_COLOR)

    # Equal aspect ratio
    ax.set_aspect("equal", adjustable="datalim")

    # Scale bar
    _add_scale_bar(ax, src_x, src_y)

    # North arrow
    _add_north_arrow(ax)

    # Info text
    n_shots = len(shots)
    n_ch = shots[0].n_channels if shots[0].receivers else 0
    ffid_lo, ffid_hi = collection.ffid_range
    info = (f"Shots: {n_shots:,}  |  Channels: {n_ch}  |  "
            f"FFID: {ffid_lo}-{ffid_hi}")
    ax.text(0.02, 0.02, info, transform=ax.transAxes,
            fontsize=8, color=SCALE_COLOR,
            verticalalignment="bottom")

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, facecolor=BG_COLOR,
                bbox_inches="tight")
    plt.close(fig)

    return output_path


def _add_scale_bar(ax, xs, ys):
    """Add a scale bar to the plot."""
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    data_range = max(x_range, y_range)

    # Choose nice scale bar length
    for length in [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]:
        if length > data_range * 0.15:
            bar_len = length
            break
    else:
        bar_len = int(data_range * 0.2)

    # Position in lower-right
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    bar_x = x_max - (x_max - x_min) * 0.05 - bar_len
    bar_y = y_min + (y_max - y_min) * 0.05

    ax.plot([bar_x, bar_x + bar_len], [bar_y, bar_y],
            '-', color=SCALE_COLOR, linewidth=2)
    ax.plot([bar_x, bar_x], [bar_y - (y_max - y_min) * 0.005,
                              bar_y + (y_max - y_min) * 0.005],
            '-', color=SCALE_COLOR, linewidth=1)
    ax.plot([bar_x + bar_len, bar_x + bar_len],
            [bar_y - (y_max - y_min) * 0.005,
             bar_y + (y_max - y_min) * 0.005],
            '-', color=SCALE_COLOR, linewidth=1)

    label = f"{bar_len} m" if bar_len < 1000 else f"{bar_len/1000:.1f} km"
    ax.text(bar_x + bar_len / 2, bar_y + (y_max - y_min) * 0.015,
            label, color=SCALE_COLOR, fontsize=8,
            ha="center", va="bottom")


def _add_north_arrow(ax):
    """Add a north arrow indicator."""
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    # Position in upper-right corner
    arrow_x = x_max - (x_max - x_min) * 0.05
    arrow_y = y_max - (y_max - y_min) * 0.12
    arrow_len = (y_max - y_min) * 0.06

    ax.annotate("N", xy=(arrow_x, arrow_y + arrow_len),
                fontsize=10, color=SCALE_COLOR, ha="center",
                fontweight="bold")
    ax.annotate("", xy=(arrow_x, arrow_y + arrow_len * 0.9),
                xytext=(arrow_x, arrow_y),
                arrowprops=dict(arrowstyle="->", color=SCALE_COLOR,
                                lw=1.5))


# -- Comparison Plot Colors --
COLOR_A = "#06b6d4"   # Cyan for Style A
COLOR_B = "#eab308"   # Gold for Style B
COLOR_A_RX = "#22d3ee"  # Light cyan for A receivers
COLOR_B_RX = "#facc15"  # Light gold for B receivers


def generate_comparison_plot(
    result: ComparisonResult,
    output_path: str,
    title: Optional[str] = None,
    zoom_ffid: Optional[int] = None,
    dpi: int = 150,
) -> str:
    """Generate Style A vs B comparison plot.

    3-panel layout:
      - Left: Full track overlay (A=cyan, B=gold)
      - Right: Zoomed shot with source + receiver fan comparison
      - Bottom: Statistics text panel

    Args:
        result: ComparisonResult from compare_p190_files()
        output_path: Path to save plot image (.png)
        title: Override title
        zoom_ffid: FFID to show in zoom panel (default: middle shot)
        dpi: Output resolution

    Returns:
        Output image path
    """
    positions = result.positions
    if not positions:
        raise ValueError("ComparisonResult has no position data for plotting")

    ffids = sorted(positions.keys())

    # Select zoom FFID (default: middle)
    if zoom_ffid is None or zoom_ffid not in positions:
        zoom_ffid = ffids[len(ffids) // 2]

    # Create figure with GridSpec
    fig = plt.figure(figsize=(18, 10), facecolor=BG_COLOR)
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1],
                          hspace=0.25, wspace=0.25)
    ax_track = fig.add_subplot(gs[0, 0])
    ax_zoom = fig.add_subplot(gs[0, 1])
    ax_stats = fig.add_subplot(gs[1, :])

    for ax in [ax_track, ax_zoom, ax_stats]:
        ax.set_facecolor(BG_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(GRID_COLOR)

    # ===== LEFT: Full Track Overlay =====
    ax_track.grid(True, color=GRID_COLOR, alpha=0.3, linewidth=0.5)

    src_a_x = [positions[f]["src_a"][0] for f in ffids]
    src_a_y = [positions[f]["src_a"][1] for f in ffids]
    src_b_x = [positions[f]["src_b"][0] for f in ffids]
    src_b_y = [positions[f]["src_b"][1] for f in ffids]

    # Plot tracks
    ax_track.plot(src_a_x, src_a_y, '-', color=COLOR_A,
                  linewidth=1.2, alpha=0.8, label="Style A (NPD GPS)", zorder=2)
    ax_track.plot(src_b_x, src_b_y, '-', color=COLOR_B,
                  linewidth=1.2, alpha=0.8, label="Style B (RadExPro)", zorder=2)

    # Start/End markers
    ax_track.plot(src_a_x[0], src_a_y[0], '*', color="#10b981",
                  markersize=12, zorder=5)
    ax_track.plot(src_a_x[-1], src_a_y[-1], 's', color="#f59e0b",
                  markersize=8, zorder=5)
    ax_track.plot(src_b_x[0], src_b_y[0], '*', color="#10b981",
                  markersize=12, zorder=5)

    # Receiver spread overlay (every 200 shots)
    step = max(1, len(ffids) // 40)
    for i in range(0, len(ffids), step):
        f = ffids[i]
        pos = positions[f]
        if pos.get("rx_a"):
            rx_ax = [r[0] for r in pos["rx_a"]]
            rx_ay = [r[1] for r in pos["rx_a"]]
            ax_track.plot(rx_ax, rx_ay, '-', color=COLOR_A_RX,
                          linewidth=0.3, alpha=0.3, zorder=1)
        if pos.get("rx_b"):
            rx_bx = [r[0] for r in pos["rx_b"]]
            rx_by = [r[1] for r in pos["rx_b"]]
            ax_track.plot(rx_bx, rx_by, '-', color=COLOR_B_RX,
                          linewidth=0.3, alpha=0.3, zorder=1)

    # Mark zoom shot
    zp = positions[zoom_ffid]
    ax_track.plot(zp["src_a"][0], zp["src_a"][1], 'o', color="#ef4444",
                  markersize=8, zorder=6, markeredgecolor="white",
                  markeredgewidth=1)

    ax_track.set_title("Full Track Overlay", color=TEXT_COLOR, fontsize=12, pad=8)
    ax_track.set_xlabel("Easting (m)", fontsize=9)
    ax_track.set_ylabel("Northing (m)", fontsize=9)
    ax_track.legend(fontsize=8, loc="upper left",
                    facecolor=BG_COLOR, edgecolor=GRID_COLOR,
                    labelcolor=TEXT_COLOR)
    ax_track.set_aspect("equal", adjustable="datalim")

    # Scale bar
    all_x = src_a_x + src_b_x
    all_y = src_a_y + src_b_y
    _add_scale_bar(ax_track, all_x, all_y)
    _add_north_arrow(ax_track)

    # ===== RIGHT: Zoomed Shot =====
    ax_zoom.grid(True, color=GRID_COLOR, alpha=0.3, linewidth=0.5)

    zp = positions[zoom_ffid]
    sa = zp["src_a"]
    sb = zp["src_b"]
    rx_a = zp.get("rx_a", [])
    rx_b = zp.get("rx_b", [])

    # Source markers
    ax_zoom.plot(sa[0], sa[1], 'D', color=COLOR_A, markersize=10,
                 zorder=5, label="Source A", markeredgecolor="white",
                 markeredgewidth=0.5)
    ax_zoom.plot(sb[0], sb[1], 'D', color=COLOR_B, markersize=10,
                 zorder=5, label="Source B", markeredgecolor="white",
                 markeredgewidth=0.5)

    # Source distance line
    dx = sa[0] - sb[0]
    dy = sa[1] - sb[1]
    dist = math.sqrt(dx * dx + dy * dy)
    ax_zoom.plot([sa[0], sb[0]], [sa[1], sb[1]], '--', color="#ef4444",
                 linewidth=1, alpha=0.8, zorder=4)
    mid_x = (sa[0] + sb[0]) / 2
    mid_y = (sa[1] + sb[1]) / 2
    ax_zoom.text(mid_x, mid_y, f"{dist:.1f}m", color="#ef4444",
                 fontsize=8, ha="center", va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", facecolor=BG_COLOR,
                           edgecolor="#ef4444", alpha=0.8))

    # Receiver fans
    if rx_a:
        rx_ax = [r[0] for r in rx_a]
        rx_ay = [r[1] for r in rx_a]
        ax_zoom.plot(rx_ax, rx_ay, 'o-', color=COLOR_A,
                     markersize=3, linewidth=1, alpha=0.7, label="RX A", zorder=3)
    if rx_b:
        rx_bx = [r[0] for r in rx_b]
        rx_by = [r[1] for r in rx_b]
        ax_zoom.plot(rx_bx, rx_by, 'o-', color=COLOR_B,
                     markersize=3, linewidth=1, alpha=0.7, label="RX B", zorder=3)

    # Heading arrows (short arrow from source showing heading direction)
    arrow_len = 8.0  # meters
    for src, heading, color, label_prefix in [
        (sa, zp.get("heading_a", 0), COLOR_A, "A"),
        (sb, zp.get("heading_b", 0), COLOR_B, "B"),
    ]:
        rad = math.radians(heading)
        end_x = src[0] + arrow_len * math.sin(rad)
        end_y = src[1] + arrow_len * math.cos(rad)
        ax_zoom.annotate("", xy=(end_x, end_y), xytext=(src[0], src[1]),
                         arrowprops=dict(arrowstyle="-|>", color=color,
                                         lw=2, mutation_scale=12),
                         zorder=6)

    # Spread direction labels
    if rx_a and rx_b:
        sd_a = zp.get("spread_dir_a", 0)
        sd_b = zp.get("spread_dir_b", 0)
        sd_diff = abs(((sd_a - sd_b + 180) % 360) - 180)

        ax_zoom.text(0.02, 0.98,
                     f"Spread A: {sd_a:.1f} deg\n"
                     f"Spread B: {sd_b:.1f} deg\n"
                     f"Diff: {sd_diff:.1f} deg",
                     transform=ax_zoom.transAxes,
                     fontsize=8, color=TEXT_COLOR,
                     verticalalignment="top",
                     bbox=dict(boxstyle="round,pad=0.4", facecolor=BG_COLOR,
                               edgecolor=GRID_COLOR, alpha=0.9))

    ax_zoom.set_title(f"FFID {zoom_ffid} Detail", color=TEXT_COLOR,
                      fontsize=12, pad=8)
    ax_zoom.set_xlabel("Easting (m)", fontsize=9)
    ax_zoom.set_ylabel("Northing (m)", fontsize=9)
    ax_zoom.legend(fontsize=7, loc="lower right",
                   facecolor=BG_COLOR, edgecolor=GRID_COLOR,
                   labelcolor=TEXT_COLOR)
    ax_zoom.set_aspect("equal", adjustable="datalim")

    # ===== BOTTOM: Statistics Panel =====
    ax_stats.axis("off")

    # Build statistics text
    stats_lines = [
        f"Common Shots: {result.n_common_shots:,}",
        "",
        "Source Position Diff:    "
        f"Mean={result.source_dist_mean:.2f}m  "
        f"Std={result.source_dist_std:.2f}m  "
        f"P95={result.source_dist_p95:.2f}m  "
        f"Max={result.source_dist_max:.2f}m",
    ]
    if result.n_channels > 0:
        stats_lines.append(
            f"Receiver Position Diff:  "
            f"Mean={result.rx_dist_mean:.2f}m  "
            f"Max={result.rx_dist_max:.2f}m  "
            f"({result.n_channels} channels)"
        )
    if result.heading_diff_mean != 0.0:
        stats_lines.append(
            f"Directional:             "
            f"Heading diff={result.heading_diff_mean:.1f} deg  "
            f"Spread A={result.spread_dir_a:.1f} deg  "
            f"Spread B={result.spread_dir_b:.1f} deg  "
            f"Feathering={abs(result.heading_diff_mean):.1f} deg"
        )

    # Assessment
    mean = result.source_dist_mean
    if mean < 3.0:
        grade = "EXCELLENT"
        grade_color = "#10b981"
    elif mean < 5.0:
        grade = "GOOD"
        grade_color = "#06b6d4"
    elif mean < 10.0:
        grade = "ACCEPTABLE"
        grade_color = "#f59e0b"
    else:
        grade = "POOR"
        grade_color = "#ef4444"

    stats_text = "\n".join(stats_lines)
    ax_stats.text(0.02, 0.85, stats_text,
                  transform=ax_stats.transAxes,
                  fontsize=10, color=TEXT_COLOR, fontfamily="monospace",
                  verticalalignment="top")
    ax_stats.text(0.02, 0.1, f"Assessment: {grade}",
                  transform=ax_stats.transAxes,
                  fontsize=13, color=grade_color, fontweight="bold",
                  verticalalignment="bottom")

    # Per-channel gradient bar (if available)
    if result.per_channel_df is not None and len(result.per_channel_df) > 1:
        ch_df = result.per_channel_df
        # Mini bar chart for per-channel mean distance
        bar_left = 0.55
        bar_width = 0.42
        bar_bottom = 0.15
        bar_height = 0.7
        ax_bar = fig.add_axes([bar_left, 0.02, bar_width, 0.12],
                              facecolor=BG_COLOR)
        ax_bar.tick_params(colors=TEXT_COLOR, labelsize=7)
        for spine in ax_bar.spines.values():
            spine.set_color(GRID_COLOR)

        channels = ch_df["channel"].values
        means = ch_df["mean_dist"].values
        colors = plt.cm.cool(np.linspace(0.2, 0.8, len(channels)))
        ax_bar.bar(channels, means, color=colors, width=0.8, alpha=0.8)
        ax_bar.set_xlabel("Channel", fontsize=7, color=TEXT_COLOR)
        ax_bar.set_ylabel("Mean dist (m)", fontsize=7, color=TEXT_COLOR)
        ax_bar.set_title("Per-Channel RX Distance", fontsize=8,
                         color=TEXT_COLOR, pad=4)

    # Main title
    plot_title = title or "Style A vs Style B P190 Comparison"
    fig.suptitle(plot_title, color=TEXT_COLOR, fontsize=16,
                 fontweight="bold", y=0.98)

    fig.savefig(output_path, dpi=dpi, facecolor=BG_COLOR,
                bbox_inches="tight")
    plt.close(fig)

    return output_path
