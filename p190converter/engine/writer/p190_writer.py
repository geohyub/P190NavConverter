"""P190 file writer — assembles H + S + R records into output file."""

from pathlib import Path
from typing import Callable, List, Optional

from .h_record import format_h_records
from .s_record import format_s_record
from .r_record import format_r_records
from ..crs.transformer import CRSTransformer
from ...models.shot_gather import ShotGatherCollection
from ...models.survey_config import SurveyConfig


class P190Writer:
    """Write P190 files from ShotGatherCollection."""

    def write(
        self,
        collection: ShotGatherCollection,
        config: SurveyConfig,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Write P190 file.

        Args:
            collection: ShotGatherCollection with all shots
            config: Survey configuration (H records, CRS, etc.)
            output_path: Output file path
            progress_callback: Optional (current, total) callback

        Returns:
            Output file path
        """
        crs_transformer = CRSTransformer(config.crs)
        lines: List[str] = []

        # Apply CRS to H records
        config.h_records.apply_crs(config.crs)

        # 1. H Records
        h_lines = format_h_records(config.h_records)
        lines.extend(h_lines)

        # 2. S + R Records for each shot
        total = collection.n_shots
        for idx, shot in enumerate(collection.shots):
            # Set line name
            if not shot.line_name:
                shot.line_name = config.line_name

            # CRS: UTM -> Lat/Lon
            lat, lon = crs_transformer.utm_to_latlon(
                shot.source_x, shot.source_y
            )
            shot.source_lat = lat
            shot.source_lon = lon

            # S Record
            s_line = format_s_record(
                shot,
                vessel_id=config.vessel_id,
                source_id=config.source_id,
            )
            lines.append(s_line)

            # R Records
            r_lines = format_r_records(
                shot,
                streamer_id=config.streamer_id,
            )
            lines.extend(r_lines)

            if progress_callback and idx % 100 == 0:
                progress_callback(idx + 1, total)

        if progress_callback:
            progress_callback(total, total)

        # Write to file
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="ascii", newline="\n") as f:
            for line in lines:
                f.write(line + "\n")

        return str(path)

    def validate_output(self, output_path: str) -> List[str]:
        """Quick validation of written P190 file.

        Returns:
            List of warning/error messages (empty = valid)
        """
        issues = []
        with open(output_path, "r", encoding="ascii") as f:
            for line_num, line in enumerate(f, 1):
                line = line.rstrip("\n").rstrip("\r")
                if len(line) != 80:
                    issues.append(
                        f"Line {line_num}: length {len(line)} != 80"
                    )
                if line and line[0] not in ("H", "S", "R", "X"):
                    issues.append(
                        f"Line {line_num}: unknown record type '{line[0]}'"
                    )
        return issues
