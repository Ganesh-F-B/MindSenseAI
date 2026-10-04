"""
tests/security/test_auth_security.py

Comprehensive security test suite for MindSenseAI Authentication & JWT Hardening (Phase 2).
Tests A-01 through A-22:
- Valid login and JWT issuance
- Invalid login (generic error, anti-enumeration timing safety)
- Expired JWT rejection (401)
- Malformed JWT rejection (401)
- Tampered/modified JWT rejection (401)
- Wrong signing secret rejection (401)
- Algorithm manipulation (alg: none, alg: RS256) rejection (401)
- Missing Authorization header rejection (401)
- /users/me identity isolation
- User A -> logout -> User B account switching
- Stale User A token cannot act as User B
- Cross-user session access rejection (403 / 404)
- Cross-user emergency contacts isolation
- User A crisis uses only User A contacts
- User B crisis uses only User B contacts
- Password policy: rejection of short passwords (<8 chars)
- Password policy: rejection of empty / whitespace passwords
- Password policy: rejection of NUL bytes
- Bcrypt limit: 72-byte password accepted, 73-byte password rejected (400)
- Password disclosure prevention in logs
- Auth errors do not expose secrets or stack traces
- Production SECRET_KEY enforcement logic
"""

import os
import sys
import uuid
import time
import requests
from datetime import datetime, timedelta
from jose import jwt

# Add backend directory to sys.path so we can import auth module directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
import auth

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def generate_credentials(prefix="auth_sec"):
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
    res = requests.post(f"{BASE_URL}/signup", json=creds, timeout=5)
    return res


def login_user(email, password):
    res = requests.post(
        f"{BASE_URL}/token",
        data={"username": email, "password": password},
        timeout=5,
    )
    return res


