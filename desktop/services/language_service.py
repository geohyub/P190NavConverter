"""Lightweight UI language toggle for the P190 desktop app."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


TRANSLATIONS = {
    "en": {
        "sidebar.input": "Input",
        "sidebar.header": "Header",
        "sidebar.crs": "CRS",
        "sidebar.geometry": "Geometry",
        "sidebar.preview": "Preview",
        "sidebar.log": "Log",
        "sidebar.results": "Results",
        "sidebar.feathering": "Feathering",
        "sidebar.comparison": "Compare",
        "sidebar.help": "Help",
        "sidebar.output": "Output",
        "top.language_button": "KO / EN",
        "compare.panel_title": "Compare",
        "compare.files_card": "P190 Files to Compare",
        "compare.file_a": "Style A P190",
        "compare.file_b": "Style B P190",
        "compare.browse": "Browse",
        "compare.compare_button": "Compare",
        "compare.stat_grade": "Grade",
        "compare.stat_src_diff": "Src Mean Diff",
        "compare.stat_rx_diff": "Rx Mean Diff",
        "compare.stat_matched": "Matched Shots",
        "compare.idle_insight": "Compare two exported P190 files to understand how source basis, offsets, and interpolation changed the final geometry.",
        "compare.overlay_card": "Selected Shot Overlay",
        "compare.overlay_idle": "After comparison, inspect one matched FFID at a time to see source and receiver differences.",
        "compare.quick_first": "First",
        "compare.quick_middle": "Middle",
        "compare.quick_worst": "Worst",
        "compare.quick_last": "Last",
        "compare.meaning_card": "Comparison Meaning",
        "compare.meaning_idle": "Run a comparison to see source/receiver difference statistics, directional context, and an export-ready summary.",
        "compare.channel_card": "Receiver Channel Summary",
        "compare.channel_idle": "Receiver comparison will appear here when both files contain comparable R records.",
        "compare.worst_card": "Largest Shot Differences",
        "compare.worst_idle": "Run a comparison to list the largest FFID-level source differences.",
        "compare.detail_card": "Selected Shot Details",
        "compare.detail_idle": "Move the FFID slider or use the quick-focus buttons to inspect per-shot coordinates and channel deltas.",
        "compare.sync_card": "Synchronized Style Workspace",
        "compare.sync_idle": "The selected FFID will stay locked across Style A and Style B so you can review both geometry stories side by side.",
        "compare.evidence_card": "Linked Evidence Review",
        "compare.evidence_idle": "Comparison evidence will appear here once two exported P190 files are loaded.",
        "compare.evidence_a": "Style A Evidence",
        "compare.evidence_b": "Style B Evidence",
        "compare.open_selected": "Open Selected",
        "compare.channel_profile_card": "Selected Shot Receiver Delta Profile",
        "compare.channel_profile_idle": "Receiver delta profile will appear here when the selected shot has comparable R records.",
        "compare.export_report": "Export Report",
        "compare.export_plot": "Export Plot",
        "compare.export_manifest": "Export Manifest",
    },
    "ko": {
        "sidebar.input": "입력",
        "sidebar.header": "헤더",
        "sidebar.crs": "좌표계",
        "sidebar.geometry": "지오메트리",
        "sidebar.preview": "미리보기",
        "sidebar.log": "로그",
        "sidebar.results": "결과",
        "sidebar.feathering": "페더링",
        "sidebar.comparison": "비교",
        "sidebar.help": "도움말",
        "sidebar.output": "출력",
        "top.language_button": "KO / EN",
        "compare.panel_title": "비교",
        "compare.files_card": "비교할 P190 파일",
        "compare.file_a": "Style A P190",
        "compare.file_b": "Style B P190",
        "compare.browse": "찾아보기",
        "compare.compare_button": "비교 실행",
        "compare.stat_grade": "등급",
        "compare.stat_src_diff": "소스 평균 차이",
        "compare.stat_rx_diff": "리시버 평균 차이",
        "compare.stat_matched": "매칭 샷 수",
        "compare.idle_insight": "두 개의 P190 산출물을 비교해 소스 기준, 오프셋, 보간 방식이 최종 지오메트리를 어떻게 바꿨는지 확인합니다.",
        "compare.overlay_card": "선택 샷 오버레이",
        "compare.overlay_idle": "비교 후에는 매칭된 FFID를 하나씩 보면서 소스와 리시버 차이를 확인할 수 있습니다.",
        "compare.quick_first": "처음",
        "compare.quick_middle": "중간",
        "compare.quick_worst": "최대차",
        "compare.quick_last": "마지막",
        "compare.meaning_card": "비교 해설",
        "compare.meaning_idle": "비교를 실행하면 소스/리시버 차이 통계와 방향성 맥락, 내보내기용 요약이 표시됩니다.",
        "compare.channel_card": "리시버 채널 요약",
        "compare.channel_idle": "두 파일 모두 비교 가능한 R 레코드를 포함하면 채널별 비교 결과가 표시됩니다.",
        "compare.worst_card": "차이가 큰 샷",
        "compare.worst_idle": "비교를 실행하면 FFID별 최대 소스 차이 목록이 표시됩니다.",
        "compare.detail_card": "선택 샷 상세",
        "compare.detail_idle": "FFID 슬라이더나 빠른 이동 버튼으로 샷별 좌표와 채널 차이를 확인할 수 있습니다.",
        "compare.sync_card": "동기화 비교 작업면",
        "compare.sync_idle": "선택한 FFID를 Style A와 Style B에 고정해서 두 지오메트리 설명을 나란히 검토합니다.",
        "compare.evidence_card": "연결된 산출물 근거",
        "compare.evidence_idle": "두 개의 P190 산출물을 불러오면 비교 근거가 여기에 표시됩니다.",
        "compare.evidence_a": "Style A 근거",
        "compare.evidence_b": "Style B 근거",
        "compare.open_selected": "선택 파일 열기",
        "compare.channel_profile_card": "선택 샷 리시버 차이 프로파일",
        "compare.channel_profile_idle": "선택 샷에 비교 가능한 R 레코드가 있으면 리시버 차이 프로파일이 표시됩니다.",
        "compare.export_report": "리포트 저장",
        "compare.export_plot": "플롯 저장",
        "compare.export_manifest": "패키지 요약 저장",
    },
}


class LanguageService(QObject):
    """Keeps current UI language and emits toggle updates."""

    language_changed = Signal(str)

    def __init__(self, language: str = "ko", parent=None):
        super().__init__(parent)
        self._language = language if language in TRANSLATIONS else "ko"

    @property
    def current_language(self) -> str:
        return self._language

    def set_language(self, language: str):
        if language not in TRANSLATIONS or language == self._language:
            return
        self._language = language
        self.language_changed.emit(language)

    def toggle(self):
        self.set_language("en" if self._language == "ko" else "ko")

    def text(self, key: str, **kwargs) -> str:
        value = TRANSLATIONS.get(self._language, {}).get(key)
        if value is None:
            value = TRANSLATIONS["en"].get(key, key)
        return value.format(**kwargs)
