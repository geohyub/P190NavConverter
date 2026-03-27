"""QualityGauge — Semi-circular arc progress gauge (0-100%)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy

from geoview_pyside6.constants import Dark


class QualityGauge(QWidget):
    """Semi-circular quality gauge with color-coded arcs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 120)
        self._value = 0.0  # 0-100
        self._label = "N/A"

    def set_value(self, value: float, label: str = ""):
        self._value = max(0.0, min(100.0, value))
        self._label = label or f"{self._value:.0f}%"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor(Dark.DARK))

        # Arc rect (semi-circle, bottom half clipped)
        arc_margin = 20
        arc_size = min(w - 2 * arc_margin, (h - arc_margin) * 2)
        arc_rect = QRectF(
            (w - arc_size) / 2,
            h - arc_size / 2 - 10,
            arc_size,
            arc_size,
        )

        pen_width = 10

        # Background arc (gray)
        p.setPen(QPen(QColor("#1F2937"), pen_width, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, 0 * 16, 180 * 16)

        # Value arc (colored)
        if self._value > 0:
            # Color: red(0-50) → amber(50-80) → green(80-100)
            if self._value < 50:
                color = QColor("#EF4444")
            elif self._value < 80:
                color = QColor("#F59E0B")
            else:
                color = QColor("#10B981")

            span = int(self._value / 100.0 * 180 * 16)
            p.setPen(QPen(color, pen_width, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc_rect, 180 * 16, -span)

        # Center text
        p.setPen(QColor(Dark.TEXT_BRIGHT))
        font = QFont("Pretendard", 22, QFont.Bold) if QFont("Pretendard").exactMatch() else QFont("Segoe UI", 22, QFont.Bold)
        p.setFont(font)
        text_rect = QRectF(0, h * 0.2, w, h * 0.5)
        p.drawText(text_rect, Qt.AlignCenter, self._label)

        p.end()
