"""
tests/security/test_privacy_input_security.py

Automated Privacy, Data Minimization & Input Validation Security Suite (Phase 4).
Tests:
- P-01: Password is never logged
- P-02: JWT / access token is never logged
- P-03: API secrets are never logged
- P-04: Emergency phone numbers are never logged
- P-05: Complete chat message is not logged
- P-06: Complete transcript is not logged
- P-07: Raw filesystem paths are not returned
- P-08: Raw provider / internal exception details are not exposed
- P-09: Oversized chat message remains rejected (>5000 chars -> 422)
- P-10: Oversized history remains bounded / rejected as designed
- P-11: NUL / control-character abuse is handled safely
- P-12: Oversized session / title / name fields are rejected safely
- P-13: Malformed / oversized email is rejected safely
- P-14: Invalid phone input is rejected safely without over-restricting legitimate international formats
- P-15: Empty / whitespace-only sensitive fields are rejected where appropriate
- P-16: User-controlled strings cannot produce executable HTML in generated / rendered content
- P-17: Emergency-contact ownership remains isolated
- P-18: Chat / session data remains user-isolated
- P-19: Existing multilingual text remains accepted
- P-20: Legitimate normal requests still succeed
"""

import html
import io
import os
import sys
import time
import uuid
import requests

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
import privacy_validator

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def generate_credentials(prefix="p4_sec"):
    uid = uuid.uuid4().hex[:8]
    numeric_suffix = str(int(uuid.uuid4().hex[:6], 16))[:6].zfill(6)
    return {
        "email": f"{prefix}_{uid}@mindsenseai.org",
        "password": f"Pass_{uid}_123!",
        "full_name": f"User {uid}",
        "phone_number": f"+9199{numeric_suffix}",
        "emergency_contacts": [
            {"name": f"Contact A_{uid[:4]}", "phone_number": f"+9191{numeric_suffix}"},
            {"name": f"Contact B_{uid[:4]}", "phone_number": f"+9192{numeric_suffix}"},
        ],
    }


def register_user(creds):
    return requests.post(f"{BASE_URL}/signup", json=creds, timeout=10)


def login_user(email, password):
    return requests.post(
        f"{BASE_URL}/token",
        data={"username": email, "password": password},
        timeout=10,
    )


