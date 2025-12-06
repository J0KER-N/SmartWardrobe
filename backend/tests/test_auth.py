"""Tests for authentication endpoints."""
import pytest
from fastapi import status


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        json={
            "phone": "13900139000",
            "password": "TestPassword123",
            "nickname": "Test User",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone"] == "13900139000"
    assert data["nickname"] == "Test User"
    assert "password" not in data


def test_register_duplicate_phone(client, test_user):
    """Test registration with duplicate phone number."""
    response = client.post(
        "/auth/register",
        json={
            "phone": test_user.phone,
            "password": "TestPassword123",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_invalid_phone(client):
    """Test registration with invalid phone number."""
    response = client.post(
        "/auth/register",
        json={
            "phone": "1234567890",
            "password": "TestPassword123",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_weak_password(client):
    """Test registration with weak password."""
    response = client.post(
        "/auth/register",
        json={
            "phone": "13900139000",
            "password": "weak",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post(
        "/auth/login",
        data={"username": test_user.phone, "password": "TestPassword123"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, test_user):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": test_user.phone, "password": "WrongPassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token(client, test_user):
    """Test token refresh."""
    # First login
    login_response = client.post(
        "/auth/login",
        data={"username": test_user.phone, "password": "TestPassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

