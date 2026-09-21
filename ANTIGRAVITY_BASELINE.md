# ANTIGRAVITY_BASELINE.md — MindSenseAI Baseline Inspection

**Date:** 2026-09-16  
**Status:** Baseline Recorded. Zero application code modified in Phase 0.

---

## 1. Current Architecture

The system operates as a multimodal mental-health support assistant:
1. **Frontend:** Next.js 14 (App router, TypeScript, Tailwind CSS, react-webcam, Lucide icons).
2. **Backend:** FastAPI (`backend/main.py`) with SQLAlchemy SQLite database (`mindsense.db`).
3. **NLP & ML Pipelines:**
   - **Text Emotion:** Fine-tuned DeBERTa-v3-base (`chatbot/emotion/predictor.py`, `chatbot/models/emotion/emotion_best.pt`), 6 classes: `sadness, joy, love, anger, fear, surprise` (93.69% validation accuracy).
   - **Text Intent:** Fine-tuned DeBERTa-v3-base (`chatbot/intent/predictor.py`, `chatbot/models/intent/intent_best.pt`), 16 classes (~52% validation accuracy).
   - **Mental State:** Rule cascade with DeBERTa emotion fallback (`backend/deberta_predictor.py`).
   - **Analytics:** Secondary TF-IDF + Logistic Regression model (`backend/nlp_service.py`, `ml_module/mental_health_model.pkl`).
   - **Conversation Flow:** `ChatEngine` (`chatbot/conversation/chat_engine.py`) orchestrating rule overrides, intent/emotion predictors, and `ResponseGenerator` (`chatbot/conversation/response_generator.py`).
   - **Response Generation LLM:** Groq API (`openai/gpt-oss-20b` with fallbacks).
   - **Multimodal Video Emotion:** DeepFace via OpenCV (`/upload-video` in `backend/main.py`).
   - **Audio Transcription:** Hosted Groq Whisper Large v3 (`/transcribe`).
   - **TTS:** Google Text-to-Speech (`gTTS`).
   - **Emergency Notification:** Green API (WhatsApp), Android SMS Gateway, Gmail SMTP, CallMeBot, Meta WA stub.

---

## 2. Files Inspected

- `backend/main.py` (Endpoints: `/chat`, `/upload-video`, `/transcribe`, emergency alerts, translation)
- `backend/deberta_predictor.py` (Mental state classification rules + DeBERTa emotion mapping)
- `backend/nlp_service.py` (TF-IDF analytics)
- `backend/auth.py` & `backend/database.py` (Authentication and SQLite ORM)
- `chatbot/conversation/chat_engine.py` (Rule-based analysis, intent/emotion coordination)
- `chatbot/conversation/response_generator.py` (Groq completion + fallback generation)
- `chatbot/intent/predictor.py`, `model.py`, `config.py` (16-class DeBERTa intent predictor)
- `chatbot/emotion/predictor.py`, `model.py`, `config.py` (6-class DeBERTa emotion predictor)
- `frontend/app/chat/page.tsx` (Chat rendering, session handling, video emotion display)
- `frontend/app/dashboard/page.tsx` (Analytics display, emergency trigger)
- `frontend/lib/api.ts` & `frontend/hooks/useAuth.tsx`

---

## 3. Current Known Problems Identified

1. **Negation Failures across All Layers:**
   - Substring matching for phrases like `"want to die"` triggers crisis alerts on `"I don't want to die"`.
   - `"I am not sad."` matches `"sad"` in fallback/model, producing `Depression (95.25%)` and `suicidal_thought (0.47)`.
   - `"I don't feel stressed."` triggers `Stress (73.79%)` and `anger (73.79%)`.
   - `"I am not depressed."` produces `Depression (99.44%)`.
   - `"I am not anxious."` produces `Anxiety (99.96%)`.
2. **General/Casual Messages Forced into Mental Health Diagnoses:**
   - `"Good morning."` -> `Stress (89.38%)`, Intent: `addiction (0.14)`.
   - `"Thank you."` -> `Stress (61.89%)`, Intent: `addiction (0.14)`.
   - `"What can you do?"` -> `Stress (83.49%)`, Intent: `career_confusion`. Bot hallucinates: *"What's been going on that's got you feeling frustrated?"*
3. **Emergency Alert Privacy Leak to User:**
   - `backend/main.py` lines 1185, 1188, 1190 append emergency alert status, contact names, and notification channels directly into `reply_final` inside the chat bubble seen by the distressed user.
4. **Crisis Flow Lack of Staging:**
   - Crisis alert fires immediately on message 1 with no supportive first-step de-escalation or continued-risk evaluation.
5. **Video Emotion Multi-Emotion & Multi-Person Deficiencies:**
   - Video analysis drops all faces except `result[0]`. Multiple people in camera cannot be analyzed separately.
   - Temporal breakdown and emotion distribution are calculated in backend but never formatted or displayed for the user in the frontend.
