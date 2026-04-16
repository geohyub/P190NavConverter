from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SHARED = ROOT.parents[1] / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from PySide6.QtWidgets import QApplication


class _StubLanguage:
    current_language = "en"

    def text(self, key: str) -> str:
        values = {
            "compare.panel_title": "Compare",
            "compare.files_card": "P190 Files to Compare",
            "compare.file_a": "Style A P190",
            "compare.file_b": "Style B P190",
            "compare.browse": "Browse",
            "compare.compare_button": "Compare",
            "compare.stat_grade": "Grade",
            "compare.stat_src_diff": "Src Mean Diff",
            "compare.stat_rx_diff": "Rx Mean Diff",
            "compare.stat_matched": "Matched Shots",
            "compare.overlay_card": "Selected Shot Overlay",
            "compare.meaning_card": "Comparison Meaning",
            "compare.channel_card": "Receiver Channel Summary",
            "compare.worst_card": "Largest Shot Differences",
            "compare.detail_card": "Selected Shot Details",
            "compare.sync_card": "Synchronized Style Workspace",
            "compare.evidence_card": "Linked Evidence Review",
            "compare.evidence_a": "Style A Evidence",
            "compare.evidence_b": "Style B Evidence",
            "compare.open_selected": "Open Selected",
            "compare.channel_profile_card": "Selected Shot Receiver Delta Profile",
            "compare.quick_first": "First",
            "compare.quick_middle": "Middle",
            "compare.quick_worst": "Worst",
            "compare.quick_last": "Last",
            "compare.export_report": "Export Report",
            "compare.export_plot": "Export Plot",
            "compare.export_manifest": "Export Manifest",
            "compare.idle_insight": "Idle insight",
            "compare.overlay_idle": "Overlay idle",
            "compare.meaning_idle": "Meaning idle",
            "compare.channel_idle": "Channel idle",
            "compare.worst_idle": "Worst idle",
            "compare.detail_idle": "Detail idle",
            "compare.sync_idle": "Sync idle",
            "compare.evidence_idle": "Evidence idle",
            "compare.channel_profile_idle": "Profile idle",
        }
        return values[key]


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_comparison_panel_language_refresh_updates_drop_zone_labels():
    _qapp()

    from desktop.panels.comparison_panel import ComparisonPanel

    panel = ComparisonPanel(controller=object())
    try:
        panel.set_language_service(_StubLanguage())

        assert panel._file_a._title_label.text() == "Style A P190"
        assert panel._file_b._title_label.text() == "Style B P190"
        assert panel._file_a._browse_btn.text() == "Browse"
        assert panel._compare_btn.text() == "Compare"
    finally:
        panel.close()
