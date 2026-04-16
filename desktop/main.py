"""P190 NavConverter Desktop v2.0 — PySide6 Edition.

Run: python -m desktop       (from P190_NavConverter/)
     python desktop/main.py  (direct)
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

# -- Path setup --
_P190_ROOT = str(Path(__file__).resolve().parents[1])
_SHARED_ROOT = str(Path(__file__).resolve().parents[3] / "_shared")

if _P190_ROOT not in sys.path:
    sys.path.insert(0, _P190_ROOT)
if _SHARED_ROOT not in sys.path:
    sys.path.insert(0, _SHARED_ROOT)

from PySide6.QtCore import QThread, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from geoview_pyside6 import GeoViewApp, Category
from geoview_pyside6.constants import Dark
from geoview_pyside6.icons import icon
from geoview_pyside6.help import set_help

from desktop.app_controller import AppController
from desktop.widgets.toast import ToastManager
from desktop.services.conversion_service import ConversionWorker
from desktop.services.settings_service import SettingsService
from desktop.services.explanation_service import SOURCE_POSITION_DESCRIPTIONS
from desktop.services.language_service import LanguageService

from desktop.panels.input_panel import InputPanel
from desktop.panels.header_panel import HeaderPanel
from desktop.panels.crs_panel import CRSPanel
from desktop.panels.geometry_panel import GeometryPanel
from desktop.panels.preview_panel import PreviewPanel
from desktop.panels.log_panel import LogPanel
from desktop.panels.results_panel import ResultsPanel
from desktop.panels.feathering_panel import FeatheringPanel
from desktop.panels.comparison_panel import ComparisonPanel
from desktop.panels.help_panel import HelpPanel

# Panels that require Style A
STYLE_A_ONLY = {"geometry", "feathering"}
PANEL_LABEL_KEYS = {
    "input": "sidebar.input",
    "header": "sidebar.header",
    "crs": "sidebar.crs",
    "geometry": "sidebar.geometry",
    "preview": "sidebar.preview",
    "log": "sidebar.log",
    "results": "sidebar.results",
    "feathering": "sidebar.feathering",
    "comparison": "sidebar.comparison",
    "help": "sidebar.help",
}


class P190App(GeoViewApp):
    """P190 NavConverter Desktop v2.0"""

    APP_NAME = "P190 NavConverter"
    APP_VERSION = "v2.0"
    CATEGORY = Category.PREPROCESSING

    def __init__(self):
        self.controller = AppController()
        self._session_settings = SettingsService()
        self._language = LanguageService(self._session_settings.load_ui_language())
        super().__init__()

        self._comparison.set_language_service(self._language)
        self._lang_btn = self.top_bar.add_action_button(
            self._language.text("top.language_button"),
            self._toggle_language,
        )
        set_help(self._lang_btn, "Toggle Korean / English")
        self._language.language_changed.connect(self._on_language_changed)

        self.toast_mgr = ToastManager(self.content_stack)
        self.controller.toast_requested.connect(self.toast_mgr.show_toast)

        self._current_style = "B"
        self._collection = None
        self._latest_collection = None
        self._converting = False
        self._start_time = None
        self._worker = None
        self._worker_thread = None
        self._recent_outputs = {"A": "", "B": ""}
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        self._connect_navigation()
        self._connect_conversion()
        self._setup_shortcuts()
        self._load_saved_settings()
        self._on_language_changed(self._language.current_language)

    # ------------------------------------------------------------------ #
    #  Panel Setup (called by GeoViewApp.__init__)
    # ------------------------------------------------------------------ #

    def setup_panels(self):
        """Register 10 panels: 5 pre-conversion + 5 post-conversion."""
        # -- Pre-conversion (workflow order) --
        self._input = InputPanel(self.controller)
        self.add_panel("input", icon("upload"), "\uc785\ub825", self._input)

        self._header = HeaderPanel()
        self.add_panel("header", icon("file-text"), "\ud5e4\ub354", self._header)

        self._crs = CRSPanel(self.controller)
        self.add_panel("crs", icon("globe"), "\uc88c\ud45c\uacc4", self._crs)

        self._geometry = GeometryPanel(self.controller)
        self.add_panel("geometry", icon("layers"), "Geometry", self._geometry)

        self._preview = PreviewPanel()
        self.add_panel("preview", icon("eye"), "\ubbf8\ub9ac\ubcf4\uae30", self._preview)

        self.add_sidebar_separator("\ucd9c\ub825")

        # -- Post-conversion --
        self._log = LogPanel()
        self.add_panel("log", icon("terminal"), "\ub85c\uadf8", self._log)

        self._results = ResultsPanel()
        self.add_panel("results", icon("star"), "\uacb0\uacfc", self._results)

        self._feathering = FeatheringPanel()
        self.add_panel("feathering", icon("waves"), "Feathering", self._feathering)

        self._comparison = ComparisonPanel(self.controller)
        self.add_panel("comparison", icon("arrow-left-right"), "\ube44\uad50", self._comparison)

        self._help = HelpPanel()
        self.add_panel("help", icon("info"), "\ub3c4\uc6c0\ub9d0", self._help)

    # ------------------------------------------------------------------ #
    #  Navigation
    # ------------------------------------------------------------------ #

    def _connect_navigation(self):
        c = self.controller
        c.navigate_input.connect(lambda: self._switch_to("input"))
        c.navigate_header.connect(lambda: self._switch_to("header"))
        c.navigate_crs.connect(lambda: self._switch_to("crs"))
        c.navigate_geometry.connect(lambda: self._switch_to("geometry"))
        c.navigate_preview.connect(lambda: self._switch_to("preview"))
        c.navigate_log.connect(lambda: self._switch_to("log"))
        c.navigate_results.connect(lambda: self._switch_to("results"))
        c.navigate_feathering.connect(lambda: self._switch_to("feathering"))
        c.navigate_comparison.connect(lambda: self._switch_to("comparison"))
        c.navigate_help.connect(lambda: self._switch_to("help"))
        self._results.request_compare.connect(self._open_recent_comparison)

        # Style change → enable/disable Style A panels
        c.style_changed.connect(self._on_style_changed)

        # File loading → parse and update panels
        self._input.file_loaded.connect(self._on_file_loaded)

        # CRS change → auto-update H Records
        self._crs.crs_changed.connect(self._on_crs_changed)

        # Profile management
        c.profile_saved.connect(self._save_profile)
        c.profile_loaded.connect(self._load_profile)
        c.profile_deleted.connect(self._delete_profile)

    def _switch_to(self, panel_id: str):
        # Block navigation to disabled panels
        if panel_id in STYLE_A_ONLY and self._current_style != "A":
            self.controller.show_toast(
                "Style A (NPD + Geometry) \uc804\uc6a9\uc785\ub2c8\ub2e4", "warning")
            return
        self.sidebar.set_active_panel(panel_id)

    def _on_style_changed(self, style: str):
        self._current_style = style
        # Enable/disable sidebar buttons for Style A panels
        for btn in self.sidebar.buttons:
            if btn.panel_id in STYLE_A_ONLY:
                btn.setEnabled(style == "A")
                btn.setToolTip(
                    "" if style == "A" else "Style A only (NPD + Geometry)")

        # Redirect if currently on a disabled panel
        current = self.content_stack.currentWidget()
        for pid in STYLE_A_ONLY:
            if current == self._panels.get(pid) and style != "A":
                self._switch_to("input")
                break

        self._log.append("info", f"\ubcc0\ud658 \ubc29\uc2dd: Style {style}")

    def _toggle_language(self):
        self._language.toggle()

    def _on_language_changed(self, language: str):
        try:
            self._session_settings.save_ui_language(language)
        except Exception:
            pass

        self._lang_btn.setText(self._language.text("top.language_button"))
        for btn in self.sidebar.buttons:
            key = PANEL_LABEL_KEYS.get(btn.panel_id)
            if key:
                btn.setText(self._language.text(key))

        for panel_id, panel in self._panels.items():
            key = PANEL_LABEL_KEYS.get(panel_id)
            if key:
                panel.panel_title = self._language.text(key)

        self._comparison.apply_language()
        if self._current_panel and self._current_panel in self._panels:
            self.top_bar.set_title(self._panels[self._current_panel].panel_title)

    def _open_recent_comparison(self):
        style_a = self._recent_outputs.get("A", "")
        style_b = self._recent_outputs.get("B", "")
        if not style_a or not style_b:
            self.controller.show_toast(
                "Need both recent Style A and Style B outputs to compare",
                "warning",
            )
            return
        if not Path(style_a).exists() or not Path(style_b).exists():
            self.controller.show_toast(
                "Recent comparison outputs are missing on disk",
                "warning",
            )
            return

        self._switch_to("comparison")
        self._comparison.compare_paths(style_a, style_b)

    # ------------------------------------------------------------------ #
    #  File Loading & Parsing
    # ------------------------------------------------------------------ #

    def _on_file_loaded(self, file_type: str, path: str):
        """Parse file and update relevant panels."""
        if file_type == "radex":
            self._load_radex_file(path)
        elif file_type == "npd":
            self._load_npd_file(path)
        elif file_type == "track":
            self._load_track_file(path)

        # Auto-detect line name
        if not self._input.get_line_name():
            from p190converter.utils.line_name import detect_line_name
            detected = detect_line_name(path)
            if detected:
                self._input.set_line_name(detected)
                self._preview.set_line_name(detected)
                self._log.append("info", f"Line name auto-detected: {detected}")

    def _load_radex_file(self, path: str):
        try:
            self._log.append("info", f"Loading: {Path(path).name}")
            from p190converter.engine.parsers.radex_parser import parse_radex_export
            self._collection = parse_radex_export(path)
            n = self._collection.n_shots
            ch = self._collection.n_channels
            ffid_lo, ffid_hi = self._collection.ffid_range

            self._input.update_summary(
                f"Shots: {n:,}  |  Channels: {ch}  |  "
                f"FFID: {ffid_lo}-{ffid_hi}")
            self._log.append("success", f"Parsed: {n:,} shots, {ch} channels")
            self.top_bar.set_title(
                f"P190 NavConverter - {Path(path).name}")

            # Update preview
            self._preview.set_collection(self._collection)
        except Exception as exc:
            self._log.append("error", f"Parse error: {exc}")
            self._input.update_summary(f"Error: {exc}")

    def _load_npd_file(self, path: str):
        try:
            self._log.append("info", f"Loading NPD: {Path(path).name}")
            from p190converter.engine.parsers.npd_parser import parse_npd_sources
            sources = parse_npd_sources(path)
            self._input.update_gps_sources(sources)
            self._log.append(
                "success", f"NPD sources: {', '.join(sources)}")
            self.top_bar.set_title(
                f"P190 NavConverter - {Path(path).name}")

            # Auto-select defaults: Head_Buoy / Tail_Buoy
            front_default = ""
            tail_default = ""
            for s in sources:
                sl = s.lower()
                if "head" in sl or "front" in sl:
                    front_default = front_default or s
                if "tail" in sl:
                    tail_default = tail_default or s
            if front_default or tail_default:
                self._input.set_selected_gps_sources(
                    front_default, tail_default)
        except Exception as exc:
            self._log.append("error", f"NPD load error: {exc}")
            # Fallback defaults
            self._input.update_gps_sources(["Head_Buoy", "Tail_Buoy"])
            self._input.set_selected_gps_sources(
                "Head_Buoy", "Tail_Buoy")

    def _load_track_file(self, path: str):
        try:
            self._log.append("info", f"Loading Track: {Path(path).name}")
            from p190converter.engine.parsers.track_parser import parse_track_file
            track_data = parse_track_file(path)

            n = track_data.n_shots
            ch = track_data.n_channels
            ffid_lo, ffid_hi = track_data.ffid_range

            self._input.update_summary(
                f"Shots: {n:,}  |  Channels: {ch if ch > 0 else '--'}  |  "
                f"FFID: {ffid_lo}-{ffid_hi}")
            if ch > 0:
                self._geometry.set_channel_count(ch)
            self._log.append(
                "success",
                f"Track: {n:,} shots, {ch if ch > 0 else '--'} ch, "
                f"FFID {ffid_lo}-{ffid_hi}")

            self._preview.set_track_data(
                track_data,
                self._input.get_line_name() or Path(path).stem,
            )

            for warn_msg in track_data.warnings:
                self._log.append("warning", warn_msg)

            self.top_bar.set_title(
                f"P190 NavConverter - {Path(path).name}")
        except Exception as exc:
            self._log.append("error", f"Track load error: {exc}")

    def _on_crs_changed(self, crs_config):
        """CRS change → auto-update H Record fields."""
        self._header.apply_crs_to_records(crs_config)
        if crs_config.display_name:
            label = f"{crs_config.display_name} (EPSG:{crs_config.epsg_code})"
        elif hasattr(crs_config, 'is_utm') and crs_config.is_utm:
            label = (f"UTM {crs_config.utm_zone}"
                     f"{crs_config.hemisphere} (EPSG:{crs_config.epsg_code})")
        else:
            label = f"EPSG:{crs_config.epsg_code}"
        self._log.append("info", f"CRS updated: {label}")

    # ------------------------------------------------------------------ #
    #  Conversion Pipeline
    # ------------------------------------------------------------------ #

    def _connect_conversion(self):
        c = self.controller
        c.conversion_log.connect(self._log.append)
        c.conversion_step.connect(self._on_conversion_step)
        c.conversion_done.connect(self._on_conversion_done)
        c.conversion_error.connect(self._on_conversion_error)

    def start_conversion(self):
        """Gather config from panels and start conversion."""
        if self._converting:
            self.controller.show_toast("\ubcc0\ud658 \uc9c4\ud589\uc911", "warning")
            return

        # Gather config
        input_vals = self._input.get_config_values()
        style = input_vals.get("style", "B")

        # Batch mode redirect
        if input_vals.get("batch_mode"):
            return self._start_batch_conversion(input_vals)

        # Validate
        if style == "B" and not input_vals.get("input_file"):
            self.controller.show_toast(
                "RadExPro \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694", "error")
            self._switch_to("input")
            return
        if style == "A":
            if not input_vals.get("npd_file"):
                self.controller.show_toast("NPD \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694", "error")
                self._switch_to("input")
                return
            if not input_vals.get("track_file"):
                self.controller.show_toast("Track \ud30c\uc77c\uc744 \uc120\ud0dd\ud558\uc138\uc694", "error")
                self._switch_to("input")
                return
        if not input_vals.get("line_name"):
            self.controller.show_toast("\ub77c\uc778\uba85\uc744 \uc785\ub825\ud558\uc138\uc694", "error")
            return

        # Build SurveyConfig
        from p190converter.models.survey_config import SurveyConfig

        try:
            radex_decimals = int(
                input_vals.get("radex_coord_decimals", 5))
        except (TypeError, ValueError):
            radex_decimals = 5

        config = SurveyConfig(
            style=style,
            input_file=input_vals.get("input_file", ""),
            line_name=input_vals.get("line_name", "Unknown"),
            output_dir=input_vals.get("output_dir", ""),
            npd_file=input_vals.get("npd_file", ""),
            track_file=input_vals.get("track_file", ""),
            front_gps_source=input_vals.get("front_gps", ""),
            tail_gps_source=input_vals.get("tail_gps", ""),
            source_position_mode=input_vals.get(
                "source_position_mode", "front_gps"),
            radex_coord_decimals=radex_decimals,
            crs=self._crs.get_crs_config(),
            h_records=self._header.get_h_record_config(),
            geometry=self._geometry.get_geometry(),
        )

        # Switch to log panel, show step indicator
        self._switch_to("log")
        self._log.clear()
        self._log.show_step_indicator()

        # Start worker thread
        self._converting = True
        self._start_time = time.time()

        self._cleanup_worker()
        self._worker_thread = QThread()
        self._worker = ConversionWorker(config, self.controller)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker.preview_ready.connect(self._on_preview_ready)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

        self._elapsed_timer.start()

    def _cleanup_worker(self):
        """Disconnect and clean up previous worker before creating a new one."""
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait(3000)
        if self._worker:
            try:
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
                self._worker.preview_ready.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._worker.deleteLater()
            self._worker = None
        if self._worker_thread:
            try:
                self._worker_thread.started.disconnect()
                self._worker_thread.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._worker_thread = None

    def _on_conversion_step(self, index: int, state: str):
        """Update step indicator in log panel."""
        self._log.set_step(index, state)
        labels = ["Parsing", "Transforming", "Writing",
                  "Validating", "QC Check"]
        if state == "active" and 0 <= index < len(labels):
            self.top_bar.set_title(
                f"P190 NavConverter - {labels[index]}...")

    def _on_conversion_done(self, output_path: str, report_path: str):
        self._converting = False
        self._elapsed_timer.stop()
        elapsed = time.time() - self._start_time

        self.top_bar.set_title("P190 NavConverter")
        self._log.hide_step_indicator()
        self.controller.show_toast(
            f"\ubcc0\ud658 \uc644\ub8cc ({elapsed:.1f}\ucd08)", "success")

        # Update results panel
        input_vals = self._input.get_config_values()
        style = input_vals.get("style", "B")
        self._results.set_context(
            style=style,
            source_position_mode=input_vals.get(
                "source_position_mode", "front_gps"),
            radex_coord_decimals=input_vals.get("radex_coord_decimals", 5),
            warnings=self._log.get_messages("warning"),
            elapsed_seconds=elapsed,
        )
        self._results.set_output(output_path, report_path)
        if self._latest_collection:
            self._results.set_collection(self._latest_collection)
        self._recent_outputs[style] = output_path
        self._comparison.set_file_paths(
            style_a=self._recent_outputs.get("A", ""),
            style_b=self._recent_outputs.get("B", ""),
        )

        # QC validation
        try:
            from p190converter.engine.qc.validator import validate_p190
            qc = validate_p190(output_path)
            self._results.set_qc_result(qc)
        except Exception as e:
            self._log.append("warning", f"QC validation skipped: {e}")

        self._switch_to("results")

        # Auto-run feathering analysis for Style A (in background thread)
        if input_vals.get("style") == "A":
            self._start_feathering_worker(output_path, input_vals)

        # Save config for next session
        try:
            self._session_settings.save_session(
                input_vals, self._crs.get_crs_config(),
                self._geometry.get_geometry(),
                self._header.get_h_record_config())
        except Exception:
            pass

    def _on_preview_ready(self, collection, context: dict):
        """Update preview/results with the final exported collection."""
        if not collection:
            return

        self._latest_collection = collection
        line_name = context.get("line_name", "")
        if line_name:
            self._preview.set_line_name(line_name)

        style = context.get("style", "B")
        note = context.get("note", "")
        if style == "A":
            input_vals = self._input.get_config_values()
            source_mode = input_vals.get("source_position_mode", "front_gps")
            source_desc = SOURCE_POSITION_DESCRIPTIONS.get(
                source_mode, SOURCE_POSITION_DESCRIPTIONS["front_gps"]
            )
            note = (
                f"{note} Active source basis: {source_desc}"
            )

        self._preview.set_collection(
            collection,
            preview_mode=context.get("preview_mode", "converted_geometry"),
            note=note,
            warnings=context.get("warnings", []),
        )
        self._results.set_collection(collection)

    def _on_conversion_error(self, error: str, tb: str):
        self._converting = False
        self._elapsed_timer.stop()
        self.top_bar.set_title("P190 NavConverter")
        self._log.hide_step_indicator()
        self.controller.show_toast(f"\ubcc0\ud658 \uc2e4\ud328: {error}", "error")

    def _start_feathering_worker(self, output_path: str, input_vals: dict):
        """Launch feathering analysis in a background thread."""
        npd_file = input_vals.get("npd_file", "")
        track_file = input_vals.get("track_file", "")
        if not npd_file or not track_file:
            return

        self._log.append("info", "Feathering analysis starting...")

        from desktop.services.conversion_service import FeatheringWorker
        geometry = self._geometry.get_geometry()

        self._feath_thread = QThread()
        self._feath_worker = FeatheringWorker(
            npd_file, track_file,
            input_vals.get("front_gps", "Head_Buoy"),
            input_vals.get("tail_gps", "Tail_Buoy"),
            geometry, output_path,
            input_vals.get("line_name", ""))
        self._feath_worker.moveToThread(self._feath_thread)
        self._feath_thread.started.connect(self._feath_worker.run)
        self._feath_worker.done.connect(self._on_feathering_done)
        self._feath_worker.error.connect(self._on_feathering_error)
        self._feath_worker.done.connect(self._feath_thread.quit)
        self._feath_worker.error.connect(self._feath_thread.quit)
        self._feath_thread.finished.connect(self._feath_thread.deleteLater)
        self._feath_thread.start()

    def _on_feathering_done(self, result, line_name: str,
                            output_path: str, report_path: str,
                            plot_path: str):
        """Handle feathering results on UI thread."""
        self._feathering.set_analysis_result(
            result, str(Path(output_path).parent), line_name)

        s = result.stats
        self._log.append(
            "success",
            f"Feathering: |mean|={s['feathering_abs_mean']:.2f} deg, "
            f"current~{s['current_speed_mean_knots']:.2f}kn, "
            f"correction~{s['correction_mean_all']:.3f}m")

        if plot_path:
            self._log.append("success", f"Feathering overview: {plot_path}")

    def _on_feathering_error(self, msg: str):
        self._log.append("warning", f"Feathering analysis skipped: {msg}")

    def _start_batch_conversion(self, input_vals: dict):
        """Start batch conversion in background thread."""
        style = input_vals.get("style", "B")
        batch_files = input_vals.get("batch_files", [])
        output_dir = input_vals.get("output_dir", "")

        if not batch_files:
            self.controller.show_toast("\uc77c\uad04 \ucc98\ub9ac\ud560 \ud30c\uc77c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4", "error")
            return
        if not output_dir:
            self.controller.show_toast(
                "\ucd9c\ub825 \uacbd\ub85c\ub97c \uc9c0\uc815\ud558\uc138\uc694", "error")
            return

        self._switch_to("log")
        self._log.clear()
        self._converting = True
        self._start_time = time.time()
        self._elapsed_timer.start()

        from desktop.services.conversion_service import BatchConversionWorker
        self._cleanup_worker()
        self._worker_thread = QThread()
        self._worker = BatchConversionWorker(
            style, batch_files, input_vals,
            self._crs.get_crs_config(),
            self._geometry.get_geometry(),
            self._header.get_h_record_config(),
            self.controller)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._on_batch_done)
        self._worker_thread.finished.connect(
            self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _on_batch_done(self, succeeded: int, failed: int):
        self._converting = False
        self._elapsed_timer.stop()
        elapsed = time.time() - self._start_time
        total = succeeded + failed
        self.top_bar.set_title("P190 NavConverter")
        if failed == 0:
            self.controller.show_toast(
                f"Batch complete: {succeeded}/{total} "
                f"({elapsed:.1f}s)", "success")
        else:
            self.controller.show_toast(
                f"Batch: {succeeded} OK, {failed} failed "
                f"({elapsed:.1f}s)", "warning")

    def _update_elapsed(self):
        if self._converting and self._start_time:
            elapsed = time.time() - self._start_time
            mins, secs = divmod(int(elapsed), 60)
            self.top_bar.set_title(
                f"P190 NavConverter - Converting {mins:02d}:{secs:02d}")

    # ------------------------------------------------------------------ #
    #  Settings Persistence
    # ------------------------------------------------------------------ #

    def _load_saved_settings(self):
        # Refresh profile list
        self._input.refresh_profiles()

        saved = self._session_settings.load_session()
        if not saved:
            return
        try:
            self._input.restore_config(saved)
            if saved.get("crs"):
                self._crs.set_crs_config(saved["crs"])
            if saved.get("geometry"):
                self._geometry.set_geometry(saved["geometry"])
            if saved.get("h_records"):
                self._header.set_h_records(saved["h_records"])

            # Re-parse files to populate GPS sources and preview
            files = saved.get("files", {})
            style = saved.get("style", "B")
            if style == "A":
                if files.get("npd_file"):
                    self._load_npd_file(files["npd_file"])
                if files.get("track_file"):
                    self._load_track_file(files["track_file"])
                # Restore GPS source selection after parsing
                gps = saved.get("gps_sources", {})
                if gps:
                    self._input.set_selected_gps_sources(
                        gps.get("front", ""),
                        gps.get("tail", ""))
            elif files.get("input_file"):
                self._load_radex_file(files["input_file"])
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
            "gps_sources": {
                "front": input_vals.get("front_gps", ""),
                "tail": input_vals.get("tail_gps", ""),
            },
            "source_position_mode": input_vals.get(
                "source_position_mode", "front_gps"),
            "export_options": {
                "radex_coord_decimals": input_vals.get(
                    "radex_coord_decimals", "5"),
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

        self._session_settings.save_profile(name, data)
        self._input.refresh_profiles()
        self.controller.show_toast(f"Profile '{name}' saved", "success")
        self._log.append("success", f"Profile '{name}' saved")

    def _load_profile(self, name: str):
        """Load a named profile and restore all panels."""
        data = self._session_settings.load_profile(name)
        if not data:
            self.controller.show_toast(
                f"Profile '{name}' not found", "error")
            return
        self._input.restore_config(data)
        if data.get("crs"):
            self._crs.set_crs_config(data["crs"])
        if data.get("geometry"):
            self._geometry.set_geometry(data["geometry"])
        if data.get("h_records"):
            self._header.set_h_records(data["h_records"])
        self.controller.show_toast(f"Profile '{name}' loaded", "success")
        self._log.append("success", f"Profile '{name}' loaded")

    def _delete_profile(self, name: str):
        """Delete a named profile."""
        if self._session_settings.delete_profile(name):
            self._input.refresh_profiles()
            self.controller.show_toast(
                f"Profile '{name}' deleted", "success")
            self._log.append("info", f"Profile '{name}' deleted")
        else:
            self.controller.show_toast(
                f"Profile '{name}' not found", "error")

    # ------------------------------------------------------------------ #
    #  TopBar Actions
    # ------------------------------------------------------------------ #

    def _switch_panel(self, panel_id: str):
        super()._switch_panel(panel_id)

        # Clear top bar actions
        while self.top_bar.actions_layout.count():
            item = self.top_bar.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if panel_id == "input":
            self.top_bar.set_title("P190 NavConverter")
            btn = self.top_bar.add_action_button(
                "\ubcc0\ud658", self.start_conversion, primary=True)
            set_help(btn, "Start P190 conversion (Ctrl+Enter)")

        elif panel_id in ("header", "crs", "geometry", "preview"):
            btn = self.top_bar.add_action_button(
                "\ubcc0\ud658", self.start_conversion, primary=True)
            set_help(btn, "Start P190 conversion (Ctrl+Enter)")

        elif panel_id == "results":
            btn = self.top_bar.add_action_button(
                "\uc0c8 \ubcc0\ud658",
                lambda: self._switch_to("input"))
            set_help(btn, "Start a new conversion")

    # ------------------------------------------------------------------ #
    #  Shortcuts
    # ------------------------------------------------------------------ #

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self.start_conversion)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)

    def _on_escape(self):
        current = self.content_stack.currentWidget()
        # From post-conversion panels → go to input
        post_panels = (self._log, self._results,
                       self._feathering, self._comparison)
        if current in post_panels:
            self._switch_to("input")


def main():
    P190App.run()


if __name__ == "__main__":
    main()
