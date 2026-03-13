"""Log panel — Real-time execution log display with timeline."""

import customtkinter as ctk
from datetime import datetime

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard, MiniProgressTimeline


# Tag -> color mapping for log levels
LOG_COLORS = {
    "info":    COLORS["accent"],
    "success": COLORS["success"],
    "warning": COLORS["warning"],
    "error":   COLORS["error"],
}


class LogPanel(ctk.CTkFrame):
    """Panel for real-time conversion log display with event timeline."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._build()

    def _build(self):
        # ── Controls ──
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=(0, SP["sm"]))

        ctk.CTkLabel(
            ctrl_frame, text="Execution Log",
            font=font("h3", bold=True),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            ctrl_frame, text="Clear", width=70,
            font=font("small"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self.clear,
        )
        clear_btn.pack(side="right")

        export_btn = ctk.CTkButton(
            ctrl_frame, text="Export", width=70,
            font=font("small"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self._export_log,
        )
        export_btn.pack(side="right", padx=(0, SP["xs"]))

        # ── Event Timeline (top 1/3) ──
        self._timeline = MiniProgressTimeline(self)
        self._timeline.pack(fill="x", pady=(0, SP["sm"]))

        # ── Log Text Area (bottom 2/3) ──
        self._textbox = ctk.CTkTextbox(
            self,
            font=mono_font(),
            fg_color=COLORS["bg_elevated"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            wrap="word",
            state="disabled",
        )
        self._textbox.pack(fill="both", expand=True)

        # Configure color tags
        for tag, color in LOG_COLORS.items():
            self._textbox._textbox.tag_configure(tag, foreground=color)

        # Initial message
        self.append("info", "P190 NavConverter ready.")

    def append(self, level: str, message: str):
        """Append a log message with level coloring.

        Args:
            level: 'info' | 'success' | 'warning' | 'error'
            message: Log message text
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "info": "INFO",
            "success": " OK ",
            "warning": "WARN",
            "error": " ERR",
        }.get(level, "INFO")

        line = f"[{timestamp}] [{prefix}] {message}\n"

        self._textbox.configure(state="normal")
        self._textbox._textbox.insert("end", line, level)
        self._textbox.configure(state="disabled")
        self._textbox._textbox.see("end")

        # Also add key events to timeline
        if level in ("success", "error", "warning"):
            self._timeline.append(level, message, timestamp)

    def clear(self):
        """Clear all log messages."""
        self._textbox.configure(state="normal")
        self._textbox._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
        self._timeline.clear()
        self.append("info", "Log cleared.")

    def _export_log(self):
        """Export log to file."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Export Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
        )
        if path:
            content = self._textbox._textbox.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.append("info", f"Log exported: {path}")
