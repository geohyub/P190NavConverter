"""GeometryDiagram — QPainter top-view marine geometry visualization."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QSizePolicy

from geoview_pyside6.constants import Dark

# Diagram colors
C_VESSEL = QColor("#f1f5f9")
C_SOURCE = QColor("#f59e0b")
C_RECEIVER = QColor("#06b6d4")
C_CABLE = QColor("#475569")
C_WATER = QColor("#0c4a6e")
C_TEXT = QColor(Dark.MUTED)
C_BG = QColor(Dark.DARK)


class GeometryDiagram(QWidget):
    """Top-view marine geometry: vessel, source, receivers, cable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Default geometry values
        self._src_dx = 0.0
        self._src_dy = 0.0
        self._rx1_dx = 0.0
        self._rx1_dy = 0.0
        self._n_channels = 48
        self._rx_interval = 3.125
        self._cable_depth = 2.0

    def update_geometry(
        self,
        src_dx: float = 0.0,
        src_dy: float = 0.0,
        rx1_dx: float = 0.0,
        rx1_dy: float = 0.0,
        n_channels: int = 48,
        rx_interval: float = 3.125,
        cable_depth: float = 2.0,
    ):
        self._src_dx = src_dx
        self._src_dy = src_dy
        self._rx1_dx = rx1_dx
        self._rx1_dy = rx1_dy
        self._n_channels = n_channels
        self._rx_interval = rx_interval
        self._cable_depth = cable_depth
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        p.fillRect(0, 0, w, h, C_BG)

        # Compute scale
        spread = self._n_channels * self._rx_interval
        max_extent = max(
            abs(self._src_dy) + abs(self._rx1_dy) + spread,
            abs(self._src_dx) + abs(self._rx1_dx) + 50,
            200,
        )
        scale = min(w * 0.7, h * 0.7) / max_extent
        cx = w * 0.5
        cy = h * 0.35  # Vessel at upper area

        # --- Vessel (triangle) ---
        vessel_size = 16
        vessel_pts = [
            QPointF(cx, cy - vessel_size),
            QPointF(cx - vessel_size * 0.7, cy + vessel_size * 0.5),
            QPointF(cx + vessel_size * 0.7, cy + vessel_size * 0.5),
        ]
        p.setPen(QPen(C_VESSEL, 2))
        p.setBrush(QBrush(C_VESSEL.darker(150)))
        p.drawPolygon(vessel_pts)

        # --- Source ---
        src_x = cx + self._src_dx * scale
        src_y = cy + self._src_dy * scale
        p.setPen(QPen(C_SOURCE, 1.5))
        p.setBrush(QBrush(C_SOURCE))
        p.drawEllipse(QPointF(src_x, src_y), 6, 6)

        # Line from vessel to source
        p.setPen(QPen(C_CABLE, 1, Qt.DashLine))
        p.drawLine(QPointF(cx, cy), QPointF(src_x, src_y))

        # --- Cable & Receivers ---
        rx1_x = cx + self._rx1_dx * scale
        rx1_y = cy + self._rx1_dy * scale

        # Cable line from vessel to RX1
        p.setPen(QPen(C_CABLE, 1.5))
        p.drawLine(QPointF(cx, cy), QPointF(rx1_x, rx1_y))

        # Direction from vessel to RX1 (unit vector for cable extent)
        dx_cable = self._rx1_dx
        dy_cable = self._rx1_dy
        cable_len = math.sqrt(dx_cable**2 + dy_cable**2)
        if cable_len < 0.01:
            dx_cable, dy_cable = 0.0, 1.0
            cable_len = 1.0
        ux = dx_cable / cable_len
        uy = dy_cable / cable_len

        # Draw cable extent from RX1
        last_rx_dy = self._rx1_dy + uy * spread
        last_rx_dx = self._rx1_dx + ux * spread
        end_x = cx + last_rx_dx * scale
        end_y = cy + last_rx_dy * scale

        p.setPen(QPen(C_CABLE, 1.5))
        p.drawLine(QPointF(rx1_x, rx1_y), QPointF(end_x, end_y))

        # Draw first receiver
        p.setPen(QPen(C_RECEIVER, 1))
        p.setBrush(QBrush(C_RECEIVER))
        p.drawEllipse(QPointF(rx1_x, rx1_y), 3, 3)

        # Draw last receiver
        p.drawEllipse(QPointF(end_x, end_y), 3, 3)

        # Draw some intermediate receivers (max 8 visible)
        n_vis = min(self._n_channels, 8)
        for i in range(1, n_vis):
            frac = i / n_vis
            ix = rx1_x + (end_x - rx1_x) * frac
            iy = rx1_y + (end_y - rx1_y) * frac
            p.drawEllipse(QPointF(ix, iy), 2, 2)

        # --- Labels (offset to avoid overlap) ---
        p.setPen(C_TEXT)
        label_font = QFont("Pretendard", 9) if QFont("Pretendard").exactMatch() else QFont("Segoe UI", 9)
        p.setFont(label_font)

        # Vessel label - always top-right of vessel
        p.drawText(int(cx) + 18, int(cy) - 6, "Vessel")

        # Source label - offset left if close to RX1
        src_label = f"Source ({self._src_dx:.1f}, {self._src_dy:.1f})"
        src_dist_to_rx1 = math.sqrt(
            (src_x - rx1_x) ** 2 + (src_y - rx1_y) ** 2)
        if src_dist_to_rx1 < 40:
            # Labels would overlap: source goes left, RX1 goes right
            p.setPen(C_SOURCE)
            p.drawText(int(src_x) - 10, int(src_y) - 12, src_label)
            p.setPen(C_RECEIVER)
            p.drawText(
                int(rx1_x) + 10, int(rx1_y) + 18,
                f"RX1 ({self._rx1_dx:.1f}, {self._rx1_dy:.1f})")
        else:
            p.setPen(C_SOURCE)
            p.drawText(int(src_x) + 10, int(src_y) - 6, src_label)
            p.setPen(C_RECEIVER)
            p.drawText(
                int(rx1_x) + 10, int(rx1_y) - 6,
                f"RX1 ({self._rx1_dx:.1f}, {self._rx1_dy:.1f})")

        # Spread label at cable end
        p.setPen(C_TEXT)
        spread_text = f"{self._n_channels}ch x {self._rx_interval}m = {spread:.1f}m"
        p.drawText(int(end_x) + 10, int(end_y) + 6, spread_text)

        # --- Legend ---
        legend_y = h - 14
        p.setPen(C_TEXT)
        p.setFont(QFont("Pretendard", 8) if QFont("Pretendard").exactMatch() else QFont("Segoe UI", 8))
        p.drawText(10, legend_y, "dx = cross-track (+ starboard)")
        p.drawText(w // 2, legend_y, "dy = along-track (+ forward)")

        p.end()
