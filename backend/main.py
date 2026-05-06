from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta, datetime
from jose import JWTError, jwt
import os
import shutil
from pypdf import PdfReader
# openai-whisper replaced by Groq hosted Whisper API (no ffmpeg needed)
from groq import Groq
from gtts import gTTS
import cv2
import requests
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
except Exception:
    DEEPFACE_AVAILABLE = False
    print("[WARNING] DeepFace not available. Run: pip install tf-keras")

import models, schemas, auth
from database import engine, get_db, SessionLocal
from dotenv import load_dotenv

# Create tables
models.Base.metadata.create_all(bind=engine)

load_dotenv(dotenv_path=".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY")

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # default sandbox number

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "")

# Android SMS Gateway
SMS_GATE_LOGIN    = os.getenv("SMS_GATE_LOGIN", "")
SMS_GATE_PASSWORD = os.getenv("SMS_GATE_PASSWORD", "")

# Green API - WhatsApp from YOUR own number (free 500 msg/month, no contact opt-in)
GREENAPI_ID_INSTANCE = os.getenv("GREENAPI_ID_INSTANCE", "")
GREENAPI_API_TOKEN   = os.getenv("GREENAPI_API_TOKEN", "")

# ── FOR PUBLISHING: Meta WhatsApp Cloud API ──────────────────────────────────
# When ready to publish commercially, fill these and switch to send_whatsapp_meta()
# Setup: developers.facebook.com/docs/whatsapp/cloud-api/get-started
# Free: 1000 conversations/month with a dedicated MindSense business number
META_WA_PHONE_NUMBER_ID = os.getenv("META_WA_PHONE_NUMBER_ID", "")  # From Meta dashboard
META_WA_ACCESS_TOKEN    = os.getenv("META_WA_ACCESS_TOKEN", "")     # Permanent system token
# ─────────────────────────────────────────────────────────────────────────────

GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")
GMAIL_APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD", "")

