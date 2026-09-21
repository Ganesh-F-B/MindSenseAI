"""
DeBERTa-v3 based mental-state predictor for MindSense AI.

DISCLAIMER:
MindSense AI mental-state classification is an AI prototype signal designed
exclusively for empathetic conversational support and early risk mitigation.
It is NOT a medical diagnosis, psychological evaluation, or clinical tool.
"""

import re
from typing import Optional

from chatbot.emotion.predictor import EmotionPredictor

_predictor = None

# Facial-emotion -> mental-state mapping, aligned with the taxonomy used by
# the text pipeline. "angry" maps to Stress (not "Anger") so both modalities
# produce the same label set.
_FACIAL_TO_STATE = {
    "happy": ("Normal", "LOW"),
    "neutral": ("Normal", "LOW"),
    "surprise": ("Normal", "LOW"),
    "disgust": ("Normal", "LOW"),
    "sad": ("Depression", "MEDIUM"),
    "angry": ("Stress", "MEDIUM"),
    "fear": ("Anxiety", "MEDIUM"),
    "ambiguous": ("Normal", "LOW"),
}


def _get_predictor():
    global _predictor

    if _predictor is None:
        _predictor = EmotionPredictor()

    return _predictor


def _is_crisis(text: str) -> bool:
    """Detect explicit crisis language before using the emotion model.
    Explicitly accounts for negation so statements like 'I don't want to die'
    are not falsely flagged as crisis."""
    clean = re.sub(r"['’`]", "", (text or "").lower())
    clean = re.sub(r"[^\w\s]", " ", clean).strip()
    clean = re.sub(r"\s+", " ", clean)

    if not clean:
        return False

    # 1. Passive ideation: explicit negation of the desire to live/exist is crisis
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
    if any(re.search(p, clean) for p in passive_crisis_patterns):
        return True

    # 2. Negated crisis & direct life affirmations
    negated_crisis = [
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
    if any(re.search(p, clean) for p in negated_crisis):
        return False

    # 3. Active Suicidal Ideation & Intent
    crisis_patterns = [
        r"\b(?:i\s+)?(?:want to|wanna|wish to|feel like|planning to|thinking of|intend to|going to|gonna)\s+(?:to\s+)?(?:die|dying|kill myself|end my life|take my own life|end it all)\b",
        r"\b(?:kill(?:ing)?\s+myself|end(?:ing)?\s+my\s+life|take\s+my\s+(?:own\s+)?life)\b",
        r"\b(?:suicid(?:e|al|ing)|commit\s+suicide)\b",
        r"\b(?:hang\s+myself|overdose|slit\s+(?:my\s+)?wrists?|slitting\s+(?:my\s+)?wrists?|jump\s+off\s+(?:a\s+)?(?:bridge|building|roof))\b",
        r"\b(?:hurt|hurting|harm|harming|cut|cutting|burn|burning)\s+myself\b",
        r"\bself[\s-]harm(?:ing)?\b",
    ]
    return any(re.search(p, clean) for p in crisis_patterns)


def _is_positive_context(text: str) -> bool:
    """
    Detect clearly positive statements.

    This prevents the six-class emotion model from turning an obviously
    positive sentence into Depression/Stress simply because the model
    does not have a neutral class.
    """

    positive_phrases = [
        "i am happy",
        "i'm happy",
        "i feel happy",
        "feeling happy",
        "i am excited",
        "i'm excited",
        "i feel excited",
        "i got a new job",
        "new job today",
        "got promoted",
        "promotion",
        "best day",
        "great day",
        "wonderful day",
        "amazing day",
        "good day",
        "having a good day",
        "things are going well",
        "everything is going well",
        "i achieved",
        "i finally achieved",
        "i accomplished",
        "i succeeded",
        "i won",
        "i am proud",
        "i'm proud",
        "love my family",
        "love my friends",
        "had lunch with my friends",
        "went out with my friends",
        "spent time with my friends",
        # Common positive / neutral statements that the six-class emotion
        # model would otherwise misclassify (e.g. as anger -> Stress).
        "i am fine",
        "i'm fine",
        "im fine",
        "i feel fine",
        "i am good",
        "i'm good",
        "im good",
        "i feel good",
        "i am doing well",
        "i am doing good",
        "i am doing fine",
        "i am doing great",
        "i am okay",
        "i'm okay",
        "i feel okay",
        "i am alright",
        "i'm alright",
        "i feel alright",
        "i am well",
        "i feel well",
        "i feel great",
        "i am great",
        "i'm great",
        "i am feeling good",
        "i am feeling fine",
        "i am feeling great",
        "i am feeling well",
        "i am feeling okay",
        "i am feeling alright",
        "i am feeling happy",
        "i am feeling good today",
        "i am fine what about you",
        "i am good what about you",
        "i am fine how are you",
        "i am good how are you",
        "i am doing well what about you",
        "i am doing good what about you",
        # Life affirmations & crisis negations
        "i want to live",
        "want to live",
        "choose to live",
        "glad to be alive",
        "happy to be alive",
        "grateful to be alive",
        "i love my life",
        "love my life",
        "i dont want to die",
        "i do not want to die",
        "i am not suicidal",
        "im not suicidal",
    ]

    # Generalized regex for adverb + positive adjectives / achievements / day quality
    gen_positive_patterns = [
        r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:so|very|really|pretty|truly|extremely|genuinely|quite|super|absolutely)?\s*(?:happy|joyful|cheerful|excited|thrilled|delighted|overjoyed|ecstatic|optimistic|energized|content|peaceful|proud|grateful|blessed|good|great|awesome|wonderful|fantastic|terrific)\b",
        r"\b(?:feeling|feel)\s+(?:so|very|really|pretty|truly|super)?\s*(?:happy|excited|energized|optimistic|good|great|awesome|wonderful|proud|delighted|cheerful)\b",
        r"\b(?:today|life|everything|things)\s+(?:has\s+been|is|are)\s+(?:so\s+|really\s+|absolutely\s+)?(?:amazing|wonderful|great|fantastic|awesome|going\s+great|going\s+well|beautiful)\b",
        r"\bhaving\s+(?:a\s+)?(?:great|wonderful|fantastic|amazing|really\s+good|lovely)\s+(?:day|time|week)\b",
        r"\b(?:i\s+)?(?:passed|cleared|aced)\s+(?:my\s+)?(?:exam|test|interview|finals|course)\b",
        r"\b(?:got\s+promoted|got\s+(?:a\s+|the\s+)?(?:promotion|new\s+job|job|offer|raise)|accepted\s+into)\b",
        r"\b(?:i\s+)?(?:finally\s+)?(?:achieved|succeeded|won)\s+(?:my|the|it)\b",
        r"\bcelebrat(?:ing|ion)\b",
    ]
    if any(re.search(p, text) for p in gen_positive_patterns):
        return True

    return any(phrase in text for phrase in positive_phrases)


