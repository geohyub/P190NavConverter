"""ResultsPanel — Post-conversion QC dashboard."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.quality_gauge import QualityGauge
from desktop.widgets.stat_card import StatCard
from desktop.services.explanation_service import build_export_package_story
from desktop.services.output_package_service import (
    build_output_package_entries,
    read_artifact_preview,
    render_output_package_manifest,
    summarize_artifact_inventory,
)


class ResultsPanel(QWidget):
    """Post-conversion results: quality gauge, output info, QC checklist."""

    panel_title = "Results"
    request_compare = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_path = ""
        self._report_path = ""
        self._style = "B"
        self._source_position_mode = "front_gps"
        self._radex_coord_decimals = 5
        self._warnings: list[str] = []
        self._collection = None
        self._plot_path = ""
        self._artifacts = []
        self._artifact_buttons = {}
        self._selected_artifact_key = ""
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
        self._stat_file = StatCard("\ucd9c\ub825 \ud30c\uc77c", "--", 0)
        self._stat_size = StatCard("\ud30c\uc77c \ud06c\uae30", "--", 1)
        self._stat_lines = StatCard("\uc804\uccb4 \ub77c\uc778", "--", 2)
        self._stat_time = StatCard("\uc18c\uc694 \uc2dc\uac04", "--", 3)
        stats_row = QHBoxLayout()
        for s in (self._stat_file, self._stat_size,
                  self._stat_lines, self._stat_time):
            stats_row.addWidget(s)
        stats_col.addLayout(stats_row)
        top_row.addLayout(stats_col, 1)

        layout.addLayout(top_row)

        # QC Details
        qc_card = SectionCard("QC \uac80\uc99d")
        check_wrap = QVBoxLayout()
        check_wrap.setSpacing(4)
        self._check_rows = {}
        for key, label in (
            ("line_length", "80\uce7c\ub7fc \ub77c\uc778 \uae38\uc774"),
            ("record_types", "\ub808\ucf54\ub4dc \ud0c0\uc785 \uc720\ud6a8\uc131"),
            ("h_records", "H \ud5e4\ub354 \ub808\ucf54\ub4dc"),
            ("s_records", "S \uc18c\uc2a4 \ub808\ucf54\ub4dc"),
            ("r_records", "R \uc218\uc2e0\uae30 \ub808\ucf54\ub4dc"),
            ("consistency", "Shot\ubcc4 R \ub808\ucf54\ub4dc \uc77c\uad00\uc131"),
        ):
            row = QHBoxLayout()
            row.setSpacing(Space.SM)
            icon = QLabel("-")
            icon.setFixedWidth(18)
            icon.setStyleSheet(
                f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                f" background:transparent; border:none;")
            text = QLabel(label)
            text.setStyleSheet(
                f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                f" background:transparent; border:none;")
            detail = QLabel("--")
            detail.setStyleSheet(
                f"color: {Dark.TEXT}; font-size: {Font.XS}px;"
                f" background:transparent; border:none;")
            row.addWidget(icon)
            row.addWidget(text, 1)
            row.addWidget(detail)
            check_wrap.addLayout(row)
            self._check_rows[key] = (icon, detail)
        qc_card.content_layout.addLayout(check_wrap)

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

        export_card = SectionCard("\ubcc0\ud658 \uc694\uc57d")
        self._export_text = QTextEdit()
        self._export_text.setReadOnly(True)
        self._export_text.setMaximumHeight(190)
        self._export_text.setStyleSheet(f"""
            QTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
                font-size: {Font.SM}px;
            }}
        """)
        export_card.content_layout.addWidget(self._export_text)
        layout.addWidget(export_card)

        package_card = SectionCard("\ucd9c\ub825 \ud328\ud0a4\uc9c0 \ud30c\uc77c")
        self._package_text = QTextEdit()
        self._package_text.setReadOnly(True)
        self._package_text.setMaximumHeight(170)
        self._package_text.setStyleSheet(f"""
            QTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
                font-family: monospace;
                font-size: {Font.XS}px;
            }}
        """)
        package_card.content_layout.addWidget(self._package_text)
        layout.addWidget(package_card)

        preview_card = SectionCard("\uc0b0\ucd9c\ubb3c \ubbf8\ub9ac\ubcf4\uae30")
        self._artifact_summary = QLabel(
            "Package coverage will appear here once a conversion finishes."
        )
        self._artifact_summary.setWordWrap(True)
        self._artifact_summary.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px; background:transparent; border:none;"
        )
        preview_card.content_layout.addWidget(self._artifact_summary)

        self._artifact_button_row = QHBoxLayout()
        self._artifact_button_row.setSpacing(Space.SM)
        preview_card.content_layout.addLayout(self._artifact_button_row)

        self._artifact_meta = QLabel(
            "Choose an output artifact to inspect its first lines or package meaning."
        )
        self._artifact_meta.setWordWrap(True)
        self._artifact_meta.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px; background:transparent; border:none;"
        )
        preview_card.content_layout.addWidget(self._artifact_meta)

        self._artifact_preview = QTextEdit()
        self._artifact_preview.setReadOnly(True)
        self._artifact_preview.setMaximumHeight(220)
        self._artifact_preview.setStyleSheet(f"""
            QTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: {Font.XS}px;
            }}
        """)
        self._artifact_preview.setPlainText(
            "Run a conversion to browse generated artifacts and preview their contents."
        )
        preview_card.content_layout.addWidget(self._artifact_preview)

        self._artifact_image_label = QLabel(
            "Image preview will appear here for generated PNG outputs."
        )
        self._artifact_image_label.setAlignment(Qt.AlignCenter)
        self._artifact_image_label.setMinimumHeight(220)
        self._artifact_image_label.setStyleSheet(f"""
            QLabel {{
                background: rgba(10,14,23,0.45);
                color: {Dark.MUTED};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
            }}
        """)
        self._artifact_image_label.hide()
        preview_card.content_layout.addWidget(self._artifact_image_label)
        layout.addWidget(preview_card)

        # Output path + actions
        path_card = SectionCard("Output")
        self._path_label = QLabel("\ucd9c\ub825 \uc5c6\uc74c")
        self._path_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_card.content_layout.addWidget(self._path_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(Space.SM)

        self._open_folder_btn = QPushButton("\ud3f4\ub354 \uc5f4\uae30")
        self._open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._open_report_btn = QPushButton("\ub9ac\ud3ec\ud2b8 \ubcf4\uae30")
        self._open_report_btn.clicked.connect(self._open_report)
        btn_row.addWidget(self._open_report_btn)

        self._export_plot_btn = QPushButton("Track Plot \ub0b4\ubcf4\ub0b4\uae30")
        self._export_plot_btn.clicked.connect(self._export_track_plot)
        btn_row.addWidget(self._export_plot_btn)

        self._open_plot_btn = QPushButton("Plot \ubcf4\uae30")
        self._open_plot_btn.clicked.connect(self._open_plot)
        btn_row.addWidget(self._open_plot_btn)

        self._open_artifact_btn = QPushButton("\uc120\ud0dd \ud30c\uc77c \uc5f4\uae30")
        self._open_artifact_btn.clicked.connect(self._open_selected_artifact)
        btn_row.addWidget(self._open_artifact_btn)

        self._compare_recent_btn = QPushButton("A/B \ube44\uad50")
        self._compare_recent_btn.clicked.connect(self.request_compare.emit)
        btn_row.addWidget(self._compare_recent_btn)
        btn_row.addStretch()

        for btn in (
            self._open_folder_btn,
            self._open_report_btn,
            self._export_plot_btn,
            self._open_plot_btn,
            self._open_artifact_btn,
            self._compare_recent_btn,
        ):
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

    def set_collection(self, collection):
        self._collection = collection

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
            with open(p, "r", encoding="ascii", errors="replace") as f:
                total_lines = sum(1 for _ in f)
            self._stat_lines.set_value(f"{total_lines:,}")
        self._render_export_story()
        self._render_package_manifest()

    def set_context(
        self,
        *,
        style: str,
        source_position_mode: str,
        radex_coord_decimals,
        warnings: list[str] | None = None,
        elapsed_seconds: float | None = None,
    ):
        self._style = style
        self._source_position_mode = source_position_mode or "front_gps"
        self._radex_coord_decimals = radex_coord_decimals
        self._warnings = list(warnings or [])
        if elapsed_seconds is not None:
            self._stat_time.set_value(f"{elapsed_seconds:.1f}s")
        self._render_export_story()

    def set_qc_result(self, qc_result):
        passed = qc_result.passed
        score = 100 if passed else 50
        label = "PASS" if passed else "WARN"
        self._gauge.set_value(score, label)

        details = [
            f"Total lines: {qc_result.total_lines:,}",
            f"H records: {qc_result.h_records}",
            f"S records: {qc_result.s_records:,}",
            f"R records: {qc_result.r_records:,}",
            f"Line length errors: {qc_result.line_length_errors}",
            f"Invalid record types: {qc_result.invalid_records}",
        ]
        if qc_result.issues:
            details.append("")
            details.append("Top issues:")
            for issue in qc_result.issues[:6]:
                details.append(f"- {issue}")
        else:
            details.append("")
            details.append("No structural P190 issues were detected.")
        self._qc_text.setPlainText("\n".join(details))

        self._set_check_row(
            "line_length",
            "pass" if qc_result.line_length_errors == 0 else "fail",
            "OK" if qc_result.line_length_errors == 0 else f"{qc_result.line_length_errors} issue(s)",
        )
        self._set_check_row(
            "record_types",
            "pass" if qc_result.invalid_records == 0 else "fail",
            "OK" if qc_result.invalid_records == 0 else f"{qc_result.invalid_records} invalid",
        )
        self._set_check_row(
            "h_records",
            "pass" if qc_result.h_records > 0 else "warning",
            f"{qc_result.h_records}",
        )
        self._set_check_row(
            "s_records",
            "pass" if qc_result.s_records > 0 else "warning",
            f"{qc_result.s_records:,}",
        )
        self._set_check_row(
            "r_records",
            "pass" if qc_result.r_records > 0 else "warning",
            f"{qc_result.r_records:,}",
        )
        inconsistent = any("Inconsistent R records" in issue for issue in qc_result.issues)
        self._set_check_row(
            "consistency",
            "warning" if inconsistent else "pass",
            "Check issues list" if inconsistent else "OK",
        )

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

    def _export_track_plot(self):
        if not self._collection or not self._output_path:
            return

        try:
            from p190converter.engine.qc.plot import generate_track_plot

            out = Path(self._output_path)
            plot_path = str(out.with_name(out.stem + "_Track_Plot.png"))
            generate_track_plot(
                self._collection,
                plot_path,
                title=f"Converted Geometry - {self._collection.line_name or out.stem}",
                show_receivers=any(s.receivers for s in self._collection.shots),
            )
            self._plot_path = plot_path
            self._render_package_manifest()
            self._export_text.append(
                "\nTrack plot exported to help visually review source trend and receiver spread."
            )
        except Exception as exc:
            self._export_text.append(f"\nTrack plot export failed: {exc}")

    def _open_plot(self):
        if self._plot_path and os.path.isfile(self._plot_path):
            try:
                os.startfile(self._plot_path)
            except OSError:
                pass

    def _open_selected_artifact(self):
        artifact = self._selected_artifact()
        if artifact and artifact.exists:
            try:
                os.startfile(str(artifact.path))
            except OSError:
                pass

    def _set_check_row(self, key: str, status: str, detail: str):
        icon, detail_label = self._check_rows[key]
        if status == "pass":
            color = "#10B981"
            marker = "+"
        elif status == "fail":
            color = "#EF4444"
            marker = "x"
        else:
            color = "#F59E0B"
            marker = "!"
        icon.setText(marker)
        icon.setStyleSheet(
            f"color: {color}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        detail_label.setText(detail)
        detail_label.setStyleSheet(
            f"color: {color}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")

    def _render_export_story(self):
        if not self._output_path:
            self._export_text.setPlainText(
                "Run a conversion to see the exported files, compatibility notes, and conversion warnings."
            )
            return
        self._export_text.setPlainText(
            build_export_package_story(
                self._output_path,
                self._style,
                self._radex_coord_decimals,
                source_position_mode=self._source_position_mode,
                warnings=self._warnings,
            )
        )

    def _render_package_manifest(self):
        if not self._output_path:
            self._package_text.setPlainText(
                "Run a conversion to inspect the generated package files."
            )
            self._set_artifact_entries([])
            return

        artifacts = build_output_package_entries(
            self._output_path,
            report_path=self._report_path,
            track_plot_path=self._plot_path,
        )
        self._package_text.setPlainText(render_output_package_manifest(artifacts))
        self._set_artifact_entries(artifacts)

    def _set_artifact_entries(self, artifacts):
        self._artifacts = artifacts
        while self._artifact_button_row.count():
            item = self._artifact_button_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._artifact_buttons = {}

        if not artifacts:
            self._selected_artifact_key = ""
            self._artifact_summary.setText(
                "Package coverage will appear here once a conversion finishes."
            )
            self._artifact_meta.setText(
                "Choose an output artifact to inspect its first lines or package meaning."
            )
            self._artifact_preview.setPlainText(
                "Run a conversion to browse generated artifacts and preview their contents."
            )
            self._artifact_image_label.hide()
            return

        self._artifact_summary.setText(summarize_artifact_inventory(artifacts))
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
        existing = {artifact.key: artifact for artifact in artifacts}
        button_keys = [key for key in preferred_order if key in existing]
        extra_keys = [
            artifact.key for artifact in artifacts if artifact.key not in button_keys
        ]
        button_keys.extend(extra_keys)

        for key in button_keys[:8]:
            artifact = existing[key]
            btn = QPushButton(artifact.label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(
                f"{artifact.note}\nStatus: {'Ready' if artifact.exists else 'Not generated'}"
            )
            btn.clicked.connect(
                lambda _checked=False, artifact_key=artifact.key: self._select_artifact(artifact_key)
            )
            self._artifact_button_row.addWidget(btn)
            self._artifact_buttons[artifact.key] = btn
        self._artifact_button_row.addStretch()

        selected_key = self._selected_artifact_key
        if selected_key not in existing or not existing[selected_key].exists:
            selected_key = button_keys[0]
        self._select_artifact(selected_key)

    def _selected_artifact(self):
        for artifact in self._artifacts:
            if artifact.key == self._selected_artifact_key:
                return artifact
        return None

    def _select_artifact(self, artifact_key: str):
        self._selected_artifact_key = artifact_key
        artifact = self._selected_artifact()
        if artifact is None:
            return

        for key, button in self._artifact_buttons.items():
            active = key == artifact_key
            item = next((entry for entry in self._artifacts if entry.key == key), None)
            exists = item.exists if item else False
            border = Dark.CYAN if active else (Dark.BORDER if exists else "#5B6474")
            background = Dark.NAVY if exists else "#111827"
            foreground = Dark.TEXT if exists else Dark.MUTED
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

        status = "Ready" if artifact.exists else "Not generated"
        self._artifact_meta.setText(
            f"{artifact.label}: {artifact.note} | Status: {status}"
        )
        self._artifact_preview.setPlainText(read_artifact_preview(artifact))
        self._render_artifact_image_preview(artifact)

    def _render_artifact_image_preview(self, artifact):
        if artifact.kind != "image" or not artifact.exists:
            self._artifact_image_label.hide()
            self._artifact_image_label.setPixmap(QPixmap())
            self._artifact_image_label.setText(
                "Image preview will appear here for generated PNG outputs."
            )
            return

        pixmap = QPixmap(str(artifact.path))
        if pixmap.isNull():
            self._artifact_image_label.show()
            self._artifact_image_label.setText(
                "Image preview could not be loaded. Use Open Selected to inspect the file directly."
            )
            self._artifact_image_label.setPixmap(QPixmap())
            return

        scaled = pixmap.scaled(
            900,
            260,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._artifact_image_label.show()
        self._artifact_image_label.setPixmap(scaled)
        self._artifact_image_label.setText("")
