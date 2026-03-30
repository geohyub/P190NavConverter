"""FeatheringPanel — Cable dynamics analysis with matplotlib charts (Style A only)."""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.stat_card import StatCard

MPL_BG = "#0a0e17"
MPL_FG = "#94a3b8"


class FeatheringPanel(QWidget):
    """Feathering analysis: angle, displacement, alpha sensitivity."""

    panel_title = "Feathering"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._out_dir = ""
        self._line_name = ""
        self._survey_config = None
        self._track_data = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # Banner
        banner = QLabel("  Style A \uc804\uc6a9 -- \ucf00\uc774\ube14 \ub3d9\uc5ed\ud559 \ubd84\uc11d")
        banner.setFixedHeight(32)
        banner.setStyleSheet(f"""
            background: rgba(6,182,212,0.1);
            color: #06B6D4;
            border: 1px solid rgba(6,182,212,0.3);
            border-radius: {Radius.SM}px;
            font-size: {Font.SM}px;
            padding-left: 8px;
        """)
        layout.addWidget(banner)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(Space.SM)
        self._stat_angle = StatCard("\ud3c9\uade0 |\uac01\ub3c4|", "--", 0)
        self._stat_current = StatCard("\ucd94\uc815 \uc870\ub958", "--", 1)
        self._stat_correction = StatCard("\ud3c9\uade0 \ubcf4\uc815\ub7c9", "--", 2)
        for s in (self._stat_angle, self._stat_current, self._stat_correction):
            stats_row.addWidget(s)
        layout.addLayout(stats_row)

        # Method description
        self._method_label = QLabel(
            "\uae30\uc900: \uc120\uc218 GPS \uae30\ubc18 \uc120\ubc15 COG (window=5 shots)  |  "
            "Feathering = \ucf00\uc774\ube14 \ubc29\uc704(\uc120\uc218->Tail) - \uc120\ubc15 \ud6c4\ubbf8 \ubc29\ud5a5  |  "
            "+ \uc6b0\ud604 / - \uc88c\ud604"
        )
        self._method_label.setWordWrap(True)
        self._method_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: rgba(6,182,212,0.05);
            border: 1px solid rgba(6,182,212,0.15);
            border-radius: {Radius.SM}px;
            padding: 6px 10px;
        """)
        layout.addWidget(self._method_label)

        # Chart
        self._fig = Figure(figsize=(8, 4), dpi=100, facecolor=MPL_BG)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(MPL_BG)
        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas, 1)

        # Placeholder
        self._ax.text(0.5, 0.5, "Style A \ubcc0\ud658 \uc2e4\ud589 \ud6c4 \ud45c\uc2dc\ub429\ub2c8\ub2e4",
                      transform=self._ax.transAxes,
                      ha="center", va="center", color=MPL_FG, fontsize=13)
        self._canvas.draw()

        # Export buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        export_btn = QPushButton("\ub9ac\ud3ec\ud2b8 \ub0b4\ubcf4\ub0b4\uae30")
        export_btn.setFixedHeight(28)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Dark.NAVY};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 0 14px;
                font-size: {Font.XS}px;
            }}
            QPushButton:hover {{ border-color: #06B6D4; }}
        """)
        export_btn.clicked.connect(self._export_report)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

    def set_analysis_result(self, result, out_dir: str, line_name: str,
                            survey_config=None, track_data=None):
        self._result = result
        self._out_dir = out_dir
        self._line_name = line_name
        self._survey_config = survey_config
        self._track_data = track_data

        s = result.stats
        self._stat_angle.set_value(f"{s['feathering_abs_mean']:.2f} deg")
        self._stat_current.set_value(
            f"{s['current_speed_mean_knots']:.2f} kn")
        self._stat_correction.set_value(
            f"{s['correction_mean_all']:.3f} m")

        # Update method label with actual COG stats
        import numpy as np
        cog = result.vessel_cog
        cog_mean = np.nanmean(cog)
        cog_std = np.nanstd(cog)
        cable_hd = result.cable_heading
        cable_mean = np.nanmean(cable_hd)

        self._method_label.setText(
            f"\uae30\uc900: \uc120\uc218 GPS \uae30\ubc18 COG (window=5)  |  "
            f"\ud3c9\uade0 COG: {cog_mean:.1f} deg  |  "
            f"\ud3c9\uade0 \ucf00\uc774\ube14 \ubc29\uc704: {cable_mean:.1f} deg  |  "
            f"Feathering = \ucf00\uc774\ube14(\uc120\uc218->Tail) - \uc120\ubc15 \ud6c4\ubbf8  |  "
            f"+ \uc6b0\ud604 / - \uc88c\ud604"
        )

        self._draw_chart(result)

    def _draw_chart(self, result):
        import numpy as np

        self._fig.clear()
        self._ax = self._fig.add_subplot(111)
        ax = self._ax
        ax.set_facecolor(MPL_BG)

        angles = np.array(result.feathering_angle, dtype=float)
        n = len(angles)
        x = np.arange(n)

        # Rolling average — the main visual (window ~1% of data, min 20)
        win = max(n // 100, 20)
        kernel = np.ones(win) / win
        smooth = np.convolve(angles, kernel, mode="same")

        # Raw data: very faint scatter
        ax.scatter(x, angles, s=0.3, c="#06B6D4", alpha=0.08,
                   rasterized=True)

        # Smooth trend: filled area from zero
        ax.fill_between(x, smooth, 0, color="#06B6D4", alpha=0.25)
        ax.plot(x, smooth, color="#06B6D4", linewidth=1.5)

        # Zero line
        ax.axhline(0, color="#334155", linewidth=0.8)

        # Y-axis: percentile-based
        p2, p98 = np.nanpercentile(angles, [2, 98])
        pad = max(abs(p98 - p2) * 0.2, 5)
        ax.set_ylim(min(p2 - pad, -5), max(p98 + pad, 5))

        # Minimal styling
        ax.set_xlabel("Shot", color=MPL_FG, fontsize=9)
        ax.set_ylabel("Feathering (deg)", color=MPL_FG, fontsize=9)
        ax.set_title(self._line_name, color=MPL_FG, fontsize=10)
        ax.tick_params(colors=MPL_FG, labelsize=8)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(axis="y", color="#1e293b", linewidth=0.4, alpha=0.5)

        self._fig.tight_layout()
        self._canvas.draw()

    def _export_report(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report",
            f"Feathering_{self._line_name}.txt",
            "Text (*.txt)")
        if path:
            from p190converter.engine.qc.feathering_analysis import (
                generate_feathering_report,
            )
            report = generate_feathering_report(self._result)
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
