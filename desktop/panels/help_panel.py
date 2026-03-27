"""HelpPanel — Usage guide, keyboard shortcuts, P190 format reference."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard


HELP_SECTIONS = [
    ("Style A Workflow (NPD + Geometry)", [
        "1. Input: Load NPD navigation file + Track file",
        "2. Select GPS sources (Front/Tail Buoy)",
        "3. Header: Edit survey metadata H Records",
        "4. CRS: Select coordinate reference system",
        "5. Geometry: Configure source/receiver offsets",
        "6. Preview: Verify track map and shot positions",
        "7. Click Convert (Ctrl+Enter)",
        "8. Review results, feathering analysis",
    ]),
    ("Style B Workflow (RadExPro Export)", [
        "1. Input: Load RadExPro header export TSV",
        "2. Header: Edit survey metadata H Records",
        "3. CRS: Select coordinate reference system",
        "4. Click Convert (Ctrl+Enter)",
        "5. Review results and QC validation",
    ]),
    ("Keyboard Shortcuts", [
        "Ctrl+Enter  --  Start conversion",
        "Escape      --  Go back to Input",
    ]),
    ("P190 Record Format", [
        "H Record: 80-char header (survey metadata)",
        "S Record: Source position per shot (FFID, lat/lon, UTM, time)",
        "R Record: Receiver positions (3 groups per line, 48ch = 16 lines)",
        "Fixed-width text format, 80 characters per line",
    ]),
    ("Interpolation Methods", [
        "Linear: Standard RadExPro-style equal spacing",
        "Catenary: Physics-based cable shape (deep water)",
        "Spline: Cubic interpolation through control points",
        "Feathering: Cross-current displacement model with alpha exponent",
    ]),
]


class HelpPanel(QWidget):
    """Usage instructions and P190 format guide."""

    panel_title = "Help"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        outer.setSpacing(Space.SM)

        # Title
        title = QLabel("P190 NavConverter Help")
        title.setStyleSheet(f"""
            color: {Dark.TEXT_BRIGHT};
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            background: transparent; border: none;
        """)
        outer.addWidget(title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        content = QVBoxLayout(container)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(Space.MD)

        for section_title, items in HELP_SECTIONS:
            card = SectionCard(section_title)
            for item in items:
                lbl = QLabel(item)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"""
                    color: {Dark.TEXT};
                    font-size: {Font.SM}px;
                    background: transparent;
                    border: none;
                    padding-left: 8px;
                """)
                card.content_layout.addWidget(lbl)
            content.addWidget(card)

        content.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)
