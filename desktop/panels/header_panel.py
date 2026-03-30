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
    "\uc870\uc0ac \uc815\ubcf4": [
        ("H0100", "\uc870\uc0ac \uc9c0\uc5ed\uba85"),
        ("H0200", "\uc870\uc0ac \ub0a0\uc9dc"),
        ("H0300", "\ud074\ub77c\uc774\uc5b8\ud2b8\uba85"),
        ("H0400", "\ubb3c\ub9ac\ud0d0\uc0ac \uc5c5\uccb4"),
        ("H0500", "\uce21\uc704 \uc5c5\uccb4"),
        ("H0600", "\uce21\uc704 \ucc98\ub9ac \uc5c5\uccb4"),
    ],
    "\uc120\ubc15 \uc815\ubcf4": [
        ("H0700", "\ucc98\ub9ac \uc5c5\uccb4"),
        ("H0800", "\uc120\ubc15\uba85"),
        ("H0900", "\uc120\ubc15 ID"),
    ],
    "\uc88c\ud45c\uacc4": [
        ("H1000", "Datum/Spheroid \uc774\ub984"),
        ("H1100", "Datum/Spheroid \uc7a5\ubc18\uacbd"),
        ("H1200", "Datum/Spheroid \ud3b8\ud3c9\ub960"),
        ("H1300", "\ud22c\uc601\ubc95 \uc885\ub958"),
        ("H1400", "\ud22c\uc601 Zone"),
        ("H1500", "\uc911\uc559 \uc790\uc624\uc120"),
        ("H1600", "\uc6d0\uc810 \uc704\ub3c4"),
        ("H1700", "\ucd95\ucc99 \uacc4\uc218"),
        ("H1800", "False Easting"),
        ("H1900", "False Northing"),
    ],
    "\uc7a5\ube44 \uc815\ubcf4": [
        ("H2000", "\uc74c\uc6d0 \uc885\ub958"),
        ("H2100", "\uc74c\uc6d0 \uc124\uba85"),
        ("H2200", "\uc2a4\ud2b8\ub9ac\uba38 \uc124\uba85"),
        ("H2300", "\ucc44\ub110 \uc218"),
        ("H2400", "\uadf8\ub8f9 \uac04\uaca9"),
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
        title = QLabel("P190 H Record \ud3b8\uc9d1\uae30")
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
