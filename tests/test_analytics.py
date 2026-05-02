"""Tests for the in-memory analytics counter module."""
import pytest
from app.analytics import increment, get_all_stats, get_counter, reset_all, record_endpoint_time


@pytest.fixture(autouse=True)
def clean_counters():
    """Reset all counters before each test."""
    reset_all()
    yield
    reset_all()


class TestIncrement:
    def test_increment_increases_counter_by_one(self):
        increment("chat_messages_sent")
        assert get_counter("chat_messages_sent") == 1

    def test_increment_multiple_times(self):
        increment("chat_messages_sent")
        increment("chat_messages_sent")
        increment("chat_messages_sent")
        assert get_counter("chat_messages_sent") == 3

    def test_increment_creates_new_counter(self):
        increment("custom_counter")
        assert get_counter("custom_counter") == 1

    def test_increment_with_labels(self):
        increment("scenarios_viewed", labels={"scenario": "lost_id"})
        assert get_counter("scenarios_viewed") == 1

    def test_increment_empty_name(self):
        increment("")
        assert get_counter("") == 1


class TestGetCounter:
    def test_get_existing_counter(self):
        increment("map_lookups")
        assert get_counter("map_lookups") == 1

    def test_get_nonexistent_counter_returns_zero(self):
        assert get_counter("nonexistent") == 0

    def test_get_all_counters_initialized_to_zero(self):
        stats = get_all_stats()
        assert stats["total_page_views"] == 0
        assert stats["chat_messages_sent"] == 0
        assert stats["scenarios_viewed"] == 0
        assert stats["map_lookups"] == 0
        assert stats["checklist_toggles"] == 0


class TestGetAllStats:
    def test_returns_all_counters(self):
        increment("chat_messages_sent")
        increment("chat_messages_sent")
        increment("map_lookups")

        stats = get_all_stats()
        assert stats["chat_messages_sent"] == 2
        assert stats["map_lookups"] == 1
        assert stats["scenarios_viewed"] == 0

    def test_returns_endpoint_stats_empty(self):
        stats = get_all_stats()
        assert stats["endpoint_stats"] == {}

    def test_returns_last_reset_indicator(self):
        stats = get_all_stats()
        assert "last_reset" in stats


class TestRecordEndpointTime:
    def test_record_single_time(self):
        record_endpoint_time("/chat/send", 150.5)
        stats = get_all_stats()
        assert "/chat/send" in stats["endpoint_stats"]
        assert stats["endpoint_stats"]["/chat/send"]["count"] == 1
        assert stats["endpoint_stats"]["/chat/send"]["avg_ms"] == 150.5

    def test_record_multiple_times(self):
        record_endpoint_time("/map/search", 100.0)
        record_endpoint_time("/map/search", 200.0)
        record_endpoint_time("/map/search", 300.0)

        stats = get_all_stats()
        map_stats = stats["endpoint_stats"]["/map/search"]
        assert map_stats["count"] == 3
        assert map_stats["avg_ms"] == 200.0
        assert map_stats["min_ms"] == 100.0
        assert map_stats["max_ms"] == 300.0

    def test_truncates_to_100_entries(self):
        for i in range(150):
            record_endpoint_time("/scenarios", float(i))

        stats = get_all_stats()
        assert stats["endpoint_stats"]["/scenarios"]["count"] == 100


class TestResetAll:
    def test_reset_clears_all_counters(self):
        increment("chat_messages_sent")
        increment("map_lookups")
        reset_all()

        assert get_counter("chat_messages_sent") == 0
        assert get_counter("map_lookups") == 0

    def test_reset_clears_endpoint_times(self):
        record_endpoint_time("/chat", 100.0)
        reset_all()

        stats = get_all_stats()
        assert stats["endpoint_stats"] == {}
