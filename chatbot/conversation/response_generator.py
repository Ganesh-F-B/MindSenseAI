import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

logger = logging.getLogger(__name__)

# Load .env from backend folder
BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV = BASE_DIR / "backend" / ".env"

load_dotenv(BACKEND_ENV)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY NOT FOUND")
else:
    logger.info("GROQ_API_KEY detected")


class ResponseGenerator:

    def __init__(self):
        self.client = None

        if GROQ_API_KEY:
            try:
                self.client = Groq(api_key=GROQ_API_KEY)
                logger.info("Groq client initialized")
            except Exception:
                logger.exception("Failed to initialize Groq client")

    def _crisis_response(self):
        return (
            "I'm really glad you told me. You don't have to face this alone. "
            "Please stay with someone you trust and seek immediate support "
            "if you feel you might act on these thoughts."
        )

    def _is_explicit_crisis_message(self, message):
        """Return True only when the CURRENT user message contains clear
        self-harm/suicide language. Model predictions must not override this.
        Explicitly rejects negated statements like 'I don't want to die'."""
        text = str(message or "").lower().strip()
        if not text:
            return False

        import re

        # 1. Passive ideation: explicit negation of the desire to live/exist is crisis
        passive_crisis_patterns = [
            r"\b(?:don'?t|dont|do not|didn'?t|did not|never|can'?t|cannot|no\s+longer)\s+(?:really\s+)?(?:want|wanna)\s+to\s+(?:live|keep living|stay alive|be alive|exist|wake up)\b",
            r"\bno\s+(?:reason|point|purpose)\s+(?:for\s+me\s+)?(?:to\s+)?(?:live|living|keep\s+living|stay\s+alive|be\s+alive|go\s+on)\b",
            r"\b(?:tired|exhausted|done|sick)\s+of\s+(?:living|life|existing)\b",
            r"\b(?:better\s+off\s+(?:without\s+me|dead)|better\s+without\s+me|world\s+(?:would\s+be\s+)?better\s+without\s+me)\b",
            r"\b(?:wish|wishing)\s+(?:i\s+)?(?:could\s+disappear|disappear\s+forever|was\s+never\s+born|were\s+never\s+born|was\s+dead|were\s+dead)\b",
            r"\b(?:wish|wished)\s+i\s+(?:never\s+woke\s+up|wouldn'?t\s+wake\s+up|didnt\s+wake\s+up)\b",
            r"\b(?:no\s+one|nobody)\s+(?:would\s+)?(?:care|miss\s+me|notice)\s+(?:if\s+i\s+(?:died|was\s+gone|disappeared|wasnt\s+here))\b",
            r"\b(?:cannot|cant)\s+go\s+on\s+living\b",
        ]
        if any(re.search(p, text) for p in passive_crisis_patterns):
            return True

        # 2. If statement explicitly negates suicidal ideation or self-harm, or affirms life, it is NOT crisis.
        negated_crisis_patterns = [
            r"\b(?:don'?t|dont|do not|never|no|not|didn'?t|did not|won'?t|will not|can'?t|cannot|ain'?t|no\s+longer)\s+(?:really\s+)?(?:want|wanna|feel like|plan|planning|intend|intending|wish|wishing|trying)\s+(?:to\s+)?(?:die|kill myself|end my life|end it all|hurt myself|harm myself|be dead|cease to exist|give up on life)\b",
            r"\b(?:don'?t|dont|do not|never|can'?t|cannot|won'?t)\s+(?:feel like|wanna|want to)\s+(?:dying|die|ending it)\b",
            r"\bi\s+(?:don'?t|dont|do not|never|won'?t)\s+want\s+to\s+die\b",
            r"\bi\s+(?:don'?t|dont|do not|never)\s+feel\s+like\s+hurting\s+myself\b",
            r"\bno\s+(?:desire|plan|intention|urge)\s+to\s+(?:die|kill myself|end my life|hurt myself)\b",
            r"\b(?:not|never|no\s+longer)\s+(?:feeling\s+)?suicidal\b",
            r"\bnot\s+(?:going to|gonna)\s+(?:kill myself|die|hurt myself|end my life)\b",
            # Direct life affirmations
            r"\b(?:i\s+)?(?:want|wanna|choose|choosing|decided|planning|intend)\s+to\s+(?:live|keep living|stay alive|be alive)\b",
            r"\b(?:glad|happy|grateful|proud)\s+to\s+be\s+alive\b",
            r"\bi\s+love\s+(?:my\s+)?life\b",
            r"\bwant\s+to\s+live\b",
        ]
        for np in negated_crisis_patterns:
            if re.search(np, text):
                return False

        # 3. Active Suicidal Ideation & Self-Harm
        crisis_patterns = [
            r"\b(?:i\s+)?(?:want to|wanna|wish to|feel like|planning to|thinking of|intend to|going to|gonna)\s+(?:to\s+)?(?:die|dying|kill myself|end my life|take my own life|end it all)\b",
            r"\b(?:kill(?:ing)?\s+myself|end(?:ing)?\s+my\s+life|take\s+my\s+(?:own\s+)?life)\b",
            r"\b(?:suicid(?:e|al|ing)|commit\s+suicide)\b",
            r"\b(?:hang\s+myself|overdose|slit\s+(?:my\s+)?wrists?|slitting\s+(?:my\s+)?wrists?|jump\s+off\s+(?:a\s+)?(?:bridge|building|roof))\b",
            r"\b(?:hurt|hurting|harm|harming|cut|cutting|burn|burning)\s+myself\b",
            r"\bself[\s-]harm(?:ing)?\b",
        ]
        return any(re.search(p, text) for p in crisis_patterns)

    def generate_video_response(
        self,
        face_emotion="neutral",
        mental_state="Normal",
        risk_level="LOW",
        history=None,
        memory="",
    ):
        """
        Generate a natural chatbot response for a video-only analysis where
        there is NO user text message. The detected facial emotion is passed
        as structured multimodal context, and Groq produces a natural,
        empathetic response to the detected emotion.
        """
        if history is None:
            history = []

        face_emotion = str(face_emotion or "neutral").lower().strip()
        mental_state = str(mental_state or "Normal")
        risk_level = str(risk_level or "LOW").upper()

        # ---------------------------------------------------------
        # SAFETY OVERRIDE
        # ---------------------------------------------------------
        # Video-only input has no user text. Preserve HIGH-risk behavior.
        if risk_level == "HIGH":
            return self._crisis_response()

        # ---------------------------------------------------------
        # IF GROQ IS NOT AVAILABLE
        # ---------------------------------------------------------
        if self.client is None:
            # Basic fallback so the flow always produces a response.
            fallback_map = {
                "happy": "You seem to be in a positive mood from your facial expression. That's nice to see! What's making you feel good today?",
                "sad": "You seem to be feeling a little low right now. I'm here to listen. Is there something that's been weighing on you?",
                "angry": "It looks like you might be feeling frustrated or upset. I'm here to listen if you want to talk about it.",
                "fear": "You seem a bit tense or worried. Would you like to talk about what's on your mind?",
                "surprise": "That expression looks like something caught you by surprise. What happened?",
                "disgust": "You look like something didn't sit right with you. Want to talk about it?",
                "neutral": "I'm here with you. How are you feeling right now?",
            }
            return fallback_map.get(
                face_emotion,
                "I'm here with you. How are you feeling right now?",
            )

        # ---------------------------------------------------------
        # BUILD RECENT CONVERSATION
        # ---------------------------------------------------------
        conversation = []
        for item in history[-10:]:
            if not isinstance(item, dict):
                continue
            user_text = item.get("user", "")
            bot_text = item.get("bot", "")
            if user_text:
                conversation.append(f"User: {user_text}")
            if bot_text:
                conversation.append(f"MindSense AI: {bot_text}")
        history_text = "\n".join(conversation)

        # ---------------------------------------------------------
        # SYSTEM PROMPT (video-only multimodal context)
        # ---------------------------------------------------------
        system_prompt = """
You are MindSense AI, a natural and supportive conversational AI.

The user just shared a video of themselves. The visual emotion-detection
system analyzed their facial expression and detected the emotion below.

There is NO text message from the user. Your ONLY job is to respond
naturally to the detected facial emotion, as if you noticed their mood.

Rules:
1. NEVER mention "video", "analysis", "detection", "model", "confidence",
   "risk engine", "AI", or any internal system.
2. NEVER say things like "I detected" or "the system detected".
3. Speak as a caring companion who simply noticed how they look.
4. Use the user's detected emotion as the basis for a natural, warm,
   1-3 sentence response.
5. Ask at most ONE gentle follow-up question.
6. If the emotion is positive (happy/surprise/neutral), respond warmly and
   naturally.
7. If the emotion is negative (sad/angry/fear/disgust), respond with empathy
   and offer to listen, without forcing a diagnosis.
8. Do NOT repeat the same template response every time.

Examples of desired behavior:

Facial emotion: happy
Good:
"Things seem to be going well for you today — that smile says a lot! What's
putting you in a good mood?"

Facial emotion: sad
Good:
"You look like you might be feeling a little low right now. I'm here to
listen. Is there something that's been weighing on you?"

Facial emotion: angry
Good:
"It seems like something is really frustrating you. I'm here to listen if
you want to talk it through."

Facial emotion: fear
Good:
"You seem a bit tense right now. What's on your mind — want to talk about it?"

Facial emotion: neutral
Good:
"I'm here with you. How are you feeling right now?"
"""

        user_prompt = f"""
DETECTED FACIAL EMOTION:
{face_emotion}

MENTAL STATE:
{mental_state}

RISK LEVEL:
{risk_level}

USER MEMORY:
{memory if memory else "None"}

RECENT CONVERSATION:
{history_text if history_text else "None"}

Now write the best natural response to the user's current emotional state.
"""

        # ---------------------------------------------------------
        # CALL GROQ
        # ---------------------------------------------------------
        models_to_try = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        for m_name in models_to_try:
            try:
                result = self.client.chat.completions.create(
                    model=m_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=600,
                )

                response = ""
                if result and result.choices:
                    response = result.choices[0].message.content.strip()

                    # Clean smart quotes and unicode dashes
                    response = (
                        response.replace("\u2019", "'")
                        .replace("\u2018", "'")
                        .replace("\u201c", '"')
                        .replace("\u201d", '"')
                        .replace("\u2014", " - ")
                        .replace("\u2013", "-")
                        .replace("\u2011", "-")
                        .replace("\u2026", "...")
                    )
                    return response

                logger.warning(f"Groq {m_name} returned empty video response, trying fallback")

            except Exception as exc:
                logger.warning(f"Groq {m_name} error in video response: {exc}")

        # ---------------------------------------------------------
        # FINAL FALLBACK
        # ---------------------------------------------------------
        fallback_map = {
            "happy": "You seem to be in a positive mood from your facial expression. That's nice to see! What's making you feel good today?",
            "sad": "You seem to be feeling a little low right now. I'm here to listen. Is there something that's been weighing on you?",
            "angry": "It looks like you might be feeling frustrated or upset. I'm here to listen if you want to talk about it.",
            "fear": "You seem a bit tense or worried. Would you like to talk about what's on your mind?",
            "surprise": "That expression looks like something caught you by surprise. What happened?",
            "disgust": "You look like something didn't sit right with you. Want to talk about it?",
            "neutral": "I'm here with you. How are you feeling right now?",
        }
        return fallback_map.get(
            face_emotion,
            "I'm here with you. How are you feeling right now?",
        )

    def _safe_fallback(self, message, emotion="neutral", intent="general", risk_level="LOW"):
        import re
        msg_clean = re.sub(r"[^\w\s]", " ", (message or "").lower()).strip()
        msg_clean = re.sub(r"\s+", " ", msg_clean)

        if str(risk_level).upper() == "HIGH":
            return self._crisis_response()

        # Negated crisis & life affirmations
        if any(re.search(p, msg_clean) for p in [
            r"\b(?:dont|do not|never|cant|cannot|wont)\s+(?:really\s+)?(?:want|feel like)\s+(?:to\s+)?(?:die|kill|hurt|harm)\b",
            r"\bnot\s+(?:feeling\s+)?suicidal\b",
            r"\b(?:want|choose|decided)\s+to\s+(?:live|keep living|stay alive)\b",
            r"\bglad\s+to\s+be\s+alive\b",
        ]):
            return "I hear you, and I'm really glad to hear you say that. Choosing to live and keep going is powerful. What's something that is keeping you grounded or bringing you hope today?"

        # Greetings & pleasantries
        if msg_clean in {
            "hi", "hello", "hey", "hii", "hiii", "good morning", "good afternoon",
            "good evening", "howdy", "sup", "greetings"
        }:
            return "Hello! I'm MindSense AI, your mental wellness companion. How are you feeling today?"

        if "thank" in msg_clean:
            return "You're very welcome! I'm always here if you want to talk or unpack what's on your mind."

        if any(p in msg_clean for p in ["who are you", "what are you", "what is mindsense"]):
            return (
                "I'm MindSense AI, a supportive companion designed to listen, "
                "help you reflect on your thoughts and feelings, and support your emotional wellbeing."
            )

        if any(p in msg_clean for p in ["what can you do", "help me", "how can you help"]):
            return (
                "I'm here to listen without judgment, help you work through stress, anxiety, or low moods, "
                "and offer practical self-care techniques. What would you like to explore today?"
            )

        if any(p in msg_clean for p in ["how are you", "how r u", "how are u"]):
            return "I'm here and ready to support you. How has your day been going so far?"

        # Situational fallbacks by intent / emotion
        intent = str(intent or "general").lower()
        emotion = str(emotion or "neutral").lower()

        if intent in {"positive_state", "joy"} or emotion in {"joy", "love"}:
            return "That's wonderful to hear! Having moments of lightness and joy is so important. What contributed to making you feel this way?"

        if intent in {"stress", "workload_stress"} or emotion == "stress":
            return (
                "It sounds like you're carrying a heavy load right now. When tasks pile up, it's easy to feel overwhelmed. "
                "Would it help to take one deep breath and focus on just one small step at a time?"
            )

        if intent == "anxiety" or emotion == "fear":
            return (
                "I hear that worry and tension in what you're sharing. Anxiety can be really draining on your mind and body. "
                "What feels like the biggest unknown or concern for you right now?"
            )

        if intent in {"sadness", "depression"} or emotion == "sadness":
            return (
                "I'm really sorry you're feeling down right now. You don't have to navigate these heavy feelings by yourself. "
                "Would you like to talk about what's been weighing on your heart?"
            )

        if intent == "anger" or emotion == "anger":
            return (
                "It makes total sense that you'd feel frustrated or angry about this. Feeling irritated is a valid emotion. "
                "What happened that triggered this feeling?"
            )

        if intent == "sleep_problem":
            return (
                "Restless nights can make everything in life feel so much more difficult. "
                "Is your mind racing with worries, or is physical tension making it hard to fall asleep?"
            )

        if intent in {"relationship", "friendship", "breakup"}:
            return (
                "Interpersonal challenges and changes in relationships can be deeply painful and confusing. "
                "If you feel comfortable, what happened between you two?"
            )

        if intent in {"career_confusion", "academic"}:
            return (
                "Decisions about your studies or career path can feel daunting when there are so many expectations. "
                "What options or pressures are currently on your plate?"
            )

        return "I'm here with you and listening attentively. Tell me a little more about what you're experiencing today."

    def generate(
        self,
        message,
        emotion="neutral",
        intent="general",
        history=None,
        memory="",
        face_emotion=None,
        risk_level="LOW",
        is_negated_crisis=False,
    ):

        if history is None:
            history = []

        message = str(message or "").strip()

        # ---------------------------------------------------------
        # SAFETY OVERRIDE
        # ---------------------------------------------------------
        # Safety is based on the CURRENT message, not a possibly noisy
        # emotion/intent prediction or an older conversation turn.
        # This prevents benign messages such as "I am very happy" from
        # receiving a crisis response when an auxiliary classifier is wrong.
        explicit_crisis = self._is_explicit_crisis_message(message)

        if explicit_crisis:
            return self._crisis_response()

        # ---------------------------------------------------------
        # IF GROQ IS NOT AVAILABLE
        # ---------------------------------------------------------
        if self.client is None:
            logger.error("Groq client unavailable. Using fallback response.")

            return self._safe_fallback(
                message,
                emotion=emotion,
                intent=intent,
                risk_level=risk_level,
            )

        # ---------------------------------------------------------
        # BUILD RECENT CONVERSATION
        # ---------------------------------------------------------
        conversation = []

        for item in history[-10:]:

            if not isinstance(item, dict):
                continue

            user_text = item.get("user", "")
            bot_text = item.get("bot", "")

            if user_text:
                conversation.append(f"User: {user_text}")

            if bot_text:
                conversation.append(f"MindSense AI: {bot_text}")

        history_text = "\n".join(conversation)

        # ---------------------------------------------------------
        # FACIAL CONTEXT
        # ---------------------------------------------------------
        face_text = "No facial emotion available."

        if face_emotion:
            face_text = (
                f"The visual system detected facial emotion: " f"{face_emotion}."
            )

        # ---------------------------------------------------------
        # SYSTEM PROMPT
        # ---------------------------------------------------------
        system_prompt = """
You are MindSense AI, a natural and supportive conversational AI.

Your PRIMARY job is to understand the user's actual message and respond
naturally to what they said.

IMPORTANT:

1. ALWAYS respond to the CURRENT USER MESSAGE.
2. Understand the meaning of the entire sentence, not just keywords.
3. Do NOT blindly follow the predicted intent.
4. Do NOT blindly follow the predicted emotion.
5. The predicted emotion and intent are supporting signals only.
6. Never force a mental-health response when the user is having a normal
   conversation.
7. If the user talks about normal life, respond normally.
8. If the user shares happiness, celebrate naturally.
9. If the user shares stress, anxiety, sadness, anger, loneliness,
   relationship problems, sleep problems, academic pressure, work pressure,
   etc., respond appropriately and empathetically.
10. If the user asks a factual or casual question, answer it naturally.
11. Never invent something the user did not say.
12. Never assume the user is angry, depressed, anxious, or suicidal without
    evidence.
13. Ask at most ONE useful follow-up question when appropriate.
14. Keep normal responses concise: usually 1–3 sentences.
15. Do not mention AI models, classifiers, prompts, confidence scores,
    risk engines, APIs, or internal analysis.
16. Do not diagnose the user.
17. Do not sound robotic or repeat the same response.
18. Use the conversation history when it helps understand context.
19. If facial emotion conflicts with the user's words, prioritize the user's
    words and gently acknowledge the visual signal only when useful.
20. For explicit self-harm or suicide content, respond supportively and
    encourage immediate real-world help.

Examples of desired behavior:

User:
"I got a new job today."

Good:
"That's wonderful news! Congratulations! How are you feeling about your
new job?"

User:
"I have three assignments due tomorrow and I don't know where to start."

Good:
"That sounds like a lot to handle at once. Let's break it down into smaller
steps. Which assignment is due first?"

User:
"My friend stopped talking to me."

Good:
"I'm sorry, that can really hurt, especially when you don't know why.
Do you want to tell me what happened between you two?"

User:
"I ate biryani today."

Good:
"Nice! Was it homemade or did you eat out?"

User:
"I am happy today."

Good:
"That's great to hear! What's making today a good day for you?"

User:
"I am stressed because I have too much work."

Good:
"That sounds overwhelming when everything piles up at once. What part of
the workload is putting the most pressure on you?"

User:
"Who are you?"

Good:
"I'm MindSense AI, your mental-wellness companion. I'm here to listen,
talk things through, and help you understand how you're feeling."

Always respond to what the user ACTUALLY said.
"""

        user_prompt = f"""
CURRENT USER MESSAGE:
{message}

MODEL SIGNALS:
Emotion: {emotion}
Intent: {intent}
Risk level: {risk_level}

{face_text}

USER MEMORY:
{memory if memory else "None"}

RECENT CONVERSATION:
{history_text if history_text else "None"}

Now write the best natural response to the CURRENT USER MESSAGE.
"""

        # If user affirms life or negates crisis, inject explicit constraint to Groq
        is_life_affirmation_or_negation = (
            is_negated_crisis
            or any(
                re.search(np, (message or "").lower())
                for np in [
                    r"\b(?:don'?t|dont|do not|never|no|not|didn'?t|did not|won'?t|will not|can'?t|cannot|ain'?t|no\s+longer)\s+(?:really\s+)?(?:want|wanna|feel like|plan|intend|wish)\s+(?:to\s+)?(?:die|kill myself|end my life|end it all|hurt myself|harm myself|give up on life)\b",
                    r"\bnot\s+(?:feeling\s+)?suicidal\b",
                    r"\b(?:want|wanna|choose|decided)\s+to\s+(?:live|keep living|stay alive)\b",
                    r"\bglad\s+to\s+be\s+alive\b",
                    r"\bi\s+love\s+(?:my\s+)?life\b",
                ]
            )
        )
        if is_life_affirmation_or_negation:
            system_prompt += """
CRITICAL CONVERSATIONAL CONSTRAINT:
The user explicitly states that they DO NOT want to die, are NOT suicidal, or WANT TO LIVE.
Under NO circumstances should you ask why they want to die, ask why they feel suicidal, bring up self-harm, or treat them as in active suicidal crisis.
Acknowledge their affirmation of life or desire to keep going with warmth, encouragement, and support.
"""
            user_prompt += """
NOTE: The user is affirming that they want to live, do not want to die, or are not suicidal. Do NOT ask them about wanting to die or harm themselves. Respond supportively to their choice to live.
"""

        # ---------------------------------------------------------
        # CALL GROQ
        # ---------------------------------------------------------
        models_to_try = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        for m_name in models_to_try:
            try:
                logger.info(
                    "Generating Groq response with %s for: %s",
                    m_name,
                    message[:100],
                )

                result = self.client.chat.completions.create(
                    model=m_name,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    temperature=0.55,
                    max_tokens=600,
                )

                response = ""

                if result and result.choices:
                    response = result.choices[0].message.content.strip()

                if response:
                    # Clean smart quotes and unicode dashes
                    response = (
                        response.replace("\u2019", "'")
                        .replace("\u2018", "'")
                        .replace("\u201c", '"')
                        .replace("\u201d", '"')
                        .replace("\u2014", " - ")
                        .replace("\u2013", "-")
                        .replace("\u2011", "-")
                        .replace("\u2026", "...")
                    )
                    logger.info("Groq response generated successfully with %s", m_name)
                    return response

                logger.warning("Groq %s returned an empty response, trying next model", m_name)

            except Exception as exc:
                logger.warning(
                    "GROQ RESPONSE ERROR with %s: %s",
                    m_name,
                    exc,
                )

        # ---------------------------------------------------------
        # FINAL FALLBACK
        # ---------------------------------------------------------
        return self._safe_fallback(
            message,
            emotion=emotion,
            intent=intent,
            risk_level=risk_level,
        )
