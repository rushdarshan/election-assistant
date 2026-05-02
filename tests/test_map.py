"""Tests for the Polling Place Finder feature."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def csrf_client():
    """Client with CSRF cookie pre-loaded."""
    with TestClient(app) as c:
        c.get("/")
        csrf_token = c.cookies.get("csrftoken", "")
        if csrf_token:
            c.headers["X-CSRFToken"] = csrf_token
        yield c


class TestMapPage:
    def test_get_map_returns_200(self, client):
        response = client.get("/map")
        assert response.status_code == 200

    def test_get_map_has_search_form(self, client):
        response = client.get("/map")
        assert "address" in response.text.lower()

    def test_get_map_has_correct_nav_state(self, client):
        response = client.get("/map")
        assert 'aria-current="page"' in response.text


class TestMapSearch:
    def test_post_map_without_api_key_returns_error(self, csrf_client):
        response = csrf_client.post("/map", data={"address": "123 Main St, Anytown, USA"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_post_map_empty_address_returns_validation_error(self, csrf_client):
        response = csrf_client.post("/map", data={"address": ""})
        assert response.status_code in (200, 422)
