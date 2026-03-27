"""FormField — Label + LineEdit + optional Browse button."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius


class FormField(QWidget):
    """Labeled text input with optional browse button."""

    value_changed = Signal(str)

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        browse: bool = False,
        browse_text: str = "...",
        label_width: int = 100,
        read_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._browse_callback = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Space.SM)

        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(label_width)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.SM}px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(lbl)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setReadOnly(read_only)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 6px 10px;
                font-size: {Font.SM}px;
            }}
            QLineEdit:focus {{
                border-color: {Dark.CYAN};
            }}
            QLineEdit:read-only {{
                color: {Dark.MUTED};
            }}
        """)
        self._input.editingFinished.connect(
            lambda: self.value_changed.emit(self._input.text()))
        layout.addWidget(self._input, 1)

        # Browse button
        if browse:
            btn = QPushButton(browse_text)
            btn.setFixedSize(36, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                    font-size: {Font.SM}px;
                }}
                QPushButton:hover {{
                    background: {Dark.SLATE};
                    border-color: {Dark.CYAN};
                }}
            """)
            btn.clicked.connect(self._on_browse)
            layout.addWidget(btn)

    @property
    def value(self) -> str:
        return self._input.text()

    @value.setter
    def value(self, text: str):
        self._input.setText(text)

    def set_browse_callback(self, callback):
        self._browse_callback = callback

    def _on_browse(self):
        if self._browse_callback:
            self._browse_callback()
