"""Tests for the Smart Checklist + Readiness Score feature."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.checklist import CHECKLIST_ITEMS


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


class TestChecklistPage:
    def test_get_checklist_returns_200(self, client):
        response = client.get("/checklist")
        assert response.status_code == 200

    def test_get_checklist_contains_all_items(self, client):
        response = client.get("/checklist")
        for item in CHECKLIST_ITEMS:
            assert item["text"] in response.text

    def test_get_checklist_has_correct_nav_state(self, client):
        response = client.get("/checklist")
        assert 'aria-current="page"' in response.text

    def test_get_checklist_shows_initial_score(self, client):
        response = client.get("/checklist")
        assert "readiness" in response.text.lower() or "score" in response.text.lower()


class TestChecklistToggle:
    def test_toggle_item_updates_session(self, csrf_client):
        response = csrf_client.post("/checklist/toggle/c1")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_toggle_all_items(self, csrf_client):
        for item in CHECKLIST_ITEMS:
            response = csrf_client.post(f"/checklist/toggle/{item['id']}")
            assert response.status_code == 200

    def test_toggle_then_untoggle(self, csrf_client):
        csrf_client.post("/checklist/toggle/c1")
        response = csrf_client.post("/checklist/toggle/c1")
        assert response.status_code == 200

    def test_toggle_unknown_item_still_works(self, csrf_client):
        response = csrf_client.post("/checklist/toggle/unknown_item")
        assert response.status_code == 200
