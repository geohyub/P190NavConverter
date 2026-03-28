"""Tests for UI language toggle behavior."""

from desktop.services.language_service import LanguageService


def test_language_service_defaults_to_korean_and_toggles():
    service = LanguageService()

    assert service.current_language == "ko"
    assert service.text("sidebar.comparison") == "비교"

    service.toggle()

    assert service.current_language == "en"
    assert service.text("sidebar.comparison") == "Compare"
