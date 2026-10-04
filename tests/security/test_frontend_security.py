"""
tests/security/test_frontend_security.py

Automated Frontend Security, Security Headers, CORS & Cookie Policy Security Suite (Phase 5).
Tests:
- F-01: CORS does not allow arbitrary origins
- F-02: Allowed development origin works (http://localhost:3000)
- F-03: Unauthorized origin is rejected / not authorized
- F-04: Credentials are not combined with wildcard origin
- F-05: X-Content-Type-Options is present (nosniff)
- F-06: X-Frame-Options is present (DENY)
- F-07: Referrer-Policy is present (strict-origin-when-cross-origin)
- F-08: Permissions-Policy is present with restrictive defaults
- F-09: Content-Security-Policy is present and not wildcard-open
- F-10: HSTS behavior is production-aware (absent on HTTP, present on HTTPS forwarded)
- F-11: No password is stored in browser storage
- F-12: Logout clears authentication artifacts
- F-13: JWT storage behavior matches documented security policy
- F-14: No API/provider secret is exposed through frontend environment variables
- F-15: No dangerouslySetInnerHTML in frontend source
- F-16: No eval / new Function / javascript: URL execution in frontend source
- F-17: External resource inventory matches CSP
- F-18: Normal login still works
- F-19: Normal authenticated API requests still work
- F-20: Normal chat workflow still works
"""

import os
import re
import sys
import uuid
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def generate_credentials(prefix="p5_sec"):
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
    return requests.post(f"{API_BASE_URL}/signup", json=creds, timeout=10)


def login_user(email, password):
    return requests.post(
        f"{API_BASE_URL}/token",
        data={"username": email, "password": password},
        timeout=10,
    )


