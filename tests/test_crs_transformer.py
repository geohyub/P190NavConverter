# -*- coding: utf-8 -*-
"""Unit tests for CRS transformer."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from p190converter.engine.crs.transformer import CRSTransformer
from p190converter.models.survey_config import CRSConfig


def _make_transformer(epsg=32652):
    """Create transformer for UTM zone 52N (Korea region)."""
    config = CRSConfig(epsg_code=epsg, utm_zone=52, hemisphere="N")
    return CRSTransformer(config)


def test_utm_to_latlon_roundtrip():
    """UTM -> LatLon -> UTM should be identity (within tolerance)."""
    t = _make_transformer()
    # Seoul area approximate UTM 52N coordinates
    orig_e, orig_n = 500000.0, 3900000.0
    lat, lon = t.utm_to_latlon(orig_e, orig_n)
    e_back, n_back = t.latlon_to_utm(lat, lon)
    assert abs(e_back - orig_e) < 0.01, f"Easting roundtrip error: {abs(e_back - orig_e)}"
    assert abs(n_back - orig_n) < 0.01, f"Northing roundtrip error: {abs(n_back - orig_n)}"


def test_utm_to_latlon_reasonable_range():
    """Result should be in valid lat/lon range."""
    t = _make_transformer()
    lat, lon = t.utm_to_latlon(500000.0, 3900000.0)
    assert -90 <= lat <= 90, f"Latitude out of range: {lat}"
    assert -180 <= lon <= 180, f"Longitude out of range: {lon}"


def test_utm_to_latlon_korea_region():
    """Coordinates in Korea should produce lat ~33-38, lon ~125-132."""
    t = _make_transformer()
    lat, lon = t.utm_to_latlon(500000.0, 3900000.0)
    assert 33 < lat < 38, f"Latitude {lat} not in Korea region"
    assert 125 < lon < 132, f"Longitude {lon} not in Korea region"


def test_latlon_to_utm_returns_positive():
    """UTM coordinates should be positive."""
    t = _make_transformer()
    e, n = t.latlon_to_utm(35.0, 129.0)
    assert e > 0, "Easting should be positive"
    assert n > 0, "Northing should be positive"


def test_different_epsg():
    """Test with UTM zone 31N (North Sea)."""
    config = CRSConfig(epsg_code=32631, utm_zone=31, hemisphere="N")
    t = CRSTransformer(config)
    lat, lon = t.utm_to_latlon(500000.0, 5800000.0)
    assert 50 < lat < 55, f"Latitude {lat} not in North Sea region"
    assert 0 < lon < 6, f"Longitude {lon} not in North Sea region"


def test_crs_object_reuse():
    """Transformer should be reusable across multiple calls."""
    t = _make_transformer()
    results = []
    for e_offset in range(5):
        lat, lon = t.utm_to_latlon(500000.0 + e_offset * 1000, 3900000.0)
        results.append((lat, lon))
    # Each call should produce different but close results
    lons = [r[1] for r in results]
    assert max(lons) - min(lons) < 0.1  # Very close
    assert len(set(f"{lon:.6f}" for lon in lons)) > 1  # But not identical


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
