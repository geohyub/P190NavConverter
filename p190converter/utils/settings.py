"""JSON settings persistence.

Saves and restores full application state including:
- Conversion style (A/B)
- File paths (input, NPD, track, output directory)
- Line name and GPS source selections
- CRS and geometry configuration
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.survey_config import SurveyConfig, CRSConfig, MarineGeometry


SETTINGS_DIR = Path.home() / ".p190converter"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
PROFILES_DIR = SETTINGS_DIR / "profiles"

# Current settings schema version
_SCHEMA_VERSION = 2


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_settings(data: Dict[str, Any]):
    """Save settings to JSON file (merges with existing)."""
    existing = load_settings()
    existing.update(data)
    existing["version"] = _SCHEMA_VERSION
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def save_full_config(config: SurveyConfig):
    """Save complete SurveyConfig to settings.

    Stores all fields needed to restore the full application state
    on next launch. File paths are only saved if they still exist.
    """
    data = {
        "version": _SCHEMA_VERSION,
        "last_style": config.style,
        "last_line_name": config.line_name,
        "last_files": {},
        "last_crs": {
            "utm_zone": config.crs.utm_zone,
            "hemisphere": config.crs.hemisphere,
            "epsg_code": config.crs.epsg_code,
            "display_name": config.crs.display_name,
            "datum_name": config.crs.datum_name,
        },
        "last_geometry": {
            "source_dx": config.geometry.source_dx,
            "source_dy": config.geometry.source_dy,
            "rx1_dx": config.geometry.rx1_dx,
            "rx1_dy": config.geometry.rx1_dy,
            "n_channels": config.geometry.n_channels,
            "rx_interval": config.geometry.rx_interval,
            "cable_depth": config.geometry.cable_depth,
            "interp_method": config.geometry.interp_method,
            "feathering_alpha": config.geometry.feathering_alpha,
        },
        "last_gps_sources": {
            "front": config.front_gps_source,
            "tail": config.tail_gps_source,
        },
        "last_export_options": {
            "radex_coord_decimals": config.radex_coord_decimals,
        },
        "last_vessel": {
            "vessel_id": config.vessel_id,
            "source_id": config.source_id,
            "streamer_id": config.streamer_id,
        },
    }

    # Only save file paths that exist
    for key, path in [
        ("input_file", config.input_file),
        ("npd_file", config.npd_file),
        ("track_file", config.track_file),
        ("output_dir", config.output_dir),
    ]:
        if path and Path(path).exists():
            data["last_files"][key] = path

    save_settings(data)


def load_full_config() -> Optional[Dict[str, Any]]:
    """Load saved config state for restoration.

    Returns dict with keys: style, line_name, files, crs, geometry,
    gps_sources, vessel. Only includes file paths that still exist.
    Returns None if no saved config or version mismatch.
    """
    settings = load_settings()
    if not settings or settings.get("version", 0) < _SCHEMA_VERSION:
        return None

    result = {
        "style": settings.get("last_style", "B"),
        "line_name": settings.get("last_line_name", ""),
        "files": {},
        "crs": settings.get("last_crs"),
        "geometry": settings.get("last_geometry"),
        "gps_sources": settings.get("last_gps_sources"),
        "export_options": settings.get("last_export_options", {}),
        "vessel": settings.get("last_vessel"),
    }

    # Validate file paths exist
    saved_files = settings.get("last_files", {})
    for key, path in saved_files.items():
        if path:
            if key == "output_dir":
                if Path(path).is_dir():
                    result["files"][key] = path
            elif Path(path).is_file():
                result["files"][key] = path

    return result


def load_h_template(name: str) -> Dict[str, str]:
    """Load H Record template by name."""
    templates_dir = SETTINGS_DIR / "templates"
    path = templates_dir / f"{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_h_template(name: str, records: Dict[str, str]):
    """Save H Record template."""
    templates_dir = SETTINGS_DIR / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# ── Profile Management ──

def list_profiles() -> List[str]:
    """List saved profile names (without .json extension)."""
    if not PROFILES_DIR.exists():
        return []
    return sorted(
        p.stem for p in PROFILES_DIR.glob("*.json")
    )


def save_profile(name: str, data: Dict[str, Any]):
    """Save a named settings profile.

    Args:
        name: Profile name (used as filename)
        data: Full config dict (style, files, crs, geometry, h_records, etc.)
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    data["version"] = _SCHEMA_VERSION
    path = PROFILES_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_profile(name: str) -> Optional[Dict[str, Any]]:
    """Load a named settings profile.

    Returns dict with profile data, or None if not found.
    File paths are validated for existence.
    """
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate file paths
    files = data.get("files", {})
    validated = {}
    for key, fpath in files.items():
        if fpath:
            if key == "output_dir":
                if Path(fpath).is_dir():
                    validated[key] = fpath
            elif Path(fpath).is_file():
                validated[key] = fpath
    data["files"] = validated

    return data


def delete_profile(name: str) -> bool:
    """Delete a named profile. Returns True if deleted."""
    path = PROFILES_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False
