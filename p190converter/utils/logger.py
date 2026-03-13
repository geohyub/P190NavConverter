"""Thread-safe logging utility."""

import logging
import threading
from typing import Callable, Optional


class AppLogger:
    """Thread-safe logger with GUI callback support."""

    def __init__(self):
        self._lock = threading.Lock()
        self._callback: Optional[Callable[[str, str], None]] = None
        self._logger = logging.getLogger("p190converter")

    def set_callback(self, callback: Callable[[str, str], None]):
        with self._lock:
            self._callback = callback

    def log(self, level: str, message: str):
        with self._lock:
            if self._callback:
                self._callback(level, message)
            getattr(self._logger, level, self._logger.info)(message)

    def info(self, msg: str):
        self.log("info", msg)

    def success(self, msg: str):
        self.log("info", f"[OK] {msg}")

    def warning(self, msg: str):
        self.log("warning", msg)

    def error(self, msg: str):
        self.log("error", msg)
