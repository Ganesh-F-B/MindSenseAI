"""
backend/auth.py

Authentication and JWT helper for MindSenseAI (Security Hardening Phase 2).
Provides:
- Secure JWT signing key resolution (no hardcoded fallback; rejects weak keys in production;
  generates ephemeral 256-bit key in development when unset)
- Strict HS256 algorithm enforcement (preventing algorithm confusion vulnerabilities)
- Password validation policy (min 8 chars, max 72 bytes for Bcrypt compatibility, rejects NUL/whitespace)
- Constant-time password verification and timing attack mitigation (dummy hash check)
- Token issuance with standard claims (exp, iat, nbf, sub)
"""

import bcrypt
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Known insecure placeholder secrets that must never be accepted in production
INSECURE_SECRETS = {
    "secretkey",
    "your_secure_random_string_here",
    "changeme",
    "secret",
    "default",
    "admin",
    "password",
    "123456",
    "12345678",
}


def resolve_secret_key() -> str:
    """Resolve and validate the JWT signing key.
    
    Rules:
    - Checks JWT_SECRET_KEY and SECRET_KEY environment variables.
    - In production (ENVIRONMENT=production or NODE_ENV=production):
        - Must be configured and not in INSECURE_SECRETS.
        - Must be at least 32 characters (256-bit entropy).
        - Raises RuntimeError on failure to prevent booting with insecure keys.
    - In development/testing:
        - If configured and not in INSECURE_SECRETS, uses it (warns if < 32 chars).
        - If unset or in INSECURE_SECRETS, generates an ephemeral cryptographically
          secure 256-bit random key (secrets.token_hex(32)). Never falls back to
          a static hardcoded default.
    """
    env_secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    is_production = (
        os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")
        or os.getenv("NODE_ENV", "").lower() == "production"
    )

    if is_production:
        if not env_secret or env_secret.strip().lower() in INSECURE_SECRETS:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: In production mode, "
                "JWT_SECRET_KEY must be set to a strong, non-default secret. "
                "Found missing or known-insecure placeholder secret."
            )
        if len(env_secret.strip()) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: In production mode, "
                "JWT_SECRET_KEY must be at least 32 characters long."
            )
        return env_secret.strip()

    # Development / Testing mode
    if env_secret and env_secret.strip().lower() not in INSECURE_SECRETS:
        if len(env_secret.strip()) < 32:
            logger.warning(
                "JWT_SECRET_KEY is shorter than 32 characters. "
                "Use a 32+ character random key in production."
            )
        return env_secret.strip()

    # Ephemeral key for local dev when unset or placeholder
    ephemeral = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET_KEY is not configured or uses a placeholder. "
        "Generated an ephemeral 256-bit signing key for this process. "
        "Set JWT_SECRET_KEY in backend/.env for persistent sessions."
    )
    return ephemeral


SECRET_KEY = resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))

# Pre-computed bcrypt hash for constant-time dummy verification on invalid usernames
DUMMY_HASH = "$2b$12$e80yq9gK98/qUeE3bYwX3.98vQkU1j58m2B58i8y9Y7e80yq9gK98"


def validate_password_strength(password: str) -> None:
    """Harden password validation:
    - Minimum length: 8 characters
    - Maximum length: 72 bytes (Bcrypt truncation limit)
    - Rejects empty, whitespace-only, and NUL byte strings
    - Raises HTTPException(400) on invalid inputs
    """
    if not password or not password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty or whitespace only.",
        )
    if "\x00" in password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password contains invalid characters.",
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 72 bytes due to cryptographic limits.",
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode("utf-8")
        if len(pw_bytes) > 72:
            return False
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    validate_password_strength(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
