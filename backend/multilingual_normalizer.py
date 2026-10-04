"""
backend/multilingual_normalizer.py

Generalized Multilingual Normalization & Semantic Routing Layer for MindSense AI.

Handles:
- English
- Kannada (native script & Kanglish / Latin transliteration)
- Hindi (Devanagari script & Hinglish / Latin transliteration)
- Other supported Indian languages (Tamil, Telugu, Malayalam, Marathi, Bengali, etc.)

Features:
- Character & vowel repeat compression (e.g. 'nangeee' -> 'nange', 'illaaa' -> 'illa')
- Phonetic & morphological normalization of common Kanglish/Hinglish pronouns, verbs, and negations
- Generalized language detection (native unicode scripts + transliteration keywords)
- Language switch request detection ("can you speak Hindi?", "Kannada alli matadi", etc.)
- Physical health distress recognition ("nanage thale novu", "sar dard", "headache", etc.)
- Multilingual emotional distress recognition ("manasu sari illa", "thumba bejar", etc.)
- High-priority multilingual crisis & negation detection (English, Kannada, Kanglish, Hindi, Hinglish)
"""

import re
from typing import Dict, Any, Optional


# ---------------------------------------------------------------------------
# 1. Text & Repeated-Character Normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Generalized text normalization:
    - Lowercases, strips punctuation, normalizes apostrophes
    - Compresses runs of 3+ identical letters to at most 2 (e.g. 'nangeeee' -> 'nangee', 'soooo' -> 'soo')
    - Cleans excess whitespace
    """
    if not text:
        return ""
    t = str(text).strip().lower()
    # Normalize apostrophes & smart quotes
    t = re.sub(r"['’`]", "", t)
    # Compress 3 or more repeated characters to 2
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)
    # Clean non-alphanumeric (preserve native unicode characters)
    t = re.sub(r"[^\w\s\u0900-\u0DFF]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_kanglish_tokens(text: str) -> str:
    """
    Normalizes common Kanglish spelling variations to canonical roots
    without creating a rigid dictionary.
    - nange / nanage / nanag / nangee -> nanage
    - illa / illae / illla / ela (in negation) -> illa
    - agalla / aagalla / agtilla / aagtilla -> agalla
    - beku / bekku / bekuu -> beku
    - madodu / maadodu / madbeku -> madodu
    - ansutte / anisutte / anisthide / anusthide -> anisutte
    """
    norm = normalize_text(text)
    if not norm:
        return ""

    tokens = norm.split()
    cleaned_tokens = []
    for tok in tokens:
        # Pronoun variations: nanage, nange, nanag, nangee -> nanage
        if re.fullmatch(r"nan?a?g[eio]*", tok) or tok in {"nange", "nangee", "nanag", "nanage"}:
            cleaned_tokens.append("nanage")
        # Negation: illa, illaa, ilaa, illae, ela
        elif re.fullmatch(r"i?ll?a+[ei]?", tok) or tok in {"illa", "illae", "ila", "ela"}:
            cleaned_tokens.append("illa")
        # Inability: agtilla, aagtilla, agalla, aagalla, agolla
        elif re.search(r"a+g(?:t?illa|alla|olla)", tok):
            cleaned_tokens.append("agalla")
        # Desire / obligation: beku, bekku, bek
        elif re.fullmatch(r"be+k[ku]*", tok):
            cleaned_tokens.append("beku")
        # Feeling / sensation: anisutte, ansutte, anisthide, anusthide
        elif re.search(r"an[iu]?s(?:th?ide|utte|uthe)", tok):
            cleaned_tokens.append("anisutte")
        # Sadness / distress: bejar, bejara, bjar
        elif re.search(r"b[ei]ja+r[au]?", tok):
            cleaned_tokens.append("bejar")
        # Speaking: matadi, maathadi, mathadi
        elif re.search(r"ma+th?a+[nd]i", tok):
            cleaned_tokens.append("matadi")
        # Pain: novu, novuu, novvu, noavu
        elif re.search(r"no+[av]v?u*", tok):
            cleaned_tokens.append("novu")
        # Head: thale, tale, thele
        elif re.search(r"th?a+le+", tok):
            cleaned_tokens.append("thale")
        # Mind / heart: manasu, manassu, mansu
        elif re.search(r"ma+na?s+u*", tok):
            cleaned_tokens.append("manasu")
        # A lot / very: thumba, tumba
        elif re.search(r"th?u+mb?a+", tok):
            cleaned_tokens.append("thumba")
        # Hindi negation: nahi, nahin, nahee, nhi
        elif re.fullmatch(r"na?h[ei]+n?", tok) or tok in {"nhi", "nhn"}:
            cleaned_tokens.append("nahi")
        # Hindi very: bahut, bohot, bht, bhot
        elif re.fullmatch(r"b[ao]h?u?t", tok) or tok == "bht":
            cleaned_tokens.append("bahut")
        # Hindi want: chahta, chahti, chahte
        elif re.search(r"cha+h?t[aei]+", tok):
            cleaned_tokens.append("chahta")
        # Hindi pain: dard, drd
        elif re.search(r"da?rd+", tok):
            cleaned_tokens.append("dard")
        else:
            cleaned_tokens.append(tok)

    return " ".join(cleaned_tokens)


# ---------------------------------------------------------------------------
# 2. Generalized Language Detection (Native + Transliterated)
# ---------------------------------------------------------------------------

KANGLISH_MARKERS = {
    "nanage", "nange", "nanu", "naanu", "nimma", "nimmanna", "beku", "illa", "agide",
    "aagide", "madodu", "hege", "yake", "yaako", "thale", "novu", "matadi", "kannada",
    "saayabeku", "badukalu", "thumba", "bejar", "kashta", "manasu", "manasilla",
    "gotilla", "gottilla", "ansutte", "anisthide", "anthide", "ivathu", "ivattu",
    "chennagi", "helidru", "bartheeni", "hogtheeni", "alli", "illi", "dayavittu",
    "kelasa", "mane", "ootha", "oota", "susthu", "jwara", "kushiyaagide", "kushi"
}

HINGLISH_MARKERS = {
    "mujhe", "mera", "meri", "mere", "karna", "nahi", "raha", "rahi", "rahe", "hai",
    "hain", "hoon", "hun", "kya", "kyun", "kaise", "dard", "marna", "jeena", "bahut",
    "bohot", "theek", "baat", "karo", "bolo", "kripya", "aap", "tum", "yaar", "dost",
    "zindagi", "samajh", "lagta", "lagti", "udas", "gussa", "tension", "dimag"
}

TELUGU_LATIN_MARKERS = {
    "nenu", "meeru", "ela", "unnaru", "cheppandi", "emi", "ikkade", "baagunnara",
    "naku", "miku", "chala", "undi", "ledu", "chaavu", "telusaa", "badha"
}

TAMIL_LATIN_MARKERS = {
    "naan", "neenga", "enna", "romba", "paaru", "sollu", "vandha", "irukku", "eppo",
    "enge", "yaar", "theriyuma", "solla", "mudiyum", "kavalai", "valikuthu"
}


def detect_language_generalized(text: str) -> dict:
    """
    Detects language taking into account:
    1. Short English common words
    2. Native Unicode scripts (Kannada, Hindi, Tamil, Telugu, etc.)
    3. Transliterated Kanglish / Hinglish / etc. via semantic token frequency
    4. Default English fallback
    """
    t = str(text or "").strip()
    if not t:
        return {"name": "English", "script": "latin", "code": "en"}

    tl = t.lower()
    norm = normalize_kanglish_tokens(t)
    tokens = set(norm.split())

    # 1. Pure English short words
    ENGLISH_SHORT = {
        "hi", "hey", "hello", "ok", "okay", "yes", "no", "bye", "thanks", "thank you",
        "good", "fine", "great", "nice", "sure", "please", "sorry", "help", "who", "what",
        "how", "why", "when", "where", "i", "am", "are", "you", "is", "it", "we"
    }
    if tl.strip("!?., ") in ENGLISH_SHORT:
        return {"name": "English", "script": "latin", "code": "en"}

    # 2. Native script Unicode inspection
    for ch in t:
        o = ord(ch)
        if 0x0C80 <= o <= 0x0CFF:
            return {"name": "Kannada", "script": "native", "code": "kn"}
        if 0x0900 <= o <= 0x097F:
            MARATHI_WORDS = ["आहे", "नाही", "कसा", "कशी", "कसे", "मरावे", "वाटते", "खूप", "मरायचं"]
            if any(w in t for w in MARATHI_WORDS):
                return {"name": "Marathi", "script": "native", "code": "mr"}
            return {"name": "Hindi", "script": "native", "code": "hi"}
        if 0x0B80 <= o <= 0x0BFF:
            return {"name": "Tamil", "script": "native", "code": "ta"}
        if 0x0C00 <= o <= 0x0C7F:
            return {"name": "Telugu", "script": "native", "code": "te"}
        if 0x0D00 <= o <= 0x0D7F:
            return {"name": "Malayalam", "script": "native", "code": "ml"}
        if 0x0980 <= o <= 0x09FF:
            return {"name": "Bengali", "script": "native", "code": "bn"}
        if 0x0A80 <= o <= 0x0AFF:
            return {"name": "Gujarati", "script": "native", "code": "gu"}
        if 0x0A00 <= o <= 0x0A7F:
            return {"name": "Punjabi", "script": "native", "code": "pa"}
        if 0x0600 <= o <= 0x06FF:
            return {"name": "Urdu", "script": "native", "code": "ur"}

    # 3. Transliterated markers matching
    kn_overlap = len(tokens & KANGLISH_MARKERS)
    hi_overlap = len(tokens & HINGLISH_MARKERS)
    te_overlap = len(tokens & TELUGU_LATIN_MARKERS)
    ta_overlap = len(tokens & TAMIL_LATIN_MARKERS)

    if re.search(r"\b(?:thale\s+novu|tale\s+novu|hotte\s+novu|manasu\s+sari\s+illa|thumba\s+bejar|saayabeku\s+anisutte|badukalu\s+illa|kannada\s+alli\s+matadi)\b", norm):
        return {"name": "Kannada", "script": "latin", "code": "kn"}
    if re.search(r"\b(?:sar\s+dard|pet\s+dard|marna\s+chahta|jeena\s+nahi|hindi\s+me\s+baat)\b", norm):
        return {"name": "Hindi", "script": "latin", "code": "hi"}

    if kn_overlap > 0 and kn_overlap >= max(hi_overlap, te_overlap, ta_overlap):
        return {"name": "Kannada", "script": "latin", "code": "kn"}
    if hi_overlap > 0 and hi_overlap >= max(kn_overlap, te_overlap, ta_overlap):
        return {"name": "Hindi", "script": "latin", "code": "hi"}
    if te_overlap > 0:
        return {"name": "Telugu", "script": "latin", "code": "te"}
    if ta_overlap > 0:
        return {"name": "Tamil", "script": "latin", "code": "ta"}

    return {"name": "English", "script": "latin", "code": "en"}


# ---------------------------------------------------------------------------
# 3. Language Switch Request Intent
# ---------------------------------------------------------------------------

def detect_language_request(text: str) -> Optional[Dict[str, Any]]:
    """
    Detects if the user is asking to switch languages.
    Examples:
    - 'can you speak Hindi?'
    - 'Kannada alli matadi'
    - 'Can we talk in Kannada?'
    - 'I want to talk in Hindi'
    - 'I will type in Kanglish, answer in Kannada'
    - 'speak to me in Kannada'
    - 'hindi mein bolo'
    """
    norm = normalize_text(text)
    if not norm:
        return None

    target_code = None
    target_name = None

    if re.search(r"\b(?:kannada|kannadadalli|kannadadalli\s+matadi|kanglish|ಕನ್ನಡ)\b", norm) or "ಕನ್ನಡ" in text:
        target_code = "kn"
        target_name = "Kannada"
    elif re.search(r"\b(?:hindi|hindustani|हिन्दी|हिंदी)\b", norm) or "हिंदी" in text or "हिन्दी" in text:
        target_code = "hi"
        target_name = "Hindi"
    elif re.search(r"\b(?:tamil|தமிழ்)\b", norm) or "தமிழ்" in text:
        target_code = "ta"
        target_name = "Tamil"
    elif re.search(r"\b(?:telugu|తెలుగు)\b", norm) or "తెలుగు" in text:
        target_code = "te"
        target_name = "Telugu"
    elif re.search(r"\b(?:english|angrezi|english\s+please)\b", norm):
        target_code = "en"
        target_name = "English"

    if not target_code:
        return None

    intent_patterns = [
        r"\b(?:can\s+(?:you|we)\s+)?(?:speak|talk|chat|communicate)\s+(?:in\s+)?",
        r"\b(?:do\s+you\s+know|do\s+you\s+speak|can\s+you\s+understand)\b",
        r"\b(?:want\s+to|wanna|like\s+to)\s+(?:talk|speak|chat)\s+(?:in\s+)?",
        r"\b(?:alli\s+matadi|matadi|maathadi|mathadi|helu)\b",  # Kannada
        r"\b(?:me\s+baat\s+karo|mein\s+baat\s+karo|mein\s+bolo|me\s+bolo|baat\s+kare?i?n)\b",  # Hindi
        r"\b(?:answer\s+in|reply\s+in|respond\s+in|type\s+in)\b",
        r"\b(?:switch|change)\s+(?:back\s+)?to\b",
        r"\b(?:conversation\s+in|continue\s+in|continue\s+this\s+conversation\s+in)\b",
    ]

    is_req = any(re.search(p, norm) for p in intent_patterns)
    if not is_req:
        if norm in {"kannada matadi", "kannada alli matadi", "hindi me baat karo", "speak hindi", "speak kannada"}:
            is_req = True
        elif f"can you speak {target_name.lower()}" in norm or f"do you know {target_name.lower()}" in norm:
            is_req = True
        elif "ಮಾತನಾಡಿ" in text or "ಮಾತಾಡಿ" in text or "बात करो" in text or "बोलिए" in text:
            is_req = True

    if is_req:
        return {
            "is_language_request": True,
            "target_code": target_code,
            "target_name": target_name,
        }

    return None


# ---------------------------------------------------------------------------
# 4. Physical Health Symptoms vs Mental State
# ---------------------------------------------------------------------------

PHYSICAL_SYMPTOM_PATTERNS = [
    # Headache (Latin)
    r"\b(?:thale\s+novu|tale\s+novu|thale\s+novtha|thale\s+suttodu|thale\s+baravagide)\b",
    r"\b(?:sar\s+me\s+dard|sar\s+dard|sir\s+dard|sar\s+dukh\s+raha)\b",
    r"\b(?:headache|head\s+hurts|head\s+pain|pounding\s+head|migraine|splitting\s+headache)\b",

    # Stomach ache (Latin)
    r"\b(?:hotte\s+novu|hotte\s+novtha)\b",
    r"\bpet\s*(?:me\s+)?(?:\w+\s+){0,3}dard\b",
    r"\b(?:stomach\s+ache|stomach\s+pain|belly\s+ache|upset\s+stomach|cramps|nausea)\b",
    r"\b(?:stomach|belly|abdomen)\s*(?:is\s+|has\s+been\s+)?(?:\w+\s+){0,2}(?:hurting|hurts|pain|ache|upset|burning|cramps)\b",

    # Fever / Cold / Cough (Latin)
    r"\b(?:jwara|sheetha|seetha|kemmu)\b",
    r"\b(?:bukhar|khansi|jukham|sardi)\b",
    r"\b(?:fever|high\s+temperature|cough|coughing|cold|sore\s+throat|flu|chills)\b",

    # Body pain / tiredness / dizziness (Latin)
    r"\b(?:mai\s+novu|deha\s+novu|susthu|kai\s+kaalu\s+novu)\b",
    r"\b(?:badan\s+dard|thakan|chakkar|kamzori)\b",
    r"\b(?:body\s+pain|body\s+ache|physical\s+exhaustion|dizzy|dizziness|muscle\s+ache|toothache|back\s+pain)\b",
]

NATIVE_INDIC_PHYSICAL = [
    "ತಲೆ ನೋವು", "ತಲೆನೋವು", "ಹೊಟ್ಟೆ ನೋವು", "ಹೊಟ್ಟೆನೋವು", "ಜ್ವರ", "ಶೀತ", "ಕೆಮ್ಮು", "ಮೈ ನೋವು", "ಸುಸ್ತು",
    "सिर दर्द", "सिरदर्द", "पेट दर्द", "बुखार", "खांसी", "जुकाम", "बदन दर्द", "चक्कर"
]


def detect_physical_health(text: str) -> Optional[Dict[str, Any]]:
    """
    Detects if the user is expressing ordinary physical symptoms (e.g. headache, fever)
    without clinical mental-health / crisis implications.
    """
    norm = normalize_kanglish_tokens(text)
    raw = str(text or "")

    has_phys = False
    symptom = "general_physical"

    # Check native Indic keywords
    for kw in NATIVE_INDIC_PHYSICAL:
        if kw in raw:
            has_phys = True
            if "ತಲೆ" in kw or "सिर" in kw:
                symptom = "headache"
            elif "ಹೊಟ್ಟೆ" in kw or "पेट" in kw:
                symptom = "stomach_pain"
            elif "ಜ್ವರ" in kw or "बुखार" in kw:
                symptom = "fever_cold"
            else:
                symptom = "body_pain"
            break

    # Check Latin patterns
    if not has_phys and norm:
        for pat in PHYSICAL_SYMPTOM_PATTERNS:
            if re.search(pat, norm) or re.search(pat, raw.lower()):
                has_phys = True
                if any(w in norm for w in ["thale", "tale", "headache", "head", "migraine", "sar", "sir"]):
                    symptom = "headache"
                elif any(w in norm for w in ["hotte", "pet", "stomach", "belly", "nausea"]):
                    symptom = "stomach_pain"
                elif any(w in norm for w in ["jwara", "bukhar", "fever", "temperature", "cold", "cough"]):
                    symptom = "fever_cold"
                else:
                    symptom = "body_pain"
                break

    if has_phys:
        return {
            "is_physical_health": True,
            "symptom": symptom,
            "intent": "physical_health",
            "emotion": "neutral",
            "risk_level": "LOW",
            "mental_state": "Normal",
        }

    return None


# ---------------------------------------------------------------------------
# 5. Multilingual Emotional Distress (Kanglish / Hinglish / Native)
# ---------------------------------------------------------------------------

MULTILINGUAL_DISTRESS_PATTERNS = [
    r"\b(?:manas[uige]*\s+sari\s+illa|manasu\s+sariyilla|mind\s+sari\s+illa)\b",
    r"\b(?:thumba\s+bejar|bejar\s+agide|bejaara\s+agide|thumba\s+kashta)\b",
    r"\b(?:manasika\s+susthu|dimag\s+thak\s+gaya|mansu\s+susthu)\b",
    r"\bmanas[uige]*\s*(?:\w+\s+)?susthu\b",
    r"\b(?:thumba\s+stress|stress\s+agide|tension\s+agide|thumba\s+chinthe)\b",
    r"\b(?:mann\s+theek\s+nahi|udas\s+hu|bahut\s+udas|bahut\s+tension|pareshan\s+hu|chinta\s+ho\s+rahi)\b",
    r"\buda+s\s*(?:hu|hai|lag\s+raha|lagti|lagta)\b",
    r"\b(?:bahut\s+)?uda+s\b",
]

NATIVE_INDIC_DISTRESS = [
    "ಮನಸ್ಸು ಸರಿ ಇಲ್ಲ", "ಮನಸ್ಸಿಗೆ ಸರಿ ಇಲ್ಲ", "ಬೇಜಾರು", "ತುಂಬಾ ಬೇಜಾರು", "ಕಷ್ಟ", "ಚಿಂತೆ",
    "मन ठीक नहीं", "बहुत उदास", "परेशान", "चिंता हो रही", "तनाव"
]


def detect_multilingual_distress(text: str) -> Optional[Dict[str, Any]]:
    """
    Detects transliterated ordinary emotional distress in Kanglish, Hinglish, or native scripts.
    Routes to appropriate supportive emotion/intent (sadness/stress) with MEDIUM risk.
    """
    norm = normalize_kanglish_tokens(text)
    raw = str(text or "")

    for kw in NATIVE_INDIC_DISTRESS:
        if kw in raw:
            if "ಚಿಂತೆ" in kw or "तनाव" in kw:
                return {
                    "is_distress": True,
                    "intent": "stress",
                    "emotion": "stress",
                    "risk_level": "MEDIUM",
                    "mental_state": "Stress",
                }
            return {
                "is_distress": True,
                "intent": "sadness",
                "emotion": "sadness",
                "risk_level": "MEDIUM",
                "mental_state": "Depression",
            }

    if norm:
        for pat in MULTILINGUAL_DISTRESS_PATTERNS:
            if re.search(pat, norm) or re.search(pat, raw.lower()):
                if "stress" in norm or "tension" in norm or "chinthe" in norm:
                    return {
                        "is_distress": True,
                        "intent": "stress",
                        "emotion": "stress",
                        "risk_level": "MEDIUM",
                        "mental_state": "Stress",
                    }
                return {
                    "is_distress": True,
                    "intent": "sadness",
                    "emotion": "sadness",
                    "risk_level": "MEDIUM",
                    "mental_state": "Depression",
                }

    return None


# ---------------------------------------------------------------------------
# 6. High-Priority Multilingual Crisis & Negation Detection
# ---------------------------------------------------------------------------

MULTILINGUAL_CRISIS_PATTERNS = [
    # Kannada / Kanglish Suicidal & Self-Harm Intent:
    r"\b(?:sa+y[ao]?beku|sa+yoke|sa+yabeku\s+anisutte|sa+yoke\s+manasagide|sa+yabeku\s+anthide)\b",
    r"\b(?:jeeva\s+(?:bidbeku|togobeku|kaledukobeku|mugisabeku)|jeevana\s+mugisalu|jeevana\s+mugisabeku)\b",
    r"\b(?:badukalu\s+(?:istavilla|ishta\s+illa|manasilla|agalla)|badukoke\s+(?:istavilla|ishta\s+illa|agalla|agtilla))\b",
    r"\b(?:atmahatye|athmahatye|aathmahatye)\b",
    r"\bnanna\s+illade\s+ella?ru\s+chennagi\b",

    # Hindi / Hinglish Suicidal & Self-Harm Intent:
    r"\b(?:marna\s+chahta|marna\s+chahti|mar\s+jana\s+chahta|mar\s+jana\s+chahti|marne\s+ka\s+man)\b",
    r"\b(?:jaan\s+dena\s+chahta|jaan\s+de\s+dunga|jaan\s+lena\s+chahta|mar\s+jaunga)\b",
    r"\b(?:zindagi\s+khatam\s+karna|khatam\s+karna\s+chahta|jeene\s+ka\s+man\s+nahi|jeene\s+ki\s*(?:\w+\s+)?wajah\s+nahi)\b",
    r"\b(?:aatmhatya|aatmahatya|khudkushi)\b",

    # Telugu / Tamil / Malayalam transliterations
    r"\b(?:chaavu|saayali|nenu\s+chaavali|chani\s+povali|bathakali\s+anukovatledu)\b",
    r"\b(?:uyira\s+maaikka|saaga\s+vendum|vaazha\s+virumbalai|uyir\s+vazha\s+pidikkala)\b",
    r"\b(?:marikkanam|aatmahatya|jeevitham\s+maduthu|jeevikkan\s+thonnunnilla)\b",

    # English Active Crisis
    r"\b(?:want\s+to\s+die|wanna\s+die|feel\s+like\s+dying|kill\s+myself|end\s+my\s+life|take\s+my\s+own\s+life|suicide|suicidal|end\s+it\s+all)\b",
    r"\b(?:hang\s+myself|overdose|slit\s+(?:my\s+)?wrists?|jump\s+off\s+(?:a\s+)?(?:bridge|building|roof))\b",
    r"\b(?:hurt|hurting|harm|harming)\s+myself\b",
    r"\b(?:better\s+off\s+(?:dead|without\s+me)|world\s+would\s+be\s+better\s+without\s+me)\b",
    r"\b(?:dont|do\s+not|never|no\s+longer)\s+want\s+to\s+(?:live|be\s+alive|exist)\b",
    r"\bno\s+(?:reason|point)\s+to\s+(?:live|keep\s+living|stay\s+alive)\b",
]

NATIVE_INDIC_CRISIS = [
    "ಸಾಯಬೇಕು", "ಆತ್ಮಹತ್ಯೆ", "ಜೀವ ಬಿಡಬೇಕು", "ಜೀವನ ಮುಗಿಸಬೇಕು", "ಬದುಕಲು ಇಷ್ಟವಿಲ್ಲ", "ಬದುಕೋಕೆ ಇಷ್ಟವಿಲ್ಲ",
    "मरना चाहता", "मरना चाहती", "मरना है", "जान देना चाहता", "जान दे दूंगा", "आत्महत्या", "खुदकुशी", "जीना नहीं चाहता",
    "చనిపోవాలని", "చావాలని", "ఆత్మಹತ್ಯ", "தற்கொலை", "சாக வேண்டும்", "ആത്മಹത്യ", "മരിക്കണം"
]

IMMINENT_PATTERNS = [
    r"\b(?:pills|knife|gun|rope|blade|poison)\s+and\s+(?:i\s+am\s+taking|ready|using)\b",
    r"\b(?:taking\s+them\s+right\s+now|about\s+to\s+jump|jumping\s+right\s+now|hanging\s+myself\s+now)\b",
    r"\b(?:goodbye\s+forever|this\s+is\s+my\s+last\s+message|final\s+goodbye|wont\s+be\s+here\s+tomorrow)\b",
    r"\b(?:iga\s+saayoke\s+hogthini|ega\s+jeeva\s+bidtini)\b",
    r"\b(?:ab\s+jaan\s+de\s+raha\s+hu|aakhri\s+alvida)\b",
]

MULTILINGUAL_NEGATED_CRISIS = [
    # English Negation
    r"\b(?:dont|do\s+not|never|wont|will\s+not|didnt|did\s+not|cant|cannot|aint|not)\s+(?:really\s+)?(?:want|feel\s+like|plan|intend|trying)\s+(?:to\s+)?(?:die|dying|kill\s+myself|end\s+my\s+life|hurt\s+myself|harm\s+myself)\b",
    r"\b(?:not|never|no\s+longer)\s+(?:feeling\s+)?suicidal\b",
    r"\b(?:i\s+)?(?:want|wanna|choose|decided|intend)\s+to\s+(?:live|keep\s+living|stay\s+alive|be\s+alive)\b",
    r"\b(?:glad|happy|grateful)\s+to\s+be\s+alive\b",
    r"\bi\s+love\s+(?:my\s+)?life\b",

    # Kannada / Kanglish Negation
    r"\b(?:sa+yalla|sa+yodu\s+illa|sa+yoke\s+ishta\s+illa|sa+yoke\s+manasilla|sa+yodilla)\b",
    r"\b(?:badukabeku|badukoke\s+ishta\s+ide|badukbeku|badukalu\s+aase\s+ide)\b",
    r"\b(?:nanna\s+jeevana\s+premisuttene|jeevana\s*(?:\w+\s+){0,3}ishta|atmahatye\s+madolla)\b",

    # Hindi / Hinglish Negation
    r"\b(?:marna\s+nahi\s+chahta|marna\s+nahi\s+chahti|marunga\s+nahi|marungi\s+nahi|jaan\s+nahi\s+dunga)\b",
    r"\b(?:jeena\s+chahta\s+hu|jeena\s+chahti\s+hu|jeena\s+hai|khudkushi\s*(?:\w+\s+)?nahi\s+(?:karunga|karungi|karenge|karega))\b",
    r"\b(?:mujhe\s+jeena\s+hai|apni\s+zindagi\s+se\s+pyar\s+hai)\b",
]

NATIVE_INDIC_NEGATED = [
    "ಸಾಯಲ್ಲ", "ಬದುಕಬೇಕು", "ಆತ್ಮಹತ್ಯೆ ಮಾಡಿಕೊಳ್ಳಲ್ಲ", "ಜೀವನ ಪ್ರೀತಿಸುತ್ತೇನೆ",
    "मरना नहीं चाहता", "मरना नहीं चाहती", "जीना चाहता हूँ", "जीना चाहती हूँ", "खुदकुशी नहीं करूँगा", "जीना है"
]


def detect_multilingual_crisis(text: str) -> Dict[str, Any]:
    """
    Unified high-priority crisis detection supporting English, Kannada, Kanglish, Hindi, Hinglish.
    Strictly checks negation FIRST to avoid false positives.
    """
    raw = str(text or "")
    raw_lower = raw.lower()
    norm = normalize_kanglish_tokens(text)

    # 1. Check Native Negation & Latin Negation FIRST
    for neg_kw in NATIVE_INDIC_NEGATED:
        if neg_kw in raw:
            return {
                "is_crisis": False,
                "is_imminent": False,
                "is_negated": True,
                "category": "negated_crisis",
            }

    is_negated = any(
        re.search(pat, norm) or re.search(pat, raw_lower)
        for pat in MULTILINGUAL_NEGATED_CRISIS
    )
    if is_negated:
        return {
            "is_crisis": False,
            "is_imminent": False,
            "is_negated": True,
            "category": "negated_crisis",
        }

    # 2. Check Imminent Crisis Intent
    is_imminent = any(
        re.search(pat, norm) or re.search(pat, raw_lower)
        for pat in IMMINENT_PATTERNS
    )
    if is_imminent:
        return {
            "is_crisis": True,
            "is_imminent": True,
            "is_negated": False,
            "category": "imminent",
        }

    # 3. Check Native Indic Crisis keywords
    for c_kw in NATIVE_INDIC_CRISIS:
        if c_kw in raw:
            return {
                "is_crisis": True,
                "is_imminent": False,
                "is_negated": False,
                "category": "active_crisis",
            }

    # 4. Check Latin Crisis Patterns
    is_crisis = any(
        re.search(pat, norm) or re.search(pat, raw_lower)
        for pat in MULTILINGUAL_CRISIS_PATTERNS
    )
    if is_crisis:
        return {
            "is_crisis": True,
            "is_imminent": False,
            "is_negated": False,
            "category": "active_crisis",
        }

    return {
        "is_crisis": False,
        "is_imminent": False,
        "is_negated": False,
        "category": "none",
    }
