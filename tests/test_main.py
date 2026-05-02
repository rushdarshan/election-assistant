from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "Election Process Education Assistant" in response.text

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}

def test_security_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"

def test_wizard_step1():
    response = client.get("/wizard/step/1")
    assert response.status_code == 200

def test_quiz_landing():
    response = client.get("/quiz")
    assert response.status_code == 200

def test_404_handler():
    response = client.get("/nonexistent_route")
    assert response.status_code == 404

def test_method_not_allowed():
    response = client.post("/")
    assert response.status_code == 405

def test_readiness_dashboard():
    response = client.get("/readiness?country=US&state=CA")
    assert response.status_code == 200
    assert "Readiness" in response.text