def _is_anxiety_context(text: str) -> bool:
    anxiety_phrases = [
        "i am anxious",
        "i'm anxious",
        "i feel anxious",
        "feeling anxious",
        "i am scared",
        "i'm scared",
        "i feel scared",
        "feeling scared",
        "i am afraid",
        "i'm afraid",
        "i feel afraid",
        "i keep worrying",
        "i am worried",
        "i'm worried",
        "i feel worried",
        "what might happen",
        "worried about tomorrow",
        "scared about tomorrow",
        "nervous about",
    ]

    return any(phrase in text for phrase in anxiety_phrases)


def _is_depression_context(text: str) -> bool:
    depression_phrases = [
        "i feel sad",
        "i am sad",
        "i'm sad",
        "feeling sad",
        "i feel empty",
        "i am empty",
        "i'm empty",
        "feel worthless",
        "i am worthless",
        "i'm worthless",
        "feel hopeless",
        "i am hopeless",
        "i'm hopeless",
        "feel alone",
        "i am lonely",
        "i'm lonely",
        "nothing matters",
        "everything has been going wrong",
        "i feel broken",
        "i feel helpless",
        "i don't feel like talking to anyone",
        "i dont feel like talking to anyone",
        "i don't want to talk to anyone",
        "i dont want to talk to anyone",
        "don't feel like talking",
        "feeling disconnected",
        "feel disconnected from everyone",
        "nothing seems enjoyable anymore",
        "nothing is enjoyable anymore",
        "nothing feels enjoyable",
        "nothing makes me happy anymore",
    ]

    return any(phrase in text for phrase in depression_phrases)