def run_frontend_security_suite():
    results = {
        "suite": "MindSenseAI Frontend Security, Headers & CORS Suite (Phase 5)",
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
    print("RUNNING MINDSENSEAI FRONTEND SECURITY TEST SUITE (F-01 through F-20)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Setup test user for authenticated flows
    # -------------------------------------------------------------------------
    creds = generate_credentials()
    reg_res = register_user(creds)
    token = None
    if reg_res.status_code == 200:
        login_res = login_user(creds["email"], creds["password"])
        if login_res.status_code == 200:
            token = login_res.json().get("access_token")
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    # -------------------------------------------------------------------------
    # F-01: CORS does not allow arbitrary origins
    # -------------------------------------------------------------------------
    try:
        evil_origin = "http://evil-attacker.com"
        r = requests.get(
            f"{API_BASE_URL}/chat/sessions",
            headers={"Origin": evil_origin, **auth_headers},
            timeout=5,
        )
        allow_origin = r.headers.get("access-control-allow-origin")
        passed = (allow_origin != evil_origin and allow_origin != "*")
        record(
            "F-01",
            "CORS does not allow arbitrary origins",
            passed,
            f"evil_origin={evil_origin}, allow_origin={allow_origin}",
        )
    except Exception as e:
        record("F-01", "CORS does not allow arbitrary origins", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-02: Allowed development origin works (http://localhost:3000)
    # -------------------------------------------------------------------------
    try:
        dev_origin = "http://localhost:3000"
        r = requests.get(
            f"{API_BASE_URL}/chat/sessions",
            headers={"Origin": dev_origin, **auth_headers},
            timeout=5,
        )
        allow_origin = r.headers.get("access-control-allow-origin")
        allow_creds = r.headers.get("access-control-allow-credentials")
        passed = (allow_origin == dev_origin and allow_creds == "true")
        record(
            "F-02",
            "Allowed development origin works (http://localhost:3000)",
            passed,
            f"allow_origin={allow_origin}, allow_credentials={allow_creds}",
        )
    except Exception as e:
        record("F-02", "Allowed development origin works", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-03: Unauthorized origin is rejected / not authorized
    # -------------------------------------------------------------------------
    try:
        unauth_origin = "http://unauthorized-domain.com"
        # Preflight test
        r_preflight = requests.options(
            f"{API_BASE_URL}/chat",
            headers={
                "Origin": unauth_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
            timeout=5,
        )
        preflight_allow = r_preflight.headers.get("access-control-allow-origin")
        passed = (preflight_allow is None or preflight_allow != unauth_origin)
        record(
            "F-03",
            "Unauthorized origin is rejected / not authorized",
            passed,
            f"preflight_status={r_preflight.status_code}, preflight_allow_origin={preflight_allow}",
        )
    except Exception as e:
        record("F-03", "Unauthorized origin is rejected", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-04: Credentials are not combined with wildcard origin
    # -------------------------------------------------------------------------
    try:
        r = requests.get(
            f"{API_BASE_URL}/chat/sessions",
            headers={"Origin": "http://localhost:3000", **auth_headers},
            timeout=5,
        )
        allow_origin = r.headers.get("access-control-allow-origin")
        allow_creds = r.headers.get("access-control-allow-credentials")
        is_wildcard = (allow_origin == "*")
        passed = not (is_wildcard and allow_creds == "true") and (allow_origin != "*")
        record(
            "F-04",
            "Credentials are not combined with wildcard origin",
            passed,
            f"allow_origin={allow_origin}, allow_credentials={allow_creds}",
        )
    except Exception as e:
        record("F-04", "Credentials are not combined with wildcard", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-05: X-Content-Type-Options is present (nosniff)
    # -------------------------------------------------------------------------
    try:
        r_api = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        r_front = requests.get(f"{FRONTEND_BASE_URL}", timeout=10)
        api_header = r_api.headers.get("x-content-type-options")
        front_header = r_front.headers.get("x-content-type-options")
        passed = (api_header == "nosniff" and front_header == "nosniff")
        record(
            "F-05",
            "X-Content-Type-Options is present (nosniff)",
            passed,
            f"api={api_header}, frontend={front_header}",
        )
    except Exception as e:
        record("F-05", "X-Content-Type-Options is present", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-06: X-Frame-Options is present (DENY)
    # -------------------------------------------------------------------------
    try:
        r_api = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        r_front = requests.get(f"{FRONTEND_BASE_URL}", timeout=10)
        api_header = r_api.headers.get("x-frame-options")
        front_header = r_front.headers.get("x-frame-options")
        passed = (api_header == "DENY" and front_header == "DENY")
        record(
            "F-06",
            "X-Frame-Options is present (DENY)",
            passed,
            f"api={api_header}, frontend={front_header}",
        )
    except Exception as e:
        record("F-06", "X-Frame-Options is present", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-07: Referrer-Policy is present (strict-origin-when-cross-origin)
    # -------------------------------------------------------------------------
    try:
        r_api = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        r_front = requests.get(f"{FRONTEND_BASE_URL}", timeout=10)
        api_header = r_api.headers.get("referrer-policy")
        front_header = r_front.headers.get("referrer-policy")
        passed = (
            api_header == "strict-origin-when-cross-origin"
            and front_header == "strict-origin-when-cross-origin"
        )
        record(
            "F-07",
            "Referrer-Policy is present (strict-origin-when-cross-origin)",
            passed,
            f"api={api_header}, frontend={front_header}",
        )
    except Exception as e:
        record("F-07", "Referrer-Policy is present", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-08: Permissions-Policy is present with restrictive defaults
    # -------------------------------------------------------------------------
    try:
        r_api = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        r_front = requests.get(f"{FRONTEND_BASE_URL}", timeout=10)
        api_perm = r_api.headers.get("permissions-policy")
        front_perm = r_front.headers.get("permissions-policy")
        # Backend restricts hardware: camera=(), microphone=(), geolocation=()
        # Frontend allows self for video/camera: camera=(self), microphone=(self), geolocation=()
        passed = (
            api_perm is not None
            and "geolocation=()" in api_perm
            and front_perm is not None
            and "camera=(self)" in front_perm
        )
        record(
            "F-08",
            "Permissions-Policy is present with restrictive defaults",
            passed,
            f"api={api_perm}, frontend={front_perm}",
        )
    except Exception as e:
        record("F-08", "Permissions-Policy is present", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-09: Content-Security-Policy is present and not wildcard-open
    # -------------------------------------------------------------------------
    try:
        r_api = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        r_front = requests.get(f"{FRONTEND_BASE_URL}", timeout=10)
        api_csp = r_api.headers.get("content-security-policy", "")
        front_csp = r_front.headers.get("content-security-policy", "")

        api_safe = (api_csp and "default-src 'none'" in api_csp and "frame-ancestors 'none'" in api_csp)
        front_safe = (
            front_csp
            and "default-src 'self'" in front_csp
            and "script-src *" not in front_csp
            and "default-src *" not in front_csp
            and "frame-ancestors 'none'" in front_csp
        )
        passed = bool(api_safe and front_safe)
        record(
            "F-09",
            "Content-Security-Policy is present and not wildcard-open",
            passed,
            f"api_csp={api_csp[:50]}..., front_csp_len={len(front_csp)} chars",
        )
    except Exception as e:
        record("F-09", "Content-Security-Policy is present", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-10: HSTS behavior is production-aware
    # -------------------------------------------------------------------------
    try:
        # Plain HTTP localhost request should NOT have HSTS
        r_http = requests.get(f"{API_BASE_URL}/chat/sessions", timeout=5)
        hsts_http = r_http.headers.get("strict-transport-security")

        # Request simulated over HTTPS via x-forwarded-proto
        r_https = requests.get(
            f"{API_BASE_URL}/chat/sessions",
            headers={"x-forwarded-proto": "https"},
            timeout=5,
        )
        hsts_https = r_https.headers.get("strict-transport-security")

        passed = (hsts_http is None and hsts_https is not None and "max-age=" in hsts_https)
        record(
            "F-10",
            "HSTS behavior is production-aware",
            passed,
            f"http_hsts={hsts_http}, https_forwarded_hsts={hsts_https}",
        )
    except Exception as e:
        record("F-10", "HSTS behavior is production-aware", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-11: No password is stored in browser storage
    # -------------------------------------------------------------------------
    try:
        # Verify across frontend source files that passwords are never saved to localStorage or sessionStorage or cookies
        frontend_src = os.path.join(PROJECT_ROOT, "frontend")
        storage_patterns = [
            re.compile(r'localStorage\.setItem\([\'"][^\'"]*pass', re.IGNORECASE),
            re.compile(r'sessionStorage\.setItem\([\'"][^\'"]*pass', re.IGNORECASE),
            re.compile(r'Cookies\.set\([\'"][^\'"]*pass', re.IGNORECASE),
        ]
        violations = []
        for root, dirs, fnames in os.walk(frontend_src):
            if "node_modules" in root or ".next" in root:
                continue
            for f in fnames:
                if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        for lno, line in enumerate(fp, 1):
                            for pat in storage_patterns:
                                if pat.search(line):
                                    violations.append(f"{f}:{lno}")
        passed = (len(violations) == 0)
        record(
            "F-11",
            "No password is stored in browser storage",
            passed,
            f"violations={violations}",
        )
    except Exception as e:
        record("F-11", "No password is stored in browser storage", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-12: Logout clears authentication artifacts
    # -------------------------------------------------------------------------
    try:
        # Inspect clearStoredToken implementation in frontend/hooks/useAuth.tsx
        use_auth_path = os.path.join(PROJECT_ROOT, "frontend", "hooks", "useAuth.tsx")
        with open(use_auth_path, "r", encoding="utf-8") as f:
            code = f.read()

        clears_cookie = "Cookies.remove('token'" in code or "Cookies.remove(\"token\"" in code
        clears_local = "localStorage.removeItem('token'" in code or "localStorage.removeItem(\"token\"" in code
        clears_session = "sessionStorage.removeItem('token'" in code or "sessionStorage.removeItem(\"token\"" in code

        passed = (clears_cookie and clears_local and clears_session)
        record(
            "F-12",
            "Logout clears authentication artifacts",
            passed,
            f"clears_cookie={clears_cookie}, clears_localStorage={clears_local}, clears_sessionStorage={clears_session}",
        )
    except Exception as e:
        record("F-12", "Logout clears authentication artifacts", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-13: JWT storage behavior matches documented security policy
    # -------------------------------------------------------------------------
    try:
        # Documented policy: Token received via /token, stored in client cookie & localStorage for SPA bearer auth
        use_auth_path = os.path.join(PROJECT_ROOT, "frontend", "hooks", "useAuth.tsx")
        api_path = os.path.join(PROJECT_ROOT, "frontend", "lib", "api.ts")
        with open(use_auth_path, "r", encoding="utf-8") as f:
            auth_code = f.read()
        with open(api_path, "r", encoding="utf-8") as f:
            api_code = f.read()

        has_bearer_interceptor = "Bearer ${token}" in api_code or "Bearer " in api_code
        has_token_persistence = "persistToken" in auth_code
        has_get_token = "getStoredToken" in auth_code

        passed = (has_bearer_interceptor and has_token_persistence and has_get_token)
        record(
            "F-13",
            "JWT storage behavior matches documented security policy",
            passed,
            f"bearer_interceptor={has_bearer_interceptor}, token_persistence={has_token_persistence}",
        )
    except Exception as e:
        record("F-13", "JWT storage behavior matches documented policy", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-14: No API/provider secret is exposed through frontend environment variables
    # -------------------------------------------------------------------------
    try:
        env_path = os.path.join(PROJECT_ROOT, "frontend", ".env.local")
        forbidden_keywords = [
            "SECRET_KEY", "JWT_SECRET", "GROQ_API_KEY", "TWILIO",
            "FAST2SMS", "SMS_GATE", "GREENAPI", "GMAIL",
        ]
        leaks = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for lno, line in enumerate(f, 1):
                    for kw in forbidden_keywords:
                        if kw in line:
                            leaks.append(f"{kw} on line {lno}")

        passed = (len(leaks) == 0)
        record(
            "F-14",
            "No API/provider secret is exposed through frontend environment variables",
            passed,
            f"leaks={leaks}",
        )
    except Exception as e:
        record("F-14", "No API secret exposed in frontend env", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-15: No dangerouslySetInnerHTML in frontend source
    # -------------------------------------------------------------------------
    try:
        frontend_src = os.path.join(PROJECT_ROOT, "frontend")
        occurrences = []
        for root, dirs, fnames in os.walk(frontend_src):
            if "node_modules" in root or ".next" in root:
                continue
            for f in fnames:
                if f.endswith((".ts", ".tsx", ".js", ".jsx", ".html")):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        for lno, line in enumerate(fp, 1):
                            if "dangerouslySetInnerHTML" in line:
                                occurrences.append(f"{f}:{lno}")
        passed = (len(occurrences) == 0)
        record(
            "F-15",
            "No dangerouslySetInnerHTML in frontend source",
            passed,
            f"count={len(occurrences)}",
        )
    except Exception as e:
        record("F-15", "No dangerouslySetInnerHTML", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-16: No eval / new Function / javascript: URL execution in frontend source
    # -------------------------------------------------------------------------
    try:
        frontend_src = os.path.join(PROJECT_ROOT, "frontend")
        patterns = [
            re.compile(r'\beval\('),
            re.compile(r'new\s+Function\('),
            re.compile(r'href=[\'"]javascript:', re.IGNORECASE),
        ]
        unsafe_calls = []
        for root, dirs, fnames in os.walk(frontend_src):
            if "node_modules" in root or ".next" in root:
                continue
            for f in fnames:
                if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="replace") as fp:
                        for lno, line in enumerate(fp, 1):
                            for pat in patterns:
                                if pat.search(line):
                                    unsafe_calls.append(f"{f}:{lno}")
        passed = (len(unsafe_calls) == 0)
        record(
            "F-16",
            "No eval / new Function / javascript: URL execution in frontend source",
            passed,
            f"count={len(unsafe_calls)}",
        )
    except Exception as e:
        record("F-16", "No eval/new Function/javascript execution", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-17: External resource inventory matches CSP
    # -------------------------------------------------------------------------
    try:
        # Check that external origins in frontend code are accounted for in CSP
        next_config_path = os.path.join(PROJECT_ROOT, "frontend", "next.config.js")
        with open(next_config_path, "r", encoding="utf-8") as f:
            cfg = f.read()

        # Connect-src contains supabase and localhost backend
        has_supabase = "https://*.supabase.co" in cfg
        has_localhost = "http://localhost:8000" in cfg or "http://127.0.0.1:8000" in cfg
        passed = (has_supabase and has_localhost)
        record(
            "F-17",
            "External resource inventory matches CSP",
            passed,
            f"supabase_in_csp={has_supabase}, localhost_backend_in_csp={has_localhost}",
        )
    except Exception as e:
        record("F-17", "External resource inventory matches CSP", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-18: Normal login still works
    # -------------------------------------------------------------------------
    try:
        new_creds = generate_credentials("p5_login")
        reg_res = register_user(new_creds)
        log_res = login_user(new_creds["email"], new_creds["password"])
        passed = (reg_res.status_code == 200 and log_res.status_code == 200 and "access_token" in log_res.json())
        record(
            "F-18",
            "Normal login still works",
            passed,
            f"signup_status={reg_res.status_code}, login_status={log_res.status_code}",
        )
    except Exception as e:
        record("F-18", "Normal login still works", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-19: Normal authenticated API requests still work
    # -------------------------------------------------------------------------
    try:
        r_me = requests.get(
            f"{API_BASE_URL}/users/me",
            headers=auth_headers,
            timeout=5,
        )
        passed = (r_me.status_code == 200 and r_me.json().get("email") == creds["email"])
        record(
            "F-19",
            "Normal authenticated API requests still work",
            passed,
            f"status={r_me.status_code}, email={r_me.json().get('email')}",
        )
    except Exception as e:
        record("F-19", "Normal authenticated API requests still work", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # F-20: Normal chat workflow still works
    # -------------------------------------------------------------------------
    try:
        chat_payload = {
            "message": "Hello, I am feeling a bit tired today but managing well.",
            "language": "en",
        }
        r_chat = requests.post(
            f"{API_BASE_URL}/chat",
            json=chat_payload,
            headers=auth_headers,
            timeout=15,
        )
        passed = (r_chat.status_code == 200 and "reply" in r_chat.json() and "analysis" in r_chat.json())
        record(
            "F-20",
            "Normal chat workflow still works",
            passed,
            f"status={r_chat.status_code}, has_reply={'reply' in r_chat.json()}",
        )
    except Exception as e:
        record("F-20", "Normal chat workflow still works", False, str(e), is_error=True)

    print("=" * 80)
    print(f"FRONTEND SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    res = run_frontend_security_suite()
    if res["failed"] > 0 or res["errors"] > 0:
        sys.exit(1)
    sys.exit(0)
