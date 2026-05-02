"""Tests for authentication endpoints and JWT verification."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestAuthRegistration:
    """Test user registration flow."""

    def test_register_success(self, client):
        """Successful registration returns token and user data."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "securepassword123",
            "name": "Test User",
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["name"] == "Test User"

    def test_register_duplicate_email(self, client):
        """Registration with existing email returns 409."""
        client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": "password123",
            "name": "First",
        })
        response = client.post("/auth/register", json={
            "email": "dup@example.com",
            "password": "password456",
            "name": "Second",
        })
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        """Registration with short password returns 422."""
        response = client.post("/auth/register", json={
            "email": "weak@example.com",
            "password": "short",
            "name": "Weak",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        """Registration with invalid email returns 422."""
        response = client.post("/auth/register", json={
            "email": "notanemail",
            "password": "password123",
            "name": "Invalid",
        })
        assert response.status_code == 422


class TestAuthLogin:
    """Test user login flow."""

    def test_login_success(self, client):
        """Successful login returns token."""
        client.post("/auth/register", json={
            "email": "login@example.com",
            "password": "password123",
            "name": "Login User",
        })
        response = client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
        assert response.status_code == 200
        assert "token" in response.json()

    def test_login_wrong_password(self, client):
        """Login with wrong password returns 401."""
        client.post("/auth/register", json={
            "email": "wrong@example.com",
            "password": "correct",
            "name": "Wrong",
        })
        response = client.post("/auth/login", json={
            "email": "wrong@example.com",
            "password": "incorrect",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent email returns 401."""
        response = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert response.status_code == 401


class TestAuthMe:
    """Test authenticated user profile endpoint."""

    def test_get_me_with_token(self, client):
        """GET /auth/me returns user profile with valid token."""
        register_response = client.post("/auth/register", json={
            "email": "me@example.com",
            "password": "password123",
            "name": "Me User",
        })
        token = register_response.json()["token"]

        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["name"] == "Me User"

    def test_get_me_without_token(self, client):
        """GET /auth/me without token returns 401."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_with_invalid_token(self, client):
        """GET /auth/me with invalid token returns 401."""
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer invalid-token-here"
        })
        assert response.status_code == 401


class TestProfileUpdate:
    """Test profile update endpoint."""

    def test_update_profile(self, client):
        """POST /auth/profile/update updates user fields."""
        register_response = client.post("/auth/register", json={
            "email": "update@example.com",
            "password": "password123",
            "name": "Update User",
        })
        token = register_response.json()["token"]

        response = client.post("/auth/profile/update", json={
            "state": "CA",
            "country": "US",
            "registration_status": "yes",
        }, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["state"] == "CA"

    def test_update_profile_unauthenticated(self, client):
        """Profile update requires authentication."""
        response = client.post("/auth/profile/update", json={
            "state": "CA",
        })
        assert response.status_code == 401