def _is_stress_context(text: str) -> bool:
    stress_phrases = [
        "i am stressed",
        "i'm stressed",
        "i feel stressed",
        "feeling stressed",
        "so much work",
        "lot of work",
        "lots of work",
        "too much work",
        "too many tasks",
        "work pressure",
        "under pressure",
        "deadline",
        "deadlines",
        "exam tomorrow",
        "haven't studied",
        "have not studied",
        "overwhelmed",
        "too much to do",
        "don't know where to start",
        "dont know where to start",
        "assignments due",
        "three assignments",
        "multiple assignments",
        "assignment deadline",
        "assignments this week",
        "exhausted from work",
        "exhausted from studying",
        "exhausted because of work",
    ]

    return any(phrase in text for phrase in stress_phrases)


def _is_physical_health_context(text: str) -> bool:
    physical_terms = [
        "headache",
        "head hurts",
        "head pain",
        "migraine",
        "stomach pain",
        "stomach ache",
        "fever",
        "cough",
        "cold",
        "sore throat",
        "toothache",
        "back pain",
        "body pain",
        "paracetamol",
        "acetaminophen",
        "ibuprofen",
    ]

    return any(term in text for term in physical_terms)


def _is_tired_context(text: str) -> bool:
    """
    Detect tiredness / fatigue / low energy.

    Tiredness alone is NOT depression. The six-class emotion model tends to
    classify "i feel tired" as sadness (-> Depression), which is misleading.
    """
    tired_phrases = [
        "i feel tired",
        "i am tired",
        "i'm tired",
        "im tired",
        "feeling tired",
        "i feel exhausted",
        "i am exhausted",
        "i'm exhausted",
        "im exhausted",
        "feeling exhausted",
        "i feel fatigued",
        "i am fatigued",
        "i'm fatigued",
        "fatigued",
        "i feel sleepy",
        "i am sleepy",
        "i'm sleepy",
        "feeling sleepy",
        "i feel drowsy",
        "i am drowsy",
        "i'm drowsy",
        "drowsy",
        "worn out",
        "i feel worn out",
        "i am worn out",
        "i feel drained",
        "i am drained",
        "i'm drained",
        "feeling drained",
        "i have no energy",
        "i am low on energy",
        "i feel low on energy",
        "i feel weak",
        "i am weak",
        "i'm weak",
        "feeling weak",
        "i feel tired all the time",
        "i am tired all the time",
        "always tired",
        "i am always tired",
        "i feel tired today",
        "i am tired today",
    ]

    return any(phrase in text for phrase in tired_phrases)


