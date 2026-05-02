"""
In-memory analytics counters for aggregate server-level stats.
Counters are module-level dicts — reset on server restart.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import threading

_lock = threading.Lock()

_counters: Dict[str, int] = {
    "total_page_views": 0,
    "chat_messages_sent": 0,
    "scenarios_viewed": 0,
    "map_lookups": 0,
    "checklist_toggles": 0,
}

_endpoint_times: Dict[str, list] = {}


def increment(counter_name: str, labels: Optional[Dict[str, str]] = None) -> None:
    """Increment a named counter. Labels are stored but not yet aggregated."""
    with _lock:
        if counter_name not in _counters:
            _counters[counter_name] = 0
        _counters[counter_name] += 1


def record_endpoint_time(endpoint: str, duration_ms: float) -> None:
    """Record response time for an endpoint."""
    with _lock:
        if endpoint not in _endpoint_times:
            _endpoint_times[endpoint] = []
        _endpoint_times[endpoint].append(duration_ms)
        # Keep only last 100 entries per endpoint
        if len(_endpoint_times[endpoint]) > 100:
            _endpoint_times[endpoint] = _endpoint_times[endpoint][-100:]


def get_all_stats() -> Dict[str, Any]:
    """Return all counters and endpoint timing stats."""
    with _lock:
        stats = dict(_counters)
        endpoint_stats = {}
        for endpoint, times in _endpoint_times.items():
            endpoint_stats[endpoint] = {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 1) if times else 0,
                "min_ms": round(min(times), 1) if times else 0,
                "max_ms": round(max(times), 1) if times else 0,
            }
        stats["endpoint_stats"] = endpoint_stats
        stats["last_reset"] = "server start (ephemeral)"
        return stats


def get_counter(name: str) -> int:
    """Get current value of a specific counter."""
    with _lock:
        return _counters.get(name, 0)


def reset_all() -> None:
    """Reset all counters. Used for testing."""
    with _lock:
        for key in _counters:
            _counters[key] = 0
        _endpoint_times.clear()
