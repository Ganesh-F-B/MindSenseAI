# 🧠 MindSense AI — Mental Health Companion Platform

<div align="center">

![MindSense AI](https://img.shields.io/badge/MindSense-AI-blue?style=for-the-badge&logo=brain&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**An AI-powered mental health platform with real-time emotion detection, multilingual support, and automatic emergency alerts.**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Emergency Alert System](#-emergency-alert-system)
- [Multilingual Support](#-multilingual-support)
- [API Reference](#-api-reference)
- [Pages & Routes](#-pages--routes)

---

## 🌟 Overview

MindSense AI is a full-stack mental health companion application that provides:
- Empathetic AI conversations powered by **Groq LLaMA 3.3 70B**
- **Facial emotion detection** via webcam video using DeepFace
- **Automatic crisis detection** from conversation text
- **Multi-channel emergency alerts** (WhatsApp + SMS + Email) sent instantly to trusted contacts
- Support for **11 Indian languages** with automatic language detection

---

## ✨ Features

### 💬 AI Chat
- Powered by **Groq LLaMA 3.3 70B** — fast, accurate, empathetic responses
- **Auto language detection** — detects the language of each message and responds in the same language
- Supports switching languages mid-conversation (English, Hindi, Telugu, Kannada, Tamil, etc.)
- **Voice input** — speak instead of type using Groq Whisper API transcription
- **Text-to-speech** — AI replies read aloud using gTTS
- **File upload** — analyze PDF/TXT documents in context
- **Memory profile** — AI remembers key facts about you across sessions
- Chat sessions saved and organized in sidebar with rename and delete support

### 😊 Facial Emotion Detection
- Record a short webcam video
- AI analyzes your facial expression using **DeepFace** + **OpenCV**
- Detected emotion (happy, sad, angry, neutral, etc.) is passed as context to the AI
- AI responds empathetically based on your detected emotion

### 🚨 Emergency Alert System
Automatic crisis detection triggers alerts when:
1. **Keyword detection** — messages containing crisis words in English or Indian languages
2. **AI detection** — AI model identifies suicidal intent from context

**Alert channels:**

| Priority | Channel | Service |
|---|---|---|
| 1st | WhatsApp | Green API (free 500 msg/month) |
| 2nd | SMS | Android SMS Gateway (free via SIM) |
| 3rd | WhatsApp | CallMeBot (per-contact opt-in) |
| 4th | Email | Gmail SMTP |

Alert cooldown: 15 minutes per session to prevent contact spam.

### 👤 Profile Management
- Update personal info (name, email, phone)
- Add emergency contacts with name and phone number
- Contacts receive instant WhatsApp/SMS/Email alerts when SOS is pressed or crisis is auto-detected

### ⚙️ Settings
- Dark / Light theme toggle (persists across sessions)
- Browser notification permissions
- Account info and Edit link
- **Delete Account** — permanently removes all data with confirmation
- **Log Out**

---

## 🛠 Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js 14** | React framework with App Router |
| **TypeScript** | Type-safe development |
| **Framer Motion** | Smooth animations |
| **Lucide React** | Icon library |
| **Axios** | HTTP client |

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | Python REST API framework |
| **SQLAlchemy** | ORM for local SQLite database |
| **SQLite** | Local database (`mindsense.db`) |
| **Groq SDK** | LLaMA 3.3 70B AI model + Whisper transcription |
| **DeepFace** | Facial emotion analysis |
| **OpenCV** | Video frame extraction |
| **gTTS** | Text-to-speech generation |
| **PyPDF** | PDF text extraction |
| **python-jose** | JWT authentication |
| **passlib** | Password hashing (bcrypt) |
| **smtplib** | Gmail email alerts |
| **requests** | WhatsApp & SMS API calls |

---

## 📁 Project Structure

```
MindSenseAI/
├── frontend/                     # Next.js application
│   ├── app/
│   │   ├── page.tsx              # Landing page
│   │   ├── login/page.tsx        # Login
│   │   ├── signup/page.tsx       # Registration
│   │   ├── dashboard/page.tsx    # Main dashboard + SOS button
│   │   ├── chat/page.tsx         # AI chat interface
│   │   ├── profile/page.tsx      # Emergency contacts management
│   │   ├── settings/page.tsx     # App settings
│   │   └── globals.css           # Global styles + theme variables
│   ├── hooks/
│   │   └── useAuth.ts            # Authentication hook
│   └── lib/
│       └── api.ts                # Axios instance
│
├── backend/                      # FastAPI application
│   ├── main.py                   # All routes and business logic
│   ├── models.py                 # SQLAlchemy database models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── auth.py                   # JWT authentication utilities
│   ├── database.py               # Database connection (SQLite)
│   ├── migrate_callmebot.py      # DB migration script
│   ├── .env                      # Environment variables (not committed)
│   └── uploads/                  # Temporary file storage
│
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **npm**

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/MindSenseAI.git
cd MindSenseAI
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run database migration (adds callmebot_key column)
python migrate_callmebot.py

# Start the server
uvicorn main:app --reload
```
Backend runs at: `http://localhost:8000`

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```
Frontend runs at: `http://localhost:3000`

### 4. Configure Environment Variables
Copy and fill in the `.env` file in the `backend/` directory (see section below).

---

## 🔐 Environment Variables

Create `backend/.env` with the following:

```env
# ── Core ──────────────────────────────────────────────────────
GROQ_API_KEY=your_groq_api_key

# ── WhatsApp Alerts (Green API — Free 500 msg/month) ──────────
# Setup: green-api.com → Sign up → Create Instance → Scan QR with WhatsApp
GREENAPI_ID_INSTANCE=your_instance_id
GREENAPI_API_TOKEN=your_api_token

# ── SMS Alerts (Android SMS Gateway — Free via your SIM) ──────
# Install "SMS Gate" APK from github.com/capcom6/android-sms-gateway
SMS_GATE_LOGIN=your_login
SMS_GATE_PASSWORD=your_password

# ── Email Alerts (Gmail — Free) ───────────────────────────────
# Setup: myaccount.google.com/apppasswords → create App Password
GMAIL_SENDER_EMAIL=youremail@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
```

### How to get each key:

| Key | Where to get |
|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys |
| `GREENAPI_ID_INSTANCE` + `GREENAPI_API_TOKEN` | [green-api.com](https://green-api.com) → Create Instance → Scan QR |
| `SMS_GATE_LOGIN/PASSWORD` | [github.com/capcom6/android-sms-gateway](https://github.com/capcom6/android-sms-gateway/releases/latest) → install APK |
| `GMAIL_APP_PASSWORD` | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) |

---

## 🚨 Emergency Alert System

### How it works

```
User says crisis words in chat
         ↓
  Crisis detected (keyword OR AI tag)
         ↓
  ┌──────────────────────────────────┐
  │  1. WhatsApp (Green API)         │ ← instant, your own WhatsApp number
  │  2. SMS (Android SMS Gateway)   │ ← works via SIM, no internet needed
  │  3. WhatsApp (CallMeBot)        │ ← per-contact opt-in
  │  4. Email (Gmail SMTP)          │ ← backup
  └──────────────────────────────────┘
         ↓
  Chat shows: "🚨 Emergency Alert Sent — Contacts notified"
  (15-minute cooldown to prevent duplicate alerts)
```

### Crisis Keywords Detected

English: `suicide`, `kill myself`, `want to die`, `self harm`, `overdose`, etc.

Indian languages (transliterated): `chaavu`, `atmahatya`, `marana`, `nenu chaavali`, `marna chahta`, etc.

### SOS Button

The Dashboard has a manual **SOS button** that immediately triggers all alert channels.

---

## 🌐 Multilingual Support

MindSense AI supports **11 languages** with automatic detection:

| Language | Native Script | Transliteration |
|---|---|---|
| English | ✅ | — |
| Hindi | ✅ (Devanagari) | ✅ (Hinglish) |
| Telugu | ✅ | ✅ (Tenglish) |
| Kannada | ✅ | ✅ (Kanglish) |
| Tamil | ✅ | ✅ |
| Malayalam | ✅ | — |
| Bengali | ✅ | — |
| Gujarati | ✅ | — |
| Punjabi | ✅ (Gurmukhi) | — |
| Marathi | ✅ | ✅ |
| Urdu | ✅ | — |

**Language detection priority:**
1. Checks for native Unicode script characters first
2. Keyword matching for transliterated text
3. Short common words (hi, hey, ok) → defaults to English

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/signup` | Register new user |
| `POST` | `/token` | Login, get JWT token |
| `GET` | `/users/me` | Get current user profile |
| `DELETE` | `/users/me` | Permanently delete account |
| `POST` | `/chat` | Send message, get AI reply |
| `GET` | `/chat/sessions` | Get all chat sessions |
| `GET` | `/chat/sessions/{id}` | Get messages in a session |
| `PUT` | `/chat/sessions/{id}` | Rename a chat session |
| `DELETE` | `/chat/sessions/{id}` | Delete a chat session |
| `POST` | `/emergency` | Trigger SOS alert manually |
| `PUT` | `/emergency-contacts` | Update emergency contacts |
| `POST` | `/upload` | Upload PDF/TXT for analysis |
| `POST` | `/upload-video` | Upload webcam video for emotion detection |
| `POST` | `/transcribe` | Transcribe audio to text (Groq Whisper) |
| `POST` | `/tts` | Text to speech (gTTS) |

---

## 📱 Pages & Routes

| Route | Page |
|---|---|
| `/` | Landing page |
| `/login` | Login |
| `/signup` | Register |
| `/dashboard` | Main dashboard with SOS button |
| `/chat` | AI conversation |
| `/profile` | Manage emergency contacts |
| `/settings` | Theme, notifications, account |

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<div align="center">
  Built with ❤️ for mental health awareness
  <br/>
  <strong>If you or someone you know is in crisis, please call your local emergency number immediately.</strong>
</div>