def _is_negated_distress(text: str) -> bool:
    """
    Detect explicit negation of negative emotional states.
    e.g. 'I am not sad', 'I don't feel stressed', 'not anxious', 'nothing is wrong'.
    These must be classified as Normal/LOW risk rather than matching the negative word.
    """
    clean = re.sub(r"['’`]", "", (text or "").lower())
    clean = re.sub(r"[^\w\s]", " ", clean).strip()
    clean = re.sub(r"\s+", " ", clean)

    negated_patterns = [
        # 1. Subject/verb + negation + distress adjective/noun/state
        r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:definitely|certainly|really|honestly|actually|necessarily)?\s*(?:not|never|by\s+no\s+means)\s+(?:feeling\s+|feel\s+|being\s+)?\s*(?:too\s+|very\s+|particularly\s+|especially\s+|overly\s+|remotely\s+|in\s+any\s+way\s+|at\s+all\s+|any\s+)?(?:sad|unhappy|depressed|miserable|down|hopeless|gloomy|blue|stressed|overwhelmed|under\s+pressure|pressured|strained|burned\s+out|burnt\s+out|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fearful|fear|apprehensive|apprehension|angry|mad|furious|irritated|annoyed|pissed|enraged|frustrated|upset|distressed|troubled|bothered|bad|terrible|horrible|awful)\b",
        # 2. Auxiliary negation: don't/didn't/wouldn't/haven't/can't feel/say/seem ...
        r"\b(?:dont|do\s+not|didnt|did\s+not|havent|have\s+not|hadnt|had\s+not|wouldnt|would\s+not|cant|cannot|aint)\s+(?:really\s+|definitely\s+|actually\s+|necessarily\s+|even\s+)?(?:been\s+)?(?:feel|feeling|seem|say\s+(?:that\s+)?(?:im|i\s+am|i\s+feel)?)\s*(?:like\s+im\s+)?(?:particularly\s+|especially\s+|overly\s+|too\s+|very\s+|any\s+|remotely\s+|all\s+that\s+)?(?:sad|unhappy|depressed|miserable|down|hopeless|gloomy|stressed|overwhelmed|under\s+pressure|pressured|strained|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fear|apprehensive|angry|mad|furious|irritated|annoyed|pissed|frustrated|upset|distressed|troubled|bad)\b",
        # 3. Direct predicate negation: not sad, not feeling down, etc.
        r"\bnot\s+(?:feeling\s+|feel\s+|being\s+)?\s*(?:really\s+|overly\s+|too\s+|very\s+|particularly\s+|especially\s+|any\s+)?(?:sad|unhappy|depressed|miserable|down|hopeless|stressed|overwhelmed|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fear|apprehensive|angry|mad|furious|irritated|annoyed|frustrated|upset|distressed|bad|terrible|horrible|awful)\b",
        # 4. Existence/possession negation: no stress, no pressure on me, etc.
        r"\b(?:there\s+is\s+|theres\s+|i\s+have\s+|have\s+|feel\s+)?(?:really\s+|truly\s+|absolutely\s+)?no\s+(?:stress|pressure|anxiety|worries|worry|fear|panic|dread|terror|apprehension|anger|resentment|depression|trouble|issues?|problems?)\b",
        r"\b(?:no\s+pressure\s+on\s+me|without\s+any\s+stress|free\s+of\s+stress|free\s+from\s+anxiety)\b",
        # 5. Idiomatic expressions: nothing is wrong, not bad, etc.
        r"\bnothing\s+(?:is\s+|feels\s+)?(?:wrong|bad|terrible|bothering\s+me)\b",
        r"\bnot\s+bad\b",
        r"\bnot\s+terrible\b",
        # 6. Crisis negations / harm denials (indicating normal/non-crisis state)
        r"\b(?:dont|do\s+not|never|wont|cant|cannot)\s+(?:really\s+)?(?:feel\s+like|want\s+to|wanna)\s+(?:hurting|harming|dying|die|killing)\s*(?:myself)?\b",
        r"\b(?:not|never)\s+(?:hurting|harming|killing)\s+myself\b",
        r"\b(?:not|never)\s+suicidal\b",
    ]
    return any(re.search(p, clean) for p in negated_patterns)


