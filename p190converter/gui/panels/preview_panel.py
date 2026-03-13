"""Preview panel — Navigation visualization with matplotlib embed.

Track Map + Receiver Spread + Shot Selector + Shot Detail Card.
Provides interactive visual feedback for geometry parameter changes.
"""

import math
import customtkinter as ctk
import numpy as np

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard

# matplotlib with Tk backend
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


# Dark theme colors for matplotlib
MPL_BG = "#0a0e17"
MPL_FG = "#f1f5f9"
MPL_GRID = "#1e293b"
MPL_TRACK = "#06b6d4"
MPL_SOURCE = "#ef4444"
MPL_RECEIVER = "#3b82f6"
MPL_SPREAD = "#22d3ee"


class PreviewPanel(ctk.CTkFrame):
    """Navigation preview panel with interactive track map."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._collection = None
        self._current_shot_idx = 0
        self._show_receivers = True
        self._show_labels = False
        self._color_mode = "Default"
        self._build()

    def _build(self):
        # ── Top: Map area ──
        map_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_elevated"],
                                  corner_radius=8, border_width=1,
                                  border_color=COLORS["border"])
        map_frame.pack(fill="both", expand=True, pady=(0, SP["sm"]))

        # matplotlib Figure
        self._fig = Figure(figsize=(8, 4), dpi=100,
                           facecolor=MPL_BG, edgecolor=MPL_BG)
        self._ax = self._fig.add_subplot(111)
        self._style_axes()

        self._canvas = FigureCanvasTkAgg(self._fig, master=map_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)

        # Custom dark-themed toolbar (replaces default NavigationToolbar2Tk)
        toolbar_frame = ctk.CTkFrame(map_frame, fg_color=COLORS["bg_secondary"],
                                      height=36, corner_radius=0)
        toolbar_frame.pack(fill="x", side="bottom")
        toolbar_frame.pack_propagate(False)
        self._build_custom_toolbar(toolbar_frame)

        # ── Bottom controls ──
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=(0, SP["sm"]))

        # Shot selector
        shot_card = SectionCard(ctrl_frame, title="Shot Selector")
        shot_card.pack(side="left", fill="both", expand=True,
                       padx=(0, SP["sm"]))

        s_inner = ctk.CTkFrame(shot_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._prev_btn = ctk.CTkButton(
            s_inner, text="\u25c4", width=36, height=28,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._prev_shot,
        )
        self._prev_btn.pack(side="left")

        self._shot_label = ctk.CTkLabel(
            s_inner, text="Shot -- of --",
            font=font("body"),
            text_color=COLORS["text_primary"],
        )
        self._shot_label.pack(side="left", padx=SP["sm"])

        self._next_btn = ctk.CTkButton(
            s_inner, text="\u25ba", width=36, height=28,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._next_shot,
        )
        self._next_btn.pack(side="left")

        # Shot slider
        self._slider = ctk.CTkSlider(
            s_inner,
            from_=0, to=1,
            number_of_steps=1,
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent_muted"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            command=self._on_slider,
        )
        self._slider.set(0)
        self._slider.pack(side="left", fill="x", expand=True, padx=SP["sm"])

        # Display options
        opt_card = SectionCard(ctrl_frame, title="Display")
        opt_card.pack(side="left", fill="y")

        o_inner = ctk.CTkFrame(opt_card, fg_color="transparent")
        o_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._rx_switch = ctk.CTkSwitch(
            o_inner, text="Receivers",
            font=font("small"),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            command=self._toggle_receivers,
        )
        self._rx_switch.select()
        self._rx_switch.pack(anchor="w", pady=1)

        self._lbl_switch = ctk.CTkSwitch(
            o_inner, text="Labels",
            font=font("small"),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            command=self._toggle_labels,
        )
        self._lbl_switch.pack(anchor="w", pady=1)

        # ── Shot Detail Card ──
        detail_card = SectionCard(self, title="Shot Detail")
        detail_card.pack(fill="x")

        self._detail_label = ctk.CTkLabel(
            detail_card,
            text="Load data to view shot details",
            font=mono_font(),
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left",
        )
        self._detail_label.pack(
            fill="x", padx=SP["md"], pady=(0, SP["md"]),
        )

        # Initial empty state
        self._draw_empty()

    def _build_custom_toolbar(self, parent):
        """Build dark-themed toolbar with icon buttons for matplotlib navigation."""
        # Use the canvas's built-in toolbar methods
        toolbar_nav = NavigationToolbar2Tk(self._canvas, parent)
        toolbar_nav.update()
        # Hide default toolbar — we use it only for its methods
        toolbar_nav.pack_forget()
        self._mpl_toolbar = toolbar_nav

        btn_cfg = dict(
            height=26, corner_radius=4,
            font=font("small"),
            fg_color="transparent",
            hover_color=COLORS["bg_input"],
            text_color=COLORS["text_secondary"],
            border_width=0,
        )

        buttons = [
            ("\u2302", "Home", lambda: self._tb_action("home")),           # Home
            ("\u25c0", "Back", lambda: self._tb_action("back")),           # Back
            ("\u25b6", "Fwd", lambda: self._tb_action("forward")),         # Forward
            (None, None, None),                                             # separator
            ("\u2725", "Pan", lambda: self._tb_action("pan")),             # Pan
            ("\u2922", "Zoom", lambda: self._tb_action("zoom")),           # Zoom
            (None, None, None),                                             # separator
            ("\u2913", "Save", lambda: self._tb_action("save_figure")),    # Save
        ]

        for icon, tip, cmd in buttons:
            if icon is None:
                sep = ctk.CTkFrame(parent, width=1, height=18,
                                    fg_color=COLORS["divider"])
                sep.pack(side="left", padx=4, pady=9)
                continue
            btn = ctk.CTkButton(parent, text=icon, width=32, command=cmd, **btn_cfg)
            btn.pack(side="left", padx=1, pady=4)

        # Coordinate display on right side
        self._coord_label = ctk.CTkLabel(
            parent, text="",
            font=mono_font(),
            text_color=COLORS["text_muted"],
        )
        self._coord_label.pack(side="right", padx=SP["sm"])

        # Connect mouse motion for coordinate display
        self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _tb_action(self, action):
        """Execute a matplotlib toolbar action."""
        tb = self._mpl_toolbar
        if action == "home":
            tb.home()
        elif action == "back":
            tb.back()
        elif action == "forward":
            tb.forward()
        elif action == "pan":
            tb.pan()
        elif action == "zoom":
            tb.zoom()
        elif action == "save_figure":
            tb.save_figure()
        self._canvas.draw_idle()

    def _on_mouse_move(self, event):
        """Update coordinate display on mouse move."""
        if event.inaxes and event.xdata is not None:
            self._coord_label.configure(
                text=f"E {event.xdata:.1f}  N {event.ydata:.1f}"
            )
        else:
            self._coord_label.configure(text="")

    def _style_axes(self):
        """Apply dark theme to matplotlib axes."""
        ax = self._ax
        ax.set_facecolor(MPL_BG)
        ax.tick_params(colors=MPL_FG, labelsize=8)
        ax.xaxis.label.set_color(MPL_FG)
        ax.yaxis.label.set_color(MPL_FG)
        ax.title.set_color(MPL_FG)
        for spine in ax.spines.values():
            spine.set_color(MPL_GRID)
        ax.grid(True, color=MPL_GRID, alpha=0.3, linewidth=0.5)
        ax.set_xlabel("Easting (m)", fontsize=9)
        ax.set_ylabel("Northing (m)", fontsize=9)

    def _draw_empty(self):
        """Draw empty placeholder."""
        self._ax.clear()
        self._style_axes()
        self._ax.text(
            0.5, 0.5, "Load data to preview navigation",
            transform=self._ax.transAxes,
            ha="center", va="center",
            color=COLORS["text_muted"], fontsize=12,
        )
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def set_collection(self, collection):
        """Set ShotGatherCollection and update map."""
        self._collection = collection
        n = len(collection.shots)
        if n == 0:
            self._draw_empty()
            return

        self._current_shot_idx = 0
        self._slider.configure(to=max(1, n - 1),
                                number_of_steps=max(1, n - 1))
        self._slider.set(0)
        self._update_display()

    def _update_display(self):
        """Redraw track map + selected shot details."""
        if not self._collection or not self._collection.shots:
            return

        shots = self._collection.shots
        n = len(shots)
        idx = self._current_shot_idx

        # Track data
        src_x = [s.source_x for s in shots]
        src_y = [s.source_y for s in shots]

        # Draw
        self._ax.clear()
        self._style_axes()

        # Full track
        self._ax.plot(src_x, src_y, '-', color=MPL_TRACK,
                      linewidth=1.0, alpha=0.6, zorder=1)
        self._ax.plot(src_x, src_y, '.', color=MPL_TRACK,
                      markersize=1.5, alpha=0.4, zorder=2)

        # Start/End markers
        self._ax.plot(src_x[0], src_y[0], '*', color=COLORS["success"],
                      markersize=12, zorder=5, label="Start")
        self._ax.plot(src_x[-1], src_y[-1], 's', color=COLORS["warning"],
                      markersize=8, zorder=5, label="End")

        # Selected shot
        shot = shots[idx]
        self._ax.plot(shot.source_x, shot.source_y, '*',
                      color=MPL_SOURCE, markersize=14, zorder=10,
                      label=f"Shot #{idx+1}")

        # Receivers
        if self._show_receivers and shot.receivers:
            rx_x = [r.x for r in shot.receivers]
            rx_y = [r.y for r in shot.receivers]
            self._ax.plot(rx_x, rx_y, 'o', color=MPL_RECEIVER,
                          markersize=3, alpha=0.8, zorder=8)
            # Fan lines from source to each receiver
            for rx in shot.receivers:
                self._ax.plot([shot.source_x, rx.x],
                              [shot.source_y, rx.y],
                              '-', color=MPL_SPREAD,
                              linewidth=0.3, alpha=0.3, zorder=7)

            # Labels for first and last receiver
            if self._show_labels and len(shot.receivers) >= 2:
                r1 = shot.receivers[0]
                rn = shot.receivers[-1]
                self._ax.annotate(
                    f"CH{r1.channel}", (r1.x, r1.y),
                    fontsize=7, color=MPL_RECEIVER, alpha=0.8,
                    xytext=(5, 5), textcoords="offset points",
                )
                self._ax.annotate(
                    f"CH{rn.channel}", (rn.x, rn.y),
                    fontsize=7, color=MPL_RECEIVER, alpha=0.8,
                    xytext=(5, 5), textcoords="offset points",
                )

        # Legend & title
        self._ax.legend(fontsize=7, loc="upper left",
                        facecolor=MPL_BG, edgecolor=MPL_GRID,
                        labelcolor=MPL_FG)

        line = self._collection.line_name or "Unknown"
        self._ax.set_title(f"Track Map - {line}", fontsize=10, pad=8)
        self._ax.set_aspect("equal", adjustable="datalim")
        self._fig.tight_layout()
        self._canvas.draw_idle()

        # Update shot label
        self._shot_label.configure(
            text=f"Shot {idx+1} of {n} (FFID: {shot.ffid})"
        )

        # Update detail card
        self._update_detail(shot)

    def _update_detail(self, shot):
        """Update shot detail card."""
        lines = [
            f"FFID: {shot.ffid:>10}  |  Day: {shot.day:03d}  |  "
            f"Time: {shot.hour:02d}:{shot.minute:02d}:{shot.second:02d}",
            f"Source:  {shot.source_x:>12.1f} E,  {shot.source_y:>12.1f} N",
        ]

        if shot.receivers:
            r1 = shot.receivers[0]
            rn = shot.receivers[-1]
            lines.append(
                f"RX1:    {r1.x:>12.1f} E,  {r1.y:>12.1f} N  (CH{r1.channel})"
            )
            lines.append(
                f"RX{rn.channel}:  {rn.x:>10.1f} E,  {rn.y:>12.1f} N  (CH{rn.channel})"
            )
            lines.append(
                f"Spread: {shot.spread_length:>8.1f} m  |  "
                f"Channels: {len(shot.receivers)}"
            )

        if shot.heading is not None:
            lines.append(f"Heading: {shot.heading:.1f} deg")

        self._detail_label.configure(
            text="\n".join(lines),
            text_color=COLORS["text_primary"],
        )

    def _prev_shot(self):
        if self._collection and self._current_shot_idx > 0:
            self._current_shot_idx -= 1
            self._slider.set(self._current_shot_idx)
            self._update_display()

    def _next_shot(self):
        if self._collection:
            max_idx = len(self._collection.shots) - 1
            if self._current_shot_idx < max_idx:
                self._current_shot_idx += 1
                self._slider.set(self._current_shot_idx)
                self._update_display()

    def _on_slider(self, value):
        idx = int(round(value))
        if self._collection and idx != self._current_shot_idx:
            self._current_shot_idx = idx
            self._update_display()

    def _toggle_receivers(self):
        self._show_receivers = self._rx_switch.get() == 1
        if self._collection:
            self._update_display()

    def _toggle_labels(self):
        self._show_labels = self._lbl_switch.get() == 1
        if self._collection:
            self._update_display()

    def update_single_shot_preview(self, shot):
        """Update preview with a single modified shot (for geometry panel feedback).

        Used for real-time geometry parameter visualization.
        """
        if not self._collection:
            return

        # Replace current shot temporarily and redraw
        idx = self._current_shot_idx
        original = self._collection.shots[idx]
        self._collection.shots[idx] = shot
        self._update_display()
        self._collection.shots[idx] = original
