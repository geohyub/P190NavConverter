"""Results panel — QC dashboard + output file info."""

import os
import subprocess
import customtkinter as ctk

from ..theme import COLORS, SP, font, mono_font
from ..widgets import SectionCard, StatCard, QCCheckItem, QualityGauge


class ResultsPanel(ctk.CTkFrame):
    """Panel for displaying conversion results and QC dashboard."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._output_path = None
        self._report_path = None
        self._build()

    def _build(self):
        # ── Top Row: Gauge + Stats ──
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, SP["md"]))

        # Quality Gauge (left)
        self._gauge = QualityGauge(top_row)
        self._gauge.pack(side="left", padx=(0, SP["md"]))

        # Stats column (right)
        stats_col = ctk.CTkFrame(top_row, fg_color="transparent")
        stats_col.pack(side="left", fill="both", expand=True)

        self._stat_file = StatCard(
            stats_col, icon="\U0001f4c4", value="--",
            label="Output File Size", accent_index=0,
        )
        self._stat_file.pack(fill="x", pady=(0, SP["xs"]))

        self._stat_lines = StatCard(
            stats_col, icon="\U0001f4dd", value="--",
            label="Total Lines", accent_index=3,
        )
        self._stat_lines.pack(fill="x")

        # ── Output File Card ──
        file_card = SectionCard(self, title="Output File")
        file_card.pack(fill="x", pady=(0, SP["md"]))

        f_inner = ctk.CTkFrame(file_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._file_label = ctk.CTkLabel(
            f_inner,
            text="No output generated yet",
            font=mono_font(),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._file_label.pack(fill="x", pady=(0, SP["xs"]))

        btn_frame = ctk.CTkFrame(f_inner, fg_color="transparent")
        btn_frame.pack(fill="x")

        self._open_file_btn = ctk.CTkButton(
            btn_frame, text="Open P190", width=120,
            font=font("body"),
            fg_color=COLORS["accent_muted"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._open_output,
            state="disabled",
        )
        self._open_file_btn.pack(side="left", padx=(0, SP["sm"]))

        self._open_folder_btn = ctk.CTkButton(
            btn_frame, text="Open Folder", width=120,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self._open_folder,
            state="disabled",
        )
        self._open_folder_btn.pack(side="left", padx=(0, SP["sm"]))

        self._open_report_btn = ctk.CTkButton(
            btn_frame, text="Open QC Report", width=130,
            font=font("body"),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self._open_report,
            state="disabled",
        )
        self._open_report_btn.pack(side="left")

        # ── QC Checks Card ──
        qc_card = SectionCard(self, title="QC Validation Checks")
        qc_card.pack(fill="x", pady=(0, SP["md"]))

        qc_inner = ctk.CTkFrame(qc_card, fg_color="transparent")
        qc_inner.pack(fill="x", padx=SP["md"], pady=(0, SP["md"]))

        self._qc_checks = {}
        check_names = [
            ("h_records", "H Record Headers"),
            ("s_records", "S Records (Source)"),
            ("r_records", "R Records (Receiver)"),
            ("line_length", "Line Length (80 cols)"),
            ("coord_range", "Coordinate Range"),
            ("sequence", "FFID Sequence"),
        ]
        for key, name in check_names:
            item = QCCheckItem(qc_inner, check_name=name)
            item.pack(fill="x", pady=1)
            self._qc_checks[key] = item

        # ── QC Summary Status ──
        self._qc_status = ctk.CTkLabel(
            qc_card,
            text="  Waiting for conversion...",
            font=font("h3", bold=True),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._qc_status.pack(fill="x", padx=SP["md"], pady=(0, SP["sm"]))

        # ── Report Text Card ──
        report_card = SectionCard(self, title="QC Report")
        report_card.pack(fill="both", expand=True)

        self._report_text = ctk.CTkTextbox(
            report_card,
            font=mono_font(),
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_width=0,
            corner_radius=6,
            wrap="none",
            state="disabled",
        )
        self._report_text.pack(
            fill="both", expand=True,
            padx=SP["sm"], pady=(0, SP["sm"]),
        )

    def set_output(self, p190_path: str, report_path: str = None):
        """Set output file paths after conversion."""
        self._output_path = p190_path
        self._report_path = report_path

        # File info
        size_kb = os.path.getsize(p190_path) / 1024 if os.path.exists(p190_path) else 0
        with open(p190_path, "r", encoding="ascii", errors="replace") as f:
            n_lines = sum(1 for _ in f)

        # Update stat cards
        if size_kb > 1024:
            self._stat_file.set_value(value=f"{size_kb/1024:.1f} MB")
        else:
            self._stat_file.set_value(value=f"{size_kb:.1f} KB")
        self._stat_lines.set_value(value=f"{n_lines:,}")

        self._file_label.configure(
            text=p190_path,
            text_color=COLORS["text_primary"],
        )

        self._open_file_btn.configure(state="normal")
        self._open_folder_btn.configure(state="normal")

        if report_path and os.path.exists(report_path):
            self._open_report_btn.configure(state="normal")
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            self._report_text.configure(state="normal")
            self._report_text.delete("1.0", "end")
            self._report_text.insert("1.0", report_content)
            self._report_text.configure(state="disabled")

    def set_qc_result(self, passed: bool, details: str):
        """Display QC result with dashboard widgets."""
        # Update overall status
        if passed:
            self._qc_status.configure(
                text="  PASS - All checks passed",
                text_color=COLORS["success"],
            )
            self._gauge.set_value(100)
        else:
            self._qc_status.configure(
                text="  FAIL - Issues detected",
                text_color=COLORS["error"],
            )
            self._gauge.set_value(40)

        # Parse details to update individual check items
        lines = details.strip().split("\n")
        for line in lines:
            line = line.strip()
            if ":" not in line:
                continue
            key_part, val_part = line.split(":", 1)
            key_part = key_part.strip().lower()
            val_part = val_part.strip()

            # Map detail keys to check items
            if "h record" in key_part:
                check_key = "h_records"
            elif "s record" in key_part:
                check_key = "s_records"
            elif "r record" in key_part:
                check_key = "r_records"
            elif "line" in key_part and "error" in key_part:
                check_key = "line_length"
            elif "issue" in key_part:
                check_key = "sequence"
            else:
                continue

            if check_key in self._qc_checks:
                # Determine status from value
                try:
                    num = int(val_part.replace(",", ""))
                    if check_key == "line_length":
                        status = "pass" if num == 0 else "fail"
                    elif check_key == "sequence":
                        status = "pass" if num == 0 else "warning"
                    else:
                        status = "pass" if num > 0 else "warning"
                except ValueError:
                    status = "pass"
                self._qc_checks[check_key].set_result(status, val_part)

        # Update coord_range as pass if we got here
        if "coord_range" in self._qc_checks:
            self._qc_checks["coord_range"].set_result(
                "pass" if passed else "warning", "OK" if passed else "Check")

        # Calculate gauge value
        if passed:
            self._gauge.set_value(100)
        else:
            # Count passes
            pass_count = sum(
                1 for line in lines
                if ":" in line and "0" not in line.split(":")[1].strip()
            )
            self._gauge.set_value(max(20, pass_count * 100 // max(len(lines), 1)))

    def _open_output(self):
        if self._output_path and os.path.exists(self._output_path):
            os.startfile(self._output_path)

    def _open_folder(self):
        if self._output_path:
            folder = os.path.dirname(self._output_path)
            if os.path.exists(folder):
                subprocess.Popen(["explorer", folder])

    def _open_report(self):
        if self._report_path and os.path.exists(self._report_path):
            os.startfile(self._report_path)
