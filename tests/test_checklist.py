"""Tests for the Smart Checklist + Readiness Score feature."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.checklist import CHECKLIST_ITEMS


@pytest.fixture
def client():
    with TestClient(app) as c:
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
        # Should display a readiness score even with no items checked
        assert "readiness" in response.text.lower() or "score" in response.text.lower()


class TestChecklistToggle:
    def test_toggle_item_updates_session(self, client):
        response = client.post("/checklist/toggle/c1")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_toggle_all_items(self, client):
        for item in CHECKLIST_ITEMS:
            response = client.post(f"/checklist/toggle/{item['id']}")
            assert response.status_code == 200

    def test_toggle_then_untoggle(self, client):
        # Toggle on
        client.post("/checklist/toggle/c1")
        # Toggle off
        response = client.post("/checklist/toggle/c1")
        assert response.status_code == 200

    def test_toggle_unknown_item_still_works(self, client):
        # The route accepts any item_id; it just adds to session state
        response = client.post("/checklist/toggle/unknown_item")
        assert response.status_code == 200
