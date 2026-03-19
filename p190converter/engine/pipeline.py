"""Conversion pipeline orchestrator."""

import math
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .parsers.radex_parser import parse_radex_export
from .parsers.npd_parser import parse_npd
from .parsers.track_parser import parse_track_file
from .geometry.interpolation import compute_heading, interpolate_receivers
from .geometry.gps_interpolation import npd_time_to_seconds, interpolate_gps_at_times
from .writer.p190_writer import P190Writer
from .writer.radex_tsv_writer import RadExTSVWriter
from .writer.s_record import point_number_value
from .qc.validator import validate_p190
from .qc.report import generate_qc_report
from ..models.shot_gather import ShotGather, ShotGatherCollection, ReceiverPosition
from ..models.survey_config import SurveyConfig


class ConversionPipeline:
    """Orchestrate the full conversion process."""

    def __init__(self):
        self.writer = P190Writer()
        self.radex_writer = RadExTSVWriter()
        self.collection: Optional[ShotGatherCollection] = None
        self.output_path: Optional[str] = None
        self._log_callback: Optional[Callable[[str, str], None]] = None

    def set_log_callback(self, callback: Callable[[str, str], None]):
        """Set logging callback: callback(level, message)."""
        self._log_callback = callback

    def _log(self, level: str, msg: str):
        if self._log_callback:
            self._log_callback(level, msg)

    def _log_p190_constraints(self):
        """Warn about hard P190 limits and point to safer sidecar exports."""
        if not self.collection or not self.collection.shots:
            return

        over_limit = [
            shot.ffid for shot in self.collection.shots
            if abs(shot.ffid) > 999999
        ]
        if over_limit:
            self._log(
                "warning",
                "P190 point numbers are limited to 6 characters. "
                f"{len(over_limit)} shot(s) exceed that limit and are truncated "
                "in the .p190 output.",
            )

        collision_map: dict[int, set[int]] = {}
        for shot in self.collection.shots:
            mapped = point_number_value(shot.ffid)
            collision_map.setdefault(mapped, set()).add(shot.ffid)

        collisions = {
            mapped: originals
            for mapped, originals in collision_map.items()
            if len(originals) > 1
        }
        if collisions:
            sample_items = list(collisions.items())[:3]
            sample = ", ".join(
                f"{mapped} <- {sorted(originals)[:3]}"
                for mapped, originals in sample_items
            )
            self._log(
                "warning",
                "Truncated P190 point-number collisions detected. "
                f"{len(collisions)} mapped value(s) are reused after 6-digit truncation. "
                f"Examples: {sample}. Prefer the RadEx geometry TSV sidecar for import.",
            )

        self._log(
            "info",
            "P190 grid coordinates are limited to 0.1 m (F9.1) by the standard. "
            "A full-precision RadEx geometry TSV sidecar is also exported.",
        )

    def _finalize(self, config: SurveyConfig, progress_callback=None):
        """Common finalization: write P190, validate, QC report."""
        # Determine output path
        input_path = config.input_file or config.npd_file
        output_dir = config.output_dir or str(Path(input_path).parent)
        output_name = f"{config.line_name}_S_{config.line_name}.p190"
        self.output_path = str(Path(output_dir) / output_name)

        # Write P190
        self._log("info", "P190 파일 작성 중...")
        self.writer.write(
            self.collection, config, self.output_path,
            progress_callback=progress_callback,
        )
        self._log("success", f"P190 작성 완료: {self.output_path}")

        base_path = str(Path(self.output_path).with_suffix(""))
        geometry_path = f"{base_path}_RadEx_Geometry.tsv"
        geometry_pretty_path = f"{base_path}_RadEx_Geometry_Aligned.txt"
        ffid_map_path = f"{base_path}_FFID_Map.tsv"
        self.radex_writer = RadExTSVWriter(coord_decimals=config.radex_coord_decimals)
        self.radex_writer.write_geometry(self.collection, geometry_path)
        self.radex_writer.write_geometry_pretty(
            self.collection,
            geometry_pretty_path,
        )
        self.radex_writer.write_ffid_map(self.collection, ffid_map_path)
        self._log("info", f"RadEx TSV export: {geometry_path}")
        self._log("info", f"RadEx aligned text export: {geometry_pretty_path}")
        self._log("info", f"FFID crosswalk export: {ffid_map_path}")
        self._log(
            "info",
            f"RadEx coordinate decimals: {config.radex_coord_decimals}",
        )
        self._log_p190_constraints()

        # Validate
        self._log("info", "출력 검증 중...")
        issues = self.writer.validate_output(self.output_path)
        if issues:
            for issue in issues[:10]:
                self._log("warning", issue)
            self._log("warning", f"총 {len(issues)} 건의 검증 이슈")
        else:
            self._log("success", "검증 통과 - 모든 라인 80 컬럼 준수")

        # QC Report
        qc_result = validate_p190(self.output_path)
        report_text = generate_qc_report(qc_result, config)
        out = Path(self.output_path)
        report_path = str(out.with_name(out.stem + "_QC_Report.txt"))
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        self._log("info", f"QC 리포트 저장: {report_path}")

        return self.output_path

    def run_style_b(
        self,
        config: SurveyConfig,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Run Style B conversion: RadExPro export -> P190.

        Args:
            config: Survey configuration with input_file, line_name, etc.
            progress_callback: Optional (current, total) progress callback

        Returns:
            Output P190 file path
        """
        self._log("info", f"Style B 변환 시작: {config.input_file}")

        # 1. Parse RadExPro export
        self._log("info", "RadExPro 익스포트 파싱 중...")
        self.collection = parse_radex_export(config.input_file)
        self.collection.line_name = config.line_name

        self._log("success",
                  f"파싱 완료: {self.collection.n_shots} shots, "
                  f"{self.collection.n_channels} channels")

        # 2. Set line name on all shots
        for shot in self.collection.shots:
            shot.line_name = config.line_name

        # 3. Finalize (write + validate + QC)
        return self._finalize(config, progress_callback)

    def run_style_a(
        self,
        config: SurveyConfig,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Run Style A conversion: NPD + Track + Marine Geometry -> P190.

        Pipeline:
          1. Parse Track file → unique shots with real FFIDs + times
          2. Parse NPD for front/tail GPS with selected sources
          3. Smooth GPS staircase via CubicSpline interpolation
          4. Evaluate GPS positions at each Track shot time
          5. Compute heading from front→tail, apply source offset rotation
          6. Interpolate receiver positions
          7. Write P190 + validate + QC report

        Args:
            config: Survey configuration with npd_file, track_file, geometry, etc.
            progress_callback: Optional (current, total) progress callback

        Returns:
            Output P190 file path
        """
        npd_file = config.npd_file or config.input_file
        track_file = config.track_file
        self._log("info", f"Style A 변환 시작: {npd_file}")

        # ── 1. Parse Track file ──
        if not track_file:
            raise ValueError("Style A requires a Track file (track_file not set)")

        self._log("info", f"Track 파일 파싱 중: {track_file}")
        track_data = parse_track_file(track_file)
        self._log("success",
                  f"Track: {track_data.n_shots} shots, "
                  f"FFID {track_data.ffid_range[0]}-{track_data.ffid_range[1]}")

        # ── 2. Parse NPD for front and tail GPS ──
        self._log("info", f"NPD 파싱 중 (Front: {config.front_gps_source})...")
        df_front = parse_npd(npd_file, source=config.front_gps_source or 0)
        self._log("success", f"Front GPS: {len(df_front)} records")

        self._log("info", f"NPD 파싱 중 (Tail: {config.tail_gps_source})...")
        df_tail = parse_npd(npd_file, source=config.tail_gps_source or 1)
        self._log("success", f"Tail GPS: {len(df_tail)} records")

        # ── 3. Convert NPD times to seconds ──
        front_times = np.array([
            npd_time_to_seconds(t) if t else np.nan
            for t in df_front["time_str"]
        ])
        front_east = df_front["east"].values.astype(float)
        front_north = df_front["north"].values.astype(float)

        tail_times = np.array([
            npd_time_to_seconds(t) if t else np.nan
            for t in df_tail["time_str"]
        ])
        tail_east = df_tail["east"].values.astype(float)
        tail_north = df_tail["north"].values.astype(float)

        # Shot times from Track
        shot_times = track_data.df["time_seconds"].values.astype(float)

        # ── 4. Interpolate GPS at shot times (CubicSpline smoothing) ──
        self._log("info", "Front GPS staircase 보간 중...")
        front_e_at_shots, front_n_at_shots = interpolate_gps_at_times(
            front_times, front_east, front_north,
            shot_times, method="cubic",
        )
        self._log("success", "Front GPS 보간 완료")

        self._log("info", "Tail GPS staircase 보간 중...")
        tail_e_at_shots, tail_n_at_shots = interpolate_gps_at_times(
            tail_times, tail_east, tail_north,
            shot_times, method="cubic",
        )
        self._log("success", "Tail GPS 보간 완료")

        # ── 5. Build ShotGatherCollection ──
        geometry = config.geometry
        n_shots = track_data.n_shots
        shots = []

        # ── Source position mode ──
        # "front_gps": NPD GPS 직접 사용 (기본값 — 독립 검증)
        #   COS_Sparker 선택 → ~11m, Head_Buoy → ~25m 차이
        # "track_sou": Track SOU_X/SOU_Y 사용 (= RadExPro 계산값)
        source_mode = getattr(config, 'source_position_mode', 'front_gps')

        # RX offset: RadExPro vessel 기준 → source 기준 변환 + convention 변환
        #   RadExPro convention: dx=PORT-positive, dy=AFT-positive
        #   Our convention: dx=STARBOARD-positive, dy=FORWARD-positive
        #   → negate both dx and dy
        from copy import copy
        adj_geom = copy(geometry)
        rel_dx = geometry.rx1_dx - geometry.source_dx  # source-relative (RadExPro frame)
        rel_dy = geometry.rx1_dy - geometry.source_dy
        adj_geom.rx1_dx = -rel_dx  # PORT→STARBOARD
        adj_geom.rx1_dy = -rel_dy  # AFT→FORWARD

        if source_mode == "track_sou":
            self._log("info",
                      f"Source: Track SOU_X/SOU_Y 사용 (RadExPro 계산값과 동일)")
        else:
            self._log("info",
                      f"Source: Front GPS ({config.front_gps_source}) 직접 사용")
        self._log("info",
                  f"RX1 offset: RadExPro({rel_dx:.4f}, {rel_dy:.4f}) "
                  f"-> convention 변환({adj_geom.rx1_dx:.4f}, {adj_geom.rx1_dy:.4f})")

        # ── 4.5. Vessel COG for feathering model ──
        use_feathering = geometry.interp_method.lower() == "feathering"
        vessel_cog = None

        if use_feathering:
            from .geometry.gps_interpolation import compute_vessel_cog
            vessel_cog = compute_vessel_cog(
                front_e_at_shots, front_n_at_shots, window=5,
            )
            mean_cog = float(np.nanmean(vessel_cog))
            cable_dir = compute_heading(
                float(front_e_at_shots[0]), float(front_n_at_shots[0]),
                float(tail_e_at_shots[0]), float(tail_n_at_shots[0]),
            )
            avg_feathering = (cable_dir - mean_cog + 180) % 360 - 180
            self._log("info",
                      f"Feathering 모델 활성: Vessel COG ~{mean_cog:.1f} deg, "
                      f"Cable dir ~{cable_dir:.1f} deg, "
                      f"Feathering ~{avg_feathering:.1f} deg")

        self._log("info", f"{n_shots} shots 리시버 보간 중 (method={geometry.interp_method})...")

        for i in range(n_shots):
            row = track_data.df.iloc[i]

            # Front/Tail GPS at this shot time (heading 계산용)
            fe, fn = float(front_e_at_shots[i]), float(front_n_at_shots[i])
            te, tn = float(tail_e_at_shots[i]), float(tail_n_at_shots[i])

            # Cable heading: Front GPS → Tail GPS 방향
            heading = compute_heading(fe, fn, te, tn)

            # Source position: 모드에 따라 결정
            if source_mode == "track_sou":
                source_x = float(row["sou_x"])
                source_y = float(row["sou_y"])
            else:
                source_x = fe
                source_y = fn

            # Time info from Track file
            day = int(row["day"])
            hour = int(row["hour"])
            minute = int(row["minute"])
            second = int(row["second"])

            # Interpolate receiver positions (source-relative offset)
            # For feathering method: pass head/tail GPS and vessel COG
            interp_kwargs = {}
            if use_feathering and vessel_cog is not None:
                interp_kwargs = {
                    'head_x': fe, 'head_y': fn,
                    'tail_x': te, 'tail_y': tn,
                    'vessel_heading_deg': float(vessel_cog[i]),
                }

            receivers = interpolate_receivers(
                source_x, source_y, heading, adj_geom,
                **interp_kwargs,
            )

            shot = ShotGather(
                ffid=int(row["ffid"]),
                source_x=source_x,
                source_y=source_y,
                receivers=receivers,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
                heading=heading,
                line_name=config.line_name,
            )
            shots.append(shot)

            # Progress (adaptive frequency)
            prog_step = max(1, min(100, n_shots // 20))
            if progress_callback and i % prog_step == 0:
                progress_callback(i, n_shots)

        self.collection = ShotGatherCollection(
            shots=shots,
            line_name=config.line_name,
            n_channels=geometry.n_channels,
        )

        self._log("success",
                  f"보간 완료: {len(shots)} shots, "
                  f"{geometry.n_channels} channels, "
                  f"method={geometry.interp_method}")

        # ── 6. Finalize (write + validate + QC) ──
        return self._finalize(config, progress_callback)
