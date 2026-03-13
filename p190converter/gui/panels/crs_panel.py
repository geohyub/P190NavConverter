"""CRS panel — Coordinate Reference System configuration.

Region-categorized preset selection (Korea / Asia-Pacific / UTM / Custom)
with coordinate preview and CRS info display.
"""

import customtkinter as ctk

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard, FormField
from ...models.survey_config import CRSConfig


# ──────────────────────────────────────────────────────────────
# CRS Preset Database
# ──────────────────────────────────────────────────────────────
CRS_PRESETS = {
    "Korea": [
        # label, epsg, zone, hemi, datum, description
        ("UTM 51N  (West Coast)",           32651, 51, "N", "WGS-84",   "WGS 84 / UTM zone 51N"),
        ("UTM 52N  (South/Ulsan/Busan)",    32652, 52, "N", "WGS-84",   "WGS 84 / UTM zone 52N"),
        ("UTM 53N  (East Sea)",             32653, 53, "N", "WGS-84",   "WGS 84 / UTM zone 53N"),
        ("EPSG:5179  Korea 2000 Unified",   5179,   0, "N", "GRS 1980", "Korea 2000 / Unified CS"),
        ("EPSG:5185  West Belt 2010",       5185,   0, "N", "GRS 1980", "Korea 2000 / West Belt 2010"),
        ("EPSG:5186  Central Belt 2010",    5186,   0, "N", "GRS 1980", "Korea 2000 / Central Belt 2010"),
        ("EPSG:5187  East Belt 2010",       5187,   0, "N", "GRS 1980", "Korea 2000 / East Belt 2010"),
        ("EPSG:5188  East Sea Belt 2010",   5188,   0, "N", "GRS 1980", "Korea 2000 / East Sea Belt 2010"),
    ],
    "Asia-Pacific": [
        ("UTM 48N  (Vietnam/Thailand)",     32648, 48, "N", "WGS-84",   "WGS 84 / UTM zone 48N"),
        ("UTM 49N  (Malaysia/Philippines)", 32649, 49, "N", "WGS-84",   "WGS 84 / UTM zone 49N"),
        ("UTM 50N  (Taiwan/Philippines)",   32650, 50, "N", "WGS-84",   "WGS 84 / UTM zone 50N"),
        ("UTM 54N  (Japan/Sakhalin)",       32654, 54, "N", "WGS-84",   "WGS 84 / UTM zone 54N"),
        ("UTM 55N  (Japan Far East)",       32655, 55, "N", "WGS-84",   "WGS 84 / UTM zone 55N"),
        ("UTM 47N  (Myanmar/Gulf of Thai)", 32647, 47, "N", "WGS-84",   "WGS 84 / UTM zone 47N"),
        ("UTM 46N  (Bay of Bengal)",        32646, 46, "N", "WGS-84",   "WGS 84 / UTM zone 46N"),
        ("SVY21  Singapore",                3414,   0, "N", "WGS-84",   "SVY21 / Singapore TM"),
        ("TWD97  Taiwan TM2",               3826,   0, "N", "GRS 1980", "TWD97 / TM2 zone 1"),
    ],
    "UTM Global": [
        ("UTM 30N  (North Sea West)",       32630, 30, "N", "WGS-84",   "WGS 84 / UTM zone 30N"),
        ("UTM 31N  (North Sea Central)",    32631, 31, "N", "WGS-84",   "WGS 84 / UTM zone 31N"),
        ("UTM 32N  (North Sea East)",       32632, 32, "N", "WGS-84",   "WGS 84 / UTM zone 32N"),
        ("UTM 33N  (Baltic/Norway)",        32633, 33, "N", "WGS-84",   "WGS 84 / UTM zone 33N"),
        ("UTM 36N  (Mediterranean)",        32636, 36, "N", "WGS-84",   "WGS 84 / UTM zone 36N"),
        ("UTM 39N  (Persian Gulf)",         32639, 39, "N", "WGS-84",   "WGS 84 / UTM zone 39N"),
        ("UTM 40N  (Arabian Sea)",          32640, 40, "N", "WGS-84",   "WGS 84 / UTM zone 40N"),
        ("UTM 17N  (Gulf of Mexico)",       32617, 17, "N", "WGS-84",   "WGS 84 / UTM zone 17N"),
        ("UTM 21S  (Brazil)",               32721, 21, "S", "WGS-84",   "WGS 84 / UTM zone 21S"),
        ("UTM 50S  (Australia NW)",         32750, 50, "S", "WGS-84",   "WGS 84 / UTM zone 50S"),
        ("UTM 51S  (Australia NE)",         32751, 51, "S", "WGS-84",   "WGS 84 / UTM zone 51S"),
    ],
}

