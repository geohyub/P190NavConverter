"""Write RadExPro-friendly geometry sidecar files."""

from __future__ import annotations

import csv
from pathlib import Path

from .s_record import point_number_value
from ...models.shot_gather import ShotGatherCollection


class RadExTSVWriter:
    """Write import-friendly geometry and FFID crosswalk tables."""

    def __init__(self, coord_decimals: int = 5):
        self.coord_decimals = coord_decimals

    def _fmt(self, value: float) -> str:
        """Format coordinates with fixed decimal places for stable columns."""
        return f"{value:.{self.coord_decimals}f}"

    def _aligned_widths(
        self,
        collection: ShotGatherCollection,
    ) -> dict[str, int]:
        """Compute column widths from the formatted data for clean text output."""
        widths = {
            "FFID": len("FFID"),
            "FFID_P190": len("FFID_P190"),
            "SOU_X": len("SOU_X"),
            "SOU_Y": len("SOU_Y"),
            "CHAN": len("CHAN"),
            "REC_X": len("REC_X"),
            "REC_Y": len("REC_Y"),
            "DAY": len("DAY"),
            "HH": len("HH"),
            "MM": len("MM"),
            "SS": len("SS"),
        }

        for shot in collection.shots:
            ffid_p190 = point_number_value(shot.ffid)
            widths["FFID"] = max(widths["FFID"], len(str(shot.ffid)))
            widths["FFID_P190"] = max(widths["FFID_P190"], len(str(ffid_p190)))
            widths["SOU_X"] = max(widths["SOU_X"], len(self._fmt(shot.source_x)))
            widths["SOU_Y"] = max(widths["SOU_Y"], len(self._fmt(shot.source_y)))
            widths["DAY"] = max(widths["DAY"], len(str(shot.day)))
            widths["HH"] = max(widths["HH"], len(str(shot.hour)))
            widths["MM"] = max(widths["MM"], len(str(shot.minute)))
            widths["SS"] = max(widths["SS"], len(str(shot.second)))

            for rx in shot.receivers:
                widths["CHAN"] = max(widths["CHAN"], len(str(rx.channel)))
                widths["REC_X"] = max(widths["REC_X"], len(self._fmt(rx.x)))
                widths["REC_Y"] = max(widths["REC_Y"], len(self._fmt(rx.y)))

        return widths

    def write_geometry(self, collection: ShotGatherCollection, output_path: str) -> str:
        """Write one-row-per-trace geometry TSV for RadExPro ASCII import."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "FFID",
                "FFID_P190",
                "SOU_X",
                "SOU_Y",
                "CHAN",
                "REC_X",
                "REC_Y",
                "DAY",
                "HOUR",
                "MINUTE",
                "SECOND",
            ])

            for shot in collection.shots:
                ffid_p190 = point_number_value(shot.ffid)
                for rx in shot.receivers:
                    writer.writerow([
                        shot.ffid,
                        ffid_p190,
                        self._fmt(shot.source_x),
                        self._fmt(shot.source_y),
                        rx.channel,
                        self._fmt(rx.x),
                        self._fmt(rx.y),
                        shot.day,
                        shot.hour,
                        shot.minute,
                        shot.second,
                    ])

        return str(path)

    def write_geometry_pretty(
        self,
        collection: ShotGatherCollection,
        output_path: str,
    ) -> str:
        """Write a fixed-width geometry text file for visual inspection."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        widths = self._aligned_widths(collection)

        header = (
            f"{'FFID':>{widths['FFID']}} {'FFID_P190':>{widths['FFID_P190']}} "
            f"{'SOU_X':>{widths['SOU_X']}} {'SOU_Y':>{widths['SOU_Y']}} "
            f"{'CHAN':>{widths['CHAN']}} {'REC_X':>{widths['REC_X']}} "
            f"{'REC_Y':>{widths['REC_Y']}} {'DAY':>{widths['DAY']}} "
            f"{'HH':>{widths['HH']}} {'MM':>{widths['MM']}} {'SS':>{widths['SS']}}"
        )

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(header + "\n")
            for shot in collection.shots:
                ffid_p190 = point_number_value(shot.ffid)
                for rx in shot.receivers:
                    line = (
                        f"{shot.ffid:>{widths['FFID']}d} "
                        f"{ffid_p190:>{widths['FFID_P190']}d} "
                        f"{self._fmt(shot.source_x):>{widths['SOU_X']}} "
                        f"{self._fmt(shot.source_y):>{widths['SOU_Y']}} "
                        f"{rx.channel:>{widths['CHAN']}d} "
                        f"{self._fmt(rx.x):>{widths['REC_X']}} "
                        f"{self._fmt(rx.y):>{widths['REC_Y']}} "
                        f"{shot.day:>{widths['DAY']}d} "
                        f"{shot.hour:>{widths['HH']}d} "
                        f"{shot.minute:>{widths['MM']}d} "
                        f"{shot.second:>{widths['SS']}d}"
                    )
                    f.write(line + "\n")

        return str(path)

    def write_ffid_map(self, collection: ShotGatherCollection, output_path: str) -> str:
        """Write one-row-per-shot FFID crosswalk for troubleshooting/import."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        counts: dict[int, int] = {}
        for shot in collection.shots:
            value = point_number_value(shot.ffid)
            counts[value] = counts.get(value, 0) + 1

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "FFID_ORIG",
                "FFID_P190",
                "TRUNCATED",
                "COLLISION_COUNT",
                "DAY",
                "HOUR",
                "MINUTE",
                "SECOND",
            ])

            for shot in collection.shots:
                ffid_p190 = point_number_value(shot.ffid)
                writer.writerow([
                    shot.ffid,
                    ffid_p190,
                    "Y" if shot.ffid != ffid_p190 else "N",
                    counts[ffid_p190],
                    shot.day,
                    shot.hour,
                    shot.minute,
                    shot.second,
                ])

        return str(path)
