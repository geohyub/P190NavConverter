"""P190 NavConverter — Application entry point.

Wires GUI panels to the conversion engine with threaded execution.
"""

import threading
import time
import traceback
from pathlib import Path

from .gui.main_window import MainWindow
from .gui.panels import (
    InputPanel,
    GeometryPanel,
    HeaderPanel,
    CRSPanel,
    PreviewPanel,
    LogPanel,
    ResultsPanel,
    FeatheringPanel,
    ComparisonPanel,
    HelpPanel,
)
from .engine.pipeline import ConversionPipeline
from .engine.parsers.radex_parser import parse_radex_export
from .models.survey_config import SurveyConfig, CRSConfig, HRecordConfig
from .utils.settings import (
    load_settings, save_settings, save_full_config, load_full_config,
    save_profile, load_profile, delete_profile, list_profiles,
)
from .utils.line_name import detect_line_name


class App:
    """Application controller — connects GUI panels to engine."""

    def __init__(self):
        self._window = MainWindow()
        self._pipeline = ConversionPipeline()
        self._collection = None
        self._converting = False
        self._start_time = None

        self._create_panels()
        self._register_panels()
        self._connect_events()
        self._load_saved_settings()

        # Show input panel by default
        self._window.show_panel("input")

    def _create_panels(self):
        self._input = InputPanel(self._window)
        self._geometry = GeometryPanel(self._window)
        self._header = HeaderPanel(self._window)
        self._crs = CRSPanel(self._window)
        self._preview = PreviewPanel(self._window)
        self._feathering = FeatheringPanel(self._window)
        self._comparison = ComparisonPanel(self._window)
        self._log = LogPanel(self._window)
        self._results = ResultsPanel(self._window)
        self._help = HelpPanel(self._window)

    def _register_panels(self):
        panels = [
            ("input", self._input),
            ("geometry", self._geometry),
            ("header", self._header),
            ("crs", self._crs),
            ("preview", self._preview),
            ("feathering", self._feathering),
            ("comparison", self._comparison),
            ("log", self._log),
            ("results", self._results),
            ("help", self._help),
        ]
        for panel_id, widget in panels:
            self._window.register_panel(panel_id, widget)

    def _connect_events(self):
        # Input panel callbacks
        self._input.set_file_loaded_callback(self._on_file_loaded)
        self._input.set_style_changed_callback(self._on_style_changed)

        # CRS panel callback
        self._crs.set_crs_changed_callback(self._on_crs_changed)

        # Geometry panel callback (real-time preview)
        self._geometry.set_geometry_changed_callback(self._on_geometry_changed)

        # Comparison panel log callback
        self._comparison.set_log_callback(self._comparison_log)

        # Profile management callbacks
        self._input.set_profile_save_callback(self._save_profile)
        self._input.set_profile_load_callback(self._load_profile)
        self._input.set_profile_delete_callback(self._delete_profile)

        # Convert button
        self._window.set_convert_command(self._start_conversion)

    def _comparison_log(self, level, msg):
        """Route comparison panel logs to log panel."""
        self._log.append(level, msg)

    def _restore_style(self, style: str):
        """Switch the input panel to the requested mode."""
        if style == "A":
            self._input._mode_seg.set("Style A: NPD + Geometry")
            self._input._on_mode_change("Style A: NPD + Geometry")
        else:
            self._input._mode_seg.set("Style B: RadExPro Export")
            self._input._on_mode_change("Style B: RadExPro Export")

    def _restore_input_files(self, style: str, files: dict):
        """Restore file widgets and refresh parsed summary/preview state."""
        if style == "A":
            npd_file = files.get("npd_file", "")
            track_file = files.get("track_file", "")

            if npd_file:
                self._input._npd_drop.value = npd_file
                self._load_npd_file(npd_file)
            if track_file:
                self._input._track_drop.value = track_file
                self._load_track_file(track_file)
            if files.get("output_dir"):
                self._input._output_dir_a.value = files["output_dir"]
        else:
            input_file = files.get("input_file", "")

            if input_file:
                self._input._radex_drop.value = input_file
                self._load_radex_file(input_file)
            if files.get("output_dir"):
                self._input._output_dir_b.value = files["output_dir"]

    def _load_saved_settings(self):
        """Restore settings from previous session."""
        # Refresh profile dropdown
        self._input.refresh_profiles()

        saved = load_full_config()
        if not saved:
            return

        style = saved.get("style", "B")
        self._restore_style(style)

        # Restore line name
        if saved.get("line_name"):
            try:
                self._input.set_line_name(saved["line_name"])
            except Exception:
                pass

        if saved.get("export_options", {}).get("radex_coord_decimals") is not None:
            try:
                self._input.set_radex_coord_decimals(
                    saved["export_options"]["radex_coord_decimals"]
                )
            except Exception:
                pass

        if saved.get("files"):
            try:
                self._restore_input_files(style, saved["files"])
            except Exception:
                pass

        if saved.get("crs"):
            try:
                self._crs.set_crs_config(saved["crs"])
            except Exception:
                pass

        if saved.get("geometry"):
            try:
                self._geometry.set_geometry(saved["geometry"])
            except Exception:
                pass

        gps = saved.get("gps_sources", {})
        if gps:
            try:
                self._input.set_selected_gps_sources(
                    gps.get("front", ""),
                    gps.get("tail", ""),
                )
            except Exception:
                pass

    def _save_profile(self, name: str):
        """Save current settings as named profile."""
        input_vals = self._input.get_config_values()
        data = {
            "style": input_vals.get("style", "B"),
            "line_name": self._input.get_line_name(),
            "files": {
                "input_file": input_vals.get("input_file", ""),
                "npd_file": input_vals.get("npd_file", ""),
                "track_file": input_vals.get("track_file", ""),
                "output_dir": input_vals.get("output_dir", ""),
            },
            "crs": {},
            "geometry": {},
            "h_records": {},
            "gps_sources": {
                "front": input_vals.get("front_gps", ""),
                "tail": input_vals.get("tail_gps", ""),
            },
            "export_options": {
                "radex_coord_decimals": input_vals.get("radex_coord_decimals", "5"),
            },
        }

        # CRS
        crs = self._crs.get_crs_config()
        data["crs"] = {
            "utm_zone": crs.utm_zone,
            "hemisphere": crs.hemisphere,
            "epsg_code": crs.epsg_code,
            "display_name": crs.display_name,
            "datum_name": crs.datum_name,
        }

        # Geometry
        geom = self._geometry.get_geometry()
        data["geometry"] = {
            "source_dx": geom.source_dx,
            "source_dy": geom.source_dy,
            "rx1_dx": geom.rx1_dx,
            "rx1_dy": geom.rx1_dy,
            "n_channels": geom.n_channels,
            "rx_interval": geom.rx_interval,
            "cable_depth": geom.cable_depth,
            "interp_method": geom.interp_method,
            "feathering_alpha": geom.feathering_alpha,
        }

        # H Records
        h_config = self._header.get_h_record_config()
        data["h_records"] = h_config.records

        save_profile(name, data)
        self._log.append("success", f"Profile '{name}' saved")

    def _load_profile(self, name: str):
        """Load a named profile and restore all panels."""
        data = load_profile(name)
        if not data:
            self._log.append("error", f"Profile '{name}' not found")
            return

        # Restore style
        style = data.get("style", "B")
        self._restore_style(style)

        # Restore line name
        if data.get("line_name"):
            self._input.set_line_name(data["line_name"])

        # Restore file paths
        files = data.get("files", {})
        self._restore_input_files(style, files)

        export_options = data.get("export_options", {})
        if export_options.get("radex_coord_decimals") is not None:
            self._input.set_radex_coord_decimals(
                export_options["radex_coord_decimals"]
            )

        # Restore CRS
        if data.get("crs"):
            self._crs.set_crs_config(data["crs"])

        # Restore Geometry
        if data.get("geometry"):
            self._geometry.set_geometry(data["geometry"])

        # Restore H Records
        if data.get("h_records"):
            self._header.set_h_records(data["h_records"])

        # Restore GPS sources
        gps = data.get("gps_sources", {})
        if gps.get("front") or gps.get("tail"):
            self._input.set_selected_gps_sources(
                gps.get("front", ""),
                gps.get("tail", ""),
            )

        self._log.append("success", f"Profile '{name}' loaded")

    def _delete_profile(self, name: str):
        """Delete a named profile."""
        if delete_profile(name):
            self._log.append("info", f"Profile '{name}' deleted")
        else:
            self._log.append("error", f"Profile '{name}' not found")

    def _on_file_loaded(self, file_type: str, path: str):
        """Handle file load from input panel."""
        if file_type == "radex":
            self._load_radex_file(path)
        elif file_type == "npd":
            self._load_npd_file(path)
        elif file_type == "track":
            self._load_track_file(path)

        # Auto-detect line name if field is empty
        if not self._input.get_line_name():
            detected = detect_line_name(path)
            if detected:
                self._input.set_line_name(detected)
                self._log.append("info", f"Line name auto-detected: {detected}")

    def _load_radex_file(self, path: str):
        """Parse RadExPro export and update preview."""
        try:
            self._log.append("info", f"Loading: {path}")
            self._collection = parse_radex_export(path)
            n = self._collection.n_shots
            ch = self._collection.n_channels
            ffid_lo, ffid_hi = self._collection.ffid_range

            summary = (
                f"Shots: {n:,}  |  Channels: {ch}  |  "
                f"FFID: {ffid_lo}-{ffid_hi}"
            )
            self._input.update_summary(summary)
            self._log.append("success", f"Parsed: {n} shots, {ch} channels")

            # Update title bar file status
            fname = Path(path).name
            self._window.set_file_status(
                f"{fname}  |  {n:,} shots, {ch}ch, FFID {ffid_lo}-{ffid_hi}"
            )

            # Update preview
            self._preview.set_collection(self._collection)
            self._log.append("info", "Preview updated with track data")

        except Exception as exc:
            self._log.append("error", f"Parse error: {exc}")
            self._input.update_summary(f"Error: {exc}")

    def _load_npd_file(self, path: str):
        """Parse NPD file and populate GPS source dropdowns."""
        try:
            self._log.append("info", f"Loading NPD: {path}")
            try:
                from .engine.parsers.npd_parser import parse_npd_sources
                sources = parse_npd_sources(path)
                self._input.update_gps_sources(sources)
                self._log.append("success",
                                 f"NPD sources: {', '.join(sources)}")
            except ImportError:
                self._log.append("warning",
                                 "NPD parser not yet implemented (Phase 11)")
                self._input.update_gps_sources(["Head_Buoy", "Tail_Buoy"])

            # Update title bar file status
            fname = Path(path).name
            self._window.set_file_status(f"{fname}  |  NPD loaded")
        except Exception as exc:
            self._log.append("error", f"NPD load error: {exc}")

    def _load_track_file(self, path: str):
        """Parse Track file and display summary."""
        try:
            self._log.append("info", f"Loading Track: {path}")
            from .engine.parsers.track_parser import parse_track_file
            track_data = parse_track_file(path)

            n = track_data.n_shots
            ch = track_data.n_channels
            ffid_lo, ffid_hi = track_data.ffid_range
            t_lo, t_hi = track_data.time_range

            summary = (
                f"Shots: {n:,}  |  Channels: {ch if ch > 0 else '--'}  |  "
                f"FFID: {ffid_lo}-{ffid_hi}"
            )
            self._input.update_summary(summary)
            if ch > 0:
                self._geometry.set_channel_count(ch)
            self._log.append("success",
                             f"Track: {n:,} shots, {ch if ch > 0 else '--'} channels, "
                             f"FFID {ffid_lo}-{ffid_hi}, "
                             f"time {t_lo:.0f}-{t_hi:.0f}s")

            # Show any parsing warnings
            for warn_msg in track_data.warnings:
                self._log.append("warning", warn_msg)

            fname = Path(path).name
            self._window.set_file_status(
                f"{fname}  |  {n:,} shots, "
                f"{ch if ch > 0 else '--'}ch, FFID {ffid_lo}-{ffid_hi}"
            )

        except Exception as exc:
            self._log.append("error", f"Track load error: {exc}")

    def _on_style_changed(self, style: str):
        """Handle mode switch between Style A/B."""
        self._window.set_style_mode(style)
        self._log.append("info", f"Mode changed to Style {style}")

    def _on_crs_changed(self, crs_config: CRSConfig):
        """Handle CRS change — update H records."""
        self._header.apply_crs_to_records(crs_config)
        if crs_config.display_name:
            crs_label = f"{crs_config.display_name} (EPSG:{crs_config.epsg_code})"
        elif crs_config.is_utm:
            crs_label = (f"UTM {crs_config.utm_zone}"
                         f"{crs_config.hemisphere} (EPSG:{crs_config.epsg_code})")
        else:
            crs_label = f"EPSG:{crs_config.epsg_code}"
        self._log.append("info", f"CRS updated: {crs_label}")

    def _on_geometry_changed(self, geometry):
        """Handle geometry parameter change — update preview."""
        pass

    def _start_conversion(self):
        """Start conversion in background thread."""
        if self._converting:
            self._log.append("warning", "Conversion already in progress")
            return

        # Check for batch mode
        input_vals = self._input.get_config_values()
        if input_vals.get("batch_mode"):
            return self._start_batch_conversion(input_vals)

        # Gather config from panels
        try:
            radex_coord_decimals = int(input_vals.get("radex_coord_decimals", 5))
        except (TypeError, ValueError):
            self._log.append("error", "RadEx Decimals must be an integer")
            self._window.show_panel("input")
            return

        if not 0 <= radex_coord_decimals <= 8:
            self._log.append("error", "RadEx Decimals must be between 0 and 8")
            self._window.show_panel("input")
            return

        config = SurveyConfig(
            style=input_vals["style"],
            input_file=input_vals.get("input_file", ""),
            line_name=input_vals.get("line_name", "Unknown"),
            output_dir=input_vals.get("output_dir", ""),
            npd_file=input_vals.get("npd_file", ""),
            track_file=input_vals.get("track_file", ""),
            front_gps_source=input_vals.get("front_gps", ""),
            tail_gps_source=input_vals.get("tail_gps", ""),
            radex_coord_decimals=radex_coord_decimals,
            crs=self._crs.get_crs_config(),
            h_records=self._header.get_h_record_config(),
            geometry=self._geometry.get_geometry(),
        )

        # Validate inputs based on style
        if config.style == "B" and not config.input_file:
            self._log.append("error", "No RadExPro export file selected")
            self._window.show_panel("input")
            return

        if config.style == "A":
            if not config.npd_file:
                self._log.append("error", "No NPD file selected")
                self._window.show_panel("input")
                return
            if not config.track_file:
                self._log.append("error", "No Track file selected")
                self._window.show_panel("input")
                return

        if not config.line_name:
            self._log.append("error", "Line name is required")
            return

        # Show & reset step indicator
        self._window.show_step_indicator()
        step = self._window.step_indicator
        step.reset()

        # Switch to log panel
        self._window.show_panel("log")

        # Start threaded conversion
        self._converting = True
        self._start_time = time.time()
        self._update_status("Converting...", "warning")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(config,),
            daemon=True,
        )
        thread.start()

        # Start elapsed time updater
        self._update_elapsed()

    def _run_conversion(self, config: SurveyConfig):
        """Run conversion pipeline in background thread."""
        try:
            # Set log callback (thread-safe via after())
            self._pipeline.set_log_callback(self._thread_log)

            step = self._window.step_indicator

            # Step 1: Parse
            self._set_step(0, "active")

            def progress_cb(current, total):
                frac = current / total if total > 0 else 0
                self._window.after(0, self._window.status_bar.set_progress, frac)

            # Step 1 done, Step 2: Transform
            self._set_step(0, "done")
            self._set_step(1, "active")

            if config.style == "B":
                output_path = self._pipeline.run_style_b(config, progress_cb)
            else:
                output_path = self._pipeline.run_style_a(config, progress_cb)

            # Steps 2-4 done during pipeline execution
            self._set_step(1, "done")
            self._set_step(2, "done")
            self._set_step(3, "done")
            self._set_step(4, "done")
            self._window.after(0, self._window.status_bar.set_step_label, "")

            # Success
            report_path = output_path.replace(".p190", "_QC_Report.txt")
            self._window.after(0, self._on_conversion_done,
                               output_path, report_path)

        except Exception as exc:
            tb = traceback.format_exc()
            # Mark current active step as error
            for i in range(5):
                if self._window.step_indicator._states[i] == "active":
                    self._window.after(0, self._window.step_indicator.set_step,
                                       i, "error")
                    break
            self._window.after(0, self._window.status_bar.set_step_label, "")
            self._window.after(0, self._on_conversion_error, str(exc), tb)

    def _set_step(self, index: int, state: str):
        """Thread-safe step indicator + status bar label update."""
        self._window.after(0, self._window.step_indicator.set_step,
                           index, state)
        labels = ["Parsing...", "Transforming...", "Writing...",
                   "Validating...", "QC Check..."]
        if state == "active" and 0 <= index < len(labels):
            self._window.after(0, self._window.status_bar.set_step_label,
                               labels[index])

    def _thread_log(self, level: str, message: str):
        """Thread-safe log append via main thread."""
        self._window.after(0, self._log.append, level, message)

    def _on_conversion_done(self, output_path: str, report_path: str):
        """Handle successful conversion."""
        self._converting = False
        elapsed = time.time() - self._start_time

        self._update_status("Complete", "success")
        self._window.status_bar.set_progress(1.0)
        self._window.hide_step_indicator()

        self._log.append("success",
                         f"Conversion complete in {elapsed:.1f}s: {output_path}")

        # Update results panel
        self._results.set_output(output_path, report_path)

        # QC check
        from .engine.qc.validator import validate_p190
        qc = validate_p190(output_path)
        details = (
            f"Total lines:  {qc.total_lines:,}\n"
            f"H Records:    {qc.h_records}\n"
            f"S Records:    {qc.s_records:,}\n"
            f"R Records:    {qc.r_records:,}\n"
            f"Line errors:  {qc.line_length_errors}\n"
            f"Issues:       {len(qc.issues)}"
        )
        self._results.set_qc_result(qc.passed, details)

        # Show results panel
        self._window.show_panel("results")

        # Run feathering analysis for Style A (automatically)
        try:
            input_vals = self._input.get_config_values()
            if input_vals.get("style") == "A":
                self._run_feathering_analysis(output_path, input_vals)
        except Exception as fe:
            self._log.append("warning", f"Feathering analysis skipped: {fe}")

        # Save full config for next session restore
        try:
            config = SurveyConfig(
                style=self._input.current_style,
                input_file=self._input.get_config_values().get("input_file", ""),
                line_name=self._input.get_line_name(),
                output_dir=self._input.get_config_values().get("output_dir", ""),
                npd_file=self._input.get_config_values().get("npd_file", ""),
                track_file=self._input.get_config_values().get("track_file", ""),
                front_gps_source=self._input.get_config_values().get("front_gps", ""),
                tail_gps_source=self._input.get_config_values().get("tail_gps", ""),
                radex_coord_decimals=int(
                    self._input.get_config_values().get("radex_coord_decimals", 5)
                ),
                crs=self._crs.get_crs_config(),
                h_records=self._header.get_h_record_config(),
                geometry=self._geometry.get_geometry(),
            )
            save_full_config(config)
        except Exception:
            # Fallback: save minimal settings
            save_settings({
                "last_output": output_path,
                "last_line_name": Path(output_path).stem,
            })

    def _on_conversion_error(self, error: str, tb: str):
        """Handle conversion error."""
        self._converting = False
        self._update_status("Error", "error")
        self._window.hide_step_indicator()
        self._log.append("error", f"Conversion failed: {error}")
        self._log.append("error", tb)

    def _run_feathering_analysis(self, output_path: str, input_vals: dict):
        """Run feathering analysis after Style A conversion.

        Parses NPD GPS and track data to compute comprehensive
        feathering analysis with all physical variables.
        """
        import numpy as np

        npd_file = input_vals.get("npd_file", "")
        track_file = input_vals.get("track_file", "")
        front_gps = input_vals.get("front_gps", "Head_Buoy")
        tail_gps = input_vals.get("tail_gps", "Tail_Buoy")

        if not npd_file or not track_file:
            return

        self._log.append("info", "Feathering analysis starting...")

        from .engine.parsers.npd_parser import parse_npd
        from .engine.parsers.track_parser import parse_track_file
        from .engine.geometry.gps_interpolation import (
            npd_time_to_seconds, interpolate_gps_at_times,
            compute_vessel_cog,
        )
        from .engine.qc.feathering_analysis import run_feathering_analysis

        # Parse track
        track_data = parse_track_file(track_file)
        shot_times = track_data.df["time_seconds"].values.astype(float)
        ffids = track_data.df["ffid"].values.astype(float)

        # Parse NPD for front and tail GPS
        df_front = parse_npd(npd_file, source=front_gps)
        df_tail = parse_npd(npd_file, source=tail_gps)

        front_t = np.array([
            npd_time_to_seconds(t) if t else np.nan
            for t in df_front["time_str"]
        ])
        front_e = df_front["east"].values.astype(float)
        front_n = df_front["north"].values.astype(float)

        tail_t = np.array([
            npd_time_to_seconds(t) if t else np.nan
            for t in df_tail["time_str"]
        ])
        tail_e = df_tail["east"].values.astype(float)
        tail_n = df_tail["north"].values.astype(float)

        # Interpolate at shot times
        fe, fn = interpolate_gps_at_times(
            front_t, front_e, front_n, shot_times, method="cubic"
        )
        te, tn = interpolate_gps_at_times(
            tail_t, tail_e, tail_n, shot_times, method="cubic"
        )

        # Vessel COG
        vessel_cog = compute_vessel_cog(fe, fn, window=5)

        # Geometry config
        geometry = self._geometry.get_geometry()

        # Run analysis
        result = run_feathering_analysis(
            head_east=fe, head_north=fn,
            tail_east=te, tail_north=tn,
            vessel_cog=vessel_cog,
            shot_times=shot_times,
            ffids=ffids,
            n_channels=geometry.n_channels,
            rx_interval=geometry.rx_interval,
            feathering_alpha=geometry.feathering_alpha,
        )

        # Build config for corrected P190 export
        config = SurveyConfig(
            style="A",
            input_file="",
            line_name=input_vals.get("line_name", ""),
            output_dir=str(Path(output_path).parent),
            npd_file=npd_file,
            track_file=track_file,
            front_gps_source=front_gps,
            tail_gps_source=tail_gps,
            radex_coord_decimals=int(
                input_vals.get("radex_coord_decimals", 5)
            ),
            crs=self._crs.get_crs_config(),
            h_records=self._header.get_h_record_config(),
            geometry=geometry,
        )

        # Track data for corrected P190 receiver recalculation
        track_data_dict = {
            "head_east": fe,
            "head_north": fn,
            "tail_east": te,
            "tail_north": tn,
            "vessel_cog": vessel_cog,
            "shot_times": shot_times,
            "ffids": ffids,
        }

        # Source positions from original collection (if available)
        if self._collection and self._collection.n_shots == len(ffids):
            import numpy as np
            track_data_dict["source_x"] = np.array(
                [s.source_x for s in self._collection.shots])
            track_data_dict["source_y"] = np.array(
                [s.source_y for s in self._collection.shots])

        # Add time fields from track data
        if hasattr(track_data, 'df') and 'day' in track_data.df.columns:
            track_data_dict["day"] = track_data.df["day"].values
        if hasattr(track_data, 'df') and 'hour' in track_data.df.columns:
            track_data_dict["hour"] = track_data.df["hour"].values
        if hasattr(track_data, 'df') and 'minute' in track_data.df.columns:
            track_data_dict["minute"] = track_data.df["minute"].values
        if hasattr(track_data, 'df') and 'second' in track_data.df.columns:
            track_data_dict["second"] = track_data.df["second"].values

        # Update feathering panel
        out_dir = str(Path(output_path).parent)
        line_name = input_vals.get("line_name", "")
        self._feathering.set_analysis_result(
            result, out_dir, line_name,
            survey_config=config,
            track_data=track_data_dict,
        )

        # Auto-export report and plot
        from .engine.qc.feathering_analysis import generate_feathering_report
        report = generate_feathering_report(result)
        report_path = output_path.replace(".p190", "_Feathering_Report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        try:
            from .engine.qc.feathering_plot import generate_feathering_overview
            plot_path = output_path.replace(".p190", "_Feathering_Overview.png")
            generate_feathering_overview(result, plot_path, line_name=line_name)
            self._log.append("success",
                             f"Feathering overview: {plot_path}")
        except Exception as e:
            self._log.append("warning", f"Plot generation failed: {e}")

        s = result.stats
        self._log.append("success",
                         f"Feathering analysis: |mean|={s['feathering_abs_mean']:.2f} deg, "
                         f"current~{s['current_speed_mean_knots']:.2f}kn, "
                         f"correction~{s['correction_mean_all']:.3f}m")

    def _start_batch_conversion(self, input_vals: dict):
        """Start batch conversion in background thread."""
        style = input_vals.get("style", "B")
        batch_files = input_vals.get("batch_files", [])

        if not batch_files:
            self._log.append("error", "No batch files selected")
            return

        # Validate output directory
        output_dir = input_vals.get("output_dir", "")
        if not output_dir:
            self._log.append("error", "Output directory is required for batch mode")
            self._window.show_panel("input")
            return

        # Switch to log panel
        self._window.show_panel("log")

        self._converting = True
        self._start_time = time.time()
        self._update_status("Batch processing...", "warning")

        thread = threading.Thread(
            target=self._run_batch_conversion,
            args=(style, batch_files, input_vals),
            daemon=True,
        )
        thread.start()
        self._update_elapsed()

    def _run_batch_conversion(self, style: str, batch_files: list,
                              input_vals: dict):
        """Run batch conversion in background thread."""
        total = len(batch_files)
        succeeded = 0
        failed = 0
        errors = []

        self._thread_log("info",
                         f"Batch start: {total} {'files' if style == 'B' else 'pairs'}")

        for idx, item in enumerate(batch_files, 1):
            file_start = time.time()

            try:
                if style == "B":
                    file_path = item
                    fname = Path(file_path).stem
                    line_name = detect_line_name(file_path) or fname
                    self._thread_log("info",
                                     f"[{idx}/{total}] Processing: {fname} ...")

                    config = SurveyConfig(
                        style="B",
                        input_file=file_path,
                        line_name=line_name,
                        output_dir=input_vals.get("output_dir", ""),
                        crs=self._crs.get_crs_config(),
                        h_records=self._header.get_h_record_config(),
                        geometry=self._geometry.get_geometry(),
                        radex_coord_decimals=int(input_vals.get("radex_coord_decimals", 5)),
                    )
                    self._pipeline.run_style_b(config)

                else:  # Style A
                    npd_path, track_path = item
                    fname = Path(npd_path).stem
                    line_name = detect_line_name(npd_path) or fname
                    self._thread_log("info",
                                     f"[{idx}/{total}] Processing: {fname} ...")

                    config = SurveyConfig(
                        style="A",
                        input_file="",
                        line_name=line_name,
                        output_dir=input_vals.get("output_dir", ""),
                        npd_file=npd_path,
                        track_file=track_path,
                        front_gps_source=input_vals.get("front_gps", ""),
                        tail_gps_source=input_vals.get("tail_gps", ""),
                        crs=self._crs.get_crs_config(),
                        h_records=self._header.get_h_record_config(),
                        geometry=self._geometry.get_geometry(),
                        radex_coord_decimals=int(input_vals.get("radex_coord_decimals", 5)),
                    )
                    self._pipeline.run_style_a(config)

                elapsed_file = time.time() - file_start
                self._thread_log("success",
                                 f"[{idx}/{total}] {fname} Done ({elapsed_file:.1f}s)")
                succeeded += 1

            except Exception as exc:
                elapsed_file = time.time() - file_start
                fname = Path(item if isinstance(item, str) else item[0]).stem
                self._thread_log("error",
                                 f"[{idx}/{total}] {fname} FAILED ({elapsed_file:.1f}s): {exc}")
                failed += 1
                errors.append((fname, str(exc)))

        # Batch summary
        total_time = time.time() - self._start_time
        self._thread_log("info", "─" * 50)
        self._thread_log(
            "success" if failed == 0 else "warning",
            f"Batch complete: {succeeded}/{total} succeeded, "
            f"{failed} failed. Total: {total_time:.1f}s"
        )
        if errors:
            for fname, err in errors:
                self._thread_log("error", f"  Failed: {fname} — {err}")

        self._window.after(0, self._on_batch_done, succeeded, failed, total_time)

    def _on_batch_done(self, succeeded: int, failed: int, total_time: float):
        """Handle batch conversion completion on main thread."""
        self._converting = False
        if failed == 0:
            self._update_status("Batch Complete", "success")
        else:
            self._update_status(f"Batch: {failed} failed", "warning")
        self._window.status_bar.set_progress(1.0)

    def _update_status(self, text: str, color_key: str):
        """Update status bar."""
        from .gui.theme import COLORS
        self._window.status_bar.set_status(text, COLORS.get(color_key))

    def _update_elapsed(self):
        """Update elapsed time display while converting."""
        if self._converting and self._start_time:
            elapsed = time.time() - self._start_time
            mins, secs = divmod(int(elapsed), 60)
            self._window.status_bar.set_elapsed(f"{mins:02d}:{secs:02d}")
            self._window.after(1000, self._update_elapsed)

    def run(self):
        """Start the application main loop."""
        self._window.mainloop()


def main():
    """Application entry point."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
