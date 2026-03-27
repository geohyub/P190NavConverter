"""P190 NavConverter AppController — Central signal hub.

Decouples panels via Qt signals. 10-panel navigation
with Style A/B mode switching.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppController(QObject):
    """Central controller for panel navigation and app-wide state."""

    # Navigation signals (10 panels)
    navigate_input = Signal()
    navigate_header = Signal()
    navigate_crs = Signal()
    navigate_geometry = Signal()
    navigate_preview = Signal()
    navigate_log = Signal()
    navigate_results = Signal()
    navigate_feathering = Signal()
    navigate_comparison = Signal()
    navigate_help = Signal()

    # Style mode
    style_changed = Signal(str)           # "A" or "B"

    # File events
    file_loaded = Signal(str, str)        # file_type, path
    gps_sources_updated = Signal(list)    # source names

    # Conversion pipeline
    conversion_started = Signal()
    conversion_progress = Signal(float)   # 0.0-1.0
    conversion_step = Signal(int, str)    # step_index, state
    conversion_log = Signal(str, str)     # level, message
    conversion_done = Signal(str, str)    # output_path, report_path
    conversion_error = Signal(str, str)   # error, traceback

    # Profile management
    profile_saved = Signal(str)           # profile name
    profile_loaded = Signal(str)          # profile name
    profile_deleted = Signal(str)         # profile name

    # Toast notification
    toast_requested = Signal(str, str)    # message, level

    def __init__(self, parent=None):
        super().__init__(parent)

    def show_toast(self, message: str, level: str = "info"):
        self.toast_requested.emit(message, level)
