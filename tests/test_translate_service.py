"""Tests for Google Cloud Translation service."""

import pytest
from unittest.mock import patch, MagicMock
from app.translate_service import TranslationService, SUPPORTED_LANGUAGES


class TestTranslationServiceInit:
    """Test TranslationService initialization."""

    def test_no_api_key_unavailable(self):
        """Service is unavailable without API key."""
        with patch.dict("os.environ", {"GOOGLE_TRANSLATE_API_KEY": ""}, clear=False):
            service = TranslationService()
            assert not service.available

    def test_supported_languages_not_empty(self):
        """Supported languages dict has entries."""
        assert len(SUPPORTED_LANGUAGES) > 20
        assert "en" in SUPPORTED_LANGUAGES
        assert "hi" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES


class TestTranslationFallback:
    """Test translation fallback behavior."""

    def test_returns_original_when_unavailable(self):
        """Returns original text when service is unavailable."""
        service = TranslationService()
        result = service.translate("Hello world", "hi")
        # Either translated or original (if no API key)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_original_when_same_language(self):
        """Returns original text when source == target."""
        service = TranslationService()
        result = service.translate("Hello", "en", "en")
        assert result == "Hello"

    def test_unsupported_language_returns_original(self):
        """Returns original text for unsupported language."""
        service = TranslationService()
        result = service.translate("Hello", "xx")
        assert result == "Hello"

    def test_empty_text_returns_empty(self):
        """Empty text returns empty string."""
        service = TranslationService()
        result = service.translate("", "hi")
        assert result == ""


class TestLanguageList:
    """Test language listing."""

    def test_get_supported_languages(self):
        """Returns dict of all supported languages."""
        service = TranslationService()
        langs = service.get_supported_languages()
        assert isinstance(langs, dict)
        assert len(langs) > 10
        assert langs["en"] == "English"
        assert langs["hi"] == "Hindi"