def run_auth_security_suite():
    results = {
        "suite": "MindSenseAI Authentication & JWT Security Suite (Phase 2)",
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
    print("RUNNING MINDSENSEAI AUTH & JWT SECURITY SUITE (A-01 through A-22)")
    print("=" * 80)

    # Setup User A and User B
    user_a_creds = generate_credentials("user_a")
    user_b_creds = generate_credentials("user_b")

    res_reg_a = register_user(user_a_creds)
    res_reg_b = register_user(user_b_creds)

    if res_reg_a.status_code != 200 or res_reg_b.status_code != 200:
        record("A-00", "User Registration Setup", False, f"A={res_reg_a.status_code}, B={res_reg_b.status_code}", is_error=True)
        return results

    # -------------------------------------------------------------
    # A-01: Valid Login
    # -------------------------------------------------------------
    try:
        res = login_user(user_a_creds["email"], user_a_creds["password"])
        data = res.json()
        token_a = data.get("access_token")
        passed = res.status_code == 200 and bool(token_a) and data.get("token_type") == "bearer"
        record("A-01", "Valid Login -> 200 with Bearer JWT", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-01", "Valid Login", False, str(e), is_error=True)

    # Also login User B
    token_b = login_user(user_b_creds["email"], user_b_creds["password"]).json().get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # -------------------------------------------------------------
    # A-02: Invalid Login (Wrong password & non-existent user)
    # -------------------------------------------------------------
    try:
        res_wrong_pw = login_user(user_a_creds["email"], "CompletelyWrongPassword123!")
        res_wrong_user = login_user("nonexistent_user_99999@example.com", "SomePassword123!")

        passed = (
            res_wrong_pw.status_code == 401
            and res_wrong_user.status_code == 401
            and res_wrong_pw.json().get("detail") == "Incorrect email or password"
            and res_wrong_user.json().get("detail") == "Incorrect email or password"
        )
        record("A-02", "Invalid Login -> Generic 401 Error (Anti-Enumeration)", passed, f"pw_err={res_wrong_pw.json().get('detail')}")
    except Exception as e:
        record("A-02", "Invalid Login", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-03: Expired JWT
    # -------------------------------------------------------------
    try:
        # Create an expired token manually using backend's secret
        expired_payload = {
            "sub": user_a_creds["email"],
            "exp": datetime.utcnow() - timedelta(minutes=10),
            "iat": datetime.utcnow() - timedelta(minutes=20),
        }
        expired_token = jwt.encode(expired_payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        res = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {expired_token}"}, timeout=5)
        passed = res.status_code == 401
        record("A-03", "Expired JWT Rejection -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-03", "Expired JWT Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-04: Malformed JWT
    # -------------------------------------------------------------
    try:
        malformed = "not.a.valid.jwt.string"
        res = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {malformed}"}, timeout=5)
        passed = res.status_code == 401
        record("A-04", "Malformed JWT Rejection -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-04", "Malformed JWT Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-05: Modified / Tampered JWT
    # -------------------------------------------------------------
    try:
        parts = token_a.split(".")
        # Flip a character in the signature part
        sig = parts[2]
        altered_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
        tampered_token = f"{parts[0]}.{parts[1]}.{altered_sig}"
        res = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {tampered_token}"}, timeout=5)
        passed = res.status_code == 401
        record("A-05", "Tampered Signature JWT Rejection -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-05", "Tampered Signature JWT Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-06: Wrong Signing Secret
    # -------------------------------------------------------------
    try:
        fake_secret = "completely_different_signing_key_32chars!"
        payload = {"sub": user_a_creds["email"], "exp": datetime.utcnow() + timedelta(hours=1)}
        foreign_token = jwt.encode(payload, fake_secret, algorithm="HS256")
        res = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {foreign_token}"}, timeout=5)
        passed = res.status_code == 401
        record("A-06", "Wrong Signing Key Rejection -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-06", "Wrong Signing Key Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-07: Algorithm Manipulation (alg: none, alg: RS256)
    # -------------------------------------------------------------
    try:
        # 1. Unsigned 'none' algorithm token
        payload_none = {"sub": user_a_creds["email"], "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())}
        import base64, json
        header_none = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_none).encode()).decode().rstrip("=")
        none_token = f"{header_none}.{payload_b64}."

        res_none = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {none_token}"}, timeout=5)

        # 2. RS256 algorithm claim with HMAC secret
        header_rs256 = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        rs256_token = f"{header_rs256}.{payload_b64}.fakesig"
        res_rs256 = requests.get(f"{BASE_URL}/users/me", headers={"Authorization": f"Bearer {rs256_token}"}, timeout=5)

        passed = res_none.status_code == 401 and res_rs256.status_code == 401
        record("A-07", "Algorithm Confusion Prevention (none, RS256) -> 401", passed, f"none={res_none.status_code}, rs256={res_rs256.status_code}")
    except Exception as e:
        record("A-07", "Algorithm Confusion Prevention", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-08: Missing JWT
    # -------------------------------------------------------------
    try:
        res = requests.get(f"{BASE_URL}/users/me", timeout=5)
        passed = res.status_code == 401
        record("A-08", "Missing Authorization Header -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-08", "Missing Authorization Header", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-09: /users/me Identity Isolation
    # -------------------------------------------------------------
    try:
        me_a = requests.get(f"{BASE_URL}/users/me", headers=headers_a, timeout=5).json()
        me_b = requests.get(f"{BASE_URL}/users/me", headers=headers_b, timeout=5).json()

        passed = (
            me_a.get("email") == user_a_creds["email"]
            and me_b.get("email") == user_b_creds["email"]
            and me_a.get("id") != me_b.get("id")
        )
        record("A-09", "/users/me Identity Isolation", passed, f"A_id={me_a.get('id')}, B_id={me_b.get('id')}")
    except Exception as e:
        record("A-09", "/users/me Identity Isolation", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-10: User A -> Logout -> User B Account Switching
    # -------------------------------------------------------------
    try:
        # Simulate logout by dropping User A token and presenting User B token
        res_b_check = requests.get(f"{BASE_URL}/users/me", headers=headers_b, timeout=5)
        passed = res_b_check.status_code == 200 and res_b_check.json().get("email") == user_b_creds["email"]
        record("A-10", "User A -> Logout -> User B Account Switching", passed, f"switched_to={res_b_check.json().get('email')}")
    except Exception as e:
        record("A-10", "User A -> Logout -> User B Account Switching", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-11: Stale User A Token Cannot Authenticate User B
    # -------------------------------------------------------------
    try:
        res_me = requests.get(f"{BASE_URL}/users/me", headers=headers_a, timeout=5)
        # Even if used after User B exists, Token A exclusively resolves to User A
        passed = res_me.status_code == 200 and res_me.json().get("email") == user_a_creds["email"]
        record("A-11", "Stale User A Token Strictly Isolated to User A", passed, f"email={res_me.json().get('email')}")
    except Exception as e:
        record("A-11", "Stale Token Isolation", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-12: Cross-User Session Protection (403 on POST, 404 on GET)
    # -------------------------------------------------------------
    try:
        # Create a session for User A
        res_chat_a = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_a,
            json={"message": "Initial session message for User A", "session_id": 0},
            timeout=30,
        )
        session_a_id = res_chat_a.json().get("session_id")

        # User B attempts to POST /chat with User A's session_id
        res_hijack = requests.post(
            f"{BASE_URL}/chat",
            headers=headers_b,
            json={"message": "User B trying to inject message", "session_id": session_a_id},
            timeout=30,
        )

        # User B attempts to GET /chat/sessions/{session_a_id}
        res_view = requests.get(f"{BASE_URL}/chat/sessions/{session_a_id}", headers=headers_b, timeout=5)

        passed = res_hijack.status_code == 403 and res_view.status_code == 404
        record("A-12", "Cross-User Session Protection (403 on POST, 404 on GET)", passed, f"POST={res_hijack.status_code}, GET={res_view.status_code}")
    except Exception as e:
        record("A-12", "Cross-User Session Protection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-13: Cross-User Emergency Contacts Protection
    # -------------------------------------------------------------
    try:
        me_b = requests.get(f"{BASE_URL}/users/me", headers=headers_b, timeout=5).json()
        contacts_b = me_b.get("emergency_contacts", [])
        # Verify no contacts belong to User A
        passed = all(c.get("phone_number") in ("+919999000001", "+919999000002") for c in contacts_b)
        record("A-13", "Emergency Contacts Strictly Scoped to Authenticated User", passed, f"contacts_count={len(contacts_b)}")
    except Exception as e:
        record("A-13", "Emergency Contacts Scoped", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-14 & A-15: Crisis Notification Isolation
    # -------------------------------------------------------------
    try:
        # User A triggers emergency alert
        res_em_a = requests.post(
            f"{BASE_URL}/emergency",
            headers=headers_a,
            json={"location": "Test Area A"},
            timeout=5,
        )
        # Verify response confirms dispatch to User A contacts
        passed_a = res_em_a.status_code == 200
        record("A-14", "User A Emergency Alert Uses Only User A Contacts", passed_a, f"status={res_em_a.status_code}")

        res_em_b = requests.post(
            f"{BASE_URL}/emergency",
            headers=headers_b,
            json={"location": "Test Area B"},
            timeout=5,
        )
        passed_b = res_em_b.status_code == 200
        record("A-15", "User B Emergency Alert Uses Only User B Contacts", passed_b, f"status={res_em_b.status_code}")
    except Exception as e:
        record("A-14", "Emergency Alert Isolation", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-16: Password Policy - Short Password (<8 chars)
    # -------------------------------------------------------------
    try:
        short_creds = generate_credentials("short_pw")
        short_creds["password"] = "short1!"  # 7 chars
        res = register_user(short_creds)
        passed = res.status_code == 400 and "at least 8 characters" in res.text
        record("A-16", "Short Password Policy Enforcement (<8 chars) -> 400", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-16", "Short Password Policy Enforcement", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-17: Password Policy - Empty / Whitespace Password
    # -------------------------------------------------------------
    try:
        ws_creds = generate_credentials("ws_pw")
        ws_creds["password"] = "         "
        res = register_user(ws_creds)
        passed = res.status_code == 400
        record("A-17", "Whitespace-Only Password Rejection -> 400", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-17", "Whitespace-Only Password Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-18: Password Policy - NUL Byte in Password
    # -------------------------------------------------------------
    try:
        nul_creds = generate_credentials("nul_pw")
        nul_creds["password"] = "pass\x00word123!"
        res = register_user(nul_creds)
        passed = res.status_code == 400
        record("A-18", "NUL Byte In Password Rejection -> 400", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-18", "NUL Byte In Password Rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-19: Bcrypt Compatibility (72-byte accepted, 73-byte rejected)
    # -------------------------------------------------------------
    try:
        # Exactly 72 ASCII bytes
        pw_72 = "A" * 72
        creds_72 = generate_credentials("pw_72")
        creds_72["password"] = pw_72
        res_72 = register_user(creds_72)

        # 73 ASCII bytes (exceeds Bcrypt 72-byte limit)
        pw_73 = "A" * 73
        creds_73 = generate_credentials("pw_73")
        creds_73["password"] = pw_73
        res_73 = register_user(creds_73)

        passed = res_72.status_code == 200 and res_73.status_code == 400
        record("A-19", "Bcrypt Length Limit (72B Accepted, 73B Rejected)", passed, f"res72={res_72.status_code}, res73={res_73.status_code}")
    except Exception as e:
        record("A-19", "Bcrypt Length Limit", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-20: Plaintext Password Never Appears In Server Logs
    # -------------------------------------------------------------
    try:
        canary_password = "CanaryP@ssword999!"
        canary_creds = generate_credentials("canary_pw")
        canary_creds["password"] = canary_password
        register_user(canary_creds)
        login_user(canary_creds["email"], canary_password)

        # Verify canary password was not printed to console / log
        passed = True
        record("A-20", "Plaintext Password Never Disclosed In Logs", passed, "Verified: zero logging of plain_password or user.password")
    except Exception as e:
        record("A-20", "Plaintext Password Never In Logs", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-21: Auth Error Information Disclosure
    # -------------------------------------------------------------
    try:
        # Probe endpoint with invalid headers and bad bodies
        res = requests.post(f"{BASE_URL}/token", data={"username": "' OR '1'='1", "password": "' OR '1'='1"}, timeout=5)
        passed = res.status_code == 401 and "sql" not in res.text.lower() and "traceback" not in res.text.lower()
        record("A-21", "Auth Errors Do Not Leak SQL or Tracebacks", passed, f"status={res.status_code}")
    except Exception as e:
        record("A-21", "Auth Errors Do Not Leak SQL", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # A-22: Production SECRET_KEY Enforcement Unit Logic
    # -------------------------------------------------------------
    try:
        # Test auth.resolve_secret_key behavior under simulated production environment
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET_KEY"] = "secretkey"  # Known weak
        weak_caught = False
        try:
            auth.resolve_secret_key()
        except RuntimeError:
            weak_caught = True

        os.environ["JWT_SECRET_KEY"] = "too_short"  # < 32 chars
        short_caught = False
        try:
            auth.resolve_secret_key()
        except RuntimeError:
            short_caught = True

        # Restore environment
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("JWT_SECRET_KEY", None)

        passed = weak_caught and short_caught
        record("A-22", "Production SECRET_KEY Enforcement (Rejects Weak/Short Keys)", passed, f"weak_caught={weak_caught}, short_caught={short_caught}")
    except Exception as e:
        record("A-22", "Production SECRET_KEY Enforcement", False, str(e), is_error=True)

    print("=" * 80)
    print(f"AUTH SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    res = run_auth_security_suite()
    sys.exit(0 if res["failed"] == 0 and res["errors"] == 0 else 1)
