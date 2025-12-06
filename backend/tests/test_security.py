"""Tests for security utilities."""
import pytest

from app.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    validate_password,
    validate_phone,
    verify_password,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_password_validation():
    """Test password strength validation."""
    # Valid password
    is_valid, msg = validate_password("TestPassword123")
    assert is_valid
    assert msg == ""

    # Too short
    is_valid, msg = validate_password("Short1")
    assert not is_valid
    assert "at least" in msg.lower()

    # Missing uppercase
    is_valid, msg = validate_password("testpassword123")
    assert not is_valid
    assert "uppercase" in msg.lower()

    # Missing lowercase
    is_valid, msg = validate_password("TESTPASSWORD123")
    assert not is_valid
    assert "lowercase" in msg.lower()

    # Missing digits
    is_valid, msg = validate_password("TestPassword")
    assert not is_valid
    assert "digit" in msg.lower()


def test_phone_validation():
    """Test phone number validation."""
    assert validate_phone("13800138000")
    assert validate_phone("15912345678")
    assert not validate_phone("12345678901")  # Doesn't start with 1
    assert not validate_phone("1380013800")  # Too short
    assert not validate_phone("138001380000")  # Too long
    assert not validate_phone("abc12345678")  # Contains letters


def test_jwt_token():
    """Test JWT token creation and decoding."""
    subject = "13800138000"
    token = create_access_token(subject)
    assert token is not None
    assert len(token) > 0

    payload = decode_token(token)
    assert payload.sub == subject
    assert payload.exp is not None

