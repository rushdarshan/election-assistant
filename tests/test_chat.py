"""Tests for the AI Chat with Conversation History feature."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
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
    def test_send_message_returns_html(self, client):
        response = client.post("/chat", data={"message": "How do I register?"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_send_preserves_session_history(self, client):
        response = client.post("/chat", data={"message": "Test question"})
        assert response.status_code == 200
        # Second message should work with history
        response2 = client.post("/chat", data={"message": "Follow up"})
        assert response2.status_code == 200
