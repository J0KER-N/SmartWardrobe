import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings
from .schemas import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength. Returns (is_valid, error_message)."""
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters long"

    if settings.password_require_uppercase and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if settings.password_require_lowercase and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if settings.password_require_digits and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    return True, ""


def validate_phone(phone: str) -> bool:
    """Validate Chinese phone number format."""
    # Chinese mobile phone: 11 digits starting with 1
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_exp_minutes))
    to_encode = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_exp_days)
    secret = settings.jwt_refresh_secret_key or settings.jwt_secret_key
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, token_type: str = "access") -> TokenPayload:
    """Decode and validate JWT token."""
    try:
        secret = settings.jwt_refresh_secret_key if token_type == "refresh" else settings.jwt_secret_key
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        token_payload = TokenPayload(**payload)

        # Verify token type
        if payload.get("type") != token_type:
            raise ValueError(f"Invalid token type. Expected {token_type}")

        return token_payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

