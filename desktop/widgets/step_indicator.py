"""StepIndicator — Pipeline step progress with animation."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy

from geoview_pyside6.constants import Dark

STEP_LABELS = ["\ud30c\uc2f1", "\ubcc0\ud658", "\uc791\uc131", "\uac80\uc99d", "QC"]

STEP_COLORS = {
    "pending": QColor("#4A5568"),
    "active":  QColor("#06B6D4"),
    "done":    QColor("#10B981"),
    "error":   QColor("#EF4444"),
}


class StepIndicator(QWidget):
    """5-step pipeline indicator with pulse animation on active step."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._states = ["pending"] * 5
        self._pulse_phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def reset(self):
        self._states = ["pending"] * 5
        self._pulse_phase = 0.0
        self._timer.stop()
        self.update()

    def set_step(self, index: int, state: str):
        if 0 <= index < 5:
            self._states[index] = state
            if state == "active" and not self._timer.isActive():
                self._timer.start()
            elif "active" not in self._states:
                self._timer.stop()
            self.update()

    def _tick(self):
        self._pulse_phase = (self._pulse_phase + 0.08) % 6.28
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        p.fillRect(0, 0, w, h, QColor(Dark.NAVY))

        margin = 40
        usable = w - 2 * margin
        spacing = usable / (len(STEP_LABELS) - 1) if len(STEP_LABELS) > 1 else 0
        cy = h / 2

        # Draw connecting lines
        for i in range(len(STEP_LABELS) - 1):
            x1 = margin + i * spacing
            x2 = margin + (i + 1) * spacing
            # Line color: done if both connected steps are done
            if self._states[i] in ("done",) and self._states[i + 1] != "pending":
                line_color = STEP_COLORS["done"]
            elif self._states[i] in ("active", "done"):
                line_color = STEP_COLORS["active"]
            else:
                line_color = STEP_COLORS["pending"]
            p.setPen(QPen(line_color, 2))
            p.drawLine(int(x1 + 10), int(cy), int(x2 - 10), int(cy))

        # Draw step circles + labels
        font = QFont("Pretendard", 8) if QFont("Pretendard").exactMatch() else QFont("Segoe UI", 8)
        p.setFont(font)

        pulse = (math.sin(self._pulse_phase) + 1) / 2  # 0-1

        for i, label in enumerate(STEP_LABELS):
            x = margin + i * spacing
            state = self._states[i]
            color = STEP_COLORS.get(state, STEP_COLORS["pending"])

            radius = 8
            if state == "active":
                radius = 8 + int(pulse * 3)

            # Circle
            p.setPen(QPen(color, 2))
            if state in ("done", "active"):
                p.setBrush(QBrush(color))
            else:
                p.setBrush(QBrush(QColor(Dark.DARK)))
            p.drawEllipse(QRectF(x - radius, cy - radius,
                                  radius * 2, radius * 2))

            # Checkmark for done
            if state == "done":
                p.setPen(QPen(QColor(Dark.DARK), 2))
                p.drawText(QRectF(x - 6, cy - 6, 12, 12),
                           Qt.AlignCenter, "V")

            # Label below
            p.setPen(QColor(Dark.TEXT if state != "pending" else Dark.MUTED))
            p.drawText(QRectF(x - 30, cy + 12, 60, 16),
                       Qt.AlignCenter, label)

        p.end()
