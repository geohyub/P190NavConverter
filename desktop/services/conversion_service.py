"""Conversion service — QThread-based pipeline execution."""

from __future__ import annotations

import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Signal


class ConversionWorker(QObject):
    """Runs ConversionPipeline in a background QThread."""

    finished = Signal(str, str)   # output_path, report_path
    error = Signal(str, str)      # error_message, traceback

    def __init__(self, config, controller, parent=None):
        super().__init__(parent)
        self._config = config
        self._controller = controller

    def run(self):
        try:
            from p190converter.engine.pipeline import ConversionPipeline

            pipeline = ConversionPipeline()
            pipeline.set_log_callback(self._log)

            # Step 0: Parse
            self._step(0, "active")

            def progress_cb(current, total):
                if total > 0:
                    self._controller.conversion_progress.emit(
                        current / total)

            self._step(0, "done")
            self._step(1, "active")

            if self._config.style == "B":
                output_path = pipeline.run_style_b(
                    self._config, progress_cb)
            else:
                output_path = pipeline.run_style_a(
                    self._config, progress_cb)

            self._step(1, "done")
            self._step(2, "active")
            # Writing happens inside _finalize() - mark done after
            self._step(2, "done")
            self._step(3, "done")
            self._step(4, "active")

            _out = Path(output_path)
            report_path = str(
                _out.with_name(_out.stem + "_QC_Report.txt"))
            self._step(4, "done")

            self._controller.conversion_done.emit(
                output_path, report_path)
            self.finished.emit(output_path, report_path)

        except Exception as exc:
            tb = traceback.format_exc()
            self._controller.conversion_error.emit(str(exc), tb)
            self._controller.conversion_log.emit("error", str(exc))
            self._controller.conversion_log.emit("error", tb)
            self.error.emit(str(exc), tb)

    def _log(self, level: str, message: str):
        self._controller.conversion_log.emit(level, message)

    def _step(self, index: int, state: str):
        self._controller.conversion_step.emit(index, state)


class BatchConversionWorker(QObject):
    """Runs batch conversion in a background QThread."""

    finished = Signal(int, int)  # succeeded, failed

    def __init__(self, style, batch_files, input_vals,
                 crs_config, geometry, h_records,
                 controller, parent=None):
        super().__init__(parent)
        self._style = style
        self._batch_files = batch_files
        self._input_vals = input_vals
        self._crs = crs_config
        self._geometry = geometry
        self._h_records = h_records
        self._controller = controller

    def run(self):
        import time
        from p190converter.engine.pipeline import ConversionPipeline
        from p190converter.models.survey_config import SurveyConfig
        from p190converter.utils.line_name import detect_line_name

        total = len(self._batch_files)
        succeeded = 0
        failed = 0

        self._log("info", f"Batch start: {total} files")

        for idx, item in enumerate(self._batch_files, 1):
            t0 = time.time()
            try:
                file_path = item if isinstance(item, str) else item[0]
                fname = Path(file_path).stem
                line_name = detect_line_name(file_path) or fname
                self._log("info",
                          f"[{idx}/{total}] Processing: {fname} ...")

                radex_decimals = int(
                    self._input_vals.get("radex_coord_decimals", 5))

                config = SurveyConfig(
                    style=self._style,
                    input_file=file_path if self._style == "B" else "",
                    line_name=line_name,
                    output_dir=self._input_vals.get("output_dir", ""),
                    npd_file=file_path if self._style == "A" else "",
                    track_file=self._input_vals.get("track_file", ""),
                    front_gps_source=self._input_vals.get("front_gps", ""),
                    tail_gps_source=self._input_vals.get("tail_gps", ""),
                    radex_coord_decimals=radex_decimals,
                    crs=self._crs,
                    h_records=self._h_records,
                    geometry=self._geometry,
                )

                pipeline = ConversionPipeline()
                if self._style == "B":
                    pipeline.run_style_b(config)
                else:
                    pipeline.run_style_a(config)

                dt = time.time() - t0
                self._log("success",
                          f"[{idx}/{total}] {fname} Done ({dt:.1f}s)")
                succeeded += 1
            except Exception as exc:
                dt = time.time() - t0
                self._log("error",
                          f"[{idx}/{total}] {fname} FAILED ({dt:.1f}s): {exc}")
                failed += 1

        self._log(
            "success" if failed == 0 else "warning",
            f"Batch complete: {succeeded}/{total} succeeded, "
            f"{failed} failed")
        self.finished.emit(succeeded, failed)

    def _log(self, level: str, message: str):
        self._controller.conversion_log.emit(level, message)


class FeatheringWorker(QObject):
    """Runs feathering analysis in a background QThread."""

    done = Signal(object, str, str, str, str)  # result, line_name, output, report, plot
    error = Signal(str)

    def __init__(self, npd_file, track_file, front_gps, tail_gps,
                 geometry, output_path, line_name, parent=None):
        super().__init__(parent)
        self._npd_file = npd_file
        self._track_file = track_file
        self._front_gps = front_gps
        self._tail_gps = tail_gps
        self._geometry = geometry
        self._output_path = output_path
        self._line_name = line_name

    def run(self):
        try:
            from p190converter.engine.parsers.npd_parser import parse_npd
            from p190converter.engine.parsers.track_parser import parse_track_file
            from p190converter.engine.geometry.gps_interpolation import (
                npd_time_to_seconds, interpolate_gps_at_times,
                compute_vessel_cog,
            )
            from p190converter.engine.qc.feathering_analysis import (
                run_feathering_analysis, generate_feathering_report,
            )

            track_data = parse_track_file(self._track_file)
            shot_times = track_data.df["time_seconds"].values.astype(float)
            ffids = track_data.df["ffid"].values.astype(float)

            df_front = parse_npd(self._npd_file, source=self._front_gps)
            df_tail = parse_npd(self._npd_file, source=self._tail_gps)

            front_t = np.array([
                npd_time_to_seconds(t) if t else np.nan
                for t in df_front["time_str"]])
            front_e = df_front["east"].values.astype(float)
            front_n = df_front["north"].values.astype(float)

            tail_t = np.array([
                npd_time_to_seconds(t) if t else np.nan
                for t in df_tail["time_str"]])
            tail_e = df_tail["east"].values.astype(float)
            tail_n = df_tail["north"].values.astype(float)

            fe, fn = interpolate_gps_at_times(
                front_t, front_e, front_n, shot_times, method="cubic")
            te, tn = interpolate_gps_at_times(
                tail_t, tail_e, tail_n, shot_times, method="cubic")

            vessel_cog = compute_vessel_cog(fe, fn, window=5)

            result = run_feathering_analysis(
                head_east=fe, head_north=fn,
                tail_east=te, tail_north=tn,
                vessel_cog=vessel_cog,
                shot_times=shot_times,
                ffids=ffids,
                n_channels=self._geometry.n_channels,
                rx_interval=self._geometry.rx_interval,
                feathering_alpha=self._geometry.feathering_alpha,
            )

            # Export report
            report = generate_feathering_report(result)
            _out = Path(self._output_path)
            report_path = str(
                _out.with_name(_out.stem + "_Feathering_Report.txt"))
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

            # Export plot
            plot_path = ""
            try:
                from p190converter.engine.qc.feathering_plot import (
                    generate_feathering_overview,
                )
                plot_path = str(
                    _out.with_name(_out.stem + "_Feathering_Overview.png"))
                generate_feathering_overview(
                    result, plot_path, line_name=self._line_name)
            except Exception:
                pass

            self.done.emit(result, self._line_name,
                           self._output_path, report_path, plot_path)

        except Exception as exc:
            self.error.emit(str(exc))
