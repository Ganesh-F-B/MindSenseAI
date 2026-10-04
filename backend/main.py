import torch
import logging
import os
import sys
import time
from types import MethodType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Windows consoles default to cp1252 and cannot encode the emoji characters
# used in diagnostic prints below. Reconfigure std streams to UTF-8 with a
# safe error handler so the application never crashes on print().
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.dirname(__file__)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Request,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from nlp_service import analyze_mental_state
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from deberta_predictor import predict_mental_state
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta, datetime
from jose import JWTError, jwt
from chatbot.conversation.chat_engine import ChatEngine
from chatbot.intent.predictor import IntentPredictor
from chatbot.emotion.predictor import EmotionPredictor

chat_engine = ChatEngine()
import os
import shutil
from pypdf import PdfReader

# openai-whisper replaced by Groq hosted Whisper API (no ffmpeg needed)
from groq import Groq
from gtts import gTTS
import cv2
import io
from fastapi.responses import FileResponse, Response
from upload_guard import secure_upload_context, sweep_stale_temp_uploads, UPLOAD_TMP_DIR
import requests
import re

try:
    from twilio.rest import Client as TwilioClient

    TWILIO_AVAILABLE = True
except Exception:
    TWILIO_AVAILABLE = False
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from deepface import DeepFace

    DEEPFACE_AVAILABLE = True
    print("✅ DeepFace loaded successfully")
except Exception as e:
    DeepFace = None
    DEEPFACE_AVAILABLE = False
    print(f"⚠️ DeepFace unavailable: {e}")

import html
import models, schemas, auth, rate_limiter, privacy_validator
import multilingual_normalizer
from database import engine, get_db, SessionLocal, init_db_migrations
from dotenv import load_dotenv

# Create tables and run additive schema migrations
models.Base.metadata.create_all(bind=engine)
init_db_migrations()

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning(
        "GROQ_API_KEY not set — running offline. Chat uses local rule-based "
        "responses and audio transcription is disabled."
    )

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv(
    "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
)  # default sandbox number

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "")

# Android SMS Gateway
SMS_GATE_LOGIN = os.getenv("SMS_GATE_LOGIN", "")
SMS_GATE_PASSWORD = os.getenv("SMS_GATE_PASSWORD", "")

# Green API - WhatsApp from YOUR own number (free 500 msg/month, no contact opt-in)
GREENAPI_ID_INSTANCE = os.getenv("GREENAPI_ID_INSTANCE", "")
GREENAPI_API_TOKEN = os.getenv("GREENAPI_API_TOKEN", "")

# ── FOR PUBLISHING: Meta WhatsApp Cloud API ──────────────────────────────────
# When ready to publish commercially, fill these and switch to send_whatsapp_meta()
# Setup: developers.facebook.com/docs/whatsapp/cloud-api/get-started
# Free: 1000 conversations/month with a dedicated MindSense business number
META_WA_PHONE_NUMBER_ID = os.getenv(
    "META_WA_PHONE_NUMBER_ID", ""
)  # From Meta dashboard
META_WA_ACCESS_TOKEN = os.getenv("META_WA_ACCESS_TOKEN", "")  # Permanent system token
# ─────────────────────────────────────────────────────────────────────────────

GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Whisper transcription is handled via Groq's hosted API — no local model needed

# ── Emergency Alert Cooldown ─────────────────────────────────────────────────
# Tracks last alert time per session to avoid spamming contacts on every message
# Format: { session_id: datetime_of_last_alert }
_last_alert_time: dict = {}
ALERT_COOLDOWN_MINUTES = 15
# ─────────────────────────────────────────────────────────────────────────────


# ── Language Detection ────────────────────────────────────────────────────────
def detect_language(text: str) -> dict:
    """
    Detect language of user message using generalized multi-script Unicode
    inspection and transliteration token matching.
    Returns dict: { "name": str, "script": "latin" | "native", "code": str }
    """
    return multilingual_normalizer.detect_language_generalized(text)


# ─────────────────────────────────────────────────────────────────────────────


ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development")).lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# In production, disable debug mode and selectively configure documentation
app = FastAPI(
    debug=False,
    docs_url=None if (IS_PRODUCTION and os.getenv("DISABLE_DOCS", "false").lower() == "true") else "/docs",
    redoc_url=None if (IS_PRODUCTION and os.getenv("DISABLE_DOCS", "false").lower() == "true") else "/redoc",
    openapi_url=None if (IS_PRODUCTION and os.getenv("DISABLE_DOCS", "false").lower() == "true") else "/openapi.json",
)

# Trusted proxies list for forwarded headers (X-Forwarded-Proto, X-Forwarded-For)
TRUSTED_PROXIES_STR = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
TRUSTED_PROXIES = {p.strip() for p in TRUSTED_PROXIES_STR.split(",") if p.strip()}


def is_trusted_proxy(client_ip: Optional[str]) -> bool:
    if not client_ip:
        return False
    return client_ip in TRUSTED_PROXIES or "*" in TRUSTED_PROXIES


def validate_origin(origin: str) -> bool:
    """Validate origin string: must be http:// or https:// with valid hostname, no wildcard, no path."""
    if not origin or origin == "*" or not (origin.startswith("http://") or origin.startswith("https://")):
        return False
    # No path components allowed in CORS origin
    parts = origin.split("://", 1)[-1].split("/")
    if len(parts) > 1 and parts[1]:
        return False
    return True


# Environment-based and development CORS origins
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
]
env_origins_str = os.getenv("ALLOWED_ORIGINS", "")
raw_env_origins = [o.strip() for o in env_origins_str.split(",") if o.strip()]
valid_env_origins = [o for o in raw_env_origins if validate_origin(o)]

if IS_PRODUCTION:
    # In production, require explicit origins from env or verified production deployment
    base_prod = ["https://mind-sense-ai-two.vercel.app"]
    cors_origins = list(dict.fromkeys(valid_env_origins + base_prod))
