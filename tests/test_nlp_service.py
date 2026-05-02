"""Tests for Google Cloud Natural Language service."""

import pytest
from unittest.mock import patch
from app.nlp_service import NLPService


class TestNLPServiceInit:
    """Test NLPService initialization."""

    def test_no_api_key_unavailable(self):
        """Service is unavailable without API key."""
        with patch.dict("os.environ", {"GOOGLE_NLP_API_KEY": ""}, clear=False):
            service = NLPService()
            assert not service.available


class TestNLPFallback:
    """Test NLP fallback behavior."""

    def test_sentiment_returns_neutral_when_unavailable(self):
        """Returns neutral sentiment when service is unavailable."""
        service = NLPService()
        result = service.analyze_sentiment("Hello world")
        assert result["score"] == 0.0
        assert result["magnitude"] == 0.0
        assert result["label"] == "neutral"

    def test_entities_returns_empty_when_unavailable(self):
        """Returns empty entities when service is unavailable."""
        service = NLPService()
        result = service.analyze_entities("Hello world")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_query_returns_full_structure(self):
        """Full analysis returns sentiment and entities."""
        service = NLPService()
        result = service.analyze_query("I love voting!")
        assert "sentiment" in result
        assert "entities" in result
        assert "score" in result["sentiment"]
        assert "label" in result["sentiment"]

    def test_empty_text_returns_defaults(self):
        """Empty text returns default neutral result."""
        service = NLPService()
        result = service.analyze_sentiment("")
        assert result["label"] == "neutral"
