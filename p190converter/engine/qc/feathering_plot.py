# -*- coding: utf-8 -*-
"""Feathering analysis visualization — comprehensive multi-panel plots.

Generates publication-quality dark-themed plots matching the GUI design.
All plots use the Agg backend for file output (PNG).

Panel layout:
  1. Feathering angle time series (+ turn detection markers)
  2. Cross-track displacement time series
  3. Vessel speed + estimated cross-current overlay
  4. Tow tension estimate
  5. Per-channel correction bar chart
  6. Alpha sensitivity + current direction rose

Output: Single PNG file with 6 panels.
"""

import math
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.gridspec import GridSpec
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from .feathering_analysis import FeatheringAnalysisResult

# ══════════════════════════════════════════════════════════════
# Theme — matches GUI Deep Navy + Electric Teal
# ══════════════════════════════════════════════════════════════
BG_COLOR = "#0a0e17"
PANEL_BG = "#111827"
GRID_COLOR = "#1e293b"
TEXT_COLOR = "#f1f5f9"
TEXT_MUTED = "#94a3b8"
ACCENT_CYAN = "#06b6d4"
ACCENT_TEAL = "#14b8a6"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"
ACCENT_GREEN = "#10b981"
ACCENT_PURPLE = "#8b5cf6"
ACCENT_GOLD = "#eab308"
DIVIDER = "#334155"


def _style_axis(ax, title="", xlabel="", ylabel=""):
    """Apply dark theme styling to axis."""
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, color=TEXT_COLOR, fontsize=10, fontweight="bold",
                 pad=6, loc="left")
    ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=8)
    ax.tick_params(colors=TEXT_MUTED, labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(DIVIDER)
    ax.spines["left"].set_color(DIVIDER)
    ax.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)


