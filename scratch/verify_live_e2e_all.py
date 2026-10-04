import os
import sys
import uuid
import time
import requests

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def safe_print(text):
    print(str(text).encode("ascii", "backslashreplace").decode("ascii"))

def send_chat(headers, payload):
    time.sleep(2.0)
    r = requests.post(f"{BASE}/chat", headers=headers, json=payload)
    if r.status_code == 429:
        retry = int(r.headers.get("Retry-After", 3))
        time.sleep(retry + 1.0)
        r = requests.post(f"{BASE}/chat", headers=headers, json=payload)
    return r

def main():
    print("=" * 80)
    print("MINDSENSE AI — LIVE PRODUCTION END-TO-END VERIFICATION")
    print("=" * 80)

    # 1. Invalid email rejection
    r_bad_email = requests.post(f"{BASE}/signup", json={
        "email": "user..bad@example.com",
        "password": "Password123!",
        "full_name": "Test User",
        "phone_number": "+919876543210",
        "emergency_contacts": [
            {"name": "Contact 1", "phone_number": "+919876543211"},
            {"name": "Contact 2", "phone_number": "+919876543212"}
        ]
    })
    safe_print(f"[LIVE 1] Invalid email rejection status: {r_bad_email.status_code}")
    safe_print(f"[LIVE 1] Invalid email detail: {r_bad_email.json().get('detail')}")
    assert r_bad_email.status_code in (400, 422)

    # 2. Invalid dummy phone rejection
    r_bad_phone = requests.post(f"{BASE}/signup", json={
        "email": "valid_user_test@example.com",
        "password": "Password123!",
        "full_name": "Test User",
        "phone_number": "+910000000000",
        "emergency_contacts": [
            {"name": "Contact 1", "phone_number": "+919876543211"},
            {"name": "Contact 2", "phone_number": "+919876543212"}
        ]
    })
    safe_print(f"[LIVE 2] Invalid dummy phone rejection status: {r_bad_phone.status_code}")
    safe_print(f"[LIVE 2] Invalid dummy phone detail: {r_bad_phone.json().get('detail')}")
    assert r_bad_phone.status_code in (400, 422)

    # 3. Create test user
    uid = uuid.uuid4().hex[:6]
    email = f"live_verify_{uid}@mindsenseai.org"
    pw = "SecurePassword123!"
    r_signup = requests.post(f"{BASE}/signup", json={
        "email": email,
        "password": pw,
        "full_name": "Live Verifier",
        "phone_number": "+919876543210",
        "emergency_contacts": [
            {"name": "Contact 1", "phone_number": "+919876543211"},
            {"name": "Contact 2", "phone_number": "+919876543212"}
        ]
    })
    assert r_signup.status_code == 200, f"Signup failed: {r_signup.text}"
    token = requests.post(f"{BASE}/token", data={"username": email, "password": pw}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    safe_print(f"[LIVE 3] Test user created & authenticated successfully (email: {email})")

    # 4. Physical health inquiry ('nanage thale novu' - headache in Kannada transliteration)
    r_headache = send_chat(headers, {"message": "nanage thale novu"})
    assert r_headache.status_code == 200
    d_headache = r_headache.json()
    reply_headache = d_headache.get("reply", "")
    safe_print(f"[LIVE 4] 'nanage thale novu' status: {r_headache.status_code}")
    safe_print(f"[LIVE 4] 'nanage thale novu' reply: {reply_headache[:120]}")
    assert "glad" not in reply_headache.lower() and "happy" not in reply_headache.lower() and "celebrat" not in reply_headache.lower()

    # 5. Language switch inquiry ('can you speak Hindi?')
    r_lang = send_chat(headers, {"message": "can you speak Hindi?"})
    assert r_lang.status_code == 200
    d_lang = r_lang.json()
    reply_lang = d_lang.get("reply", "")
    safe_print(f"[LIVE 5] 'can you speak Hindi?' reply: {reply_lang[:120]}")

    # 6. Multi-turn crisis session
    # Turn 1: crisis statement
    r_t1 = send_chat(headers, {"message": "i feel like dying"})
    assert r_t1.status_code == 200
    d_t1 = r_t1.json()
    sid = d_t1.get("session_id")
    safe_print(f"[LIVE 6] Turn 1: state={d_t1.get('crisis_state')}, risk={d_t1.get('analysis', {}).get('risk_level')}")
    assert d_t1.get("crisis_state") == "crisis_assessing"
    assert d_t1.get("analysis", {}).get("risk_level") == "HIGH"

    # Turn 2: language switch request during crisis assessment
    r_t2 = send_chat(headers, {"message": "can you speak Kannada?", "session_id": sid})
    assert r_t2.status_code == 200
    d_t2 = r_t2.json()
    safe_print(f"[LIVE 7] Turn 2 (lang switch): state={d_t2.get('crisis_state')}, risk={d_t2.get('analysis', {}).get('risk_level')}, reply={d_t2.get('reply', '')[:60]}")
    assert d_t2.get("crisis_state") == "crisis_assessing"
    assert d_t2.get("analysis", {}).get("risk_level") == "HIGH"

    # Turn 3: routine inquiry during crisis assessment
    r_t3 = send_chat(headers, {"message": "what is the weather today?", "session_id": sid})
    assert r_t3.status_code == 200
    d_t3 = r_t3.json()
    safe_print(f"[LIVE 8] Turn 3 (routine query): state={d_t3.get('crisis_state')}, risk={d_t3.get('analysis', {}).get('risk_level')}")
    assert d_t3.get("crisis_state") == "crisis_assessing"
    assert d_t3.get("analysis", {}).get("risk_level") == "HIGH"

    # Turn 4: explicit safe de-escalation
    r_t4 = send_chat(headers, {"message": "i am safe now, thank you for being here", "session_id": sid})
    assert r_t4.status_code == 200
    d_t4 = r_t4.json()
    safe_print(f"[LIVE 9] Turn 4 (safe de-escalation): state={d_t4.get('crisis_state')}, risk={d_t4.get('analysis', {}).get('risk_level')}")
    assert d_t4.get("crisis_state") == "resolved"
    assert d_t4.get("analysis", {}).get("risk_level") == "LOW"

    print("=" * 80)
    print("ALL LIVE PRODUCTION END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
