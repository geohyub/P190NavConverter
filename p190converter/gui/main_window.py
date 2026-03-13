"""Main application window — CustomTkinter."""

import customtkinter as ctk

from .theme import COLORS, SP, SIDEBAR_WIDTH, WINDOW_MIN_W, WINDOW_MIN_H, font
from .widgets import SidebarButton, StatusBar, StepIndicator


# Panels that require Style A (disabled when Style B is active)
STYLE_A_ONLY_PANELS = {"geometry", "feathering"}


class MainWindow(ctk.CTk):
    """P190 NavConverter main window with sidebar navigation."""

    NAV_ITEMS = [
        # -- Pre-conversion setup (workflow order) --
        ("input",      "📂", "Input"),         # Folder icon
        ("header",     "📐", "Header"),         # Triangular ruler
        ("crs",        "🌐", "CRS"),            # Globe
        ("geometry",   "⚙️", "Geometry"),     # Gear (Style A only)
        ("preview",    "🗺️", "Preview"),  # World map
        # -- Post-conversion outputs --
        ("log",        "📋", "Log"),            # Clipboard
        ("results",    "📊", "Results"),         # Chart
        ("feathering", "🌊", "Feathering"),     # Wave (Style A only)
        ("comparison", "🔍", "Compare"),        # Magnifier (A vs B)
        ("help",       "❓",     "Help"),            # Question mark
    ]

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("P190 NavConverter v1.0")
        self.geometry(f"{WINDOW_MIN_W}x{WINDOW_MIN_H}")
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.configure(fg_color=COLORS["bg_primary"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # High DPI
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self._panels = {}
        self._active_panel = None
        self._sidebar_buttons = {}
        self._current_style = "B"

        self._build_layout()

    def _build_layout(self):
        """Build main layout: header + sidebar + content + status bar."""

        # ── Header bar (title + mode badge + file status) ──
        self._header = ctk.CTkFrame(
            self, fg_color=COLORS["bg_secondary"],
            height=48, corner_radius=0,
        )
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        # Left: Title
        title_label = ctk.CTkLabel(
            self._header,
            text="  P190 NavConverter",
            font=font("h2", bold=True),
            text_color=COLORS["accent"],
        )
        title_label.pack(side="left", padx=(SP["md"], SP["xs"]))

        version_label = ctk.CTkLabel(
            self._header,
            text="v1.0",
            font=font("small"),
            text_color=COLORS["text_muted"],
        )
        version_label.pack(side="left", padx=(0, SP["lg"]))

        # Center: Mode badge (current style)
        self._mode_badge = ctk.CTkLabel(
            self._header,
            text="  Style B : RadExPro Export  ",
            font=font("small", bold=True),
            text_color=COLORS["accent"],
            fg_color=COLORS["accent_dim"],
            corner_radius=12,
            padx=12,
            height=26,
        )
        self._mode_badge.pack(side="left", padx=SP["sm"])

        # Right: File status
        self._file_status = ctk.CTkLabel(
            self._header,
            text="No file loaded",
            font=font("small"),
            text_color=COLORS["text_muted"],
        )
        self._file_status.pack(side="right", padx=SP["md"])

        # ── Pipeline Step Indicator (hidden until conversion) ──
        self._step_indicator = StepIndicator(self)
        self._step_visible = False
        # NOT packed — will show during conversion via show_step_indicator()

        # ── Main body: Sidebar + Content ──
        self._body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = ctk.CTkFrame(
            self._body,
            fg_color=COLORS["sidebar_bg"],
            width=SIDEBAR_WIDTH,
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar nav buttons
        for nav_id, icon, tooltip in self.NAV_ITEMS:
            btn = SidebarButton(
                sidebar, icon=icon, tooltip=tooltip,
                command=lambda nid=nav_id: self.show_panel(nid),
            )
            btn.pack(fill="x", pady=1)
            self._sidebar_buttons[nav_id] = btn

        # Spacer
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Convert button at sidebar bottom
        self._convert_btn = ctk.CTkButton(
            sidebar,
            text="\u25b6",  # Play symbol
            width=SIDEBAR_WIDTH - 8,
            height=40,
            font=("Segoe UI", 18),
            fg_color=COLORS["button_primary"],
            hover_color=COLORS["button_hover"],
            text_color=COLORS["button_text"],
            corner_radius=8,
        )
        self._convert_btn.pack(pady=SP["sm"], padx=4)

        # Content area
        self._content = ctk.CTkFrame(
            self._body, fg_color=COLORS["bg_primary"], corner_radius=0,
        )
        self._content.pack(side="left", fill="both", expand=True)

        # ── Status bar ──
        self._status_bar = StatusBar(self)
        self._status_bar.pack(fill="x", side="bottom")

        # Apply initial Style B state (disable Geometry for Style B)
        self.set_style_mode("B")

    def register_panel(self, panel_id: str, panel_widget):
        """Register a panel widget for sidebar navigation."""
        self._panels[panel_id] = panel_widget
        panel_widget.pack_forget()

    def show_panel(self, panel_id: str):
        """Switch to a panel by ID."""
        # Block disabled panels
        if panel_id in STYLE_A_ONLY_PANELS:
            btn = self._sidebar_buttons.get(panel_id)
            if btn and not btn._enabled:
                return

        if self._active_panel and self._active_panel in self._panels:
            self._panels[self._active_panel].pack_forget()

        # Update sidebar button states
        for nid, btn in self._sidebar_buttons.items():
            btn.set_active(nid == panel_id)

        if panel_id in self._panels:
            self._panels[panel_id].pack(
                in_=self._content,
                fill="both", expand=True,
                padx=SP["lg"], pady=SP["lg"],
            )
            self._active_panel = panel_id

    def set_convert_command(self, command):
        """Set the convert button command."""
        self._convert_btn.configure(command=command)

    def set_style_mode(self, style: str):
        """Update header badge and sidebar states for Style A/B."""
        self._current_style = style
        if style == "A":
            self._mode_badge.configure(
                text="  Style A : NPD + Geometry  ",
            )
            for pid in STYLE_A_ONLY_PANELS:
                btn = self._sidebar_buttons.get(pid)
                if btn:
                    btn.set_enabled(True)
        else:
            self._mode_badge.configure(
                text="  Style B : RadExPro Export  ",
            )
            for pid in STYLE_A_ONLY_PANELS:
                btn = self._sidebar_buttons.get(pid)
                if btn:
                    btn.set_enabled(False, "Style A only (NPD + Geometry)")

            # Redirect if currently viewing a disabled panel
            if self._active_panel in STYLE_A_ONLY_PANELS:
                self.show_panel("input")

    def set_file_status(self, text: str):
        """Update file status indicator in header bar."""
        self._file_status.configure(text=text)

    def show_step_indicator(self):
        """Show pipeline step indicator (during conversion)."""
        if not self._step_visible:
            self._step_indicator.pack(fill="x", before=self._body)
            self._step_visible = True

    def hide_step_indicator(self):
        """Hide pipeline step indicator."""
        if self._step_visible:
            self._step_indicator.pack_forget()
            self._step_visible = False

    @property
    def status_bar(self) -> StatusBar:
        return self._status_bar

    @property
    def step_indicator(self) -> StepIndicator:
        return self._step_indicator
