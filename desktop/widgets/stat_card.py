"""StatCard — Metric display card with accent bar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from geoview_pyside6.constants import Dark, Font, Space, Radius

# Rotating accent colors
ACCENTS = ["#06B6D4", "#8B5CF6", "#F59E0B", "#10B981"]


class StatCard(QFrame):
    """Compact stat card with value + label + accent top bar."""

    def __init__(
        self,
        label: str,
        value: str = "--",
        accent_index: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self._desc_label = None

        accent = ACCENTS[accent_index % len(ACCENTS)]

        self.setFixedHeight(72)
        self.setMinimumWidth(120)
        self.setStyleSheet(f"""
            StatCard {{
                background: {Dark.NAVY};
                border: 1px solid {Dark.BORDER};
                border-top: 3px solid {accent};
                border-radius: {Radius.SM}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Space.MD, Space.SM, Space.MD, Space.SM)
        layout.setSpacing(2)

        self._value_label = QLabel(value)
        self._value_label.setAlignment(Qt.AlignLeft)
        self._value_label.setStyleSheet(f"""
            color: {Dark.TEXT_BRIGHT};
            font-size: {Font.LG}px;
            font-weight: {Font.BOLD};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._value_label)

        self._desc_label = QLabel(label)
        self._desc_label.setAlignment(Qt.AlignLeft)
        self._desc_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._desc_label)

    def set_value(self, text: str):
        self._value_label.setText(text)
        is_empty = text in ("--", "", "0")
        self._value_label.setStyleSheet(f"""
            color: {Dark.MUTED if is_empty else Dark.TEXT_BRIGHT};
            font-size: {Font.LG}px;
            font-weight: {Font.BOLD};
            background: transparent;
            border: none;
        """)

    def set_label(self, text: str):
        if self._desc_label is not None:
            self._desc_label.setText(text)
