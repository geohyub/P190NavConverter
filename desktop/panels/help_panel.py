"""HelpPanel — Usage guide, keyboard shortcuts, P190 format reference."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
)

from geoview_pyside6.constants import Dark, Font, Space, Radius

from desktop.widgets.section_card import SectionCard


HELP_SECTIONS = [
    ("Style A 워크플로우 (NPD + Geometry)", [
        "1. Input: NPD 항법 파일 + Track 파일 로드",
        "2. GPS 소스 선택 (선수/선미 Buoy)",
        "3. Header: 조사 메타데이터 H Record 편집",
        "4. CRS: 좌표계 선택",
        "5. Geometry: 음원/수신기 오프셋 설정",
        "6. Preview: 트랙 맵과 Shot 위치 확인",
        "7. Convert 클릭 (Ctrl+Enter)",
        "8. 결과 확인, Feathering 분석 검토",
    ]),
    ("Style B 워크플로우 (RadExPro Export)", [
        "1. Input: RadExPro Header Export TSV 로드",
        "2. Header: 조사 메타데이터 H Record 편집",
        "3. CRS: 좌표계 선택",
        "4. Convert 클릭 (Ctrl+Enter)",
        "5. 결과 및 QC 검증 확인",
    ]),
    ("단축키", [
        "Ctrl+Enter  --  변환 시작",
        "Escape      --  입력 화면으로 돌아가기",
    ]),
    ("P190 레코드 형식", [
        "H Record: 80자 헤더 (조사 메타데이터)",
        "S Record: Shot당 소스 위치 (FFID, 위경도, UTM, 시각)",
        "R Record: 수신기 위치 (줄당 3그룹, 48ch = 16줄)",
        "고정 폭 텍스트, 줄당 80자",
    ]),
    ("보간법 안내", [
        "Linear: RadExPro 표준 등간격 배치",
        "Catenary: 물리 기반 케이블 현수선 (심해용)",
        "Spline: 제어점 통과 큐빅 보간",
        "Feathering: 조류 편향 모델 (alpha 지수)",
    ]),
]


class HelpPanel(QWidget):
    """사용 안내 및 P190 형식 참조."""

    panel_title = "도움말"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.LG, Space.MD, Space.LG, Space.MD)
        outer.setSpacing(Space.SM)

        # Title
        title = QLabel("P190 NavConverter 도움말")
        title.setStyleSheet(f"""
            color: {Dark.TEXT_BRIGHT};
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            background: transparent; border: none;
        """)
        outer.addWidget(title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        content = QVBoxLayout(container)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(Space.MD)

        for section_title, items in HELP_SECTIONS:
            card = SectionCard(section_title)
            for item in items:
                lbl = QLabel(item)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"""
                    color: {Dark.TEXT};
                    font-size: {Font.SM}px;
                    background: transparent;
                    border: none;
                    padding-left: 8px;
                """)
                card.content_layout.addWidget(lbl)
            content.addWidget(card)

        content.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)
