"""Google Cloud Translation service.

Provides translation of text into supported languages.
Gracefully falls back to the original text if the API is unavailable.
"""

import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Supported languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "bn": "Bengali",
    "te": "Telugu",
    "mr": "Marathi",
    "ta": "Tamil",
    "ur": "Urdu",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "mai": "Maithili",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "fr": "French",
    "de": "German",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
}


class TranslationService:
    """Google Cloud Translation wrapper with graceful fallback."""

    def __init__(self):
        self._client = None
        self._api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
        self._available = False

        if self._api_key:
            try:
                from google.cloud import translate_v2 as translate
                self._client = translate.Client(client_options={"api_key": self._api_key})
                self._available = True
                logger.info("Google Cloud Translate initialized")
            except Exception as e:
                logger.warning(f"Google Cloud Translate unavailable: {e}")
                self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def translate(self, text: str, target_language: str, source_language: str = "en") -> str:
        """Translate text to the target language.

        Falls back to the original text if translation is unavailable.
        """
        if not self._available or target_language == source_language:
            return text

        target_language = target_language.lower()
        if target_language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported target language: {target_language}")
            return text

        try:
            result = self._client.translate(
                text,
                target_language=target_language,
                source_language=source_language,
            )
            return result.get("translatedText", text)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text

    def get_supported_languages(self) -> dict[str, str]:
        """Return dict of language code -> display name."""
        return SUPPORTED_LANGUAGES


# Singleton instance
translation_service = TranslationService()
