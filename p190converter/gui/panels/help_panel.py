"""Help panel — P190 format guide and usage instructions."""

import customtkinter as ctk

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard, StatCard


# ── Quick Start cards with icons ──
WORKFLOW_STEPS_B = [
    ("\U0001f4c2", "1. Select Mode", "Choose 'Style B: RadExPro Export'"),
    ("\U0001f4c4", "2. Load File", "Browse for RadExPro Marine Geometry export (.txt)"),
    ("\u270f\ufe0f", "3. Line Name", "Enter line name for P190 header"),
    ("\U0001f310", "4. CRS Setup", "Set UTM zone in CRS panel (default: 52N)"),
    ("\u25b6\ufe0f", "5. Convert", "Click Convert button at sidebar bottom"),
]

WORKFLOW_STEPS_A = [
    ("\U0001f4c2", "1. Load NPD", "Browse for NPD navigation file"),
    ("\U0001f4e1", "2. GPS Source", "Select Front/Tail GPS from auto-detected list"),
    ("\u2699\ufe0f", "3. Geometry", "Configure offsets in Geometry panel"),
    ("\U0001f310", "4. CRS Setup", "Set UTM zone in CRS panel"),
    ("\u25b6\ufe0f", "5. Convert", "Click Convert button"),
]

SHORTCUTS = [
    ("Ctrl+O", "Open input file"),
    ("Ctrl+S", "Quick save settings"),
    ("F5", "Run conversion"),
    ("Ctrl+L", "Switch to Log panel"),
]

HELP_SECTIONS = [
    ("P190 Record Format", [
        "H Record: Header information (survey, datum, projection)",
        "S Record: Source (shot) position - 80 columns fixed width",
        "  Col  1     : 'S'",
        "  Col  2-16  : Line name (15 chars, left-justified)",
        "  Col  20-25 : Point# = FFID (I6, right-justified)",
        "  Col  26-35 : Latitude (DDMMSS.SSN/S)",
        "  Col  36-46 : Longitude (DDDMMSS.SSE/W)",
        "  Col  47-55 : Easting (F9.1)",
        "  Col  56-64 : Northing (F9.1)",
        "  Col  65-70 : Depth (F6.1)",
        "  Col  71-73 : Julian Day (I3)",
        "  Col  74-79 : Time (HHMMSS)",
        "",
        "R Record: Receiver group position - 3 groups per line",
        "  Each group (26 chars): CH#(I4) + Easting(F9.1) + Northing(F9.1) + Depth(F4.1)",
        "  48 channels = 16 R record lines per shot",
    ]),
    ("CRS / Coordinate System", [
        "P190 requires both UTM and Geographic (Lat/Lon DMS) coordinates.",
        "pyproj is used for UTM <-> WGS-84 transformation.",
        "",
        "Common UTM zones for Korean waters:",
        "  UTM 51N (EPSG:32651) - West coast",
        "  UTM 52N (EPSG:32652) - South/East coast (Ulsan, Busan)",
        "  UTM 53N (EPSG:32653) - East coast (Dokdo area)",
    ]),
    ("RadExPro Import Tips", [
        "If FFID exceeds 6 digits or full-precision UTM is required, prefer the companion *_RadEx_Geometry.tsv file.",
        "RadExPro Geometry Spreadsheet -> Tools/Import can match FFID and CHAN, then assign SOU_X, SOU_Y, REC_X, REC_Y.",
        "Use direct P190 import only when the 6-char point number and 0.1 m grid precision are acceptable.",
    ]),
    ("Interpolation Methods (Style A)", [
        "Linear (default): Standard RadExPro method.",
        "  Suitable for 48ch UHR (~150m cable), error < 2m.",
        "",
        "Catenary: Physics-based cable shape model.",
        "  For deep water / long streamers (>5km).",
        "",
        "Spline: Cubic spline interpolation.",
        "  For irregular trace distributions / 3D regularization.",
        "",
        "Feathering: Head/Tail Buoy GPS power-law cable curvature.",
        "  Cross-current displacement: d(t) = C * (t^a - t)",
        "  Requires NPD with Head + Tail Buoy GPS (Style A only).",
    ]),
]


