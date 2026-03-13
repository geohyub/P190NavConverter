"""Marine Geometry model — offset definitions and cable layout."""

from dataclasses import dataclass
from typing import Tuple
import math


@dataclass
class OffsetDefinition:
    """Offset in vessel-relative rectangular coordinates (P190 Code 2).

    Cross-track (dx): + starboard
    Along-track (dy): + bow
    """
    dx: float = 0.0
    dy: float = 0.0

    def rotate(self, heading_rad: float) -> Tuple[float, float]:
        """Rotate offset by ship heading to get absolute coordinates.

        Args:
            heading_rad: Ship heading in radians (CW from North)

        Returns:
            (delta_easting, delta_northing) in map coordinates
        """
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)
        # Rotation matrix: heading CW from North
        # delta_E = dx * cos(h) + dy * sin(h)
        # delta_N = -dx * sin(h) + dy * cos(h)
        delta_e = self.dx * cos_h + self.dy * sin_h
        delta_n = -self.dx * sin_h + self.dy * cos_h
        return delta_e, delta_n
