"""Geometry panel — Marine Geometry parameters (Style A only)."""

import customtkinter as ctk

from ..theme import COLORS, SP, CORNER_RADIUS, font, mono_font
from ..widgets import SectionCard, FormField, GeometryDiagram, InterpolationInfoDialog
from ...models.survey_config import MarineGeometry


class GeometryPanel(ctk.CTkFrame):
    """Panel for Marine Geometry offset configuration (Style A only).

    Provides real-time preview connection: parameter changes trigger
    preview panel update via callback.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_geometry_changed = None
        self._build()

    def _build(self):
        # ── Style A indicator banner ──
        banner = ctk.CTkFrame(self, fg_color=COLORS["accent_dim"],
                               corner_radius=6, height=32)
        banner.pack(fill="x", pady=(0, SP["sm"]))
        banner.pack_propagate(False)
        ctk.CTkLabel(
            banner,
            text="\u2699  Marine Geometry  -  Style A Only (NPD + Geometry Interpolation)",
            font=font("small", bold=True),
            text_color=COLORS["accent"],
        ).pack(side="left", padx=SP["md"])

        # ── Geometry Diagram (Top) ──
        self._diagram = GeometryDiagram(self)
        self._diagram.pack(fill="x", pady=(0, SP["md"]))

        # ── Scrollable form area ──
        form_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_input"],
            scrollbar_button_color=COLORS["accent_muted"],
        )
        form_scroll.pack(fill="both", expand=True)

        # ── Source Offset Card ──
        src_card = SectionCard(form_scroll, title="Source Offset")
        src_card.pack(fill="x", pady=(0, SP["md"]))

        s_inner = ctk.CTkFrame(src_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._src_dx = FormField(s_inner, label="Cross-track dx (m):", default="0.0")
        self._src_dx.pack(fill="x", pady=SP["xs"])
        self._src_dx.bind_change(self._notify_change)

        self._src_dy = FormField(s_inner, label="Along-track dy (m):", default="0.0")
        self._src_dy.pack(fill="x", pady=SP["xs"])
        self._src_dy.bind_change(self._notify_change)

        src_info = ctk.CTkLabel(
            s_inner,
            text="  + starboard (cross-track), + bow (along-track) | P190 Code 2 (Rectangular)",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        src_info.pack(fill="x", pady=(SP["xs"], 0))

        # ── First Receiver Offset Card ──
        rx_card = SectionCard(form_scroll, title="First Receiver (RX1) Offset")
        rx_card.pack(fill="x", pady=(0, SP["md"]))

        r_inner = ctk.CTkFrame(rx_card, fg_color="transparent")
        r_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._rx1_dx = FormField(r_inner, label="Cross-track dx (m):", default="-10.0")
        self._rx1_dx.pack(fill="x", pady=SP["xs"])
        self._rx1_dx.bind_change(self._notify_change)

        self._rx1_dy = FormField(r_inner, label="Along-track dy (m):", default="20.0")
        self._rx1_dy.pack(fill="x", pady=SP["xs"])
        self._rx1_dy.bind_change(self._notify_change)

        # ── Receiver Array Card ──
        arr_card = SectionCard(form_scroll, title="Receiver Array")
        arr_card.pack(fill="x", pady=(0, SP["md"]))

        a_inner = ctk.CTkFrame(arr_card, fg_color="transparent")
        a_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._n_channels = FormField(a_inner, label="Channels:", default="48")
        self._n_channels.pack(fill="x", pady=SP["xs"])
        self._n_channels.bind_change(self._notify_change)

        self._rx_interval = FormField(a_inner, label="Interval (m):", default="3.125")
        self._rx_interval.pack(fill="x", pady=SP["xs"])
        self._rx_interval.bind_change(self._notify_change)

        self._cable_depth = FormField(a_inner, label="Cable Depth (m):", default="2.0")
        self._cable_depth.pack(fill="x", pady=SP["xs"])
        self._cable_depth.bind_change(self._notify_change)

        # ── Interpolation Method Card ──
        interp_card = SectionCard(form_scroll, title="")
        interp_card.pack(fill="x", pady=(0, SP["md"]))

        # Custom header with info button
        title_row = ctk.CTkFrame(interp_card, fg_color="transparent")
        title_row.pack(fill="x", padx=SP["md"], pady=(SP["md"], SP["sm"]))

        ctk.CTkLabel(
            title_row,
            text="Interpolation Method",
            font=font("h3", bold=True),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(side="left")

        self._info_btn = ctk.CTkButton(
            title_row, text="\u2139", width=28, height=28,
            font=font("body"),
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["accent"],
            border_width=1,
            border_color=COLORS["accent_muted"],
            corner_radius=14,
            command=self._show_interp_info,
        )
        self._info_btn.pack(side="left", padx=(SP["sm"], 0))

        i_inner = ctk.CTkFrame(interp_card, fg_color="transparent")
        i_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._interp_seg = ctk.CTkSegmentedButton(
            i_inner,
            values=["Linear", "Catenary", "Spline", "Feathering"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_input"],
            unselected_hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._on_interp_method_changed,
        )
        self._interp_seg.set("Linear")
        self._interp_seg.pack(fill="x")

        self._interp_info_label = ctk.CTkLabel(
            i_inner,
            text="RadExPro standard. Receivers equally spaced along cable direction. Sufficient for 48ch UHR (~150 m).",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=500,
        )
        self._interp_info_label.pack(fill="x", pady=(SP["xs"], 0))

        # ── Feathering-specific controls (hidden by default) ──
        self._feathering_frame = ctk.CTkFrame(i_inner, fg_color="transparent")

        self._alpha_field = FormField(
            self._feathering_frame, label="Alpha (\u03b1):", default="2.0",
        )
        self._alpha_field.pack(fill="x", pady=SP["xs"])
        self._alpha_field.bind_change(self._notify_change)

        ctk.CTkLabel(
            self._feathering_frame,
            text="Power-law exponent (2.0 = quadratic, 1.5 = sub-quadratic)",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(fill="x")

        # Style A warning
        warn_frame = ctk.CTkFrame(
            self._feathering_frame,
            fg_color=COLORS["accent_dim"],
            corner_radius=6,
            height=28,
        )
        warn_frame.pack(fill="x", pady=(SP["xs"], 0))
        warn_frame.pack_propagate(False)
        ctk.CTkLabel(
            warn_frame,
            text="\u26a0  Requires NPD file with Head + Tail Buoy GPS (Style A only)",
            font=font("small", bold=True),
            text_color=COLORS["warning"],
        ).pack(side="left", padx=SP["sm"])

        # ── Spread Summary ──
        self._spread_label = ctk.CTkLabel(
            form_scroll,
            text=self._calc_spread_text(),
            font=font("body"),
            text_color=COLORS["accent"],
            anchor="w",
        )
        self._spread_label.pack(fill="x", pady=(0, SP["sm"]))

    def _calc_spread_text(self) -> str:
        try:
            n = int(self._n_channels.value)
            interval = float(self._rx_interval.value)
            spread = interval * (n - 1)
            return f"Total Spread: {spread:.1f} m  ({n} channels x {interval} m interval)"
        except (ValueError, AttributeError):
            return "Total Spread: -- m"

    # ── Interpolation method handlers ──

    _INTERP_DESCRIPTIONS = {
        "Linear": "RadExPro standard. Receivers equally spaced along cable direction. Sufficient for 48ch UHR (~150 m).",
        "Catenary": "Physics-based cable shape (catenary equation). For deep water / long streamers (>5 km).",
        "Spline": "Cubic spline through known positions. For irregular distributions / 3D regularization.",
        "Feathering": "Cross-current cable displacement model using Head/Tail Buoy GPS. Most physically realistic.",
    }

    def _on_interp_method_changed(self, value=None):
        """Handle interpolation method selection change."""
        method = self._interp_seg.get()

        # Toggle feathering controls visibility
        if method == "Feathering":
            self._feathering_frame.pack(fill="x", pady=(SP["sm"], 0))
        else:
            self._feathering_frame.pack_forget()

        # Update info label text
        self._interp_info_label.configure(
            text=self._INTERP_DESCRIPTIONS.get(method, "")
        )
        self._notify_change()

    def _show_interp_info(self):
        """Open the interpolation methods info dialog."""
        current = self._interp_seg.get()
        InterpolationInfoDialog(self, current_method=current)

    def _notify_change(self):
        self._spread_label.configure(text=self._calc_spread_text())
        geom = self.get_geometry()
        # Update diagram in real-time
        self._diagram.update_geometry(geom)
        if self._on_geometry_changed:
            self._on_geometry_changed(geom)

    def set_geometry_changed_callback(self, callback):
        """Set callback(geometry) for parameter change events."""
        self._on_geometry_changed = callback

    def get_geometry(self) -> MarineGeometry:
        """Return MarineGeometry from current field values."""
        try:
            alpha = 2.0
            try:
                alpha = float(self._alpha_field.value)
            except (ValueError, AttributeError):
                pass

            return MarineGeometry(
                source_dx=float(self._src_dx.value),
                source_dy=float(self._src_dy.value),
                rx1_dx=float(self._rx1_dx.value),
                rx1_dy=float(self._rx1_dy.value),
                n_channels=int(self._n_channels.value),
                rx_interval=float(self._rx_interval.value),
                cable_depth=float(self._cable_depth.value),
                interp_method=self._interp_seg.get().lower(),
                feathering_alpha=alpha,
            )
        except ValueError:
            return MarineGeometry()

    def set_geometry(self, geom_dict: dict):
        """Restore geometry values from a profile dict."""
        if not geom_dict:
            return
        field_map = {
            "source_dx": self._src_dx,
            "source_dy": self._src_dy,
            "rx1_dx": self._rx1_dx,
            "rx1_dy": self._rx1_dy,
            "n_channels": self._n_channels,
            "rx_interval": self._rx_interval,
            "cable_depth": self._cable_depth,
        }
        for key, field in field_map.items():
            if key in geom_dict:
                field.value = str(geom_dict[key])

        if "interp_method" in geom_dict:
            method = geom_dict["interp_method"].capitalize()
            if method in ["Linear", "Catenary", "Spline", "Feathering"]:
                self._interp_seg.set(method)
                self._on_interp_method_changed()

        if "feathering_alpha" in geom_dict:
            self._alpha_field.value = str(geom_dict["feathering_alpha"])

        self._notify_change()

    def set_channel_count(self, count: int):
        """Update the channel count field from parsed track data."""
        if count <= 0:
            return
        self._n_channels.value = str(count)
        self._notify_change()