groq_client = Groq(api_key=GROQ_API_KEY)

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
    Detect language of user message.
    Returns dict: { "name": "Telugu", "script": "latin" | "native", "code": "te" }
    Priority: native script → keyword matching → default English
    """
    t = text.strip()
    tl = t.lower()

    # 1. Pure English short words — return immediately
    ENGLISH_WORDS = {
        "hi","hey","hello","ok","okay","yes","no","bye","thanks","thank you",
        "good","fine","great","nice","sure","please","sorry","help","namaste",
        "vanakkam","namaskara","namaskaram","sat sri akal","namaskar","howdy",
        "sup","what","how","why","who","when","where"
    }
    if tl.strip("!?.,") in ENGLISH_WORDS:
        return {"name": "English", "script": "latin", "code": "en"}

    # 2. Native script detection via Unicode ranges
    for ch in t:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F: return {"name": "Hindi",     "script": "native", "code": "hi"}
        if 0x0C00 <= o <= 0x0C7F: return {"name": "Telugu",    "script": "native", "code": "te"}
        if 0x0B80 <= o <= 0x0BFF: return {"name": "Tamil",     "script": "native", "code": "ta"}
        if 0x0C80 <= o <= 0x0CFF: return {"name": "Kannada",   "script": "native", "code": "kn"}
        if 0x0D00 <= o <= 0x0D7F: return {"name": "Malayalam", "script": "native", "code": "ml"}
        if 0x0980 <= o <= 0x09FF: return {"name": "Bengali",   "script": "native", "code": "bn"}
        if 0x0A80 <= o <= 0x0AFF: return {"name": "Gujarati",  "script": "native", "code": "gu"}
        if 0x0A00 <= o <= 0x0A7F: return {"name": "Punjabi",   "script": "native", "code": "pa"}
        if 0x0600 <= o <= 0x06FF: return {"name": "Urdu",      "script": "native", "code": "ur"}

    # 3. Transliteration keyword matching
    KW = {
        "te": ["nenu","meeru","ela","unnaru","cheppandi","emi","ikkade","baagunnara",
               "naku","miku","oka","roju","chala","undi","ledu","chestunnanu","telusaa",
               "ekkadiki","evaru","chaavu","nenu chaavali"],
        "kn": ["nanu","nimma","enu","beku","illa","hogbeku","alli","iga","yaako",
               "ondhu","naanu","chennagi","helidru","bartheeni","hogtheeni"],
        "ta": ["naan","neenga","enna","romba","paaru","sollu","vandha","irukku",
               "eppo","enge","yaar","theriyuma","solla","mudiyum"],
        "hi": ["mujhe","aapko","kaise","hain","kya","nahi","bahut","achi","baat",
               "hun","hoon","tum","mere","mera","tera","teri","yaar","dost",
               "theek","accha","bura","zyada","thoda","raha","rahi","chahta",
               "chahti","samajh","bolna","sochna","lagta","lagti","duniya"],
        "mr": ["mala","tumhi","kasa","aahe","nahi","bara","ghari","sangto","karto"],
    }
    for code, keywords in KW.items():
        if any(kw in tl for kw in keywords):
            names = {"te":"Telugu","kn":"Kannada","ta":"Tamil","hi":"Hindi","mr":"Marathi"}
            return {"name": names[code], "script": "latin", "code": code}

    # 4. Default — English
    return {"name": "English", "script": "latin", "code": "en"}
# ─────────────────────────────────────────────────────────────────────────────


app = FastAPI()

# In production, set ALLOWED_ORIGINS env var to your Vercel URL (comma-separated)
# e.g. ALLOWED_ORIGINS=https://mindsenseai.vercel.app
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

# ---------- AUTH ----------

@app.post("/signup", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user.emergency_contacts) < 2:
        raise HTTPException(status_code=400, detail="At least 2 emergency contacts are required")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    for contact in user.emergency_contacts:
        db_contact = models.EmergencyContact(
            name=contact.name,
            phone_number=contact.phone_number,
            user_id=db_user.id
        )
        db.add(db_contact)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
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
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.delete("/users/me")
def delete_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently delete user account and all associated data."""
    try:
        # Delete all chat history and sessions
        session_ids = [s.id for s in db.query(models.ChatSession).filter(
            models.ChatSession.user_id == current_user.id
        ).all()]
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
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")


def send_emergency_email(to_email: str, user_name: str, contacts: list) -> bool:
    """Send emergency alert email via Gmail SMTP (free backup channel)."""
    if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        print("[EMAIL] Gmail not configured. Add GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD to .env")
        return False
    try:
        contacts_html = "".join(
            f"<tr><td style='padding:8px 12px;color:#fff;border-bottom:1px solid #333'>{c.name}</td>"
            f"<td style='padding:8px 12px;color:#aaa;border-bottom:1px solid #333'>{c.phone_number}</td></tr>"
            for c in contacts
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;background:#0a0a0f;color:#fff;padding:32px;border-radius:16px;max-width:520px;margin:auto">
          <div style="background:#ef4444;border-radius:12px;padding:16px 24px;margin-bottom:24px">
            <span style="font-size:24px">🚨</span>
            <span style="font-size:18px;font-weight:bold;margin-left:10px">EMERGENCY ALERT – MindSense AI</span>
          </div>
          <p style="font-size:15px;color:#e2e8f0"><strong style="color:#f87171">{user_name}</strong> may be in emotional distress and needs immediate attention.</p>
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
        msg["Subject"] = f"🚨 URGENT: {user_name} needs help – MindSense AI"
        msg["From"] = GMAIL_SENDER_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL SENT ✓] → {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def normalize_phone_india(number: str) -> str:
    """Strip to 10-digit Indian number for Fast2SMS."""
    cleaned = number.strip().replace(" ", "").replace("-", "").replace("+91", "").replace("+", "")
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
        response = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": FAST2SMS_API_KEY, "Content-Type": "application/json"},
            json={"route": "q", "message": message, "numbers": numbers},
            timeout=10
        )
        data = response.json()
        print(f"[SMS Fast2SMS] Response: {data}")
        return data.get("return") == True
    except Exception as e:
        print(f"[SMS ERROR] Fast2SMS: {e}")
        return False

