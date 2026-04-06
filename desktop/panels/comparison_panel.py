"""ComparisonPanel — Style A vs B P190 comparison with charts."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")
from matplotlib import font_manager

for _family in (
    "Pretendard",
    "Noto Sans KR",
    "Malgun Gothic",
    "AppleGothic",
    "NanumGothic",
):
    if any(font.name == _family for font in font_manager.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = _family
        break
matplotlib.rcParams["axes.unicode_minus"] = False

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QPlainTextEdit, QSlider, QScrollArea,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.drop_zone import FileDropZone
from desktop.widgets.stat_card import StatCard
from desktop.services.output_package_service import (
    discover_output_package_entries,
    read_artifact_preview,
    summarize_artifact_inventory,
)
from desktop.services.export_service import export_package_manifest

MPL_BG = Dark.BG
MPL_FG = "#94a3b8"  # matplotlib text -- slightly lighter than Dark.MUTED for readability
MPL_GRID = Dark.SLATE  # #1E293B -- grid/spine color
_STYLE_A = Dark.CYAN       # Style A accent
_STYLE_B = "#EAB308"       # Style B yellow (app-specific, no Dark constant)
_STYLE_DELTA = Dark.RED    # delta / difference accent


class ComparisonPanel(QWidget):
    """Compare two P190 files (Style A vs B)."""

    panel_title = "Compare"

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._result = None
        self._ffids = []
        self._selected_ffid = None
        self._evidence_artifacts = {"A": [], "B": []}
        self._evidence_buttons = {}
        self._selected_evidence_key = ""
        self._language = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer.addWidget(scroll, 1)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Space.MD)

        # File selectors
        self._files_card = SectionCard("P190 Files to Compare")
        self._file_a = FileDropZone(
            "Style A P190", "P190 Files (*.p190);;All (*)")
        self._file_b = FileDropZone(
            "Style B P190", "P190 Files (*.p190);;All (*)")
        self._files_card.content_layout.addWidget(self._file_a)
        self._files_card.content_layout.addWidget(self._file_b)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setFixedHeight(32)
        self._compare_btn.setCursor(Qt.PointingHandCursor)
        self._compare_btn.setStyleSheet(f"""
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
        self._compare_btn.clicked.connect(self._run_comparison)
        self._files_card.content_layout.addWidget(
            self._compare_btn, alignment=Qt.AlignRight)
        layout.addWidget(self._files_card)

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

        self._insight_label = QLabel(
            "Compare two exported P190 files to understand how source basis, offsets, and interpolation changed the final geometry."
        )
        self._insight_label.setWordWrap(True)
        self._insight_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.SM}px;
            background: rgba(6,182,212,0.08);
            border: 1px solid rgba(6,182,212,0.2);
            border-radius: {Radius.SM}px;
            padding: 8px 10px;
        """)
        layout.addWidget(self._insight_label)

        # Chart
        self._fig = Figure(figsize=(8, 3), dpi=100, facecolor=MPL_BG)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(MPL_BG)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setMinimumHeight(260)
        layout.addWidget(self._canvas)

        # Placeholder
        self._ax.text(0.5, 0.5, "Select two P190 files to compare",
                      transform=self._ax.transAxes,
                      ha="center", va="center", color=MPL_FG, fontsize=13)
        self._canvas.draw()

        self._overlay_card = SectionCard("Selected Shot Overlay")
        self._detail_label = QLabel(
            "After comparison, inspect one matched FFID at a time to see source and receiver differences."
        )
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        self._overlay_card.content_layout.addWidget(self._detail_label)

        self._detail_fig = Figure(figsize=(8, 3), dpi=100, facecolor=MPL_BG)
        self._detail_ax = self._detail_fig.add_subplot(111)
        self._detail_ax.set_facecolor(MPL_BG)
        self._detail_canvas = FigureCanvasQTAgg(self._detail_fig)
        self._detail_canvas.setMinimumHeight(260)
        self._overlay_card.content_layout.addWidget(self._detail_canvas)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(Space.SM)
        self._detail_slider = QSlider(Qt.Horizontal)
        self._detail_slider.setMinimum(0)
        self._detail_slider.setMaximum(0)
        self._detail_slider.valueChanged.connect(self._update_shot_overlay)
        slider_row.addWidget(self._detail_slider, 1)

        self._detail_ffid = QLabel("FFID --")
        self._detail_ffid.setStyleSheet(
            f"color: {Dark.TEXT}; font-size: {Font.SM}px; background:transparent; border:none;"
        )
        slider_row.addWidget(self._detail_ffid)
        self._overlay_card.content_layout.addLayout(slider_row)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(Space.SM)
        self._btn_first = QPushButton("First")
        self._btn_mid = QPushButton("Middle")
        self._btn_worst = QPushButton("Worst")
        self._btn_last = QPushButton("Last")
        for btn in (self._btn_first, self._btn_mid, self._btn_worst, self._btn_last):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                    padding: 4px 10px;
                    font-size: {Font.XS}px;
                }}
                QPushButton:hover {{ border-color: {Dark.CYAN}; }}
            """)
        self._btn_first.clicked.connect(lambda: self._focus_ffid_index(0))
        self._btn_mid.clicked.connect(self._focus_middle)
        self._btn_worst.clicked.connect(self._focus_worst)
        self._btn_last.clicked.connect(lambda: self._focus_ffid_index(len(self._ffids) - 1))
        for btn in (self._btn_first, self._btn_mid, self._btn_worst, self._btn_last):
            quick_row.addWidget(btn)
        quick_row.addStretch()
        self._overlay_card.content_layout.addLayout(quick_row)
        layout.addWidget(self._overlay_card)

        self._meaning_card = SectionCard("Comparison Meaning")
        self._report_text = QPlainTextEdit()
        self._report_text.setReadOnly(True)
        self._report_text.setMinimumHeight(180)
        self._report_text.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: {Font.XS}px;
            }}
        """)
        self._report_text.setPlainText(
            "Run a comparison to see source/receiver difference statistics, directional context, and an export-ready summary."
        )
        self._meaning_card.content_layout.addWidget(self._report_text)
        layout.addWidget(self._meaning_card)

        self._channel_card = SectionCard("Receiver Channel Summary")
        self._channel_text = QPlainTextEdit()
        self._channel_text.setReadOnly(True)
        self._channel_text.setMaximumHeight(140)
        self._channel_text.setStyleSheet(self._report_text.styleSheet())
        self._channel_text.setPlainText(
            "Receiver comparison will appear here when both files contain comparable R records."
        )
        self._channel_card.content_layout.addWidget(self._channel_text)
        layout.addWidget(self._channel_card)

        self._worst_card = SectionCard("Largest Shot Differences")
        self._worst_text = QPlainTextEdit()
        self._worst_text.setReadOnly(True)
        self._worst_text.setMaximumHeight(120)
        self._worst_text.setStyleSheet(self._report_text.styleSheet())
        self._worst_text.setPlainText(
            "Run a comparison to list the largest FFID-level source differences."
        )
        self._worst_card.content_layout.addWidget(self._worst_text)
        layout.addWidget(self._worst_card)

        self._detail_card = SectionCard("Selected Shot Details")
        self._shot_detail_text = QPlainTextEdit()
        self._shot_detail_text.setReadOnly(True)
        self._shot_detail_text.setMaximumHeight(170)
        self._shot_detail_text.setStyleSheet(self._report_text.styleSheet())
        self._shot_detail_text.setPlainText(
            "Move the FFID slider or use the quick-focus buttons to inspect per-shot coordinates and channel deltas."
        )
        self._detail_card.content_layout.addWidget(self._shot_detail_text)
        layout.addWidget(self._detail_card)

        self._sync_card = SectionCard("Synchronized Style Workspace")
        self._sync_workspace_label = QLabel(
            "The selected FFID will stay locked across Style A and Style B so you can review both geometry stories side by side."
        )
        self._sync_workspace_label.setWordWrap(True)
        self._sync_workspace_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        self._sync_card.content_layout.addWidget(self._sync_workspace_label)

        sync_row = QHBoxLayout()
        sync_row.setSpacing(Space.SM)

        def _sync_style_sheet(accent: str) -> str:
            return f"""
                QPlainTextEdit {{
                    background: rgba(10,14,23,0.8);
                    color: {Dark.TEXT};
                    border: 1px solid {accent};
                    border-radius: {Radius.SM}px;
                    padding: 8px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: {Font.XS}px;
                }}
            """

        self._style_a_text = QPlainTextEdit()
        self._style_a_text.setReadOnly(True)
        self._style_a_text.setMinimumHeight(180)
        self._style_a_text.setStyleSheet(_sync_style_sheet(_STYLE_A))
        sync_row.addWidget(self._style_a_text, 5)

        self._style_delta_text = QPlainTextEdit()
        self._style_delta_text.setReadOnly(True)
        self._style_delta_text.setMinimumHeight(180)
        self._style_delta_text.setStyleSheet(_sync_style_sheet(_STYLE_DELTA))
        sync_row.addWidget(self._style_delta_text, 4)

        self._style_b_text = QPlainTextEdit()
        self._style_b_text.setReadOnly(True)
        self._style_b_text.setMinimumHeight(180)
        self._style_b_text.setStyleSheet(_sync_style_sheet(_STYLE_B))
        sync_row.addWidget(self._style_b_text, 5)

        self._sync_card.content_layout.addLayout(sync_row)
        layout.addWidget(self._sync_card)

        self._evidence_card = SectionCard("Linked Evidence Review")
        self._evidence_summary_label = QLabel(
            "Comparison evidence will appear here once two exported P190 files are loaded."
        )
        self._evidence_summary_label.setWordWrap(True)
        self._evidence_summary_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        self._evidence_card.content_layout.addWidget(self._evidence_summary_label)

        self._evidence_button_row = QHBoxLayout()
        self._evidence_button_row.setSpacing(Space.SM)
        self._evidence_card.content_layout.addLayout(self._evidence_button_row)

        evidence_preview_row = QHBoxLayout()
        evidence_preview_row.setSpacing(Space.SM)

        def _build_evidence_column(title: str, accent: str):
            column = QVBoxLayout()
            column.setSpacing(Space.SM)

            header_row = QHBoxLayout()
            header_row.setSpacing(Space.SM)
            label = QLabel(title)
            label.setStyleSheet(f"""
                color: {Dark.TEXT};
                font-size: {Font.SM}px;
                font-weight: {Font.SEMIBOLD};
                background: transparent;
                border: none;
            """)
            header_row.addWidget(label)
            header_row.addStretch()

            open_btn = QPushButton("Open Selected")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setFixedHeight(26)
            open_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {accent};
                    border-radius: {Radius.SM}px;
                    padding: 0 10px;
                    font-size: {Font.XS}px;
                }}
                QPushButton:hover {{ border-color: {Dark.CYAN}; }}
            """)
            header_row.addWidget(open_btn)
            column.addLayout(header_row)

            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setMinimumHeight(170)
            text.setStyleSheet(f"""
                QPlainTextEdit {{
                    background: rgba(10,14,23,0.8);
                    color: {Dark.TEXT};
                    border: 1px solid {accent};
                    border-radius: {Radius.SM}px;
                    padding: 8px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: {Font.XS}px;
                }}
            """)
            column.addWidget(text)

            image = QLabel("Image evidence preview will appear here.")
            image.setAlignment(Qt.AlignCenter)
            image.setMinimumHeight(180)
            image.setStyleSheet(f"""
                QLabel {{
                    background: rgba(10,14,23,0.45);
                    color: {Dark.MUTED};
                    border: 1px solid {accent};
                    border-radius: {Radius.SM}px;
                    padding: 8px;
                }}
            """)
            image.hide()
            column.addWidget(image)
            return column, label, open_btn, text, image

        left_column, self._evidence_a_title, self._open_evidence_a_btn, self._evidence_a_text, self._evidence_a_image = _build_evidence_column(
            "Style A Evidence", _STYLE_A
        )
        right_column, self._evidence_b_title, self._open_evidence_b_btn, self._evidence_b_text, self._evidence_b_image = _build_evidence_column(
            "Style B Evidence", _STYLE_B
        )
        self._open_evidence_a_btn.clicked.connect(lambda: self._open_selected_evidence("A"))
        self._open_evidence_b_btn.clicked.connect(lambda: self._open_selected_evidence("B"))

        evidence_preview_row.addLayout(left_column, 1)
        evidence_preview_row.addLayout(right_column, 1)
        self._evidence_card.content_layout.addLayout(evidence_preview_row)
        layout.addWidget(self._evidence_card)

        self._channel_profile_card = SectionCard("Selected Shot Receiver Delta Profile")
        self._channel_profile_label = QLabel(
            "Receiver delta profile will appear here when the selected shot has comparable R records."
        )
        self._channel_profile_label.setWordWrap(True)
        self._channel_profile_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        self._channel_profile_card.content_layout.addWidget(self._channel_profile_label)

        self._channel_profile_fig = Figure(figsize=(8, 2.3), dpi=100, facecolor=MPL_BG)
        self._channel_profile_ax = self._channel_profile_fig.add_subplot(111)
        self._channel_profile_ax.set_facecolor(MPL_BG)
        self._channel_profile_canvas = FigureCanvasQTAgg(self._channel_profile_fig)
        self._channel_profile_canvas.setMinimumHeight(220)
        self._channel_profile_card.content_layout.addWidget(self._channel_profile_canvas)
        layout.addWidget(self._channel_profile_card)

        # Export
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._export_report_btn = QPushButton("Export Report")
        self._export_plot_btn = QPushButton("Export Plot")
        self._export_manifest_btn = QPushButton("Export Manifest")
        for btn in (self._export_report_btn, self._export_plot_btn, self._export_manifest_btn):
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
        self._export_report_btn.clicked.connect(self._export_report)
        self._export_plot_btn.clicked.connect(self._export_plot)
        self._export_manifest_btn.clicked.connect(self._export_manifest)
        btn_row.addWidget(self._export_report_btn)
        btn_row.addWidget(self._export_plot_btn)
        btn_row.addWidget(self._export_manifest_btn)
        layout.addLayout(btn_row)
        layout.addStretch()
        self._draw_empty_sync_workspace()
        self._draw_empty_evidence_workspace()
        self._draw_empty_channel_profile()

    def set_file_paths(self, style_a: str = "", style_b: str = ""):
        """Pre-fill compare inputs from recent conversion outputs."""
        if style_a:
            self._file_a.value = style_a
        if style_b:
            self._file_b.value = style_b

    def compare_paths(self, style_a: str, style_b: str):
        """Set comparison inputs and run immediately."""
        self.set_file_paths(style_a, style_b)
        self._run_comparison()

    def set_language_service(self, language_service):
        self._language = language_service
        self.apply_language()

    def _t(self, key: str) -> str:
        if self._language is None:
            fallback = {
                "panel_title": "Compare",
                "files_card": "P190 Files to Compare",
                "file_a": "Style A P190",
                "file_b": "Style B P190",
                "browse": "Browse",
                "compare_button": "Compare",
                "stat_grade": "Grade",
                "stat_src_diff": "Src Mean Diff",
                "stat_rx_diff": "Rx Mean Diff",
                "stat_matched": "Matched Shots",
                "idle_insight": "Compare two exported P190 files to understand how source basis, offsets, and interpolation changed the final geometry.",
                "overlay_card": "Selected Shot Overlay",
                "overlay_idle": "After comparison, inspect one matched FFID at a time to see source and receiver differences.",
                "quick_first": "First",
                "quick_middle": "Middle",
                "quick_worst": "Worst",
                "quick_last": "Last",
                "meaning_card": "Comparison Meaning",
                "meaning_idle": "Run a comparison to see source/receiver difference statistics, directional context, and an export-ready summary.",
                "channel_card": "Receiver Channel Summary",
                "channel_idle": "Receiver comparison will appear here when both files contain comparable R records.",
                "worst_card": "Largest Shot Differences",
                "worst_idle": "Run a comparison to list the largest FFID-level source differences.",
                "detail_card": "Selected Shot Details",
                "detail_idle": "Move the FFID slider or use the quick-focus buttons to inspect per-shot coordinates and channel deltas.",
                "sync_card": "Synchronized Style Workspace",
                "sync_idle": "The selected FFID will stay locked across Style A and Style B so you can review both geometry stories side by side.",
                "evidence_card": "Linked Evidence Review",
                "evidence_idle": "Comparison evidence will appear here once two exported P190 files are loaded.",
                "evidence_a": "Style A Evidence",
                "evidence_b": "Style B Evidence",
                "open_selected": "Open Selected",
                "channel_profile_card": "Selected Shot Receiver Delta Profile",
                "channel_profile_idle": "Receiver delta profile will appear here when the selected shot has comparable R records.",
                "export_report": "Export Report",
                "export_plot": "Export Plot",
                "export_manifest": "Export Manifest",
            }
            return fallback[key]
        return self._language.text(f"compare.{key}")

    def apply_language(self):
        self.panel_title = self._t("panel_title")
        self._files_card.set_title(self._t("files_card"))
        self._file_a.set_label_text(self._t("file_a"))
        self._file_b.set_label_text(self._t("file_b"))
        self._file_a.set_browse_text(self._t("browse"))
        self._file_b.set_browse_text(self._t("browse"))
        self._compare_btn.setText(self._t("compare_button"))
        self._stat_grade.set_label(self._t("stat_grade"))
        self._stat_src_diff.set_label(self._t("stat_src_diff"))
        self._stat_rx_diff.set_label(self._t("stat_rx_diff"))
        self._stat_matched.set_label(self._t("stat_matched"))
        self._overlay_card.set_title(self._t("overlay_card"))
        self._meaning_card.set_title(self._t("meaning_card"))
        self._channel_card.set_title(self._t("channel_card"))
        self._worst_card.set_title(self._t("worst_card"))
        self._detail_card.set_title(self._t("detail_card"))
        self._sync_card.set_title(self._t("sync_card"))
        self._evidence_card.set_title(self._t("evidence_card"))
        self._evidence_a_title.setText(self._t("evidence_a"))
        self._evidence_b_title.setText(self._t("evidence_b"))
        self._open_evidence_a_btn.setText(self._t("open_selected"))
        self._open_evidence_b_btn.setText(self._t("open_selected"))
        self._channel_profile_card.set_title(self._t("channel_profile_card"))
        self._btn_first.setText(self._t("quick_first"))
        self._btn_mid.setText(self._t("quick_middle"))
        self._btn_worst.setText(self._t("quick_worst"))
        self._btn_last.setText(self._t("quick_last"))
        self._export_report_btn.setText(self._t("export_report"))
        self._export_plot_btn.setText(self._t("export_plot"))
        self._export_manifest_btn.setText(self._t("export_manifest"))

        if self._result is not None:
            self._display_result(self._result)
            if self._selected_evidence_key:
                self._select_evidence_artifact(self._selected_evidence_key)
        else:
            self._insight_label.setText(self._t("idle_insight"))
            self._detail_label.setText(self._t("overlay_idle"))
            self._report_text.setPlainText(self._t("meaning_idle"))
            self._channel_text.setPlainText(self._t("channel_idle"))
            self._worst_text.setPlainText(self._t("worst_idle"))
            self._shot_detail_text.setPlainText(self._t("detail_idle"))
            self._draw_empty_sync_workspace()
            self._draw_empty_evidence_workspace()
            self._draw_empty_channel_profile()
            self._draw_main_chart()

    def _draw_empty_evidence_workspace(self, message: str | None = None):
        self._selected_evidence_key = ""
        self._evidence_summary_label.setText(
            message
            or self._t("evidence_idle")
        )
        while self._evidence_button_row.count():
            item = self._evidence_button_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._evidence_buttons = {}
        if self._language and self._language.current_language == "ko":
            self._evidence_a_text.setPlainText(
                "Style A 근거\n\n비교 결과를 선택하면 exported P190, QC report, geometry TSV, FFID map, plot 같은 관련 산출물을 미리볼 수 있습니다."
            )
            self._evidence_b_text.setPlainText(
                "Style B 근거\n\n같은 artifact type의 반대편 산출물을 나란히 미리봅니다."
            )
        else:
            self._evidence_a_text.setPlainText(
                "Style A evidence\n\nSelect a comparison result to preview related package artifacts such as the exported P190, QC report, geometry TSV, FFID map, or plots."
            )
            self._evidence_b_text.setPlainText(
                "Style B evidence\n\nSelect a comparison result to preview the matching artifact type from the other export package."
            )
        for image in (self._evidence_a_image, self._evidence_b_image):
            image.hide()
            image.setPixmap(QPixmap())
            image.setText("이미지 근거 미리보기가 여기에 표시됩니다." if self._language and self._language.current_language == "ko" else "Image evidence preview will appear here.")

    def _refresh_evidence_workspace(self, path_a: str, path_b: str):
        self._evidence_artifacts = {
            "A": discover_output_package_entries(path_a),
            "B": discover_output_package_entries(path_b),
        }
        while self._evidence_button_row.count():
            item = self._evidence_button_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._evidence_buttons = {}

        all_keys = {
            artifact.key
            for artifacts in self._evidence_artifacts.values()
            for artifact in artifacts
        }
        preferred_order = [
            "p190",
            "report",
            "geometry_tsv",
            "ffid_map",
            "track_plot",
            "feathering_report",
            "feathering_plot",
            "geometry_aligned",
        ]
        button_keys = [key for key in preferred_order if key in all_keys]
        button_keys.extend(sorted(all_keys - set(button_keys)))

        for key in button_keys[:8]:
            btn = QPushButton(key.replace("_", " ").title())
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _checked=False, artifact_key=key: self._select_evidence_artifact(artifact_key)
            )
            self._evidence_button_row.addWidget(btn)
            self._evidence_buttons[key] = btn
        self._evidence_button_row.addStretch()

        summary_a = summarize_artifact_inventory(self._evidence_artifacts["A"])
        summary_b = summarize_artifact_inventory(self._evidence_artifacts["B"])
        self._evidence_summary_label.setText(
            f"Style A: {summary_a} Style B: {summary_b}"
        )

        default_key = "p190" if "p190" in button_keys else (button_keys[0] if button_keys else "")
        if default_key:
            self._select_evidence_artifact(default_key)
        else:
            self._draw_empty_evidence_workspace(
                "No output-package evidence could be derived from the selected comparison files."
            )

    def _artifact_for_side(self, side: str, artifact_key: str):
        for artifact in self._evidence_artifacts.get(side, []):
            if artifact.key == artifact_key:
                return artifact
        return None

    def _select_evidence_artifact(self, artifact_key: str):
        self._selected_evidence_key = artifact_key
        artifact_a = self._artifact_for_side("A", artifact_key)
        artifact_b = self._artifact_for_side("B", artifact_key)
        if artifact_a is None and artifact_b is None:
            return

        for key, button in self._evidence_buttons.items():
            art_a = self._artifact_for_side("A", key)
            art_b = self._artifact_for_side("B", key)
            ready_count = sum(
                1 for artifact in (art_a, art_b) if artifact is not None and artifact.exists
            )
            active = key == artifact_key
            border = Dark.CYAN if active else (Dark.BORDER if ready_count == 2 else Dark.SURFACE)
            background = Dark.NAVY if ready_count else Dark.BG_ALT
            foreground = Dark.TEXT if ready_count else Dark.MUTED
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {background};
                    color: {foreground};
                    border: 1px solid {border};
                    border-radius: {Radius.SM}px;
                    padding: 4px 10px;
                    font-size: {Font.XS}px;
                }}
                QPushButton:hover {{ border-color: {Dark.CYAN}; color: {Dark.TEXT}; }}
            """)
            button.setToolTip(
                f"Style A: {'Ready' if art_a and art_a.exists else 'Not generated'}\n"
                f"Style B: {'Ready' if art_b and art_b.exists else 'Not generated'}"
            )

        self._render_evidence_column(
            artifact_a,
            self._evidence_a_text,
            self._evidence_a_image,
            "Style A evidence",
        )
        self._render_evidence_column(
            artifact_b,
            self._evidence_b_text,
            self._evidence_b_image,
            "Style B evidence",
        )

        label = artifact_a.label if artifact_a is not None else artifact_b.label
        self._evidence_summary_label.setText(
            f"Reviewing {label}. "
            f"Style A: {'Ready' if artifact_a and artifact_a.exists else 'Not generated'} | "
            f"Style B: {'Ready' if artifact_b and artifact_b.exists else 'Not generated'}."
        )

    def _render_evidence_column(self, artifact, text_widget, image_widget, placeholder_title: str):
        if artifact is None:
            text_widget.setPlainText(
                f"{placeholder_title}\n\n"
                + (
                    "이 artifact type은 선택한 파일의 표준 output package에 포함되지 않습니다."
                    if self._language and self._language.current_language == "ko"
                    else "This artifact type is not part of the known package for the selected file."
                )
            )
            image_widget.hide()
            image_widget.setPixmap(QPixmap())
            image_widget.setText("이미지 근거 미리보기가 여기에 표시됩니다." if self._language and self._language.current_language == "ko" else "Image evidence preview will appear here.")
            return

        text_widget.setPlainText(read_artifact_preview(artifact))
        if artifact.kind != "image" or not artifact.exists:
            image_widget.hide()
            image_widget.setPixmap(QPixmap())
            image_widget.setText("이미지 근거 미리보기가 여기에 표시됩니다." if self._language and self._language.current_language == "ko" else "Image evidence preview will appear here.")
            return

        pixmap = QPixmap(str(artifact.path))
        if pixmap.isNull():
            image_widget.show()
            image_widget.setPixmap(QPixmap())
            image_widget.setText(
                "이미지 근거를 불러오지 못했습니다. 직접 열어서 확인하세요."
                if self._language and self._language.current_language == "ko"
                else "Image evidence could not be loaded. Use Open Selected to inspect the file directly."
            )
            return

        image_widget.show()
        image_widget.setPixmap(
            pixmap.scaled(520, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        image_widget.setText("")

    def _open_selected_evidence(self, side: str):
        artifact = self._artifact_for_side(side, self._selected_evidence_key)
        if artifact and artifact.exists:
            try:
                os.startfile(str(artifact.path))
            except OSError:
                pass

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
        self._result = result
        self._refresh_evidence_workspace(self._file_a.value, self._file_b.value)
        self._stat_grade.set_value(result.grade)
        self._stat_src_diff.set_value(
            f"{result.source_mean_diff:.3f} m")
        self._stat_rx_diff.set_value(
            f"{result.receiver_mean_diff:.3f} m"
            if result.has_receivers else "N/A")
        self._stat_matched.set_value(str(result.matched_shots))

        receiver_note = (
            (
                f"리시버 지오메트리를 {result.n_channels}개 채널 기준으로 비교했습니다."
                if self._language and self._language.current_language == "ko"
                else f"Receiver geometry was compared across {result.n_channels} channels."
            )
            if result.has_receivers else
            (
                "한쪽 또는 양쪽 파일에 비교 가능한 R 레코드가 없어 리시버 비교를 할 수 없습니다."
                if self._language and self._language.current_language == "ko"
                else "Receiver comparison is unavailable because one or both files do not expose comparable R records."
            )
        )
        self._insight_label.setText(
            f"{result.grade}: {result.assessment_note} "
            f"Matched shots: {result.n_common_shots:,}. "
            f"Source P95: {result.source_dist_p95:.2f} m. "
            f"{receiver_note}"
        )

        from p190converter.engine.qc.comparison import format_comparison_report
        self._report_text.setPlainText(format_comparison_report(result))

        if result.per_channel_df is not None and not result.per_channel_df.empty:
            lines = [
                f"{'CH':>4s}  {'Mean(m)':>8s}  {'Max(m)':>8s}  {'Std(m)':>8s}",
                "-" * 38,
            ]
            for _, row in result.per_channel_df.iterrows():
                lines.append(
                    f"{int(row['channel']):>4d}  "
                    f"{row['mean_dist']:8.3f}  "
                    f"{row['max_dist']:8.3f}  "
                    f"{row['std_dist']:8.3f}"
                )
            self._channel_text.setPlainText("\n".join(lines))
        else:
            self._channel_text.setPlainText(
                "리시버 비교를 할 수 없습니다. 채널별 차이를 보려면 두 산출물 모두 비교 가능한 R 레코드를 포함해야 합니다."
                if self._language and self._language.current_language == "ko"
                else "Receiver comparison unavailable. Compare exports that both contain R records to review per-channel differences."
            )

        self._ffids = sorted(result.positions.keys())
        self._selected_ffid = None
        self._render_worst_shots()
        if self._ffids:
            self._detail_slider.blockSignals(True)
            self._detail_slider.setMaximum(len(self._ffids) - 1)
            self._detail_slider.setValue(len(self._ffids) // 2)
            self._detail_slider.blockSignals(False)
            self._update_shot_overlay(self._detail_slider.value())
        else:
            self._draw_main_chart()
            self._draw_empty_overlay()
            self._draw_empty_channel_profile()

    def _export_report(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison", "Style_AB_Comparison_Report.txt",
            "Text (*.txt)")
        if path:
            from p190converter.engine.qc.report import generate_comparison_report
            report = generate_comparison_report(self._result)
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)

    def _export_plot(self):
        if not self._result:
            return
        default_name = "Style_AB_Comparison_Plot.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison Plot", default_name, "PNG (*.png)"
        )
        if path:
            from p190converter.engine.qc.plot import generate_comparison_plot

            zoom_ffid = self._current_ffid()
            generate_comparison_plot(self._result, path, zoom_ffid=zoom_ffid)

    def _export_manifest(self):
        path_a = self._file_a.value
        path_b = self._file_b.value
        if not path_a or not path_b:
            self._controller.show_toast(
                "두 P190 파일을 먼저 지정하세요." if self._language and self._language.current_language == "ko" else "Select both P190 files first",
                "warning",
            )
            return

        default_name = "Style_AB_Package_Manifest.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Package Manifest",
            default_name,
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return

        saved_path = export_package_manifest(path_a, path_b, path)
        if self._controller is not None:
            self._controller.conversion_log.emit(
                "success",
                f"Package manifest exported: {saved_path}",
            )
            self._controller.show_toast(
                "패키지 요약을 저장했습니다." if self._language and self._language.current_language == "ko" else "Package manifest exported",
                "success",
            )

    def _current_ffid(self):
        if not self._ffids:
            return None
        idx = max(0, min(self._detail_slider.value(), len(self._ffids) - 1))
        return self._ffids[idx]

    def _draw_empty_overlay(self):
        self._detail_ax.clear()
        self._detail_ax.set_facecolor(MPL_BG)
        self._detail_ax.text(
            0.5, 0.5,
            "샷별 지오메트리가 없습니다"
            if self._language and self._language.current_language == "ko"
            else "No per-shot geometry available",
            transform=self._detail_ax.transAxes,
            ha="center", va="center", color=MPL_FG, fontsize=11
        )
        self._detail_ax.set_xticks([])
        self._detail_ax.set_yticks([])
        self._detail_canvas.draw()
        self._shot_detail_text.setPlainText(
            "샷별 지오메트리가 없습니다."
            if self._language and self._language.current_language == "ko"
            else "No per-shot geometry available."
        )
        self._draw_empty_sync_workspace()
        self._draw_empty_channel_profile()

    def _draw_empty_sync_workspace(self, message: str | None = None):
        self._sync_workspace_label.setText(
            message
            or self._t("sync_idle")
        )
        if self._language and self._language.current_language == "ko":
            self._style_a_text.setPlainText(
                "Style A 스냅샷\n\n비교 결과를 선택하면 소스, 헤딩, spread, 리시버 맥락을 확인할 수 있습니다."
            )
            self._style_delta_text.setPlainText(
                "차이 스냅샷\n\n가운데 칸에서 소스 이동량, 헤딩 변화, spread 차이, 주요 채널 차이를 설명합니다."
            )
            self._style_b_text.setPlainText(
                "Style B 스냅샷\n\n비교 결과를 선택하면 소스, 헤딩, spread, 리시버 맥락을 확인할 수 있습니다."
            )
        else:
            self._style_a_text.setPlainText(
                "Style A snapshot\n\nSelect a comparison result to inspect source, heading, spread, and receiver context."
            )
            self._style_delta_text.setPlainText(
                "Delta snapshot\n\nThe center lane will explain source shift, heading change, spread difference, and dominant receiver channels."
            )
            self._style_b_text.setPlainText(
                "Style B snapshot\n\nSelect a comparison result to inspect source, heading, spread, and receiver context."
            )

    def _draw_empty_channel_profile(self, message: str | None = None):
        self._channel_profile_ax.clear()
        self._channel_profile_ax.set_facecolor(MPL_BG)
        profile_message = message or (
            "이 샷에서는 리시버 차이 프로파일을 표시할 수 없습니다"
            if self._language and self._language.current_language == "ko"
            else "Receiver delta profile is unavailable for this shot"
        )
        self._channel_profile_ax.text(
            0.5,
            0.5,
            profile_message,
            transform=self._channel_profile_ax.transAxes,
            ha="center",
            va="center",
            color=MPL_FG,
            fontsize=10,
        )
        self._channel_profile_ax.set_xticks([])
        self._channel_profile_ax.set_yticks([])
        self._channel_profile_canvas.draw()
        self._channel_profile_label.setText(
            message
            or self._t("channel_profile_idle")
        )

    def _draw_main_chart(self):
        self._ax.clear()
        self._ax.set_facecolor(MPL_BG)
        if not self._result:
            self._ax.text(
                0.5, 0.5,
                "비교할 두 개의 P190 파일을 선택하세요"
                if self._language and self._language.current_language == "ko"
                else "Select two P190 files to compare",
                transform=self._ax.transAxes,
                ha="center", va="center", color=MPL_FG, fontsize=13
            )
            self._canvas.draw()
            return

        diffs = self._result.source_diffs
        x = list(range(len(diffs)))
        if len(diffs) > 200:
            self._ax.plot(x, diffs, color=Dark.ORANGE, linewidth=1.2)
            self._ax.fill_between(x, diffs, 0, color=Dark.ORANGE, alpha=0.18)
        else:
            self._ax.bar(x, diffs, color=Dark.ORANGE, alpha=0.75, width=0.9)
        self._ax.axhline(self._result.source_dist_mean, color=Dark.CYAN,
                         linewidth=1.0, linestyle="--")
        self._ax.axhline(self._result.source_dist_p95, color=Dark.RED,
                         linewidth=1.0, linestyle=":")

        if self._selected_ffid in self._ffids:
            selected_index = self._ffids.index(self._selected_ffid)
            self._ax.axvline(selected_index, color=Dark.TEXT_BRIGHT,
                             linewidth=1.0, linestyle="-.", alpha=0.85)

        if self._result.worst_ffid in self._ffids:
            worst_index = self._ffids.index(self._result.worst_ffid)
            self._ax.axvline(worst_index, color="#F97316",  # deep-orange accent
                             linewidth=1.0, linestyle=":", alpha=0.8)

        self._ax.set_xlabel("Matched Shot Order", color=MPL_FG, fontsize=9)
        self._ax.set_ylabel("Source Position Diff (m)",
                            color=MPL_FG, fontsize=9)
        self._ax.set_title(
            f"{self._result.grade} | Mean {self._result.source_dist_mean:.2f} m | P95 {self._result.source_dist_p95:.2f} m",
            color=MPL_FG, fontsize=10)
        self._ax.tick_params(colors=MPL_FG, labelsize=8)
        self._ax.grid(axis="y", color=MPL_GRID, linewidth=0.5, alpha=0.6)
        for spine in self._ax.spines.values():
            spine.set_color(MPL_GRID)
        self._fig.tight_layout()
        self._canvas.draw()

    def _render_worst_shots(self):
        if not self._result:
            self._worst_text.setPlainText(
                "Run a comparison to list the largest FFID-level source differences."
            )
            return

        worst = self._result.worst_shots(5)
        if worst.empty:
            self._worst_text.setPlainText("No matched shots available.")
            return

        lines = [
            f"{'FFID':>8s}  {'Dist(m)':>8s}  {'dE(m)':>8s}  {'dN(m)':>8s}",
            "-" * 42,
        ]
        for _, row in worst.iterrows():
            lines.append(
                f"{int(row['ffid']):>8d}  "
                f"{row['source_dist']:8.3f}  "
                f"{row['dx']:8.3f}  "
                f"{row['dy']:8.3f}"
            )
        self._worst_text.setPlainText("\n".join(lines))

    def _focus_ffid_index(self, index: int):
        if not self._ffids:
            return
        index = max(0, min(index, len(self._ffids) - 1))
        self._detail_slider.setValue(index)

    def _focus_middle(self):
        if self._ffids:
            self._focus_ffid_index(len(self._ffids) // 2)

    def _focus_worst(self):
        if not self._result or self._result.worst_ffid not in self._ffids:
            return
        self._focus_ffid_index(self._ffids.index(self._result.worst_ffid))

    def _update_shot_overlay(self, value: int):
        if not self._result or not self._ffids:
            self._draw_empty_overlay()
            return

        ffid = self._ffids[max(0, min(value, len(self._ffids) - 1))]
        self._selected_ffid = ffid
        pos = self._result.positions.get(ffid)
        if not pos:
            self._draw_empty_overlay()
            return

        self._detail_ax.clear()
        self._detail_ax.set_facecolor(MPL_BG)
        self._detail_ax.grid(True, color=MPL_GRID, linewidth=0.4, alpha=0.5)
        for spine in self._detail_ax.spines.values():
            spine.set_color(MPL_GRID)
        self._detail_ax.tick_params(colors=MPL_FG, labelsize=8)

        src_a = pos["src_a"]
        src_b = pos["src_b"]
        rx_a = pos.get("rx_a", [])
        rx_b = pos.get("rx_b", [])

        if rx_a:
            ax_x = [src_a[0]] + [r[0] for r in rx_a]
            ax_y = [src_a[1]] + [r[1] for r in rx_a]
            self._detail_ax.plot(ax_x, ax_y, "-o", color=_STYLE_A,
                                 linewidth=1.2, markersize=3, label="Style A")
        else:
            self._detail_ax.plot(src_a[0], src_a[1], "D", color=_STYLE_A,
                                 markersize=7, label="Style A")

        if rx_b:
            bx_x = [src_b[0]] + [r[0] for r in rx_b]
            bx_y = [src_b[1]] + [r[1] for r in rx_b]
            self._detail_ax.plot(bx_x, bx_y, "-o", color=_STYLE_B,
                                 linewidth=1.2, markersize=3, label="Style B")
        else:
            self._detail_ax.plot(src_b[0], src_b[1], "D", color=_STYLE_B,
                                 markersize=7, label="Style B")

        self._detail_ax.plot(
            [src_a[0], src_b[0]],
            [src_a[1], src_b[1]],
            "--",
            color=_STYLE_DELTA,
            linewidth=1.0,
            alpha=0.8,
        )

        for rx1, rx2 in zip(rx_a, rx_b):
            self._detail_ax.plot(
                [rx1[0], rx2[0]],
                [rx1[1], rx2[1]],
                ":",
                color=MPL_FG,
                linewidth=0.7,
                alpha=0.5,
            )

        source_dist = (
            self._result.per_shot_df.loc[
                self._result.per_shot_df["ffid"] == ffid, "source_dist"
            ].iloc[0]
            if self._result.per_shot_df is not None
            else 0.0
        )
        self._detail_ax.set_aspect("equal", adjustable="datalim")
        self._detail_ax.set_title(
            f"FFID {ffid} | Source diff {source_dist:.2f} m",
            color=MPL_FG,
            fontsize=10,
        )
        self._detail_ax.set_xlabel("Easting (m)", color=MPL_FG, fontsize=8)
        self._detail_ax.set_ylabel("Northing (m)", color=MPL_FG, fontsize=8)
        self._detail_ax.legend(
            fontsize=8,
            loc="upper left",
            facecolor=MPL_BG,
            edgecolor=MPL_GRID,
            labelcolor=MPL_FG,
        )
        self._detail_fig.tight_layout()
        self._detail_canvas.draw()

        self._detail_ffid.setText(f"FFID {ffid}")
        heading_diff = pos.get("heading_a", 0.0) - pos.get("heading_b", 0.0)
        channel_note = ""
        if self._result.per_channel_df is not None and not self._result.per_channel_df.empty:
            max_channel = self._result.per_channel_df.sort_values(
                "mean_dist", ascending=False
            ).iloc[0]
            channel_note = (
                f" Strongest persistent receiver delta is CH{int(max_channel['channel'])} "
                f"at mean {max_channel['mean_dist']:.2f} m."
            )
        self._detail_label.setText(
            f"Selected shot shows exported source and receiver geometry for both styles. "
            f"Source difference: {source_dist:.2f} m. "
            f"Heading A/B: {pos.get('heading_a', 0.0):.1f} / {pos.get('heading_b', 0.0):.1f} deg "
            f"(delta {heading_diff:.1f} deg)."
            f"{channel_note}"
        )
        self._shot_detail_text.setPlainText(
            self._build_selected_shot_detail(ffid, pos, source_dist)
        )
        self._update_sync_workspace(ffid, pos, source_dist)
        self._update_channel_profile(ffid)
        self._draw_main_chart()

    def _update_sync_workspace(self, ffid: int, pos: dict, source_dist: float):
        channel_df = (
            self._result.channel_deltas_for_ffid(ffid)
            if self._result is not None
            else None
        )
        rx_a = pos.get("rx_a", [])
        rx_b = pos.get("rx_b", [])
        src_a = pos["src_a"]
        src_b = pos["src_b"]
        head_a = pos.get("heading_a", 0.0)
        head_b = pos.get("heading_b", 0.0)
        spread_a = pos.get("spread_dir_a", 0.0)
        spread_b = pos.get("spread_dir_b", 0.0)

        def _receiver_summary(rx_list):
            if not rx_list:
                return ["Receivers: not available"]
            first = rx_list[0]
            last = rx_list[-1]
            tail_dist = ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5
            return [
                f"Receivers: {len(rx_list)}",
                f"First RX: ({first[0]:.3f}, {first[1]:.3f})",
                f"Last RX:  ({last[0]:.3f}, {last[1]:.3f})",
                f"Streamer span: {tail_dist:.3f} m",
            ]

        self._style_a_text.setPlainText(
            "\n".join(
                [
                    f"Style A | FFID {ffid}",
                    f"Source: ({src_a[0]:.3f}, {src_a[1]:.3f})",
                    f"Heading: {head_a:.1f} deg",
                    f"Spread dir: {spread_a:.1f} deg",
                    *_receiver_summary(rx_a),
                ]
            )
        )
        self._style_b_text.setPlainText(
            "\n".join(
                [
                    f"Style B | FFID {ffid}",
                    f"Source: ({src_b[0]:.3f}, {src_b[1]:.3f})",
                    f"Heading: {head_b:.1f} deg",
                    f"Spread dir: {spread_b:.1f} deg",
                    *_receiver_summary(rx_b),
                ]
            )
        )

        delta_lines = [
            f"Delta | FFID {ffid}",
            f"Source shift: {source_dist:.3f} m",
            f"Heading delta: {head_a - head_b:.1f} deg",
            f"Spread delta: {spread_a - spread_b:.1f} deg",
            f"Receiver count: {len(rx_a)} / {len(rx_b)}",
        ]
        if channel_df is not None and not channel_df.empty:
            mean_delta = channel_df["dist"].mean()
            peak_row = channel_df.sort_values("dist", ascending=False).iloc[0]
            delta_lines.extend(
                [
                    "",
                    f"Mean RX delta: {mean_delta:.3f} m",
                    f"Peak RX delta: CH{int(peak_row['channel'])} at {peak_row['dist']:.3f} m",
                    f"Peak dE/dN: {peak_row['dx']:.3f} / {peak_row['dy']:.3f} m",
                ]
            )
        else:
            delta_lines.extend(
                [
                    "",
                    "Receiver delta: unavailable",
                    "Only source geometry can be compared for this shot.",
                ]
            )
        self._style_delta_text.setPlainText("\n".join(delta_lines))
        self._sync_workspace_label.setText(
            f"Style A and Style B are synchronized on FFID {ffid}. "
            f"Use the quick-focus buttons to jump through first, middle, worst, or last matched shots while keeping both stories aligned."
        )

    def _update_channel_profile(self, ffid: int):
        if not self._result:
            self._draw_empty_channel_profile()
            return

        channel_df = self._result.channel_deltas_for_ffid(ffid)
        self._channel_profile_ax.clear()
        self._channel_profile_ax.set_facecolor(MPL_BG)
        self._channel_profile_ax.grid(True, axis="y", color=MPL_GRID, linewidth=0.4, alpha=0.5)
        for spine in self._channel_profile_ax.spines.values():
            spine.set_color(MPL_GRID)
        self._channel_profile_ax.tick_params(colors=MPL_FG, labelsize=8)

        if channel_df.empty:
            self._draw_empty_channel_profile(
                "This shot does not have comparable receiver records, so only source geometry can be reviewed."
            )
            return

        channels = channel_df["channel"].tolist()
        distances = channel_df["dist"].tolist()
        self._channel_profile_ax.bar(
            channels,
            distances,
            color=Dark.GREEN,
            alpha=0.8,
            width=0.8,
        )
        mean_dist = channel_df["dist"].mean()
        self._channel_profile_ax.axhline(
            mean_dist,
            color=Dark.CYAN,
            linewidth=1.0,
            linestyle="--",
            alpha=0.9,
        )
        peak_row = channel_df.sort_values("dist", ascending=False).iloc[0]
        self._channel_profile_ax.axvline(
            int(peak_row["channel"]),
            color="#F97316",  # deep-orange peak marker (app-specific)
            linewidth=1.0,
            linestyle=":",
            alpha=0.75,
        )
        self._channel_profile_ax.set_title(
            f"FFID {ffid} | Receiver delta by channel",
            color=MPL_FG,
            fontsize=10,
        )
        self._channel_profile_ax.set_xlabel("Channel", color=MPL_FG, fontsize=8)
        self._channel_profile_ax.set_ylabel("Delta (m)", color=MPL_FG, fontsize=8)
        self._channel_profile_fig.tight_layout()
        self._channel_profile_canvas.draw()
        self._channel_profile_label.setText(
            f"Peak receiver delta is CH{int(peak_row['channel'])} at {peak_row['dist']:.2f} m. "
            f"Mean selected-shot receiver delta is {mean_dist:.2f} m across {len(channel_df)} channels."
        )

    def _build_selected_shot_detail(self, ffid: int, pos: dict, source_dist: float) -> str:
        src_a = pos["src_a"]
        src_b = pos["src_b"]
        dx = src_a[0] - src_b[0]
        dy = src_a[1] - src_b[1]
        lines = [
            f"FFID {ffid}",
            f"Source A: ({src_a[0]:.3f}, {src_a[1]:.3f})",
            f"Source B: ({src_b[0]:.3f}, {src_b[1]:.3f})",
            f"Delta: dE={dx:.3f} m, dN={dy:.3f} m, dist={source_dist:.3f} m",
            (
                f"Heading / spread: "
                f"A {pos.get('heading_a', 0.0):.1f} deg / {pos.get('spread_dir_a', 0.0):.1f} deg, "
                f"B {pos.get('heading_b', 0.0):.1f} deg / {pos.get('spread_dir_b', 0.0):.1f} deg"
            ),
        ]

        rx_a = pos.get("rx_a", [])
        rx_b = pos.get("rx_b", [])
        if rx_a and rx_b:
            channel_rows = []
            for idx, (ra, rb) in enumerate(zip(rx_a, rx_b), start=1):
                ch_dx = ra[0] - rb[0]
                ch_dy = ra[1] - rb[1]
                ch_dist = (ch_dx ** 2 + ch_dy ** 2) ** 0.5
                channel_rows.append((idx, ch_dist, ch_dx, ch_dy))
            channel_rows.sort(key=lambda row: row[1], reverse=True)
            lines.append("")
            lines.append("Top channel deltas:")
            for channel, ch_dist, ch_dx, ch_dy in channel_rows[:3]:
                lines.append(
                    f"  CH{channel}: dist={ch_dist:.3f} m, dE={ch_dx:.3f}, dN={ch_dy:.3f}"
                )
        else:
            lines.append("")
            lines.append("Receiver detail unavailable for this shot.")

        return "\n".join(lines)