def generate_feathering_overview(
    result: FeatheringAnalysisResult,
    output_path: str,
    dpi: int = 150,
    line_name: str = "",
) -> str:
    """Generate comprehensive 6-panel feathering analysis plot.

    Args:
        result: FeatheringAnalysisResult from analysis engine
        output_path: Path to save PNG
        dpi: Output resolution
        line_name: Survey line name for title

    Returns:
        Path to saved PNG file
    """
    if not HAS_MPL:
        raise ImportError("matplotlib is required for feathering plots")

    fig = plt.figure(figsize=(18, 13), facecolor=BG_COLOR)
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.30,
                  left=0.06, right=0.97, top=0.93, bottom=0.05)

    # Title
    title = "FEATHERING ANALYSIS"
    if line_name:
        title += f" - {line_name}"
    fig.suptitle(title, color=ACCENT_CYAN, fontsize=14, fontweight="bold",
                 y=0.97)

    # Subtitle with cable info
    sub = (f"Cable: GeoEel Solid LH-16 (D=44.5mm) | "
           f"{result.n_channels}ch x {result.rx_interval}m = {result.total_spread}m spread | "
           f"{result.n_shots:,} shots")
    fig.text(0.5, 0.945, sub, color=TEXT_MUTED, fontsize=9, ha="center")

    # X-axis: shot index
    x = result.shot_indices
    turn_mask = result.is_turning

    # ── Panel 1: Feathering Angle (top-left, spans 2 cols) ──
    ax1 = fig.add_subplot(gs[0, :2])
    _style_axis(ax1, "Feathering Angle", "Shot Index", "Angle (deg)")

    # Plot clean and turning shots differently
    ax1.plot(x, result.feathering_angle, color=ACCENT_CYAN,
             linewidth=0.5, alpha=0.8, label="Feathering")

    # Mark turning shots
    if turn_mask.any():
        ax1.scatter(x[turn_mask], result.feathering_angle[turn_mask],
                    color=ACCENT_RED, s=3, alpha=0.6, zorder=3,
                    label=f"Turning ({turn_mask.sum()})")

    # Mean line
    clean = ~turn_mask
    if clean.any():
        mean_fa = np.mean(result.feathering_angle[clean])
        ax1.axhline(mean_fa, color=ACCENT_AMBER, linewidth=1,
                     linestyle="--", alpha=0.7, label=f"Mean: {mean_fa:+.1f} deg")

    ax1.axhline(0, color=TEXT_MUTED, linewidth=0.5, alpha=0.3)
    ax1.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=DIVIDER,
               labelcolor=TEXT_COLOR, loc="upper right")

    # ── Panel 2: Statistics Summary (top-right) ──
    ax_stats = fig.add_subplot(gs[0, 2])
    ax_stats.set_facecolor(PANEL_BG)
    ax_stats.set_xlim(0, 1)
    ax_stats.set_ylim(0, 1)
    ax_stats.axis("off")

    s = result.stats
    stat_lines = [
        ("FEATHERING", "", True),
        ("Mean |angle|", f"{s['feathering_abs_mean']:.2f} deg", False),
        ("Max |angle|", f"{max(abs(s['feathering_min']), abs(s['feathering_max'])):.2f} deg", False),
        ("Dominant drift", "STBD" if s['cross_track_mean'] > 0 else "PORT", False),
        ("", "", False),
        ("VESSEL", "", True),
        ("Mean speed", f"{s['vessel_speed_mean_knots']:.2f} knots", False),
        ("Turning shots", f"{s['n_shots_turning']} ({s['turn_pct']:.1f}%)", False),
        ("", "", False),
        ("CROSS-CURRENT (est.)", "", True),
        ("Mean speed", f"{s['current_speed_mean']:.3f} m/s ({s['current_speed_mean_knots']:.2f} kn)", False),
        ("Max speed", f"{s['current_speed_max']:.3f} m/s", False),
        ("", "", False),
        ("TOW TENSION (est.)", "", True),
        ("Mean", f"{s['tension_mean_N']:.1f} N ({s['tension_mean_N']/9.81:.1f} kgf)", False),
        ("", "", False),
        ("CORRECTION (alpha=2)", "", True),
        ("Mean all ch", f"{s['correction_mean_all']:.3f} m", False),
        ("Max all ch", f"{s['correction_max_all']:.3f} m", False),
    ]

    y_pos = 0.96
    for label, value, is_header in stat_lines:
        if not label and not value:
            y_pos -= 0.025
            continue
        if is_header:
            ax_stats.text(0.05, y_pos, label, color=ACCENT_CYAN,
                          fontsize=8, fontweight="bold",
                          transform=ax_stats.transAxes)
        else:
            ax_stats.text(0.08, y_pos, label, color=TEXT_MUTED,
                          fontsize=7, transform=ax_stats.transAxes)
            ax_stats.text(0.95, y_pos, value, color=TEXT_COLOR,
                          fontsize=7, ha="right",
                          transform=ax_stats.transAxes)
        y_pos -= 0.047

    # ── Panel 3: Cross-track displacement (middle-left, spans 2 cols) ──
    ax2 = fig.add_subplot(gs[1, :2])
    _style_axis(ax2, "Cross-Track Displacement (Tail vs Head)",
                "Shot Index", "Displacement (m)")

    ax2.fill_between(x, 0, result.cross_track_disp,
                     where=result.cross_track_disp >= 0,
                     color=ACCENT_TEAL, alpha=0.3, label="Starboard drift")
    ax2.fill_between(x, 0, result.cross_track_disp,
                     where=result.cross_track_disp < 0,
                     color=ACCENT_PURPLE, alpha=0.3, label="Port drift")
    ax2.plot(x, result.cross_track_disp, color=TEXT_COLOR,
             linewidth=0.5, alpha=0.6)
    ax2.axhline(0, color=TEXT_MUTED, linewidth=0.5, alpha=0.3)
    ax2.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=DIVIDER,
               labelcolor=TEXT_COLOR, loc="upper right")

    # ── Panel 4: Vessel speed + Current speed (middle-right) ──
    ax3 = fig.add_subplot(gs[1, 2])
    _style_axis(ax3, "Vessel Speed & Current (est.)",
                "Shot Index", "Speed (knots)")

    ax3.plot(x, result.vessel_speed_knots, color=ACCENT_CYAN,
             linewidth=0.8, alpha=0.8, label="Vessel speed")
    ax3.plot(x, result.current_speed * 1.94384, color=ACCENT_RED,
             linewidth=0.6, alpha=0.6, label="Cross-current (est.)")

    ax3.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=DIVIDER,
               labelcolor=TEXT_COLOR, loc="upper right")

    # ── Panel 5: Per-channel correction (bottom-left) ──
    ax4 = fig.add_subplot(gs[2, 0])
    _style_axis(ax4, "Per-Channel Correction (alpha=2.0)",
                "Channel", "Correction (m)")

    channels = np.arange(1, result.n_channels + 1)
    colors_ch = plt.cm.cool(np.linspace(0.2, 0.8, result.n_channels))

    ax4.bar(channels, result.channel_correction_mean,
            color=colors_ch, alpha=0.8, width=0.7, label="Mean")
    ax4.bar(channels, result.channel_correction_max,
            color="none", edgecolor=ACCENT_AMBER, linewidth=0.8,
            width=0.7, alpha=0.5, label="Max")

    ax4.set_xticks(channels)
    ax4.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=DIVIDER,
               labelcolor=TEXT_COLOR)

    # ── Panel 6: Alpha sensitivity (bottom-center) ──
    ax5 = fig.add_subplot(gs[2, 1])
    _style_axis(ax5, "Alpha Sensitivity",
                "Alpha", "Mean Correction (m)")

    alphas = sorted(result.alpha_sensitivity.keys())
    corrections = [result.alpha_sensitivity[a] for a in alphas]

    ax5.bar(range(len(alphas)), corrections,
            color=[ACCENT_GREEN if a == 2.0 else ACCENT_CYAN
                   for a in alphas],
            alpha=0.8, width=0.6)
    ax5.set_xticks(range(len(alphas)))
    ax5.set_xticklabels([f"{a:.1f}" for a in alphas])

    # Annotate alpha=2.0
    for i, (a, c) in enumerate(zip(alphas, corrections)):
        ax5.text(i, c + 0.02, f"{c:.3f}",
                 color=TEXT_COLOR, fontsize=7, ha="center", va="bottom")

    # ── Panel 7: Tow tension time series (bottom-right) ──
    ax6 = fig.add_subplot(gs[2, 2])
    _style_axis(ax6, "Tow Tension Estimate (drag model)",
                "Shot Index", "Tension (N)")

    ax6.plot(x, result.tow_tension_estimate, color=ACCENT_AMBER,
             linewidth=0.6, alpha=0.8)
    ax6.fill_between(x, 0, result.tow_tension_estimate,
                     color=ACCENT_AMBER, alpha=0.15)

    # Mean tension line
    mean_t = result.stats.get("tension_mean_N", 0)
    ax6.axhline(mean_t, color=ACCENT_RED, linewidth=0.8,
                linestyle="--", alpha=0.6,
                label=f"Mean: {mean_t:.1f} N")
    ax6.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=DIVIDER,
               labelcolor=TEXT_COLOR)

    # Save
    output = Path(output_path)
    fig.savefig(str(output), dpi=dpi, facecolor=BG_COLOR)
    plt.close(fig)

    return str(output)


