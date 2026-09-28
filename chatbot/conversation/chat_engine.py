import logging
import re

from chatbot.intent.predictor import IntentPredictor
from chatbot.emotion.predictor import EmotionPredictor
from chatbot.conversation.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


class ChatEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self.intent_predictor = None
        self.emotion_predictor = None
        self.response_generator = ResponseGenerator()
        self.history = []

    def _get_predictors(self):
        if self.intent_predictor is None:
            self.intent_predictor = IntentPredictor()

        if self.emotion_predictor is None:
            self.emotion_predictor = EmotionPredictor()

        return self.intent_predictor, self.emotion_predictor

    # ---------------------------------------------------------
    # HIGH-CONFIDENCE TEXT OVERRIDES
    # ---------------------------------------------------------
    # HIGH-CONFIDENCE TEXT OVERRIDES & DETERMINISTIC ROUTING
    # Used for obvious phrases where the ML model should not
    # override the literal meaning of the user's message.
    # ---------------------------------------------------------
    def _rule_based_analysis(self, message: str):
        msg_raw = str(message or "").lower().strip()
        # Normalize apostrophes first so "don't" becomes "dont", avoiding token splitting
        msg_clean = re.sub(r"['’`]", "", msg_raw)
        msg_clean = re.sub(r"[^\w\s]", " ", msg_clean)
        msg_clean = re.sub(r"\s+", " ", msg_clean).strip()

        if not msg_clean:
            return None

        # ---------------- PASSIVE SUICIDAL IDEATION & LACK OF DESIRE TO EXIST ----------------
        # Explicit negation of the desire to live/exist is passive crisis, NOT life affirmation.
        passive_crisis_patterns = [
            r"\b(?:dont|do not|didnt|did not|never|cant|cannot|no longer)\s+(?:really\s+)?(?:want|wanna)\s+to\s+(?:live|keep living|stay alive|be alive|exist|wake up)\b",
            r"\bno\s+(?:reason|point|purpose)\s+(?:for\s+me\s+)?(?:to\s+)?(?:live|living|keep\s+living|stay\s+alive|be\s+alive|go\s+on)\b",
            r"\b(?:tired|exhausted|done|sick)\s+of\s+(?:living|life|existing)\b",
            r"\b(?:better\s+off\s+(?:without\s+me|dead)|better\s+without\s+me|world\s+(?:would\s+be\s+)?better\s+without\s+me)\b",
            r"\b(?:wish|wishing)\s+(?:i\s+)?(?:could\s+disappear|disappear\s+forever|was\s+never\s+born|were\s+never\s+born|was\s+dead|were\s+dead)\b",
            r"\b(?:wish|wished)\s+i\s+(?:never\s+woke\s+up|wouldn'?t\s+wake\s+up|didnt\s+wake\s+up)\b",
            r"\b(?:no\s+one|nobody)\s+(?:would\s+)?(?:care|miss\s+me|notice)\s+(?:if\s+i\s+(?:died|was\s+gone|disappeared|wasnt\s+here))\b",
            r"\b(?:cannot|cant)\s+go\s+on\s+living\b",
        ]
        if any(re.search(p, msg_clean) for p in passive_crisis_patterns):
            return {
                "intent": "suicidal_thought",
                "emotion": "sadness",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "HIGH",
            }

        # ---------------- NEGATED CRISIS & LIFE AFFIRMATION ----------------
        # Explicit denials of suicide/harm and assertions of wanting to live must NEVER trigger crisis
        negated_crisis = [
            # Grammatical negation: [negator] + [verb] + [harm/death]
            r"\b(?:dont|do not|didnt|did not|never|wont|will not|cant|cannot|aint|no longer|not|no)\s+(?:really\s+)?(?:want|wanna|feel like|plan|planning|intend|intending|wish|wishing|trying)\s+(?:to\s+)?(?:die|kill myself|end my life|end it all|hurt myself|harm myself|be dead|cease to exist|give up on life)\b",
            r"\b(?:dont|do not|never|cant|cannot|wont)\s+(?:feel like|wanna|want to)\s+(?:dying|die|ending it)\b",
            r"\bi\s+(?:dont|do not|never|wont)\s+want\s+to\s+die\b",
            r"\bi\s+(?:dont|do not|never)\s+feel\s+like\s+hurting\s+myself\b",
            r"\bno\s+(?:desire|plan|intention|urge)\s+to\s+(?:die|kill myself|end my life|hurt myself)\b",
            r"\b(?:not|never|no longer)\s+(?:feeling\s+)?suicidal\b",
            r"\bnot\s+(?:going to|gonna)\s+(?:kill myself|die|hurt myself|end my life)\b",
            # Direct life affirmations
            r"\b(?:i\s+)?(?:want|wanna|choose|choosing|decided|planning|intend)\s+to\s+(?:live|keep living|stay alive|be alive)\b",
            r"\b(?:glad|happy|grateful|proud)\s+to\s+be\s+alive\b",
            r"\bi\s+love\s+(?:my\s+)?life\b",
            r"\bwant\s+to\s+live\b",
        ]
        if any(re.search(p, msg_clean) for p in negated_crisis):
            return {
                "intent": "general",
                "emotion": "neutral",
                "intent_confidence": 0.98,
                "emotion_confidence": 0.95,
                "risk_level": "LOW",
                "is_negated_crisis": True,
            }

        # ---------------- ACTIVE CRISIS & EXPLICIT SELF-HARM ----------------
        crisis_patterns = [
            # 1. Active Suicidal Ideation & Intent
            r"\b(?:i\s+)?(?:want to|wanna|wish to|feel like|planning to|thinking of|intend to|going to|gonna)\s+(?:to\s+)?(?:die|dying|kill myself|end my life|take my own life|end it all)\b",
            r"\b(?:kill(?:ing)?\s+myself|end(?:ing)?\s+my\s+life|take\s+my\s+(?:own\s+)?life)\b",
            r"\b(?:suicid(?:e|al|ing)|commit\s+suicide)\b",
            r"\b(?:hang\s+myself|overdose|slit\s+(?:my\s+)?wrists?|slitting\s+(?:my\s+)?wrists?|jump\s+off\s+(?:a\s+)?(?:bridge|building|roof))\b",
            # 2. Explicit Self-Harm
            r"\b(?:hurt|hurting|harm|harming|cut|cutting|burn|burning)\s+myself\b",
            r"\bself[\s-]harm(?:ing)?\b",
        ]
        if any(re.search(p, msg_clean) for p in crisis_patterns):
            return {
                "intent": "suicidal_thought",
                "emotion": "sadness",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "HIGH",
            }

        # ---------------- NEGATION OF DISTRESS / NEGATIVE EMOTIONS ----------------
        # Negated distress (e.g. "I am not sad", "I don't feel stressed", "I wouldn't say I'm panicked", "There is no pressure on me")
        # Per specification: Negated distress routes to intent: general, emotion: neutral, risk: LOW
        # UNLESS explicit positive emotion is also present (e.g. "I am not sad, I'm actually really happy").
        has_explicit_positive = bool(re.search(
            r"\b(?:happy|joyful|excited|thrilled|cheerful|delighted|glad|proud|grateful|energized|optimistic|ecstatic|wonderful|great|amazing|fantastic)\b",
            msg_clean
        ))

        negated_distress_patterns = [
            # 1. Subject/verb + negation + distress adjective/noun/state
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:definitely|certainly|really|honestly|actually|necessarily)?\s*(?:not|never|by\s+no\s+means)\s+(?:feeling\s+|feel\s+|being\s+)?\s*(?:too\s+|very\s+|particularly\s+|especially\s+|overly\s+|remotely\s+|in\s+any\s+way\s+|at\s+all\s+|any\s+)?(?:sad|unhappy|depressed|miserable|down|low|hopeless|gloomy|blue|stressed|overwhelmed|under\s+pressure|pressured|strained|burned\s+out|burnt\s+out|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fearful|fear|apprehensive|apprehension|angry|mad|furious|irritated|annoyed|pissed|enraged|frustrated|upset|distressed|troubled|bothered|bad|terrible|horrible|awful)\b",
            # 2. Auxiliary negation: don't/didn't/wouldn't/haven't/can't feel/say/seem ...
            r"\b(?:dont|do\s+not|didnt|did\s+not|havent|have\s+not|hadnt|had\s+not|wouldnt|would\s+not|cant|cannot|aint)\s+(?:really\s+|definitely\s+|actually\s+|necessarily\s+|even\s+)?(?:been\s+)?(?:feel|feeling|seem|say\s+(?:that\s+)?(?:im|i\s+am|i\s+feel)?)\s*(?:like\s+im\s+)?(?:particularly\s+|especially\s+|overly\s+|too\s+|very\s+|any\s+|remotely\s+|all\s+that\s+)?(?:sad|unhappy|depressed|miserable|down|low|hopeless|gloomy|stressed|overwhelmed|under\s+pressure|pressured|strained|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fear|apprehensive|angry|mad|furious|irritated|annoyed|pissed|frustrated|upset|distressed|troubled|bad)\b",
            # 3. Direct predicate negation: not sad, not feeling down, etc.
            r"\bnot\s+(?:feeling\s+|feel\s+|being\s+)?\s*(?:really\s+|overly\s+|too\s+|very\s+|particularly\s+|especially\s+|any\s+)?(?:sad|unhappy|depressed|miserable|down|low|hopeless|stressed|overwhelmed|anxious|nervous|worried|scared|afraid|panicked|panic|dread|terrified|terror|fear|apprehensive|angry|mad|furious|irritated|annoyed|frustrated|upset|distressed|bad|terrible|horrible|awful)\b",
            # 4. Existence/possession negation: no stress, no pressure on me, etc.
            r"\b(?:there\s+is\s+|theres\s+|i\s+have\s+|have\s+|feel\s+)?(?:really\s+|truly\s+|absolutely\s+)?no\s+(?:stress|pressure|anxiety|worries|worry|fear|panic|dread|terror|apprehension|anger|resentment|depression|trouble|issues?|problems?)\b",
            r"\b(?:no\s+pressure\s+on\s+me|without\s+any\s+stress|free\s+of\s+stress|free\s+from\s+anxiety)\b",
            # 5. Idiomatic expressions: nothing is wrong, not bad, etc.
            r"\bnothing\s+(?:is\s+|feels\s+)?(?:wrong|bad|terrible|bothering\s+me)\b",
            r"\bnot\s+bad\b",
            r"\bnot\s+terrible\b",
        ]
        if any(re.search(p, msg_clean) for p in negated_distress_patterns):
            if has_explicit_positive:
                return {
                    "intent": "positive_state",
                    "emotion": "joy",
                    "intent_confidence": 0.98,
                    "emotion_confidence": 0.95,
                    "risk_level": "LOW",
                }
            return {
                "intent": "general",
                "emotion": "neutral",
                "intent_confidence": 0.95,
                "emotion_confidence": 0.95,
                "risk_level": "LOW",
            }

        # ---------------- TEMPORAL CONTRAST / COPING TRANSITION ----------------
        # Handles: "Yesterday I was stressed, but today I am excited",
        # "I used to feel overwhelmed, but currently I have things under control",
        # "Last week I was depressed. This week I feel much better",
        # "I was scared during the exam, but afterward I felt relieved and happy"
        contrast_match = re.search(
            r"\b(?:yesterday|past|earlier|previously|used\s+to|last\s+(?:week|month|year|night)|was\s+feeling|was\s+depressed|was\s+scared|was\s+stressed).+?"
            r"\b(?:but\s+today|but\s+now|now|today|currently|this\s+(?:week|month|year)|afterward|afterwards|at\s+present)\s*"
            r"(?:i\s+(?:feel|am|have|felt)\s+)?(.+)",
            msg_clean
        )
        if contrast_match:
            current_state = contrast_match.group(1)
            positive_or_coping = [
                "happy", "excited", "good", "great", "fine", "better", "much better", "awesome",
                "relieved", "peaceful", "calm", "relaxed", "confident", "under control",
                "in control", "things under control", "handling it", "doing well", "okay", "alright", "coping"
            ]
            if any(w in current_state for w in positive_or_coping):
                return {
                    "intent": "positive_state",
                    "emotion": "joy",
                    "intent_confidence": 0.98,
                    "emotion_confidence": 0.98,
                    "risk_level": "LOW",
                }

        # ---------------- GREETINGS & CASUAL ----------------
        greetings = {
            "hi", "hello", "hey", "hii", "hiii", "good morning", "good afternoon",
            "good evening", "howdy", "sup", "greetings", "yo"
        }
        if msg_clean in greetings:
            return {
                "intent": "greeting",
                "emotion": "neutral",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- GRATITUDE ----------------
        if msg_clean in {"thank you", "thanks", "thanks a lot", "thank u", "many thanks", "thx", "appreciate it"}:
            return {
                "intent": "gratitude",
                "emotion": "neutral",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- IDENTITY & CAPABILITIES ----------------
        if any(p in msg_clean for p in [
            "who are you", "what are you", "what is mindsense", "tell me about yourself",
            "what can you do", "help me", "how can you help", "tell me a joke"
        ]):
            return {
                "intent": "general",
                "emotion": "neutral",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- HOW ARE YOU ----------------
        if msg_clean in {"how are you", "how r u", "how are u", "how do you do"}:
            return {
                "intent": "how_are_you",
                "emotion": "neutral",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- POSITIVE / WELLBEING ----------------
        positive_patterns = [
            # 1. Adverb + positive emotions & states
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:\w+\s+)?(?:happy|joyful|cheerful|excited|thrilled|delighted|overjoyed|ecstatic|optimistic|energized|content|peaceful|proud|grateful|blessed|good|great|awesome|wonderful|fantastic|terrific)\b",
            r"\b(?:feeling|feel)\s+(?:\w+\s+)?(?:happy|excited|energized|optimistic|good|great|awesome|wonderful|proud|delighted|cheerful)\b",
            # 2. General day/life wellbeing
            r"\b(?:today|life|everything|things)\s+(?:has\s+been|is|are)\s+(?:so\s+|really\s+|absolutely\s+)?(?:amazing|wonderful|great|fantastic|awesome|going\s+great|going\s+well|beautiful)\b",
            r"\bhaving\s+(?:a\s+)?(?:great|wonderful|fantastic|amazing|really\s+good|lovely)\s+(?:day|time|week)\b",
            # 3. Achievements & milestones
            r"\b(?:i\s+)?(?:passed|cleared|aced)\s+(?:my\s+)?(?:exam|test|interview|finals|course)\b",
            r"\b(?:got\s+promoted|got\s+(?:a\s+|the\s+)?(?:promotion|new\s+job|job|offer|raise)|accepted\s+into)\b",
            r"\b(?:i\s+)?(?:finally\s+)?(?:achieved|succeeded|won)\s+(?:my|the|it)\b",
            r"\bcelebrat(?:ing|ion)\b",
            # 4. Standard wellbeing phrases
            r"\b(?:i\s+am|im|i\s+feel)\s+(?:fine|good|great|okay|alright|doing\s+well|doing\s+good|doing\s+great)\b",
            r"\bthings\s+are\s+going\s+well\b",
        ]
        if any(re.search(p, msg_clean) for p in positive_patterns):
            return {
                "intent": "positive_state",
                "emotion": "joy",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- LOVE / FAMILY ----------------
        if "i love my family" in msg_clean or "love my friends" in msg_clean:
            return {
                "intent": "family_positive",
                "emotion": "love",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        family_patterns = [
            r"\b(?:my\s+)?(?:parents?|mother|father|mom|dad|brother|sister|sibling)\s+(?:and\s+i|screamed|yelled|blamed|argued|fighting|criticiz|took\s+(?:his|her|their)\s+side|rules?)\b",
            r"\b(?:fight|argument|conflict)\s+with\s+(?:my\s+)?(?:parents?|mother|father|mom|dad|brother|sister|family)\b",
        ]
        if any(re.search(p, msg_clean) for p in family_patterns) or ("family" in msg_clean and any(w in msg_clean for w in ["mother", "father", "brother", "sister", "parents"])):
            return {
                "intent": "family",
                "emotion": "neutral",
                "intent_confidence": 0.95,
                "emotion_confidence": 0.90,
                "risk_level": "LOW",
            }

        # ---------------- RELATIONSHIP & DATING ----------------
        relationship_patterns = [
            r"\b(?:my\s+)?(?:partner|boyfriend|girlfriend|husband|wife|spouse|fiance|fiancee)\s+(?:and\s+i\s+)?(?:had\s+(?:a\s+)?(?:huge\s+|terrible\s+|big\s+|bad\s+)?(?:fight|argument)|fighting|arguing|broke\s+up|split\s+up|argued|cheated|having\s+problems)\b",
            r"\b(?:fight|argument|trouble)\s+with\s+(?:my\s+)?(?:partner|boyfriend|girlfriend|husband|wife|spouse)\b",
            r"\b(?:breakup|broke\s+up\s+with|divorce|broken\s+heart)\b",
        ]
        if any(re.search(p, msg_clean) for p in relationship_patterns):
            return {
                "intent": "relationship",
                "emotion": "sadness",
                "intent_confidence": 0.98,
                "emotion_confidence": 0.90,
                "risk_level": "LOW",
            }

        # ---------------- ROUTINE ACTIVITIES & FACTUAL / CASUAL INQUIRIES ----------------
        routine_patterns = [
            r"\b(?:hungry|eating\s+(?:lunch|dinner|breakfast|food)|having\s+(?:lunch|dinner|breakfast)|cooking|eating\s+biryani)\b",
            r"\b(?:made\s+(?:a\s+)?cup\s+of\s+coffee|making\s+coffee|making\s+tea|drinking\s+coffee|had\s+(?:a\s+)?(?:cup\s+of\s+)?coffee|just\s+had\s+coffee|having\s+coffee|drank\s+coffee)\b",
            r"\b(?:going\s+to\s+(?:college|school|university|class|work|the\s+gym|bed|sleep))\b",
            r"\b(?:submitted\s+(?:all\s+)?(?:the\s+)?(?:documents|assignment|application)|visa\s+application|flight\s+departs)\b",
            r"\b(?:finished\s+(?:my\s+)?(?:assignment|homework)|cleaning\s+(?:my\s+)?room|doing\s+laundry)\b",
            r"\b(?:watching\s+(?:a\s+)?(?:movie|tv|show|film)|listening\s+to\s+music|playing\s+(?:a\s+)?game|reading\s+(?:a\s+)?book|went\s+for\s+a\s+walk|going\s+for\s+a\s+walk)\b",
            r"\b(?:having\s+a\s+normal\s+day|just\s+chilling|just\s+relaxing|hanging\s+out)\b",
            r"\b(?:the\s+weather\s+is|weather\s+outside|nice\s+day\s+outside|sunny\s+day|raining\s+outside)\b",
            r"^(?:what\s+is|whats|what\s+are|where\s+is|when\s+did|who\s+is|why\s+is|how\s+does|how\s+do|can\s+you\s+explain|define|tell\s+me\s+about)\s+(?!depression|anxiety|stress|trauma|ptsd|mental|suicid|grief|lonel|panic|disorder|therapy|counsel)",
            r"\b(?:tell\s+me\s+something\s+interesting|can\s+you\s+tell\s+me\s+a\s+story|tell\s+me\s+a\s+fact)\b",
            r"\b(?:advice\s+on\s+dealing\s+with\s+procrastination|explain\s+how\s+cognitive\s+behavioral\s+therapy\s+works)\b",
        ]
        if any(re.search(p, msg_clean) for p in routine_patterns):
            return {
                "intent": "general",
                "emotion": "neutral",
                "intent_confidence": 0.95,
                "emotion_confidence": 0.90,
                "risk_level": "LOW",
            }

        # ---------------- ANGER ----------------
        anger_patterns = [
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:so\s+|very\s+|really\s+|extremely\s+|absolutely\s+)?(?:angry|mad|furious|pissed|enraged|irritated|annoyed|frustrated)\b",
            r"\b(?:so\s+furious|so\s+pissed|pissed\s+off|angry\s+at\s+myself|absolutely\s+furious|blood\s+boil)\b",
        ]
        if any(re.search(p, msg_clean) for p in anger_patterns):
            return {
                "intent": "anger",
                "emotion": "anger",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "LOW",
            }

        # ---------------- ANXIETY ----------------
        anxiety_patterns = [
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:so\s+|very\s+|really\s+|extremely\s+)?(?:anxious|scared|afraid|worried|nervous|panicked|terrified)\b",
            r"\b(?:i\s+have|having)\s+(?:anxiety|a\s+panic\s+attack|panic)\b",
            r"\b(?:feeling\s+anxious|worried\s+about\s+tomorrow|terrified\s+of\s+messing\s+up)\b",
        ]
        if any(re.search(p, msg_clean) for p in anxiety_patterns):
            return {
                "intent": "anxiety",
                "emotion": "fear",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "MEDIUM",
            }

        # ---------------- STRESS / WORKLOAD ----------------
        # ---------------- STRESS / WORKLOAD ----------------
        stress_patterns = [
            r"\b(?:a\s+lot\s+of\s+work|lot\s+of\s+work|lots\s+of\s+work|too\s+much\s+work|so\s+much\s+work)\b",
            r"\b(?:many\s+tasks|too\s+many\s+tasks|work\s+to\s+complete|work\s+to\s+finish)\b",
            r"\b(?:deadlines?|work\s+pressure|pressure\s+from\s+work|under\s+pressure)\b",
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:so\s+|very\s+|really\s+)?(?:stre+ss+ed|overwhelmed|under\s+stre+ss+|stre+ss+ed\s+out)\b",
            r"\b(?:stre+ss+ed\s+because|stre+ss+ed\s+out|presentations?\s+this\s+week)\b",
        ]
        if any(re.search(p, msg_clean) for p in stress_patterns):
            return {
                "intent": "stress",
                "emotion": "stress",
                "intent_confidence": 0.98,
                "emotion_confidence": 0.95,
                "risk_level": "MEDIUM",
            }

        # ---------------- SLEEP ----------------
        sleep_patterns = [
            r"\b(?:cannot|cant|can\s+not)\s+sleep\b",
            r"\b(?:not\s+able\s+to\s+sleep|having\s+trouble\s+sleeping|insomnia|sleepless)\b",
            r"\b(?:tossing\s+and\s+turning|head\s+hits\s+the\s+pillow|mind\s+wont\s+stop\s+racing)\b",
        ]
        if any(re.search(p, msg_clean) for p in sleep_patterns):
            return {
                "intent": "sleep_problem",
                "emotion": "sadness",
                "intent_confidence": 1.0,
                "emotion_confidence": 0.90,
                "risk_level": "LOW",
            }

        # ---------------- SADNESS / DEPRESSION ----------------
        # Explicit depression statements
        depression_patterns = [
            r"\b(?:i\s+)?(?:am|im|feel|feeling)\s+(?:so\s+|very\s+|really\s+|deeply\s+)?depressed\b",
            r"\b(?:struggling\s+with\s+depression|deeply\s+depressed|clinical\s+depression)\b",
            r"\b(?:everything\s+feels\s+heavy|no\s+motivation\s+to\s+get\s+out\s+of\s+bed|feel\s+so\s+lonely\s+and\s+completely\s+invisible)\b",
        ]
        if any(re.search(p, msg_clean) for p in depression_patterns):
            return {
                "intent": "depression",
                "emotion": "sadness",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "MEDIUM",
            }

        sadness_patterns = [
            r"\b(?:i\s+)?(?:am|im|feel|feeling|have\s+been\s+feeling|been\s+feeling)\s+(?:so\s+|very\s+|really\s+|deeply\s+|pretty\s+|quite\s+)?(?:sad|unhappy|miserable|down|low|hopeless|worthless|empty|broken)\b",
            r"\b(?:feel\s+empty|feel\s+worthless|feel\s+hopeless|feeling\s+sad|feeling\s+down|feeling\s+low|feel\s+low)\b",
        ]
        if any(re.search(p, msg_clean) for p in sadness_patterns):
            return {
                "intent": "sadness",
                "emotion": "sadness",
                "intent_confidence": 1.0,
                "emotion_confidence": 1.0,
                "risk_level": "MEDIUM",
            }

        return None

    def _model_analysis(self, message: str):
        intent_name = "general"
        emotion_name = "neutral"
        intent_confidence = 0.0
        emotion_confidence = 0.0

        try:
            intent_predictor, emotion_predictor = self._get_predictors()

            intent_result = dict(intent_predictor.predict(message) or {})
            raw_intent = str(intent_result.get("intent") or "general")
            raw_intent_conf = float(intent_result.get("confidence") or 0.0)

            # CALIBRATION: The 16-class intent model only has mental-health classes.
            # Avoid falsely routing normal conversation or factual queries to clinical conditions.
            msg_lower = (message or "").lower().strip()

            # Factual queries / general informational questions should never be clinical conditions
            is_factual_query = bool(re.search(
                r"^(?:what\s+is|whats|what\s+are|where\s+is|when\s+did|who\s+is|why\s+is|how\s+does|how\s+do|can\s+you\s+explain|define|tell\s+me\s+about)\s+(?!depression|anxiety|stress|trauma|ptsd|mental|suicid|grief|lonel|panic|disorder|therapy|counsel)",
                msg_lower
            ))

            has_suicide_cue = any(w in msg_lower for w in [
                "die", "dying", "dead", "death", "suicid", "kill", "harm", "hurt",
                "alive", "living", "live", "exist", "existing", "disappear", "born",
                "without me", "no reason", "no point", "better off", "wake up", "give up"
            ])
            has_addiction_cue = any(w in msg_lower for w in ["drug", "alcohol", "drink", "smoke", "addict", "substance", "weed", "pill", "sober", "relapse"])
            has_trauma_cue = any(w in msg_lower for w in ["trauma", "abuse", "ptsd", "assault", "accident", "flashback", "attacked"])
            has_depression_cue = (
                any(w in msg_lower for w in ["depress", "hopeless", "worthless", "empty", "sad", "miserable", "despair", "no motivation", "unhappy", "hurting", "crying", "lonely", "alone", "giving up", "low mood", "exhausted", "numb", "darkness", "bleak", "gloom"])
                or bool(re.search(r"\b(?:feel|feeling|am|im|been)\s+(?:so\s+|very\s+|really\s+|pretty\s+|quite\s+)?low\b", msg_lower))
                or bool(re.search(r"\bfeeling\s+low\b", msg_lower))
            )
            has_grief_cue = any(w in msg_lower for w in ["passed away", "died", "loss", "grief", "lost my", "funeral", "mourning", "miss him", "miss her", "death of"])
            has_career_cue = any(w in msg_lower for w in ["career", "job", "profession", "future", "work", "major", "field", "degree", "college", "university", "interview", "resume", "confused", "which path", "promotion", "unemployed", "studying", "engineering", "switch", "boss", "coworker", "office"])
            has_relationship_cue = any(w in msg_lower for w in ["girlfriend", "boyfriend", "partner", "spouse", "husband", "wife", "dating", "relationship", "breakup", "broke up", "ex", "love", "cheated", "dumped", "divorce", "together", "fight with", "fighting with", "falling out"])
            has_family_cue = any(w in msg_lower for w in ["family", "parent", "parents", "mother", "mom", "father", "dad", "brother", "sister", "sibling", "child", "son", "daughter", "cousin", "relative"])
            has_friendship_cue = any(w in msg_lower for w in ["friend", "friends", "friendship", "bestie", "pal", "buddy", "roommate", "classmate", "peers", "ignored me", "falling out"])
            has_sleep_cue = any(w in msg_lower for w in ["sleep", "sleeping", "insomnia", "sleepless", "nightmare", "awake", "tossing and turning", "bed", "pillow", "restless", "night"])
            has_anger_cue = any(w in msg_lower for w in ["anger", "angry", "mad", "furious", "pissed", "hate", "rage", "irritat", "annoy", "infuriat", "frustrat", "outrage", "blood boil"])
            has_stress_cue = (
                bool(re.search(r"\bstre+ss+", msg_lower))
                or any(w in msg_lower for w in ["stress", "pressure", "overwhelm", "deadline", "burden", "burnout", "burnt out", "too much", "workload", "exhaust", "strain", "presentation", "racing", "tasks"])
            )
            has_anxiety_cue = any(w in msg_lower for w in ["anxious", "anxiety", "panic", "worry", "worried", "nervous", "scared", "fear", "afraid", "freaking out", "dread", "terrified", "apprehens"])
            has_self_esteem_cue = any(w in msg_lower for w in ["confidence", "self-esteem", "self esteem", "insecure", "ugly", "not good enough", "worthless", "hate myself", "failure", "loser", "inferior", "ashamed"])

            if is_factual_query:
                intent_name = "general"
                intent_confidence = 0.90
            elif raw_intent == "suicidal_thought" and not has_suicide_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent in {"addiction", "substance_abuse"} and not has_addiction_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "trauma" and not has_trauma_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "depression" and not has_depression_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "grief" and not has_grief_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "career_confusion" and not has_career_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent in {"relationship", "breakup"} and not has_relationship_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "family" and not has_family_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "friendship" and not has_friendship_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "sleep_problem" and not has_sleep_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "self_esteem" and not has_self_esteem_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "anger" and not has_anger_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "anxiety" and not has_anxiety_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent == "stress" and not has_stress_cue:
                intent_name = "general"
                intent_confidence = 0.50
            elif raw_intent_conf < 0.40:
                intent_name = "general"
                intent_confidence = raw_intent_conf
            else:
                intent_name = raw_intent
                intent_confidence = raw_intent_conf

        except Exception:
            logger.exception("Intent prediction failed")

        try:
            intent_predictor, emotion_predictor = self._get_predictors()

            emotion_result = dict(emotion_predictor.predict(message) or {})
            raw_emotion = str(emotion_result.get("emotion") or "neutral")
            raw_emotion_conf = float(emotion_result.get("confidence") or 0.0)
            raw_dist = emotion_result.get("distribution")
            raw_secondary = emotion_result.get("secondary", [])
            raw_is_mixed = emotion_result.get("is_mixed", False)
            raw_pattern = emotion_result.get("pattern", "concentrated")

            # The 6-class emotion model lacks a 'neutral' class, so casual, short,
            # or factual sentences frequently trigger negative emotions falsely.
            msg_lower = (message or "").lower()
            has_anger_cue = any(w in msg_lower for w in ["angry", "mad", "furious", "hate", "pissed", "annoy", "irritat", "rage", "damn", "frustrat", "infuriat", "outrage", "blood boil"])
            has_sadness_cue = (
                any(w in msg_lower for w in ["sad", "depress", "unhappy", "cry", "miserable", "heartbroken", "grief", "hopeless", "lonely", "hurt", "pain", "loss", "mourn", "weep", "sobbing", "low mood"])
                or bool(re.search(r"\b(?:feel|feeling|am|im|been)\s+(?:so\s+|very\s+|really\s+|pretty\s+|quite\s+)?low\b", msg_lower))
                or bool(re.search(r"\bfeeling\s+low\b", msg_lower))
            )
            has_fear_cue = any(w in msg_lower for w in ["scared", "fear", "anxious", "anxiety", "panic", "terrified", "worried", "nervous", "afraid", "dread", "apprehens", "frightened", "alarmed", "uneasy"])

            if raw_emotion == "anger" and not has_anger_cue:
                emotion_name = "neutral"
                emotion_confidence = 70.0
                secondary_emotions = []
                is_mixed = False
                pattern = "concentrated"
            elif intent_name == "general" and raw_emotion in {"sadness", "fear"} and not (has_sadness_cue or has_fear_cue):
                emotion_name = "neutral"
                emotion_confidence = 70.0
                secondary_emotions = []
                is_mixed = False
                pattern = "concentrated"
            else:
                emotion_name = raw_emotion
                emotion_confidence = raw_emotion_conf
                secondary_emotions = raw_secondary
                is_mixed = raw_is_mixed
                pattern = raw_pattern

        except Exception:
            logger.exception("Emotion prediction failed")
            secondary_emotions = []
            is_mixed = False
            pattern = "concentrated"
            raw_dist = None

        return {
            "intent": intent_name,
            "emotion": emotion_name,
            "intent_confidence": intent_confidence,
            "emotion_confidence": emotion_confidence,
            "risk_level": "HIGH" if intent_name == "suicidal_thought" else "LOW",
            "secondary_emotions": secondary_emotions,
            "is_mixed": is_mixed,
            "pattern": pattern,
            "distribution": raw_dist,
        }

    def generate_video_response(
        self,
        face_emotion="neutral",
        mental_state="Normal",
        risk_level="LOW",
        history=None,
        memory="",
    ):
        """
        Generate a natural chatbot response for a video-only analysis.
        Delegates to the ResponseGenerator's video-specific method so the
        detected facial emotion is used as structured multimodal context
        (no artificial user message is created).
        """
        if history is None:
            history = []
        return self.response_generator.generate_video_response(
            face_emotion=face_emotion,
            mental_state=mental_state,
            risk_level=risk_level,
            history=history,
            memory=memory,
        )

    def analyze(self, message: str) -> dict:
        """
        Run the complete unified analysis pipeline (rules + calibrated model analysis).
        Returns:
            {
                "intent": intent_name,
                "intent_confidence": intent_confidence,
                "emotion": emotion_name,
                "emotion_confidence": emotion_confidence,
                "risk_level": risk_level,
                "is_negated_crisis": is_negated_crisis,
                "source": "rule" | "model" | "default"
            }
        """
        message = str(message or "").strip()
        if not message:
            return {
                "intent": "general",
                "intent_confidence": 0.0,
                "emotion": "neutral",
                "emotion_confidence": 0.0,
                "risk_level": "LOW",
                "is_negated_crisis": False,
                "source": "default",
            }

        rule_result = self._rule_based_analysis(message)
        if rule_result is not None:
            res = dict(rule_result)
            res.setdefault("secondary_emotions", [])
            res.setdefault("is_mixed", False)
            res.setdefault("pattern", "rule")
            res.setdefault("distribution", None)
            res["source"] = "rule"
            return res

        model_result = self._model_analysis(message)
        res = dict(model_result)
        res["source"] = "model"
        return res

    def chat(
        self,
        message: str,
        history=None,
        memory="",
        face_emotion=None,
    ):
        if history is None:
            history = []

        message = str(message or "").strip()

        if not message:
            return {
                "user_message": message,
                "intent": "general",
                "intent_confidence": 0.0,
                "emotion": "neutral",
                "emotion_confidence": 0.0,
                "risk_level": "LOW",
                "response": "I'm here with you. What would you like to talk about?",
                "secondary_emotions": [],
                "is_mixed": False,
            }

        analysis = self.analyze(message)

        intent_name = analysis["intent"]
        emotion_name = analysis["emotion"]
        intent_confidence = analysis["intent_confidence"]
        emotion_confidence = analysis["emotion_confidence"]
        risk_level = analysis.get("risk_level", "LOW")
        is_negated_crisis = analysis.get("is_negated_crisis", False)

        # Generate contextual response.
        try:
            response = self.response_generator.generate(
                message=message,
                emotion=emotion_name,
                intent=intent_name,
                history=history,
                memory=memory,
                face_emotion=face_emotion,
                risk_level=risk_level,
                is_negated_crisis=is_negated_crisis,
            )

            response = str(
                response
                or "I'm here with you. Tell me more about what you're experiencing."
            )

        except Exception:
            logger.exception("Response generation failed")
            response = (
                "I'm here with you. Tell me a little more about "
                "what you're experiencing."
            )

        # Store conversation.
        self.history.append(
            {
                "user": message,
                "intent": {
                    "intent": intent_name,
                    "confidence": intent_confidence,
                },
                "emotion": {
                    "emotion": emotion_name,
                    "confidence": emotion_confidence,
                },
                "risk_level": risk_level,
                "bot": response,
            }
        )

        if len(self.history) > 10:
            self.history.pop(0)

        return {
            "user_message": message,
            "intent": intent_name,
            "intent_confidence": intent_confidence,
            "emotion": emotion_name,
            "emotion_confidence": emotion_confidence,
            "risk_level": risk_level,
            "response": response,
            "secondary_emotions": analysis.get("secondary_emotions", []),
            "is_mixed": analysis.get("is_mixed", False),
        }
