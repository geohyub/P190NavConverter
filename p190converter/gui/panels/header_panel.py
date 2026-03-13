"""Header panel — P190 H Record editor with structured form.

Instead of raw H-code editing, provides human-readable form fields
grouped by category, which auto-generate the correct H record codes.
CRS-related fields auto-sync from the CRS panel.
Bottom section shows raw H Record preview for verification.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import COLORS, SP, CORNER_RADIUS, font, mono_font
from ..widgets import SectionCard
from ...models.survey_config import HRecordConfig
from ...utils.settings import load_h_template, save_h_template


# ──────────────────────────────────────────────────────────────
# Form field definitions: (label, h_code, placeholder, category)
# ──────────────────────────────────────────────────────────────
FORM_FIELDS = [
    # ── Project Information ──
    ("Survey Area",              "H0100", "e.g. East Sea Block 6-1",        "Project"),
    ("Client",                   "H0300", "e.g. JAKO Offshore",             "Project"),
    ("Geophysical Contractor",   "H0400", "e.g. GeoView Co., Ltd.",         "Project"),
    ("Positioning Contractor",   "H0500", "e.g. GeoView Co., Ltd.",         "Project"),
    ("Positioning Processing",   "H0600", "e.g. NaviPac / RadExPro",        "Project"),
    # ── Vessel & Equipment ──
    ("Vessel Details",           "H0102", "e.g. R/V GeoExplorer",           "Vessel"),
    ("Source Details",           "H0103", "e.g. SBP Innomar SES-2000",      "Vessel"),
    ("Streamer Details",         "H0104", "e.g. Single streamer 150m",      "Vessel"),
    ("Positioning System",       "H0700", "e.g. Differential GPS C-Nav",    "Vessel"),
    # ── Survey Details ──
    ("Survey Date",              "H0200", "e.g. 01-JAN-2025 to 28-FEB-2025","Survey"),
    ("Tape Date (D.M.Y.)",       "H0201", "e.g. 15.03.2025",               "Survey"),
    ("Tape Version",             "H0202", "UKOOA-P1/90",                    "Survey"),
    ("Shotpoint Position",       "H0800", "e.g. Centre of source",          "Survey"),
    ("Offset Ship to SP",        "H0900", "e.g. Stern -10.0m",             "Survey"),
    ("Clock Time",               "H1000", "GMT",                            "Survey"),
]

# CRS-related fields (auto-synced, read-only)
CRS_FIELDS = [
    ("Geodetic Datum (Surveyed)","H1400", "Auto-filled from CRS panel",     "CRS"),
    ("Geodetic Datum (Plotted)", "H1500", "Auto-filled from CRS panel",     "CRS"),
    ("Vertical Datum",           "H1700", "e.g. MSL / LAT / Chart Datum",  "CRS"),
    ("Projection",               "H1800", "Auto-filled from CRS panel",     "CRS"),
    ("Zone",                     "H1900", "Auto-filled from CRS panel",     "CRS"),
    ("Grid Units",               "H2000", "",                               "CRS"),
    ("Height Units",             "H2001", "",                               "CRS"),
    ("Angular Units",            "H2002", "",                               "CRS"),
    ("Central Meridian",         "H2200", "Auto-filled from CRS panel",     "CRS"),
    ("Data Unloader",            "H2600", "UKOOA P1/90 FORMAT",             "CRS"),
]

# H codes that are auto-filled from CRS panel (user shouldn't edit)
CRS_AUTO_CODES = {"H1400", "H1500", "H1800", "H1900", "H2200"}


class HeaderPanel(ctk.CTkFrame):
    """Panel for editing P190 H Record header lines with structured form."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._entries = {}       # h_code -> CTkEntry
        self._h_config = HRecordConfig()
        self._build()

    def _build(self):
        # Main scrollable container
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_input"],
            scrollbar_button_color=COLORS["accent_muted"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        self._scroll.pack(fill="both", expand=True)

        # ── Template Controls ──
        ctrl_card = SectionCard(self._scroll, title="Template Management")
        ctrl_card.pack(fill="x", pady=(0, SP["md"]))

        ctrl_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._template_name = ctk.CTkEntry(
            ctrl_frame,
            placeholder_text="Template name (e.g. JAKO_2025)",
            width=200,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self._template_name.pack(side="left", padx=(0, SP["sm"]))

        for text, cmd, fg, hover in [
            ("Save",  self._save_template,  COLORS["accent_muted"], COLORS["accent"]),
            ("Load",  self._load_template,  COLORS["bg_input"],     COLORS["sidebar_hover"]),
            ("Reset", self._reset_defaults, COLORS["bg_input"],     COLORS["sidebar_hover"]),
        ]:
            btn = ctk.CTkButton(
                ctrl_frame, text=text, width=80,
                font=font("body"),
                fg_color=fg,
                hover_color=hover,
                text_color=COLORS["text_primary"],
                corner_radius=6,
                command=cmd,
            )
            btn.pack(side="left", padx=(0, SP["xs"]))

        # ── Form sections by category ──
        categories = [
            ("Project",  "Project Information",       FORM_FIELDS),
            ("Vessel",   "Vessel & Equipment",        FORM_FIELDS),
            ("Survey",   "Survey Details",            FORM_FIELDS),
            ("CRS",      "Geodetic / CRS (auto-sync available)", CRS_FIELDS),
        ]

        for cat_key, cat_title, field_list in categories:
            card = SectionCard(self._scroll, title=cat_title)
            card.pack(fill="x", pady=(0, SP["sm"]))

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

            for label, h_code, placeholder, cat in (
                field_list if cat_key == "CRS" else FORM_FIELDS
            ):
                if cat != cat_key:
                    continue
                self._build_field_row(inner, label, h_code, placeholder)

        # ── Raw H Record Preview ──
        preview_card = SectionCard(self._scroll, title="Raw H Record Output Preview")
        preview_card.pack(fill="x", pady=(SP["sm"], 0))

        self._preview_text = ctk.CTkTextbox(
            preview_card,
            height=200,
            font=mono_font(),
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            state="disabled",
        )
        self._preview_text.pack(
            fill="x", padx=SP["md"], pady=(0, SP["md"]),
        )

        refresh_btn = ctk.CTkButton(
            preview_card, text="Refresh Preview", width=140,
            font=font("body"),
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._refresh_preview,
        )
        refresh_btn.pack(pady=(0, SP["md"]))

        # Populate entries from defaults
        self._load_from_config(self._h_config)

    def _build_field_row(self, parent, label: str, h_code: str,
                          placeholder: str):
        """Build a single form field row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)

        # H code badge
        badge = ctk.CTkLabel(
            row, text=h_code, width=55,
            font=mono_font(),
            text_color=COLORS["accent"],
            fg_color=COLORS["accent_dim"],
            corner_radius=4,
            padx=4,
        )
        badge.pack(side="left", padx=(0, SP["xs"]))

        # Label
        lbl = ctk.CTkLabel(
            row, text=label, width=180,
            font=font("body"),
            text_color=COLORS["text_secondary"],
            anchor="e",
        )
        lbl.pack(side="left", padx=(0, SP["sm"]))

        # Entry
        is_auto = h_code in CRS_AUTO_CODES
        entry = ctk.CTkEntry(
            row,
            placeholder_text=placeholder,
            font=mono_font(),
            fg_color=COLORS["bg_input"] if not is_auto else COLORS["bg_secondary"],
            text_color=COLORS["text_primary"] if not is_auto else COLORS["text_muted"],
            border_color=COLORS["border"] if not is_auto else COLORS["accent_dim"],
            corner_radius=4,
            state="normal",
        )
        entry.pack(side="left", fill="x", expand=True)

        if is_auto:
            auto_tag = ctk.CTkLabel(
                row, text="AUTO",
                font=font("small"),
                text_color=COLORS["accent"],
                fg_color=COLORS["accent_dim"],
                corner_radius=4,
                width=42,
                padx=4,
            )
            auto_tag.pack(side="left", padx=(SP["xs"], 0))

        self._entries[h_code] = entry

    # ── Data Loading ──

    def _load_from_config(self, config: HRecordConfig):
        """Populate form entries from HRecordConfig."""
        for h_code, entry in self._entries.items():
            entry.configure(state="normal")
            entry.delete(0, "end")
            # Get content: strip the fixed-width label prefix
            raw = config.records.get(h_code, "")
            # H record content is after the H-code label text
            # e.g. "SURVEY AREA               East Sea Block"
            # We need to extract user-editable part
            content = self._extract_content(h_code, raw)
            if content:
                entry.insert(0, content)

    def _extract_content(self, h_code: str, raw: str) -> str:
        """Extract user-editable content from raw H record value.

        H record values in HRecordConfig have format:
            "LABEL_TEXT                 user_content"
        We need to strip the standard label prefix.
        """
        # Map H codes to their standard label prefixes
        label_map = {
            "H0100": "SURVEY AREA",
            "H0102": "VESSEL DETAILS",
            "H0103": "SOURCE DETAILS",
            "H0104": "STREAMER DETAILS",
            "H0200": "SURVEY DATE",
            "H0201": "TAPE DATE (D.M.Y.)",
            "H0202": "TAPE VERSION",
            "H0300": "CLIENT",
            "H0400": "GEOPHYSICAL CONTRACTOR",
            "H0500": "POSITIONING CONTRACTOR",
            "H0600": "POSITIONING PROCESSING",
            "H0700": "POSITIONING SYSTEM",
            "H0800": "SHOTPOINT POSITION",
            "H0900": "OFFSET SHIP SYSTEM TO SP",
            "H1000": "CLOCK TIME",
            "H1400": "GEODETIC DATUM AS SURVEYED",
            "H1500": "GEODETIC DATUM AS PLOTTED",
            "H1700": "VERTICAL DATUM",
            "H1800": "PROJECTION",
            "H1900": "ZONE",
            "H2000": "GRID UNITS",
            "H2001": "HEIGHT UNITS",
            "H2002": "ANGULAR UNITS",
            "H2200": "CENTRAL MERIDIAN",
            "H2600": "SEISMIC DATA UNLOADER",
        }
        prefix = label_map.get(h_code, "")
        if prefix and raw.startswith(prefix):
            content = raw[len(prefix):].strip()
            return content
        return raw.strip()

    # ── Config Generation ──

    def _build_h_record_value(self, h_code: str, user_content: str) -> str:
        """Build full H record value from user content.

        Format: "FIXED_LABEL_TEXT          user_content"
        The fixed label is left-padded to 26 chars, then user content follows.
        """
        label_map = {
            "H0100": "SURVEY AREA",
            "H0102": "VESSEL DETAILS",
            "H0103": "SOURCE DETAILS",
            "H0104": "STREAMER DETAILS",
            "H0200": "SURVEY DATE",
            "H0201": "TAPE DATE (D.M.Y.)",
            "H0202": "TAPE VERSION",
            "H0300": "CLIENT",
            "H0400": "GEOPHYSICAL CONTRACTOR",
            "H0500": "POSITIONING CONTRACTOR",
            "H0600": "POSITIONING PROCESSING",
            "H0700": "POSITIONING SYSTEM",
            "H0800": "SHOTPOINT POSITION",
            "H0900": "OFFSET SHIP SYSTEM TO SP",
            "H1000": "CLOCK TIME",
            "H1400": "GEODETIC DATUM AS SURVEYED",
            "H1500": "GEODETIC DATUM AS PLOTTED",
            "H1700": "VERTICAL DATUM",
            "H1800": "PROJECTION",
            "H1900": "ZONE",
            "H2000": "GRID UNITS",
            "H2001": "HEIGHT UNITS",
            "H2002": "ANGULAR UNITS",
            "H2200": "CENTRAL MERIDIAN",
            "H2600": "SEISMIC DATA UNLOADER",
        }
        prefix = label_map.get(h_code, "")
        if prefix:
            padded = prefix.ljust(26)
            return f"{padded}{user_content}"
        return user_content

    def _get_current_records(self) -> dict:
        """Build HRecordConfig records dict from form entries."""
        records = {}
        for h_code, entry in self._entries.items():
            user_content = entry.get().strip()
            records[h_code] = self._build_h_record_value(h_code, user_content)
        return records

    # ── Template Management ──

    def _save_template(self):
        name = self._template_name.get().strip()
        if not name:
            messagebox.showwarning("Save Template",
                                   "Enter a template name first.")
            return
        records = self._get_current_records()
        save_h_template(name, records)
        messagebox.showinfo("Save Template",
                            f"Template '{name}' saved successfully.")

    def _load_template(self):
        name = self._template_name.get().strip()
        if not name:
            messagebox.showwarning("Load Template",
                                   "Enter a template name to load.")
            return
        records = load_h_template(name)
        if not records:
            messagebox.showwarning("Load Template",
                                   f"Template '{name}' not found.")
            return
        self._h_config.records = records
        self._load_from_config(self._h_config)

    def _reset_defaults(self):
        self._h_config = HRecordConfig()
        self._load_from_config(self._h_config)

    # ── Preview ──

    def _refresh_preview(self):
        """Generate and display raw H record lines."""
        records = self._get_current_records()
        lines = []
        for code in sorted(records.keys()):
            content = records[code]
            line = f"{code} {content}"
            line = line.ljust(80)[:80]
            lines.append(line)

        preview = "\n".join(lines)
        preview += f"\n\n--- {len(lines)} H records, all 80 columns ---"

        self._preview_text.configure(state="normal")
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("1.0", preview)
        self._preview_text.configure(state="disabled")

    # ── Public API ──

    def get_h_record_config(self) -> HRecordConfig:
        """Return HRecordConfig from current editor state."""
        records = self._get_current_records()
        return HRecordConfig(records=records)

    def set_h_records(self, records_dict: dict):
        """Restore H records from a profile dict.

        Args:
            records_dict: dict of h_code -> record value string
        """
        if not records_dict:
            return
        config = HRecordConfig(records=records_dict)
        self._load_from_config(config)
        self._refresh_preview()

    def apply_crs_to_records(self, crs_config):
        """Update CRS-related H records from CRS panel.

        Auto-fills H1400, H1500, H1800, H1900, H2200.
        """
        h = self.get_h_record_config()
        h.apply_crs(crs_config)
        self._h_config = h
        # Update only CRS auto-fields in the form
        for h_code in CRS_AUTO_CODES:
            if h_code in self._entries and h_code in h.records:
                entry = self._entries[h_code]
                entry.configure(state="normal")
                entry.delete(0, "end")
                content = self._extract_content(h_code, h.records[h_code])
                entry.insert(0, content)
