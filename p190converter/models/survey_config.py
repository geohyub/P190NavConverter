"""Survey configuration model."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MarineGeometry:
    """Marine geometry parameters for Style A interpolation."""
    source_dx: float = 0.0          # Source offset cross-track (m, +starboard)
    source_dy: float = 0.0          # Source offset along-track (m, +bow)
    rx1_dx: float = -10.0           # First receiver cross-track offset (m)
    rx1_dy: float = 20.0            # First receiver along-track offset (m)
    n_channels: int = 48            # Number of receiver channels
    rx_interval: float = 3.125      # Receiver group interval (m)
    cable_depth: float = 0.0        # Cable depth (m), 0.0 for 2D
    interp_method: str = "linear"   # linear | catenary | spline | feathering
    feathering_alpha: float = 2.0   # Feathering model exponent (2.0=quadratic)

    @property
    def total_spread(self) -> float:
        """Total receiver spread length (m)."""
        return self.rx_interval * (self.n_channels - 1)


@dataclass
class CRSConfig:
    """Coordinate Reference System configuration."""
    utm_zone: int = 52              # UTM zone number (0 for non-UTM)
    hemisphere: str = "N"           # N or S
    epsg_code: int = 32652          # EPSG code
    display_name: str = ""          # Human-readable name (e.g. "Korea 2000 Unified CS")
    datum_name: str = "WGS-84"     # Datum name for H records

    @classmethod
    def from_zone(cls, zone: int, hemisphere: str = "N") -> "CRSConfig":
        base = 32600 if hemisphere.upper() == "N" else 32700
        return cls(
            utm_zone=zone,
            hemisphere=hemisphere.upper(),
            epsg_code=base + zone,
            display_name=f"WGS 84 / UTM zone {zone}{hemisphere.upper()}",
            datum_name="WGS-84",
        )

    @classmethod
    def from_preset(cls, epsg: int, name: str = "", datum: str = "WGS-84",
                    zone: int = 0, hemi: str = "N") -> "CRSConfig":
        return cls(
            utm_zone=zone,
            hemisphere=hemi,
            epsg_code=epsg,
            display_name=name,
            datum_name=datum,
        )

    @property
    def is_utm(self) -> bool:
        return self.utm_zone > 0


@dataclass
class HRecordConfig:
    """H Record (header) configuration for P190 output."""
    records: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.records:
            self.records = self.default_records()

    @staticmethod
    def default_records() -> Dict[str, str]:
        return {
            "H0100": "SURVEY AREA               ",
            "H0102": "VESSEL DETAILS            ",
            "H0103": "SOURCE DETAILS            ",
            "H0104": "STREAMER DETAILS          ",
            "H0200": "SURVEY DATE               ",
            "H0201": "TAPE DATE (D.M.Y.)        ",
            "H0202": "TAPE VERSION              UKOOA-P1/90",
            "H0300": "CLIENT                    ",
            "H0400": "GEOPHYSICAL CONTRACTOR    ",
            "H0500": "POSITIONING CONTRACTOR    ",
            "H0600": "POSITIONING PROCESSING    ",
            "H0700": "POSITIONING SYSTEM        ",
            "H0800": "SHOTPOINT POSITION        ",
            "H0900": "OFFSET SHIP SYSTEM TO SP  ",
            "H1000": "CLOCK TIME                GMT",
            "H1400": "GEODETIC DATUM AS SURVEYED",
            "H1500": "GEODETIC DATUM AS PLOTTED ",
            "H1700": "VERTICAL DATUM            ",
            "H1800": "PROJECTION                ",
            "H1900": "ZONE                      ",
            "H2000": "GRID UNITS                1Meter                   1.000000000000",
            "H2001": "HEIGHT UNITS              1Meter                   1.000000000000",
            "H2002": "ANGULAR UNITS             1DEGREES                 0 0 0.00",
            "H2200": "CENTRAL MERIDIAN          ",
            "H2600": "SEISMIC DATA UNLOADER     UKOOA P1/90 FORMAT",
        }

    def set(self, code: str, content: str):
        self.records[code] = content

    def get(self, code: str) -> str:
        return self.records.get(code, "")

    def apply_crs(self, crs: "CRSConfig"):
        """Update H records with CRS info."""
        datum = crs.datum_name
        if datum == "WGS-84":
            ellipsoid = "6378137.0 298.26"
        elif datum == "GRS 1980":
            ellipsoid = "6378137.0 298.26"
        else:
            ellipsoid = ""

        self.records["H1400"] = f"GEODETIC DATUM AS SURVEYED{datum}  {ellipsoid}".rstrip()
        self.records["H1500"] = f"GEODETIC DATUM AS PLOTTED {datum}  {ellipsoid}".rstrip()

        if crs.is_utm:
            self.records["H1800"] = f"PROJECTION                 001  UTM zone {crs.utm_zone}{crs.hemisphere}"
            self.records["H1900"] = f"ZONE                      {crs.utm_zone}{crs.hemisphere}"
            central_meridian = (crs.utm_zone * 6) - 183
            self.records["H2200"] = f"CENTRAL MERIDIAN          {central_meridian} 0 0.000E"
        else:
            proj_name = crs.display_name or f"EPSG:{crs.epsg_code}"
            self.records["H1800"] = f"PROJECTION                {proj_name}"
            self.records["H1900"] = f"ZONE                      EPSG:{crs.epsg_code}"
            self.records["H2200"] = f"CENTRAL MERIDIAN          "


@dataclass
class SurveyConfig:
    """Complete survey configuration for P190 conversion."""
    # Mode
    style: str = "B"                # "A" (NPD) or "B" (RadExPro export)

    # Files
    input_file: str = ""
    output_dir: str = ""
    line_name: str = ""

    # Style A specific
    npd_file: str = ""
    track_file: str = ""            # Track file path (Style A)
    front_gps_source: str = ""      # Selected NPD position source
    tail_gps_source: str = ""
    geometry: MarineGeometry = field(default_factory=MarineGeometry)
    radex_coord_decimals: int = 5

    # Source position mode for Style A:
    #   "front_gps" — Front GPS 실측 위치 직접 사용 (기본값, 독립 검증용)
    #                 COS_Sparker 선택 시 ~11m, Head_Buoy 선택 시 ~25m 차이 예상
    #   "track_sou" — Track 파일의 SOU_X/SOU_Y 사용 (RadExPro 계산값과 동일)
    source_position_mode: str = "front_gps"

    # Common
    crs: CRSConfig = field(default_factory=CRSConfig)
    h_records: HRecordConfig = field(default_factory=HRecordConfig)

    # Vessel info
    vessel_id: str = "1"
    source_id: str = "1"
    streamer_id: str = "1"