class HelpPanel(ctk.CTkFrame):
    """Panel displaying help information with visual workflow cards."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._build()

    def _build(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color=COLORS["bg_input"],
            scrollbar_button_color=COLORS["accent_muted"],
            scrollbar_button_hover_color=COLORS["accent"],
        )
        scroll.pack(fill="both", expand=True)

        # ── About Card ──
        about_card = SectionCard(scroll, title="P190 NavConverter")
        about_card.pack(fill="x", pady=(0, SP["md"]))

        about_text = ctk.CTkLabel(
            about_card,
            text="Converts marine seismic navigation data to UKOOA P1/90 format.\n"
                 "Compatible with RadExPro 'Import UKOOA P1-90' module.\n"
                 "Also exports a full-precision RadEx geometry TSV sidecar for ASCII import.\n\n"
                 "Two conversion styles supported:\n"
                 "  Style A: NPD real GPS + Marine Geometry -> interpolated receivers\n"
                 "  Style B: RadExPro Marine Geometry header export (SOU_X/Y, REC_X/Y)",
            font=font("body"),
            text_color=COLORS["text_secondary"],
            anchor="w",
            justify="left",
        )
        about_text.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # ── Quick Start Style B — Visual Cards ──
        card_b = SectionCard(scroll, title="Quick Start - Style B")
        card_b.pack(fill="x", pady=(0, SP["md"]))

        steps_frame_b = ctk.CTkFrame(card_b, fg_color="transparent")
        steps_frame_b.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        for i, (icon, title, desc) in enumerate(WORKFLOW_STEPS_B):
            step = StatCard(
                steps_frame_b, icon=icon,
                value=title, label=desc,
                accent_index=i % 4,
            )
            step.pack(fill="x", pady=2)

        # ── Quick Start Style A — Visual Cards ──
        card_a = SectionCard(scroll, title="Quick Start - Style A")
        card_a.pack(fill="x", pady=(0, SP["md"]))

        steps_frame_a = ctk.CTkFrame(card_a, fg_color="transparent")
        steps_frame_a.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        for i, (icon, title, desc) in enumerate(WORKFLOW_STEPS_A):
            step = StatCard(
                steps_frame_a, icon=icon,
                value=title, label=desc,
                accent_index=i % 4,
            )
            step.pack(fill="x", pady=2)

        # ── Keyboard Shortcuts Card ──
        kb_card = SectionCard(scroll, title="Keyboard Shortcuts")
        kb_card.pack(fill="x", pady=(0, SP["md"]))

        kb_inner = ctk.CTkFrame(kb_card, fg_color="transparent")
        kb_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        for shortcut, desc in SHORTCUTS:
            row = ctk.CTkFrame(kb_inner, fg_color="transparent", height=28)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            key_lbl = ctk.CTkLabel(
                row, text=shortcut, width=80,
                font=mono_font(),
                fg_color=COLORS["bg_input"],
                text_color=COLORS["accent"],
                corner_radius=4,
            )
            key_lbl.pack(side="left", padx=(0, SP["sm"]))

            ctk.CTkLabel(
                row, text=desc,
                font=font("body"),
                text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        # ── Technical Reference Cards ──
        for title, lines in HELP_SECTIONS:
            card = SectionCard(scroll, title=title)
            card.pack(fill="x", pady=(0, SP["md"]))

            text = "\n".join(lines)
            lbl = ctk.CTkLabel(
                card,
                text=text,
                font=mono_font(),
                text_color=COLORS["text_secondary"],
                anchor="w",
                justify="left",
            )
            lbl.pack(
                fill="x", padx=SP["md"], pady=(0, SP["md"]),
            )
