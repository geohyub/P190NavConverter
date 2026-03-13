# -*- coding: utf-8 -*-
"""Comparison panel — Style A vs Style B P190 position comparison.

Wires the existing comparison engine (comparison.py + plot.py) into
an interactive GUI panel with file selection, embedded results, and export.
"""

import os
import threading
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog

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


class ComparisonPanel(ctk.CTkFrame):
    """Panel for Style A vs Style B P190 comparison."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._result = None
        self._style_a_path = ""
        self._style_b_path = ""
        self._log_callback = None
        self._build()

    def set_log_callback(self, callback):
        """Set logging callback: callback(level, message)."""
        self._log_callback = callback

    def _log(self, level, msg):
        if self._log_callback:
            self._log_callback(level, msg)

    def _build(self):
        """Build panel layout."""
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, SP["sm"]))

        title = ctk.CTkLabel(
            header,
            text="\U0001f50d  Style A vs B Comparison",
            font=font("h2", bold=True),
            text_color=COLORS["accent"],
        )
        title.pack(side="left")

        self._grade_label = ctk.CTkLabel(
            header,
            text="  Not compared  ",
            font=font("small", bold=True),
            text_color=COLORS["text_muted"],
            fg_color=COLORS["bg_elevated"],
            corner_radius=8,
        )
        self._grade_label.pack(side="left", padx=SP["md"])

        # Export button
        self._btn_export = ctk.CTkButton(
            header, text="\U0001f4ca Export Plot + Report",
            font=font("small"), width=180, height=28,
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            command=self._export_all,
        )
        self._btn_export.pack(side="right")

        # ── File selection row ──
        file_card = SectionCard(self, title="P190 Files")
        file_card.pack(fill="x", pady=(0, SP["sm"]))

        file_inner = ctk.CTkFrame(file_card, fg_color="transparent")
        file_inner.pack(fill="x", padx=SP["md"], pady=SP["sm"])

        # Style A file
        a_row = ctk.CTkFrame(file_inner, fg_color="transparent")
        a_row.pack(fill="x", pady=(0, SP["xs"]))

        ctk.CTkLabel(
            a_row, text="Style A:", font=font("body", bold=True),
            text_color=COLORS["accent"], width=70,
        ).pack(side="left")

        self._entry_a = ctk.CTkEntry(
            a_row, font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            placeholder_text="Select Style A P190 file...",
        )
        self._entry_a.pack(side="left", fill="x", expand=True, padx=SP["xs"])

        ctk.CTkButton(
            a_row, text="Browse", width=70, height=28,
            font=font("small"),
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            command=lambda: self._browse_file("a"),
        ).pack(side="left")

        # Style B file
        b_row = ctk.CTkFrame(file_inner, fg_color="transparent")
        b_row.pack(fill="x", pady=(0, SP["xs"]))

        ctk.CTkLabel(
            b_row, text="Style B:", font=font("body", bold=True),
            text_color=COLORS["accent_muted"], width=70,
        ).pack(side="left")

        self._entry_b = ctk.CTkEntry(
            b_row, font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            placeholder_text="Select Style B P190 file...",
        )
        self._entry_b.pack(side="left", fill="x", expand=True, padx=SP["xs"])

        ctk.CTkButton(
            b_row, text="Browse", width=70, height=28,
            font=font("small"),
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            command=lambda: self._browse_file("b"),
        ).pack(side="left")

        # Compare button
        btn_row = ctk.CTkFrame(file_inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(SP["xs"], 0))

        self._btn_compare = ctk.CTkButton(
            btn_row, text="\u25b6  Run Comparison",
            font=font("body", bold=True), height=36,
            fg_color=COLORS["button_primary"],
            hover_color=COLORS["button_hover"],
            text_color=COLORS["button_text"],
            command=self._run_comparison,
        )
        self._btn_compare.pack(side="left")

        self._compare_status = ctk.CTkLabel(
            btn_row, text="",
            font=font("small"),
            text_color=COLORS["text_muted"],
        )
        self._compare_status.pack(side="left", padx=SP["md"])

        # ── Stats row ──
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, SP["sm"]))

        self._stat_src = StatCard(
            stats_row, icon="\U0001f4cd", value="--",
            label="Source Mean Diff", accent_index=0,
        )
        self._stat_src.pack(side="left", fill="x", expand=True,
                            padx=(0, SP["xs"]))

        self._stat_rx = StatCard(
            stats_row, icon="\U0001f4e1", value="--",
            label="Receiver Mean Diff", accent_index=1,
        )
        self._stat_rx.pack(side="left", fill="x", expand=True,
                           padx=(0, SP["xs"]))

        self._stat_heading = StatCard(
            stats_row, icon="\U0001f9ed", value="--",
            label="Heading Diff", accent_index=2,
        )
        self._stat_heading.pack(side="left", fill="x", expand=True,
                                padx=(0, SP["xs"]))

        self._stat_shots = StatCard(
            stats_row, icon="\U0001f4ca", value="--",
            label="Common Shots", accent_index=3,
        )
        self._stat_shots.pack(side="left", fill="x", expand=True)

        # ── Report text ──
        report_card = SectionCard(self, title="Comparison Report")
        report_card.pack(fill="x", pady=(0, SP["sm"]))

        self._report_text = ctk.CTkTextbox(
            report_card,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            height=250,
            wrap="none",
        )
        self._report_text.pack(fill="x", padx=SP["sm"], pady=SP["sm"])

        # ── Per-channel table ──
        ch_card = SectionCard(self, title="Per-Channel Receiver Comparison")
        ch_card.pack(fill="x", pady=(0, SP["sm"]))

        self._channel_text = ctk.CTkTextbox(
            ch_card,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            height=200,
            wrap="none",
        )
        self._channel_text.pack(fill="x", padx=SP["sm"], pady=SP["sm"])

    def _browse_file(self, which: str):
        """Open file dialog for A or B P190 file."""
        path = filedialog.askopenfilename(
            title=f"Select Style {'A' if which == 'a' else 'B'} P190",
            filetypes=[("P190 files", "*.p190"), ("All files", "*.*")],
        )
        if path:
            entry = self._entry_a if which == "a" else self._entry_b
            entry.delete(0, "end")
            entry.insert(0, path)
            if which == "a":
                self._style_a_path = path
            else:
                self._style_b_path = path

    def set_file_paths(self, style_a: str = "", style_b: str = ""):
        """Pre-fill file paths (called from app after conversion)."""
        if style_a:
            self._style_a_path = style_a
            self._entry_a.delete(0, "end")
            self._entry_a.insert(0, style_a)
        if style_b:
            self._style_b_path = style_b
            self._entry_b.delete(0, "end")
            self._entry_b.insert(0, style_b)

    def _run_comparison(self):
        """Run comparison in background thread."""
        path_a = self._entry_a.get().strip() or self._style_a_path
        path_b = self._entry_b.get().strip() or self._style_b_path

        if not path_a or not path_b:
            self._compare_status.configure(
                text="Both P190 files required",
                text_color=COLORS["error"],
            )
            return

        self._compare_status.configure(
            text="Comparing...",
            text_color=COLORS["warning"],
        )
        self._btn_compare.configure(state="disabled")

        def _worker():
            try:
                from ...engine.qc.comparison import (
                    compare_p190_files, format_comparison_report,
                )
                result = compare_p190_files(path_a, path_b)
                self.after(0, self._on_comparison_done, result)
            except Exception as e:
                self.after(0, self._on_comparison_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_comparison_done(self, result):
        """Handle comparison completion."""
        self._result = result
        self._btn_compare.configure(state="normal")

        # Grade
        mean = result.source_dist_mean
        if mean < 3.0:
            grade, color = "EXCELLENT", COLORS["success"]
        elif mean < 5.0:
            grade, color = "GOOD", COLORS["accent"]
        elif mean < 10.0:
            grade, color = "ACCEPTABLE", COLORS["warning"]
        else:
            grade, color = "POOR", COLORS["error"]

        self._grade_label.configure(
            text=f"  {grade} ({mean:.2f}m)  ",
            text_color=color,
        )
        self._compare_status.configure(
            text=f"Done: {result.n_common_shots} common shots",
            text_color=COLORS["success"],
        )

        # Stats
        self._stat_src.set_value(value=f"{mean:.2f} m")
        self._stat_rx.set_value(
            value=f"{result.rx_dist_mean:.2f} m" if result.n_channels > 0 else "N/A"
        )
        self._stat_heading.set_value(value=f"{result.heading_diff_mean:.1f} deg")
        self._stat_shots.set_value(value=f"{result.n_common_shots:,}")

        # Report
        from ...engine.qc.comparison import format_comparison_report
        report = format_comparison_report(result)
        self._report_text.configure(state="normal")
        self._report_text.delete("1.0", "end")
        self._report_text.insert("1.0", report)
        self._report_text.configure(state="disabled")

        # Per-channel table
        if result.per_channel_df is not None:
            self._channel_text.configure(state="normal")
            self._channel_text.delete("1.0", "end")

            header = f"  {'CH':>4s}  {'Mean(m)':>8s}  {'Max(m)':>8s}  {'Std(m)':>8s}\n"
            self._channel_text.insert("end", header)
            self._channel_text.insert("end", "  " + "-" * 34 + "\n")

            for _, row in result.per_channel_df.iterrows():
                line = (
                    f"  {int(row['channel']):>4d}  "
                    f"{row['mean_dist']:8.3f}  "
                    f"{row['max_dist']:8.3f}  "
                    f"{row['std_dist']:8.3f}\n"
                )
                self._channel_text.insert("end", line)

            self._channel_text.configure(state="disabled")

        self._log("success", f"Comparison: {grade} (mean {mean:.2f}m)")

    def _on_comparison_error(self, error: str):
        """Handle comparison error."""
        self._btn_compare.configure(state="normal")
        self._compare_status.configure(
            text=f"Error: {error}",
            text_color=COLORS["error"],
        )
        self._log("error", f"Comparison failed: {error}")

    def _export_all(self):
        """Export comparison plot + report."""
        if not self._result:
            return

        path_a = self._entry_a.get().strip()
        out_dir = str(Path(path_a).parent) if path_a else os.getcwd()

        # Text report
        from ...engine.qc.comparison import format_comparison_report
        report = format_comparison_report(self._result)
        report_path = os.path.join(out_dir, "Style_AB_Comparison_Report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # Plot
        try:
            from ...engine.qc.plot import generate_comparison_plot
            plot_path = os.path.join(out_dir, "Style_AB_Comparison_Plot.png")
            generate_comparison_plot(self._result, plot_path)
            self._log("success", f"Comparison plot: {plot_path}")
        except Exception as e:
            self._log("warning", f"Plot generation failed: {e}")

        try:
            os.startfile(report_path)
        except Exception:
            pass
