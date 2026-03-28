"""GeometryPanel — Marine geometry offset configuration (Style A only)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QButtonGroup,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.widgets.form_field import FormField
from desktop.widgets.geometry_diagram import GeometryDiagram
from desktop.services.explanation_service import (
    INTERP_METHOD_DESCRIPTIONS,
    build_geometry_story,
)


INTERP_METHODS = ["linear", "catenary", "spline", "feathering"]


class GeometryPanel(QWidget):
    """Marine geometry offset editor with real-time diagram."""

    panel_title = "Geometry"

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # Style A banner
        banner = QLabel("  Style A Only -- Marine Geometry Configuration")
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

        self._banner_hint = QLabel(
            "Offsets are entered in vessel coordinates and are used to derive the source-relative receiver geometry written to the export."
        )
        self._banner_hint.setWordWrap(True)
        self._banner_hint.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        layout.addWidget(self._banner_hint)

        # Diagram (expanded for better visibility)
        self._diagram = GeometryDiagram()
        layout.addWidget(self._diagram, 2)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        form = QVBoxLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(Space.SM)

        # Source Offset
        src_card = SectionCard("Source Offset")
        self._src_dx = FormField("Cross-track dx", "0.0", label_width=120)
        self._src_dy = FormField("Along-track dy", "0.0", label_width=120)
        self._src_dx.value = "0.0"
        self._src_dy.value = "0.0"
        self._src_dx.value_changed.connect(self._notify_change)
        self._src_dy.value_changed.connect(self._notify_change)
        src_card.content_layout.addWidget(self._src_dx)
        src_card.content_layout.addWidget(self._src_dy)
        form.addWidget(src_card)

        # RX1 Offset
        rx1_card = SectionCard("First Receiver (RX1) Offset")
        self._rx1_dx = FormField("Cross-track dx", "0.0", label_width=120)
        self._rx1_dy = FormField("Along-track dy", "0.0", label_width=120)
        self._rx1_dx.value = "0.0"
        self._rx1_dy.value = "0.0"
        self._rx1_dx.value_changed.connect(self._notify_change)
        self._rx1_dy.value_changed.connect(self._notify_change)
        rx1_card.content_layout.addWidget(self._rx1_dx)
        rx1_card.content_layout.addWidget(self._rx1_dy)
        form.addWidget(rx1_card)

        # Receiver Array
        arr_card = SectionCard("Receiver Array")
        self._n_ch = FormField("Channels", "48", label_width=120)
        self._rx_interval = FormField("Interval (m)", "3.125", label_width=120)
        self._cable_depth = FormField("Cable Depth (m)", "2.0", label_width=120)
        self._n_ch.value = "48"
        self._rx_interval.value = "3.125"
        self._cable_depth.value = "2.0"
        for f in (self._n_ch, self._rx_interval, self._cable_depth):
            f.value_changed.connect(self._notify_change)
        arr_card.content_layout.addWidget(self._n_ch)
        arr_card.content_layout.addWidget(self._rx_interval)
        arr_card.content_layout.addWidget(self._cable_depth)
        form.addWidget(arr_card)

        # Interpolation Method
        interp_card = SectionCard("Interpolation Method")
        btn_row = QHBoxLayout()
        btn_row.setSpacing(Space.SM)
        self._interp_group = QButtonGroup(self)
        self._interp_btns = {}
        for i, method in enumerate(INTERP_METHODS):
            btn = QPushButton(method.capitalize())
            btn.setCheckable(True)
            btn.setChecked(method == "linear")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            self._interp_group.addButton(btn, i)
            btn_row.addWidget(btn)
            self._interp_btns[method] = btn
        self._interp_group.idClicked.connect(self._on_interp_changed)
        self._update_interp_style()
        interp_card.content_layout.addLayout(btn_row)

        # Feathering alpha
        self._alpha_field = FormField(
            "Alpha (a)", "2.0", label_width=120)
        self._alpha_field.value = "2.0"
        self._alpha_field.value_changed.connect(self._notify_change)
        self._alpha_field.setVisible(False)
        interp_card.content_layout.addWidget(self._alpha_field)

        self._method_hint = QLabel("")
        self._method_hint.setWordWrap(True)
        self._method_hint.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        interp_card.content_layout.addWidget(self._method_hint)

        self._feathering_hint = QLabel(
            "Feathering requires Head/Tail GPS and uses alpha to decide how strongly current-driven bend grows toward the tail."
        )
        self._feathering_hint.setWordWrap(True)
        self._feathering_hint.setStyleSheet(
            f"color: #F59E0B; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        self._feathering_hint.setVisible(False)
        interp_card.content_layout.addWidget(self._feathering_hint)

        form.addWidget(interp_card)

        self._meaning_card = SectionCard("Derived Meaning")
        self._meaning_label = QLabel("")
        self._meaning_label.setWordWrap(True)
        self._meaning_label.setStyleSheet(f"""
            color: {Dark.TEXT};
            font-size: {Font.SM}px;
            background: transparent;
            border: none;
        """)
        self._meaning_card.content_layout.addWidget(self._meaning_label)
        form.addWidget(self._meaning_card)

        # Spread summary
        self._spread_label = QLabel("")
        self._spread_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        form.addWidget(self._spread_label)
        form.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self._notify_change()

    def _on_interp_changed(self, id_: int):
        method = INTERP_METHODS[id_]
        self._alpha_field.setVisible(method == "feathering")
        self._feathering_hint.setVisible(method == "feathering")
        self._update_interp_style()
        self._notify_change()

    def _update_interp_style(self):
        checked_id = self._interp_group.checkedId()
        for i, method in enumerate(INTERP_METHODS):
            btn = self._interp_btns[method]
            active = (i == checked_id)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.CYAN if active else Dark.NAVY};
                    color: {Dark.DARK if active else Dark.MUTED};
                    border: {"none" if active
                             else f"1px solid {Dark.BORDER}"};
                    border-radius: {Radius.SM}px;
                    font-size: {Font.SM}px;
                    padding: 0 14px;
                }}
                QPushButton:hover {{ border-color: #06B6D4; }}
            """)

    def _notify_change(self, *_):
        try:
            src_dx = float(self._src_dx.value or 0)
            src_dy = float(self._src_dy.value or 0)
            rx1_dx = float(self._rx1_dx.value or 0)
            rx1_dy = float(self._rx1_dy.value or 0)
            n_ch = int(self._n_ch.value or 48)
            interval = float(self._rx_interval.value or 3.125)
            depth = float(self._cable_depth.value or 2.0)
        except ValueError:
            return

        self._diagram.update_geometry(
            src_dx, src_dy, rx1_dx, rx1_dy,
            n_ch, interval, depth)

        spread = n_ch * interval
        self._spread_label.setText(
            f"Cable spread: {n_ch} ch x {interval} m = {spread:.1f} m")
        current_method = self.get_geometry().interp_method.lower()
        self._method_hint.setText(
            INTERP_METHOD_DESCRIPTIONS.get(
                current_method,
                INTERP_METHOD_DESCRIPTIONS["linear"],
            )
        )
        self._meaning_label.setText(build_geometry_story(self.get_geometry()))

    def get_geometry(self):
        from p190converter.models.survey_config import MarineGeometry

        checked_id = self._interp_group.checkedId()
        method = INTERP_METHODS[checked_id] if checked_id >= 0 else "linear"

        try:
            return MarineGeometry(
                source_dx=float(self._src_dx.value or 0),
                source_dy=float(self._src_dy.value or 0),
                rx1_dx=float(self._rx1_dx.value or 0),
                rx1_dy=float(self._rx1_dy.value or 0),
                n_channels=int(self._n_ch.value or 48),
                rx_interval=float(self._rx_interval.value or 3.125),
                cable_depth=float(self._cable_depth.value or 2.0),
                interp_method=method,
                feathering_alpha=float(self._alpha_field.value or 2.0),
            )
        except (ValueError, TypeError):
            return MarineGeometry()

    def set_geometry(self, data: dict):
        self._src_dx.value = str(data.get("source_dx", 0))
        self._src_dy.value = str(data.get("source_dy", 0))
        self._rx1_dx.value = str(data.get("rx1_dx", 0))
        self._rx1_dy.value = str(data.get("rx1_dy", 0))
        self._n_ch.value = str(data.get("n_channels", 48))
        self._rx_interval.value = str(data.get("rx_interval", 3.125))
        self._cable_depth.value = str(data.get("cable_depth", 2.0))

        method = data.get("interp_method", "linear")
        if method in INTERP_METHODS:
            idx = INTERP_METHODS.index(method)
            self._interp_group.button(idx).setChecked(True)
            self._on_interp_changed(idx)

        self._alpha_field.value = str(data.get("feathering_alpha", 2.0))
        self._notify_change()

    def set_channel_count(self, n: int):
        self._n_ch.value = str(n)
        self._notify_change()
