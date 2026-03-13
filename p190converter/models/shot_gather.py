"""Shot gather data model for P190 conversion."""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class ReceiverPosition:
    """Single receiver channel position."""
    channel: int
    x: float          # Easting (UTM meters)
    y: float          # Northing (UTM meters)
    depth: float = 0.0  # Cable depth (meters)


@dataclass
class ShotGather:
    """One shot record with source and receiver positions.

    Maps directly to one S Record + multiple R Records in P190.
    """
    ffid: int                               # Field File ID (= Point Number)
    source_x: float                         # Source Easting (UTM)
    source_y: float                         # Source Northing (UTM)
    receivers: List[ReceiverPosition] = field(default_factory=list)

    # Time
    day: int = 0                            # Julian day
    hour: int = 0
    minute: int = 0
    second: int = 0

    # Optional
    source_depth: float = 0.0               # Source depth (meters)
    heading: float = 0.0                    # Ship heading (degrees, CW from N)
    line_name: str = ""

    # Lat/Lon (computed by CRS transformer)
    source_lat: Optional[float] = None      # Decimal degrees
    source_lon: Optional[float] = None      # Decimal degrees

    @property
    def n_channels(self) -> int:
        return len(self.receivers)

    @property
    def time_str(self) -> str:
        """HHMMSS format."""
        return f"{self.hour:02d}{self.minute:02d}{self.second:02d}"

    @property
    def spread_length(self) -> float:
        """Distance from first to last receiver (meters)."""
        if len(self.receivers) < 2:
            return 0.0
        r0, rn = self.receivers[0], self.receivers[-1]
        return float(np.sqrt((rn.x - r0.x)**2 + (rn.y - r0.y)**2))


@dataclass
class ShotGatherCollection:
    """Collection of shot gathers for a line."""
    shots: List[ShotGather] = field(default_factory=list)
    line_name: str = ""
    n_channels: int = 0

    @property
    def n_shots(self) -> int:
        return len(self.shots)

    @property
    def ffid_range(self) -> tuple:
        if not self.shots:
            return (0, 0)
        return (self.shots[0].ffid, self.shots[-1].ffid)

    @property
    def easting_range(self) -> tuple:
        if not self.shots:
            return (0.0, 0.0)
        xs = [s.source_x for s in self.shots]
        return (min(xs), max(xs))

    @property
    def northing_range(self) -> tuple:
        if not self.shots:
            return (0.0, 0.0)
        ys = [s.source_y for s in self.shots]
        return (min(ys), max(ys))
