"""FileDropZone — DEPRECATED: Thin wrapper around geoview_pyside6.widgets.FileDropZone.

This file preserves the P190_NavConverter-specific API (``file_selected(str)`` signal
and ``.value`` property) while delegating all visual/DnD work to the shared widget.

All new code should use::

    from geoview_pyside6.widgets import FileDropZone
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy

from geoview_pyside6.widgets import FileDropZone as _SharedFileDropZone


def _exts_from_filter(filt: str) -> set[str] | None:
    """Extract extensions from a Qt file-dialog filter string."""
    import re
    exts: set[str] = set()
    for m in re.finditer(r'\*\.(\w+)', filt):
        exts.add(f".{m.group(1).lower()}")
    return exts or None


class FileDropZone(_SharedFileDropZone):
    """Backward-compatible single-file drop zone for P190_NavConverter.

    Adds:
    - ``file_selected(str)`` signal (emitted for first dropped file)
    - ``.value`` property (get/set selected file path)
    """

    file_selected = Signal(str)  # path — compat signal

    def __init__(
        self,
        label: str = "Drop file here",
        extensions: str = "All Files (*)",
        parent=None,
    ):
        exts = _exts_from_filter(extensions)
        super().__init__(
            accepted_extensions=exts,
            title=label,
            icon_name="upload",
            compact=True,
            min_size=100,
            parent=parent,
        )
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._file_path = ""

        # Bridge: shared files_dropped(list) -> local file_selected(str)
        self.files_dropped.connect(self._on_shared_dropped)

    def _on_shared_dropped(self, paths: list[str]):
        if paths:
            self._file_path = paths[0]
            self.file_selected.emit(paths[0])

    @property
    def value(self) -> str:
        return self._file_path

    @value.setter
    def value(self, path: str):
        if path and os.path.isfile(path):
            self._file_path = path
        else:
            self._file_path = ""
