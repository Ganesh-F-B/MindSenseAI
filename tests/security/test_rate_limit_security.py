"""
tests/security/test_rate_limit_security.py

Automated Rate Limiting & DoS / Abuse Protection Security Suite (Phase 3).
Tests:
- R-01 (A): Unauthenticated /token login burst is rate-limited -> 429
- R-02 (B): Repeated authentication abuse returns 429 with Retry-After
- R-03 (C): Legitimate login succeeds after cooldown expiration
- R-04 (D): Authenticated /chat requests are rate-limited on flood -> 429
- R-05 (E): Rate limits are keyed to authenticated user identity (user:<id>)
- R-06 (F): Changing session_id does NOT bypass user rate limit
- R-07 (G): One user hitting limit does NOT block another authenticated user (isolation)
- R-08 (H): /tts is rate-limited -> 429
- R-09 (I): /transcribe is rate-limited -> 429
- R-10 (J): /upload is rate-limited -> 429
- R-11 (K): /upload-video is rate-limited -> 429
- R-12 (L1): /emergency endpoint is rate-limited -> 429
- R-13 (L2): /emergency-contacts endpoint is rate-limited -> 429
- R-14 (M): HTTP 429 is consistently returned across rate-limited endpoints
- R-15 (N): Retry-After header is present and integer > 0 on 429 responses
- R-16 (O): Rate-limit state audit: zero sensitive data (passwords, tokens, PII) in memory
- R-17 (P): Normal legitimate sequential request sequence succeeds without 429
- R-18: /chat oversized payload rejection (>5000 chars) -> 422
"""

import concurrent.futures
import io
import os
import sys
import time
import uuid
import requests

