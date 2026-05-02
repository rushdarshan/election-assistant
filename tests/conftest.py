"""Shared test fixtures and configuration for all test modules."""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "csrf_test: mark test as requiring CSRF middleware (do not bypass)")


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for all tests."""
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    def noop(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

    with patch.object(Limiter, "limit", side_effect=noop):
        yield


@pytest.fixture(autouse=True)
def mock_google_services():
    """Mock all Google Cloud services to avoid real API calls."""
    with patch.dict(os.environ, {
        "GOOGLE_CIVIC_API_KEY": "test-key",
        "GEMINI_API_KEY": "test-key",
        "GOOGLE_TRANSLATE_API_KEY": "",
        "GOOGLE_NLP_API_KEY": "",
        "SESSION_SECRET": "test-session-secret-for-testing",
        "JWT_SECRET": "test-jwt-secret-for-testing",
    }):
        yield


@pytest.fixture(autouse=True)
def bypass_csrf(request):
    """Bypass CSRF middleware for all tests except those marked with csrf_test."""
    if request.node.get_closest_marker("csrf_test"):
        yield
        return

    from app import csrf
    original = csrf.CSRF_ENABLED
    csrf.CSRF_ENABLED = False
    yield
    csrf.CSRF_ENABLED = original


@pytest.fixture(autouse=True)
def mock_mongodb():
    """Mock MongoDB connection for tests."""
    with patch("app.db.connect_to_mongo", new_callable=AsyncMock) as mock_connect, \
         patch("app.db.close_mongo", new_callable=AsyncMock) as mock_close:
        mock_connect.return_value = None
        mock_close.return_value = None
        yield mock_connect, mock_close


@pytest.fixture
def client():
    """FastAPI TestClient for making HTTP requests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def csrf_client():
    """TestClient that automatically handles CSRF tokens for POST requests."""
    with TestClient(app) as c:
        # GET a page first to obtain the CSRF cookie
        c.get("/")
        csrf_token = c.cookies.get("csrftoken", "")
        if csrf_token:
            c.headers["X-CSRFToken"] = csrf_token
        yield c


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response for AI tests."""
    mock_response = MagicMock()
    mock_response.text = '{"answer": "Test response", "source": "vote.gov"}'
    return mock_response


@pytest.fixture
def mock_civic_api_response():
    """Mock Google Civic API response."""
    return {
        "election": {
            "id": "2000",
            "name": "General Election 2026",
            "electionDay": "2026-11-03",
        },
        "normalizedInput": {
            "line1": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "90210",
        },
        "pollingLocations": [
            {
                "address": {
                    "locationName": "Community Center",
                    "line1": "456 Oak Ave",
                    "city": "Anytown",
                    "state": "CA",
                    "zip": "90210",
                },
                "pollingHours": "7:00 AM - 8:00 PM",
                "availableMethods": ["in_person_early", "in_person_election_day"],
            }
        ],
    }


@pytest.fixture
def auth_headers():
    """Generate headers with a valid JWT token for authenticated requests."""
    import jwt
    import time

    secret = "test-jwt-secret-for-testing"
    token = jwt.encode({
        "sub": "user_1",
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 7,
    }, secret, algorithm="HS256")

    return {"Authorization": f"Bearer {token}"}
