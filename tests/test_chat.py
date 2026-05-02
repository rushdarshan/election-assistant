"""Tests for the AI Chat with Conversation History feature."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def csrf_client():
    """Client with CSRF cookie pre-loaded for form POSTs."""
    with TestClient(app) as c:
        c.get("/")
        token = c.cookies.get("csrftoken")
        if token:
            c.headers["X-CSRFToken"] = token
        yield c


class TestChatPage:
    def test_get_chat_returns_200(self, client):
        response = client.get("/chat")
        assert response.status_code == 200

    def test_get_chat_has_chat_word_in_response(self, client):
        response = client.get("/chat")
        assert "chat" in response.text.lower()

    def test_get_chat_has_correct_nav_state(self, client):
        response = client.get("/chat")
        assert 'aria-current="page"' in response.text


class TestChatSend:
    def test_send_message_returns_html(self, csrf_client):
        response = csrf_client.post("/chat", data={"message": "How do I register?"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_send_preserves_session_history(self, csrf_client):
        response = csrf_client.post("/chat", data={"message": "Test question"})
        assert response.status_code == 200
        response2 = csrf_client.post("/chat", data={"message": "Follow up"})
        assert response2.status_code == 200
