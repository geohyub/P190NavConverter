"""LogPanel — Real-time conversion log with color-coded levels."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFileDialog,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.step_indicator import StepIndicator

LOG_COLORS = {
    "info":    "#94A3B8",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error":   "#EF4444",
}


class LogPanel(QWidget):
    """Real-time execution log with HTML-formatted entries."""

    panel_title = "Log"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[str] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.SM)

        # Step indicator (hidden until conversion)
        self._step_indicator = StepIndicator()
        self._step_indicator.setVisible(False)
        layout.addWidget(self._step_indicator)

        # Log display
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.BASE}px;
                padding: 8px;
                font-family: "JetBrains Mono", "Cascadia Code", "Consolas";
                font-size: {Font.SM}px;
            }}
        """)
        layout.addWidget(self._text, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        btn_row.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)
        btn_row.addWidget(export_btn)

        for btn in (clear_btn, export_btn):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.NAVY};
                    color: {Dark.TEXT};
                    border: 1px solid {Dark.BORDER};
                    border-radius: {Radius.SM}px;
                    padding: 0 14px;
                    font-size: {Font.XS}px;
                }}
                QPushButton:hover {{ border-color: #06B6D4; }}
            """)

        layout.addLayout(btn_row)

    def append(self, level: str, message: str):
        color = LOG_COLORS.get(level, LOG_COLORS["info"])
        ts = datetime.now().strftime("%H:%M:%S")
        html = (
            f'<span style="color:{Dark.MUTED}">{ts}</span> '
            f'<span style="color:{color}">[{level.upper():7s}]</span> '
            f'<span style="color:{Dark.TEXT}">{message}</span>')
        self._entries.append(f"{ts} [{level.upper()}] {message}")
        self._text.append(html)
        # Auto-scroll
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        self._text.clear()
        self._entries.clear()
        self._step_indicator.reset()
        self._step_indicator.setVisible(False)

    def show_step_indicator(self):
        self._step_indicator.reset()
        self._step_indicator.setVisible(True)

    def hide_step_indicator(self):
        self._step_indicator.setVisible(False)

    def set_step(self, index: int, state: str):
        self._step_indicator.setVisible(True)
        self._step_indicator.set_step(index, state)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "conversion_log.txt",
            "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._entries))