6. **Multilingual Safety Gaps:**
   - Crisis keywords are primarily English with a few transliterated Telugu phrases. Native scripts (Hindi, Tamil, Kannada, Marathi, Malayalam, Bengali) risk failing if the translation pre-processing times out or returns empty.
7. **Encoding / Fallback Issues:**
   - Smart quotes or unicode characters sometimes trigger empty Groq responses or mojibake in terminal.
   - Groq fallback responses are overly generic (`"I understand. Tell me a little more..."`).

---

## 4. Baseline Tests Performed & Results

Execution of `scratch/baseline_test.py` against active models produced:

| Input Message | Baseline Mental State | Baseline Intent (Confidence) | Baseline Emotion (Confidence) | Baseline Response / Behavior | Status |
|---|---|---|---|---|---|
| `I am happy today.` | Normal (98.0%, LOW) | positive_state (1.0) | joy (1.0) | "That's wonderful to hear! What's making today feel so good?" | PASS |
| `I am sad.` | Depression (98.0%, MEDIUM) | sadness (1.0) | sadness (1.0) | "I'm sorry you're feeling that way..." | PASS |
| `I am not sad.` | **Depression (95.25%, MEDIUM)** | **suicidal_thought (0.47)** | **sadness (95.25)** | Groq returned empty response; bot asked how day is going | **FAIL** (Negation broken) |
| `I feel stressed.` | Stress (98.0%, MEDIUM) | stress (1.0) | stress (1.0) | Natural empathetic stress response | PASS |
| `I don't feel stressed.` | **Stress (73.79%, MEDIUM)** | **stress (0.50)** | **anger (73.79)** | Generic fallback used | **FAIL** (Negation broken) |
| `I am depressed.` | Depression (98.38%, MEDIUM) | anger (0.24) | sadness (98.38) | Empathetic depression response | PASS |
| `I am not depressed.` | **Depression (99.44%, MEDIUM)** | depression (0.26) | **sadness (99.44)** | Responded that it's good to hear feeling okay | **FAIL** (Model classified as Depression) |
| `I am anxious.` | Anxiety (98.0%, MEDIUM) | anxiety (1.0) | fear (1.0) | Empathetic anxiety response | PASS |
| `I am not anxious.` | **Anxiety (99.96%, MEDIUM)** | **career_confusion (0.51)** | **fear (99.96)** | Hallucinated career confusion | **FAIL** (Negation broken) |
| `I want to die.` | Suicidal (100%, HIGH) | suicidal_thought (1.0) | sadness (1.0) | Crisis response triggered | PASS |
| `I don't want to die.` | **Suicidal (100%, HIGH)** | **suicidal_thought (0.86)** | fear (37.43) | **CRISIS RESPONSE FALSE POSITIVE** | **CRITICAL FAIL** |
| `I feel like dying.` | Suicidal (100%, HIGH) | suicidal_thought (1.0) | sadness (1.0) | Crisis response triggered | PASS |
| `Good morning.` | **Stress (89.38%, MEDIUM)** | **addiction (0.14)** | **anger (89.38)** | "Good morning! Hope your day is off to a smooth start..." | **FAIL** (Falsely labeled Stress/Anger) |
| `Thank you.` | **Stress (61.89%, MEDIUM)** | **addiction (0.15)** | **anger (61.89)** | "You're welcome! If there's anything else..." | **FAIL** (Falsely labeled Stress/Anger) |
| `What can you do?` | **Stress (83.49%, MEDIUM)** | **career_confusion (0.27)** | **anger (83.49)** | "...What's been going on that's got you feeling frustrated?" | **FAIL** (Hallucinated frustration) |
| `Yesterday I was stressed, but today I feel excited and happy.` | Normal (98.0%, LOW) | **suicidal_thought (0.38)** | joy (99.98) | Empathetic positive response | **FAIL** (Intent hallucinated suicidal_thought) |

---

## 5. Files That Will Need Modification

1. `chatbot/conversation/response_generator.py` (Fix response prompts, situational fallbacks, error handling, encoding safety, crisis prompt separation).
2. `chatbot/conversation/chat_engine.py` (Negation handling, general/casual intent classification, mixed-emotion awareness, crisis pattern scope).
3. `backend/deberta_predictor.py` (Negation scope checking, non-clinical general/normal statement handling, anxiety vs depression distinction, crisis negation protection).
4. `backend/main.py`:
   - Crisis keyword matching (prevent negation match like "don't want to die").
   - Safety response flow (do not leak emergency notification text/contact names to user in chat).
   - Multilingual safety (pre-translation and post-translation crisis detection for Indian languages).
   - Video emotion multi-person support (detect all faces, per-person tracking/aggregation).
   - Video emotion multi-emotion distribution & temporal tracking.
5. `frontend/app/chat/page.tsx` (Display emotion distribution clearly, support multi-person emotion summary if returned, render clean responses without alert text leaks).

*Phase 0 inspection complete.*
