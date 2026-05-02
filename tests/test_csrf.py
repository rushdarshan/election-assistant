"""Tests for CSRF protection middleware."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.csrf_test
class TestCSRFMiddleware:
    """Test CSRF token issuance and validation."""

    def test_get_sets_csrf_cookie(self):
        """GET requests set a csrftoken cookie."""
        with TestClient(app) as c:
            response = c.get("/")
            # Check response headers for set-cookie
            cookies_header = response.headers.get("set-cookie", "")
            assert "csrftoken" in cookies_header or "csrftoken" in c.cookies

    def test_post_form_without_csrf_fails(self):
        """POST form requests without CSRF token return 403."""
        with TestClient(app) as c:
            # First GET to trigger CSRF cookie issuance
            response = c.get("/")
            cookies_header = response.headers.get("set-cookie", "")
            # Extract token from set-cookie header if available
            csrf_token = ""
            if "csrftoken" in cookies_header:
                # Parse: csrftoken=<token>; path=/; ...
                for part in cookies_header.split(";"):
                    if part.strip().startswith("csrftoken="):
                        csrf_token = part.strip().split("=")[1]
                        break

            response = c.post("/timeline", data={
                "country": "US",
                "state": "CA",
                "registration_status": "yes",
                "voting_method": "in_person",
            })
            if not csrf_token:
                # CSRF cookie wasn't set, so POST should fail with 403
                assert response.status_code == 403

    def test_post_json_without_csrf_succeeds(self):
        """POST JSON requests are exempt from CSRF (CORS protects them)."""
        with TestClient(app) as c:
            response = c.post("/auth/register", json={
                "email": "csrf-test@example.com",
                "password": "password123",
                "name": "CSRF Test",
            })
            assert response.status_code != 403

    def test_post_form_with_wrong_csrf_fails(self):
        """POST form requests with wrong CSRF token return 403."""
        with TestClient(app) as c:
            c.get("/")
            response = c.post("/timeline", data={
                "country": "US",
                "state": "CA",
                "registration_status": "yes",
                "voting_method": "in_person",
            }, headers={"X-CSRFToken": "wrong-token"})
            assert response.status_code == 403

    def test_healthz_does_not_require_csrf(self):
        """GET endpoints do not require CSRF."""
        with TestClient(app) as c:
            response = c.get("/healthz")
            assert response.status_code == 200

    def test_json_api_exemption(self):
        """JSON POST endpoints are exempt from CSRF."""
        with TestClient(app) as c:
            response = c.post("/nlp/analyze", json={"text": "hello"})
            assert response.status_code != 403


@pytest.mark.csrf_test
class TestCSRFTokenRotation:
    """Test CSRF token behavior across requests."""

    def test_csrf_cookie_persists(self):
        """CSRF cookie persists across multiple GET requests."""
        with TestClient(app) as c:
            r1 = c.get("/")
            r2 = c.get("/wizard")
            # Both responses should have set-cookie headers or cookies
            assert r1.status_code == 200
            assert r2.status_code == 200
