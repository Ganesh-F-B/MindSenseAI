import os
import sys
import hashlib
import json
import time
import requests
import uuid

API_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://localhost:3000"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_baseline():
    print("=" * 80)
    print("MINDSENSEAI SECURITY HARDENING — PHASE 0 BASELINE AUDIT")
    print("=" * 80)

    report = {}

    # 1. ENVIRONMENT CHECK
    print("\n[1] Environment Check...")
    report["environment"] = {
        "python": sys.version.split()[0],
        "python_path": sys.executable,
        "platform": sys.platform,
        "cwd": os.getcwd()
    }
    print(f"  Python: {report['environment']['python']} ({sys.executable})")

    # 2. BACKEND BASELINE CHECK
    print("\n[2] Backend API Baseline Checks (http://127.0.0.1:8000)...")
    test_id = str(uuid.uuid4())[:8]
    test_email = f"baseline_user_{test_id}@mindsenseai.org"
    test_password = f"BaselinePass123!_{test_id}"

    # 2.1 Docs / Root
    docs_resp = requests.get(f"{API_BASE}/docs", timeout=5)
    print(f"  GET /docs: HTTP {docs_resp.status_code}")

    # 2.2 Signup
    signup_payload = {
        "email": test_email,
        "password": test_password,
        "full_name": f"Baseline User {test_id}",
        "phone_number": "+919999000100",
        "emergency_contacts": [
            {"name": "Contact A1", "phone_number": "+919999000101"},
            {"name": "Contact A2", "phone_number": "+919999000102"}
        ]
    }
    signup_resp = requests.post(f"{API_BASE}/signup", json=signup_payload, timeout=5)
    signup_ok = (signup_resp.status_code == 200)
    print(f"  POST /signup: HTTP {signup_resp.status_code} ({'OK' if signup_ok else signup_resp.text})")
    user_id = signup_resp.json().get("id") if signup_ok else None

    # 2.3 Login / Token
    token_resp = requests.post(f"{API_BASE}/token", data={"username": test_email, "password": test_password}, timeout=5)
    token_ok = (token_resp.status_code == 200)
    token = token_resp.json().get("access_token") if token_ok else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    print(f"  POST /token: HTTP {token_resp.status_code} ({'JWT issued' if token_ok else 'Failed'})")

    # 2.4 /users/me
    me_resp = requests.get(f"{API_BASE}/users/me", headers=headers, timeout=5)
    me_ok = (me_resp.status_code == 200 and me_resp.json().get("email") == test_email)
    print(f"  GET /users/me: HTTP {me_resp.status_code} ({'Matched User' if me_ok else 'Failed'})")

    # 2.5 Chat & Sessions
    chat_resp = requests.post(f"{API_BASE}/chat", headers=headers, json={"message": "Hello MindSense, baseline test.", "session_id": 0}, timeout=10)
    chat_ok = (chat_resp.status_code == 200)
    session_id = chat_resp.json().get("session_id") if chat_ok else None
    print(f"  POST /chat: HTTP {chat_resp.status_code} (Session ID: {session_id})")

    sess_resp = requests.get(f"{API_BASE}/chat/sessions", headers=headers, timeout=5)
    print(f"  GET /chat/sessions: HTTP {sess_resp.status_code} ({len(sess_resp.json())} sessions)")

    # 2.6 /emergency
    emerg_resp = requests.post(f"{API_BASE}/emergency", headers=headers, timeout=5)
    msg_text = emerg_resp.json().get('message', '').encode('ascii', errors='replace').decode('ascii')
    print(f"  POST /emergency: HTTP {emerg_resp.status_code} ({msg_text[:60]}...)")

    # 2.7 /tts (Check auth status)
    tts_unauth_resp = requests.post(f"{API_BASE}/tts", json={"text": "Security audit test", "language": "en"}, timeout=10)
    tts_unauth_allowed = (tts_unauth_resp.status_code == 200)
    print(f"  POST /tts (Unauthenticated): HTTP {tts_unauth_resp.status_code} (VULNERABILITY: {'Allows unauthenticated access' if tts_unauth_allowed else 'Protected'})")

    # 2.8 /upload
    canary_content = b"Canary test file for baseline audit."
    upload_resp = requests.post(
        f"{API_BASE}/upload",
        headers=headers,
        files={"file": ("canary_test.txt", canary_content, "text/plain")},
        timeout=5
    )
    print(f"  POST /upload: HTTP {upload_resp.status_code} ({upload_resp.json()})")

    # 3. FRONTEND BASELINE CHECK
    print("\n[3] Frontend Availability Checks (http://localhost:3000)...")
    for route in ["", "/login", "/signup", "/dashboard", "/chat", "/profile", "/settings"]:
        try:
            r = requests.get(f"{FRONTEND_BASE}{route}", timeout=5)
            print(f"  GET {FRONTEND_BASE}{route}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  GET {FRONTEND_BASE}{route}: ERROR ({e})")

    # 4. BASELINE SECURITY VULNERABILITY TESTS (Safe Canaries)
    print("\n[4] Safe Security Vulnerability Tests...")

    # A. Upload path traversal test (safe canary filename)
    traversal_filename = "..\\canary_traversal.txt"
    try:
        r_trav = requests.post(
            f"{API_BASE}/upload",
            headers=headers,
            files={"file": (traversal_filename, b"Canary path traversal content", "text/plain")},
            timeout=5
        )
        # Check if file was written outside uploads
        escaped_file = os.path.join(PROJECT_ROOT, "backend", "canary_traversal.txt")
        traversal_occurred = os.path.exists(escaped_file)
        print(f"  [VULN-A] Upload Path Traversal: Endpoint HTTP {r_trav.status_code}. Escaped outside uploads directory: {traversal_occurred}")
        if traversal_occurred:
            try:
                os.remove(escaped_file)
                print("    (Cleaned up canary traversal file)")
            except:
                pass
    except Exception as e:
        print(f"  [VULN-A] Upload Path Traversal error: {e}")

    # B. Duplicate filename collision between users
    user_b_email = f"baseline_user_b_{test_id}@mindsenseai.org"
    signup_b = requests.post(f"{API_BASE}/signup", json={
        "email": user_b_email,
        "password": test_password,
        "full_name": f"User B {test_id}",
        "phone_number": "+919999000103",
        "emergency_contacts": [
            {"name": "Contact B1", "phone_number": "+919999000104"},
            {"name": "Contact B2", "phone_number": "+919999000105"}
        ]
    })
    token_b = requests.post(f"{API_BASE}/token", data={"username": user_b_email, "password": test_password}).json().get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A uploads canary_shared.txt
    requests.post(f"{API_BASE}/upload", headers=headers, files={"file": ("canary_shared.txt", b"User A private content", "text/plain")})
    # User B uploads canary_shared.txt with different content
    requests.post(f"{API_BASE}/upload", headers=headers_b, files={"file": ("canary_shared.txt", b"User B overwriting content", "text/plain")})

    shared_path = os.path.join(PROJECT_ROOT, "backend", "uploads", "canary_shared.txt")
    if os.path.exists(shared_path):
        with open(shared_path, "rb") as f:
            final_content = f.read()
        clobbered = (final_content == b"User B overwriting content")
        print(f"  [VULN-B] Unisolated User Uploads (Filename Collision): {clobbered} (User B overwrote User A's file)")
        try:
            os.remove(shared_path)
        except:
            pass

    # C. /tts unauthenticated & shared output.mp3
    tts_out_path = os.path.join(PROJECT_ROOT, "backend", "uploads", "output.mp3")
    tts_shared_exists = os.path.exists(tts_out_path)
    print(f"  [VULN-C/D] TTS Unauthenticated & Static Shared File: output.mp3 shared path exists = {tts_shared_exists}")

    # E. Uploads directory accumulation
    uploads_dir = os.path.join(PROJECT_ROOT, "backend", "uploads")
    if os.path.exists(uploads_dir):
        files_count = len(os.listdir(uploads_dir))
        print(f"  [VULN-E] Upload Persistence: {files_count} files stored persistently in backend/uploads with no TTL or cleanup")

    # G. Missing Rate Limiting (Burst 20 requests)
    start_burst = time.time()
    statuses = []
    for _ in range(15):
        r = requests.post(f"{API_BASE}/token", data={"username": "invalid@test.com", "password": "wrongpassword"})
        statuses.append(r.status_code)
    burst_duration = time.time() - start_burst
    all_401 = all(s == 401 for s in statuses)
    any_429 = any(s == 429 for s in statuses)
    print(f"  [VULN-G] Missing Rate Limiting: 15 failed logins in {burst_duration:.2f}s returned HTTP {set(statuses)}. Throttled (429): {any_429}")

    # H. Oversized input handling
    large_msg = "A" * 150000  # 150KB
    try:
        r_large = requests.post(f"{API_BASE}/chat", headers=headers, json={"message": large_msg, "session_id": session_id}, timeout=15)
        print(f"  [VULN-H] Oversized Input Handling: 150KB message processed with HTTP {r_large.status_code} (No body length limit)")
    except Exception as e:
        print(f"  [VULN-H] Oversized input error: {e}")

    # Clean up canary test files in uploads
    for cfile in ["canary_test.txt"]:
        cp = os.path.join(uploads_dir, cfile)
        if os.path.exists(cp):
            try:
                os.remove(cp)
            except:
                pass

    # 5. BASELINE FILE CHECKSUMS (SHA-256)
    print("\n[5] Computing Baseline SHA-256 Checksums for Core Files...")
    core_files = [
        "backend/deberta_predictor.py",
        "backend/nlp_service.py",
        "backend/main.py",
        "backend/models.py",
        "backend/database.py",
        "backend/schemas.py",
        "backend/auth.py",
        "chatbot/conversation/chat_engine.py",
        "chatbot/conversation/response_generator.py",
        "chatbot/emotion/predictor.py",
        "chatbot/emotion/config.py",
        "chatbot/emotion/model.py",
        "chatbot/intent/predictor.py",
        "chatbot/intent/config.py",
        "chatbot/intent/model.py",
        "frontend/hooks/useAuth.tsx",
        "frontend/lib/api.ts",
    ]

    checksums = {}
    for rel_path in core_files:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(full_path):
            h = sha256_file(full_path)
            checksums[rel_path] = h
            print(f"  {h[:12]}...  {rel_path}")
        else:
            print(f"  MISSING: {rel_path}")

    # Save baseline checksums for subsequent phase verifications
    checksum_file = os.path.join(PROJECT_ROOT, "scratch", "security_phase0_baseline_checksums.json")
    with open(checksum_file, "w") as f:
        json.dump(checksums, f, indent=2)
    print(f"\nChecksums saved to: {checksum_file}")

if __name__ == "__main__":
    run_baseline()
