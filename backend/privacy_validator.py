"""
backend/privacy_validator.py

Privacy, Data Sanitization & Input Validation for MindSenseAI (Security Hardening Phase 4).
Provides:
- Bounded input validation for user profiles, credentials, chat, and emergency contacts
- Robust rejection of NUL bytes (\\x00) and dangerous control characters
- Safe length bounding for string fields (names, titles, messages, emails, phone numbers)
- Safe international phone number format validation
- PII masking utilities for logs (emails, phone numbers)
- HTML injection defense utilities (HTML escaping)
- Generic exception sanitization to prevent internal server error leakage
"""

import html
import re
from typing import Optional
from fastapi import HTTPException, status


# ---------------------------------------------------------------------------
# PII Masking Utilities for Server Logs
# ---------------------------------------------------------------------------

def mask_email(email: Optional[str]) -> str:
    """Mask email address for privacy in logs (e.g. jo****e@example.com)."""
    if not email or "@" not in email:
        return "****"
    try:
        user_part, domain = email.strip().split("@", 1)
        if len(user_part) <= 2:
            masked_user = user_part[0] + "*"
        else:
            masked_user = user_part[:2] + "****" + user_part[-1:]
        return f"{masked_user}@{domain}"
    except Exception:
        return "****"


def mask_phone_number(phone: Optional[str]) -> str:
    """Mask phone number for privacy in server logs (e.g. +91****01)."""
    if not phone:
        return "****"
    s = str(phone).strip()
    if len(s) <= 4:
        return "****"
    return f"{s[:2]}****{s[-2:]}"


# ---------------------------------------------------------------------------
# String & Text Validation
# ---------------------------------------------------------------------------

def validate_string_field(
    value: str,
    field_name: str = "Field",
    min_len: int = 1,
    max_len: int = 255,
    allow_empty: bool = False,
    reject_control_chars: bool = True,
) -> str:
    """Validate a generic string field:
    - Type checking
    - Rejects NUL bytes (\\x00)
    - Rejects dangerous control characters (ASCII < 32 except newline, tab, carriage return)
    - Enforces min and max length bounds
    - Preserves multilingual Unicode text (Hindi, Tamil, emojis, accented Latin, etc.)
    """
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a string.",
        )

    # Reject NUL bytes immediately
    if "\x00" in value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains invalid characters.",
        )

    # Reject non-printable control characters if requested
    if reject_control_chars:
        for ch in value:
            code = ord(ch)
            if code < 32 and ch not in ("\n", "\r", "\t"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} contains invalid control characters.",
                )

    trimmed = value.strip()
    if not allow_empty and not trimmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be empty or whitespace only.",
        )

    if len(value) > max_len:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} exceeds maximum length of {max_len} characters.",
        )

    if not allow_empty and len(trimmed) < min_len:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_len} characters long.",
        )

    return trimmed


# ---------------------------------------------------------------------------
# Specific Field Validators
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> str:
    """Validate email address bounds and format:
    - RFC 5321 maximum email length is 254 octets
    - Rejects NUL bytes, spaces, multiple @-signs
    - Validates local-part and domain-part structure, rejecting consecutive dots and malformed domains
    """
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required.",
        )

    if "\x00" in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email contains invalid characters.",
        )

    cleaned = email.strip()
    if " " in cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address cannot contain spaces.",
        )

    if len(cleaned) < 5 or len(cleaned) > 254:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address length must be between 5 and 254 characters.",
        )

    if cleaned.count("@") != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address format.",
        )

    local_part, domain_part = cleaned.split("@")
    if (
        not local_part
        or len(local_part) > 64
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email username format.",
        )

    if (
        not domain_part
        or len(domain_part) > 189
        or domain_part.startswith(".")
        or domain_part.endswith(".")
        or ".." in domain_part
        or "." not in domain_part
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email domain format.",
        )

    parts = domain_part.split(".")
    if len(parts[-1]) < 2 or not parts[-1].isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email top-level domain.",
        )

    for part in parts:
        if not part or not re.match(r"^[a-zA-Z0-9-]+$", part) or part.startswith("-") or part.endswith("-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email domain component.",
            )

    return cleaned.lower()


# Allows international prefix +, digits, spaces, hyphens, parentheses (7 to 25 chars)
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,25}$")


def validate_phone_number(phone: str, field_name: str = "Phone number") -> str:
    """Validate international phone number input:
    - Between 7 and 25 characters
    - Must contain between 7 and 15 actual numeric digits (ITU-T E.164)
    - Rejects letters, HTML, SQL characters, control characters, NUL bytes
    - Rejects all-identical repeated digits (e.g. 0000000000, 9999999999)
    - Rejects malformed country code like +0...
    - Supports legitimate international formats (+91 ..., +1 ..., (555) ..., etc.)
    """
    if not phone or not isinstance(phone, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )

    if "\x00" in phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains invalid characters.",
        )

    cleaned = phone.strip()
    if len(cleaned) < 7 or len(cleaned) > 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be between 7 and 25 characters long.",
        )

    if not PHONE_REGEX.match(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid phone number (digits, optional + prefix, spaces or hyphens).",
        )

    if cleaned.startswith("+") and cleaned.startswith("+0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} has an invalid country code.",
        )

    digits = [c for c in cleaned if c.isdigit()]
    if len(digits) < 7 or len(digits) > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must contain between 7 and 15 digits.",
        )

    digits_str = "".join(digits)
    if len(set(digits)) == 1 or re.search(r"(\d)\1{6,}", digits_str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot consist of repeated dummy digits.",
        )

    return cleaned


def validate_full_name(name: str, field_name: str = "Full name") -> str:
    """Validate full name: 1 to 100 characters, no NUL/control characters."""
    return validate_string_field(
        value=name,
        field_name=field_name,
        min_len=1,
        max_len=100,
        allow_empty=False,
        reject_control_chars=True,
    )


def validate_session_title(title: str) -> str:
    """Validate chat session title: 1 to 200 characters, no NUL/control characters."""
    return validate_string_field(
        value=title,
        field_name="Session title",
        min_len=1,
        max_len=200,
        allow_empty=False,
        reject_control_chars=True,
    )


def validate_chat_message(message: str) -> str:
    """Validate incoming chat message:
    - Rejects NUL bytes (\\x00)
    - Rejects empty or whitespace-only messages
    - Enforces maximum length of 5000 characters
    - Preserves normal Unicode text, emojis, and multilingual script
    """
    if not isinstance(message, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat message must be a string.",
        )

    if "\x00" in message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message contains invalid characters.",
        )

    if not message or not message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat message cannot be empty or whitespace only.",
        )

    if len(message) > 5000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message exceeds maximum allowed length of 5000 characters.",
        )

    return message


LANGUAGE_REGEX = re.compile(r"^[a-zA-Z0-9\-_]{1,20}$")


def sanitize_language_code(lang: Optional[str]) -> str:
    """Sanitize language parameter to safe bounded identifier, defaulting to 'en'."""
    if not lang or not isinstance(lang, str):
        return "en"
    cleaned = lang.strip().lower()
    if not LANGUAGE_REGEX.match(cleaned):
        return "en"
    return cleaned[:20]


def sanitize_html(text: Optional[str]) -> str:
    """Safely escape text for inclusion in HTML contexts (such as email templates)."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)
