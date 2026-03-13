"""Reusable CustomTkinter widgets."""

import math
import os
import tkinter as tk
from datetime import datetime

import customtkinter as ctk
from .theme import (
    COLORS, SP, CORNER_RADIUS, font, mono_font,
    STEP_COLORS, STEP_LABELS, STAT_ACCENTS, GEOM_COLORS,
)


class SectionCard(ctk.CTkFrame):
    """Elevated card with optional title."""

    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_elevated"],
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        if title:
            lbl = ctk.CTkLabel(
                self, text=title,
                font=font("h3", bold=True),
                text_color=COLORS["text_primary"],
                anchor="w",
            )
            lbl.pack(
                fill="x",
                padx=SP["md"], pady=(SP["md"], SP["sm"]),
            )


class FormField(ctk.CTkFrame):
    """Label + Entry row."""

    def __init__(self, parent, label: str, default: str = "",
                 width: int = 250, browse: bool = False,
                 browse_callback=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(
            self, text=label,
            font=font("body"),
            text_color=COLORS["text_secondary"],
            width=120, anchor="e",
        )
        self._label.pack(side="left", padx=(0, SP["sm"]))

        self._entry = ctk.CTkEntry(
            self,
            width=width,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        if default:
            self._entry.insert(0, default)
        self._entry.pack(side="left", fill="x", expand=True)

        if browse and browse_callback:
            btn = ctk.CTkButton(
                self, text="...", width=36, height=28,
                font=font("body"),
                fg_color=COLORS["bg_input"],
                hover_color=COLORS["sidebar_hover"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=6,
                command=browse_callback,
            )
            btn.pack(side="left", padx=(SP["xs"], 0))

    @property
    def value(self) -> str:
        return self._entry.get()

    @value.setter
    def value(self, v: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, v)

    def bind_change(self, callback):
        self._entry.bind("<FocusOut>", lambda e: callback())
        self._entry.bind("<Return>", lambda e: callback())


class StatusBar(ctk.CTkFrame):
    """Bottom status bar with status indicator + progress + elapsed time."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_secondary"],
            height=32,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)

        self._status_dot = ctk.CTkLabel(
            self, text="\u25cf", width=20,
            font=font("body"),
            text_color=COLORS["success"],
        )
        self._status_dot.pack(side="left", padx=(SP["md"], 0))

        self._status_text = ctk.CTkLabel(
            self, text="Ready",
            font=font("small"),
            text_color=COLORS["text_secondary"],
        )
        self._status_text.pack(side="left", padx=(SP["xs"], SP["md"]))

        self._progress = ctk.CTkProgressBar(
            self, width=200, height=8,
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent"],
            corner_radius=4,
        )
        self._progress.set(0)
        self._progress.pack(side="left", padx=SP["sm"])

        self._percent = ctk.CTkLabel(
            self, text="0%",
            font=font("small"),
            text_color=COLORS["text_muted"],
            width=40,
        )
        self._percent.pack(side="left")

        # Step label (shows current pipeline stage)
        self._step_label = ctk.CTkLabel(
            self, text="",
            font=font("small"),
            text_color=COLORS["accent"],
        )
        self._step_label.pack(side="left", padx=(SP["sm"], 0))

        self._elapsed = ctk.CTkLabel(
            self, text="",
            font=mono_font(),
            text_color=COLORS["text_muted"],
        )
        self._elapsed.pack(side="right", padx=SP["md"])

    def set_status(self, text: str, color: str = None):
        self._status_text.configure(text=text)
        if color:
            self._status_dot.configure(text_color=color)

    def set_step_label(self, text: str):
        """Show current pipeline step name."""
        self._step_label.configure(text=text)

    def set_progress(self, fraction: float):
        self._progress.set(fraction)
        self._percent.configure(text=f"{int(fraction * 100)}%")

    def set_elapsed(self, text: str):
        self._elapsed.configure(text=text)


class SidebarButton(ctk.CTkFrame):
    """Sidebar navigation item with icon and optional tooltip."""

    def __init__(self, parent, icon: str, tooltip: str = "",
                 command=None, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            height=48, width=56,
            cursor="hand2",
            **kwargs,
        )
        self.pack_propagate(False)
        self._command = command
        self._active = False
        self._enabled = True
        self._tooltip = tooltip
        self._disabled_reason = ""

        self._indicator = ctk.CTkFrame(
            self, width=3, height=24,
            fg_color="transparent",
            corner_radius=2,
        )
        self._indicator.place(x=0, rely=0.5, anchor="w")

        self._icon_lbl = ctk.CTkLabel(
            self, text=icon,
            font=("Segoe UI Emoji", 16),
            text_color=COLORS["text_muted"],
        )
        self._icon_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Tooltip (delayed show / immediate hide)
        self._tip_window = None
        self._tip_after_id = None
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._icon_lbl.bind("<Enter>", self._on_enter)
        self._icon_lbl.bind("<Leave>", self._on_leave)

        # Click
        self.bind("<Button-1>", self._on_click)
        self._icon_lbl.bind("<Button-1>", self._on_click)

    def _on_click(self, event=None):
        self._hide_tooltip()
        if not self._enabled:
            return
        if self._command:
            self._command()

    def _on_enter(self, event=None):
        if not self._enabled:
            # Show disabled tooltip with reason
            if self._disabled_reason:
                self._tooltip_override = self._disabled_reason
                self._schedule_tooltip()
            return
        if not self._active:
            self.configure(fg_color=COLORS["sidebar_hover"])
        if self._tooltip:
            self._tooltip_override = None
            self._schedule_tooltip()

    def _on_leave(self, event=None):
        if not self._active:
            self.configure(fg_color="transparent")
        self._cancel_tooltip()
        self._hide_tooltip()

    def _schedule_tooltip(self):
        """Show tooltip after a short delay to avoid flicker."""
        self._cancel_tooltip()
        self._tip_after_id = self.after(400, self._show_tooltip)

    def _cancel_tooltip(self):
        """Cancel pending tooltip display."""
        if self._tip_after_id is not None:
            self.after_cancel(self._tip_after_id)
            self._tip_after_id = None

    def _show_tooltip(self):
        self._tip_after_id = None
        if self._tip_window:
            return
        # Use override text (disabled reason) or regular tooltip
        tip_text = getattr(self, "_tooltip_override", None) or self._tooltip
        if not tip_text:
            return
        x = self.winfo_rootx() + 60
        y = self.winfo_rooty() + 10
        try:
            tw = ctk.CTkToplevel(self)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            tw.attributes("-disabled", True)
            tw.lift()
            # Different color for disabled state
            is_disabled_tip = not self._enabled
            bg = COLORS["bg_elevated"]
            fg = COLORS["text_muted"] if is_disabled_tip else COLORS["text_primary"]
            lbl = ctk.CTkLabel(
                tw, text=tip_text,
                font=font("small"),
                fg_color=bg,
                text_color=fg,
                corner_radius=4,
                padx=8, pady=4,
            )
            lbl.pack()
            self._tip_window = tw
        except Exception:
            self._tip_window = None

    def _hide_tooltip(self):
        tw = self._tip_window
        if tw is not None:
            self._tip_window = None
            try:
                tw.destroy()
            except Exception:
                pass

    def set_active(self, active: bool):
        self._active = active
        if not self._enabled:
            return
        if active:
            self.configure(fg_color=COLORS["sidebar_active"])
            self._icon_lbl.configure(text_color=COLORS["accent"])
            self._indicator.configure(fg_color=COLORS["accent"])
        else:
            self.configure(fg_color="transparent")
            self._icon_lbl.configure(text_color=COLORS["text_muted"])
            self._indicator.configure(fg_color="transparent")

    def set_enabled(self, enabled: bool, reason: str = ""):
        """Enable or disable this sidebar button.

        When disabled, the button is visually dimmed and clicks are ignored.
        An optional reason is shown as tooltip on hover.
        """
        self._enabled = enabled
        self._disabled_reason = reason
        if enabled:
            self.configure(cursor="hand2")
            self._icon_lbl.configure(
                text_color=COLORS["accent"] if self._active else COLORS["text_muted"]
            )
        else:
            self.configure(cursor="arrow", fg_color="transparent")
            self._icon_lbl.configure(text_color=COLORS["bg_input"])
            self._indicator.configure(fg_color="transparent")


# ──────────────────────────────────────────────────────────────
# New Visual Widgets
# ──────────────────────────────────────────────────────────────

class StepIndicator(ctk.CTkFrame):
    """Horizontal pipeline step indicator with animated active state.

    Shows conversion stages: Parse -> Transform -> Write -> Validate -> QC
    """

    def __init__(self, parent, labels: list = None, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_secondary"],
            height=60, corner_radius=0, **kwargs,
        )
        self.pack_propagate(False)
        self._labels = labels or STEP_LABELS
        self._states = ["pending"] * len(self._labels)
        self._canvas = tk.Canvas(
            self, bg=COLORS["bg_secondary"],
            highlightthickness=0, height=56,
        )
        self._canvas.pack(fill="x", expand=True, padx=SP["lg"], pady=2)
        self._canvas.bind("<Configure>", lambda e: self._draw())
        self._pulse_phase = 0
        self._pulse_active = False

    def _draw(self, **kwargs):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10:
            return

        n = len(self._labels)
        padding = 40
        step_w = (w - 2 * padding) / max(n - 1, 1)
        cy = h // 2 - 4
        r = 14

        for i in range(n):
            x = padding + i * step_w
            state = self._states[i]
            color = STEP_COLORS.get(state, STEP_COLORS["pending"])

            # Draw connecting line (before current circle)
            if i > 0:
                prev_x = padding + (i - 1) * step_w
                prev_state = self._states[i - 1]
                line_color = STEP_COLORS["done"] if prev_state == "done" else COLORS["divider"]
                c.create_line(prev_x + r, cy, x - r, cy,
                              fill=line_color, width=2)

            # Draw circle
            if state == "active":
                # Glow effect
                glow_r = r + 4 + 2 * math.sin(self._pulse_phase)
                c.create_oval(x - glow_r, cy - glow_r, x + glow_r, cy + glow_r,
                              fill="", outline=color, width=1,
                              stipple="gray25")
            c.create_oval(x - r, cy - r, x + r, cy + r,
                          fill=color if state != "pending" else COLORS["bg_input"],
                          outline=color, width=2)

            # Inner icon
            if state == "done":
                # Checkmark
                c.create_text(x, cy, text="\u2713", fill="white",
                              font=("Segoe UI", 11, "bold"))
            elif state == "error":
                c.create_text(x, cy, text="\u2717", fill="white",
                              font=("Segoe UI", 11, "bold"))
            else:
                # Step number
                txt_color = "white" if state == "active" else COLORS["text_muted"]
                c.create_text(x, cy, text=str(i + 1), fill=txt_color,
                              font=("Segoe UI", 10, "bold"))

            # Label below
            c.create_text(x, cy + r + 12, text=self._labels[i],
                          fill=color if state != "pending" else COLORS["text_muted"],
                          font=(font("small")[0], 9))

    def set_step(self, index: int, state: str):
        """Set step state: 'pending', 'active', 'done', 'error'."""
        if 0 <= index < len(self._states):
            self._states[index] = state
            if state == "active" and not self._pulse_active:
                self._pulse_active = True
                self._animate_pulse()
            elif "active" not in self._states:
                self._pulse_active = False
            self._draw()

    def reset(self):
        """Reset all steps to pending."""
        self._states = ["pending"] * len(self._labels)
        self._pulse_active = False
        self._draw()

    def _animate_pulse(self):
        if not self._pulse_active:
            return
        self._pulse_phase += 0.3
        self._draw()
        self.after(50, self._animate_pulse)


class StatCard(ctk.CTkFrame):
    """Compact statistics card with accent bar, icon, value, and label."""

    def __init__(self, parent, icon: str = "", value: str = "--",
                 label: str = "", accent_index: int = 0, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_elevated"],
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=COLORS["border"],
            **kwargs,
        )
        self._accent_color = STAT_ACCENTS[accent_index % len(STAT_ACCENTS)]

        # Left accent bar
        bar = ctk.CTkFrame(
            self, width=3, fg_color=self._accent_color,
            corner_radius=2,
        )
        bar.pack(side="left", fill="y", padx=(6, 0), pady=8)

        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True,
                     padx=(8, SP["md"]), pady=SP["sm"])

        # Icon + Value row
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        self._icon_lbl = ctk.CTkLabel(
            top_row, text=icon,
            font=("Segoe UI Emoji", 14),
            text_color=self._accent_color,
        )
        self._icon_lbl.pack(side="left", padx=(0, 4))

        self._value_lbl = ctk.CTkLabel(
            top_row, text=value,
            font=font("h2", bold=True),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self._value_lbl.pack(side="left", fill="x", expand=True)

        # Label
        self._label_lbl = ctk.CTkLabel(
            content, text=label,
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._label_lbl.pack(fill="x")

        # Hover effect
        self.bind("<Enter>", lambda e: self.configure(
            fg_color=COLORS["sidebar_hover"]))
        self.bind("<Leave>", lambda e: self.configure(
            fg_color=COLORS["bg_elevated"]))

    def set_value(self, icon: str = None, value: str = None,
                  label: str = None):
        if icon is not None:
            self._icon_lbl.configure(text=icon)
        if value is not None:
            self._value_lbl.configure(text=value)
        if label is not None:
            self._label_lbl.configure(text=label)


class FileDropZone(ctk.CTkFrame):
    """Visual file selection zone with dashed border and status display."""

    def __init__(self, parent, label: str = "Click to select file",
                 browse_callback=None, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_input"],
            corner_radius=CORNER_RADIUS,
            border_width=2, border_color=COLORS["divider"],
            height=80, **kwargs,
        )
        self._browse_callback = browse_callback
        self._file_path = ""

        # Empty state
        self._empty_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._empty_frame.pack(fill="both", expand=True)

        self._icon = ctk.CTkLabel(
            self._empty_frame, text="\U0001f4c1",
            font=("Segoe UI Emoji", 22),
            text_color=COLORS["text_muted"],
        )
        self._icon.pack(pady=(12, 2))

        self._hint = ctk.CTkLabel(
            self._empty_frame, text=label,
            font=font("body"),
            text_color=COLORS["text_muted"],
        )
        self._hint.pack()

        # Loaded state (hidden initially)
        self._loaded_frame = ctk.CTkFrame(self, fg_color="transparent")

        self._check_icon = ctk.CTkLabel(
            self._loaded_frame, text="\u2705",
            font=("Segoe UI Emoji", 16),
            text_color=COLORS["success"],
        )
        self._check_icon.pack(side="left", padx=(SP["md"], SP["sm"]))

        info_frame = ctk.CTkFrame(self._loaded_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        self._filename_lbl = ctk.CTkLabel(
            info_frame, text="",
            font=font("body", bold=True),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self._filename_lbl.pack(fill="x")

        self._filesize_lbl = ctk.CTkLabel(
            info_frame, text="",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._filesize_lbl.pack(fill="x")

        self._clear_btn = ctk.CTkButton(
            self._loaded_frame, text="\u2715", width=28, height=28,
            font=font("body"),
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=4,
            command=self.clear,
        )
        self._clear_btn.pack(side="right", padx=SP["sm"])

        # Click to browse
        for w in [self, self._empty_frame, self._icon, self._hint]:
            w.bind("<Button-1>", lambda e: self._on_click())

        # Hover
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_click(self):
        if self._browse_callback:
            self._browse_callback()

    def _on_enter(self, event=None):
        if not self._file_path:
            self.configure(border_color=COLORS["accent_muted"])

    def _on_leave(self, event=None):
        if not self._file_path:
            self.configure(border_color=COLORS["divider"])

    def set_file(self, path: str):
        """Show loaded file info."""
        self._file_path = path
        self._empty_frame.pack_forget()
        self._loaded_frame.pack(fill="both", expand=True)

        name = os.path.basename(path)
        try:
            size = os.path.getsize(path)
            if size > 1024 * 1024:
                size_str = f"{size / (1024*1024):.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
        except OSError:
            size_str = ""

        self._filename_lbl.configure(text=name)
        self._filesize_lbl.configure(text=size_str)
        self.configure(border_color=COLORS["success"])

    def clear(self):
        """Reset to empty state."""
        self._file_path = ""
        self._loaded_frame.pack_forget()
        self._empty_frame.pack(fill="both", expand=True)
        self.configure(border_color=COLORS["divider"])

    @property
    def value(self) -> str:
        return self._file_path

    @value.setter
    def value(self, v: str):
        if v:
            self.set_file(v)
        else:
            self.clear()


class QCCheckItem(ctk.CTkFrame):
    """Single QC check result row with status icon."""

    STATUS_ICONS = {
        "pass": ("\u2713", COLORS["success"]),
        "fail": ("\u2717", COLORS["error"]),
        "warning": ("\u26a0", COLORS["warning"]),
        "pending": ("\u2022", COLORS["text_muted"]),
    }

    def __init__(self, parent, check_name: str, **kwargs):
        super().__init__(
            parent, fg_color="transparent", height=28, **kwargs,
        )
        self.pack_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            self, text="\u2022", width=24,
            font=font("body", bold=True),
            text_color=COLORS["text_muted"],
        )
        self._status_lbl.pack(side="left")

        self._name_lbl = ctk.CTkLabel(
            self, text=check_name,
            font=font("body"),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self._name_lbl.pack(side="left", fill="x", expand=True)

        self._detail_lbl = ctk.CTkLabel(
            self, text="",
            font=mono_font(),
            text_color=COLORS["text_muted"],
            anchor="e",
        )
        self._detail_lbl.pack(side="right", padx=(SP["sm"], 0))

    def set_result(self, status: str, detail: str = ""):
        """Set check result. status: 'pass', 'fail', 'warning', 'pending'."""
        icon, color = self.STATUS_ICONS.get(
            status, self.STATUS_ICONS["pending"])
        self._status_lbl.configure(text=icon, text_color=color)
        self._detail_lbl.configure(text=detail, text_color=color)


class GeometryDiagram(ctk.CTkFrame):
    """Canvas-based marine geometry diagram showing vessel, source, and receivers."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_elevated"],
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=COLORS["border"],
            **kwargs,
        )
        title = ctk.CTkLabel(
            self, text="Geometry Layout (Top View)",
            font=font("small", bold=True),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        title.pack(fill="x", padx=SP["md"], pady=(SP["sm"], 0))

        self._canvas = tk.Canvas(
            self, bg=COLORS["bg_elevated"],
            highlightthickness=0, height=180,
        )
        self._canvas.pack(fill="x", padx=SP["sm"], pady=SP["sm"])
        self._canvas.bind("<Configure>", lambda e: self._draw())

        self._src_dx = 0.0
        self._src_dy = 0.0
        self._rx1_dx = -10.0
        self._rx1_dy = 20.0
        self._n_channels = 48
        self._rx_interval = 3.125

    def update_geometry(self, geom):
        """Update diagram from MarineGeometry dataclass."""
        self._src_dx = geom.source_dx
        self._src_dy = geom.source_dy
        self._rx1_dx = geom.rx1_dx
        self._rx1_dy = geom.rx1_dy
        self._n_channels = geom.n_channels
        self._rx_interval = geom.rx_interval
        self._draw()

    def _draw(self, **kwargs):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50:
            return

        cx = w // 2
        # Scale: fit everything in canvas
        total_spread = self._rx_interval * max(self._n_channels - 1, 1)
        max_extent = max(total_spread, abs(self._rx1_dy) + 20, 50)
        scale = min((w - 80) / max_extent, 1.5)

        # ── Water background gradient ──
        c.create_rectangle(0, 0, w, h, fill=GEOM_COLORS["water"], outline="")

        # ── Vessel (top center) ──
        vy = 30
        vw, vh = 32, 18
        c.create_rectangle(cx - vw//2, vy - vh//2, cx + vw//2, vy + vh//2,
                           fill=GEOM_COLORS["vessel"], outline=COLORS["divider"],
                           width=1)
        c.create_text(cx, vy, text="V", fill=COLORS["bg_primary"],
                      font=("Segoe UI", 9, "bold"))

        # Direction arrow (bow)
        c.create_polygon(cx, vy - vh//2 - 8, cx - 5, vy - vh//2,
                         cx + 5, vy - vh//2,
                         fill=GEOM_COLORS["vessel"], outline="")

        # ── Source point ──
        sx = cx + self._src_dx * scale
        sy = vy + max(self._src_dy * scale, 15)
        # Line from vessel to source
        c.create_line(cx, vy + vh//2, sx, sy,
                      fill=GEOM_COLORS["source"], width=1, dash=(4, 2))
        c.create_oval(sx - 6, sy - 6, sx + 6, sy + 6,
                      fill=GEOM_COLORS["source"], outline="")
        c.create_text(sx, sy, text="S", fill="white",
                      font=("Segoe UI", 8, "bold"))

        # ── Cable from vessel to first receiver ──
        rx1_x = cx + self._rx1_dx * scale
        rx1_y = vy + max(self._rx1_dy * scale, 30)
        c.create_line(cx, vy + vh//2, rx1_x, rx1_y,
                      fill=GEOM_COLORS["cable"], width=2)

        # ── Receiver array ──
        n_show = min(self._n_channels, 24)  # Show max 24 dots
        step = max(self._n_channels // n_show, 1)
        for i in range(0, self._n_channels, step):
            rx_x = rx1_x + i * self._rx_interval * scale * 0.15
            # Slight vertical offset for each receiver
            rx_y = rx1_y + i * 0.5
            if rx_y > h - 15:
                break
            r = 3
            c.create_oval(rx_x - r, rx_y - r, rx_x + r, rx_y + r,
                          fill=GEOM_COLORS["receiver"], outline="")

        # Cable line through receivers
        last_i = min(self._n_channels - 1, (n_show - 1) * step)
        last_rx_x = rx1_x + last_i * self._rx_interval * scale * 0.15
        last_rx_y = rx1_y + last_i * 0.5
        if last_rx_y < h - 15:
            c.create_line(rx1_x, rx1_y, last_rx_x, last_rx_y,
                          fill=GEOM_COLORS["cable"], width=1)

        # ── Labels ──
        c.create_text(w - 10, 15, text=f"Spread: {total_spread:.0f}m",
                      fill=COLORS["accent"], font=("Segoe UI", 9),
                      anchor="e")
        c.create_text(w - 10, 28, text=f"{self._n_channels}ch x {self._rx_interval}m",
                      fill=COLORS["text_muted"], font=("Segoe UI", 8),
                      anchor="e")

        # Legend
        ly = h - 12
        for i, (name, color) in enumerate([
            ("Vessel", GEOM_COLORS["vessel"]),
            ("Source", GEOM_COLORS["source"]),
            ("Receiver", GEOM_COLORS["receiver"]),
        ]):
            lx = 10 + i * 80
            c.create_oval(lx, ly - 4, lx + 8, ly + 4, fill=color, outline="")
            c.create_text(lx + 14, ly, text=name, fill=COLORS["text_muted"],
                          font=("Segoe UI", 8), anchor="w")


class QualityGauge(ctk.CTkFrame):
    """Semi-circular quality gauge (0-100%)."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_elevated"],
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=COLORS["border"],
            **kwargs,
        )
        self._canvas = tk.Canvas(
            self, bg=COLORS["bg_elevated"],
            highlightthickness=0, width=160, height=100,
        )
        self._canvas.pack(padx=SP["sm"], pady=SP["sm"])
        self._value = 0
        self._draw()

    def set_value(self, percent: float):
        """Set gauge value (0-100)."""
        self._value = max(0, min(100, percent))
        self._draw()

    def _draw(self, **kwargs):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        cx = w // 2
        cy = h - 10
        r = min(cx - 10, cy - 5)

        # Background arc
        c.create_arc(cx - r, cy - r, cx + r, cy + r,
                     start=0, extent=180,
                     fill=COLORS["bg_input"], outline=COLORS["divider"],
                     width=1)

        # Value arc
        if self._value > 0:
            extent = self._value * 180 / 100
            if self._value >= 70:
                color = COLORS["success"]
            elif self._value >= 40:
                color = COLORS["warning"]
            else:
                color = COLORS["error"]
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=180 - extent, extent=extent,
                         fill=color, outline="")

        # Center text
        c.create_text(cx, cy - r // 2,
                      text=f"{int(self._value)}%",
                      fill=COLORS["text_primary"],
                      font=font("h2", bold=True))
        c.create_text(cx, cy - r // 2 + 18,
                      text="Quality",
                      fill=COLORS["text_muted"],
                      font=font("small"))


class MiniProgressTimeline(ctk.CTkFrame):
    """Vertical timeline showing key process events."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent, fg_color=COLORS["bg_elevated"],
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=COLORS["border"],
            **kwargs,
        )
        title = ctk.CTkLabel(
            self, text="Event Timeline",
            font=font("small", bold=True),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        title.pack(fill="x", padx=SP["md"], pady=(SP["sm"], 0))

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_input"],
            scrollbar_button_color=COLORS["accent_muted"],
            height=150,
        )
        self._scroll.pack(fill="both", expand=True,
                          padx=SP["xs"], pady=(0, SP["xs"]))
        self._items = []

    LEVEL_ICONS = {
        "info": ("\u25cb", COLORS["accent"]),
        "success": ("\u25cf", COLORS["success"]),
        "warning": ("\u25b2", COLORS["warning"]),
        "error": ("\u25cf", COLORS["error"]),
    }

    def append(self, level: str, message: str, timestamp: str = None):
        """Add event to timeline."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        icon, color = self.LEVEL_ICONS.get(level, self.LEVEL_ICONS["info"])

        row = ctk.CTkFrame(self._scroll, fg_color="transparent", height=24)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Timestamp
        ctk.CTkLabel(
            row, text=timestamp, width=60,
            font=mono_font(), text_color=COLORS["text_muted"],
        ).pack(side="left")

        # Vertical line + dot
        ctk.CTkLabel(
            row, text=icon, width=16,
            font=("Segoe UI", 10),
            text_color=color,
        ).pack(side="left", padx=(0, 4))

        # Message
        ctk.CTkLabel(
            row, text=message,
            font=font("small"),
            text_color=color,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        self._items.append(row)

        # Auto-scroll
        self._scroll._parent_canvas.yview_moveto(1.0)

    def clear(self):
        """Remove all timeline items."""
        for item in self._items:
            item.destroy()
        self._items.clear()


# ──────────────────────────────────────────────────────────────
# Interpolation Method Info — Data + Dialog
# ──────────────────────────────────────────────────────────────

INTERP_METHOD_INFO = [
    {
        "name": "Linear",
        "icon": "━━━",
        "description": (
            "Standard straight-line interpolation. Receivers are equally "
            "spaced along the cable direction from the first receiver offset, "
            "extending aft from the source. This is the default method used "
            "by RadExPro Marine Geometry."
        ),
        "formula": None,
        "use_case": (
            "48ch UHR surveys with short cable (~150 m). "
            "Position error < 2 m under normal conditions."
        ),
        "pros": [
            "Simple, fast, deterministic",
            "Matches RadExPro standard output",
            "No additional GPS data required",
        ],
        "cons": [
            "Ignores cable curvature from cross-currents",
            "Accuracy degrades with longer cables",
        ],
        "note_style_a": False,
    },
    {
        "name": "Catenary",
        "icon": "\u2312",
        "description": (
            "Physics-based cable shape model using catenary equation. "
            "The cable hangs under its own weight balanced by horizontal "
            "tow tension, producing a characteristic curved shape."
        ),
        "formula": "y(x) = (T/W) \u00b7 cosh(W\u00b7x/T) \u2212 T/W",
        "use_case": (
            "Deep water surveys with long streamers (>5 km) "
            "where cable sag is significant."
        ),
        "pros": [
            "Physically accurate cable shape",
            "Accounts for cable weight and tension",
        ],
        "cons": [
            "Requires tension/weight parameters",
            "Minimal benefit for short UHR cables (<200 m)",
        ],
        "note_style_a": False,
    },
    {
        "name": "Spline",
        "icon": "~",
        "description": (
            "Cubic spline interpolation through known control points. "
            "When partial receiver GPS positions are available, fits a "
            "smooth curve through them. Falls back to linear if fewer "
            "than 3 known positions."
        ),
        "formula": "S(t) = CubicSpline(t_known, pos_known)",
        "use_case": (
            "3D surveys with irregular trace distributions "
            "where known positions exist for some receivers."
        ),
        "pros": [
            "Smooth, continuous curve through known points",
            "Handles irregular distributions",
        ],
        "cons": [
            "Requires known receiver positions as control points",
            "Falls back to linear without sufficient data",
        ],
        "note_style_a": False,
    },
    {
        "name": "Feathering",
        "icon": "\u3030",
        "description": (
            "Cross-current cable displacement model using Head Buoy and "
            "Tail Buoy GPS. Determines actual cable path, then applies a "
            "power-law correction to account for the difference between "
            "straight-line and curved cable positions."
        ),
        "formula": (
            "Cross-track displacement:\n"
            "  \u03b4(t) = C_total \u00b7 (t^\u03b1 \u2212 t)\n"
            "\n"
            "\u03b1 = 2.0 : quadratic (default)\n"
            "\u03b1 = 1.5 : sub-quadratic"
        ),
        "use_case": (
            "Any survey with measurable cross-current. Requires NPD "
            "file with Head + Tail Buoy GPS (Style A only)."
        ),
        "pros": [
            "Most physically realistic receiver positions",
            "Corrects for actual current-induced cable drift",
            "Configurable alpha (\u03b1) exponent",
        ],
        "cons": [
            "Requires Head + Tail Buoy GPS (Style A only)",
            "Requires vessel COG computation",
        ],
        "note_style_a": True,
    },
]


class InterpolationInfoDialog(ctk.CTkToplevel):
    """Info dialog showing all 4 interpolation methods with details."""

    def __init__(self, parent, current_method: str = "Linear", **kwargs):
        super().__init__(parent, **kwargs)
        self.title("Interpolation Methods Guide")
        self.geometry("560x620")
        self.resizable(False, True)
        self.configure(fg_color=COLORS["bg_primary"])
        self.attributes("-topmost", True)
        self._parent_ref = parent
        self.transient(parent)

        # Center on parent
        self.after(50, self._center_on_parent)
        self.after(100, self.focus_force)

        self._build(current_method)

    def _center_on_parent(self):
        """Center dialog over the main window."""
        try:
            top = self._parent_ref.winfo_toplevel()
            px = top.winfo_rootx() + (top.winfo_width() - 560) // 2
            py = top.winfo_rooty() + (top.winfo_height() - 620) // 2
            self.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        except Exception:
            pass

    def _build(self, current_method: str):
        # ── Header ──
        header = ctk.CTkFrame(
            self, fg_color=COLORS["bg_secondary"],
            height=44, corner_radius=0,
        )
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="\u2139  Interpolation Methods Guide",
            font=font("h2", bold=True),
            text_color=COLORS["accent"],
        ).pack(side="left", padx=SP["md"])

        # ── Scrollable content ──
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_input"],
            scrollbar_button_color=COLORS["accent_muted"],
        )
        scroll.pack(fill="both", expand=True, padx=SP["sm"], pady=SP["sm"])

        for info in INTERP_METHOD_INFO:
            is_current = info["name"].lower() == current_method.lower()
            self._add_method_block(scroll, info, is_current)

        # ── Close button ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        btn_frame.pack(fill="x", padx=SP["md"], pady=(0, SP["sm"]))
        ctk.CTkButton(
            btn_frame, text="Close", width=100, height=32,
            font=font("body"),
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self.destroy,
        ).pack(side="right")

    def _add_method_block(self, parent, info: dict, is_current: bool):
        """Render a single method info card."""
        border_color = COLORS["accent"] if is_current else COLORS["border"]
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_elevated"],
            border_width=1,
            border_color=border_color,
            corner_radius=8,
        )
        card.pack(fill="x", pady=(0, SP["sm"]))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=SP["md"], pady=SP["sm"])

        # ── Title row ──
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        name_color = COLORS["accent"] if is_current else COLORS["text_primary"]
        ctk.CTkLabel(
            title_row,
            text=f"{info['icon']}  {info['name']}",
            font=font("h3", bold=True),
            text_color=name_color,
            anchor="w",
        ).pack(side="left")

        if is_current:
            ctk.CTkLabel(
                title_row,
                text="\u25c0 Current",
                font=font("small"),
                text_color=COLORS["accent"],
            ).pack(side="right")

        if info.get("note_style_a"):
            ctk.CTkLabel(
                title_row,
                text="Style A Only",
                font=font("small", bold=True),
                text_color=COLORS["warning"],
            ).pack(side="right", padx=(0, SP["sm"]))

        # ── Description ──
        ctk.CTkLabel(
            inner,
            text=info["description"],
            font=font("body"),
            text_color=COLORS["text_secondary"],
            anchor="w",
            wraplength=490,
            justify="left",
        ).pack(fill="x", pady=(SP["xs"], 0))

        # ── Formula (if present) ──
        if info.get("formula"):
            formula_frame = ctk.CTkFrame(
                inner, fg_color=COLORS["bg_input"],
                corner_radius=6,
            )
            formula_frame.pack(fill="x", pady=(SP["xs"], 0))
            ctk.CTkLabel(
                formula_frame,
                text=info["formula"],
                font=mono_font(),
                text_color=COLORS["text_primary"],
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=SP["sm"], pady=SP["xs"])

        # ── Use case ──
        ctk.CTkLabel(
            inner,
            text=f"Use case: {info['use_case']}",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=490,
            justify="left",
        ).pack(fill="x", pady=(SP["xs"], 0))

        # ── Pros / Cons ──
        pc_frame = ctk.CTkFrame(inner, fg_color="transparent")
        pc_frame.pack(fill="x", pady=(SP["xs"], 0))

        for pro in info.get("pros", []):
            ctk.CTkLabel(
                pc_frame,
                text=f"  \u2713 {pro}",
                font=font("small"),
                text_color=COLORS["success"],
                anchor="w",
            ).pack(fill="x")

        for con in info.get("cons", []):
            ctk.CTkLabel(
                pc_frame,
                text=f"  \u26a0 {con}",
                font=font("small"),
                text_color=COLORS["warning"],
                anchor="w",
            ).pack(fill="x")