def send_sms_android_gateway(phone_numbers: list, message: str) -> bool:
    """Send FREE SMS via Android SMS Gate app (sms-gate.app).
    Install 'SMS Gate' app on your Android phone → sign up free → get login/password.
    Your phone's SIM sends the SMS — works without internet on receiver's end.
    """
    if not SMS_GATE_LOGIN or not SMS_GATE_PASSWORD:
        print("[SMS Gate] Not configured. Add SMS_GATE_LOGIN and SMS_GATE_PASSWORD to .env")
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
        credentials = base64.b64encode(f"{SMS_GATE_LOGIN}:{SMS_GATE_PASSWORD}".encode()).decode()
        response = requests.post(
            "https://api.sms-gate.app/3rdparty/v1/message",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            },
            json={"message": message, "phoneNumbers": normalized},
            timeout=15
        )
        data = response.json()
        print(f"[SMS Gate] Response: {data}")
        # Success if we get an id back
        return "id" in data or response.status_code == 202
    except Exception as e:
        print(f"[SMS Gate ERROR] {e}")
        return False


def send_whatsapp_callmebot(contacts: list, message: str) -> bool:
    """Send FREE WhatsApp via CallMeBot (100% free, no trial, no credits).
    Each contact must opt-in once: save +34644597621 on WhatsApp and send
    'I allow callmebot to send me messages' to get their personal API key.
    """
    sent = 0
    for c in contacts:
        key = getattr(c, 'callmebot_key', '') or ''
        phone = c.phone_number.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = f"+91{phone.lstrip('91').lstrip('+91')}"
        if not key:
            print(f"[WhatsApp] No CallMeBot key for {c.name}. Skipping.")
            continue
        try:
            encoded_msg = requests.utils.quote(message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                print(f"[WhatsApp SENT ✓] → {c.name} ({phone})")
                sent += 1
            else:
                print(f"[WhatsApp ERROR] {c.name}: {resp.text[:100]}")
        except Exception as e:
            print(f"[WhatsApp ERROR] {c.name}: {e}")
    return sent > 0

def send_whatsapp_greenapi(phone_numbers: list, message: str) -> bool:
    """Send WhatsApp from YOUR OWN number via Green API.
    Free tier: 500 messages/month. No contact opt-in needed.
    Setup: green-api.com → create free instance → scan QR with WhatsApp.
    """
    if not GREENAPI_ID_INSTANCE or not GREENAPI_API_TOKEN:
        print("[Green API] Not configured. Add GREENAPI_ID_INSTANCE and GREENAPI_API_TOKEN to .env")
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
            resp = requests.post(url, json={"chatId": chat_id, "message": message}, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get("idMessage"):
                print(f"[WhatsApp Green API ✓] → {number}")
                sent += 1
            else:
                print(f"[WhatsApp Green API ERROR] {number}: {data}")
        except Exception as e:
            print(f"[WhatsApp Green API ERROR] {number}: {e}")
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
        print("[Meta WA] Not configured. Add META_WA_PHONE_NUMBER_ID and META_WA_ACCESS_TOKEN to .env")
        return False
    sent = 0
    url = f"https://graph.facebook.com/v19.0/{META_WA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WA_ACCESS_TOKEN}",
        "Content-Type": "application/json"
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
                "text": {"body": message}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get("messages"):
                print(f"[Meta WA SENT ✓] → {number}")
                sent += 1
            else:
                print(f"[Meta WA ERROR] {number}: {data}")
        except Exception as e:
            print(f"[Meta WA ERROR] {number}: {e}")
    return sent > 0
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/emergency")
def trigger_emergency(current_user: models.User = Depends(get_current_user)):
    contacts = current_user.emergency_contacts
    if not contacts:
        return {"message": "No emergency contacts found. Please add contacts in your Profile page."}

    contact_names  = [c.name for c in contacts]
    phone_numbers  = [c.phone_number for c in contacts]
    alert_text     = (
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

    contacts_display = ', '.join(contact_names)
    if results:
        return {"message": f"✅ Emergency alert sent via {' + '.join(results)} to {contacts_display}."}
    else:
        manual = ', '.join([f"{c.name} ({c.phone_number})" for c in contacts])
        return {"message": f"⚠️ Notifications not configured yet. Please call manually: {manual}"}



class EmergencyContactUpdate(schemas.BaseModel):
    contacts: List[schemas.ContactCreate]

@app.put("/emergency-contacts")
def update_emergency_contacts(
    data: EmergencyContactUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if len(data.contacts) < 1:
        raise HTTPException(status_code=400, detail="At least 1 emergency contact is required.")

    # Delete existing contacts and replace with new ones
    db.query(models.EmergencyContact).filter(
        models.EmergencyContact.user_id == current_user.id
    ).delete()

    for c in data.contacts:
        db_contact = models.EmergencyContact(
            name=c.name,
            phone_number=c.phone_number,
            callmebot_key=c.callmebot_key or "",
            user_id=current_user.id
        )
        db.add(db_contact)
    db.commit()

    updated_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    db.refresh(updated_user)
    return {"message": "Emergency contacts updated successfully.", "contacts": [{"name": c.name, "phone_number": c.phone_number} for c in updated_user.emergency_contacts]}

# ---------- CHAT ----------
class ChatRequest(schemas.BaseModel):
    message: str
    language: str = "en"
    history: list = []
    session_id: Optional[int] = None
    emotion_context: Optional[str] = None

@app.get("/chat/sessions", response_model=List[schemas.ChatSession])
def get_chat_sessions(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(models.ChatSession).filter(models.ChatSession.user_id == current_user.id).order_by(models.ChatSession.updated_at.desc()).all()
    return sessions

@app.get("/chat/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_chat_session(session_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

class ChatSessionUpdate(schemas.BaseModel):
    title: str

@app.put("/chat/sessions/{session_id}", response_model=schemas.ChatSession)
def update_chat_session(session_id: int, data: ChatSessionUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = data.title
    db.commit()
    db.refresh(session)
    return session

@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}

def extract_and_update_memory(user_id: int, user_message: str, current_memory: str):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return

        memory_prompt = [
            {
                "role": "system",
                "content": "You are a memory extraction bot. The user has sent a new message to a mental health AI. "
                           "Your job is to read the user's message and update their ongoing memory profile if there are new important facts, names, or preferences. "
                           "Return the UPDATED memory profile as a concise bulleted list. If there is nothing new to add, just return the existing memory profile exactly as it is. Do NOT output anything else."
            },
            {
                "role": "user",
                "content": f"Existing Memory Profile:\n{current_memory}\n\nNew User Message: {user_message}"
            }
        ]
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=memory_prompt,
            temperature=0.1,
            max_tokens=300
        )
        new_memory = response.choices[0].message.content.strip()
        
        user.memory_profile = new_memory
        db.commit()
    except Exception as e:
        print("Memory extraction error:", e)
    finally:
        db.close()

@app.post("/chat")
def chat(data: ChatRequest, background_tasks: BackgroundTasks, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Determine the target language name
        target_lang_name = data.language
        if target_lang_name == "en":
            target_lang_name = "English"
        elif target_lang_name == "hi": target_lang_name = "Hindi"
        elif target_lang_name == "kn": target_lang_name = "Kannada"
        elif target_lang_name == "ta": target_lang_name = "Tamil"
        elif target_lang_name == "te": target_lang_name = "Telugu"
        elif target_lang_name == "ml": target_lang_name = "Malayalam"
        elif target_lang_name == "mr": target_lang_name = "Marathi"
        elif target_lang_name == "bn": target_lang_name = "Bengali"
        elif target_lang_name == "gu": target_lang_name = "Gujarati"
        elif target_lang_name == "pa": target_lang_name = "Punjabi"
        elif target_lang_name == "ur": target_lang_name = "Urdu"

        # Step 1: Pre-process translation to avoid hallucinations with Kanglish/Hinglish
        translated_input = data.message
        if target_lang_name != "English":
            try:
                trans_messages = [
                    {
                        "role": "system",
                        "content": f"You are an expert translator. The user provides text in {target_lang_name} (it may be written in native script or English alphabet/Kanglish/Hinglish). Translate it literally and accurately to English. Reply with ONLY the English translation, no explanations or extra text."
                    },
                    {"role": "user", "content": data.message}
                ]
                trans_res = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=trans_messages,
                    temperature=0.1,
                    max_tokens=200
                )
                translated_input = trans_res.choices[0].message.content.strip()
            except Exception as e:
                print("Translation pre-processing failed:", e)

        # Step 2: Detect language deterministically
        lang_info = detect_language(data.message)
        lang_name = lang_info["name"]
        lang_script = lang_info["script"]
        print(f"[Lang Detected] '{data.message[:30]}' → {lang_name} ({lang_script})")

        script_rule = (
            f"Reply using the English alphabet (romanized/transliterated {lang_name}), NOT native script."
            if lang_script == "latin" and lang_name != "English"
            else f"Reply in {lang_name} using its native script."
            if lang_script == "native"
            else "Reply in English."
        )

        system_content = (
            "You are MindSense AI, a warm and empathetic mental health assistant.\n\n"
            f"## LANGUAGE INSTRUCTION (MANDATORY):\n"
            f"The user's message is in **{lang_name}**.\n"
            f"You MUST reply ONLY in {lang_name}. {script_rule}\n"
            f"Do NOT use any other language in your reply.\n\n"
            "## CONVERSATION RULES:\n"
            "1. Be warm, supportive, and concise. Ask one follow-up question.\n"
            "2. Never explain your language choice.\n"
            "3. EMERGENCY RULE (READ CAREFULLY):\n"
            "   - Include '[EMERGENCY_TRIGGERED]' ONLY if the user's CURRENT message (below) EXPLICITLY expresses:\n"
            "     suicidal intent, active self-harm, or immediate danger to their life RIGHT NOW.\n"
            "   - Evaluate the CURRENT MESSAGE IN ISOLATION. Ignore what was said in history.\n"
            "   - Do NOT trigger for: casual greetings, questions, sadness, stress, venting, or follow-up small talk.\n"
            "   - Do NOT trigger if the user is just checking in, asking 'how are you', or discussing past feelings.\n"
            "   - Examples that DO trigger: 'I want to kill myself', 'marna chahta hoon', 'nenu chaavali'\n"
            "   - Examples that do NOT trigger: 'I feel sad', 'how are you', 'I felt like dying yesterday', casual chat\n"
            "4. If user asks 'how are you' or similar, respond warmly and check in on them — do NOT assume crisis.\n"
        )



        if current_user.memory_profile:
            system_content += f"\n\n[USER MEMORY PROFILE - This is what you know about the user from past chats:]\n{current_user.memory_profile}"
            
        if data.emotion_context:
            system_content += f"\n\n[DETECTED FACIAL EMOTION: The user recently recorded a video of their face. Their detected emotion is '{data.emotion_context}'. Use this as strong emotional context for your response without sounding robotic.]"

        messages = [
            {
                "role": "system",
                "content": system_content,
            }
        ]

        if data.history:
            for h in data.history:
                if isinstance(h, dict):
                    role = h.get("role", "user")
                    content = h.get("content", "")
                    # Strip emergency alert footers from history so AI doesn't assume ongoing crisis
                    if role == "assistant" and "\n\n🚨" in content:
                        content = content.split("\n\n🚨")[0].strip()
                    messages.append({"role": role, "content": content})

        # Always send the original message — AI auto-detects and responds in same language
        messages.append({"role": "user", "content": data.message})

        
        session_id = data.session_id
        if not session_id:
            title = data.message[:30] + "..." if len(data.message) > 30 else data.message
            new_session = models.ChatSession(user_id=current_user.id, title=title)
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session_id = new_session.id
        else:
            session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.user_id == current_user.id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

        user_msg = models.ChatHistory(session_id=session_id, role="user", content=data.message)
        db.add(user_msg)
        db.commit()

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )

        reply_final = response.choices[0].message.content.strip()

        # ── CRISIS DETECTION ─────────────────────────────────────────────────
        # 1. Keyword-based detection (instant, no AI needed)
        CRISIS_KEYWORDS = [
            "want to die", "kill myself", "end my life", "suicide", "suicidal",
            "i want to kill", "want to end it", "don't want to live", "dont want to live",
            "no reason to live", "can't go on", "cant go on", "better off dead",
            "hurt myself", "cut myself", "self harm", "self-harm", "overdose",
            "jump off", "hang myself", "slit my", "take my own life",
            # Telugu/Kannada/Hindi transliterations
            "chaavu", "saayali", "saagam", "marana", "atmahatya", "jeevitam vundadu",
            "nenu chaavali", "saayana", "naa life end", "mari jaunga", "marna chahta"
        ]
        msg_lower = data.message.lower()
        keyword_crisis = any(kw in msg_lower for kw in CRISIS_KEYWORDS)

        # 2. AI-tag based detection
        ai_crisis = "[EMERGENCY_TRIGGERED]" in reply_final
        if ai_crisis:
            reply_final = reply_final.replace("[EMERGENCY_TRIGGERED]", "").strip()

        if keyword_crisis or ai_crisis:
            contacts = current_user.emergency_contacts
            contact_names = [c.name for c in contacts] if contacts else []

            # ── Cooldown check: only alert once per ALERT_COOLDOWN_MINUTES per session ──
            now = datetime.utcnow()
            last_alert = _last_alert_time.get(session_id)
            cooldown_active = (
                last_alert is not None and
                (now - last_alert).total_seconds() < ALERT_COOLDOWN_MINUTES * 60
            )

            if contacts and not cooldown_active:
                # First crisis alert in this window — send notifications
                _last_alert_time[session_id] = now
                phone_numbers = [c.phone_number for c in contacts]
                alert_text = (
                    f"🚨 URGENT: {current_user.full_name} is showing signs of emotional crisis "
                    f"and may need immediate support. This is an automated alert from MindSense AI. "
                    f"Please check on them immediately."
                )

                sent_channels = []
                if send_whatsapp_greenapi(phone_numbers, alert_text):
                    sent_channels.append("WhatsApp")
                if send_sms_android_gateway(phone_numbers, alert_text):
                    sent_channels.append("SMS")
                if send_emergency_email(current_user.email, current_user.full_name, contacts):
                    sent_channels.append("Email")

                channel_str = " + ".join(sent_channels) if sent_channels else "no channels configured"
                alert_msg = (
                    f"\n\n🚨 **Emergency Alert Sent** — Your contacts ({', '.join(contact_names)}) "
                    f"have been notified via {channel_str}. You are not alone. Help is on the way."
                )
                print(f"[CRISIS] Alert sent for session {session_id} via {channel_str}")

            elif contacts and cooldown_active:
                # Alert already sent recently — remind user without re-notifying contacts
                mins_ago = int((now - last_alert).total_seconds() / 60)
                alert_msg = (
                    f"\n\n💙 Your contacts ({', '.join(contact_names)}) were already notified "
                    f"{mins_ago} minute(s) ago. You are not alone."
                )
                print(f"[CRISIS] Cooldown active for session {session_id}, skipping re-alert")

            else:
                alert_msg = (
                    "\n\n🚨 **Crisis Detected** — No emergency contacts found. "
                    "Please add contacts in your Profile page so we can alert them automatically."
                )

            reply_final += alert_msg
        # ── END CRISIS DETECTION ─────────────────────────────────────────────


        assistant_msg = models.ChatHistory(session_id=session_id, role="assistant", content=reply_final)
        db.add(assistant_msg)
        
        session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
            
        db.commit()

        # Add background task to extract memory so it doesn't delay the chat response
        background_tasks.add_task(extract_and_update_memory, current_user.id, data.message, current_user.memory_profile or "")

        return {"reply": reply_final, "reply_en": reply_final, "session_id": session_id}


    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ---------- FILE UPLOAD ----------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    try:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = file.filename.split(".")[-1].lower()
        content = ""

        if ext == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
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
            "content": content[:3000] # return up to 3000 chars to avoid overwhelming the prompt
        }

    except Exception as e:
        return {"error": str(e)}

# ---------- AUDIO ----------
from fastapi.responses import FileResponse

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    """Transcribe audio using Groq's hosted Whisper Large v3 API.
    Supports webm, mp3, mp4, wav, ogg, flac — no local ffmpeg required.
    """
    try:
        os.makedirs("uploads", exist_ok=True)
        path = f"uploads/{file.filename}"

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Validate file is not empty (silent recording)
        file_size = os.path.getsize(path)
        if file_size < 1000:  # less than 1KB is likely an empty/silent recording
            return {"text": ""}

        mime_type = file.content_type or "audio/webm"
        print(f"[TRANSCRIBE] filename={file.filename}, size={file_size}b, mime={mime_type}")

        # Use Groq's hosted Whisper API — handles webm/audio natively, no ffmpeg needed
        with open(path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(file.filename, audio_file, mime_type),
                model="whisper-large-v3",
                response_format="text",
            )

        # Groq returns plain text string when response_format="text"
        text = transcription.strip() if isinstance(transcription, str) else (transcription.text or "").strip()
        print(f"[TRANSCRIBE] result: '{text[:60]}'")

        return {"text": text}

    except Exception as e:
        print("TRANSCRIBE ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

class TTSRequest(schemas.BaseModel):
    text: str
    language: str = "en"

@app.post("/tts")
def tts_generate(data: TTSRequest):
    try:
        tts_lang = data.language
        if tts_lang not in ['en', 'hi', 'kn', 'ta', 'te', 'ml', 'mr', 'bn', 'gu', 'pa', 'ur']:
            tts_lang = 'en'
            
        tts = gTTS(text=data.text, lang=tts_lang)
        os.makedirs("uploads", exist_ok=True)
        file_path = "uploads/output.mp3"
        tts.save(file_path)
        return FileResponse(file_path, media_type="audio/mpeg")
    except Exception as e:
        print("TTS ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    try:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = file.filename.split(".")[-1].lower()
        if ext not in ["mp4", "mov", "avi", "webm"]:
            return {"error": "Unsupported video format. Please upload MP4, MOV, or AVI."}

        # Extract middle frame and detect emotion
        cap = cv2.VideoCapture(file_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
        
        ret, frame = cap.read()
        cap.release()

        dominant_emotion = "neutral"
        if ret and DEEPFACE_AVAILABLE:
            try:
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                if isinstance(result, list):
                    dominant_emotion = result[0]['dominant_emotion']
                else:
                    dominant_emotion = result['dominant_emotion']
            except Exception as e:
                print("DeepFace Error:", e)
        elif not DEEPFACE_AVAILABLE:
            return {"error": "Emotion detection unavailable. Please run: pip install tf-keras"}

        return {
            "message": f"Video analyzed. Detected facial emotion: {dominant_emotion}",
            "type": "video",
            "emotion": dominant_emotion
        }

    except Exception as e:
        return {"error": str(e)}