"""ComparisonPanel — Style A vs B P190 comparison with charts."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.drop_zone import FileDropZone
from desktop.widgets.stat_card import StatCard

MPL_BG = "#0a0e17"
MPL_FG = "#94a3b8"


class ComparisonPanel(QWidget):
    """Compare two P190 files (Style A vs B)."""

    panel_title = "Compare"

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._result = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # File selectors
        files_card = SectionCard("P190 Files to Compare")
        self._file_a = FileDropZone(
            "Style A P190", "P190 Files (*.p190);;All (*)")
        self._file_b = FileDropZone(
            "Style B P190", "P190 Files (*.p190);;All (*)")
        files_card.content_layout.addWidget(self._file_a)
        files_card.content_layout.addWidget(self._file_b)

        compare_btn = QPushButton("Compare")
        compare_btn.setFixedHeight(32)
        compare_btn.setCursor(Qt.PointingHandCursor)
        compare_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Dark.CYAN};
                color: {Dark.DARK};
                border: none;
                border-radius: {Radius.SM}px;
                font-size: {Font.SM}px;
                font-weight: {Font.SEMIBOLD};
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: #22D3EE; }}
        """)
        compare_btn.clicked.connect(self._run_comparison)
        files_card.content_layout.addWidget(
            compare_btn, alignment=Qt.AlignRight)
        layout.addWidget(files_card)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(Space.SM)
        self._stat_grade = StatCard("Grade", "--", 0)
        self._stat_src_diff = StatCard("Src Mean Diff", "--", 1)
        self._stat_rx_diff = StatCard("Rx Mean Diff", "--", 2)
        self._stat_matched = StatCard("Matched Shots", "--", 3)
        for s in (self._stat_grade, self._stat_src_diff,
                  self._stat_rx_diff, self._stat_matched):
            stats_row.addWidget(s)
        layout.addLayout(stats_row)

        # Chart
        self._fig = Figure(figsize=(8, 3), dpi=100, facecolor=MPL_BG)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(MPL_BG)
        self._canvas = FigureCanvasQTAgg(self._fig)
        layout.addWidget(self._canvas, 1)

        # Placeholder
        self._ax.text(0.5, 0.5, "Select two P190 files to compare",
                      transform=self._ax.transAxes,
                      ha="center", va="center", color=MPL_FG, fontsize=13)
        self._canvas.draw()

        # Export
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        export_btn = QPushButton("Export Report")
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
            QPushButton:hover {{ border-color: {Dark.CYAN}; }}
        """)
        export_btn.clicked.connect(self._export_report)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

    def _run_comparison(self):
        path_a = self._file_a.value
        path_b = self._file_b.value

        if not path_a or not path_b:
            self._controller.show_toast(
                "Select both P190 files", "warning")
            return

        try:
            self._controller.conversion_log.emit(
                "info", f"Comparing: {Path(path_a).name} vs {Path(path_b).name}")
            from p190converter.engine.qc.comparison import compare_p190_files
            result = compare_p190_files(path_a, path_b)
            self._result = result
            self._display_result(result)
            self._controller.conversion_log.emit(
                "success",
                f"Comparison: grade={result.grade}, "
                f"src_diff={result.source_mean_diff:.3f}m, "
                f"matched={result.matched_shots}")
            self._controller.show_toast("Comparison complete", "success")
        except Exception as e:
            self._controller.conversion_log.emit(
                "error", f"Comparison error: {e}")
            self._controller.show_toast(f"Comparison error: {e}", "error")

    def _display_result(self, result):
        self._stat_grade.set_value(result.grade)
        self._stat_src_diff.set_value(
            f"{result.source_mean_diff:.3f} m")
        self._stat_rx_diff.set_value(
            f"{result.receiver_mean_diff:.3f} m")
        self._stat_matched.set_value(str(result.matched_shots))

        # Draw chart
        self._ax.clear()
        self._ax.set_facecolor(MPL_BG)

        diffs = result.source_diffs
        self._ax.bar(range(len(diffs)), diffs,
                     color="#F59E0B", alpha=0.7, width=1.0)
        self._ax.set_xlabel("Shot Index", color=MPL_FG, fontsize=9)
        self._ax.set_ylabel("Source Position Diff (m)",
                            color=MPL_FG, fontsize=9)
        self._ax.tick_params(colors=MPL_FG, labelsize=8)
        self._fig.tight_layout()
        self._canvas.draw()

    def _export_report(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison", "comparison_report.txt",
            "Text (*.txt)")
        if path:
            from p190converter.engine.qc.report import generate_comparison_report
            report = generate_comparison_report(self._result)
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
