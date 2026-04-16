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


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_p190_app_boots_with_session_settings_service_intact():
    _qapp()

    from desktop.main import P190App
    from desktop.services.settings_service import SettingsService

    window = P190App()
    try:
        assert isinstance(window._session_settings, SettingsService)
        assert window._language is not None
    finally:
        window.close()
