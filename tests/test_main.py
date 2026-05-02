from fastapi.testclient import TestClient
from app.main import app
import pytest


def test_read_main():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Election Process Education Assistant" in response.text


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


def test_security_headers():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"


def test_wizard_step1():
    with TestClient(app) as client:
        response = client.get("/wizard/step/1")
        assert response.status_code == 200


def test_quiz_landing():
    with TestClient(app) as client:
        response = client.get("/quiz")
        assert response.status_code == 200


def test_404_handler():
    with TestClient(app) as client:
        response = client.get("/nonexistent_route")
        assert response.status_code == 404


def test_readiness_dashboard():
    with TestClient(app) as client:
        response = client.get("/readiness?country=US&state=CA")
        assert response.status_code == 200
        assert "Readiness" in response.text


def test_healthz_version():
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.json()["version"] == "2.0.0"
