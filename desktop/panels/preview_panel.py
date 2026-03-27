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
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.SM)

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
        self._rx_check = QCheckBox("Show Receivers")
        self._rx_check.setChecked(True)
        self._rx_check.stateChanged.connect(self._toggle_receivers)
        opts.addWidget(self._rx_check)

        self._lbl_check = QCheckBox("Show Labels")
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
        self._ax.text(0.5, 0.42, "Load NPD / Track file to preview",
                      transform=self._ax.transAxes,
                      ha="center", va="center",
                      color="#475569", fontsize=12)
        self._ax.text(0.5, 0.35, "Source positions and receiver geometry will be displayed here",
                      transform=self._ax.transAxes,
                      ha="center", va="center",
                      color="#334155", fontsize=9)
        self._canvas.draw()

    def set_collection(self, collection):
        self._collection = collection
        if not collection or collection.n_shots == 0:
            self._draw_empty()
            return
        self._slider.setMaximum(collection.n_shots - 1)
        self._current_idx = 0
        self._slider.setValue(0)
        self._draw_track()

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

        # Highlight current shot
        if 0 <= self._current_idx < c.n_shots:
            shot = c.shots[self._current_idx]
            self._ax.scatter(
                [shot.source_x], [shot.source_y],
                c='white', s=40, zorder=5, marker='o', edgecolors=MPL_ACCENT)

            # Receivers
            if self._show_receivers and shot.receivers:
                rx_x = [r.x for r in shot.receivers]
                rx_y = [r.y for r in shot.receivers]
                self._ax.scatter(
                    rx_x, rx_y, c=MPL_RECEIVER, s=2, zorder=3, alpha=0.6)

            # Detail
            self._detail_label.setText(
                f"FFID: {shot.ffid}  |  "
                f"Source: ({shot.source_x:.1f}, {shot.source_y:.1f})  |  "
                f"Time: {shot.hour:02d}:{shot.minute:02d}:{shot.second:02d}  |  "
                f"Ch: {shot.n_channels}  |  "
                f"Heading: {shot.heading:.1f} deg")

        self._ax.set_xlabel("Easting (m)", color=MPL_FG, fontsize=9)
        self._ax.set_ylabel("Northing (m)", color=MPL_FG, fontsize=9)
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