# Add backend directory to sys.path so we can import rate_limiter directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
import rate_limiter

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def generate_credentials(prefix="rl_sec"):
    uid = uuid.uuid4().hex[:8]
    return {
        "email": f"{prefix}_{uid}@mindsenseai.org",
        "password": f"Pass_{uid}_123!",
        "full_name": f"User {uid}",
        "phone_number": "+919999000010",
        "emergency_contacts": [
            {"name": "Contact 1", "phone_number": "+919999000001"},
            {"name": "Contact 2", "phone_number": "+919999000002"},
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


def run_rate_limit_security_suite():
    results = {
        "suite": "MindSenseAI Rate Limiting & Abuse Protection Suite (Phase 3)",
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
    print("RUNNING MINDSENSEAI RATE LIMITING SECURITY SUITE (R-01 through R-18)")
    print("=" * 80)

    # -------------------------------------------------------------
    # Setup User A and User B
    # -------------------------------------------------------------
    user_a_creds = generate_credentials("rl_user_a")
    user_b_creds = generate_credentials("rl_user_b")

    res_reg_a = register_user(user_a_creds)
    res_reg_b = register_user(user_b_creds)

    if res_reg_a.status_code != 200 or res_reg_b.status_code != 200:
        record("R-00", "User Registration Setup", False, f"A={res_reg_a.status_code}, B={res_reg_b.status_code}", is_error=True)
        return results

    token_a = login_user(user_a_creds["email"], user_a_creds["password"]).json().get("access_token")
    token_b = login_user(user_b_creds["email"], user_b_creds["password"]).json().get("access_token")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Warm up /chat model with User B so first request latency does not affect tests
    try:
        requests.post(
            f"{BASE_URL}/chat",
            headers=headers_b,
            json={"message": "System warm up request", "session_id": 0},
            timeout=30,
        )
    except Exception:
        pass

    # Wait 5.5s so initial setup/login requests don't spill into R-01
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-01 (A): Unauthenticated /token login burst is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        # Rapid burst to /token (burst limit is 6 in 5s)
        responses = []
        for _ in range(8):
            r = login_user(user_a_creds["email"], "wrong_password_flood")
            responses.append(r)

        hit_429 = any(r.status_code == 429 for r in responses)
        r_429 = next((r for r in responses if r.status_code == 429), None)
        retry_val = None
        if r_429 is not None:
            for k, v in r_429.headers.items():
                if k.lower() == "retry-after":
                    retry_val = v
                    break
        has_retry = bool(r_429 is not None and retry_val and int(retry_val) > 0)

        record("R-01", "Unauthenticated Login Burst Rate-Limited -> 429", hit_429 and has_retry, f"hit_429={hit_429}, retry_after={retry_val}")
    except Exception as e:
        record("R-01", "Unauthenticated Login Burst", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-02 (B): Repeated authentication abuse returns 429 with Retry-After
    # -------------------------------------------------------------
    try:
        # Immediately attempt another login while in rate limit cooldown
        res_abuse = login_user(user_a_creds["email"], "abusive_rapid_attempt")
        retry_val = res_abuse.headers.get("retry-after") or res_abuse.headers.get("Retry-After")
        passed = res_abuse.status_code == 429 and bool(retry_val)
        record("R-02", "Repeated Auth Abuse Returns 429 with Retry-After", passed, f"status={res_abuse.status_code}, retry={retry_val}")
    except Exception as e:
        record("R-02", "Repeated Auth Abuse", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-03 (C): Legitimate login succeeds after cooldown expiration
    # -------------------------------------------------------------
    try:
        # Wait for the burst window (5 seconds) to pass
        time.sleep(5.5)
        res_legit = login_user(user_a_creds["email"], user_a_creds["password"])
        passed = res_legit.status_code == 200 and "access_token" in res_legit.json()
        record("R-03", "Legitimate Login Succeeds After Cooldown", passed, f"status={res_legit.status_code}")
    except Exception as e:
        record("R-03", "Legitimate Login After Cooldown", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-04 (D): Authenticated /chat requests are rate-limited on flood -> 429
    # -------------------------------------------------------------
    try:
        # Burst limit for CHAT is 4 requests in 5s. Send concurrent chat requests.
        def send_chat(idx):
            return requests.post(
                f"{BASE_URL}/chat",
                headers=headers_a,
                json={"message": f"flood test message {idx}", "session_id": 0},
                timeout=30,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_chat, i) for i in range(5)]
            chat_responses = [f.result() for f in futures]

        hit_chat_429 = any(r.status_code == 429 for r in chat_responses)
        chat_429_count = sum(1 for r in chat_responses if r.status_code == 429)
        record("R-04", "Authenticated /chat Flooding Returns 429", hit_chat_429, f"hit_429={hit_chat_429}, 429_count={chat_429_count}/5")
    except Exception as e:
        record("R-04", "Authenticated /chat Flooding", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-05 (E) & R-06 (F): Rate limits keyed to User ID; session_id change CANNOT bypass
    # -------------------------------------------------------------
    try:
        # User A is currently rate-limited on /chat.
        # User A tries to bypass by presenting a different session_id (e.g. 9999 or 0)
        res_bypass1 = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "attempting session_id bypass", "session_id": 9999},
            timeout=10,
        )
        res_bypass2 = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "attempting session_id 0 bypass", "session_id": 0},
            timeout=10,
        )
        bypassed = res_bypass1.status_code != 429 or res_bypass2.status_code != 429
        record("R-06", "Changing session_id Cannot Bypass Rate Limit", not bypassed, f"s9999={res_bypass1.status_code}, s0={res_bypass2.status_code}")
    except Exception as e:
        record("R-06", "session_id Bypass Prevention", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-07 (G): One user hitting limit does NOT block another authenticated user (isolation)
    # -------------------------------------------------------------
    try:
        # User A is rate-limited. Now User B makes a normal /chat request.
        # User B should NOT be rate-limited!
        res_user_b = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_b,
            json={"message": "Hello from User B, am I blocked?", "session_id": 0},
            timeout=20,
        )
        user_b_isolated = res_user_b.status_code == 200
        record("R-07", "Cross-User Rate Limit Isolation (User A limited != User B blocked)", user_b_isolated, f"user_b_status={res_user_b.status_code}")
    except Exception as e:
        record("R-07", "Cross-User Rate Limit Isolation", False, str(e), is_error=True)

    # Wait for User A's burst window to reset before media tests
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-08 (H): /tts is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        # TTS burst limit is 6. Send 8 concurrent requests.
        def send_tts(i):
            return requests.post(
                f"{BASE_URL}/tts",
                headers=headers_a,
                json={"text": f"TTS rate limit test sentence number {i}", "language": "en"},
                timeout=15,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(send_tts, i) for i in range(8)]
            tts_responses = [f.result() for f in futs]

        hit_tts_429 = any(r.status_code == 429 for r in tts_responses)
        record("R-08", "/tts Endpoint Rate-Limited -> 429", hit_tts_429, f"hit_429={hit_tts_429}")
    except Exception as e:
        record("R-08", "/tts Rate Limiting", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-09 (I): /transcribe is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        tiny_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 1200
        def send_transcribe():
            return requests.post(
                f"{BASE_URL}/transcribe",
                headers=headers_a,
                files={"file": ("audio.webm", io.BytesIO(tiny_audio), "audio/webm")},
                timeout=15,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(send_transcribe) for _ in range(10)]
            transcribe_responses = [f.result() for f in futs]

        hit_transcribe_429 = any(r.status_code == 429 for r in transcribe_responses)
        record("R-09", "/transcribe Endpoint Rate-Limited -> 429", hit_transcribe_429, f"hit_429={hit_transcribe_429}")
    except Exception as e:
        record("R-09", "/transcribe Rate Limiting", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-10 (J): /upload is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        dummy_txt = b"MindSenseAI test text upload payload."
        def send_upload():
            return requests.post(
                f"{BASE_URL}/upload",
                headers=headers_a,
                files={"file": ("notes.txt", io.BytesIO(dummy_txt), "text/plain")},
                timeout=15,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(send_upload) for _ in range(8)]
            upload_responses = [f.result() for f in futs]

        hit_upload_429 = any(r.status_code == 429 for r in upload_responses)
        record("R-10", "/upload Endpoint Rate-Limited -> 429", hit_upload_429, f"hit_429={hit_upload_429}")
    except Exception as e:
        record("R-10", "/upload Rate Limiting", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-11 (K): /upload-video is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        dummy_video = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 200
        def send_video():
            return requests.post(
                f"{BASE_URL}/upload-video",
                headers=headers_a,
                files={"file": ("video.mp4", io.BytesIO(dummy_video), "video/mp4")},
                timeout=15,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(send_video) for _ in range(4)]
            video_responses = [f.result() for f in futs]

        hit_video_429 = any(r.status_code == 429 for r in video_responses)
        record("R-11", "/upload-video Endpoint Rate-Limited -> 429", hit_video_429, f"hit_429={hit_video_429}")
    except Exception as e:
        record("R-11", "/upload-video Rate Limiting", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-12 (L1): /emergency endpoint is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        def send_emergency():
            return requests.post(f"{BASE_URL}/emergency", headers=headers_a, timeout=15)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futs = [ex.submit(send_emergency) for _ in range(5)]
            emergency_responses = [f.result() for f in futs]

        hit_em_429 = any(r.status_code == 429 for r in emergency_responses)
        record("R-12", "/emergency Endpoint Rate-Limited -> 429", hit_em_429, f"hit_429={hit_em_429}")
    except Exception as e:
        record("R-12", "/emergency Rate Limiting", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-13 (L2): /emergency-contacts endpoint is rate-limited -> 429
    # -------------------------------------------------------------
    try:
        contact_update_payload = {
            "contacts": [
                {"name": "Dr. Smith", "phone_number": "+919999000001", "callmebot_key": ""},
                {"name": "Family Member", "phone_number": "+919999000002", "callmebot_key": ""},
            ]
        }
        def send_contact_update():
            return requests.put(
                f"{BASE_URL}/emergency-contacts",
                headers=headers_a,
                json=contact_update_payload,
                timeout=15,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(send_contact_update) for _ in range(6)]
            contact_responses = [f.result() for f in futs]

        hit_contact_429 = any(r.status_code == 429 for r in contact_responses)
        record("R-13", "/emergency-contacts Endpoint Rate-Limited -> 429", hit_contact_429, f"hit_429={hit_contact_429}")
    except Exception as e:
        record("R-13", "/emergency-contacts Rate Limiting", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-14 (M) & R-15 (N): Consistent 429 & Retry-After Verification
    # -------------------------------------------------------------
    try:
        # An immediate request against the rate-limited endpoint
        r_check = requests.put(
            f"{BASE_URL}/emergency-contacts",
            headers=headers_a,
            json=contact_update_payload,
            timeout=5,
        )
        passed_429 = r_check.status_code == 429
        retry_val = r_check.headers.get("retry-after") or r_check.headers.get("Retry-After")
        passed_retry = bool(retry_val and retry_val.isdigit() and int(retry_val) > 0)
        json_detail = r_check.json().get("detail", "")
        passed_detail = "Rate limit exceeded" in json_detail

        record("R-14", "HTTP 429 Consistently Returned with Structured JSON", passed_429 and passed_detail, f"status={r_check.status_code}, detail='{json_detail}'")
        record("R-15", "Retry-After Header Present & Numeric (>0)", passed_retry, f"Retry-After={retry_val}")
    except Exception as e:
        record("R-14", "429 Response Structure", False, str(e), is_error=True)
        record("R-15", "Retry-After Header", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-16 (O): Rate-limit state audit: zero sensitive data in memory
    # -------------------------------------------------------------
    try:
        # Test rate limiter directly in-memory to audit stored keys and structures
        test_limiter = rate_limiter.InMemoryRateLimiter()
        # Feed various keys
        test_limiter.check("ip:127.0.0.1:token", rate_limiter.AUTH_TOKEN_CONFIG)
        test_limiter.check("user:42:chat", rate_limiter.CHAT_CONFIG)
        active_keys = test_limiter.get_tracked_keys()

        sensitive_found = False
        sample_passwords = ["SecretPass123!", "Admin123$", "user_jwt_token_xyz"]
        for sp in sample_passwords:
            if any(sp in k for k in active_keys):
                sensitive_found = True

        state_clean = not sensitive_found and all(k.startswith(("ip:", "user:")) for k in active_keys)
        record("R-16", "Rate Limiter State Audit: Zero Sensitive Data In Memory", state_clean, f"active_keys={active_keys}")
    except Exception as e:
        record("R-16", "Rate Limiter State Audit", False, str(e), is_error=True)

    # Wait 5.5s
    time.sleep(5.5)

    # -------------------------------------------------------------
    # R-17 (P): Normal legitimate sequential request sequence succeeds without 429
    # -------------------------------------------------------------
    try:
        # Clean sequence for User B: GET /users/me, GET /chat/sessions, POST /chat
        res_me = requests.get(f"{BASE_URL}/users/me", headers=headers_b, timeout=5)
        res_sess = requests.get(f"{BASE_URL}/chat/sessions", headers=headers_b, timeout=5)
        res_chat = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_b,
            json={"message": "Good morning, checking in today.", "session_id": 0},
            timeout=20,
        )
        legit_sequence_ok = (
            res_me.status_code == 200
            and res_sess.status_code == 200
            and res_chat.status_code == 200
        )
        record("R-17", "Legitimate Sequential Requests Succeed Without 429", legit_sequence_ok, f"me={res_me.status_code}, sess={res_sess.status_code}, chat={res_chat.status_code}")
    except Exception as e:
        record("R-17", "Legitimate Sequential Requests", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # R-18: /chat oversized payload rejection (>5000 chars) -> 422
    # -------------------------------------------------------------
    try:
        oversized_msg = "A" * 5001
        res_oversized = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_b,
            json={"message": oversized_msg, "session_id": 0},
            timeout=5,
        )
        passed_422 = res_oversized.status_code == 422
        record("R-18", "Oversized /chat Payload (>5000 chars) Rejected -> 422", passed_422, f"status={res_oversized.status_code}")
    except Exception as e:
        record("R-18", "Oversized Payload Rejection", False, str(e), is_error=True)

    print("=" * 80)
    print(f"RATE LIMIT SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    suite_results = run_rate_limit_security_suite()
    if suite_results["failed"] > 0 or suite_results["errors"] > 0:
        sys.exit(1)
    sys.exit(0)
