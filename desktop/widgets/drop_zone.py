"""FileDropZone — Single-file drag-drop selector for P190 inputs."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSizePolicy,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius


class FileDropZone(QFrame):
    """Single-file drop zone with empty/loaded state."""

    file_selected = Signal(str)  # path

    def __init__(
        self,
        label: str = "Drop file here",
        extensions: str = "All Files (*)",
        parent=None,
    ):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._label_text = label
        self._extensions = extensions
        self._file_path = ""
        self._drag_over = False

        self._update_style()
        self._build_ui()

    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            Space.MD, Space.SM, Space.MD, Space.SM)
        self._layout.setSpacing(4)

        # Empty state
        self._empty_row = QHBoxLayout()
        self._empty_label = QLabel(self._label_text)
        self._empty_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.SM}px;
            background: transparent; border: none;
        """)
        self._empty_row.addWidget(self._empty_label, 1)

        self._browse_btn = QPushButton("Browse")
        self._browse_btn.setFixedSize(72, 28)
        self._browse_btn.setCursor(Qt.PointingHandCursor)
        self._browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Dark.NAVY};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                font-size: {Font.XS}px;
            }}
            QPushButton:hover {{
                border-color: {Dark.CYAN};
            }}
        """)
        self._browse_btn.clicked.connect(self._browse)
        self._empty_row.addWidget(self._browse_btn)
        self._layout.addLayout(self._empty_row)

        # Loaded state (hidden initially)
        self._loaded_row = QHBoxLayout()
        self._file_label = QLabel("")
        self._file_label.setStyleSheet(f"""
            color: {Dark.TEXT_BRIGHT};
            font-size: {Font.SM}px;
            background: transparent; border: none;
        """)
        self._loaded_row.addWidget(self._file_label, 1)

        self._size_label = QLabel("")
        self._size_label.setStyleSheet(f"""
            color: {Dark.MUTED};
            font-size: {Font.XS}px;
            background: transparent; border: none;
        """)
        self._loaded_row.addWidget(self._size_label)

        clear_btn = QPushButton("X")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Dark.MUTED};
                border: none;
                font-size: {Font.SM}px;
            }}
            QPushButton:hover {{ color: {Dark.TEXT}; }}
        """)
        clear_btn.clicked.connect(self._clear)
        self._loaded_row.addWidget(clear_btn)
        self._layout.addLayout(self._loaded_row)

        self._show_empty()

    def _show_empty(self):
        self._empty_label.show()
        self._browse_btn.show()
        self._file_label.hide()
        self._size_label.hide()

    def _show_loaded(self):
        self._empty_label.hide()
        self._browse_btn.hide()
        self._file_label.show()
        self._size_label.show()

    @property
    def value(self) -> str:
        return self._file_path

    @value.setter
    def value(self, path: str):
        if path and os.path.isfile(path):
            self._file_path = path
            self._file_label.setText(Path(path).name)
            sz = os.path.getsize(path)
            if sz > 1_048_576:
                self._size_label.setText(f"{sz / 1_048_576:.1f} MB")
            else:
                self._size_label.setText(f"{sz / 1024:.0f} KB")
            self._show_loaded()
        else:
            self._clear()

    def _clear(self):
        self._file_path = ""
        self._file_label.setText("")
        self._size_label.setText("")
        self._show_empty()

    def _update_style(self):
        if self._drag_over:
            self.setStyleSheet(f"""
                FileDropZone {{
                    background: {Dark.DARK};
                    border: 2px dashed {Dark.CYAN};
                    border-radius: {Radius.BASE}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                FileDropZone {{
                    background: {Dark.DARK};
                    border: 1px dashed {Dark.BORDER};
                    border-radius: {Radius.BASE}px;
                }}
                FileDropZone:hover {{
                    border-color: {Dark.MUTED};
                }}
            """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self._update_style()

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self._update_style()

    def dropEvent(self, event):
        self._drag_over = False
        self._update_style()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.value = path
                self.file_selected.emit(path)
                break

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", self._extensions)
        if path:
            self.value = path
            self.file_selected.emit(path)
