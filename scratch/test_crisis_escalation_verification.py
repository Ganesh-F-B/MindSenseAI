import os
import sys
import unittest
from datetime import datetime, timedelta

# Add project root and backend to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(1, PROJECT_ROOT)

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
import schemas
from database import Base, get_db
import main


class TestCrisisEscalation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy.pool import StaticPool

        # Setup isolated in-memory SQLite database sharing the same memory pool
        cls.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.test_engine
        )
        models.Base.metadata.create_all(bind=cls.test_engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db

        # Track active user id for get_current_user override
        cls.current_user_id = 1

        def override_get_current_user(db = Depends(get_db)):
            if cls.current_user_id:
                return db.query(models.User).filter_by(id=cls.current_user_id).first()
            return None

        main.app.dependency_overrides[main.get_current_user] = override_get_current_user

        cls.client = TestClient(main.app)

        # Mock notification dispatchers to capture calls without external network I/O
        cls.dispatched_alerts = []

        def mock_whatsapp(phone_numbers, alert_text):
            cls.dispatched_alerts.append({
                "channel": "whatsapp",
                "phone_numbers": phone_numbers,
                "text": alert_text,
            })
            return True

        def mock_sms(phone_numbers, alert_text):
            cls.dispatched_alerts.append({
                "channel": "sms",
                "phone_numbers": phone_numbers,
                "text": alert_text,
            })
            return True

        def mock_email(user_email, user_name, contacts):
            cls.dispatched_alerts.append({
                "channel": "email",
                "user_email": user_email,
                "contacts": [c.phone_number for c in contacts],
            })
            return True

        main.send_whatsapp_greenapi = mock_whatsapp
        main.send_sms_android_gateway = mock_sms
        main.send_emergency_email = mock_email

    def setUp(self):
        self.dispatched_alerts.clear()
        main._last_alert_time.clear()

        # Create isolated test users
        db = self.TestingSessionLocal()
        db.query(models.EmergencyContact).delete()
        db.query(models.ChatHistory).delete()
        db.query(models.ChatSession).delete()
        db.query(models.User).delete()
        db.commit()

        # User A with 2 contacts
        user_a = models.User(
            id=1,
            email="user_a@test.local",
            hashed_password="pw",
            full_name="User Alpha",
            phone_number="+919800000001",
        )
        # User B with 1 contact
        user_b = models.User(
            id=2,
            email="user_b@test.local",
            hashed_password="pw",
            full_name="User Beta",
            phone_number="+919800000002",
        )
        # User C with NO contacts
        user_c = models.User(
            id=3,
            email="user_c@test.local",
            hashed_password="pw",
            full_name="User Gamma",
            phone_number="+919800000003",
        )
        db.add_all([user_a, user_b, user_c])
        db.commit()

        contact_a1 = models.EmergencyContact(
            id=1, user_id=1, name="Contact_A1", phone_number="+919811111111"
        )
        contact_a2 = models.EmergencyContact(
            id=2, user_id=1, name="Contact_A2", phone_number="+919822222222"
        )
        contact_b1 = models.EmergencyContact(
            id=3, user_id=2, name="Contact_B1", phone_number="+919833333333"
        )
        db.add_all([contact_a1, contact_a2, contact_b1])
        db.commit()
        db.close()

    # --------------------------------------------------------------------------
    # GROUP A: First Crisis Statement (Case A: e.g. "I feel like dying")
    # --------------------------------------------------------------------------
    def test_group_a_first_crisis_statement(self):
        """Case A: First crisis statement enters CRISIS_ASSESSING with NO emergency dispatch."""
        self.__class__.current_user_id = 1

        res = self.client.post("/chat", json={"message": "i feel like dying"})
        self.assertEqual(res.status_code, 200)
        data = res.json()

        session_id = data["session_id"]
        self.assertEqual(data["crisis_state"], "crisis_assessing")
        self.assertEqual(data["analysis"]["risk_level"], "HIGH")

        # Response must contain supportive inquiry
        self.assertIn("safe place", data["reply"].lower())
        # Response must include helpline info
        self.assertTrue("Tele-MANAS" in data["reply"] or "988" in data["reply"])

        # CRITICAL ASSERTION: Zero notifications dispatched on first crisis statement!
        self.assertEqual(len(self.dispatched_alerts), 0)

        # Verify DB session state
        db = self.TestingSessionLocal()
        session = db.query(models.ChatSession).filter_by(id=session_id).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.crisis_state, "crisis_assessing")
        self.assertEqual(session.escalation_level, "assessing")
        self.assertIsNone(session.last_alert_at)
        db.close()

    # --------------------------------------------------------------------------
    # GROUP B: De-escalation & Safety Reassurance (Case B)
    # --------------------------------------------------------------------------
    def test_group_b_deescalation_reassurance(self):
        """Case B: In CRISIS_ASSESSING, user confirms safety/negation -> transitions to RESOLVED, NO dispatch."""
        deescalation_cases = [
            "i will not die",
            "i am safe right now",
            "i want things to get better",
            "please don't send anyone",
            "no i am safe",
        ]

        for reassurance_msg in deescalation_cases:
            self.dispatched_alerts.clear()
            self.__class__.current_user_id = 1

            # Turn 1: Trigger assessment
            r1 = self.client.post("/chat", json={"message": "i feel like dying"})
            sid = r1.json()["session_id"]
            self.assertEqual(r1.json()["crisis_state"], "crisis_assessing")
            self.assertEqual(len(self.dispatched_alerts), 0)

            # Turn 2: Provide reassurance / de-escalation
            r2 = self.client.post("/chat", json={"message": reassurance_msg, "session_id": sid})
            self.assertEqual(r2.status_code, 200)
            data2 = r2.json()

            # Assert state transitioned to resolved
            self.assertEqual(data2["crisis_state"], "resolved")
            self.assertEqual(data2["analysis"]["risk_level"], "LOW")
            self.assertIn("glad to hear that you are safe", data2["reply"].lower())

            # CRITICAL ASSERTION: NO emergency dispatch on de-escalation!
            self.assertEqual(len(self.dispatched_alerts), 0)

            # Verify DB session state
            db = self.TestingSessionLocal()
            session = db.query(models.ChatSession).filter_by(id=sid).first()
            self.assertEqual(session.crisis_state, "resolved")
            self.assertEqual(session.escalation_level, "none")
            db.close()

    # --------------------------------------------------------------------------
    # GROUP C: Persistent Crisis & Support Rejection (Case C)
    # --------------------------------------------------------------------------
    def test_group_c_persistent_crisis_escalation(self):
        """Case C: In CRISIS_ASSESSING, user rejects support or reinforces crisis -> ESCALATED, dispatch alerts."""
        rejection_cases = [
            "no i am not safe",
            "i still feel like dying",
            "leave me alone, i cannot go on",
        ]

        for reject_msg in rejection_cases:
            self.dispatched_alerts.clear()
            main._last_alert_time.clear()
            self.__class__.current_user_id = 1

            # Turn 1: Enter assessment
            r1 = self.client.post("/chat", json={"message": "i feel like dying"})
            sid = r1.json()["session_id"]
            self.assertEqual(len(self.dispatched_alerts), 0)

            # Turn 2: Reinforce distress / reject safety
            r2 = self.client.post("/chat", json={"message": reject_msg, "session_id": sid})
            self.assertEqual(r2.status_code, 200)
            data2 = r2.json()

            # Assert transitioned to escalated
            self.assertEqual(data2["crisis_state"], "escalated")
            self.assertEqual(data2["analysis"]["risk_level"], "HIGH")

            # CRITICAL ASSERTION: Emergency alerts dispatched!
            self.assertGreater(len(self.dispatched_alerts), 0)

            # Dispatched strictly to User A's contacts (+919811111111, +919822222222)
            whatsapp_alerts = [a for a in self.dispatched_alerts if a["channel"] == "whatsapp"]
            self.assertEqual(len(whatsapp_alerts), 1)
            self.assertIn("+919811111111", whatsapp_alerts[0]["phone_numbers"])
            self.assertIn("+919822222222", whatsapp_alerts[0]["phone_numbers"])
            self.assertNotIn("+919833333333", whatsapp_alerts[0]["phone_numbers"])

            # Verify DB session state
            db = self.TestingSessionLocal()
            session = db.query(models.ChatSession).filter_by(id=sid).first()
            self.assertEqual(session.crisis_state, "escalated")
            self.assertEqual(session.escalation_level, "escalated")
            self.assertIsNotNone(session.last_alert_at)
            db.close()

    # --------------------------------------------------------------------------
    # GROUP D: Clear Imminent Intent Bypass (Case D)
    # --------------------------------------------------------------------------
    def test_group_d_imminent_intent_bypass(self):
        """Case D: Immediate explicit intent bypasses assessment, dispatches alert immediately."""
        imminent_cases = [
            "i am going to hurt myself right now",
            "i have the pills and i am taking them right now",
            "i am about to jump",
        ]

        for imm_msg in imminent_cases:
            self.dispatched_alerts.clear()
            main._last_alert_time.clear()
            self.__class__.current_user_id = 1

            res = self.client.post("/chat", json={"message": imm_msg})
            self.assertEqual(res.status_code, 200)
            data = res.json()

            # Assert immediately escalated with imminent level
            self.assertEqual(data["crisis_state"], "escalated")
            self.assertEqual(data["analysis"]["risk_level"], "HIGH")

            # Alert dispatched immediately on Turn 1!
            self.assertGreater(len(self.dispatched_alerts), 0)
            whatsapp_alerts = [a for a in self.dispatched_alerts if a["channel"] == "whatsapp"]
            self.assertEqual(len(whatsapp_alerts), 1)
            self.assertIn("IMMEDIATE CRISIS ALERT", whatsapp_alerts[0]["text"])

            # Verify DB
            db = self.TestingSessionLocal()
            session = db.query(models.ChatSession).filter_by(id=data["session_id"]).first()
            self.assertEqual(session.crisis_state, "escalated")
            self.assertEqual(session.escalation_level, "imminent")
            self.assertIsNotNone(session.last_alert_at)
            db.close()

    # --------------------------------------------------------------------------
    # GROUP E: Historical Crisis Context (Case E)
    # --------------------------------------------------------------------------
    def test_group_e_historical_crisis_context(self):
        """Case E: Historical/past crisis statements with coping are acknowledged supportively without crisis entry or dispatch."""
        historical_cases = [
            "i felt like dying earlier today, but i am better now",
            "i had suicidal thoughts last year, but i am doing well now",
            "used to be suicidal, but now things are under control",
        ]

        for hist_msg in historical_cases:
            self.dispatched_alerts.clear()
            self.__class__.current_user_id = 1

            res = self.client.post("/chat", json={"message": hist_msg})
            self.assertEqual(res.status_code, 200)
            data = res.json()

            self.assertEqual(data["crisis_state"], "no_active_crisis")
            self.assertEqual(data["analysis"]["risk_level"], "LOW")
            self.assertIn("better now", data["reply"].lower())

            # CRITICAL ASSERTION: Zero alerts dispatched!
            self.assertEqual(len(self.dispatched_alerts), 0)

            # DB remains no_active_crisis
            db = self.TestingSessionLocal()
            session = db.query(models.ChatSession).filter_by(id=data["session_id"]).first()
            self.assertIsNotNone(session)
            self.assertEqual(session.crisis_state, "no_active_crisis")
            self.assertEqual(session.escalation_level, "none")
            self.assertIsNone(session.last_alert_at)
            db.close()

    # --------------------------------------------------------------------------
    # GROUP F: Cooldown Protection & Higher-Risk Elevation
    # --------------------------------------------------------------------------
    def test_group_f_cooldown_and_elevation(self):
        """Case F: Duplicate alerts of same level suppressed within cooldown; higher-risk imminent overrides cooldown."""
        self.__class__.current_user_id = 1

        # Turn 1: Enter assessment
        r1 = self.client.post("/chat", json={"message": "i feel like dying"})
        sid = r1.json()["session_id"]
        self.assertEqual(len(self.dispatched_alerts), 0)

        # Turn 2: Escalate (first alert dispatched)
        r2 = self.client.post("/chat", json={"message": "no i am not safe", "session_id": sid})
        self.assertEqual(r2.json()["crisis_state"], "escalated")
        count_after_escalate = len(self.dispatched_alerts)
        self.assertGreater(count_after_escalate, 0)

        # Turn 3: User sends another escalated message 2 minutes later -> duplicate alert suppressed by cooldown
        r3 = self.client.post("/chat", json={"message": "i am still feeling awful and suicidal", "session_id": sid})
        self.assertEqual(r3.json()["crisis_state"], "escalated")
        # Assert NO additional alerts dispatched
        self.assertEqual(len(self.dispatched_alerts), count_after_escalate)

        # Turn 4: User states IMMINENT intent -> higher-risk elevation OVERRIDES cooldown!
        r4 = self.client.post("/chat", json={"message": "i am going to kill myself right now", "session_id": sid})
        self.assertEqual(r4.json()["crisis_state"], "escalated")
        self.assertGreater(len(self.dispatched_alerts), count_after_escalate)

        # Verify last alert is imminent
        imminent_alerts = [a for a in self.dispatched_alerts if a["channel"] == "whatsapp" and "IMMEDIATE CRISIS ALERT" in a["text"]]
        self.assertEqual(len(imminent_alerts), 1)

    # --------------------------------------------------------------------------
    # GROUP G: Emergency Contact Isolation & Ownership
    # --------------------------------------------------------------------------
    def test_group_g_contact_isolation_and_ownership(self):
        """Case G: Contacts are strictly partitioned by authenticated user_id; users with no contacts fail gracefully."""
        # 1. User A escalation
        self.__class__.current_user_id = 1
        self.dispatched_alerts.clear()

        # Direct imminent bypass
        self.client.post("/chat", json={"message": "i am going to kill myself right now"})
        a_contacts = [a["phone_numbers"] for a in self.dispatched_alerts if "phone_numbers" in a]
        for phones in a_contacts:
            self.assertIn("+919811111111", phones)
            self.assertIn("+919822222222", phones)
            self.assertNotIn("+919833333333", phones)

        # 2. User B escalation
        self.__class__.current_user_id = 2
        self.dispatched_alerts.clear()

        self.client.post("/chat", json={"message": "i am going to kill myself right now"})
        b_contacts = [a["phone_numbers"] for a in self.dispatched_alerts if "phone_numbers" in a]
        for phones in b_contacts:
            self.assertIn("+919833333333", phones)
            self.assertNotIn("+919811111111", phones)
            self.assertNotIn("+919822222222", phones)

        # 3. User C (NO contacts configured)
        self.__class__.current_user_id = 3
        self.dispatched_alerts.clear()

        res_c = self.client.post("/chat", json={"message": "i am going to kill myself right now"})
        self.assertEqual(res_c.status_code, 200)
        # Zero notifications dispatched, no crash, no leak
        self.assertEqual(len(self.dispatched_alerts), 0)

    # --------------------------------------------------------------------------
    # GROUP H: Session Ownership & Cross-User Security Enforcement
    # --------------------------------------------------------------------------
    def test_group_h_session_ownership_enforcement(self):
        """Case H: Users cannot access or hijack another user's session_id; rejected with 403 Forbidden."""
        # User A creates a session
        self.__class__.current_user_id = 1
        r1 = self.client.post("/chat", json={"message": "hello"})
        session_a_id = r1.json()["session_id"]
        self.assertGreater(session_a_id, 0)

        # User B attempts to send a message to User A's session
        self.__class__.current_user_id = 2
        r2 = self.client.post("/chat", json={"message": "trying to hijack session", "session_id": session_a_id})

        # MUST be rejected with HTTP 403 Forbidden!
        self.assertEqual(r2.status_code, 403)
        self.assertIn("Access denied", r2.json()["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
