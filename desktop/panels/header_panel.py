"""HeaderPanel — P190 H Record editor with categorized form."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QPushButton,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard

# H Record categories and codes
H_CATEGORIES = {
    "Survey": [
        ("H0100", "Survey Area Name"),
        ("H0200", "Survey Date"),
        ("H0300", "Client Name"),
        ("H0400", "Geophysical Contractor"),
        ("H0500", "Positioning Contractor"),
        ("H0600", "Position Processing Contractor"),
    ],
    "Vessel": [
        ("H0700", "Processing Contractor"),
        ("H0800", "Vessel Name"),
        ("H0900", "Vessel ID"),
    ],
    "Coordinate System": [
        ("H1000", "Datum/Spheroid Name"),
        ("H1100", "Datum/Spheroid Semi-Major Axis"),
        ("H1200", "Datum/Spheroid Flattening"),
        ("H1300", "Projection Type"),
        ("H1400", "Projection Zone"),
        ("H1500", "Central Meridian"),
        ("H1600", "Latitude of Origin"),
        ("H1700", "Scale Factor"),
        ("H1800", "False Easting"),
        ("H1900", "False Northing"),
    ],
    "Equipment": [
        ("H2000", "Source Type"),
        ("H2100", "Source Description"),
        ("H2200", "Streamer Description"),
        ("H2300", "No. of Channels"),
        ("H2400", "Group Interval"),
        ("H2500", "Near Offset"),
        ("H2600", "Far Offset"),
    ],
}


class HeaderPanel(QWidget):
    """H Record metadata editor organized by category."""

    panel_title = "Header"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: dict[str, QLineEdit] = {}
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        outer.setSpacing(Space.SM)

        # Title
        title = QLabel("P190 H Record Editor")
        title.setStyleSheet(f"""
            color: {Dark.TEXT_BRIGHT};
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            background: transparent; border: none;
        """)
        outer.addWidget(title)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(Space.MD)

        for cat_name, codes in H_CATEGORIES.items():
            card = SectionCard(cat_name)
            for code, desc in codes:
                row = QHBoxLayout()
                row.setSpacing(Space.SM)

                code_lbl = QLabel(code)
                code_lbl.setFixedWidth(50)
                code_lbl.setStyleSheet(
                    f"color: #06B6D4; font-size: {Font.XS}px;"
                    f" font-family: monospace;"
                    f" background:transparent; border:none;")
                row.addWidget(code_lbl)

                desc_lbl = QLabel(desc)
                desc_lbl.setFixedWidth(200)
                desc_lbl.setStyleSheet(
                    f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                    f" background:transparent; border:none;")
                row.addWidget(desc_lbl)

                edit = QLineEdit()
                edit.setStyleSheet(f"""
                    QLineEdit {{
                        background: {Dark.DARK};
                        color: {Dark.TEXT};
                        border: 1px solid {Dark.BORDER};
                        border-radius: {Radius.SM}px;
                        padding: 4px 8px;
                        font-size: {Font.SM}px;
                    }}
                    QLineEdit:focus {{ border-color: #06B6D4; }}
                """)
                row.addWidget(edit, 1)
                self._fields[code] = edit

                card.content_layout.addLayout(row)

            form_layout.addWidget(card)

        form_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

    def get_h_record_config(self):
        """Return HRecordConfig from form fields."""
        from p190converter.models.survey_config import HRecordConfig
        records = {}
        for code, edit in self._fields.items():
            text = edit.text().strip()
            if text:
                records[code] = text
        config = HRecordConfig()
        config.records.update(records)
        return config

    def set_h_records(self, records: dict):
        for code, value in records.items():
            if code in self._fields:
                self._fields[code].setText(str(value))

    def apply_crs_to_records(self, crs_config):
        """Auto-fill CRS-related H records from CRS config."""
        if crs_config.datum_name:
            if "H1000" in self._fields:
                self._fields["H1000"].setText(crs_config.datum_name)
        if crs_config.is_utm:
            if "H1300" in self._fields:
                self._fields["H1300"].setText("UTM")
            if "H1400" in self._fields:
                self._fields["H1400"].setText(
                    f"{crs_config.utm_zone}{crs_config.hemisphere}")
