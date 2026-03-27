"""ResultsPanel — Post-conversion QC dashboard."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.quality_gauge import QualityGauge
from desktop.widgets.stat_card import StatCard


class ResultsPanel(QWidget):
    """Post-conversion results: quality gauge, output info, QC checklist."""

    panel_title = "Results"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_path = ""
        self._report_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # Top row: Gauge + Stats
        top_row = QHBoxLayout()
        top_row.setSpacing(Space.LG)

        # Quality Gauge
        self._gauge = QualityGauge()
        top_row.addWidget(self._gauge)

        # Stats
        stats_col = QVBoxLayout()
        stats_col.setSpacing(Space.SM)
        self._stat_file = StatCard("Output File", "--", 0)
        self._stat_size = StatCard("File Size", "--", 1)
        self._stat_lines = StatCard("Total Lines", "--", 2)
        self._stat_time = StatCard("Elapsed", "--", 3)
        stats_row = QHBoxLayout()
        for s in (self._stat_file, self._stat_size,
                  self._stat_lines, self._stat_time):
            stats_row.addWidget(s)
        stats_col.addLayout(stats_row)
        top_row.addLayout(stats_col, 1)

        layout.addLayout(top_row)

        # QC Details
        qc_card = SectionCard("QC Validation")
        self._qc_text = QTextEdit()
        self._qc_text.setReadOnly(True)
        self._qc_text.setMaximumHeight(140)
        self._qc_text.setStyleSheet(f"""
            QTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
                font-family: monospace;
                font-size: {Font.SM}px;
            }}
        """)
        qc_card.content_layout.addWidget(self._qc_text)
        layout.addWidget(qc_card)

        # Output path + actions
        path_card = SectionCard("Output")
        self._path_label = QLabel("No output yet")
        self._path_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_card.content_layout.addWidget(self._path_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(Space.SM)

        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._open_report_btn = QPushButton("View Report")
        self._open_report_btn.clicked.connect(self._open_report)
        btn_row.addWidget(self._open_report_btn)
        btn_row.addStretch()

        for btn in (self._open_folder_btn, self._open_report_btn):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
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

        path_card.content_layout.addLayout(btn_row)
        layout.addWidget(path_card)
        layout.addStretch()

    def set_output(self, output_path: str, report_path: str):
        self._output_path = output_path
        self._report_path = report_path

        p = Path(output_path)
        self._path_label.setText(str(p))
        self._stat_file.set_value(p.name)

        if p.exists():
            sz = p.stat().st_size
            if sz > 1_048_576:
                self._stat_size.set_value(f"{sz / 1_048_576:.1f} MB")
            else:
                self._stat_size.set_value(f"{sz / 1024:.0f} KB")

    def set_qc_result(self, passed: bool, details: str):
        score = 100 if passed else 50
        label = "PASS" if passed else "ISSUES"
        self._gauge.set_value(score, label)
        self._qc_text.setPlainText(details)

        # Parse lines from details
        for line in details.split("\n"):
            if "Total lines" in line:
                val = line.split(":")[1].strip()
                self._stat_lines.set_value(val)

    def _open_folder(self):
        if self._output_path:
            folder = str(Path(self._output_path).parent)
            if os.path.isdir(folder):
                subprocess.Popen(["explorer", folder])

    def _open_report(self):
        if self._report_path and os.path.isfile(self._report_path):
            try:
                os.startfile(self._report_path)
            except OSError:
                pass
