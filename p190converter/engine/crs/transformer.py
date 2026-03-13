"""CRS transformation wrapper using pyproj."""

from typing import Tuple

from pyproj import Transformer

from ...models.survey_config import CRSConfig


class CRSTransformer:
    """UTM <-> WGS-84 coordinate transformer."""

    def __init__(self, crs_config: CRSConfig):
        self.config = crs_config
        # UTM -> WGS-84 (lat/lon)
        self._to_latlon = Transformer.from_crs(
            f"EPSG:{crs_config.epsg_code}",
            "EPSG:4326",
            always_xy=True,
        )
        # WGS-84 -> UTM
        self._to_utm = Transformer.from_crs(
            "EPSG:4326",
            f"EPSG:{crs_config.epsg_code}",
            always_xy=True,
        )

    def utm_to_latlon(self, easting: float, northing: float) -> Tuple[float, float]:
        """Convert UTM to WGS-84 (latitude, longitude in decimal degrees).

        Args:
            easting: UTM Easting (meters)
            northing: UTM Northing (meters)

        Returns:
            (latitude, longitude) in decimal degrees
        """
        lon, lat = self._to_latlon.transform(easting, northing)
        return lat, lon

    def latlon_to_utm(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert WGS-84 to UTM.

        Returns:
            (easting, northing) in meters
        """
        easting, northing = self._to_utm.transform(lon, lat)
        return easting, northing