else:
    cors_origins = list(dict.fromkeys(DEV_ORIGINS + valid_env_origins + ["https://mind-sense-ai-two.vercel.app"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Production-aware HSTS: enabled only when direct HTTPS or X-Forwarded-Proto is HTTPS from a TRUSTED proxy
        is_https = request.url.scheme == "https"
        if not is_https and request.headers.get("x-forwarded-proto") == "https":
            client_ip = request.client.host if request.client else None
            if is_trusted_proxy(client_ip):
                is_https = True

        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


app.add_middleware(SecurityHeadersMiddleware)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
async def on_startup():
    sweep_stale_temp_uploads()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            auth.SECRET_KEY,
            algorithms=[auth.ALGORITHM],
            options={"verify_signature": True, "verify_exp": True},
        )
        email: str = payload.get("sub")
        if not email or not isinstance(email, str):
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


# ---------- AUTH ----------


@app.post("/signup", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.get_client_ip(request)
    rate_limiter.enforce_rate_limit(f"ip:{client_ip}:signup", rate_limiter.AUTH_SIGNUP_CONFIG, "signup")

    privacy_validator.validate_email(user.email)
    clean_full_name = privacy_validator.validate_full_name(user.full_name, "Full name")
    clean_phone = privacy_validator.validate_phone_number(user.phone_number, "User phone number")
    auth.validate_password_strength(user.password)

    if len(user.emergency_contacts) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 emergency contacts are required"
        )
    if len(user.emergency_contacts) > 10:
        raise HTTPException(
            status_code=400, detail="Maximum 10 emergency contacts allowed"
        )

    for contact in user.emergency_contacts:
        contact.name = privacy_validator.validate_full_name(contact.name, "Contact name")
        contact.phone_number = privacy_validator.validate_phone_number(contact.phone_number, "Contact phone number")
        if contact.callmebot_key:
            contact.callmebot_key = privacy_validator.validate_string_field(
                contact.callmebot_key, "CallMeBot key", min_len=0, max_len=100, allow_empty=True
            )

    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=clean_full_name,
        phone_number=clean_phone,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    for contact in user.emergency_contacts:
        db_contact = models.EmergencyContact(
            name=contact.name, phone_number=contact.phone_number, user_id=db_user.id
        )
        db.add(db_contact)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = rate_limiter.get_client_ip(request)
    rate_limiter.enforce_rate_limit(f"ip:{client_ip}:token", rate_limiter.AUTH_TOKEN_CONFIG, "login")

    # Anti-enumeration input sanitize: reject malformed/NUL/oversized usernames with generic 401
    if (
        not form_data.username
        or len(form_data.username) > 254
        or "\x00" in form_data.username
        or "\x00" in (form_data.password or "")
    ):
        auth.verify_password(form_data.password or "", auth.DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        # Constant-time dummy verification prevents timing-based account enumeration
        auth.verify_password(form_data.password, auth.DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(get_current_user),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:read_me", rate_limiter.GENERAL_READ_CONFIG, "profile read")
    return current_user


@app.delete("/users/me")
def delete_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Permanently delete user account and all associated data."""
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:delete_account", rate_limiter.STATE_CHANGE_CONFIG, "account deletion")
    try:
        # Delete all chat history and sessions
        session_ids = [
            s.id
            for s in db.query(models.ChatSession)
            .filter(models.ChatSession.user_id == current_user.id)
            .all()
        ]
        if session_ids:
            db.query(models.ChatHistory).filter(
                models.ChatHistory.session_id.in_(session_ids)
            ).delete(synchronize_session=False)
        db.query(models.ChatSession).filter(
            models.ChatSession.user_id == current_user.id
        ).delete()
        # Delete emergency contacts
        db.query(models.EmergencyContact).filter(
            models.EmergencyContact.user_id == current_user.id
        ).delete()
        # Delete user
        db.delete(current_user)
        db.commit()
        return {"message": "Account permanently deleted."}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete account: {type(e).__name__}")
        raise HTTPException(
            status_code=500, detail="Failed to delete account."
        )


def send_emergency_email(to_email: str, user_name: str, contacts: list) -> bool:
    """Send emergency alert email via Gmail SMTP (free backup channel)."""
    if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        print(
            "[EMAIL] Gmail not configured. Add GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD to .env"
        )
        return False
    try:
        safe_user_name = html.escape(str(user_name or "A user"))
        contacts_html = "".join(
            f"<tr><td style='padding:8px 12px;color:#fff;border-bottom:1px solid #333'>{html.escape(str(c.name))}</td>"
            f"<td style='padding:8px 12px;color:#aaa;border-bottom:1px solid #333'>{html.escape(str(c.phone_number))}</td></tr>"
            for c in contacts
        )
        html_body = f"""
        <div style="font-family:Arial,sans-serif;background:#0a0a0f;color:#fff;padding:32px;border-radius:16px;max-width:520px;margin:auto">
          <div style="background:#ef4444;border-radius:12px;padding:16px 24px;margin-bottom:24px">
            <span style="font-size:24px">🚨</span>
            <span style="font-size:18px;font-weight:bold;margin-left:10px">EMERGENCY ALERT – MindSense AI</span>
          </div>
          <p style="font-size:15px;color:#e2e8f0"><strong style="color:#f87171">{safe_user_name}</strong> may be in emotional distress and needs immediate attention.</p>
          <table style="width:100%;border-collapse:collapse;margin-top:16px;background:#1e293b;border-radius:10px;overflow:hidden">
            <thead><tr style="background:#1d4ed8">
              <th style="padding:10px 12px;text-align:left;color:#bfdbfe">Contact</th>
              <th style="padding:10px 12px;text-align:left;color:#bfdbfe">Phone</th>
            </tr></thead>
            <tbody>{contacts_html}</tbody>
          </table>
          <p style="color:#64748b;font-size:12px;margin-top:24px">Automated alert from MindSense AI. Do not reply.</p>
        </div>"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 URGENT: {safe_user_name} needs help – MindSense AI"
        msg["From"] = GMAIL_SENDER_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL SENT ✓] → {privacy_validator.mask_email(to_email)}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {type(e).__name__}")
        return False


def mask_phone_number(phone: str) -> str:
    """Mask phone number for privacy in server logs, e.g. +9198****10 or 98****10."""
    if not phone:
        return "****"
    s = str(phone).strip()
    if len(s) <= 4:
        return "****"
    return f"{s[:2]}****{s[-2:]}"


def normalize_phone_india(number: str) -> str:
    """Strip to 10-digit Indian number for Fast2SMS."""
    cleaned = (
        number.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("+91", "")
        .replace("+", "")
    )
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    return cleaned  # returns 10-digit number


def send_sms_fast2sms(phone_numbers: list, message: str) -> bool:
    """Send free SMS via Fast2SMS (India). Get free API key at fast2sms.com"""
    if not FAST2SMS_API_KEY:
        print("[SMS] Fast2SMS not configured. Add FAST2SMS_API_KEY to .env")
        return False
    try:
        numbers = ",".join([normalize_phone_india(n) for n in phone_numbers])
        masked = [mask_phone_number(n) for n in phone_numbers]
        print(f"[SMS Fast2SMS] Dispatching to: {masked}")
        response = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={
                "authorization": FAST2SMS_API_KEY,
                "Content-Type": "application/json",
            },
            json={"route": "q", "message": message, "numbers": numbers},
            timeout=10,
        )
        data = response.json()
        print(f"[SMS Fast2SMS] Response status: {data.get('return')}")
        return data.get("return") == True
    except Exception as e:
        logger.error(f"[SMS ERROR] Fast2SMS: {type(e).__name__}")
        return False


def send_sms_android_gateway(phone_numbers: list, message: str) -> bool:
    """Send FREE SMS via Android SMS Gate app (sms-gate.app).
    Install 'SMS Gate' app on your Android phone → sign up free → get login/password.
    Your phone's SIM sends the SMS — works without internet on receiver's end.
    """
    if not SMS_GATE_LOGIN or not SMS_GATE_PASSWORD:
        print(
            "[SMS Gate] Not configured. Add SMS_GATE_LOGIN and SMS_GATE_PASSWORD to .env"
        )
        return False
    try:
        # Normalize numbers to E.164 format
        normalized = []
        for n in phone_numbers:
            cleaned = n.strip().replace(" ", "").replace("-", "")
            if not cleaned.startswith("+"):
                cleaned = f"+91{cleaned.lstrip('91')}"
            normalized.append(cleaned)

        import base64

        credentials = base64.b64encode(
            f"{SMS_GATE_LOGIN}:{SMS_GATE_PASSWORD}".encode()
        ).decode()
        masked = [mask_phone_number(n) for n in phone_numbers]
        print(f"[SMS Gate] Dispatching to: {masked}")
        response = requests.post(
            "https://api.sms-gate.app/3rdparty/v1/message",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            json={"message": message, "phoneNumbers": normalized},
            timeout=15,
        )
        data = response.json()
        print(f"[SMS Gate] Response received: id={data.get('id', 'N/A')}")
        # Success if we get an id back
        return "id" in data or response.status_code == 202
    except Exception as e:
        logger.error(f"[SMS Gate ERROR]: {type(e).__name__}")
        return False


def send_whatsapp_callmebot(contacts: list, message: str) -> bool:
    """Send FREE WhatsApp via CallMeBot (100% free, no trial, no credits).
    Each contact must opt-in once: save +34644597621 on WhatsApp and send
    'I allow callmebot to send me messages' to get their personal API key.
    """
    sent = 0
    for c in contacts:
        key = getattr(c, "callmebot_key", "") or ""
        phone = c.phone_number.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = f"+91{phone.lstrip('91').lstrip('+91')}"
        if not key:
            print("[WhatsApp] Skipping contact without CallMeBot key.")
            continue
        try:
            encoded_msg = requests.utils.quote(message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                print(f"[WhatsApp SENT ✓] → {mask_phone_number(phone)}")
                sent += 1
            else:
                print(f"[WhatsApp ERROR] CallMeBot status code: {resp.status_code}")
        except Exception:
            print("[WhatsApp ERROR] CallMeBot dispatch request failed")
    return sent > 0


def send_whatsapp_greenapi(phone_numbers: list, message: str) -> bool:
    """Send WhatsApp from YOUR OWN number via Green API.
    Free tier: 500 messages/month. No contact opt-in needed.
    Setup: green-api.com → create free instance → scan QR with WhatsApp.
    """
    if not GREENAPI_ID_INSTANCE or not GREENAPI_API_TOKEN:
        print(
            "[Green API] Not configured. Add GREENAPI_ID_INSTANCE and GREENAPI_API_TOKEN to .env"
        )
        return False
    sent = 0
    for number in phone_numbers:
        try:
            # Format: 919876543210@c.us (country code + number, no +)
            cleaned = number.strip().replace(" ", "").replace("-", "").lstrip("+")
            if cleaned.startswith("91") and len(cleaned) == 12:
                chat_id = f"{cleaned}@c.us"
            elif len(cleaned) == 10:
                chat_id = f"91{cleaned}@c.us"
            else:
                chat_id = f"{cleaned}@c.us"

            url = f"https://api.green-api.com/waInstance{GREENAPI_ID_INSTANCE}/sendMessage/{GREENAPI_API_TOKEN}"
            resp = requests.post(
                url, json={"chatId": chat_id, "message": message}, timeout=15
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("idMessage"):
                print(f"[WhatsApp Green API ✓] → {mask_phone_number(number)}")
                sent += 1
            else:
                print(f"[WhatsApp Green API ERROR] {mask_phone_number(number)}: Status {resp.status_code}")
        except Exception:
            print(f"[WhatsApp Green API ERROR] {mask_phone_number(number)}: Dispatch failed")
    return sent > 0


# ── FOR PUBLISHING: Meta WhatsApp Cloud API ───────────────────────────────────
# Uncomment the call in trigger_emergency() and the chat crisis block to use this
# instead of Green API when you go live with a real MindSense business number.
def send_whatsapp_meta(phone_numbers: list, message: str) -> bool:
    """Send WhatsApp via official Meta Cloud API.
    Uses a dedicated MindSense business number — professional sender for all users.
    Free: 1000 conversations/month. Setup: developers.facebook.com/docs/whatsapp
    """
    if not META_WA_PHONE_NUMBER_ID or not META_WA_ACCESS_TOKEN:
        print(
            "[Meta WA] Not configured. Add META_WA_PHONE_NUMBER_ID and META_WA_ACCESS_TOKEN to .env"
        )
        return False
    sent = 0
    url = f"https://graph.facebook.com/v19.0/{META_WA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    for number in phone_numbers:
        try:
            cleaned = number.strip().replace(" ", "").replace("-", "").lstrip("+")
            if len(cleaned) == 10:
                cleaned = f"91{cleaned}"
            payload = {
                "messaging_product": "whatsapp",
                "to": cleaned,
                "type": "text",
                "text": {"body": message},
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get("messages"):
                print(f"[Meta WA SENT ✓] → {mask_phone_number(number)}")
                sent += 1
            else:
                print(f"[Meta WA ERROR] {mask_phone_number(number)}: Status {resp.status_code}")
        except Exception:
            print(f"[Meta WA ERROR] {mask_phone_number(number)}: Dispatch failed")
    return sent > 0


# ─────────────────────────────────────────────────────────────────────────────


@app.post("/emergency")
def trigger_emergency(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:emergency", rate_limiter.EMERGENCY_CONFIG, "emergency alert")
    contacts = (
        db.query(models.EmergencyContact)
        .filter(models.EmergencyContact.user_id == current_user.id)
        .all()
    )
    if not contacts:
        return {
            "message": "No emergency contacts found. Please add contacts in your Profile page."
        }

    contact_names = [c.name for c in contacts]
    phone_numbers = [c.phone_number for c in contacts]
    alert_text = (
        f"🚨 URGENT: {current_user.full_name} may be in emotional distress and needs "
        f"your immediate attention. This is an automated alert from MindSense AI."
    )

    results = []

    # 🥇 Channel 1: WhatsApp via Green API (YOUR own WhatsApp — seen instantly like a normal message)
    if send_whatsapp_greenapi(phone_numbers, alert_text):
        results.append("WhatsApp")

    # 🥈 Channel 2: SMS via Android SMS Gateway (YOUR SIM — works even without internet on receiver)
    if send_sms_android_gateway(phone_numbers, alert_text):
        results.append("SMS")

    # 🥉 Channel 3: WhatsApp via CallMeBot (if contacts have set their key in Profile)
    if send_whatsapp_callmebot(contacts, alert_text):
        if "WhatsApp" not in results:
            results.append("WhatsApp")

    # 📧 Channel 4: Email backup (always try)
    if send_emergency_email(current_user.email, current_user.full_name, contacts):
        results.append("Email")

    contacts_display = ", ".join(contact_names)
    if results:
        return {
            "message": f"✅ Emergency alert sent via {' + '.join(results)} to {contacts_display}."
        }
    else:
        manual = ", ".join([f"{c.name} ({mask_phone_number(c.phone_number)})" for c in contacts])
        return {
            "message": f"⚠️ Notifications not configured yet. Please call manually: {manual}"
        }


class EmergencyContactUpdate(schemas.BaseModel):
    contacts: List[schemas.ContactCreate]


@app.put("/emergency-contacts")
def update_emergency_contacts(
    data: EmergencyContactUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:contacts", rate_limiter.STATE_CHANGE_CONFIG, "emergency contacts update")
    if len(data.contacts) < 1:
        raise HTTPException(
            status_code=400, detail="At least 1 emergency contact is required."
        )
    if len(data.contacts) > 10:
        raise HTTPException(
            status_code=400, detail="Maximum 10 emergency contacts allowed."
        )

    clean_contacts = []
    for c in data.contacts:
        clean_name = privacy_validator.validate_full_name(c.name, "Contact name")
        clean_phone = privacy_validator.validate_phone_number(c.phone_number, "Contact phone number")
        clean_key = ""
        if c.callmebot_key:
            clean_key = privacy_validator.validate_string_field(
                c.callmebot_key, "CallMeBot key", min_len=0, max_len=100, allow_empty=True
            )
        clean_contacts.append((clean_name, clean_phone, clean_key))

    # Delete existing contacts and replace with new ones
    db.query(models.EmergencyContact).filter(
        models.EmergencyContact.user_id == current_user.id
    ).delete()

    for name, phone, key in clean_contacts:
        db_contact = models.EmergencyContact(
            name=name,
            phone_number=phone,
            callmebot_key=key,
            user_id=current_user.id,
        )
        db.add(db_contact)
    db.commit()

    updated_user = (
        db.query(models.User).filter(models.User.id == current_user.id).first()
    )
    db.refresh(updated_user)
    return {
        "message": "Emergency contacts updated successfully.",
        "contacts": [
            {"name": c.name, "phone_number": c.phone_number}
            for c in updated_user.emergency_contacts
        ],
    }


# ---------- CHAT ----------
class ChatRequest(schemas.BaseModel):
    message: str
    language: str = "en"
    history: list = []
    session_id: Optional[int] = None
    emotion_context: Optional[str] = None
    emotion_confidence: Optional[float] = None


@app.get("/chat/sessions", response_model=List[schemas.ChatSession])
def get_chat_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:read_sessions", rate_limiter.GENERAL_READ_CONFIG, "sessions read")
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.updated_at.desc())
        .all()
    )
    return sessions


@app.get("/chat/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_chat_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:read_session_detail", rate_limiter.GENERAL_READ_CONFIG, "session detail read")
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


class ChatSessionUpdate(schemas.BaseModel):
    title: str


@app.put("/chat/sessions/{session_id}", response_model=schemas.ChatSession)
def update_chat_session(
    session_id: int,
    data: ChatSessionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:update_session", rate_limiter.STATE_CHANGE_CONFIG, "session update")
    clean_title = privacy_validator.validate_session_title(data.title)
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = clean_title
    db.commit()
    db.refresh(session)
    return session


@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:delete_session", rate_limiter.STATE_CHANGE_CONFIG, "session delete")
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == session_id,
            models.ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}


def extract_and_update_memory(user_id: int, user_message: str, current_memory: str):
    """Placeholder for future memory extraction; keep it lightweight and non-blocking."""
    logger.info("Memory extraction skipped for this request path")
    return


def _wrap_predictor_for_timing(predictor, timings: dict, stage_name: str):
    if getattr(predictor, "_timing_wrapped", False):
        return predictor

    original_predict = predictor.predict

    def timed_predict(text):
        start = time.perf_counter()
        try:
            return original_predict(text)
        finally:
            timings[stage_name] = max(
                timings.get(stage_name, 0.0), time.perf_counter() - start
            )

    predictor.predict = timed_predict
    predictor._timing_wrapped = True
    return predictor


def _is_imminent_crisis(text: str) -> bool:
    """Detect immediate, active harm intent, explicit suicide plan, or imminent action."""
    if not text:
        return False
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()

    imminent_patterns = [
        r"\b(?:going to|gonna|about to|will|planning to)\s+(?:kill|end|hurt|harm|slit|hang|overdose|shoot)\s+(?:myself|my life)\b",
        r"\b(?:kill|end|hurt|harm)\s+myself\s+(?:right\s+now|now|today|tonight|immediately|this\s+second|this\s+moment)\b",
        r"\b(?:taking|swallowing|downing|drank|drinking)\s+(?:all\s+the\s+)?(?:pills|poison|medicine|tablets)\b",
        r"\b(?:have|got)\s+(?:the\s+)?(?:pills|poison|medicine|tablets|knife|blade|gun|rope)\b.*\b(?:taking|swallowing|downing|using)\s+them\b",
        r"\b(?:taking|swallowing|downing)\s+(?:them|the\s+pills|all\s+the\s+pills|pills|poison)\s+(?:now|right\s+now|today|tonight)\b",
        r"\b(?:have|got)\s+(?:the\s+)?(?:pills|knife|gun|rope|blade)\s+(?:in\s+(?:my\s+)?hand|ready|with\s+me)\b",
        r"\b(?:about\s+to|going\s+to|gonna|ready\s+to)\s+jump\b",
        r"\b(?:this\s+is\s+my\s+)?(?:final|last)\s+(?:goodbye|farewell|message|note)\b",
        r"\bgoodbye\s+(?:everyone|all|cruel\s+world|forever)\b",
        r"\b(?:i\s+am|im)\s+ending\s+it\s+(?:all\s+)?(?:right\s+now|now|today|tonight)\b",
        r"\b(?:i\s+am|im)\s+doing\s+it\s+(?:right\s+now|now|today|tonight)\b",
    ]
    for pat in imminent_patterns:
        if re.search(pat, t_norm):
            return True
    return False


def _is_deescalation_reassurance(text: str) -> bool:
    """Detect clear reassurance of safety, de-escalation, life-affirmation, or rejection of self-harm."""
    if not text:
        return False
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()

    deescalation_patterns = [
        r"\b(?:i\s+am|im)\s+(?:safe|fine|okay|alright|doing\s+okay|feeling\s+better|much\s+better)\b",
        r"\b(?:yes|yeah|yep|sure)\s*,?\s*(?:i\s+am|im)\s+safe\b",
        r"\b(?:no|nope)\s*,?\s*(?:i\s+am|im)\s+safe\b",
        r"\b(?:no|nope)\s*,?\s*(?:i\s+am|im)\s+not\s+(?:going\s+to|gonna)\s+(?:do\s+it|hurt\s+myself|harm\s+myself|kill\s+myself)\b",
        r"\b(?:i\s+)?am\s+in\s+a\s+safe\s+place\b",
        r"\b(?:safe\s+right\s+now|safe\s+here|currently\s+safe)\b",
        r"\b(?:please\s+)?(?:dont|do\s+not)\s+send\s+(?:anyone|anybody|help|an?\s+alert|police)\b",
        r"\b(?:i\s+)?(?:want|wanna)\s+things\s+to\s+get\s+better\b",
        r"\bi\s+(?:will|gonna)\s+be\s+okay\b",
        r"\b(?:i\s+am|im)\s+not\s+(?:going\s+to|gonna)\s+(?:hurt|harm|kill)\s+myself\b",
        r"\b(?:dont|do\s+not|never|wont|will\s+not)\s+want\s+to\s+die\b",
        r"\b(?:i\s+)?want\s+to\s+(?:live|keep\s+living|survive|stay\s+alive)\b",
        r"\b(?:i\s+)?will\s+not\s+die\b",
        r"\b(?:i\s+)?wont\s+die\b",
        r"\b(?:i\s+am|im)\s+not\s+suicidal\b",
        r"\bno\s+imminent\s+danger\b",
        r"\bnot\s+going\s+to\s+hurt\s+myself\b",
    ]
    for pat in deescalation_patterns:
        if re.search(pat, t_norm):
            return True
    return False


def _is_historical_crisis(text: str) -> bool:
    """Detect past-tense or historical crisis expressions where user is currently stable or coping."""
    if not text:
        return False
    t = text.lower()
    t = re.sub(r"['’`]", "", t)
    t_norm = re.sub(r"[^\w\s]", " ", t)
    t_norm = re.sub(r"\s+", " ", t_norm).strip()

    past_markers = r"\b(?:felt\s+like\s+dying|felt\s+like|was\s+feeling|had\s+(?:suicidal\s+thoughts|thoughts\s+of\s+dying)|used\s+to|was\s+suicidal|earlier\s+today|yesterday|previously|last\s+(?:week|month|year))\b"
    current_coping = r"\b(?:better|fine|okay|alright|recovering|safe|doing\s+well|in\s+control|under\s+control|things\s+under\s+control|handled\s+it|past\s+it|moved\s+on)\b"

    if re.search(past_markers, t_norm) and re.search(current_coping, t_norm):
        return True
    if re.search(r"\b(?:felt\s+like\s+dying\s+earlier|was\s+suicidal\s+before|used\s+to\s+want\s+to\s+die|used\s+to\s+be\s+suicidal)\b", t_norm):
        return True
    return False


@app.post("/chat")
def chat(
    data: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:chat", rate_limiter.CHAT_CONFIG, "chat")

    privacy_validator.validate_chat_message(data.message)
    data.language = privacy_validator.sanitize_language_code(data.language)
    if data.emotion_context:
        data.emotion_context = privacy_validator.validate_string_field(
            data.emotion_context, "Emotion context", min_len=0, max_len=50, allow_empty=True
        )

    if data.history and len(data.history) > 100:
        data.history = data.history[-100:]

    request_start = time.perf_counter()
    timings = {}
    analysis = {
        "mental_state": "Normal",
        "confidence": 0.0,
        "risk_level": "LOW",
    }
    reply_final = (
        "I'm here with you. I had trouble generating a response, but I'm listening."
    )
    intent = ""
    session_id = data.session_id or 0
    session = None
    if session_id:
        session = (
            db.query(models.ChatSession)
            .filter(models.ChatSession.id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Access denied to requested chat session."
            )

    try:
        detected_lang = detect_language(data.message)
        detected_code = detected_lang.get("code", "en")
        target_lang_name = (data.language or "").lower().strip()
        if not target_lang_name or target_lang_name == "en":
            target_lang_name = detected_code if detected_code != "en" else "en"

        lang_label_map = {
            "en": "English",
            "hi": "Hindi",
            "kn": "Kannada",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "mr": "Marathi",
            "bn": "Bengali",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "ur": "Urdu",
        }
        lang_label = lang_label_map.get(target_lang_name, "English")

        translation_start = time.perf_counter()
        translated_input = data.message
        if target_lang_name != "en":
            try:
                UNIVERSAL_BYPASS = {
                    "hi", "hello", "hey", "ok", "okay", "yes", "no", "bye", "thanks", "thank you"
                }
                msg_trimmed = data.message.strip().lower().strip("!?., ")
                should_translate = (target_lang_name != "en") and (msg_trimmed not in UNIVERSAL_BYPASS)
                if should_translate:
                    trans_messages = [
                        {
                            "role": "system",
                            "content": f"You are an expert translator. Translate the user's message in {lang_label} (including transliterated or Romanized text like Kanglish or Hinglish) to English accurately. Reply with ONLY the direct English translation without notes.",
                        },
                        {"role": "user", "content": data.message},
                    ]
                    trans_res = None
                    try:
                        trans_res = groq_client.chat.completions.create(
                            model="qwen/qwen3.8-27b",
                            messages=trans_messages,
                            temperature=0.1,
                            max_tokens=150,
                            timeout=3.0,
                        )
                    except Exception:
                        trans_res = groq_client.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=trans_messages,
                            temperature=0.1,
                            max_tokens=150,
                            timeout=3.0,
                        )
                    if trans_res and trans_res.choices:
                        translated_input = (
                            trans_res.choices[0].message.content.strip() or data.message
                        )
                else:
                    translated_input = data.message
            except Exception as exc:
                logger.exception("Translation pre-processing failed")
                translated_input = data.message
        timings["Translation"] = time.perf_counter() - translation_start
        print(f"[{timings['Translation']:.2f}s] Translation")

        try:
            lang_info = detect_language(data.message)
            lang_name = lang_info.get("name", "English")
            lang_script = lang_info.get("script", "latin")
            logger.info("Language detected: %s (%s)", lang_name, lang_script)
        except Exception as exc:
            logger.exception("Language detection failed")
            lang_name = "English"
            lang_script = "latin"

        if not session:
            try:
                title = (
                    data.message[:30] + "..."
                    if len(data.message) > 30
                    else data.message
                )
                session = models.ChatSession(
                    user_id=current_user.id,
                    title=title,
                    crisis_state="no_active_crisis",
                    escalation_level="none",
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                session_id = session.id
            except Exception as exc:
                logger.exception("Failed to create chat session")
                db.rollback()
                session = None
                session_id = 0

        if session and session_id:
            try:
                user_msg = models.ChatHistory(
                    session_id=session_id, role="user", content=data.message
                )
                db.add(user_msg)
                db.commit()
            except Exception as exc:
                logger.exception("Failed to save user message")
                db.rollback()

        mental_state_start = time.perf_counter()
        try:
            analysis = predict_mental_state(
                translated_input,
                facial_emotion=data.emotion_context,
                facial_confidence=data.emotion_confidence,
            )
            analysis = {
                "mental_state": analysis.get("mental_state", "Normal"),
                "confidence": float(analysis.get("confidence", 0.0) or 0.0),
                "risk_level": analysis.get("risk_level", "LOW"),
            }
        except Exception as exc:
            logger.exception("Mental-state prediction failed")
            analysis = {
                "mental_state": "Normal",
                "confidence": 0.0,
                "risk_level": "LOW",
            }
        timings["Mental State"] = time.perf_counter() - mental_state_start
        print(f"[{timings['Mental State']:.2f}s] Mental State")

        try:
            intent_predictor = getattr(chat_engine, "intent_predictor", None)
            if intent_predictor is None:
                intent_predictor = IntentPredictor()
                chat_engine.intent_predictor = intent_predictor
            emotion_predictor = getattr(chat_engine, "emotion_predictor", None)
            if emotion_predictor is None:
                emotion_predictor = EmotionPredictor()
                chat_engine.emotion_predictor = emotion_predictor

            chat_engine_start = time.perf_counter()
            chat_result = chat_engine.chat(
                message=translated_input,
                history=data.history or [],
                memory=current_user.memory_profile or "",
                face_emotion=data.emotion_context,
            )
            timings["ChatEngine"] = time.perf_counter() - chat_engine_start
            print(f"[{timings['ChatEngine']:.2f}s] ChatEngine")
            if not isinstance(chat_result, dict):
                raise TypeError("ChatEngine.chat() did not return a dictionary")
            reply_final = str(
                chat_result.get("response") or "I'm here with you. I'm listening."
            )

            # Only ChatEngine crisis intent can override the model.

            intent = str(chat_result.get("intent", "")).lower()

        except Exception as exc:
            logger.exception("ChatEngine failed")
            reply_final = "I'm here with you. I had trouble generating a response, but I'm listening."

        if (
            not reply_final
            or reply_final
            == "I'm here with you. I had trouble generating a response, but I'm listening."
        ):
            reply_final = "I'm here with you. I'm listening."

        # ── MULTILINGUAL CRISIS DETECTION WITH NEGATION PROTECTION ──
        negated_crisis_patterns = [
            r"\b(?:dont|do not|never|no|not|didnt|did not|wont|will not|cant|cannot|aint|no\s+longer)\s+(?:really\s+)?(?:want|wanna|feel like|plan|planning|intend|intending|wish|wishing|trying)\s+(?:to\s+)?(?:die|kill myself|end my life|end it all|hurt myself|harm myself|be dead|cease to exist|give up on life)\b",
            r"\b(?:dont|do not|never|cant|cannot|wont)\s+(?:feel like|wanna|want to)\s+(?:dying|die|ending it)\b",
            r"\bi\s+(?:dont|do not|never|wont)\s+want\s+to\s+die\b",
            r"\bi\s+(?:dont|do not|never)\s+feel\s+like\s+hurting\s+myself\b",
            r"\bno\s+(?:desire|plan|intention|urge)\s+to\s+(?:die|kill myself|end my life|hurt myself)\b",
            r"\b(?:not|never|no\s+longer)\s+(?:feeling\s+)?suicidal\b",
            r"\bnot\s+(?:going to|gonna)\s+(?:kill myself|die|hurt myself|end my life)\b",
            # Direct life affirmations
            r"\b(?:i\s+)?(?:want|wanna|choose|choosing|decided|planning|intend)\s+to\s+(?:live|keep living|stay alive|be alive)\b",
            r"\b(?:glad|happy|grateful|proud)\s+to\s+be\s+alive\b",
            r"\bi\s+love\s+(?:my\s+)?life\b",
            r"\bwant\s+to\s+live\b",
        ]
        
        msg_norm = re.sub(r"['’`]", "", (data.message or "").lower())
        msg_norm = re.sub(r"[^\w\s]", " ", msg_norm)
        msg_norm = re.sub(r"\s+", " ", msg_norm).strip()

        trans_norm = re.sub(r"['’`]", "", (translated_input or "").lower())
        trans_norm = re.sub(r"[^\w\s]", " ", trans_norm)
        trans_norm = re.sub(r"\s+", " ", trans_norm).strip()

        passive_crisis_patterns = [
            r"\b(?:dont|do not|didnt|did not|never|cant|cannot|no\s+longer)\s+(?:really\s+)?(?:want|wanna)\s+to\s+(?:live|keep living|stay alive|be alive|exist|wake up)\b",
            r"\bno\s+(?:reason|point|purpose)\s+(?:for\s+me\s+)?(?:to\s+)?(?:live|living|keep\s+living|stay\s+alive|be\s+alive|go\s+on)\b",
            r"\b(?:tired|exhausted|done|sick)\s+of\s+(?:living|life|existing)\b",
            r"\b(?:better\s+off\s+(?:without\s+me|dead)|better\s+without\s+me|world\s+(?:would\s+be\s+)?better\s+without\s+me)\b",
            r"\b(?:wish|wishing)\s+(?:i\s+)?(?:could\s+disappear|disappear\s+forever|was\s+never\s+born|were\s+never\s+born|was\s+dead|were\s+dead)\b",
            r"\b(?:wish|wished)\s+i\s+(?:never\s+woke\s+up|wouldn'?t\s+wake\s+up|didnt\s+wake\s+up)\b",
            r"\b(?:no\s+one|nobody)\s+(?:would\s+)?(?:care|miss\s+me|notice)\s+(?:if\s+i\s+(?:died|was\s+gone|disappeared|wasnt\s+here))\b",
            r"\b(?:cannot|cant)\s+go\s+on\s+living\b",
        ]
        has_passive_crisis = any(re.search(p, msg_norm) for p in passive_crisis_patterns) or any(re.search(p, trans_norm) for p in passive_crisis_patterns)

        is_negated_crisis = not has_passive_crisis and (
            any(re.search(p, msg_norm) for p in negated_crisis_patterns)
            or any(re.search(p, trans_norm) for p in negated_crisis_patterns)
        )

        CRISIS_KEYWORDS = [
            # English (Active & Passive)
            "want to die", "wanna die", "kill myself", "killing myself", "end my life",
            "ending my life", "suicide", "suicidal", "take my own life", "hurt myself",
            "harm myself", "self harm", "self-harm", "overdose", "jump off",
            "hang myself", "slit my", "better off dead", "better off without me",
            "better without me", "world would be better without me", "feel like dying",
            "feel like die", "wish i was dead", "wish i were dead", "disappear forever",
            "wish i could disappear", "was never born", "were never born", "never woke up",
            "dont want to live", "do not want to live", "dont want to be alive", "do not want to be alive",
            "tired of living", "sick of living", "exhausted of living", "done with life",
            "no reason to live", "no reason to keep living", "no point in living", "cant go on", "can't go on",
            "cannot go on living", "cant go on living",
            # Hindi (transliterated & native)
            "marna chahta", "marna chahti", "mar jana chahta", "mar jana chahti", "jaan dena chahta",
            "jaan de dunga", "mar jaunga", "zindagi khatam", "khatam karna chahta",
            "jeene ki wajah nahi", "koi wajah nahi jeene ki", "mere bina sab theek",
            "आत्महत्या", "मरना चाहता", "मरना चाहती", "जान दे दूंगा", "जान देना", "जान देना चाहता",
            # Telugu (transliterated & native)
            "chaavu", "saayali", "nenu chaavali", "marana", "atmahatya", "naa life end",
            "bathakalanipinchadam ledu", "nenu bathakali anukovatledu", "chani povali",
            "ఆత్మహత్య", "చనిపోవాలని", "చావాలని",
            # Kannada (transliterated & native)
            "saayabeku", "atmahatye", "jeevana mugisalu", "badukalu istavilla", "badukoke istavilla",
            "nanna illade", "jeevana mugisabeku", "ಆತ್ಮಹತ್ಯೆ", "ಸಾಯಬೇಕು",
            # Tamil (transliterated & native)
            "uyira maaikka", "saaga vendum", "vaazha virumbalai", "uyir vazha pidikkala",
            "தற்கொலை", "சாக வேண்டும்",
            # Malayalam (transliterated & native)
            "marikkanam", "aatmahatya", "jeevitham maduthu", "jeevikkan thonnunnilla",
            "ആത്മഹത്യ", "മരിക്കണം",
            # Marathi (transliterated & native)
            "maraycha aahe", "jeev dyava", "jagaycha nahi", "maravese vatte",
            "मला मरावेसे वाटते", "मला मरायचं आहे", "जीव द्यावा", "जगायचं नाही", "आत्महत्या", "मरायचं आहे",
            # Bengali (transliterated & native)
            "morte chai", "aatmahatya", "baanchte chai na", "baachte chai na",
            "shob shesh korte chai", "আত্মহত্যা", "মরতে চাই", "বাঁচতে চাই না",
        ]

        keyword_crisis = has_passive_crisis
        if not is_negated_crisis and not keyword_crisis:
            for kw in CRISIS_KEYWORDS:
                if kw in msg_norm or kw in trans_norm or kw in data.message.lower():
                    keyword_crisis = True
                    break

        ai_crisis = "[EMERGENCY_TRIGGERED]" in reply_final
        if ai_crisis:
            reply_final = reply_final.replace("[EMERGENCY_TRIGGERED]", "").strip()

        # Check crisis triggers
        raw_msg = data.message or ""
        trans_msg = translated_input or ""

        # Multilingual crisis analysis
        ml_crisis = multilingual_normalizer.detect_multilingual_crisis(raw_msg)
        if not ml_crisis.get("is_crisis") and trans_msg and trans_msg != raw_msg:
            ml_crisis_trans = multilingual_normalizer.detect_multilingual_crisis(trans_msg)
            if ml_crisis_trans.get("is_crisis"):
                ml_crisis = ml_crisis_trans

        is_historical = _is_historical_crisis(raw_msg) or _is_historical_crisis(trans_msg)
        is_imminent = _is_imminent_crisis(raw_msg) or _is_imminent_crisis(trans_msg) or ml_crisis.get("is_imminent", False)
        is_deescalating = (
            _is_deescalation_reassurance(raw_msg)
            or _is_deescalation_reassurance(trans_msg)
            or is_negated_crisis
            or ml_crisis.get("is_negated", False)
        )

        is_crisis_detected = (
            not is_historical
            and not is_negated_crisis
            and not is_deescalating
            and (
                ml_crisis.get("is_crisis", False)
                or intent == "suicidal_thought"
                or keyword_crisis
                or ai_crisis
                or (
                    analysis.get("mental_state") == "Suicidal"
                    and analysis.get("confidence", 0.0) >= 70
                )
            )
        )

        lang_req = multilingual_normalizer.detect_language_request(raw_msg) or multilingual_normalizer.detect_language_request(trans_msg)
        phys_req = multilingual_normalizer.detect_physical_health(raw_msg) or multilingual_normalizer.detect_physical_health(trans_msg)
        is_factual_query = bool(re.search(r"^(?:what\s+is|whats|what\s+are|where\s+is|when\s+did|who\s+is|why\s+is|how\s+does|how\s+do|can\s+you|could\s+you|tell\s+me)\b", trans_msg.lower()))

        # Explicit safety rejection or continuing distress in assessment (e.g. 'no i am not safe', 'leave me alone', 'cannot go on')
        safety_rejection_pattern = r"\b(?:no|not\s+safe|unsafe|in\s+danger|leave\s+me|cant\s+go\s+on|cannot\s+go\s+on|still\s+feel|want\s+to\s+die|feel\s+like\s+dying|end\s+it|hurt\s+myself|hopeless|pointless|give\s+up|done\s+with\s+life)\b"
        is_safety_rejection = bool(re.search(safety_rejection_pattern, raw_msg.lower()) or re.search(safety_rejection_pattern, trans_msg.lower()))

        is_unrelated_or_general = (
            not is_crisis_detected
            and not is_imminent
            and not is_safety_rejection
            and (
                phys_req is not None
                or intent in {"greeting", "gratitude", "how_are_you", "physical_health", "language_request"}
                or is_factual_query
            )
        )

        current_state = (
            getattr(session, "crisis_state", "no_active_crisis") or "no_active_crisis"
        )
        current_level = getattr(session, "escalation_level", "none") or "none"
        last_alert = getattr(session, "last_alert_at", None) or _last_alert_time.get(
            session_id
        )

        should_dispatch_alert = False
        dispatch_level = "none"

        if is_historical:
            # Case E: Past crisis acknowledged, stable now.
            if current_state == "crisis_assessing":
                if session:
                    session.crisis_state = "resolved"
                    session.escalation_level = "none"
            if analysis.get("mental_state") == "Suicidal":
                analysis["mental_state"] = "Normal"
                analysis["risk_level"] = "LOW"
            reply_final = (
                "Thank you for sharing that with me. It takes real courage to navigate those dark moments, "
                "and I am truly glad to hear that you are doing better now. I'm always here whenever you need a safe space to talk."
            )

        elif is_imminent:
            # Case D: Clear imminent intent bypass
            if session:
                session.crisis_state = "escalated"
                session.escalation_level = "imminent"
            analysis["mental_state"] = "Suicidal"
            analysis["risk_level"] = "HIGH"
            dispatch_level = "imminent"

            # Check cooldown: Imminent overrides cooldown unless already alerted at imminent level recently
            cooldown_active = False
            if last_alert is not None:
                seconds_since_alert = (datetime.utcnow() - last_alert).total_seconds()
                if seconds_since_alert < ALERT_COOLDOWN_MINUTES * 60:
                    if current_level == "imminent":
                        cooldown_active = True
                    else:
                        cooldown_active = False  # Higher risk imminent overrides lower level alert cooldown!

            if not cooldown_active:
                should_dispatch_alert = True

            reply_final = (
                "I hear how much pain you are experiencing right now, and your safety is the absolute most important thing. "
                "Please stay with me, and please reach out to someone who can help keep you safe right now."
            )

        elif current_state == "crisis_assessing":
            # Session was waiting for safety assessment from previous turn
            if is_deescalating:
                # Case B: Safety affirmed / de-escalation
                if session:
                    session.crisis_state = "resolved"
                    session.escalation_level = "none"
                if analysis.get("mental_state") == "Suicidal":
                    analysis["mental_state"] = "Normal"
                    analysis["risk_level"] = "LOW"
                reply_final = (
                    "I am so glad to hear that you are safe. Thank you for telling me. "
                    "Remember that you are not alone, and I am here whenever you want to talk or need support."
                )
            elif lang_req:
                # Case B2: Language switch request during assessment - acknowledge in requested language
                target_code = lang_req.get("target_code", "en")
                target_name = lang_req.get("target_name", "your preferred language")
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"
                if target_code == "kn":
                    reply_final = (
                        "ಖಂಡಿತ, ನಾವು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಬಹುದು. ನಿಮ್ಮ ಸುರಕ್ಷತೆ ನನಗೆ ಅತ್ಯಂತ ಮುಖ್ಯವಾಗಿದೆ. "
                        "ನೀವು ಈಗ ಸುರಕ್ಷಿತವಾಗಿದ್ದೀರಾ ಎಂದು ನನಗೆ ತಿಳಿಸಬಹುದೇ? (Sure, we can speak in Kannada. Your safety is very important to me. Can you tell me if you are safe right now?)"
                    )
                elif target_code == "hi":
                    reply_final = (
                        "हाँ बिल्कुल, हम हिंदी में बात कर सकते हैं। आपकी सुरक्षा मेरे लिए बहुत महत्वपूर्ण है। "
                        "क्या आप मुझे बता सकते हैं कि आप अभी सुरक्षित हैं? (Sure, we can speak in Hindi. Your safety is very important to me. Can you tell me if you are safe right now?)"
                    )
                else:
                    reply_final = (
                        f"Yes, certainly! We can speak in {target_name}. Your safety is my highest priority. "
                        "Can you tell me if you are in a safe place right now?"
                    )
                should_dispatch_alert = False

            elif is_unrelated_or_general:
                # Case B3: General question, routine chat, or physical health during assessment
                # Answer question naturally, maintain crisis state & risk HIGH, append gentle safety note
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"
                safety_reminder = (
                    "\n\n(I also want to check in on your safety — earlier you mentioned feeling in deep distress. "
                    "Please know I'm here for you and want to ensure you are safe.)"
                )
                if safety_reminder.strip() not in reply_final:
                    reply_final = reply_final + safety_reminder
                should_dispatch_alert = False

            else:
                # Case C: Continuing distress, rejected support, or persistent crisis in assessment
                if session:
                    session.crisis_state = "escalated"
                    session.escalation_level = "escalated"
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"
                dispatch_level = "escalated"

                cooldown_active = False
                if last_alert is not None:
                    seconds_since_alert = (
                        datetime.utcnow() - last_alert
                    ).total_seconds()
                    if seconds_since_alert < ALERT_COOLDOWN_MINUTES * 60:
                        cooldown_active = True

                if not cooldown_active:
                    should_dispatch_alert = True

                reply_final = (
                    "I hear you, and I can sense how overwhelming things feel right now. "
                    "You don't have to carry this alone. Please connect with emergency support or someone you trust right now."
                )

        elif current_state == "escalated":
            # Session was already escalated
            if is_deescalating:
                if session:
                    session.crisis_state = "resolved"
                    session.escalation_level = "none"
                if analysis.get("mental_state") == "Suicidal":
                    analysis["mental_state"] = "Normal"
                    analysis["risk_level"] = "LOW"
                reply_final = (
                    "I am so relieved to hear that you are safe right now. Thank you for checking in with me. "
                    "I'm here to support you at your own pace."
                )
            elif lang_req:
                # Language switch request during escalation
                target_code = lang_req.get("target_code", "en")
                target_name = lang_req.get("target_name", "your preferred language")
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"
                if target_code == "kn":
                    reply_final = (
                        "ಖಂಡಿತ, ನಾವು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಬಹುದು. ನಿಮ್ಮ ಸುರಕ್ಷತೆ ನನಗೆ ಅತ್ಯಂತ ಮುಖ್ಯವಾಗಿದೆ. ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಇದ್ದೇನೆ. "
                        "(Sure, we can speak in Kannada. Your safety is very important to me. I am here with you.)"
                    )
                elif target_code == "hi":
                    reply_final = (
                        "हाँ बिल्कुल, हम हिंदी में बात कर सकते हैं। आपकी सुरक्षा मेरे लिए बहुत महत्वपूर्ण है। मैं आपके साथ हूँ। "
                        "(Sure, we can speak in Hindi. Your safety is very important to me. I am here with you.)"
                    )
                else:
                    reply_final = (
                        f"Yes, certainly! We can speak in {target_name}. Your safety is my highest priority. "
                        "I am right here with you."
                    )
                should_dispatch_alert = False

            elif is_unrelated_or_general:
                # General question, routine chat, or physical health during escalation
                # Answer user message, retain escalated state & risk HIGH, append gentle safety note
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"
                safety_reminder = (
                    "\n\n(I also care very much about your safety and wellbeing right now — "
                    "please remember support is available and you don't have to face this alone.)"
                )
                if safety_reminder.strip() not in reply_final:
                    reply_final = reply_final + safety_reminder
                should_dispatch_alert = False

            else:
                # User remains in escalated state
                if session:
                    session.crisis_state = "escalated"
                    session.escalation_level = "escalated"
                analysis["mental_state"] = "Suicidal"
                analysis["risk_level"] = "HIGH"

                cooldown_active = False
                if last_alert is not None:
                    seconds_since_alert = (
                        datetime.utcnow() - last_alert
                    ).total_seconds()
                    if seconds_since_alert < ALERT_COOLDOWN_MINUTES * 60:
                        cooldown_active = True

                if not cooldown_active:
                    should_dispatch_alert = True
                    dispatch_level = "escalated"

                reply_final = (
                    "I hear how much pain you are experiencing right now, and I care very much about your safety. "
                    "Please stay connected, and please know that you are not alone in this."
                )

        elif current_state in {"no_active_crisis", "resolved"} and is_crisis_detected:
            # Case A: First crisis statement detected (when state was no_active_crisis or resolved)
            # Enter CRISIS_ASSESSING. Do NOT dispatch emergency alert yet!
            if session:
                session.crisis_state = "crisis_assessing"
                session.escalation_level = "assessing"
            should_dispatch_alert = False

            reply_final = (
                "I hear how much pain you are experiencing right now, and your safety is the most important thing. "
                "Please know that you do not have to go through this alone. Can you tell me if you are in a safe place right now?"
            )

        # Dispatch alert if determined by state machine
        if should_dispatch_alert:
            now = datetime.utcnow()
            if session:
                session.last_alert_at = now
            _last_alert_time[session_id] = now

            contacts = (
                db.query(models.EmergencyContact)
                .filter(models.EmergencyContact.user_id == current_user.id)
                .all()
            )
            if contacts:
                phone_numbers = [c.phone_number for c in contacts]
                if dispatch_level == "imminent":
                    alert_text = (
                        f"🚨 IMMEDIATE CRISIS ALERT: {current_user.full_name} has expressed immediate intent of self-harm "
                        f"and requires urgent intervention. This is an automated alert from MindSense AI. "
                        f"Please contact them or emergency services immediately."
                    )
                else:
                    alert_text = (
                        f"🚨 URGENT: {current_user.full_name} is showing signs of emotional crisis "
                        f"and may need immediate support. This is an automated alert from MindSense AI. "
                        f"Please check on them immediately."
                    )

                try:
                    send_whatsapp_greenapi(phone_numbers, alert_text)
                except Exception:
                    logger.exception("WhatsApp alert dispatch failed")
                try:
                    send_sms_android_gateway(phone_numbers, alert_text)
                except Exception:
                    logger.exception("SMS alert dispatch failed")
                try:
                    send_emergency_email(
                        current_user.email, current_user.full_name, contacts
                    )
                except Exception:
                    logger.exception("Email alert dispatch failed")
            else:
                print(
                    f"[Crisis Alert] No emergency contacts configured for user {current_user.id}. Skipping dispatch."
                )

        # Append helpline resources for assessing or escalated crisis states
        active_crisis_state = (
            getattr(session, "crisis_state", "no_active_crisis")
            if session
            else "no_active_crisis"
        )
        if active_crisis_state in {"crisis_assessing", "escalated"}:
            helpline_text = (
                "\n\n💙 If you are in immediate distress or need to speak with someone right now, "
                "please know that free, confidential support is available 24/7:\n"
                "• In India: Tele-MANAS helpline at 14416 or 1800-891-4416 (or call 112)\n"
                "• In the US/Canada: Call or text 988\n"
                "• International: Contact your local emergency services or a trusted person."
            )
            if "Tele-MANAS" not in reply_final and "988" not in reply_final:
                reply_final += helpline_text

        database_start = time.perf_counter()
        try:
            if session_id:
                assistant_msg = models.ChatHistory(
                    session_id=session_id, role="assistant", content=reply_final
                )
                db.add(assistant_msg)
            if session:
                session.updated_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            logger.exception("Failed to save assistant response")
            db.rollback()
        timings["Database"] = time.perf_counter() - database_start
        print(f"[{timings['Database']:.2f}s] Database")

        if "Intent" in timings:
            print(f"[{timings['Intent']:.2f}s] Intent")
        if "Emotion" in timings:
            print(f"[{timings['Emotion']:.2f}s] Emotion")
        total_elapsed = time.perf_counter() - request_start
        timings["TOTAL"] = total_elapsed
        print(f"[{timings['TOTAL']:.2f}s] TOTAL")

        bottleneck = max(timings.items(), key=lambda item: item[1])
        if bottleneck[1] > 1.0:
            print(f"[BOTTLENECK] {bottleneck[0]} ({bottleneck[1]:.2f}s)")

        return {
            "reply": reply_final,
            "session_id": session_id,
            "analysis": analysis,
            "crisis_state": (
                getattr(session, "crisis_state", "no_active_crisis")
                if session
                else "no_active_crisis"
            ),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected /chat failure")
        db.rollback()
        return {
            "reply": "I'm here with you. I had trouble processing that message, but I'm listening.",
            "session_id": session_id,
            "analysis": analysis,
            "crisis_state": (
                getattr(session, "crisis_state", "no_active_crisis")
                if session
                else "no_active_crisis"
            ),
        }


# ---------- FILE UPLOAD ----------


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:upload", rate_limiter.UPLOAD_CONFIG, "file upload")
    try:
        async with secure_upload_context(
            file=file,
            user_id=current_user.id,
            category="text_or_pdf",
        ) as file_path:
            ext = file_path.split(".")[-1].lower()
            content = ""

            if ext == "txt":
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            elif ext == "pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    content += page.extract_text() or ""
            else:
                return {"error": "Unsupported file"}

            # Return a chunk or full text
            return {
                "type": "text",
                "content": content[
                    :3000
                ],  # return up to 3000 chars to avoid overwhelming the prompt
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upload Error]: {type(e).__name__}")
        return {"error": "Failed to process the uploaded file."}


# ---------- AUDIO ----------


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:transcribe", rate_limiter.TRANSCRIBE_CONFIG, "audio transcription")
    """Transcribe audio using Groq's hosted Whisper Large v3 API.
    Supports webm, mp3, mp4, wav, ogg, flac — no local ffmpeg required.
    """
    if groq_client is None:
        raise HTTPException(
            status_code=503,
            detail="Audio transcription requires GROQ_API_KEY (Groq Whisper API). "
            "Configure it in backend/.env to enable voice input.",
        )
    try:
        async with secure_upload_context(
            file=file,
            user_id=current_user.id,
            category="audio",
        ) as path:
            # Validate file is not empty (silent recording)
            file_size = os.path.getsize(path)
            if file_size < 1000:  # less than 1KB is likely an empty/silent recording
                return {"text": ""}

            mime_type = file.content_type or "audio/webm"
            safe_name = os.path.basename(path)
            logger.info(
                f"[TRANSCRIBE] safe_name={safe_name}, size={file_size}b, mime={mime_type}"
            )

            # Use Groq's hosted Whisper API — handles webm/audio natively, no ffmpeg needed
            with open(path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(safe_name, audio_file, mime_type),
                    model="whisper-large-v3",
                    response_format="text",
                )

            # Groq returns plain text string when response_format="text"
            text = (
                transcription.strip()
                if isinstance(transcription, str)
                else (transcription.text or "").strip()
            )
            logger.info(f"[TRANSCRIBE] result length={len(text)} chars")

            return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TRANSCRIBE ERROR: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Audio transcription service temporarily unavailable.")


class TTSRequest(schemas.BaseModel):
    text: str
    language: str = "en"


@app.post("/tts")
def tts_generate(
    data: TTSRequest,
    current_user: models.User = Depends(get_current_user),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:tts", rate_limiter.TTS_CONFIG, "TTS generation")
    raw_text = data.text or ""
    # Strip control characters (ASCII < 32 except newline and tab)
    clean_text = "".join(
        ch for ch in raw_text if ch in ("\n", "\t") or (ord(ch) >= 32 and ord(ch) != 127)
    ).strip()

    if not clean_text:
        raise HTTPException(
            status_code=422,
            detail="Text must contain at least one non-whitespace, printable character.",
        )

    if len(clean_text) > 800:
        raise HTTPException(
            status_code=422,
            detail="Text exceeds maximum allowed length of 800 characters.",
        )

    tts_lang = (data.language or "en").lower().strip()
    if tts_lang not in [
        "en",
        "hi",
        "kn",
        "ta",
        "te",
        "ml",
        "mr",
        "bn",
        "gu",
        "pa",
        "ur",
    ]:
        tts_lang = "en"

    try:
        tts = gTTS(text=clean_text, lang=tts_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_content = fp.read()
        return Response(content=audio_content, media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS ERROR: {type(e).__name__}")
        raise HTTPException(
            status_code=502,
            detail="Text-to-speech service temporarily unavailable.",
        )


def _emotion_to_analysis(
    dominant_emotion: str,
    confidence: float,
    distribution: Optional[dict] = None,
) -> dict:
    """Map a facial emotion to a mental-state analysis consistent with the text
    pipeline. Confidence comes from the DeepFace emotion-distribution percentage
    (a real value from the model), not invented. Risk uses the existing
    LOW / MEDIUM / HIGH taxonomy already used by the text pipeline.

    Ambiguity gating: If dominant confidence < 35% or the margin between
    the top-1 and top-2 emotions is < 10 percentage points, the visual signal
    is treated as ambiguous/neutral (Normal / LOW) to prevent unwarranted
    clinical/distress states.
    """
    e = (dominant_emotion or "neutral").lower().strip()
    conf = float(confidence or 0.0)

    # Check for ambiguity
    is_ambiguous = False
    if e in {"ambiguous", "neutral", "unknown"}:
        is_ambiguous = True
    elif conf > 0.0 and conf < 35.0:
        is_ambiguous = True
    elif distribution and len(distribution) > 1:
        sorted_vals = sorted([float(v or 0.0) for v in distribution.values()], reverse=True)
        if len(sorted_vals) >= 2:
            top1 = sorted_vals[0]
            top2 = sorted_vals[1]
            if top1 < 35.0 or (top1 - top2) < 10.0:
                is_ambiguous = True

    if is_ambiguous:
        return {
            "mental_state": "Normal",
            "confidence": round(conf, 2),
            "risk_level": "LOW",
        }

    mapping = {
        "happy": {"mental_state": "Normal", "risk_level": "LOW"},
        "neutral": {"mental_state": "Normal", "risk_level": "LOW"},
        "sad": {"mental_state": "Depression", "risk_level": "MEDIUM"},
        "angry": {"mental_state": "Stress", "risk_level": "MEDIUM"},
        "fear": {"mental_state": "Anxiety", "risk_level": "MEDIUM"},
        "surprise": {"mental_state": "Normal", "risk_level": "LOW"},
        "disgust": {"mental_state": "Normal", "risk_level": "LOW"},
        "ambiguous": {"mental_state": "Normal", "risk_level": "LOW"},
    }
    state = mapping.get(e, mapping["neutral"])
    return {
        "mental_state": state["mental_state"],
        "confidence": round(conf, 2),
        "risk_level": state["risk_level"],
    }


@app.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    session_id: Optional[int] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:video", rate_limiter.VIDEO_CONFIG, "video processing")
    rate_limiter.video_concurrency_guard.acquire()

    if not DEEPFACE_AVAILABLE:
        rate_limiter.video_concurrency_guard.release()
        return {
            "error": "Emotion detection unavailable. Please install the required DeepFace dependencies."
        }

    upload_cm = secure_upload_context(
        file=file,
        user_id=current_user.id,
        category="video",
    )
    try:
        file_path = await upload_cm.__aenter__()

        cap = cv2.VideoCapture(file_path)

        if not cap.isOpened():
            return {"error": "Unable to open the uploaded video."}

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if frame_count <= 0:
            cap.release()
            return {"error": "Unable to read frames from the video."}

        # Resource limits on dimensions and duration
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w > 4096 or h > 4096:
            cap.release()
            return {"error": "Video resolution exceeds maximum allowed dimensions (4096x4096)."}

        if fps and fps > 0:
            duration_sec = frame_count / fps
        else:
            duration_sec = frame_count / 25.0

        if duration_sec > 300.0 or frame_count > 15000:
            cap.release()
            return {"error": "Video duration exceeds maximum allowed limit (5 minutes)."}

        # ---------------------------------------------------------
        # Bounded duration-aware frame sampling
        # ---------------------------------------------------------
        # Analyze ~1 frame per second of video, bounded between a
        # minimum of 8 frames (for short clips) and a hard maximum of
        # 20 frames (to keep CPU processing bounded).
        min_samples = 8
        max_samples = 20

        if fps and fps > 0:
            duration_sec = frame_count / fps
        else:
            duration_sec = frame_count / 25.0

        duration_samples = int(round(duration_sec)) if duration_sec > 0 else min_samples
        desired_samples = max(min_samples, min(duration_samples, max_samples))
        sample_count = min(frame_count, desired_samples)

        # Accumulate the REAL emotion probability vectors per analyzed
        # frame (DeepFace returns percentages per emotion class). Averaging
        # these probabilities is far more robust than majority-voting the
        # unreliable per-frame dominant label.
        # Multi-person tracking and multi-emotion temporal aggregation
        person_tracks = []  # list of person state dicts
        temporal_timeline = []
        analyzed_frames = 0

        for i in range(sample_count):
            # Spread frames across the entire video.
            if sample_count == 1:
                frame_index = 0
            else:
                frame_index = int(round(i * (frame_count - 1) / (sample_count - 1)))

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            if not ret:
                continue

            try:
                h, w = frame.shape[:2]
                if w > 640:
                    scale = 640.0 / w
                    frame = cv2.resize(frame, (640, int(h * scale)))
                    h, w = frame.shape[:2]

                raw_results = DeepFace.analyze(
                    frame, actions=["emotion"], enforce_detection=False
                )

                face_list = raw_results if isinstance(raw_results, list) else [raw_results]
                analyzed_frames += 1
                frame_time = round(frame_index / fps, 2) if fps else round(i * 0.5, 2)

                # Collect valid detections for this frame
                current_detections = []
                for face_data in face_list:
                    if not isinstance(face_data, dict):
                        continue
                    reg = face_data.get("region") or {}
                    rx = float(reg.get("x", 0))
                    ry = float(reg.get("y", 0))
                    rw = float(reg.get("w", 100))
                    rh = float(reg.get("h", 100))
                    cx = rx + rw / 2.0
                    cy = ry + rh / 2.0
                    probs = face_data.get("emotion") or {}
                    dom = str(face_data.get("dominant_emotion", "neutral")).lower()
                    current_detections.append({
                        "cx": cx,
                        "cy": cy,
                        "rx": rx,
                        "ry": ry,
                        "rw": rw,
                        "rh": rh,
                        "probs": probs,
                        "dom": dom,
                    })

                # Pairwise candidate matches between current detections and existing tracks.
                # Enforce strict 1-to-1 matching per frame so multiple faces cannot collide.
                candidates = []
                for det_idx, det in enumerate(current_detections):
                    cx, cy = det["cx"], det["cy"]
                    max_thresh = max(180.0, min(240.0, max(det["rw"], det["rh"]) * 2.2))
                    for track_idx, p in enumerate(person_tracks):
                        lx, ly = p["last_centroid"]
                        dist = ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5
                        if dist < max_thresh:
                            candidates.append((dist, det_idx, track_idx))

                # Sort candidate matches by distance ascending
                candidates.sort(key=lambda c: c[0])

                matched_dets = set()
                matched_tracks = set()
                assignments = {}

                for dist, det_idx, track_idx in candidates:
                    if det_idx not in matched_dets and track_idx not in matched_tracks:
                        matched_dets.add(det_idx)
                        matched_tracks.add(track_idx)
                        assignments[det_idx] = track_idx

                # Process all detections
                for det_idx, det in enumerate(current_detections):
                    cx, cy = det["cx"], det["cy"]
                    probs = det["probs"]
                    dom = det["dom"]

                    if det_idx in assignments:
                        track_idx = assignments[det_idx]
                        matched_person = person_tracks[track_idx]
                        matched_person["last_centroid"] = (cx, cy)
                        matched_person["last_box"] = (det["rx"], det["ry"], det["rw"], det["rh"])
                    else:
                        # Unmatched detection creates a new person track
                        new_id = len(person_tracks) + 1
                        matched_person = {
                            "person_id": new_id,
                            "last_centroid": (cx, cy),
                            "last_box": (det["rx"], det["ry"], det["rw"], det["rh"]),
                            "emotion_scores": {},
                            "frame_dominants": [],
                            "frames_detected": 0,
                        }
                        person_tracks.append(matched_person)

                    matched_person["frames_detected"] += 1
                    matched_person["frame_dominants"].append(dom)
                    for k, v in probs.items():
                        matched_person["emotion_scores"][k] = (
                            matched_person["emotion_scores"].get(k, 0.0) + float(v or 0.0)
                        )

                    temporal_timeline.append({
                        "frame": frame_index,
                        "timestamp_sec": frame_time,
                        "person_id": matched_person["person_id"],
                        "dominant_emotion": dom,
                    })

            except Exception as frame_error:
                print(f"[Video Emotion] Frame {frame_index} error: {frame_error}")

        cap.release()

        # ---------------------------------------------------------
        # Aggregate emotion probabilities per detected person
        # ---------------------------------------------------------
        people_list = []
        # Sort tracks by frequency of appearance
        person_tracks.sort(key=lambda p: p["frames_detected"], reverse=True)

        for p in person_tracks:
            scores = p["emotion_scores"]
            if not scores:
                p_dom = "neutral"
                p_dist = {}
                dominant_pct = 0.0
            else:
                p_total = sum(scores.values())
                p_dist = {
                    k: round((v / p_total) * 100.0, 2) if p_total > 0 else 0.0
                    for k, v in scores.items()
                }
                # Sort emotions by percentage descending
                sorted_emotions = sorted(p_dist.items(), key=lambda item: item[1], reverse=True)
                raw_dom, top1 = sorted_emotions[0]
                top2 = sorted_emotions[1][1] if len(sorted_emotions) > 1 else 0.0
                margin = top1 - top2

                # Ambiguity gating: dominant < 35% OR top1 - top2 < 10%
                if top1 < 35.0 or margin < 10.0:
                    p_dom = "ambiguous"
                    dominant_pct = top1
                else:
                    p_dom = raw_dom
                    dominant_pct = top1

            people_list.append({
                "person_id": p["person_id"],
                "dominant_emotion": p_dom,
                "confidence": dominant_pct,
                "emotion_distribution": p_dist,
                "frames_detected": p["frames_detected"],
            })

        # Primary person (Person 1) provides default single-person values
        if people_list:
            primary_person = people_list[0]
            dominant_emotion = primary_person["dominant_emotion"]
            emotion_distribution = primary_person["emotion_distribution"]
            dominant_pct = primary_person["confidence"]
        else:
            dominant_emotion = "neutral"
            emotion_distribution = {}
            dominant_pct = 0.0

        print(f"[Video Emotion] Analyzed {analyzed_frames} frames, detected {len(people_list)} person(s)")
        print(f"[Video Emotion] Dominant emotion: {dominant_emotion}")
        print(f"[Video Emotion] Distribution: {emotion_distribution}")

        analysis = _emotion_to_analysis(
            dominant_emotion,
            dominant_pct,
            distribution=emotion_distribution,
        )

        # Generate natural chatbot response using detected emotion as context
        chatbot_reply = ""
        try:
            intent_predictor = getattr(chat_engine, "intent_predictor", None)
            if intent_predictor is None:
                intent_predictor = IntentPredictor()
                chat_engine.intent_predictor = intent_predictor
            emotion_predictor = getattr(chat_engine, "emotion_predictor", None)
            if emotion_predictor is None:
                emotion_predictor = EmotionPredictor()
                chat_engine.emotion_predictor = emotion_predictor

            chatbot_reply = chat_engine.generate_video_response(
                face_emotion=dominant_emotion,
                mental_state=analysis.get("mental_state", "Normal"),
                risk_level=analysis.get("risk_level", "LOW"),
                history=[],
                memory=current_user.memory_profile or "",
            )
            chatbot_reply = str(
                chatbot_reply or "I'm here with you. How are you feeling right now?"
            )
        except Exception as exc:
            logger.exception("Failed to generate chatbot response for video")
            chatbot_reply = "I'm here with you. How are you feeling right now?"

        return {
            "message": (
                f"Video analyzed successfully. "
                f"Detected {len(people_list)} person(s), dominant emotion: {dominant_emotion}"
            ),
            "type": "video",
            "emotion": dominant_emotion,
            "dominant_emotion": dominant_emotion,
            "frames_analyzed": analyzed_frames,
            "total_frames": frame_count,
            "fps": fps,
            "emotion_distribution": emotion_distribution,
            "people": people_list,
            "temporal_timeline": temporal_timeline,
            "analysis": analysis,
            "chatbot_reply": chatbot_reply,
            "disclaimer": "Facial expressions provide visual emotion cues and do NOT constitute a medical or psychological diagnosis.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Video Upload Error]: {type(e).__name__}")
        return {"error": "Failed to process the uploaded video."}
    finally:
        rate_limiter.video_concurrency_guard.release()
        await upload_cm.__aexit__(None, None, None)


# ---------- NLP ANALYTICS ----------


@app.get("/nlp-analytics")
def nlp_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    rate_limiter.enforce_rate_limit(f"user:{current_user.id}:nlp_analytics", rate_limiter.GENERAL_READ_CONFIG, "nlp analytics")
    """
    Aggregate NLP mental-state analysis across all user messages for the
    authenticated user.  Returns per-state counts, total messages analysed,
    and average model confidence.
    """
    try:
        # Fetch every user-role message across all sessions owned by this user
        user_sessions = (
            db.query(models.ChatSession)
            .filter(models.ChatSession.user_id == current_user.id)
            .all()
        )

        counts = {"Normal": 0, "Anxiety": 0, "Depression": 0, "Suicidal": 0}
        total = 0
        confidence_sum = 0.0

        for session in user_sessions:
            for msg in session.messages:
                if msg.role != "user":
                    continue
                content = (msg.content or "").strip()
                if not content:
                    continue
                try:
                    result = analyze_mental_state(content)
                    state = result["mental_state"]
                    counts[state] = counts.get(state, 0) + 1
                    confidence_sum += result["confidence"]
                    total += 1
                except Exception:
                    # Skip any message that can't be vectorized
                    pass

        avg_confidence = round(confidence_sum / total, 2) if total > 0 else 0.0

        return {
            "total_analyzed": total,
            "counts": counts,
            "avg_confidence": avg_confidence,
        }

    except Exception as e:
        logger.error(f"NLP analytics error: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics.")
