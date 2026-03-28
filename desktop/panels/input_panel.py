"""InputPanel — File selection, Style A/B mode, profile management."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QStackedWidget,
    QCheckBox, QFileDialog, QSizePolicy,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.drop_zone import FileDropZone
from desktop.widgets.form_field import FormField
from desktop.widgets.stat_card import StatCard
from desktop.services.explanation_service import (
    SOURCE_POSITION_OPTIONS,
    SOURCE_POSITION_DESCRIPTIONS,
    build_conversion_story,
    describe_coord_decimals,
)


class InputPanel(QWidget):
    """File input + Style A/B mode + profile management."""

    panel_title = "Input"

    file_loaded = Signal(str, str)      # file_type, path
    style_changed = Signal(str)         # "A" or "B"

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._current_style = "B"
        self._build_ui()

    @property
    def current_style(self) -> str:
        return self._current_style

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # ── Profile Row ──
        profile_row = QHBoxLayout()
        profile_row.setSpacing(Space.SM)

        profile_lbl = QLabel("Profile")
        profile_lbl.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        profile_row.addWidget(profile_lbl)

        self._profile_combo = QComboBox()
        self._profile_combo.setMinimumWidth(180)
        self._profile_combo.setStyleSheet(f"""
            QComboBox {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 4px 8px;
                font-size: {Font.SM}px;
            }}
        """)
        profile_row.addWidget(self._profile_combo, 1)

        for txt, slot in [("Load", self._load_profile),
                          ("Save", self._save_profile),
                          ("Del", self._delete_profile)]:
            btn = QPushButton(txt)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                    padding: 0 10px;
                    font-size: {Font.XS}px;
                }}
                QPushButton:hover {{ border-color: {Dark.CYAN}; }}
            """)
            btn.clicked.connect(slot)
            profile_row.addWidget(btn)

        layout.addLayout(profile_row)

        # ── Style Selector ──
        style_card = SectionCard("Conversion Style")
        style_row = QHBoxLayout()
        style_row.setSpacing(Space.SM)

        self._style_btns = {}
        for label, key in [("Style A: NPD + Geometry", "A"),
                           ("Style B: RadExPro Export", "B")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(key == "B")
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._set_style(k))
            style_row.addWidget(btn)
            self._style_btns[key] = btn

        self._update_style_buttons()
        style_card.content_layout.addLayout(style_row)

        self._mode_desc = QLabel("")
        self._mode_desc.setWordWrap(True)
        self._mode_desc.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        style_card.content_layout.addWidget(self._mode_desc)

        # Batch mode toggle
        batch_row = QHBoxLayout()
        self._batch_check = QCheckBox("Batch Mode (multiple files)")
        self._batch_check.setStyleSheet(f"""
            QCheckBox {{ color: {Dark.MUTED}; font-size: {Font.SM}px; }}
        """)
        self._batch_check.stateChanged.connect(self._on_batch_toggle)
        batch_row.addWidget(self._batch_check)
        self._batch_info = QLabel("")
        self._batch_info.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        self._batch_info.setVisible(False)
        batch_row.addWidget(self._batch_info, 1)
        style_card.content_layout.addLayout(batch_row)

        layout.addWidget(style_card)

        # Batch file storage
        self._batch_files: list = []

        # ── Input Cards (Style A / Style B stacked) ──
        self._input_stack = QStackedWidget()

        # Style A page
        style_a = QWidget()
        a_layout = QVBoxLayout(style_a)
        a_layout.setContentsMargins(0, 0, 0, 0)
        a_layout.setSpacing(Space.SM)

        self._npd_drop = FileDropZone(
            "NPD File (NaviPac navigation)",
            "NPD Files (*.NPD *.npd);;All (*)")
        self._npd_drop.file_selected.connect(
            lambda p: self._handle_file_selected("npd", p))
        a_layout.addWidget(self._npd_drop)

        self._track_drop = FileDropZone(
            "Track File (header export)",
            "Track Files (*.txt *.tsv *.csv);;All (*)")
        self._track_drop.file_selected.connect(
            lambda p: self._handle_file_selected("track", p))
        a_layout.addWidget(self._track_drop)

        # GPS source selection
        gps_row = QHBoxLayout()
        gps_row.setSpacing(Space.SM)
        gps_row.addWidget(QLabel("Front GPS:"))
        self._front_gps = QComboBox()
        self._front_gps.setMinimumWidth(140)
        gps_row.addWidget(self._front_gps)
        gps_row.addWidget(QLabel("Tail GPS:"))
        self._tail_gps = QComboBox()
        self._tail_gps.setMinimumWidth(140)
        gps_row.addWidget(self._tail_gps)
        gps_row.addStretch()
        a_layout.addLayout(gps_row)

        for w in style_a.findChildren(QLabel):
            w.setStyleSheet(
                f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                f" background:transparent; border:none;")
        for w in (self._front_gps, self._tail_gps):
            w.setStyleSheet(f"""
                QComboBox {{
                    background: {Dark.DARK}; color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                    padding: 4px 8px; font-size: {Font.SM}px;
                }}
            """)
            w.currentTextChanged.connect(self._refresh_explanation)

        basis_row = QHBoxLayout()
        basis_row.setSpacing(Space.SM)
        basis_lbl = QLabel("Source Basis:")
        basis_lbl.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        basis_row.addWidget(basis_lbl)
        self._source_mode = QComboBox()
        self._source_mode.setMinimumWidth(220)
        self._source_mode.setStyleSheet(f"""
            QComboBox {{
                background: {Dark.DARK}; color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 4px 8px; font-size: {Font.SM}px;
            }}
        """)
        for key, label in SOURCE_POSITION_OPTIONS:
            self._source_mode.addItem(label, userData=key)
        self._source_mode.currentIndexChanged.connect(self._refresh_explanation)
        basis_row.addWidget(self._source_mode)
        basis_row.addStretch()
        a_layout.addLayout(basis_row)

        self._source_mode_hint = QLabel("")
        self._source_mode_hint.setWordWrap(True)
        self._source_mode_hint.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        a_layout.addWidget(self._source_mode_hint)

        self._input_stack.addWidget(style_a)

        # Style B page
        style_b = QWidget()
        b_layout = QVBoxLayout(style_b)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(Space.SM)

        self._radex_drop = FileDropZone(
            "RadExPro Header Export (TSV)",
            "TSV Files (*.txt *.tsv);;All (*)")
        self._radex_drop.file_selected.connect(
            lambda p: self._handle_file_selected("radex", p))
        b_layout.addWidget(self._radex_drop)

        self._input_stack.addWidget(style_b)
        self._input_stack.setCurrentIndex(1)  # Default: Style B
        layout.addWidget(self._input_stack)

        # ── Common fields ──
        common_card = SectionCard("Output")
        self._line_name = FormField("Line Name", "e.g. M1406",
                                     label_width=80)
        common_card.content_layout.addWidget(self._line_name)

        self._output_dir = FormField(
            "Output Dir", "", browse=True, label_width=80)
        self._output_dir.set_browse_callback(self._browse_output_dir)
        common_card.content_layout.addWidget(self._output_dir)

        self._radex_decimals = FormField(
            "Coord Dec.", "5", label_width=80)
        self._radex_decimals.value = "5"
        self._radex_decimals.value_changed.connect(self._refresh_explanation)
        common_card.content_layout.addWidget(self._radex_decimals)

        self._coord_hint = QLabel("")
        self._coord_hint.setWordWrap(True)
        self._coord_hint.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        common_card.content_layout.addWidget(self._coord_hint)

        layout.addWidget(common_card)

        self._story_card = SectionCard("Current Conversion Story")
        self._story_label = QLabel("")
        self._story_label.setWordWrap(True)
        self._story_label.setStyleSheet(f"""
            color: {Dark.TEXT};
            font-size: {Font.SM}px;
            background: transparent;
            border: none;
        """)
        self._story_card.content_layout.addWidget(self._story_label)
        layout.addWidget(self._story_card)

        # ── Summary Stats ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(Space.SM)
        self._stat_shots = StatCard("Shots", "--", 0)
        self._stat_channels = StatCard("Channels", "--", 1)
        self._stat_ffid = StatCard("FFID Range", "--", 2)
        stats_row.addWidget(self._stat_shots)
        stats_row.addWidget(self._stat_channels)
        stats_row.addWidget(self._stat_ffid)
        layout.addLayout(stats_row)

        layout.addStretch()
        self._refresh_explanation()

    # ── Style switching ──

    def _set_style(self, style: str):
        self._current_style = style
        self._input_stack.setCurrentIndex(0 if style == "A" else 1)
        self._update_style_buttons()
        self._refresh_explanation()
        self.style_changed.emit(style)
        self._controller.style_changed.emit(style)

    def _update_style_buttons(self):
        for key, btn in self._style_btns.items():
            active = (key == self._current_style)
            btn.setChecked(active)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Dark.CYAN};
                        color: {Dark.DARK};
                        border: none;
                        border-radius: {Radius.SM}px;
                        font-size: {Font.SM}px;
                        font-weight: {Font.SEMIBOLD};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Dark.NAVY};
                        color: {Dark.MUTED};
                        border: 1px solid {Dark.BORDER};
                        border-radius: {Radius.SM}px;
                        font-size: {Font.SM}px;
                    }}
                    QPushButton:hover {{ border-color: {Dark.CYAN}; }}
                """)

    # ── Data access ──

    def get_config_values(self) -> dict:
        return {
            "style": self._current_style,
            "input_file": self._radex_drop.value,
            "npd_file": self._npd_drop.value,
            "track_file": self._track_drop.value,
            "output_dir": self._output_dir.value,
            "line_name": self._line_name.value,
            "front_gps": self._front_gps.currentText(),
            "tail_gps": self._tail_gps.currentText(),
            "source_position_mode": self.get_source_position_mode(),
            "radex_coord_decimals": self._radex_decimals.value,
            "batch_mode": self._batch_check.isChecked(),
            "batch_files": list(self._batch_files),
        }

    def get_line_name(self) -> str:
        return self._line_name.value

    def set_line_name(self, name: str):
        self._line_name.value = name
        self._refresh_explanation()

    def set_radex_coord_decimals(self, val):
        self._radex_decimals.value = str(val)
        self._refresh_explanation()

    def get_source_position_mode(self) -> str:
        mode = self._source_mode.currentData()
        return str(mode or "front_gps")

    def set_source_position_mode(self, mode: str):
        key = mode or "front_gps"
        idx = self._source_mode.findData(key)
        if idx < 0:
            idx = 0
        self._source_mode.setCurrentIndex(idx)
        self._refresh_explanation()

    def update_summary(self, text: str):
        """Parse summary text: 'Shots: N | Channels: N | FFID: lo-hi'."""
        parts = text.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("Shots"):
                self._stat_shots.set_value(part.split(":")[1].strip())
            elif part.startswith("Channels"):
                self._stat_channels.set_value(part.split(":")[1].strip())
            elif part.startswith("FFID"):
                self._stat_ffid.set_value(part.split(":")[1].strip())
        self._refresh_explanation()

    def update_gps_sources(self, sources: list[str]):
        for combo in (self._front_gps, self._tail_gps):
            combo.clear()
            combo.addItems(sources)
        self._refresh_explanation()

    def set_selected_gps_sources(self, front: str, tail: str):
        idx = self._front_gps.findText(front)
        if idx >= 0:
            self._front_gps.setCurrentIndex(idx)
        idx = self._tail_gps.findText(tail)
        if idx >= 0:
            self._tail_gps.setCurrentIndex(idx)
        self._refresh_explanation()

    def restore_config(self, saved: dict):
        style = saved.get("style", "B")
        self._set_style(style)
        if saved.get("line_name"):
            self._line_name.value = saved["line_name"]
        files = saved.get("files", {})
        if files.get("input_file"):
            self._radex_drop.value = files["input_file"]
        if files.get("npd_file"):
            self._npd_drop.value = files["npd_file"]
        if files.get("track_file"):
            self._track_drop.value = files["track_file"]
        if files.get("output_dir"):
            self._output_dir.value = files["output_dir"]
        gps = saved.get("gps_sources", {})
        if gps:
            self.set_selected_gps_sources(
                gps.get("front", ""), gps.get("tail", ""))
        if saved.get("source_position_mode"):
            self.set_source_position_mode(saved["source_position_mode"])
        if saved.get("export_options", {}).get("radex_coord_decimals"):
            self._radex_decimals.value = str(
                saved["export_options"]["radex_coord_decimals"])
        self._refresh_explanation()

    def refresh_profiles(self):
        from desktop.services.settings_service import SettingsService
        self._profile_combo.clear()
        self._profile_combo.addItems(SettingsService.list_profiles())

    # ── Batch mode ──

    def _on_batch_toggle(self, state):
        batch = (state == 2)  # Qt.Checked
        if batch:
            # Only open dialog if triggered by user click (not programmatic)
            if not self._batch_files:
                self._browse_batch()
        else:
            self._batch_files.clear()
            self._batch_info.setVisible(False)
        self._refresh_explanation()

    def _browse_batch(self):
        if self._current_style == "B":
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Select Batch Files", "",
                "TSV Files (*.txt *.tsv);;All (*)")
            if paths:
                self._batch_files = paths
                self._batch_info.setText(f"{len(paths)} files selected")
                self._batch_info.setVisible(True)
            else:
                self._batch_check.setChecked(False)
        else:
            folder = QFileDialog.getExistingDirectory(
                self, "Select Folder with NPD + Track Pairs")
            if folder:
                import glob
                npd_files = sorted(glob.glob(
                    str(Path(folder) / "*.NPD")) + glob.glob(
                    str(Path(folder) / "*.npd")))
                if npd_files:
                    self._batch_files = npd_files
                    self._batch_info.setText(
                        f"{len(npd_files)} NPD files found")
                    self._batch_info.setVisible(True)
                else:
                    self._controller.show_toast(
                        "No NPD files found in folder", "warning")
                    self._batch_check.setChecked(False)
            else:
                self._batch_check.setChecked(False)
        self._refresh_explanation()

    # ── Browse ──

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Output Directory")
        if path:
            self._output_dir.value = path
            self._refresh_explanation()

    # ── Profile management (delegated to main.py) ──

    def _save_profile(self):
        name = self._profile_combo.currentText().strip()
        if not name:
            self._controller.show_toast("Enter profile name", "warning")
            return
        self._controller.profile_saved.emit(name)

    def _load_profile(self):
        name = self._profile_combo.currentText().strip()
        if not name:
            return
        self._controller.profile_loaded.emit(name)

    def _delete_profile(self):
        name = self._profile_combo.currentText().strip()
        if not name:
            return
        self._controller.profile_deleted.emit(name)

    def _handle_file_selected(self, file_type: str, path: str):
        self._refresh_explanation()
        self.file_loaded.emit(file_type, path)

    def _refresh_explanation(self, *_):
        style = self._current_style
        self._mode_desc.setText(
            "Style A rebuilds source/receiver geometry from Track timing + NPD GPS + offsets."
            if style == "A"
            else "Style B repackages an existing RadExPro geometry export into the P190 delivery format."
        )

        coord_text, coord_ok = describe_coord_decimals(self._radex_decimals.value)
        self._coord_hint.setText(coord_text)
        self._coord_hint.setStyleSheet(
            f"color: {Dark.MUTED if coord_ok else '#F59E0B'};"
            f" font-size: {Font.XS}px; background:transparent; border:none;"
        )

        source_mode = self.get_source_position_mode()
        self._source_mode_hint.setText(
            SOURCE_POSITION_DESCRIPTIONS.get(
                source_mode, SOURCE_POSITION_DESCRIPTIONS["front_gps"]
            )
        )

        self._story_label.setText(
            build_conversion_story(style, self.get_config_values())
        )