REGION_DESCRIPTIONS = {
    "Korea":        "Korean Peninsula offshore survey CRS",
    "Asia-Pacific": "Asia-Pacific region CRS for marine survey",
    "UTM Global":   "Common UTM zones worldwide for offshore",
    "Custom":       "Enter any EPSG code manually",
}


class CRSPanel(ctk.CTkFrame):
    """Panel for CRS / UTM zone selection and preview."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_crs_changed = None
        self._current_crs = CRSConfig.from_zone(52, "N")
        self._build()

    def _build(self):
        # ── Region Selector ──
        region_card = SectionCard(self, title="Region")
        region_card.pack(fill="x", pady=(0, SP["md"]))

        r_inner = ctk.CTkFrame(region_card, fg_color="transparent")
        r_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._region_seg = ctk.CTkSegmentedButton(
            r_inner,
            values=["Korea", "Asia-Pacific", "UTM Global", "Custom"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_input"],
            unselected_hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._on_region_select,
        )
        self._region_seg.set("Korea")
        self._region_seg.pack(fill="x")

        self._region_desc = ctk.CTkLabel(
            r_inner,
            text=REGION_DESCRIPTIONS["Korea"],
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._region_desc.pack(fill="x", pady=(SP["xs"], 0))

        # ── CRS Preset Selector ──
        preset_card = SectionCard(self, title="CRS Preset")
        preset_card.pack(fill="x", pady=(0, SP["md"]))

        p_inner = ctk.CTkFrame(preset_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # Preset dropdown
        self._preset_options = self._get_preset_labels("Korea")
        self._preset_menu = ctk.CTkOptionMenu(
            p_inner,
            values=self._preset_options,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_muted"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_elevated"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["sidebar_hover"],
            dropdown_font=font("body"),
            corner_radius=6,
            command=self._on_preset_select,
        )
        self._preset_menu.set(self._preset_options[1])  # UTM 52N default
        self._preset_menu.pack(fill="x")
        self._preset_card = preset_card

        # ── Custom EPSG Card ──
        self._custom_card = SectionCard(self, title="Custom CRS (EPSG)")
        c_inner = ctk.CTkFrame(self._custom_card, fg_color="transparent")
        c_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        epsg_row = ctk.CTkFrame(c_inner, fg_color="transparent")
        epsg_row.pack(fill="x", pady=SP["xs"])

        ctk.CTkLabel(
            epsg_row, text="EPSG Code:", width=100,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["sm"]))

        self._epsg_entry = ctk.CTkEntry(
            epsg_row, width=140,
            placeholder_text="e.g. 32652, 5179",
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self._epsg_entry.pack(side="left")

        apply_btn = ctk.CTkButton(
            epsg_row, text="Apply", width=80,
            font=font("body"),
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._apply_custom_epsg,
        )
        apply_btn.pack(side="left", padx=(SP["sm"], 0))

        custom_hint = ctk.CTkLabel(
            c_inner,
            text="Any valid EPSG code supported (pyproj). "
                 "UTM: 326XX(N)/327XX(S), Korea 2000: 5179/5185-5188",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=500,
        )
        custom_hint.pack(fill="x", pady=(SP["xs"], 0))
        # Hidden by default
        # (will show/hide based on region selection)

        # ── CRS Info Card ──
        info_card = SectionCard(self, title="Current CRS Configuration")
        info_card.pack(fill="x", pady=(0, SP["md"]))

        self._info_text = ctk.CTkLabel(
            info_card,
            text=self._format_crs_info(self._current_crs),
            font=mono_font(),
            text_color=COLORS["text_primary"],
            anchor="w",
            justify="left",
        )
        self._info_text.pack(
            fill="x", padx=SP["md"], pady=(0, SP["md"]),
        )

        # ── Conversion Preview Card ──
        preview_card = SectionCard(self, title="Coordinate Preview")
        preview_card.pack(fill="x")

        pv_inner = ctk.CTkFrame(preview_card, fg_color="transparent")
        pv_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # Sample coordinate input
        sample_row = ctk.CTkFrame(pv_inner, fg_color="transparent")
        sample_row.pack(fill="x", pady=SP["xs"])

        ctk.CTkLabel(
            sample_row, text="Sample E:", width=80,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["xs"]))

        self._sample_e = ctk.CTkEntry(
            sample_row, width=120,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self._sample_e.insert(0, "618538.3")
        self._sample_e.pack(side="left", padx=(0, SP["md"]))

        ctk.CTkLabel(
            sample_row, text="Sample N:", width=80,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["xs"]))

        self._sample_n = ctk.CTkEntry(
            sample_row, width=120,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self._sample_n.insert(0, "3892818.4")
        self._sample_n.pack(side="left")

        convert_btn = ctk.CTkButton(
            sample_row, text="Convert", width=80,
            font=font("body"),
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._preview_conversion,
        )
        convert_btn.pack(side="left", padx=(SP["sm"], 0))

        self._preview_label = ctk.CTkLabel(
            pv_inner,
            text="Click 'Convert' to preview coordinate transformation",
            font=mono_font(),
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left",
        )
        self._preview_label.pack(fill="x", pady=(SP["xs"], 0))

        # Set initial view (Korea, hide custom card)
        self._on_region_select("Korea")

    # ── Region / Preset Selection ──

    def _get_preset_labels(self, region: str):
        presets = CRS_PRESETS.get(region, [])
        return [p[0] for p in presets]

    def _find_preset(self, region: str, label: str):
        for p in CRS_PRESETS.get(region, []):
            if p[0] == label:
                return p
        return None

    def _on_region_select(self, region: str):
        self._region_desc.configure(
            text=REGION_DESCRIPTIONS.get(region, ""),
        )

        if region == "Custom":
            self._preset_card.pack_forget()
            self._custom_card.pack(fill="x", pady=(0, SP["md"]),
                                    before=self._info_text.master)
        else:
            self._custom_card.pack_forget()
            self._preset_card.pack(fill="x", pady=(0, SP["md"]),
                                    before=self._info_text.master)
            labels = self._get_preset_labels(region)
            self._preset_menu.configure(values=labels)
            if labels:
                self._preset_menu.set(labels[0])
                self._on_preset_select(labels[0])

    def _on_preset_select(self, label: str):
        region = self._region_seg.get()
        if region == "Custom":
            return
        preset = self._find_preset(region, label)
        if not preset:
            return
        _, epsg, zone, hemi, datum, desc = preset
        self._current_crs = CRSConfig.from_preset(
            epsg=epsg, name=desc, datum=datum, zone=zone, hemi=hemi,
        )
        self._update_info_display()
        if self._on_crs_changed:
            self._on_crs_changed(self._current_crs)

    def _apply_custom_epsg(self):
        try:
            epsg = int(self._epsg_entry.get().strip())
        except ValueError:
            return
        # Auto-detect UTM zone from EPSG
        if 32601 <= epsg <= 32660:
            zone = epsg - 32600
            hemi = "N"
            name = f"WGS 84 / UTM zone {zone}N"
            datum = "WGS-84"
        elif 32701 <= epsg <= 32760:
            zone = epsg - 32700
            hemi = "S"
            name = f"WGS 84 / UTM zone {zone}S"
            datum = "WGS-84"
        else:
            zone = 0
            hemi = "N"
            name = f"EPSG:{epsg}"
            datum = "WGS-84"
            # Check known Korean/Asian presets
            for region_presets in CRS_PRESETS.values():
                for p in region_presets:
                    if p[1] == epsg:
                        zone, hemi, datum, name = p[2], p[3], p[4], p[5]
                        break

        self._current_crs = CRSConfig.from_preset(
            epsg=epsg, name=name, datum=datum, zone=zone, hemi=hemi,
        )
        self._update_info_display()
        if self._on_crs_changed:
            self._on_crs_changed(self._current_crs)

    # ── Display ──

    def _update_info_display(self):
        self._info_text.configure(
            text=self._format_crs_info(self._current_crs),
        )

    def _format_crs_info(self, crs: CRSConfig) -> str:
        lines = [
            f"Name:       {crs.display_name or 'N/A'}",
            f"EPSG Code:  {crs.epsg_code}",
            f"Datum:      {crs.datum_name}",
        ]
        if crs.is_utm:
            lines.append(f"UTM Zone:   {crs.utm_zone}{crs.hemisphere}")
            cm = (crs.utm_zone * 6) - 183
            lines.append(f"Central M.: {cm} E")
            lines.append(f"Hemisphere: {'Northern' if crs.hemisphere == 'N' else 'Southern'}")
        else:
            lines.append(f"Type:       Projected (non-UTM)")
        return "\n".join(lines)

    def _preview_conversion(self):
        try:
            e = float(self._sample_e.get())
            n = float(self._sample_n.get())
        except ValueError:
            self._preview_label.configure(
                text="Invalid coordinate values",
                text_color=COLORS["error"],
            )
            return

        try:
            from ...engine.crs.transformer import CRSTransformer
            from ...engine.crs.dms_formatter import format_latitude, format_longitude

            tx = CRSTransformer(self._current_crs)
            lat, lon = tx.utm_to_latlon(e, n)

            lat_dms = format_latitude(lat)
            lon_dms = format_longitude(lon)

            result = (
                f"CRS ({self._current_crs.epsg_code}) -> WGS-84:\n"
                f"  Easting:   {e:.1f}    Northing: {n:.1f}\n"
                f"  Latitude:  {lat:.8f}  ({lat_dms})\n"
                f"  Longitude: {lon:.8f}  ({lon_dms})"
            )
            self._preview_label.configure(
                text=result, text_color=COLORS["success"],
            )
        except Exception as exc:
            self._preview_label.configure(
                text=f"Error: {exc}",
                text_color=COLORS["error"],
            )

    # ── Public API ──

    def set_crs_changed_callback(self, callback):
        """Set callback(crs_config) for CRS change events."""
        self._on_crs_changed = callback

    def get_crs_config(self) -> CRSConfig:
        return self._current_crs

    def set_crs_config(self, crs_dict: dict):
        """Restore CRS from a profile dict.

        Args:
            crs_dict: dict with utm_zone, hemisphere, epsg_code,
                      display_name, datum_name
        """
        if not crs_dict:
            return
        epsg = crs_dict.get("epsg_code", 32652)
        zone = crs_dict.get("utm_zone", 52)
        hemi = crs_dict.get("hemisphere", "N")
        name = crs_dict.get("display_name", f"EPSG:{epsg}")
        datum = crs_dict.get("datum_name", "WGS-84")

        self._current_crs = CRSConfig.from_preset(
            epsg=epsg, name=name, datum=datum, zone=zone, hemi=hemi,
        )

        # Try to select the matching region/preset in the UI
        found_region = None
        found_label = None
        for region, presets in CRS_PRESETS.items():
            for p in presets:
                if p[1] == epsg:
                    found_region = region
                    found_label = p[0]
                    break
            if found_region:
                break

        if found_region:
            self._region_seg.set(found_region)
            self._on_region_select(found_region)
            if found_label:
                self._preset_menu.set(found_label)
        else:
            # Custom EPSG
            self._region_seg.set("Custom")
            self._on_region_select("Custom")
            self._epsg_entry.delete(0, "end")
            self._epsg_entry.insert(0, str(epsg))

        self._update_info_display()
        if self._on_crs_changed:
            self._on_crs_changed(self._current_crs)
