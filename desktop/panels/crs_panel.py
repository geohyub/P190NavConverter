"""CRSPanel — Coordinate Reference System selection with presets."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QFrame,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard
from desktop.services.explanation_service import build_crs_impact_story

# CRS Presets organized by region
CRS_PRESETS = {
    "\ud55c\uad6d": [
        ("Korea 2000 / Unified CS", 5186, 52, "N", "WGS-84"),
        ("Korea 2000 / East Belt", 5187, 52, "N", "WGS-84"),
        ("Korea 2000 / West Belt", 5185, 51, "N", "WGS-84"),
        ("WGS 84 / UTM zone 51N", 32651, 51, "N", "WGS-84"),
        ("WGS 84 / UTM zone 52N", 32652, 52, "N", "WGS-84"),
    ],
    "Asia-Pacific": [
        ("WGS 84 / UTM zone 49N", 32649, 49, "N", "WGS-84"),
        ("WGS 84 / UTM zone 50N", 32650, 50, "N", "WGS-84"),
        ("WGS 84 / UTM zone 53N", 32653, 53, "N", "WGS-84"),
        ("WGS 84 / UTM zone 54N", 32654, 54, "N", "WGS-84"),
        ("WGS 84 / UTM zone 55N", 32655, 55, "N", "WGS-84"),
        ("WGS 84 / UTM zone 56N", 32656, 56, "N", "WGS-84"),
        ("WGS 84 / UTM zone 50S", 32750, 50, "S", "WGS-84"),
        ("WGS 84 / UTM zone 51S", 32751, 51, "S", "WGS-84"),
    ],
    "UTM Global": [
        (f"WGS 84 / UTM zone {z}N", 32600 + z, z, "N", "WGS-84")
        for z in range(1, 61)
    ] + [
        (f"WGS 84 / UTM zone {z}S", 32700 + z, z, "S", "WGS-84")
        for z in range(1, 61)
    ],
    "\uc9c1\uc811 \uc785\ub825": [],
}


class CRSPanel(QWidget):
    """CRS/UTM zone selector with regional presets."""

    panel_title = "CRS"
    crs_changed = Signal(object)  # emits CRSConfig

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._presets = {}
        self._build_ui()
        self._set_region("\ud55c\uad6d")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        layout.setSpacing(Space.MD)

        # Region selector
        region_card = SectionCard("\uc9c0\uc5ed")
        region_row = QHBoxLayout()
        region_row.setSpacing(Space.SM)

        self._region_btns = {}
        for region in ("\ud55c\uad6d", "Asia-Pacific", "UTM Global", "\uc9c1\uc811 \uc785\ub825"):
            btn = QPushButton(region)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda _, r=region: self._set_region(r))
            region_row.addWidget(btn)
            self._region_btns[region] = btn

        region_card.content_layout.addLayout(region_row)
        layout.addWidget(region_card)

        # Preset dropdown
        preset_card = SectionCard("\uc88c\ud45c\uacc4 \uc120\ud0dd")
        self._preset_combo = QComboBox()
        self._preset_combo.setStyleSheet(f"""
            QComboBox {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 6px 10px;
                font-size: {Font.SM}px;
                min-height: 28px;
            }}
        """)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_card.content_layout.addWidget(self._preset_combo)

        # EPSG info
        info_row = QHBoxLayout()
        info_row.setSpacing(Space.MD)

        self._epsg_label = QLabel("EPSG: --")
        self._epsg_label.setStyleSheet(
            f"color: #06B6D4; font-size: {Font.BASE}px;"
            f" font-weight: {Font.SEMIBOLD};"
            f" background:transparent; border:none;")
        info_row.addWidget(self._epsg_label)

        self._zone_label = QLabel("Zone: --")
        self._zone_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        info_row.addWidget(self._zone_label)

        self._datum_label = QLabel("Datum: --")
        self._datum_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        info_row.addWidget(self._datum_label)
        info_row.addStretch()

        preset_card.content_layout.addLayout(info_row)

        # Custom EPSG input
        custom_row = QHBoxLayout()
        custom_row.setSpacing(Space.SM)
        custom_row.addWidget(QLabel("EPSG \uc9c1\uc811 \uc785\ub825:"))
        self._custom_epsg = QLineEdit()
        self._custom_epsg.setPlaceholderText("e.g. 32652")
        self._custom_epsg.setFixedWidth(120)
        self._custom_epsg.setStyleSheet(f"""
            QLineEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 4px 8px;
                font-size: {Font.SM}px;
            }}
        """)
        self._custom_epsg.editingFinished.connect(self._apply_custom_epsg)
        custom_row.addWidget(self._custom_epsg)

        for lbl in preset_card.findChildren(QLabel):
            if lbl.text() == "EPSG \uc9c1\uc811 \uc785\ub825:":
                lbl.setStyleSheet(
                    f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                    f" background:transparent; border:none;")
        custom_row.addStretch()
        preset_card.content_layout.addLayout(custom_row)
        layout.addWidget(preset_card)

        # CRS Detail card — fill empty space with useful info
        detail_card = SectionCard("CRS \uc0c1\uc138 \uc815\ubcf4")
        self._detail_grid = QVBoxLayout()
        self._detail_grid.setSpacing(4)

        detail_rows = [
            ("\ud0c0\uc6d0\uccb4", "_ell_val", "WGS-84"),
            ("\uc7a5\ubc18\uacbd", "_sma_val", "6,378,137.0 m"),
            ("\ud3b8\ud3c9\ub960 (1/f)", "_flat_val", "298.257223563"),
            ("\ud22c\uc601\ubc95", "_proj_val", "Transverse Mercator"),
            ("\uc911\uc559 \uc790\uc624\uc120", "_cm_val", "--"),
            ("\ucd95\ucc99 \uacc4\uc218", "_sf_val", "0.9996"),
            ("False Easting", "_fe_val", "500,000 m"),
            ("False Northing", "_fn_val", "0 m"),
        ]

        for label_text, attr_name, default_val in detail_rows:
            row = QHBoxLayout()
            row.setSpacing(Space.SM)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(140)
            lbl.setStyleSheet(
                f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
                f" background:transparent; border:none;")
            val = QLabel(default_val)
            val.setStyleSheet(
                f"color: {Dark.TEXT}; font-size: {Font.SM}px;"
                f" background:transparent; border:none;")
            setattr(self, attr_name, val)
            row.addWidget(lbl)
            row.addWidget(val, 1)
            self._detail_grid.addLayout(row)

        detail_card.content_layout.addLayout(self._detail_grid)
        layout.addWidget(detail_card)

        preview_card = SectionCard("\uc88c\ud45c \ubbf8\ub9ac\ubcf4\uae30")
        sample_row = QHBoxLayout()
        sample_row.setSpacing(Space.SM)

        sample_e_label = QLabel("\uc608\uc2dc E:")
        sample_e_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        sample_row.addWidget(sample_e_label)

        self._sample_e = QLineEdit("618538.3")
        self._sample_e.setFixedWidth(120)
        self._sample_e.setStyleSheet(f"""
            QLineEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 4px 8px;
                font-size: {Font.SM}px;
            }}
        """)
        sample_row.addWidget(self._sample_e)

        sample_n_label = QLabel("\uc608\uc2dc N:")
        sample_n_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.SM}px;"
            f" background:transparent; border:none;")
        sample_row.addWidget(sample_n_label)

        self._sample_n = QLineEdit("3892818.4")
        self._sample_n.setFixedWidth(120)
        self._sample_n.setStyleSheet(f"""
            QLineEdit {{
                background: {Dark.DARK};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 4px 8px;
                font-size: {Font.SM}px;
            }}
        """)
        sample_row.addWidget(self._sample_n)

        preview_btn = QPushButton("\ud655\uc778")
        preview_btn.setFixedHeight(30)
        preview_btn.setCursor(Qt.PointingHandCursor)
        preview_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Dark.NAVY};
                color: {Dark.TEXT};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 0 12px;
                font-size: {Font.SM}px;
            }}
            QPushButton:hover {{ border-color: {Dark.CYAN}; }}
        """)
        preview_btn.clicked.connect(self._update_coordinate_preview)
        sample_row.addWidget(preview_btn)
        sample_row.addStretch()
        preview_card.content_layout.addLayout(sample_row)

        self._impact_label = QLabel("")
        self._impact_label.setWordWrap(True)
        self._impact_label.setStyleSheet(
            f"color: {Dark.MUTED}; font-size: {Font.XS}px;"
            f" background:transparent; border:none;")
        preview_card.content_layout.addWidget(self._impact_label)

        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet(f"""
            color: {Dark.TEXT};
            font-size: {Font.SM}px;
            background: {Dark.DARK};
            border: 1px solid {Dark.BORDER};
            border-radius: {Radius.SM}px;
            padding: 8px;
        """)
        preview_card.content_layout.addWidget(self._preview_label)
        layout.addWidget(preview_card)

        layout.addStretch()
        self._refresh_story()

    def _set_region(self, region: str):
        for r, btn in self._region_btns.items():
            active = (r == region)
            btn.setChecked(active)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Dark.CYAN if active else Dark.NAVY};
                    color: {Dark.DARK if active else Dark.MUTED};
                    border: {"none" if active
                             else f"1px solid {Dark.BORDER}"};
                    border-radius: {Radius.SM}px;
                    font-size: {Font.XS}px;
                    {"font-weight: " + str(Font.SEMIBOLD) + ";"
                     if active else ""}
                    padding: 0 12px;
                }}
                QPushButton:hover {{ border-color: #06B6D4; }}
            """)

        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._presets.clear()

        presets = CRS_PRESETS.get(region, [])
        for item in presets:
            name, epsg, zone, hemi, datum = item
            self._preset_combo.addItem(name)
            self._presets[name] = {
                "epsg_code": epsg,
                "utm_zone": zone,
                "hemisphere": hemi,
                "datum_name": datum,
                "display_name": name,
            }
        self._preset_combo.blockSignals(False)

        if presets:
            preferred_index = 0
            if region == "\ud55c\uad6d":
                utm_52_idx = self._preset_combo.findText("WGS 84 / UTM zone 52N")
                if utm_52_idx >= 0:
                    preferred_index = utm_52_idx
            self._preset_combo.setCurrentIndex(preferred_index)
            self._on_preset_changed(preferred_index)

    def _on_preset_changed(self, index: int):
        name = self._preset_combo.currentText()
        info = self._presets.get(name)
        if info:
            self._epsg_label.setText(f"EPSG: {info['epsg_code']}")
            self._zone_label.setText(
                f"Zone: {info['utm_zone']}{info['hemisphere']}")
            self._datum_label.setText(f"Datum: {info['datum_name']}")
            self._update_detail_card(info)
            self._refresh_story()
            self.crs_changed.emit(self.get_crs_config())

    def _update_detail_card(self, info: dict):
        """Update CRS detail card with computed UTM parameters."""
        zone = info.get("utm_zone", 0)
        hemi = info.get("hemisphere", "N")
        datum = info.get("datum_name", "WGS-84")

        if datum == "WGS-84":
            self._ell_val.setText("WGS-84")
            self._sma_val.setText("6,378,137.0 m")
            self._flat_val.setText("298.257223563")
        else:
            self._ell_val.setText(datum)
            self._sma_val.setText("--")
            self._flat_val.setText("--")

        self._proj_val.setText("Transverse Mercator")

        if zone > 0:
            cm = (zone - 1) * 6 - 180 + 3
            self._cm_val.setText(f"{cm} deg")
        else:
            self._cm_val.setText("--")

        self._sf_val.setText("0.9996")
        self._fe_val.setText("500,000 m")
        self._fn_val.setText("10,000,000 m" if hemi == "S" else "0 m")

    def _apply_custom_epsg(self):
        text = self._custom_epsg.text().strip()
        if text.isdigit():
            epsg = int(text)
            self._epsg_label.setText(f"EPSG: {epsg}")
            self._zone_label.setText("Zone: Custom")
            self._datum_label.setText("Datum: Custom")
            self._refresh_story()
            self.crs_changed.emit(self.get_crs_config())

    def get_crs_config(self):
        """Return CRSConfig from current selection."""
        from p190converter.models.survey_config import CRSConfig

        name = self._preset_combo.currentText()
        info = self._presets.get(name)

        if info:
            return CRSConfig(
                utm_zone=info["utm_zone"],
                hemisphere=info["hemisphere"],
                epsg_code=info["epsg_code"],
                display_name=info["display_name"],
                datum_name=info["datum_name"],
            )

        # Custom EPSG fallback
        custom = self._custom_epsg.text().strip()
        epsg = int(custom) if custom.isdigit() else 32652
        return CRSConfig(
            utm_zone=0,
            hemisphere="N",
            epsg_code=epsg,
            display_name=f"EPSG:{epsg}",
            datum_name="Custom",
        )

    def set_crs_config(self, data: dict):
        epsg = data.get("epsg_code", 32652)
        display = data.get("display_name", "")
        # Try to find in current presets
        for name, info in self._presets.items():
            if info["epsg_code"] == epsg:
                idx = self._preset_combo.findText(name)
                if idx >= 0:
                    self._preset_combo.setCurrentIndex(idx)
                    return
        # Fallback: set custom
        self._custom_epsg.setText(str(epsg))
        self._apply_custom_epsg()

    def _refresh_story(self):
        self._impact_label.setText(build_crs_impact_story(self.get_crs_config()))
        self._update_coordinate_preview()

    def _update_coordinate_preview(self):
        try:
            easting = float(self._sample_e.text())
            northing = float(self._sample_n.text())
        except ValueError:
            self._preview_label.setStyleSheet(f"""
                color: #F59E0B;
                font-size: {Font.SM}px;
                background: {Dark.DARK};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
            """)
            self._preview_label.setText(
                "Enter numeric sample Easting/Northing values to verify the selected CRS."
            )
            return

        try:
            from p190converter.engine.crs.transformer import CRSTransformer
            from p190converter.engine.crs.dms_formatter import (
                format_latitude,
                format_longitude,
            )

            transformer = CRSTransformer(self.get_crs_config())
            lat, lon = transformer.utm_to_latlon(easting, northing)
            self._preview_label.setStyleSheet(f"""
                color: {Dark.TEXT};
                font-size: {Font.SM}px;
                background: {Dark.DARK};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
            """)
            self._preview_label.setText(
                "\n".join(
                    [
                        f"Projected: E {easting:,.1f} m  |  N {northing:,.1f} m",
                        f"Decimal degrees: {lat:.8f}, {lon:.8f}",
                        f"P190 DMS fields: {format_latitude(lat)}  |  {format_longitude(lon)}",
                    ]
                )
            )
        except Exception as exc:
            self._preview_label.setStyleSheet(f"""
                color: #F59E0B;
                font-size: {Font.SM}px;
                background: {Dark.DARK};
                border: 1px solid {Dark.BORDER};
                border-radius: {Radius.SM}px;
                padding: 8px;
            """)
            self._preview_label.setText(f"Preview failed: {exc}")
