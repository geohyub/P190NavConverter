"""SectionCard — Elevated card container with optional title."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from geoview_pyside6.constants import Dark, Font, Space, Radius


class SectionCard(QFrame):
    """Card container with optional title and border."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title_label: QLabel | None = None

        self.setStyleSheet(f"""
            SectionCard {{
                background: {Dark.NAVY};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.BASE}px;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            Space.BASE, Space.MD, Space.BASE, Space.BASE)
        self._layout.setSpacing(Space.SM)

        if title:
            self._title_label = QLabel(title)
            self._title_label.setStyleSheet(f"""
                color: {Dark.TEXT_BRIGHT};
                font-size: {Font.BASE}px;
                font-weight: {Font.SEMIBOLD};
                background: transparent;
                border: none;
            """)
            self._layout.addWidget(self._title_label)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def set_title(self, title: str):
        if self._title_label is None:
            self._title_label = QLabel()
            self._title_label.setStyleSheet(f"""
                color: {Dark.TEXT_BRIGHT};
                font-size: {Font.BASE}px;
                font-weight: {Font.SEMIBOLD};
                background: transparent;
                border: none;
            """)
            self._layout.insertWidget(0, self._title_label)
        self._title_label.setText(title)
