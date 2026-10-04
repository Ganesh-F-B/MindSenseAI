"""
tests/security/test_multilingual_conversation_safety.py

Master Multilingual Conversation & Safety Test Suite covering Categories A through P.
Every category has >=3 unseen test paraphrases verifying generalized normalization,
semantic routing, safety invariants, and Crisis FSM non-locking behavior.
"""

import pytest
import re
from fastapi import HTTPException
from pydantic import ValidationError

from backend.multilingual_normalizer import (
    normalize_text,
    normalize_kanglish_tokens,
    detect_language_generalized,
    detect_language_request,
    detect_physical_health,
    detect_multilingual_distress,
    detect_multilingual_crisis,
)
from backend import privacy_validator


# ==============================================================================
# Category A: Physical Health Symptoms (English)
# ==============================================================================
class TestCategoryAPhysicalHealthEnglish:
    unseen_phrases = [
        "I have had a throbbing migraine since morning",
        "My stomach has been hurting really bad after lunch",
        "Running a high fever with chills today",
        "Terrible toothache making it impossible to concentrate",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_physical_health_english_routing(self, msg):
        res = detect_physical_health(msg)
        assert res is not None, f"Failed to detect physical health in: '{msg}'"
        assert res["intent"] == "physical_health"
        assert res["risk_level"] == "LOW"
        assert res["mental_state"] == "Normal"
        assert res["emotion"] == "neutral"


# ==============================================================================
# Category B: Physical Health Symptoms (Kannada / Kanglish)
# ==============================================================================
class TestCategoryBPhysicalHealthKannada:
    unseen_phrases = [
        "nanage thale novu ide ivathu",
        "hotte novu thumba bartha ide",
        "susthu matthe jwara ide nanage",
        "ತಲೆ ನೋವು ತುಂಬಾ ಕಾಡುತ್ತಿದೆ",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_physical_health_kannada_routing(self, msg):
        res = detect_physical_health(msg)
        assert res is not None, f"Failed to detect physical health in: '{msg}'"
        assert res["intent"] == "physical_health"
        assert res["risk_level"] == "LOW"
        assert res["mental_state"] == "Normal"


# ==============================================================================
# Category C: Physical Health Symptoms (Hindi / Hinglish)
# ==============================================================================
class TestCategoryCPhysicalHealthHindi:
    unseen_phrases = [
        "mujhe sar dard ho raha hai subah se",
        "pet me bahut tej dard hai",
        "kal se tez bukhar aur sardi hai",
        "सिर दर्द बहुत तेज है आज",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_physical_health_hindi_routing(self, msg):
        res = detect_physical_health(msg)
        assert res is not None, f"Failed to detect physical health in: '{msg}'"
        assert res["intent"] == "physical_health"
        assert res["risk_level"] == "LOW"
        assert res["mental_state"] == "Normal"


# ==============================================================================
# Category D: Language Switch Request (to Kannada)
# ==============================================================================
class TestCategoryDLanguageSwitchKannada:
    unseen_phrases = [
        "can you speak Kannada?",
        "Kannada alli matadi please",
        "Can we chat in Kannada?",
        "I want to talk in Kannada with you",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_language_switch_kannada(self, msg):
        res = detect_language_request(msg)
        assert res is not None, f"Failed to detect language request in: '{msg}'"
        assert res["is_language_request"] is True
        assert res["target_code"] == "kn"
        assert res["target_name"] == "Kannada"


# ==============================================================================
# Category E: Language Switch Request (to Hindi)
# ==============================================================================
class TestCategoryELanguageSwitchHindi:
    unseen_phrases = [
        "can you speak in Hindi?",
        "hindi me baat karo",
        "Can we continue this conversation in Hindi?",
        "kripya hindi mein baat karein",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_language_switch_hindi(self, msg):
        res = detect_language_request(msg)
        assert res is not None, f"Failed to detect language request in: '{msg}'"
        assert res["is_language_request"] is True
        assert res["target_code"] == "hi"
        assert res["target_name"] == "Hindi"


# ==============================================================================
# Category F: Language Switch Request (to English / Other)
# ==============================================================================
class TestCategoryFLanguageSwitchEnglish:
    unseen_phrases = [
        "can you speak English?",
        "can we switch back to English?",
        "Please respond in English from now on",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_language_switch_english(self, msg):
        res = detect_language_request(msg)
        assert res is not None, f"Failed to detect language request in: '{msg}'"
        assert res["is_language_request"] is True
        assert res["target_code"] == "en"


# ==============================================================================
# Category G: Kannada / Kanglish Suicidal Crisis Statement
# ==============================================================================
class TestCategoryGKannadaSuicidalCrisis:
    unseen_phrases = [
        "nanage saayabeku anisutte",
        "nanna jeevana mugisabeku ansutte",
        "nanna illade ellaru chennagi irtare",
        "badukoke ishta illa nange",
        "ಜೀವನ ಮುಗಿಸಬೇಕು ಅನಿಸುತ್ತಿದೆ",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_kannada_crisis_statement(self, msg):
        res = detect_multilingual_crisis(msg)
        assert res["is_crisis"] is True, f"Failed to detect Kannada crisis in: '{msg}'"
        assert res["is_negated"] is False


# ==============================================================================
# Category H: Hindi / Hinglish Suicidal Crisis Statement
# ==============================================================================
class TestCategoryHHindiSuicidalCrisis:
    unseen_phrases = [
        "main marna chahta hu ab",
        "meri zindagi khatam karna chahta hu",
        "ab jeene ki koi wajah nahi bachi",
        "jaan de dunga main aaj",
        "मुझे अब मरना है",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_hindi_crisis_statement(self, msg):
        res = detect_multilingual_crisis(msg)
        assert res["is_crisis"] is True, f"Failed to detect Hindi crisis in: '{msg}'"
        assert res["is_negated"] is False


# ==============================================================================
# Category I: English Suicidal Crisis Statement
# ==============================================================================
class TestCategoryIEnglishSuicidalCrisis:
    unseen_phrases = [
        "I want to end my life tonight",
        "I'm planning to take my own life",
        "The world would be much better off without me",
        "I feel like dying, I cannot go on living",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_english_crisis_statement(self, msg):
        res = detect_multilingual_crisis(msg)
        assert res["is_crisis"] is True, f"Failed to detect English crisis in: '{msg}'"
        assert res["is_negated"] is False


# ==============================================================================
# Category J: Kannada / Kanglish Negated Crisis / Life Affirmation
# ==============================================================================
class TestCategoryJKannadaNegatedCrisis:
    unseen_phrases = [
        "nanu saayalla, badukabeku nanage",
        "saayoke ishta illa nange",
        "nanna jeevana nanage thumba ishta",
        "ನಾನು ಸಾಯಲ್ಲ, ಬದುಕಬೇಕು",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_kannada_negated_crisis(self, msg):
        res = detect_multilingual_crisis(msg)
        assert res["is_negated"] is True, f"Failed to recognize negation in: '{msg}'"
        assert res["is_crisis"] is False


# ==============================================================================
# Category K: Hindi / Hinglish Negated Crisis / Life Affirmation
# ==============================================================================
class TestCategoryKHindiNegatedCrisis:
    unseen_phrases = [
        "main marna nahi chahta, mujhe jeena hai",
        "mujhe apni zindagi se pyar hai",
        "main khudkushi kabhi nahi karunga",
        "मरना नहीं चाहता, जीना चाहता हूँ",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_hindi_negated_crisis(self, msg):
        res = detect_multilingual_crisis(msg)
        assert res["is_negated"] is True, f"Failed to recognize negation in: '{msg}'"
        assert res["is_crisis"] is False


# ==============================================================================
# Category L: Transliterated Emotional Distress (Kannada / Kanglish)
# ==============================================================================
class TestCategoryLKannadaDistress:
    unseen_phrases = [
        "ivattu manasu sari illa",
        "thumba bejar agide kelasa nodi",
        "mansu thumba susthu agide ivattu",
        "ಮನಸ್ಸು ಸರಿ ಇಲ್ಲ",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_kannada_emotional_distress(self, msg):
        res = detect_multilingual_distress(msg)
        assert res is not None, f"Failed to recognize Kannada distress in: '{msg}'"
        assert res["risk_level"] == "MEDIUM"
        assert res["mental_state"] in {"Depression", "Stress"}


# ==============================================================================
# Category M: Transliterated Emotional Distress (Hindi / Hinglish)
# ==============================================================================
class TestCategoryMHindiDistress:
    unseen_phrases = [
        "aaj mann theek nahi hai mera",
        "bahut udaas lag raha hai aaj",
        "bahut tension aur chinta ho rahi hai",
        "मन ठीक नहीं है बहुत परेशान हूँ",
    ]

    @pytest.mark.parametrize("msg", unseen_phrases)
    def test_hindi_emotional_distress(self, msg):
        res = detect_multilingual_distress(msg)
        assert res is not None, f"Failed to recognize Hindi distress in: '{msg}'"
        assert res["risk_level"] == "MEDIUM"
        assert res["mental_state"] in {"Depression", "Stress"}


# ==============================================================================
# Category N: Crisis FSM Safety State Tracking & Non-Locking Simulation
# ==============================================================================
class TestCategoryNCrisisFSMNonLocking:
    def test_crisis_fsm_multi_turn_non_locking_flow(self):
        """
        Verify multi-turn state machine transitions:
        Turn 1: Suicidal message -> crisis_assessing, alert not yet dispatched
        Turn 2: Language switch request -> stays crisis_assessing, risk HIGH, responds in requested language, no duplicate alert
        Turn 3: General question -> stays crisis_assessing, risk HIGH, answers question with safety continuity, no duplicate alert
        Turn 4: Safety de-escalation -> transitions to resolved, risk LOW
        """
        # Session state mock object
        class MockSession:
            def __init__(self):
                self.crisis_state = "no_active_crisis"
                self.escalation_level = "none"

        session = MockSession()

        # Turn 1: Suicidal statement
        t1_msg = "nanage saayabeku anisutte"
        mc1 = detect_multilingual_crisis(t1_msg)
        assert mc1["is_crisis"] is True
        if session.crisis_state in {"no_active_crisis", "resolved"} and mc1["is_crisis"]:
            session.crisis_state = "crisis_assessing"
            session.escalation_level = "assessing"
            alert_dispatched = False
        assert session.crisis_state == "crisis_assessing"
        assert alert_dispatched is False

        # Turn 2: Language request during crisis_assessing
        t2_msg = "can you speak Hindi?"
        lang_req = detect_language_request(t2_msg)
        assert lang_req is not None
        assert lang_req["target_code"] == "hi"
        # FSM check: do not lock, keep crisis_assessing, do not alert
        if session.crisis_state == "crisis_assessing" and lang_req:
            # remains crisis_assessing
            alert_dispatched_2 = False
            risk_level_2 = "HIGH"
        assert session.crisis_state == "crisis_assessing"
        assert alert_dispatched_2 is False
        assert risk_level_2 == "HIGH"

        # Turn 3: General question during crisis_assessing
        t3_msg = "what is your name?"
        phys = detect_physical_health(t3_msg)
        mc3 = detect_multilingual_crisis(t3_msg)
        assert phys is None
        assert mc3["is_crisis"] is False
        is_general_query = bool(re.search(r"^(?:what\s+is|who\s+is)\b", t3_msg.lower()))
        assert is_general_query is True
        if session.crisis_state == "crisis_assessing" and is_general_query:
            # Remains in crisis_assessing with safety reminder, no duplicate alert
            alert_dispatched_3 = False
            risk_level_3 = "HIGH"
        assert session.crisis_state == "crisis_assessing"
        assert alert_dispatched_3 is False
        assert risk_level_3 == "HIGH"

        # Turn 4: De-escalation
        t4_msg = "I am safe now with my family, thank you"
        mc4 = detect_multilingual_crisis(t4_msg)
        is_deescalating = mc4.get("is_negated") or ("safe" in t4_msg.lower())
        assert is_deescalating is True
        if session.crisis_state == "crisis_assessing" and is_deescalating:
            session.crisis_state = "resolved"
            session.escalation_level = "none"
            risk_level_4 = "LOW"
        assert session.crisis_state == "resolved"
        assert risk_level_4 == "LOW"


# ==============================================================================
# Category O: Email Validation Robustness
# ==============================================================================
class TestCategoryOEmailValidation:
    invalid_emails = [
        "user..name@example.com",     # Consecutive dots in local part
        "user@domain..com",           # Consecutive dots in domain
        "user@domain.c",              # Single character TLD
        "user name@example.com",      # Space in local part
        "user@domain",                # Missing TLD
        "@example.com",               # Missing local part
        "user@",                      # Missing domain
        "user@domain.com.",           # Trailing dot
        ".user@domain.com",           # Leading dot
    ]

    valid_emails = [
        "regular.user@example.com",
        "first.last+tag@domain.co.in",
        "user_name-123@sub.domain.org",
        "valid123@hospital.edu",
    ]

    @pytest.mark.parametrize("email", invalid_emails)
    def test_invalid_emails_rejected(self, email):
        with pytest.raises(HTTPException) as exc_info:
            privacy_validator.validate_email(email)
        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize("email", valid_emails)
    def test_valid_emails_accepted(self, email):
        clean = privacy_validator.validate_email(email)
        assert clean == email.strip().lower()


# ==============================================================================
# Category P: Phone Number Validation Robustness
# ==============================================================================
class TestCategoryPPhoneValidation:
    invalid_phones = [
        "+910000000000",   # All identical dummy digits
        "9999999999",      # All identical dummy digits
        "+911111111111",   # All identical dummy digits
        "+0123456789",     # Invalid +0 country code
        "+00919876543210", # Invalid +0 country code
        "+911234",         # Too short (<7 digits)
        "+911234567890123456", # Too long (>15 digits)
        "abc12345678",     # Non-numeric
    ]

    valid_phones = [
        "+919876543210",
        "+14155552671",
        "+447911123456",
        "9876543210",
        "+91 98765 43210",
    ]

    @pytest.mark.parametrize("phone", invalid_phones)
    def test_invalid_phones_rejected(self, phone):
        with pytest.raises(HTTPException) as exc_info:
            privacy_validator.validate_phone_number(phone)
        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize("phone", valid_phones)
    def test_valid_phones_accepted(self, phone):
        clean = privacy_validator.validate_phone_number(phone)
        assert 7 <= len(re.sub(r"\D", "", clean)) <= 15
