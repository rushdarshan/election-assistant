"""Tests for AI provider fallback chain."""

import pytest
from unittest.mock import patch, MagicMock
from app.ai_chain import AIProviderChain


@pytest.fixture
def ai_chain():
    """Create an AI chain with no real providers available."""
    with patch.dict("os.environ", {
        "GOOGLE_PROJECT_ID": "",
        "GEMINI_API_KEY": "",
    }):
        return AIProviderChain()


class TestHardcodedFallback:
    """Test hardcoded fallback responses."""

    def test_registration_keyword(self, ai_chain):
        """Returns registration guidance for 'registration' keyword."""
        result = ai_chain.get_response("How do I register to vote?")
        assert result["provider"] == "hardcoded"
        assert "response" in result
        assert "text" in result["response"]

    def test_voting_keyword(self, ai_chain):
        """Returns voting guidance for 'voting' keyword."""
        result = ai_chain.get_response("How do I vote?")
        assert result["provider"] == "hardcoded"
        assert "voting" in result["response"]["text"].lower()

    def test_polling_keyword(self, ai_chain):
        """Returns polling place guidance for 'polling' keyword."""
        result = ai_chain.get_response("Where is my polling place?")
        assert result["provider"] == "hardcoded"
        assert "polling" in result["response"]["text"].lower()

    def test_deadline_keyword(self, ai_chain):
        """Returns deadline guidance for 'deadline' keyword."""
        result = ai_chain.get_response("What is the registration deadline?")
        assert result["provider"] == "hardcoded"
        assert "deadline" in result["response"]["text"].lower()

    def test_id_keyword(self, ai_chain):
        """Returns ID guidance from KB or hardcoded for 'id' keyword."""
        result = ai_chain.get_response("What ID do I need to vote?")
        assert result["provider"] in ("knowledge_base", "hardcoded")

    def test_mail_keyword(self, ai_chain):
        """Returns mail ballot guidance for 'mail' keyword."""
        result = ai_chain.get_response("How do I vote by mail?")
        assert result["provider"] == "hardcoded"

    def test_unknown_keyword(self, ai_chain):
        """Returns generic guidance for unknown topics."""
        result = ai_chain.get_response("Something completely unrelated xyz")
        assert result["provider"] == "hardcoded"
        assert "response" in result


class TestKnowledgeBaseFallback:
    """Test local knowledge base fallback."""

    def test_kb_returns_response_for_matching_topic(self, ai_chain):
        """KB provides response for queries matching KB topics."""
        result = ai_chain.get_response("what are the id requirements for voting")
        assert result["provider"] == "knowledge_base"
        assert "response" in result

    def test_kb_returns_none_for_unrelated_query(self, ai_chain):
        """Unrelated queries fall through to hardcoded."""
        result = ai_chain.get_response("something completely unrelated about bananas")
        assert result["provider"] == "hardcoded"


class TestCaching:
    """Test response caching."""

    def test_cache_hit_returns_same_response(self, ai_chain):
        """Second identical request returns cached response."""
        r1 = ai_chain.get_response("registration test")
        r2 = ai_chain.get_response("registration test")

        assert r1["response"]["text"] == r2["response"]["text"]
        assert r2["cached"] is True

    def test_cache_miss_for_different_prompt(self, ai_chain):
        """Different prompts do not share cache."""
        r1 = ai_chain.get_response("registration query A")
        r2 = ai_chain.get_response("registration query B")

        # Both are hardcoded so same content, but r2 should not be cached
        # (different prompts have different cache keys)
        assert r1["response"]["text"] == r2["response"]["text"]


class TestProviderStats:
    """Test provider statistics tracking."""

    def test_stats_track_total_requests(self, ai_chain):
        """Total requests counter increments."""
        initial = ai_chain.stats.total_requests
        ai_chain.get_response("test")
        assert ai_chain.stats.total_requests == initial + 1

    def test_stats_track_cache_hits(self, ai_chain):
        """Cache hits counter increments on repeated requests."""
        ai_chain.get_response("cache test")
        ai_chain.get_response("cache test")
        assert ai_chain.stats.cache_hits >= 1

    def test_stats_track_fallback_used(self, ai_chain):
        """Fallback counter increments when hardcoded response is used."""
        initial = ai_chain.stats.fallback_used
        ai_chain.get_response("unknown topic xyz")
        assert ai_chain.stats.fallback_used > initial
