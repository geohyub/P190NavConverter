# -*- coding: utf-8 -*-
"""Feathering Analysis panel — comprehensive cable dynamics dashboard.

Shows real-time feathering analysis after Style A conversion:
  - Embedded matplotlib overview plot
  - Statistics summary cards
  - Export buttons for report + plots
  - Detail shot viewer
"""

import copy
import os
import threading
from pathlib import Path
from typing import Dict, Optional

import customtkinter as ctk

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard, StatCard

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class FeatheringPanel(ctk.CTkFrame):
    """Panel for feathering analysis visualization and export."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._analysis_result = None
        self._output_dir = None
        self._line_name = ""
        self._survey_config = None
        self._track_data = None
        self._build()

    def _build(self):
        """Build panel layout."""
        # ── Header row ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, SP["sm"]))

        title = ctk.CTkLabel(
            header,
            text="\U0001f30a  Feathering Analysis",
            font=font("h2", bold=True),
            text_color=COLORS["accent"],
        )
        title.pack(side="left")

        # Status indicator
        self._status_label = ctk.CTkLabel(
            header,
            text="  No analysis data  ",
            font=font("small"),
            text_color=COLORS["text_muted"],
            fg_color=COLORS["bg_elevated"],
            corner_radius=8,
        )
        self._status_label.pack(side="left", padx=SP["md"])

        # ── Main content: Scrollable ──
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["divider"],
        )
        self._scroll.pack(fill="both", expand=True)

        # ── Export Actions ──
        export_card = SectionCard(self._scroll, title="Export Actions")
        export_card.pack(fill="x", pady=(0, SP["sm"]))

        export_inner = ctk.CTkFrame(export_card, fg_color="transparent")
        export_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # 4-column grid for export buttons
        for i in range(4):
            export_inner.columnconfigure(i, weight=1)

        btn_defs = [
            ("\U0001f4c4 Export Report",
             "Feathering text analysis report (.txt)",
             self._export_report),
            ("\U0001f4ca Export Plot",
             "6-panel overview plot (.png)",
             self._export_overview_plot),
            ("\U0001f50d Detail Shot",
             "Max feathering shot detail (.png)",
             self._export_detail_plot),
            ("\U0001f3af Corrected P190",
             "Feathering-corrected receiver P190",
             self._export_corrected_p190),
        ]

        for col, (text, desc, cmd) in enumerate(btn_defs):
            btn = ctk.CTkButton(
                export_inner, text=text,
                font=font("small"), height=32,
                fg_color=COLORS["bg_elevated"],
                hover_color=COLORS["sidebar_hover"],
                text_color=COLORS["text_primary"],
                command=cmd,
            )
            btn.grid(row=0, column=col, padx=SP["xs"], pady=(0, 2),
                     sticky="ew")

            lbl = ctk.CTkLabel(
                export_inner, text=desc,
                font=font("small"),
                text_color=COLORS["text_muted"],
            )
            lbl.grid(row=1, column=col, padx=SP["xs"], pady=(0, SP["xs"]),
                     sticky="ew")

        # ── Stats row (4 cards) ──
        stats_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, SP["sm"]))

        self._stat_feathering = StatCard(
            stats_row, icon="\U0001f4d0", value="--",
            label="Mean |Feathering|", accent_index=0,
        )
        self._stat_feathering.pack(side="left", fill="x", expand=True,
                                   padx=(0, SP["xs"]))

        self._stat_crosstrack = StatCard(
            stats_row, icon="\u2194\ufe0f", value="--",
            label="Mean |Cross-track|", accent_index=1,
        )
        self._stat_crosstrack.pack(side="left", fill="x", expand=True,
                                   padx=(0, SP["xs"]))

        self._stat_current = StatCard(
            stats_row, icon="\U0001f30a", value="--",
            label="Est. Current", accent_index=2,
        )
        self._stat_current.pack(side="left", fill="x", expand=True,
                                padx=(0, SP["xs"]))

        self._stat_correction = StatCard(
            stats_row, icon="\u2699\ufe0f", value="--",
            label="Mean Correction", accent_index=3,
        )
        self._stat_correction.pack(side="left", fill="x", expand=True)

        # ── Plot area ──
        plot_card = SectionCard(self._scroll, title="Feathering Overview")
        plot_card.pack(fill="x", pady=(0, SP["sm"]))

        self._plot_frame = ctk.CTkFrame(plot_card, fg_color=COLORS["bg_primary"],
                                        height=520)
        self._plot_frame.pack(fill="x", padx=SP["sm"], pady=SP["sm"])
        self._plot_frame.pack_propagate(False)

        if HAS_MPL:
            self._fig = Figure(figsize=(16, 7), facecolor="#0a0e17")
            self._canvas = FigureCanvasTkAgg(self._fig, master=self._plot_frame)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            no_mpl = ctk.CTkLabel(
                self._plot_frame,
                text="matplotlib not available",
                font=font("body"),
                text_color=COLORS["text_muted"],
            )
            no_mpl.pack(expand=True)

        # ── Report text area ──
        report_card = SectionCard(self._scroll, title="Analysis Report")
        report_card.pack(fill="x", pady=(0, SP["sm"]))

        self._report_text = ctk.CTkTextbox(
            report_card,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            height=300,
            wrap="none",
        )
        self._report_text.pack(fill="x", padx=SP["sm"], pady=SP["sm"])

        # ── Physical variables info ──
        phys_card = SectionCard(self._scroll, title="Physical Variables (GeoEel LH-16)")
        phys_card.pack(fill="x", pady=(0, SP["sm"]))

        phys_text = ctk.CTkTextbox(
            phys_card,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_secondary"],
            height=120,
            wrap="none",
        )
        phys_text.pack(fill="x", padx=SP["sm"], pady=SP["sm"])
        phys_text.insert("1.0", (
            "  Cable Model:     GeoEel Solid LH-16\n"
            "  Cable Diameter:  44.5 mm (polyurethane solid)\n"
            "  Cable Weight:    ~1.56 kg/m (neutrally buoyant)\n"
            "  Tow Cable:       18.5 mm Kevlar, 0.5 kg/m\n"
            "  Drag Coeff (Cd): 1.1 (smooth cylinder, Re~10^3-10^4)\n"
            "  Water Density:   1025 kg/m^3\n"
            "\n"
            "  Variables Reflected in Analysis:\n"
            "    - Cross-current: estimated from tan(feathering) x vessel_speed\n"
            "    - Vessel speed: from GPS trajectory (central difference)\n"
            "    - Tow tension: 0.5 * rho * Cd * D * V^2 * L (drag model)\n"
            "    - Cable curvature: power-law cross(t) = C_total * t^alpha\n"
            "    - Turn detection: COG rate > 2 deg/s threshold\n"
            "    - Current direction: perpendicular to vessel heading\n"
        ))
        phys_text.configure(state="disabled")

    def set_analysis_result(
        self,
        result,
        output_dir: str = "",
        line_name: str = "",
        survey_config=None,
        track_data: Optional[Dict] = None,
    ):
        """Update panel with new feathering analysis result.

        Args:
            result: FeatheringAnalysisResult
            output_dir: Directory for export files
            line_name: Survey line name
            survey_config: SurveyConfig for corrected P190 output
            track_data: dict with head/tail GPS + vessel_cog arrays
        """
        self._analysis_result = result
        self._output_dir = output_dir
        self._line_name = line_name
        self._survey_config = survey_config
        self._track_data = track_data

        if result is None:
            self._status_label.configure(
                text="  No analysis data  ",
                text_color=COLORS["text_muted"],
            )
            return

        s = result.stats

        # Update status
        abs_mean = s["feathering_abs_mean"]
        if abs_mean < 5:
            grade_text = "MINIMAL"
            grade_color = COLORS["success"]
        elif abs_mean < 15:
            grade_text = "MODERATE"
            grade_color = COLORS["accent"]
        elif abs_mean < 30:
            grade_text = "SIGNIFICANT"
            grade_color = COLORS["warning"]
        else:
            grade_text = "SEVERE"
            grade_color = COLORS["error"]

        self._status_label.configure(
            text=f"  {grade_text} ({abs_mean:.1f} deg)  ",
            text_color=grade_color,
        )

        # Update stat cards
        self._stat_feathering.set_value(value=f"{abs_mean:.2f} deg")
        self._stat_crosstrack.set_value(value=f"{s['cross_track_abs_mean']:.2f} m")
        self._stat_current.set_value(
            value=f"{s['current_speed_mean_knots']:.2f} kn"
        )
        self._stat_correction.set_value(value=f"{s['correction_mean_all']:.3f} m")

        # Update report
        from ...engine.qc.feathering_analysis import generate_feathering_report
        report = generate_feathering_report(result)
        self._report_text.configure(state="normal")
        self._report_text.delete("1.0", "end")
        self._report_text.insert("1.0", report)
        self._report_text.configure(state="disabled")

        # Update embedded plot
        if HAS_MPL:
            self._update_embedded_plot(result)

    def _update_embedded_plot(self, result):
        """Draw the overview plot on the embedded canvas."""
        self._fig.clear()

        # Use compact 2x3 layout for embedded view
        gs = self._fig.add_gridspec(2, 3, hspace=0.40, wspace=0.30,
                                    left=0.06, right=0.97,
                                    top=0.92, bottom=0.08)

        from ...engine.qc.feathering_plot import (
            _style_axis, ACCENT_CYAN, ACCENT_TEAL, ACCENT_PURPLE,
            ACCENT_AMBER, ACCENT_RED, ACCENT_GREEN, TEXT_COLOR, TEXT_MUTED,
            PANEL_BG, DIVIDER, BG_COLOR,
        )
        import numpy as np

        x = result.shot_indices
        turn = result.is_turning
        clean = ~turn

        # Panel 1: Feathering angle
        ax1 = self._fig.add_subplot(gs[0, 0])
        _style_axis(ax1, "Feathering Angle", "", "deg")
        ax1.plot(x, result.feathering_angle, color=ACCENT_CYAN,
                 linewidth=0.5, alpha=0.8)
        if turn.any():
            ax1.scatter(x[turn], result.feathering_angle[turn],
                        color=ACCENT_RED, s=2, alpha=0.5)
        if clean.any():
            m = float(np.mean(result.feathering_angle[clean]))
            ax1.axhline(m, color=ACCENT_AMBER, linewidth=0.8,
                        linestyle="--", alpha=0.6)
        ax1.axhline(0, color=TEXT_MUTED, linewidth=0.3, alpha=0.3)

        # Panel 2: Cross-track displacement
        ax2 = self._fig.add_subplot(gs[0, 1])
        _style_axis(ax2, "Cross-Track Disp.", "", "m")
        ax2.fill_between(x, 0, result.cross_track_disp,
                         where=result.cross_track_disp >= 0,
                         color=ACCENT_TEAL, alpha=0.3)
        ax2.fill_between(x, 0, result.cross_track_disp,
                         where=result.cross_track_disp < 0,
                         color=ACCENT_PURPLE, alpha=0.3)
        ax2.plot(x, result.cross_track_disp, color=TEXT_COLOR,
                 linewidth=0.4, alpha=0.5)
        ax2.axhline(0, color=TEXT_MUTED, linewidth=0.3)

        # Panel 3: Vessel speed
        ax3 = self._fig.add_subplot(gs[0, 2])
        _style_axis(ax3, "Vessel Speed & Current", "", "knots")
        ax3.plot(x, result.vessel_speed_knots, color=ACCENT_CYAN,
                 linewidth=0.6, alpha=0.8, label="Vessel")
        ax3.plot(x, result.current_speed * 1.94384, color=ACCENT_RED,
                 linewidth=0.4, alpha=0.5, label="Current")
        ax3.legend(fontsize=6, facecolor=PANEL_BG, edgecolor=DIVIDER,
                   labelcolor=TEXT_COLOR)

        # Panel 4: Per-channel correction
        ax4 = self._fig.add_subplot(gs[1, 0])
        _style_axis(ax4, "Per-Channel Correction", "Channel", "m")
        import matplotlib.pyplot as plt
        chs = np.arange(1, result.n_channels + 1)
        colors = plt.cm.cool(np.linspace(0.2, 0.8, result.n_channels))
        ax4.bar(chs, result.channel_correction_mean,
                color=colors, alpha=0.8, width=0.7)
        ax4.set_xticks(chs)

        # Panel 5: Alpha sensitivity
        ax5 = self._fig.add_subplot(gs[1, 1])
        _style_axis(ax5, "Alpha Sensitivity", "Alpha", "m")
        alphas = sorted(result.alpha_sensitivity.keys())
        corrs = [result.alpha_sensitivity[a] for a in alphas]
        ax5.bar(range(len(alphas)), corrs,
                color=[ACCENT_GREEN if a == 2.0 else ACCENT_CYAN
                       for a in alphas],
                alpha=0.8, width=0.6)
        ax5.set_xticks(range(len(alphas)))
        ax5.set_xticklabels([f"{a:.1f}" for a in alphas], fontsize=6)

        # Panel 6: Tension
        ax6 = self._fig.add_subplot(gs[1, 2])
        _style_axis(ax6, "Tow Tension (est.)", "", "N")
        ax6.plot(x, result.tow_tension_estimate, color=ACCENT_AMBER,
                 linewidth=0.5, alpha=0.8)
        ax6.fill_between(x, 0, result.tow_tension_estimate,
                         color=ACCENT_AMBER, alpha=0.1)

        self._canvas.draw()

    def _export_report(self):
        """Export text report to file."""
        if not self._analysis_result:
            return

        from ...engine.qc.feathering_analysis import generate_feathering_report
        report = generate_feathering_report(self._analysis_result)

        out_dir = self._output_dir or os.getcwd()
        fname = f"{self._line_name}_Feathering_Report.txt" if self._line_name else "Feathering_Report.txt"
        path = os.path.join(out_dir, fname)

        with open(path, "w", encoding="utf-8") as f:
            f.write(report)

        # Open file
        try:
            os.startfile(path)
        except Exception:
            pass

    def _export_overview_plot(self):
        """Export 6-panel overview PNG."""
        if not self._analysis_result:
            return

        from ...engine.qc.feathering_plot import generate_feathering_overview

        out_dir = self._output_dir or os.getcwd()
        fname = f"{self._line_name}_Feathering_Overview.png" if self._line_name else "Feathering_Overview.png"
        path = os.path.join(out_dir, fname)

        generate_feathering_overview(
            self._analysis_result, path,
            line_name=self._line_name,
        )

        try:
            os.startfile(path)
        except Exception:
            pass

    def _export_detail_plot(self):
        """Export detail shot PNG (max feathering shot)."""
        if not self._analysis_result:
            return

        from ...engine.qc.feathering_plot import generate_feathering_detail

        out_dir = self._output_dir or os.getcwd()
        fname = f"{self._line_name}_Feathering_Detail.png" if self._line_name else "Feathering_Detail.png"
        path = os.path.join(out_dir, fname)

        generate_feathering_detail(
            self._analysis_result, path,
            line_name=self._line_name,
        )

        try:
            os.startfile(path)
        except Exception:
            pass

    def _export_corrected_p190(self):
        """Export feathering-corrected P190 with updated receiver positions."""
        if not self._analysis_result:
            return
        if not self._survey_config or not self._track_data:
            return

        import numpy as np
        from ...engine.geometry.interpolation import interpolate_receivers_feathering
        from ...engine.writer.p190_writer import P190Writer
        from ...models.shot_gather import ShotGather, ShotGatherCollection

        result = self._analysis_result
        config = self._survey_config
        td = self._track_data

        # Build corrected shot collection
        corrected_shots = []
        n = len(result.ffids)
        geometry = config.geometry

        for i in range(n):
            ffid = int(result.ffids[i])

            # Source position from track data
            src_x = float(td["source_x"][i]) if "source_x" in td else float(td["head_east"][i])
            src_y = float(td["source_y"][i]) if "source_y" in td else float(td["head_north"][i])

            # GPS positions for feathering correction
            head_x = float(td["head_east"][i])
            head_y = float(td["head_north"][i])
            tail_x = float(td["tail_east"][i])
            tail_y = float(td["tail_north"][i])
            vessel_cog = float(td["vessel_cog"][i])

            # Cable heading from head to tail
            cable_heading = float(np.degrees(
                np.arctan2(tail_x - head_x, tail_y - head_y)
            )) % 360

            # Feathering-corrected receiver interpolation
            receivers = interpolate_receivers_feathering(
                source_x=src_x,
                source_y=src_y,
                cable_heading_deg=cable_heading,
                geometry=geometry,
                head_x=head_x, head_y=head_y,
                tail_x=tail_x, tail_y=tail_y,
                vessel_heading_deg=vessel_cog,
                feathering_alpha=getattr(geometry, "feathering_alpha", 2.0),
            )

            shot = ShotGather(
                ffid=ffid,
                source_x=src_x,
                source_y=src_y,
                receivers=receivers,
                heading=vessel_cog,
                line_name=config.line_name,
            )

            # Copy time fields if available
            if "day" in td:
                shot.day = int(td["day"][i])
            if "hour" in td:
                shot.hour = int(td["hour"][i])
            if "minute" in td:
                shot.minute = int(td["minute"][i])
            if "second" in td:
                shot.second = int(td["second"][i])

            corrected_shots.append(shot)

        collection = ShotGatherCollection(
            shots=corrected_shots,
            line_name=config.line_name,
            n_channels=geometry.n_channels,
        )

        # Write corrected P190
        out_dir = self._output_dir or os.getcwd()
        fname = (f"{self._line_name}_Corrected.p190"
                 if self._line_name else "Corrected.p190")
        path = os.path.join(out_dir, fname)

        writer = P190Writer()
        writer.write(collection, config, path)

        try:
            os.startfile(path)
        except Exception:
            pass