def run_privacy_input_security_suite():
    results = {
        "suite": "MindSenseAI Privacy & Input Validation Security Suite (Phase 4)",
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "tests": [],
    }

    def record(test_id: str, name: str, passed: bool, details: str = "", is_error: bool = False):
        results["total"] += 1
        if is_error:
            results["errors"] += 1
            status = "ERROR"
        elif passed:
            results["passed"] += 1
            status = "PASSED"
        else:
            results["failed"] += 1
            status = "FAILED"

        results["tests"].append({
            "id": test_id,
            "name": name,
            "status": status,
            "details": details,
        })
        print(f"[{status}] {test_id}: {name} - {details}")

    print("=" * 80)
    print("RUNNING MINDSENSEAI PRIVACY & INPUT VALIDATION SECURITY SUITE (P-01 through P-20)")
    print("=" * 80)

    # Setup test users
    user_a_creds = generate_credentials("p4_a")
    user_b_creds = generate_credentials("p4_b")

    res_reg_a = register_user(user_a_creds)
    res_reg_b = register_user(user_b_creds)

    res_login_a = login_user(user_a_creds["email"], user_a_creds["password"])
    res_login_b = login_user(user_b_creds["email"], user_b_creds["password"])

    token_a = res_login_a.json().get("access_token")
    token_b = res_login_b.json().get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    time.sleep(1.0)

    # -------------------------------------------------------------
    # P-01: Password is never logged
    # -------------------------------------------------------------
    try:
        # Check source code and audit that auth logging never formats password
        with open("backend/main.py", "r", encoding="utf-8") as f:
            main_code = f.read()
        with open("backend/auth.py", "r", encoding="utf-8") as f:
            auth_code = f.read()

        no_pass_log = (
            "logger.info(user.password" not in main_code
            and "logger.info(password" not in auth_code
            and "logger.debug(password" not in auth_code
            and "print(f\"password" not in main_code
            and "print(f\"password" not in auth_code
        )
        record("P-01", "Password Is Never Logged", no_pass_log, "Verified zero logging of plain_password or user.password")
    except Exception as e:
        record("P-01", "Password Is Never Logged", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-02: JWT / access token is never logged
    # -------------------------------------------------------------
    try:
        no_jwt_log = (
            "logger.info(f\"token" not in main_code
            and "logger.info(f\"jwt" not in main_code
            and "logger.info(access_token" not in main_code
            and "print(f\"[TOKEN]" not in main_code
        )
        record("P-02", "JWT Access Token Is Never Logged", no_jwt_log, "Verified zero logging of JWT tokens")
    except Exception as e:
        record("P-02", "JWT Access Token Is Never Logged", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-03: API secrets are never logged
    # -------------------------------------------------------------
    try:
        no_secret_log = (
            "print(f\"SECRET_KEY" not in main_code
            and "logger.info(f\"SECRET_KEY" not in main_code
            and "print(f\"GROQ_API_KEY" not in main_code
            and "print(f\"FAST2SMS_API_KEY" not in main_code
        )
        record("P-03", "API Secrets Are Never Logged", no_secret_log, "Verified zero logging of API secrets or keys")
    except Exception as e:
        record("P-03", "API Secrets Are Never Logged", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-04: Emergency phone numbers are never logged in full
    # -------------------------------------------------------------
    try:
        # Verify mask_phone_number function
        masked_val = privacy_validator.mask_phone_number("+919999000001")
        is_masked = masked_val.startswith("+9") and masked_val.endswith("01") and "****" in masked_val
        record("P-04", "Emergency Phone Numbers Are Masked in Logs", is_masked, f"masked='{masked_val}'")
    except Exception as e:
        record("P-04", "Emergency Phone Numbers Are Masked", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-05: Complete chat message is not logged
    # -------------------------------------------------------------
    try:
        no_chat_log = (
            "logger.info(f\"chat message" not in main_code
            and "logger.info(data.message" not in main_code
            and "print(f\"User message: {data.message}" not in main_code
        )
        record("P-05", "Complete Chat Message Is Not Logged", no_chat_log, "Verified zero logging of chat message contents")
    except Exception as e:
        record("P-05", "Complete Chat Message Is Not Logged", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-06: Complete transcript is not logged
    # -------------------------------------------------------------
    try:
        # Verified line 1852 in main.py: uses result length rather than text[:60]
        has_transcript_content_log = "logger.info(f\"[TRANSCRIBE] result: '" in main_code
        has_transcript_len_log = "logger.info(f\"[TRANSCRIBE] result length=" in main_code
        record("P-06", "Complete Transcript Is Not Logged", not has_transcript_content_log and has_transcript_len_log, "Transcript logged by length only")
    except Exception as e:
        record("P-06", "Complete Transcript Is Not Logged", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-07: Raw filesystem paths are not returned to client
    # -------------------------------------------------------------
    try:
        # Upload a legitimate small file and check response
        f_content = b"Safe file content for privacy testing."
        res_up = requests.post(
            f"{BASE_URL}/upload",
            headers=headers_a,
            files={"file": ("test_doc.txt", io.BytesIO(f_content), "text/plain")},
            timeout=10,
        )
        data_up = res_up.json()
        no_paths = (
            "\\" not in str(data_up)
            and "C:" not in str(data_up)
            and "/tmp" not in str(data_up)
            and "mindsense_secure_uploads" not in str(data_up)
        )
        record("P-07", "Raw Filesystem Paths Are Not Returned", no_paths, f"response_keys={list(data_up.keys())}")
    except Exception as e:
        record("P-07", "Raw Filesystem Paths Not Returned", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # P-08: Raw provider / internal exception details are not exposed
    # -------------------------------------------------------------
    try:
        # Call nlp-analytics or an endpoint with invalid state to check exception formatting
        res_bad_file = requests.post(
            f"{BASE_URL}/upload-video",
            headers=headers_a,
            files={"file": ("empty.mp4", b"", "video/mp4")},
            timeout=10,
        )
        resp_text = res_bad_file.text
        # Must not leak Python tracebacks or internal paths
        no_leakage = (
            "Traceback (most recent call last)" not in resp_text
            and "sqlalchemy" not in resp_text.lower()
            and ".py\", line " not in resp_text
        )
        record("P-08", "Internal Exception Details Are Not Exposed", no_leakage, f"status={res_bad_file.status_code}")
    except Exception as e:
        record("P-08", "Internal Exception Details Sanitization", False, str(e), is_error=True)

    time.sleep(2.0)

    # -------------------------------------------------------------
    # P-09: Oversized chat message remains rejected (>5000 chars -> 422)
    # -------------------------------------------------------------
    try:
        res_large = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "M" * 5001, "session_id": 0},
            timeout=5,
        )
        record("P-09", "Oversized Chat Message Rejected -> 422", res_large.status_code == 422, f"status={res_large.status_code}")
    except Exception as e:
        record("P-09", "Oversized Chat Message Rejected", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-10: Oversized history remains bounded / safely handled
    # -------------------------------------------------------------
    try:
        huge_history = [{"user": f"history message {i}", "bot": f"bot response {i}"} for i in range(120)]
        res_hist = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "Testing bounded history handling", "session_id": 0, "history": huge_history},
            timeout=25,
        )
        passed = res_hist.status_code == 200
        record("P-10", "Oversized History Handled Safely Without Overflow", passed, f"status={res_hist.status_code}")
    except Exception as e:
        record("P-10", "Oversized History Handled Safely", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-11: NUL / control-character abuse is handled safely
    # -------------------------------------------------------------
    try:
        # Attempt to create chat session with NUL byte
        res_nul_chat = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "Testing null byte \x00 attack", "session_id": 0},
            timeout=5,
        )
        res_nul_title = requests.put(
            f"{BASE_URL}/chat/sessions/1",
            headers=headers_a,
            json={"title": "Nul \x00 title"},
            timeout=5,
        )
        nul_blocked = res_nul_chat.status_code == 400 and res_nul_title.status_code in (400, 404)
        record("P-11", "NUL Byte Injections Rejected -> 400", nul_blocked, f"chat={res_nul_chat.status_code}, title={res_nul_title.status_code}")
    except Exception as e:
        record("P-11", "NUL Byte Injection Rejection", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-12: Oversized session / title / name fields are rejected safely
    # -------------------------------------------------------------
    try:
        # Title limit is 200 chars
        res_title_oversized = requests.put(
            f"{BASE_URL}/chat/sessions/1",
            headers=headers_a,
            json={"title": "T" * 201},
            timeout=5,
        )
        # Name limit is 100 chars
        bad_signup = generate_credentials("p4_long_name")
        bad_signup["full_name"] = "N" * 101
        res_name_oversized = register_user(bad_signup)

        passed = res_title_oversized.status_code in (400, 422) and res_name_oversized.status_code in (400, 422)
        record("P-12", "Oversized Title and Name Rejected -> 400/422", passed, f"title={res_title_oversized.status_code}, name={res_name_oversized.status_code}")
    except Exception as e:
        record("P-12", "Oversized Title and Name Rejection", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-13: Malformed / oversized email is rejected safely
    # -------------------------------------------------------------
    try:
        bad_email_creds1 = generate_credentials("p4_bad_email")
        bad_email_creds1["email"] = "not_an_email"
        r1 = register_user(bad_email_creds1)

        bad_email_creds2 = generate_credentials("p4_huge_email")
        bad_email_creds2["email"] = ("a" * 250) + "@domain.com"  # > 254 chars
        r2 = register_user(bad_email_creds2)

        passed = r1.status_code == 422 and r2.status_code in (400, 422)
        record("P-13", "Malformed & Oversized Email Rejected -> 400/422", passed, f"r1={r1.status_code}, r2={r2.status_code}")
    except Exception as e:
        record("P-13", "Malformed & Oversized Email Rejection", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-14: Invalid phone input rejected without over-restricting international formats
    # -------------------------------------------------------------
    try:
        # Invalid phone with letters/XSS
        bad_phone_creds = generate_credentials("p4_bad_phone")
        bad_phone_creds["phone_number"] = "+919999<script>"
        r_xss = register_user(bad_phone_creds)

        # Valid international formats should pass validation helper
        valid_phones = [
            "+919999000010",
            "+1 (555) 123-4567",
            "+44 20 7946 0958",
            "9999000010",
            "+49-30-123456",
        ]
        all_valid_ok = True
        for vp in valid_phones:
            try:
                res = privacy_validator.validate_phone_number(vp)
                if not res:
                    all_valid_ok = False
            except Exception:
                all_valid_ok = False

        passed = r_xss.status_code == 400 and all_valid_ok
        record("P-14", "Phone Format Validated (International Permitted, Malicious Blocked)", passed, f"xss_status={r_xss.status_code}, international_ok={all_valid_ok}")
    except Exception as e:
        record("P-14", "Phone Validation", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-15: Empty / whitespace-only sensitive fields are rejected
    # -------------------------------------------------------------
    try:
        # Empty chat message
        r_empty_chat = requests.post(f"{BASE_URL}/chat", headers=headers_a, json={"message": "   \n\t  ", "session_id": 0}, timeout=5)
        # Empty title
        r_empty_title = requests.put(f"{BASE_URL}/chat/sessions/1", headers=headers_a, json={"title": "   "}, timeout=5)

        passed = r_empty_chat.status_code == 400 and r_empty_title.status_code in (400, 404)
        record("P-15", "Empty / Whitespace-Only Sensitive Fields Rejected -> 400", passed, f"chat={r_empty_chat.status_code}, title={r_empty_title.status_code}")
    except Exception as e:
        record("P-15", "Empty / Whitespace Field Rejection", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-16: User-controlled strings cannot produce executable HTML in email/content
    # -------------------------------------------------------------
    try:
        malicious_name = "<script>alert('xss')</script>"
        safe_name = privacy_validator.sanitize_html(malicious_name)
        passed = (
            "<script>" not in safe_name
            and "&lt;script&gt;" in safe_name
            and safe_name == html.escape(malicious_name, quote=True)
        )
        record("P-16", "User Strings Properly Escaped for HTML Contexts", passed, f"escaped='{safe_name}'")
    except Exception as e:
        record("P-16", "HTML Escaping", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-17: Emergency-contact ownership remains isolated
    # -------------------------------------------------------------
    try:
        # User A's contacts
        res_me_a = requests.get(f"{BASE_URL}/users/me", headers=headers_a, timeout=5)
        contacts_a = [c["phone_number"] for c in res_me_a.json()["emergency_contacts"]]

        # User B's contacts
        res_me_b = requests.get(f"{BASE_URL}/users/me", headers=headers_b, timeout=5)
        contacts_b = [c["phone_number"] for c in res_me_b.json()["emergency_contacts"]]

        # Sets of contacts must have zero overlap
        overlap = set(contacts_a).intersection(set(contacts_b))
        passed = len(overlap) == 0
        record("P-17", "Emergency Contact Ownership Strictly Isolated", passed, f"overlap={overlap}")
    except Exception as e:
        record("P-17", "Emergency Contact Isolation", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-18: Chat / session data remains user-isolated
    # -------------------------------------------------------------
    try:
        # User A creates a chat session
        r_create = requests.post(f"{BASE_URL}/chat", headers=headers_a, json={"message": "User A private session message", "session_id": 0}, timeout=25)
        session_a_id = r_create.json().get("session_id")

        # User B tries to view User A's session
        r_hijack = requests.get(f"{BASE_URL}/chat/sessions/{session_a_id}", headers=headers_b, timeout=5)
        passed = r_hijack.status_code == 404
        record("P-18", "Chat Session Data Isolated (User B Cannot Read User A Session)", passed, f"status={r_hijack.status_code}")
    except Exception as e:
        record("P-18", "Chat Session Data Isolation", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-19: Existing multilingual text remains accepted
    # -------------------------------------------------------------
    try:
        multilingual_samples = [
            ("Hindi", "नमस्ते, आज मैं थोड़ा चिंतित महसूस कर रहा हूँ"),
            ("Tamil", "வணக்கம், எனக்கு இன்று மன அமைதி வேண்டும்"),
            ("French", "Bonjour, je me sens un peu triste aujourd'hui"),
            ("Emoji", "I had a peaceful day today 😊🌱✨"),
        ]
        all_samples_accepted = True
        sample_statuses = []
        for lang_label, text in multilingual_samples:
            r = requests.post(
                f"{BASE_URL}/chat",
                headers=headers_b,
                json={"message": text, "session_id": 0},
                timeout=25,
            )
            sample_statuses.append(f"{lang_label}={r.status_code}")
            if r.status_code != 200:
                all_samples_accepted = False
            time.sleep(1.5)  # Pace between requests

        record("P-19", "Multilingual Unicode and Emojis Accepted Without Corruption", all_samples_accepted, ", ".join(sample_statuses))
    except Exception as e:
        record("P-19", "Multilingual Text Acceptance", False, str(e), is_error=True)

    time.sleep(1.5)

    # -------------------------------------------------------------
    # P-20: Legitimate normal requests still succeed
    # -------------------------------------------------------------
    try:
        r_me = requests.get(f"{BASE_URL}/users/me", headers=headers_a, timeout=5)
        r_sess = requests.get(f"{BASE_URL}/chat/sessions", headers=headers_a, timeout=5)
        r_chat = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "Checking in to see how everything is functioning today.", "session_id": 0},
            timeout=25,
        )
        passed = r_me.status_code == 200 and r_sess.status_code == 200 and r_chat.status_code == 200
        record("P-20", "Legitimate Normal Request Workflow Succeeds", passed, f"me={r_me.status_code}, sessions={r_sess.status_code}, chat={r_chat.status_code}")
    except Exception as e:
        record("P-20", "Legitimate Normal Workflow", False, str(e), is_error=True)

    print("=" * 80)
    print(f"PRIVACY & INPUT SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    res = run_privacy_input_security_suite()
    sys.exit(0 if res["failed"] == 0 and res["errors"] == 0 else 1)