def generate_feathering_detail(
    result: FeatheringAnalysisResult,
    output_path: str,
    shot_idx: Optional[int] = None,
    dpi: int = 150,
    line_name: str = "",
) -> str:
    """Generate detailed single-shot feathering diagram.

    Shows cable shape, receiver positions (linear vs feathering),
    vessel heading, current arrow, and correction vectors.
    If shot_idx is None, uses the shot with maximum cross-track displacement.

    Args:
        result: FeatheringAnalysisResult
        output_path: PNG output path
        shot_idx: Shot index (0-based), or None for max-feathering shot
        dpi: Resolution
        line_name: Line name for title

    Returns:
        Path to saved PNG
    """
    if not HAS_MPL:
        raise ImportError("matplotlib required")

    # Select shot
    if shot_idx is None:
        clean = ~result.is_turning
        if clean.any():
            clean_ct = np.abs(result.cross_track_disp.copy())
            clean_ct[~clean] = 0
            shot_idx = int(np.argmax(clean_ct))
        else:
            shot_idx = int(np.argmax(np.abs(result.cross_track_disp)))

    i = shot_idx
    he, hn = result.head_east[i], result.head_north[i]
    te, tn = result.tail_east[i], result.tail_north[i]
    cog = result.vessel_cog[i]
    fa = result.feathering_angle[i]
    ct = result.cross_track_disp[i]
    chord = result.cable_chord[i]
    v_speed = result.vessel_speed_knots[i]
    c_speed = result.current_speed[i]
    tension = result.tow_tension_estimate[i]

    # Figure
    fig, ax = plt.subplots(1, 1, figsize=(10, 10), facecolor=BG_COLOR)
    ax.set_facecolor(PANEL_BG)
    ax.set_aspect("equal")

    title = f"SHOT #{i}"
    if result.ffids is not None and len(result.ffids) > i:
        title += f"  (FFID: {int(result.ffids[i])})"
    if line_name:
        title = f"{line_name} - {title}"
    ax.set_title(title, color=ACCENT_CYAN, fontsize=12, fontweight="bold",
                 pad=10)

    # ── Draw cable (Head → Tail) ──
    ax.plot([he, te], [hn, tn], color=TEXT_MUTED, linewidth=1.5,
            linestyle="--", alpha=0.5, label="Cable chord (straight)")

    # Head and Tail buoys
    ax.scatter([he], [hn], color=ACCENT_GREEN, s=100, zorder=5,
               marker="^", label="Head Buoy")
    ax.scatter([te], [tn], color=ACCENT_RED, s=100, zorder=5,
               marker="v", label="Tail Buoy")

    # ── Vessel heading arrow ──
    arrow_len = chord * 0.3
    cog_rad = math.radians(cog)
    vh_de = arrow_len * math.sin(cog_rad)
    vh_dn = arrow_len * math.cos(cog_rad)
    ax.annotate("", xy=(he + vh_de, hn + vh_dn), xytext=(he, hn),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT_AMBER,
                                lw=2, mutation_scale=15))
    ax.text(he + vh_de * 1.15, hn + vh_dn * 1.15,
            f"COG {cog:.1f}deg", color=ACCENT_AMBER, fontsize=8,
            ha="center", va="center")

    # ── Simulated cable curve (quadratic feathering model) ──
    if chord > 0.1 and abs(ct) > 0.1:
        # Cable direction unit vectors
        cable_ux = (te - he) / chord
        cable_uy = (tn - hn) / chord
        # Cross-tow direction
        cross_e = math.cos(cog_rad)
        cross_n = -math.sin(cog_rad)

        t_vals = np.linspace(0, 1, 50)
        curve_e = []
        curve_n = []
        for t in t_vals:
            # Linear position + quadratic correction
            base_e = he + cable_ux * chord * t
            base_n = hn + cable_uy * chord * t
            # Power-law cross displacement (alpha=2)
            cross_at_t = ct * (t ** 2 - t)
            curve_e.append(base_e + cross_at_t * cross_e)
            curve_n.append(base_n + cross_at_t * cross_n)

        ax.plot(curve_e, curve_n, color=ACCENT_CYAN, linewidth=2,
                alpha=0.9, label="Feathering model (alpha=2)")

        # ── Receiver positions (on the curve) ──
        for ch in range(result.n_channels):
            dist = result.rx_interval * ch
            t = dist / chord
            t = min(t, 1.5)
            base_e_ch = he + cable_ux * chord * t
            base_n_ch = hn + cable_uy * chord * t
            cross_ch = ct * (t ** 2 - t)
            rx_e = base_e_ch + cross_ch * cross_e
            rx_n = base_n_ch + cross_ch * cross_n

            # Linear position for comparison
            lin_e = he + cable_ux * chord * t
            lin_n = hn + cable_uy * chord * t

            # Correction arrow
            if ch % 4 == 0 or ch == result.n_channels - 1:
                ax.plot([lin_e, rx_e], [lin_n, rx_n],
                        color=ACCENT_PURPLE, linewidth=0.8, alpha=0.5)

            ax.scatter([rx_e], [rx_n], color=ACCENT_CYAN, s=20,
                       zorder=4, alpha=0.8)

            if ch == 0 or ch == result.n_channels - 1:
                ax.annotate(f"CH{ch+1}", (rx_e, rx_n),
                            textcoords="offset points", xytext=(8, 5),
                            color=TEXT_COLOR, fontsize=7)

    # ── Current direction arrow ──
    c_dir = result.current_direction[i]
    c_rad = math.radians(c_dir)
    c_arrow_len = chord * 0.25
    mid_e = (he + te) / 2
    mid_n = (hn + tn) / 2
    c_de = c_arrow_len * math.sin(c_rad)
    c_dn = c_arrow_len * math.cos(c_rad)
    ax.annotate("", xy=(mid_e + c_de, mid_n + c_dn),
                xytext=(mid_e, mid_n),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT_PURPLE,
                                lw=2.5, mutation_scale=18))
    ax.text(mid_e + c_de * 1.3, mid_n + c_dn * 1.3,
            f"Current\n{c_speed:.3f} m/s", color=ACCENT_PURPLE,
            fontsize=8, ha="center", va="center",
            fontweight="bold")

    # ── Info box ──
    info_text = (
        f"Feathering: {fa:+.2f} deg\n"
        f"Cross-track: {ct:+.2f} m\n"
        f"Cable chord: {chord:.1f} m\n"
        f"Vessel speed: {v_speed:.2f} knots\n"
        f"Current (est.): {c_speed:.3f} m/s\n"
        f"Tension (est.): {tension:.1f} N"
    )
    props = dict(boxstyle="round,pad=0.5", facecolor=BG_COLOR,
                 edgecolor=DIVIDER, alpha=0.9)
    ax.text(0.02, 0.02, info_text, transform=ax.transAxes,
            fontsize=8, color=TEXT_COLOR, verticalalignment="bottom",
            fontfamily="monospace", bbox=props)

    ax.legend(fontsize=8, facecolor=PANEL_BG, edgecolor=DIVIDER,
              labelcolor=TEXT_COLOR, loc="upper right")

    ax.set_xlabel("Easting (m)", color=TEXT_MUTED, fontsize=9)
    ax.set_ylabel("Northing (m)", color=TEXT_MUTED, fontsize=9)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(DIVIDER)
    ax.spines["left"].set_color(DIVIDER)

    # Auto-margin
    margin = chord * 0.15
    all_e = [he, te]
    all_n = [hn, tn]
    ax.set_xlim(min(all_e) - margin - chord * 0.3,
                max(all_e) + margin + chord * 0.3)
    ax.set_ylim(min(all_n) - margin - chord * 0.3,
                max(all_n) + margin + chord * 0.3)

    fig.savefig(str(output_path), dpi=dpi, facecolor=BG_COLOR,
                bbox_inches="tight")
    plt.close(fig)

    return str(output_path)