def _is_temporal_coping_context(text: str) -> bool:
    """
    Detect temporal shifts where historical distress is resolved into a current
    positive, coping, or relieved state.
    e.g. "I used to feel overwhelmed, but currently I have things under control",
         "Yesterday I was stressed, but today I am excited".
    """
    clean = re.sub(r"['’`]", "", (text or "").lower())
    clean = re.sub(r"[^\w\s]", " ", clean).strip()
    clean = re.sub(r"\s+", " ", clean)

    contrast = re.search(
        r"\b(?:yesterday|past|earlier|previously|used\s+to|last\s+(?:week|month|year|night)|was\s+feeling|was\s+depressed|was\s+scared|was\s+stressed).+?"
        r"\b(?:but\s+today|but\s+now|now|today|currently|this\s+(?:week|month|year)|afterward|afterwards|at\s+present)\s*"
        r"(?:i\s+(?:feel|am|have|felt)\s+)?(.+)",
        clean
    )
    if contrast:
        current_state = contrast.group(1)
        positive_or_coping = [
            "happy", "excited", "good", "great", "fine", "better", "much better", "awesome",
            "relieved", "peaceful", "calm", "relaxed", "confident", "under control",
            "in control", "things under control", "handling it", "doing well", "okay", "alright", "coping"
        ]
        if any(w in current_state for w in positive_or_coping):
            return True
    return False


def _is_general_casual_context(text: str) -> bool:
    """
    Detect casual pleasantries, greetings, gratitude, and routine daily activities
    that should be safely classified as Normal/LOW instead of being forced into
    Stress or Depression by a 6-class model that lacks a neutral label.
    """
    clean = re.sub(r"[^\w\s]", " ", (text or "").lower()).strip()
    clean = re.sub(r"\s+", " ", clean)

    greetings = {
        "hi", "hello", "hey", "hii", "hiii", "good morning", "good afternoon",
        "good evening", "howdy", "sup", "greetings", "yo"
    }
    if clean in greetings:
        return True

    gratitude = {
        "thank you", "thanks", "thanks a lot", "thank u", "many thanks", "thx", "appreciate it"
    }
    if clean in gratitude:
        return True

    casual_phrases = [
        "who are you", "what are you", "what is mindsense", "tell me about yourself",
        "what can you do", "help me", "how can you help", "tell me a joke",
        "how are you", "how r u", "how are u",
        "finished my assignment", "finished my homework", "having a normal day",
        "eating lunch", "eating dinner", "watching a movie", "watching movie",
        "listening to music", "going for a walk", "just chilling", "just relaxing",
        "made a cup of coffee", "making coffee", "cup of coffee", "making tea",
        "had coffee", "just had coffee", "having coffee", "drank coffee",
        "going to college", "going to school", "going to class", "going to work",
        "submitted all the documents", "submitted documents", "visa application", "flight departs",
        "the weather is", "nice outside today", "weather outside", "capital of france",
        "tell me something interesting"
    ]
    if any(p in clean for p in casual_phrases):
        return True

    # Factual / out-of-domain queries
    if re.search(r"^(?:what\s+is|whats|what\s+are|where\s+is|when\s+did|who\s+is|why\s+is|how\s+does|how\s+do|can\s+you\s+explain|define|tell\s+me\s+about)\s+(?!depression|anxiety|stress|trauma|ptsd|mental|suicid|grief|lonel|panic|disorder|therapy|counsel)", clean):
        return True

    if _is_temporal_coping_context(text):
        return True

    return False


