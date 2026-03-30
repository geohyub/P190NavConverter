"""PreviewPanel — Track map + shot selector using matplotlib Qt backend."""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QCheckBox, QSizePolicy,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

# Matplotlib dark theme colors
MPL_BG = "#0a0e17"
MPL_FG = "#94a3b8"
MPL_GRID = "#1e293b"
MPL_ACCENT = "#06b6d4"
MPL_SOURCE = "#f59e0b"
MPL_RECEIVER = "#06b6d4"


class PreviewPanel(QWidget):
    """Interactive track map with shot selector."""

    panel_title = "Preview"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collection = None
        self._current_idx = 0
        self._show_receivers = True
        self._show_labels = False
        self._preview_mode = "empty"
        self._preview_note = ""
        self._line_name = ""
        self._preview_warnings = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.SM)

        self._mode_label = QLabel("Preview scope will appear after a file is loaded.")
        self._mode_label.setWordWrap(True)
        self._mode_label.setStyleSheet(f"""
            color: {Dark.TEXT};
            font-size: {Font.SM}px;
            background: rgba(6,182,212,0.08);
            border: 1px solid rgba(6,182,212,0.2);
            border-radius: {Radius.SM}px;
            padding: 8px 10px;
        """)
        layout.addWidget(self._mode_label)

        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._summary_label)

        # Matplotlib canvas
        self._fig = Figure(figsize=(8, 4), dpi=100, facecolor=MPL_BG)
        self._ax = self._fig.add_subplot(111)
        self._style_axes()
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas, 1)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setSpacing(Space.SM)

        prev_btn = QPushButton("<")
        prev_btn.setFixedSize(32, 28)
        prev_btn.clicked.connect(self._prev_shot)
        ctrl.addWidget(prev_btn)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(0)
        self._slider.valueChanged.connect(self._on_slider)
        ctrl.addWidget(self._slider, 1)

        next_btn = QPushButton(">")
        next_btn.setFixedSize(32, 28)
        next_btn.clicked.connect(self._next_shot)
        ctrl.addWidget(next_btn)

        self._shot_label = QLabel("Shot --/--")
        self._shot_label.setFixedWidth(120)
        self._shot_label.setStyleSheet(
            f"color: {Dark.TEXT}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        ctrl.addWidget(self._shot_label)

        for btn in (prev_btn, next_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                }}
                QPushButton:hover {{ border-color: {Dark.CYAN}; }}
            """)

        layout.addLayout(ctrl)

        # Options row
        opts = QHBoxLayout()
        self._rx_check = QCheckBox("\uc218\uc2e0\uae30 \ud45c\uc2dc")
        self._rx_check.setChecked(True)
        self._rx_check.stateChanged.connect(self._toggle_receivers)
        opts.addWidget(self._rx_check)

        self._lbl_check = QCheckBox("FFID \ub77c\ubca8")
        self._lbl_check.setChecked(False)
        self._lbl_check.stateChanged.connect(self._toggle_labels)
        opts.addWidget(self._lbl_check)

        for cb in (self._rx_check, self._lbl_check):
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {Dark.MUTED}; font-size: {Font.SM}px; }}
            """)
        opts.addStretch()
        layout.addLayout(opts)

        # Shot detail
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(f"""
            color: {Dark.TEXT};
            font-family: monospace;
            font-size: {Font.XS}px;
            background: {Dark.DARK};
            border: 1px solid {Dark.BORDER};
            border-radius: {Radius.SM}px;
            padding: 8px;
        """)
        self._detail_label.setFixedHeight(60)
        layout.addWidget(self._detail_label)

        self._draw_empty()

    def _style_axes(self):
        ax = self._ax
        ax.set_facecolor(MPL_BG)
        ax.tick_params(colors=MPL_FG, labelsize=8)
        ax.spines['bottom'].set_color(MPL_GRID)
        ax.spines['left'].set_color(MPL_GRID)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def _draw_empty(self):
        self._preview_mode = "empty"
        self._ax.clear()
        self._style_axes()
        # Hide axes for clean empty state
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        self._ax.spines['bottom'].set_visible(False)
        self._ax.spines['left'].set_visible(False)

        # Icon-like marker
        self._ax.text(0.5, 0.55, "\u25CB",
                      transform=self._ax.transAxes,
                      ha="center", va="center",
                      color="#334155", fontsize=48)
        self._ax.text(0.5, 0.42, "NPD / Track \ud30c\uc77c\uc744 \ub85c\ub4dc\ud558\uba74 \ubbf8\ub9ac\ubcf4\uae30\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4",
                      transform=self._ax.transAxes,
                      ha="center", va="center",
                      color="#475569", fontsize=12)
        self._ax.text(0.5, 0.35, "\uc18c\uc2a4 \uc704\uce58\uc640 \uc218\uc2e0\uae30 Geometry\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4",
                      transform=self._ax.transAxes,
                      ha="center", va="center",
                      color="#334155", fontsize=9)
        self._canvas.draw()
        self._mode_label.setText(
            "Load a RadEx export or Track file to preview the geometry that will drive conversion."
        )
        self._summary_label.setText("")
        self._detail_label.setText("")

    def set_collection(
        self,
        collection,
        preview_mode: str = "loaded_geometry",
        note: str = "",
        warnings=None,
    ):
        self._collection = collection
        self._preview_mode = preview_mode
        self._preview_note = note
        self._preview_warnings = warnings or []
        if not collection or collection.n_shots == 0:
            self._draw_empty()
            return
        has_receivers = any(shot.receivers for shot in collection.shots)
        self._rx_check.setEnabled(has_receivers)
        if not has_receivers:
            self._rx_check.setChecked(False)
        self._slider.setMaximum(collection.n_shots - 1)
        self._current_idx = 0
        self._slider.setValue(0)
        self._update_summary()
        self._draw_track()

    def set_track_data(self, track_data, line_name: str = ""):
        """Preview track SOU positions even before Style A conversion runs."""
        from p190converter.models.shot_gather import (
            ShotGather, ShotGatherCollection,
        )

        self._line_name = line_name or self._line_name
        shots = []
        for row in track_data.df.itertuples(index=False):
            shots.append(
                ShotGather(
                    ffid=int(row.ffid),
                    source_x=float(row.sou_x),
                    source_y=float(row.sou_y),
                    day=int(row.day),
                    hour=int(row.hour),
                    minute=int(row.minute),
                    second=int(row.second),
                    line_name=self._line_name,
                )
            )

        collection = ShotGatherCollection(
            shots=shots,
            line_name=self._line_name,
            n_channels=track_data.n_channels,
        )
        self.set_collection(
            collection,
            preview_mode="track_source",
            note=(
                "Track preview shows SOU_X/SOU_Y shot positions before Style A offsets, receiver interpolation, and feathering corrections are applied."
            ),
            warnings=track_data.warnings,
        )

    def set_line_name(self, line_name: str):
        self._line_name = line_name or self._line_name
        self._update_summary()

    def _update_summary(self):
        c = self._collection
        if not c:
            return
        line_name = self._line_name or c.line_name or "Unassigned line"
        has_receivers = any(shot.receivers for shot in c.shots)
        mode_title = {
            "track_source": "Track Source Preview",
            "loaded_geometry": "Loaded Geometry Preview",
            "converted_geometry": "Converted Geometry Preview",
        }.get(self._preview_mode, "Preview")
        xs = [s.source_x for s in c.shots]
        ys = [s.source_y for s in c.shots]
        span_x = max(xs) - min(xs) if xs else 0.0
        span_y = max(ys) - min(ys) if ys else 0.0
        warning_text = ""
        if self._preview_warnings:
            warning_text = f" Warning: {self._preview_warnings[0]}"
        self._mode_label.setText(
            f"{mode_title}: {self._preview_note or 'Inspect shot order, source trend, and receiver spread before export.'}"
        )
        self._summary_label.setText(
            f"Line: {line_name}  |  Shots: {c.n_shots:,}  |  "
            f"Receivers shown: {'Yes' if has_receivers else 'No'}  |  "
            f"Span: {span_x:.1f}m E-W x {span_y:.1f}m N-S.{warning_text}"
        )

    def _draw_track(self):
        c = self._collection
        if not c:
            return
        self._ax.clear()
        self._style_axes()

        xs = [s.source_x for s in c.shots]
        ys = [s.source_y for s in c.shots]

        # Track line
        self._ax.plot(xs, ys, '-', color=MPL_GRID, linewidth=0.5, alpha=0.5)

        # Source scatter
        self._ax.scatter(xs, ys, c=MPL_SOURCE, s=4, zorder=2, alpha=0.7)

        if self._show_labels:
            label_step = max(len(xs) // 10, 1)
            for idx in range(0, len(xs), label_step):
                shot = c.shots[idx]
                self._ax.annotate(
                    str(shot.ffid),
                    (shot.source_x, shot.source_y),
                    textcoords="offset points",
                    xytext=(3, 3),
                    color=MPL_FG,
                    fontsize=6,
                    alpha=0.75,
                )

        # Highlight current shot
        if 0 <= self._current_idx < c.n_shots:
            shot = c.shots[self._current_idx]
            self._ax.scatter(
                [shot.source_x], [shot.source_y],
                c='white', s=40, zorder=5, marker='o', edgecolors=MPL_ACCENT)
            self._ax.annotate(
                f"FFID {shot.ffid}",
                (shot.source_x, shot.source_y),
                textcoords="offset points",
                xytext=(8, 8),
                color="white",
                fontsize=8,
            )

            # Receivers
            if self._show_receivers and shot.receivers:
                rx_x = [r.x for r in shot.receivers]
                rx_y = [r.y for r in shot.receivers]
                self._ax.scatter(
                    rx_x, rx_y, c=MPL_RECEIVER, s=2, zorder=3, alpha=0.6)

            # Detail
            heading_text = (
                f"{shot.heading:.1f} deg" if shot.heading else "--"
            )
            self._detail_label.setText(
                f"FFID: {shot.ffid}  |  "
                f"Source: ({shot.source_x:.1f}, {shot.source_y:.1f})  |  "
                f"Time: {shot.hour:02d}:{shot.minute:02d}:{shot.second:02d}  |  "
                f"Ch: {shot.n_channels if shot.n_channels else '--'}  |  "
                f"Heading: {heading_text}")

        self._ax.set_xlabel("Easting (m)", color=MPL_FG, fontsize=9)
        self._ax.set_ylabel("Northing (m)", color=MPL_FG, fontsize=9)
        if self._line_name or c.line_name:
            self._ax.set_title(
                self._line_name or c.line_name,
                color=MPL_FG,
                fontsize=10,
            )
        self._ax.set_aspect("equal", adjustable="datalim")
        self._fig.tight_layout()
        self._canvas.draw()

        self._shot_label.setText(
            f"Shot {self._current_idx + 1}/{c.n_shots}")

    def _on_slider(self, value: int):
        self._current_idx = value
        self._draw_track()

    def _prev_shot(self):
        if self._current_idx > 0:
            self._slider.setValue(self._current_idx - 1)

    def _next_shot(self):
        if self._collection and self._current_idx < self._collection.n_shots - 1:
            self._slider.setValue(self._current_idx + 1)

    def _toggle_receivers(self, state):
        self._show_receivers = bool(state)
        self._draw_track()

    def _toggle_labels(self, state):
        self._show_labels = bool(state)
        self._draw_track()
