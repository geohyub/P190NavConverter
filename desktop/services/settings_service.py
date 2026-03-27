"""Settings service — JSON persistence wrapper around utils/settings.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure p190converter is importable
_P190_ROOT = str(Path(__file__).resolve().parents[2])
if _P190_ROOT not in sys.path:
    sys.path.insert(0, _P190_ROOT)

from p190converter.utils.settings import (
    load_full_config,
    save_full_config,
    save_profile,
    load_profile,
    delete_profile,
    list_profiles,
)


class SettingsService:
    """Adapter for p190converter settings persistence."""

    def load_session(self) -> dict | None:
        """Load last session config."""
        return load_full_config()

    def save_session(self, input_vals: dict, crs_config, geometry, h_records):
        """Save current session config."""
        from p190converter.models.survey_config import SurveyConfig

        config = SurveyConfig(
            style=input_vals.get("style", "B"),
            input_file=input_vals.get("input_file", ""),
            line_name=input_vals.get("line_name", ""),
            output_dir=input_vals.get("output_dir", ""),
            npd_file=input_vals.get("npd_file", ""),
            track_file=input_vals.get("track_file", ""),
            front_gps_source=input_vals.get("front_gps", ""),
            tail_gps_source=input_vals.get("tail_gps", ""),
            radex_coord_decimals=int(
                input_vals.get("radex_coord_decimals", 5)),
            crs=crs_config,
            h_records=h_records,
            geometry=geometry,
        )
        save_full_config(config)

    # -- Profile management --

    @staticmethod
    def list_profiles() -> list[str]:
        return list_profiles()

    def save_profile(self, name: str, data: dict):
        save_profile(name, data)

    def load_profile(self, name: str) -> dict | None:
        return load_profile(name)

    def delete_profile(self, name: str) -> bool:
        return delete_profile(name)
