from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_rate_limiting_ask_why():
    # Make multiple requests to trigger rate limiting
    # Limit is 20/minute
    responses = []
    payload = {
        "topic_id": "voter_id",
        "country": "US",
        "state": "CA",
        "timeline_context": {
            "jurisdiction": {"country": "US", "state": "CA"},
            "milestones": [],
            "checklist": [],
            "official_links": [],
            "source_notes": []
        }
    }
    for _ in range(21):
        response = client.post("/ask-why", json=payload)
        responses.append(response.status_code)
    
    # At least one response should be 429 Too Many Requests
    assert 429 in responses

def test_xss_sanitization():
    # Test that HTML tags are stripped from input
    response = client.post("/wizard/step/1", data={"country": "<script>alert('xss')</script>US"})
    assert response.status_code == 200
    assert "<script>" not in response.text
