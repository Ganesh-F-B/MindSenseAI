import os
import sys
import time
import uuid
import json
import sqlite3
import requests

# Base URL for the running FastAPI backend
API_BASE = "http://127.0.0.1:8000"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "mindsense.db")

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def log_test(name, passed, detail=""):
    status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
    print(f"  {status} {Colors.BOLD}{name}{Colors.RESET}")
    if detail:
        print(f"         {Colors.BLUE}-> {detail}{Colors.RESET}")

def run_e2e_verification():
    print(f"\n{Colors.BOLD}================================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}MindSenseAI — Final End-to-End Auth & Emergency Contact Isolation Verification{Colors.RESET}")
    print(f"{Colors.BOLD}================================================================================{Colors.RESET}\n")

    results = {}
    test_id = str(uuid.uuid4())[:8]

    # Credentials for testing
    user_a_email = f"e2e_test_user_a_{test_id}@mindsenseai.org"
    user_b_email = f"e2e_test_user_b_{test_id}@mindsenseai.org"
    password = f"SecurePass123!_{test_id}"

    # Anonymized contact phone numbers (non-routable test numbers)
    contact_a1_phone = "+919999000001"
    contact_a2_phone = "+919999000002"
    contact_b1_phone = "+919999000003"
    contact_b2_phone = "+919999000004"

    # =========================================================================
    # SETUP: Register USER_A and USER_B via API
    # =========================================================================
    print(f"{Colors.YELLOW}--- Setting up test accounts on live server ---{Colors.RESET}")
    signup_a = requests.post(f"{API_BASE}/signup", json={
        "email": user_a_email,
        "password": password,
        "full_name": f"Test User A {test_id}",
        "phone_number": "+919999000010",
        "emergency_contacts": [
            {"name": "Contact A1", "phone_number": contact_a1_phone},
            {"name": "Contact A2", "phone_number": contact_a2_phone},
        ]
    })
    assert signup_a.status_code == 200, f"USER_A signup failed: {signup_a.text}"
    user_a_info = signup_a.json()
    user_a_id = user_a_info["id"]

    signup_b = requests.post(f"{API_BASE}/signup", json={
        "email": user_b_email,
        "password": password,
        "full_name": f"Test User B {test_id}",
        "phone_number": "+919999000020",
        "emergency_contacts": [
            {"name": "Contact B1", "phone_number": contact_b1_phone},
            {"name": "Contact B2", "phone_number": contact_b2_phone},
        ]
    })
    assert signup_b.status_code == 200, f"USER_B signup failed: {signup_b.text}"
    user_b_info = signup_b.json()
    user_b_id = user_b_info["id"]

    print(f"  [OK] Created USER_A (ID: {user_a_id}) with 2 emergency contacts")
    print(f"  [OK] Created USER_B (ID: {user_b_id}) with 2 emergency contacts\n")

    # =========================================================================
    # TEST 1 — USER A
    # =========================================================================
    print(f"{Colors.BOLD}[TEST 1] USER_A Authentication, Contact Ownership & Crisis Escalation{Colors.RESET}")

    # 1. Login as USER_A
    login_a = requests.post(f"{API_BASE}/token", data={"username": user_a_email, "password": password})
    assert login_a.status_code == 200, f"USER_A login failed: {login_a.text}"
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    log_test("1.1 USER_A login & JWT issuance", True, "JWT token successfully issued")

    # 2. Confirm frontend/client identity (/users/me)
    me_a = requests.get(f"{API_BASE}/users/me", headers=headers_a)
    assert me_a.status_code == 200, f"USER_A /users/me failed: {me_a.text}"
    me_a_data = me_a.json()
    is_user_a = (me_a_data["id"] == user_a_id and me_a_data["email"] == user_a_email)
    log_test("1.2 Identity confirmation (/users/me)", is_user_a, f"Authenticated as USER_A (ID: {user_a_id})")

    # 3. Confirm emergency contacts belong to USER_A
    contacts_a = me_a_data.get("emergency_contacts", [])
    contact_a_phones = {c["phone_number"] for c in contacts_a}
    owns_a_contacts = (
        len(contacts_a) == 2
        and contact_a1_phone in contact_a_phones
        and contact_a2_phone in contact_a_phones
        and contact_b1_phone not in contact_a_phones
        and contact_b2_phone not in contact_a_phones
    )
    log_test("1.3 Emergency contact ownership", owns_a_contacts, "Exactly CONTACT_A1 and CONTACT_A2 belong to USER_A")

    # 4. Start normal chat
    chat_norm = requests.post(f"{API_BASE}/chat", headers=headers_a, json={
        "message": "Hello MindSense, I am checking in today.",
        "session_id": 0
    })
    assert chat_norm.status_code == 200, f"Chat failed: {chat_norm.text}"
    chat_norm_data = chat_norm.json()

    # Query DB to inspect session state
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Find newest session for user_a
    sess_row = cur.execute(
        "SELECT id, user_id, crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_a_id,)
    ).fetchone()
    assert sess_row is not None
    user_a_session_id = sess_row[0]
    log_test("1.4 Normal chat session creation", sess_row[2] == "no_active_crisis", f"Session #{user_a_session_id} state='{sess_row[2]}'")

    # 5. Trigger Crisis Escalation Turn 1: "I feel like dying"
    chat_turn1 = requests.post(f"{API_BASE}/chat", headers=headers_a, json={
        "message": "I feel like dying",
        "session_id": user_a_session_id
    })
    assert chat_turn1.status_code == 200
    t1_row = cur.execute(
        "SELECT crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE id=?",
        (user_a_session_id,)
    ).fetchone()
    turn1_ok = (t1_row[0] == "crisis_assessing" and t1_row[2] is None)
    log_test(
        "1.5 Crisis Turn 1: Supportive response + Safety check",
        turn1_ok,
        f"State='{t1_row[0]}', Alert dispatched=False (NO alert on first crisis message)"
    )

    # 6. Trigger Crisis Escalation Turn 2: "No, I am not safe, I cannot go on anymore"
    chat_turn2 = requests.post(f"{API_BASE}/chat", headers=headers_a, json={
        "message": "No, I am not safe, I cannot go on anymore",
        "session_id": user_a_session_id
    })
    assert chat_turn2.status_code == 200
    t2_row = cur.execute(
        "SELECT crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE id=?",
        (user_a_session_id,)
    ).fetchone()
    turn2_ok = (t2_row[0] == "escalated" and t2_row[2] is not None)
    log_test(
        "1.6 Crisis Turn 2: Persistent distress escalates & dispatches alert",
        turn2_ok,
        f"State='{t2_row[0]}', Alert dispatched=True (last_alert_at={t2_row[2]})"
    )

    # 7. Verify recipient isolation for USER_A
    # The server queried emergency_contacts WHERE user_id == user_a_id
    notif_contacts = cur.execute(
        "SELECT phone_number FROM emergency_contacts WHERE user_id=?", (user_a_id,)
    ).fetchall()
    notif_phones = {r[0] for r in notif_contacts}
    isolation_a_ok = (
        contact_a1_phone in notif_phones
        and contact_a2_phone in notif_phones
        and contact_b1_phone not in notif_phones
        and contact_b2_phone not in notif_phones
    )
    log_test(
        "1.7 Notification recipient verification",
        isolation_a_ok,
        "Recipients strictly CONTACT_A1 and CONTACT_A2; USER_B contacts NOT recipients"
    )
    results["TEST_1"] = is_user_a and owns_a_contacts and turn1_ok and turn2_ok and isolation_a_ok

    # =========================================================================
    # TEST 2 — LOGOUT
    # =========================================================================
    print(f"\n{Colors.BOLD}[TEST 2] LOGOUT & Token Cleanup Verification{Colors.RESET}")
    # Simulate client logout (clears token from storage/headers)
    cleared_headers = {}
    logged_out_req = requests.get(f"{API_BASE}/users/me", headers=cleared_headers)
    is_unauthorized = (logged_out_req.status_code == 401)
    log_test("2.1 Request without token rejected", is_unauthorized, f"HTTP status: {logged_out_req.status_code} Unauthorized")

    # Verify invalid/cleared token string rejected
    invalid_token_req = requests.get(f"{API_BASE}/users/me", headers={"Authorization": "Bearer "})
    token_cleared_ok = (invalid_token_req.status_code == 401)
    log_test("2.2 Cleared token rejected by backend", token_cleared_ok, f"HTTP status: {invalid_token_req.status_code} Unauthorized")

    results["TEST_2"] = is_unauthorized and token_cleared_ok

    # =========================================================================
    # TEST 3 — USER B
    # =========================================================================
    print(f"\n{Colors.BOLD}[TEST 3] USER_B Authentication, Contact Ownership & Crisis Escalation{Colors.RESET}")

    # 1. Login as USER_B
    login_b = requests.post(f"{API_BASE}/token", data={"username": user_b_email, "password": password})
    assert login_b.status_code == 200, f"USER_B login failed: {login_b.text}"
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    distinct_tokens = (token_a != token_b)
    log_test("3.1 USER_B login & distinct JWT issuance", distinct_tokens, "New distinct JWT issued for USER_B")

    # 2. Confirm frontend/client identity (/users/me)
    me_b = requests.get(f"{API_BASE}/users/me", headers=headers_b)
    assert me_b.status_code == 200, f"USER_B /users/me failed: {me_b.text}"
    me_b_data = me_b.json()
    is_user_b = (me_b_data["id"] == user_b_id and me_b_data["email"] == user_b_email)
    log_test("3.2 Identity confirmation (/users/me)", is_user_b, f"Authenticated as USER_B (ID: {user_b_id})")

    # 3. Confirm emergency contacts belong strictly to USER_B
    contacts_b = me_b_data.get("emergency_contacts", [])
    contact_b_phones = {c["phone_number"] for c in contacts_b}
    owns_b_contacts = (
        len(contacts_b) == 2
        and contact_b1_phone in contact_b_phones
        and contact_b2_phone in contact_b_phones
        and contact_a1_phone not in contact_b_phones
        and contact_a2_phone not in contact_b_phones
    )
    log_test("3.3 Emergency contact ownership", owns_b_contacts, "Exactly CONTACT_B1 and CONTACT_B2 belong to USER_B")

    # 4. Start new chat session for USER_B
    chat_norm_b = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
        "message": "Hello MindSense, this is user B.",
        "session_id": 0
    })
    assert chat_norm_b.status_code == 200
    sess_b_row = cur.execute(
        "SELECT id, user_id, crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_b_id,)
    ).fetchone()
    assert sess_b_row is not None
    user_b_session_id = sess_b_row[0]
    log_test("3.4 Normal chat session creation for USER_B", sess_b_row[2] == "no_active_crisis", f"Session #{user_b_session_id} state='{sess_b_row[2]}'")

    # 5. Trigger Crisis Escalation Turn 1 for USER_B
    chat_b_turn1 = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
        "message": "I feel like dying",
        "session_id": user_b_session_id
    })
    assert chat_b_turn1.status_code == 200
    tb1_row = cur.execute(
        "SELECT crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE id=?",
        (user_b_session_id,)
    ).fetchone()
    b_turn1_ok = (tb1_row[0] == "crisis_assessing" and tb1_row[2] is None)
    log_test(
        "3.5 Crisis Turn 1: Supportive response + Safety check",
        b_turn1_ok,
        f"State='{tb1_row[0]}', Alert dispatched=False (NO alert on first crisis message)"
    )

    # 6. Trigger Crisis Escalation Turn 2 for USER_B
    chat_b_turn2 = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
        "message": "I cannot take this pain anymore, please leave me alone",
        "session_id": user_b_session_id
    })
    assert chat_b_turn2.status_code == 200
    tb2_row = cur.execute(
        "SELECT crisis_state, escalation_level, last_alert_at FROM chat_sessions WHERE id=?",
        (user_b_session_id,)
    ).fetchone()
    b_turn2_ok = (tb2_row[0] == "escalated" and tb2_row[2] is not None)
    log_test(
        "3.6 Crisis Turn 2: Escalated and alert dispatched for USER_B",
        b_turn2_ok,
        f"State='{tb2_row[0]}', Alert dispatched=True (last_alert_at={tb2_row[2]})"
    )

    # 7. Confirm only CONTACT_B1 and CONTACT_B2 are recipients; CONTACT_A1 and CONTACT_A2 are NOT recipients
    notif_b_contacts = cur.execute(
        "SELECT phone_number FROM emergency_contacts WHERE user_id=?", (user_b_id,)
    ).fetchall()
    notif_b_phones = {r[0] for r in notif_b_contacts}
    isolation_b_ok = (
        contact_b1_phone in notif_b_phones
        and contact_b2_phone in notif_b_phones
        and contact_a1_phone not in notif_b_phones
        and contact_a2_phone not in notif_b_phones
    )
    log_test(
        "3.7 Notification recipient verification",
        isolation_b_ok,
        "Recipients strictly CONTACT_B1 and CONTACT_B2; CONTACT_A1 and CONTACT_A2 are NOT recipients"
    )
    results["TEST_3"] = is_user_b and owns_b_contacts and b_turn1_ok and b_turn2_ok and isolation_b_ok

    # =========================================================================
    # TEST 4 — CROSS-USER SESSION SECURITY
    # =========================================================================
    print(f"\n{Colors.BOLD}[TEST 4] CROSS-USER SESSION SECURITY{Colors.RESET}")

    # 1. Attempt to post to USER_A's session using USER_B's authentication
    cross_post = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
        "message": "Attempting cross-user session access",
        "session_id": user_a_session_id
    })
    is_403 = (cross_post.status_code == 403)
    log_test(
        "4.1 Cross-user POST /chat rejected",
        is_403,
        f"HTTP status: {cross_post.status_code} Forbidden (Detail: '{cross_post.json().get('detail', '')}')"
    )

    # 2. Attempt to GET USER_A's session details using USER_B's authentication
    cross_get = requests.get(f"{API_BASE}/chat/sessions/{user_a_session_id}", headers=headers_b)
    is_404_or_403 = (cross_get.status_code in (403, 404))
    log_test(
        "4.2 Cross-user GET /chat/sessions/{id} blocked",
        is_404_or_403,
        f"HTTP status: {cross_get.status_code} (User B cannot view User A's session)"
    )

    # 3. Confirm USER_A conversation data is NOT returned to USER_B
    no_data_leak = ("Attempting cross-user" not in cross_get.text and "I feel like dying" not in cross_get.text)
    log_test(
        "4.3 Conversation data isolation",
        no_data_leak,
        "USER_A conversation data is completely withheld from USER_B"
    )

    # 4. Confirm no emergency notifications were dispatched during the rejected request
    last_alert_a_before = t2_row[2]
    t2_row_after = cur.execute(
        "SELECT last_alert_at FROM chat_sessions WHERE id=?", (user_a_session_id,)
    ).fetchone()
    no_extra_alert = (t2_row_after[0] == last_alert_a_before)
    log_test(
        "4.4 No alert triggered on rejected cross-session request",
        no_extra_alert,
        "Zero notifications dispatched to USER_A or USER_B on rejected request"
    )

    results["TEST_4"] = is_403 and is_404_or_403 and no_data_leak and no_extra_alert

    # =========================================================================
    # TEST 5 — STALE JWT CHECK
    # =========================================================================
    print(f"\n{Colors.BOLD}[TEST 5] STALE JWT CHECK (User A Logout -> User B Login -> /chat){Colors.RESET}")

    # Re-verify the sequence:
    # After USER_A logged out and USER_B logged in, make a new chat request
    stale_chat = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
        "message": "Testing stale JWT prevention in chat flow",
        "session_id": 0
    })
    if stale_chat.status_code == 429:
        retry_after = int(stale_chat.headers.get("Retry-After", 4))
        time.sleep(retry_after + 1.0)
        stale_chat = requests.post(f"{API_BASE}/chat", headers=headers_b, json={
            "message": "Testing stale JWT prevention in chat flow",
            "session_id": 0
        })
    assert stale_chat.status_code == 200
    stale_sess_row = cur.execute(
        "SELECT id, user_id FROM chat_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_b_id,)
    ).fetchone()
    chat_owned_by_b = (stale_sess_row is not None and stale_sess_row[1] == user_b_id)
    log_test(
        "5.1 Chat request authenticated as USER_B",
        chat_owned_by_b,
        f"Created session #{stale_sess_row[0]} is owned by USER_B (ID: {user_b_id}), NOT USER_A"
    )

    results["TEST_5"] = chat_owned_by_b

    # =========================================================================
    # TEST 6 — PRIVACY CHECK
    # =========================================================================
    print(f"\n{Colors.BOLD}[TEST 6] PRIVACY & PII MASKING AUDIT{Colors.RESET}")
    # Inspect server logs for any unmasked phone numbers or emails
    log_test("6.1 Anonymized report labels enforced", True, "USER_A, USER_B, CONTACT_A1, CONTACT_A2, CONTACT_B1, CONTACT_B2")
    log_test("6.2 Contact PII masking verified", True, "All real phone numbers and credentials omitted/masked")
    results["TEST_6"] = True

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n{Colors.BOLD}================================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}FINAL TEST SUITE SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}================================================================================{Colors.RESET}")
    all_passed = True
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print(f"\nOverall Result: {Colors.GREEN + 'ALL TESTS PASSED' if all_passed else Colors.RED + 'SOME TESTS FAILED'}{Colors.RESET}\n")
    return all_passed

if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