def predict_mental_state(
    text: str,
    facial_emotion: Optional[str] = None,
    facial_confidence: Optional[float] = None,
    validated_emotion: Optional[str] = None,
    validated_intent: Optional[str] = None,
    secondary_emotions: Optional[list] = None,
    is_mixed: Optional[bool] = None,
    pattern: Optional[str] = None,
) -> dict:
    """
    Predict MindSense mental state signal.

    IMPORTANT NOTE:
    This is an automated conversational support signal, NOT a clinical diagnosis.

    When *facial_emotion* is provided the DeBERTa text signal and the DeepFace
    facial signal are fused into ONE mental state / risk output.

    Fusion priority:
        1. Explicit crisis (text)            -> Suicidal / HIGH (respects negation)
        2. Negated negative distress         -> Normal / LOW
        3. Temporal coping contrast          -> Normal / LOW
        4. Clearly positive context          -> Normal / LOW
        5. Casual / General conversation     -> Normal / LOW
        6. Explicit anxiety                  -> Anxiety / MEDIUM
        7. Explicit depression               -> Depression / MEDIUM
        8. Explicit stress                   -> Stress / MEDIUM
        9. Physical health / tiredness       -> Normal / LOW
        10. DeBERTa-v3 emotion signal (fused with facial emotion if present)
        11. Safe Normal fallback
    """

    text = (text or "").strip()

    sec_emotions = secondary_emotions or []
    is_mixed_flag = bool(is_mixed) if is_mixed is not None else False
    pattern_label = pattern or "concentrated"

    if not text:
        return {
            "mental_state": "Normal",
            "confidence": 0.0,
            "risk_level": "LOW",
            "secondary_emotions": [],
            "is_mixed": False,
            "pattern": "concentrated",
        }

    lower = text.lower()

    # ---------------------------------------------------------
    # 1. CRISIS HAS HIGHEST PRIORITY (respects negation)
    # ---------------------------------------------------------
    if _is_crisis(lower):
        return {
            "mental_state": "Suicidal",
            "confidence": 100.0,
            "risk_level": "HIGH",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # SYNCHRONIZE WITH UPSTREAM CHATENGINE IF NOT PROVIDED
    # ---------------------------------------------------------
    if validated_emotion is None or validated_intent is None or not sec_emotions:
        try:
            from chatbot.conversation.chat_engine import ChatEngine
            engine = ChatEngine()
            analysis = engine.analyze(text)
            if validated_emotion is None:
                validated_emotion = analysis.get("emotion")
            if validated_intent is None:
                validated_intent = analysis.get("intent")
            if not sec_emotions:
                sec_emotions = analysis.get("secondary_emotions", [])
            if is_mixed is None:
                is_mixed_flag = analysis.get("is_mixed", False)
            if pattern is None:
                pattern_label = analysis.get("pattern", "concentrated")
        except Exception:
            pass

    # ---------------------------------------------------------
    # 2. NEGATED DISTRESS ("I am not sad", "I don't feel stressed")
    # ---------------------------------------------------------
    if _is_negated_distress(lower) or (validated_intent == "positive_state" and _is_negated_distress(lower)):
        return {
            "mental_state": "Normal",
            "confidence": 95.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 3. TEMPORAL RESOLUTION / COPING TRANSITIONS
    # ---------------------------------------------------------
    if _is_temporal_coping_context(lower) or (validated_intent == "positive_state" and "used to" in lower):
        return {
            "mental_state": "Normal",
            "confidence": 98.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 4. CLEARLY POSITIVE / NORMAL
    # ---------------------------------------------------------
    if _is_positive_context(lower) or validated_intent == "positive_state" or validated_emotion in {"joy", "love"}:
        return {
            "mental_state": "Normal",
            "confidence": 98.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 5. CASUAL / GENERAL CONVERSATION / FACTUAL / ROUTINE
    # ---------------------------------------------------------
    if _is_general_casual_context(lower) or (validated_intent in {"general", "greeting", "gratitude", "how_are_you"} and validated_emotion == "neutral"):
        return {
            "mental_state": "Normal",
            "confidence": 92.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 6. CLEAR ANXIETY / DEPRESSION / STRESS
    # ---------------------------------------------------------
    has_anger_cues = any(w in lower for w in ["angry", "mad", "furious", "hate", "pissed", "annoy", "irritat", "rage", "damn", "frustrat", "infuriat", "outrage", "blood boil"])
    has_sad_cues = any(w in lower for w in ["sad", "unhapp", "depress", "cry", "wept", "tear", "down", "lonely", "alone", "hopeless", "hurt", "grief", "pain", "mourn", "weep", "sobbing", "heartbroken"])
    has_fear_cues = any(w in lower for w in ["scared", "fear", "anxious", "worry", "worried", "panic", "afraid", "nervous", "terrified", "dread", "apprehens", "frightened", "alarmed", "uneasy"])

    if _is_anxiety_context(lower) or validated_intent == "anxiety" or (validated_emotion == "fear" and has_fear_cues):
        return {
            "mental_state": "Anxiety",
            "confidence": 98.0,
            "risk_level": "MEDIUM",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    if _is_depression_context(lower) or validated_intent == "depression" or (validated_emotion == "sadness" and has_sad_cues):
        return {
            "mental_state": "Depression",
            "confidence": 98.0,
            "risk_level": "MEDIUM",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    if _is_stress_context(lower) or validated_intent == "stress" or (validated_emotion == "anger" and has_anger_cues):
        return {
            "mental_state": "Stress",
            "confidence": 98.0,
            "risk_level": "MEDIUM",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 7. PHYSICAL HEALTH & FATIGUE
    # ---------------------------------------------------------
    if _is_physical_health_context(lower):
        return {
            "mental_state": "Normal",
            "confidence": 90.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    if _is_tired_context(lower):
        return {
            "mental_state": "Normal",
            "confidence": 85.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    if lower in {"no", "nope", "nah", "not really", "okay", "ok"}:
        return {
            "mental_state": "Normal",
            "confidence": 70.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 8. VALIDATED UPSTREAM NEUTRAL / POSITIVE GATING
    # ---------------------------------------------------------
    if validated_emotion == "neutral" and not (has_anger_cues or has_sad_cues or has_fear_cues):
        return {
            "mental_state": "Normal",
            "confidence": 90.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    if validated_emotion in {"joy", "love", "surprise"}:
        return {
            "mental_state": "Normal",
            "confidence": 95.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 9. DEBERTa-v3 emotion signal (fallback)
    # ---------------------------------------------------------
    try:
        result = _get_predictor().predict(text)

        emotion = str(result.get("emotion", "neutral")).lower()
        confidence = float(result.get("confidence", 0.0))
        if not sec_emotions:
            sec_emotions = result.get("secondary", [])
        if is_mixed is None:
            is_mixed_flag = result.get("is_mixed", False)
        if pattern is None:
            pattern_label = result.get("pattern", "concentrated")

    except Exception as exc:
        print(f"[DeBERTa] Prediction error: {exc}")

        return {
            "mental_state": "Normal",
            "confidence": 0.0,
            "risk_level": "LOW",
            "secondary_emotions": sec_emotions,
            "is_mixed": is_mixed_flag,
            "pattern": pattern_label,
        }

    # ---------------------------------------------------------
    # 10. Convert DeBERTa emotion to supporting mental state
    # ---------------------------------------------------------
    # The 6-class emotion model lacks 'neutral', so it frequently predicts
    # anger or sadness for neutral/ordinary statements.
    # Require explicit cues before mapping to a distress mental state.
    if emotion == "fear" and has_fear_cues:
        mental_state = "Anxiety"
        risk_level = "MEDIUM"

    elif emotion == "sadness" and has_sad_cues:
        mental_state = "Depression"
        risk_level = "MEDIUM"

    elif emotion == "anger" and has_anger_cues:
        mental_state = "Stress"
        risk_level = "MEDIUM"

    else:
        mental_state = "Normal"
        risk_level = "LOW"

    # ---------------------------------------------------------
    # 11. FUSE the facial emotion into the SAME output when present.
    # ---------------------------------------------------------
    if facial_emotion:
        face_key = (facial_emotion or "").lower()
        face_state = _FACIAL_TO_STATE.get(face_key)

        if face_state is not None:
            face_label, face_risk = face_state
            face_conf = float(facial_confidence or 0.0)

            # Low-confidence (< 35%) or ambiguous facial signals must never produce clinical distress states
            if (0.0 < face_conf < 35.0) or (face_key in {"ambiguous", "neutral"}):
                face_label = "Normal"
                face_risk = "LOW"

            if face_label == "Normal":
                mental_state = "Normal"
                risk_level = "LOW"
                confidence = max(confidence, face_conf)
            else:
                mental_state = face_label
                risk_level = face_risk
                confidence = max(confidence, face_conf)

    return {
        "mental_state": mental_state,
        "confidence": round(confidence, 2),
        "risk_level": risk_level,
        "secondary_emotions": sec_emotions,
        "is_mixed": is_mixed_flag,
        "pattern": pattern_label,
    }
