"""Input panel — File selection + Style A/B mode switch."""

import customtkinter as ctk
from tkinter import filedialog

from ..theme import COLORS, SP, CORNER_RADIUS, font
from ..widgets import SectionCard, FormField, FileDropZone, StatCard


class InputPanel(ctk.CTkFrame):
    """Panel for file input configuration and style selection."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_file_loaded = None
        self._on_style_changed = None
        self._on_profile_save = None
        self._on_profile_load = None
        self._on_profile_delete = None
        self._batch_mode = False
        self._batch_files = []
        self._build()

    def _build(self):
        # ── Profile Management Card ──
        profile_card = SectionCard(self, title="Profile")
        profile_card.pack(fill="x", pady=(0, SP["md"]))

        prof_inner = ctk.CTkFrame(profile_card, fg_color="transparent")
        prof_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # Row 1: Profile selector + Load/Delete
        row1 = ctk.CTkFrame(prof_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, SP["xs"]))

        ctk.CTkLabel(
            row1, text="Profile:", width=60,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["xs"]))

        self._profile_menu = ctk.CTkOptionMenu(
            row1,
            values=["(No profiles)"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_muted"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_elevated"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["sidebar_hover"],
            corner_radius=6,
            width=200,
        )
        self._profile_menu.pack(side="left", padx=(0, SP["xs"]))

        self._btn_load_profile = ctk.CTkButton(
            row1, text="Load",
            font=font("small"), width=60, height=28,
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._load_profile,
        )
        self._btn_load_profile.pack(side="left", padx=(0, SP["xs"]))

        self._btn_delete_profile = ctk.CTkButton(
            row1, text="Delete",
            font=font("small"), width=60, height=28,
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["error"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            command=self._delete_profile,
        )
        self._btn_delete_profile.pack(side="left")

        # Row 2: Name entry + Save
        row2 = ctk.CTkFrame(prof_inner, fg_color="transparent")
        row2.pack(fill="x")

        ctk.CTkLabel(
            row2, text="Name:", width=60,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["xs"]))

        self._profile_name_entry = ctk.CTkEntry(
            row2, width=200,
            placeholder_text="Enter profile name...",
            font=font("body"),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self._profile_name_entry.pack(side="left", padx=(0, SP["xs"]))

        self._btn_save_profile = ctk.CTkButton(
            row2, text="Save",
            font=font("small"), width=60, height=28,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._save_profile,
        )
        self._btn_save_profile.pack(side="left")

        # ── Mode Selection Card ──
        mode_card = SectionCard(self, title="Conversion Mode")
        mode_card.pack(fill="x", pady=(0, SP["md"]))

        mode_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
        mode_frame.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._mode_var = ctk.StringVar(value="B")
        self._mode_seg = ctk.CTkSegmentedButton(
            mode_frame,
            values=["Style A: NPD + Geometry", "Style B: RadExPro Export"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_input"],
            unselected_hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            text_color_disabled=COLORS["text_muted"],
            corner_radius=6,
            command=self._on_mode_change,
        )
        self._mode_seg.set("Style B: RadExPro Export")
        self._mode_seg.pack(fill="x")

        desc_lbl = ctk.CTkLabel(
            mode_frame,
            text="Style B: RadExPro Marine Geometry header export (SOU_X/Y, REC_X/Y) -> P190",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(SP["xs"], 0))
        self._mode_desc = desc_lbl

        # Batch mode checkbox
        batch_row = ctk.CTkFrame(mode_frame, fg_color="transparent")
        batch_row.pack(fill="x", pady=(SP["xs"], 0))

        self._batch_var = ctk.BooleanVar(value=False)
        self._batch_check = ctk.CTkCheckBox(
            batch_row,
            text="Batch Mode (multi-file processing)",
            variable=self._batch_var,
            font=font("body"),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            corner_radius=4,
            command=self._on_batch_toggle,
        )
        self._batch_check.pack(side="left")

        # Batch file list label (hidden by default)
        self._batch_info = ctk.CTkLabel(
            mode_frame,
            text="",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )

        # ── Style B Input Card ──
        self._style_b_card = SectionCard(self, title="Style B - RadExPro Export Input")
        self._style_b_card.pack(fill="x", pady=(0, SP["md"]))

        b_inner = ctk.CTkFrame(self._style_b_card, fg_color="transparent")
        b_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # FileDropZone for RadExPro file
        self._radex_drop = FileDropZone(
            b_inner, label="Click to select RadExPro export file",
            browse_callback=self._browse_radex,
        )
        self._radex_drop.pack(fill="x", pady=(0, SP["sm"]))

        self._line_name_b = FormField(
            b_inner, label="Line Name",
            default="Ulsan_Line021-1",
        )
        self._line_name_b.pack(fill="x", pady=SP["xs"])

        self._output_dir_b = FormField(
            b_inner, label="Output Dir",
            browse=True, browse_callback=self._browse_output_b,
        )
        self._output_dir_b.pack(fill="x", pady=SP["xs"])

        self._radex_decimals_b = FormField(
            b_inner, label="RadEx Decimals",
            default="5", width=80,
        )
        self._radex_decimals_b.pack(fill="x", pady=SP["xs"])

        # ── Style A Input Card (hidden by default) ──
        self._style_a_card = SectionCard(self, title="Style A - NPD + Track Input")

        a_inner = ctk.CTkFrame(self._style_a_card, fg_color="transparent")
        a_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # FileDropZone for NPD
        self._npd_drop = FileDropZone(
            a_inner, label="Click to select NPD file",
            browse_callback=self._browse_npd,
        )
        self._npd_drop.pack(fill="x", pady=(0, SP["xs"]))

        # FileDropZone for Track
        self._track_drop = FileDropZone(
            a_inner, label="Click to select Track file",
            browse_callback=self._browse_track,
        )
        self._track_drop.pack(fill="x", pady=(0, SP["sm"]))

        self._line_name_a = FormField(
            a_inner, label="Line Name",
        )
        self._line_name_a.pack(fill="x", pady=SP["xs"])

        self._output_dir_a = FormField(
            a_inner, label="Output Dir",
            browse=True, browse_callback=self._browse_output_a,
        )
        self._output_dir_a.pack(fill="x", pady=SP["xs"])

        self._radex_decimals_a = FormField(
            a_inner, label="RadEx Decimals",
            default="5", width=80,
        )
        self._radex_decimals_a.pack(fill="x", pady=SP["xs"])

        # ── GPS Source Selection (Style A only) ──
        self._gps_card = SectionCard(self, title="GPS Source Selection")

        gps_inner = ctk.CTkFrame(self._gps_card, fg_color="transparent")
        gps_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        # Front GPS
        front_row = ctk.CTkFrame(gps_inner, fg_color="transparent")
        front_row.pack(fill="x", pady=SP["xs"])

        ctk.CTkLabel(
            front_row, text="Front GPS:", width=120,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["sm"]))

        self._front_gps = ctk.CTkOptionMenu(
            front_row,
            values=["(Load NPD file first)"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_muted"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_elevated"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["sidebar_hover"],
            corner_radius=6,
        )
        self._front_gps.pack(side="left", fill="x", expand=True)

        # Tail GPS
        tail_row = ctk.CTkFrame(gps_inner, fg_color="transparent")
        tail_row.pack(fill="x", pady=SP["xs"])

        ctk.CTkLabel(
            tail_row, text="Tail GPS:", width=120,
            font=font("body"), text_color=COLORS["text_secondary"],
            anchor="e",
        ).pack(side="left", padx=(0, SP["sm"]))

        self._tail_gps = ctk.CTkOptionMenu(
            tail_row,
            values=["(Load NPD file first)"],
            font=font("body"),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_muted"],
            button_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_elevated"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_hover_color=COLORS["sidebar_hover"],
            corner_radius=6,
        )
        self._tail_gps.pack(side="left", fill="x", expand=True)

        gps_info = ctk.CTkLabel(
            gps_inner,
            text="  NPD file load after auto-detected position sources are displayed.",
            font=font("small"),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        gps_info.pack(fill="x", pady=(SP["xs"], 0))

        # ── Quick Summary → StatCard row ──
        self._summary_card = SectionCard(self, title="Data Summary")
        self._summary_card.pack(fill="x", pady=(0, SP["md"]))

        stats_frame = ctk.CTkFrame(self._summary_card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._stat_shots = StatCard(
            stats_frame, icon="\U0001f4cd", value="--",
            label="Shots", accent_index=0,
        )
        self._stat_shots.pack(side="left", fill="x", expand=True, padx=(0, SP["xs"]))

        self._stat_channels = StatCard(
            stats_frame, icon="\U0001f50a", value="--",
            label="Channels", accent_index=1,
        )
        self._stat_channels.pack(side="left", fill="x", expand=True, padx=(0, SP["xs"]))

        self._stat_ffid = StatCard(
            stats_frame, icon="\U0001f522", value="--",
            label="FFID Range", accent_index=2,
        )
        self._stat_ffid.pack(side="left", fill="x", expand=True)

    def _on_mode_change(self, value: str):
        is_a = value.startswith("Style A")
        if is_a:
            self._style_b_card.pack_forget()
            self._summary_card.pack_forget()
            self._style_a_card.pack(fill="x", pady=(0, SP["md"]),
                                     after=self._mode_desc.master.master)
            self._summary_card.pack(fill="x", pady=(0, SP["md"]),
                                    after=self._style_a_card)
            self._gps_card.pack(fill="x", pady=(0, SP["md"]),
                                after=self._summary_card)
            self._mode_desc.configure(
                text="Style A: NPD real GPS + Marine Geometry -> interpolated receivers -> P190"
            )
        else:
            self._style_a_card.pack_forget()
            self._gps_card.pack_forget()
            self._summary_card.pack_forget()
            self._style_b_card.pack(fill="x", pady=(0, SP["md"]),
                                     after=self._mode_desc.master.master)
            self._summary_card.pack(fill="x", pady=(0, SP["md"]),
                                    after=self._style_b_card)
            self._mode_desc.configure(
                text="Style B: RadExPro Marine Geometry header export (SOU_X/Y, REC_X/Y) -> P190"
            )

        if self._on_style_changed:
            self._on_style_changed("A" if is_a else "B")

    def _browse_radex(self):
        if self._batch_mode:
            return self._browse_batch_radex()
        path = filedialog.askopenfilename(
            title="Select RadExPro Export File",
            filetypes=[("Text files", "*.txt"), ("TSV files", "*.tsv"),
                       ("All files", "*.*")],
        )
        if path:
            self._radex_drop.set_file(path)
            if self._on_file_loaded:
                self._on_file_loaded("radex", path)

    def _browse_npd(self):
        path = filedialog.askopenfilename(
            title="Select NPD File",
            filetypes=[("NPD files", "*.npd *.NPD"),
                       ("Nav files", "*.txt *.nav"),
                       ("All files", "*.*")],
        )
        if path:
            self._npd_drop.set_file(path)
            if self._on_file_loaded:
                self._on_file_loaded("npd", path)

    def _browse_track(self):
        path = filedialog.askopenfilename(
            title="Select Track File",
            filetypes=[("Text files", "*.txt"), ("TSV files", "*.tsv"),
                       ("All files", "*.*")],
        )
        if path:
            self._track_drop.set_file(path)
            if self._on_file_loaded:
                self._on_file_loaded("track", path)

    def _browse_output_b(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self._output_dir_b.value = path

    def _browse_output_a(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self._output_dir_a.value = path

    def set_file_loaded_callback(self, callback):
        """Set callback(file_type, path) for file load events."""
        self._on_file_loaded = callback

    def set_style_changed_callback(self, callback):
        """Set callback(style) for mode change events."""
        self._on_style_changed = callback

    def update_gps_sources(self, sources: list):
        """Update GPS source dropdowns after NPD file load."""
        if sources:
            self._front_gps.configure(values=sources)
            self._tail_gps.configure(values=sources)
            if len(sources) >= 1:
                self._front_gps.set(sources[0])
            if len(sources) >= 2:
                self._tail_gps.set(sources[1])

    def set_selected_gps_sources(self, front: str = "", tail: str = ""):
        """Restore front/tail GPS selections after values are loaded."""
        if front:
            self._front_gps.set(front)
        if tail:
            self._tail_gps.set(tail)

    def update_summary(self, text: str):
        """Update stat cards from summary text.

        Expected format: "Shots: 1,247  |  Channels: 48  |  FFID: 100-1346"
        Falls back to displaying raw text if parsing fails.
        """
        try:
            parts = text.split("|")
            for part in parts:
                part = part.strip()
                if part.startswith("Shots:"):
                    val = part.replace("Shots:", "").strip()
                    self._stat_shots.set_value(value=val)
                elif part.startswith("Channels:"):
                    val = part.replace("Channels:", "").strip()
                    self._stat_channels.set_value(value=val)
                elif part.startswith("FFID:"):
                    val = part.replace("FFID:", "").strip()
                    self._stat_ffid.set_value(value=val)
        except Exception:
            # Fallback: show raw text in shots card
            self._stat_shots.set_value(value=text[:20])

    @property
    def current_style(self) -> str:
        val = self._mode_seg.get()
        return "A" if val.startswith("Style A") else "B"

    def set_line_name(self, name: str):
        """Set line name field for the currently active style."""
        if self.current_style == "A":
            self._line_name_a.value = name
        else:
            self._line_name_b.value = name

    def get_line_name(self) -> str:
        """Get current line name value."""
        if self.current_style == "A":
            return self._line_name_a.value
        return self._line_name_b.value

    def set_radex_coord_decimals(self, value):
        """Keep the RadEx sidecar precision in sync across both modes."""
        text = str(value)
        self._radex_decimals_a.value = text
        self._radex_decimals_b.value = text

    def get_radex_coord_decimals(self) -> str:
        """Return the current RadEx sidecar precision value."""
        if self.current_style == "A":
            return self._radex_decimals_a.value
        return self._radex_decimals_b.value

    def get_config_values(self) -> dict:
        """Return current panel values as dict."""
        if self.current_style == "B":
            result = {
                "style": "B",
                "input_file": self._radex_drop.value,
                "line_name": self._line_name_b.value,
                "output_dir": self._output_dir_b.value,
                "radex_coord_decimals": self._radex_decimals_b.value,
            }
            if self._batch_mode:
                result["batch_mode"] = True
                result["batch_files"] = list(self._batch_files)
            return result
        else:
            result = {
                "style": "A",
                "npd_file": self._npd_drop.value,
                "track_file": self._track_drop.value,
                "line_name": self._line_name_a.value,
                "output_dir": self._output_dir_a.value,
                "front_gps": self._front_gps.get(),
                "tail_gps": self._tail_gps.get(),
                "radex_coord_decimals": self._radex_decimals_a.value,
            }
            if self._batch_mode:
                result["batch_mode"] = True
                result["batch_files"] = list(self._batch_files)
            return result

    # ── Profile Management ──

    def _save_profile(self):
        name = self._profile_name_entry.get().strip()
        if not name:
            return
        if self._on_profile_save:
            self._on_profile_save(name)
        self.refresh_profiles()

    def _load_profile(self):
        name = self._profile_menu.get()
        if not name or name == "(No profiles)":
            return
        if self._on_profile_load:
            self._on_profile_load(name)

    def _delete_profile(self):
        name = self._profile_menu.get()
        if not name or name == "(No profiles)":
            return
        if self._on_profile_delete:
            self._on_profile_delete(name)
        self.refresh_profiles()

    def refresh_profiles(self):
        """Refresh profile dropdown from saved profiles."""
        from ...utils.settings import list_profiles
        profiles = list_profiles()
        if profiles:
            self._profile_menu.configure(values=profiles)
            self._profile_menu.set(profiles[0])
        else:
            self._profile_menu.configure(values=["(No profiles)"])
            self._profile_menu.set("(No profiles)")

    def set_profile_save_callback(self, callback):
        """Set callback(name) for profile save."""
        self._on_profile_save = callback

    def set_profile_load_callback(self, callback):
        """Set callback(name) for profile load."""
        self._on_profile_load = callback

    def set_profile_delete_callback(self, callback):
        """Set callback(name) for profile delete."""
        self._on_profile_delete = callback

    # ── Batch Mode ──

    @property
    def is_batch_mode(self) -> bool:
        return self._batch_mode

    def _on_batch_toggle(self):
        """Handle batch mode checkbox toggle."""
        self._batch_mode = self._batch_var.get()
        if self._batch_mode:
            self._batch_info.pack(fill="x", pady=(SP["xs"], 0))
            self._batch_info.configure(
                text="Batch mode ON - Click file selector to choose multiple files"
            )
            # Disable line name in batch mode (auto-detected per file)
            if self.current_style == "B":
                self._line_name_b.value = "(auto-detect)"
            else:
                self._line_name_a.value = "(auto-detect)"
        else:
            self._batch_info.pack_forget()
            self._batch_files = []
            if self.current_style == "B":
                self._line_name_b.value = ""
            else:
                self._line_name_a.value = ""

    def _browse_batch_radex(self):
        """Browse for multiple RadExPro export files."""
        paths = filedialog.askopenfilenames(
            title="Select RadExPro Export Files (Batch)",
            filetypes=[("Text files", "*.txt"), ("TSV files", "*.tsv"),
                       ("All files", "*.*")],
        )
        if paths:
            self._batch_files = list(paths)
            self._batch_info.configure(
                text=f"Batch: {len(paths)} files selected"
            )
            # Show first file in drop zone
            self._radex_drop.set_file(paths[0])
            if self._on_file_loaded:
                self._on_file_loaded("radex", paths[0])

    def _browse_batch_folder_a(self):
        """Browse for folder containing NPD+Track file pairs."""
        folder = filedialog.askdirectory(
            title="Select folder with NPD + Track file pairs"
        )
        if folder:
            from pathlib import Path
            p = Path(folder)
            # Find file pairs by common stem patterns
            npd_files = sorted(p.glob("*.npd")) + sorted(p.glob("*.NPD"))
            track_files = sorted(p.glob("*track*")) + sorted(p.glob("*Track*"))
            pairs = []
            for npd in npd_files:
                stem = npd.stem
                for track in track_files:
                    if stem.lower() in track.stem.lower():
                        pairs.append((str(npd), str(track)))
                        break
            if pairs:
                self._batch_files = pairs
                self._batch_info.configure(
                    text=f"Batch: {len(pairs)} NPD+Track pairs found"
                )
            else:
                self._batch_info.configure(
                    text="No matching NPD+Track pairs found in folder"
                )
