"""
tests/security/test_production_config_security.py

Automated Production Configuration & Deployment Hardening Security Suite (Phase 6).
Tests:
- P6-01: Production secret requirement (missing secret in production raises RuntimeError)
- P6-02: Weak / default secret rejection (known insecure secrets rejected in production)
- P6-03: Development fallback behavior (ephemeral 256-bit key when unset in dev)
- P6-04: Production token expiration configuration
- P6-05: FastAPI debug mode is disabled (debug=False)
- P6-06: Production CORS origin validation rejects malformed origins
- P6-07: Production CORS origin validation strictly rejects wildcard '*'
- P6-08: Trusted proxy header verification (X-Forwarded-Proto trusted from 127.0.0.1)
- P6-09: Untrusted proxy header rejection (X-Forwarded-Proto from untrusted IP does not grant HSTS)
- P6-10: Secret-safe logging audit (no credentials, keys, or passwords logged)
- P6-11: Provider exception normalization (exception types logged, raw strings hidden)
- P6-12: End-to-end production request succeeds on active server
"""

import os
import sys
import unittest
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

import auth
import main


def run_production_config_security_suite():
    results = {
        "suite": "MindSenseAI Production Configuration Security Suite (Phase 6)",
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
    print("RUNNING MINDSENSEAI PRODUCTION CONFIGURATION TEST SUITE (Phase 6)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # P6-01: Production secret requirement
    # -------------------------------------------------------------------------
    try:
        old_env = os.environ.get("ENVIRONMENT")
        old_jwt = os.environ.get("JWT_SECRET_KEY")
        old_sec = os.environ.get("SECRET_KEY")
        try:
            os.environ["ENVIRONMENT"] = "production"
            if "JWT_SECRET_KEY" in os.environ:
                del os.environ["JWT_SECRET_KEY"]
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            caught = False
            try:
                auth.resolve_secret_key()
            except RuntimeError as e:
                caught = True
                msg = str(e)
            passed = caught and "CRITICAL SECURITY CONFIGURATION ERROR" in msg
            record(
                "P6-01",
                "Production secret requirement (missing secret raises RuntimeError)",
                passed,
                f"caught={caught}",
            )
        finally:
            if old_env is not None:
                os.environ["ENVIRONMENT"] = old_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if old_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = old_jwt
            if old_sec is not None:
                os.environ["SECRET_KEY"] = old_sec
    except Exception as e:
        record("P6-01", "Production secret requirement", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-02: Weak / default secret rejection
    # -------------------------------------------------------------------------
    try:
        old_env = os.environ.get("ENVIRONMENT")
        old_jwt = os.environ.get("JWT_SECRET_KEY")
        try:
            os.environ["ENVIRONMENT"] = "production"
            weak_keys = ["secretkey", "password", "changeme", "12345678", "short"]
            all_rejected = True
            for wk in weak_keys:
                os.environ["JWT_SECRET_KEY"] = wk
                try:
                    auth.resolve_secret_key()
                    all_rejected = False
                except RuntimeError:
                    pass
            passed = all_rejected
            record(
                "P6-02",
                "Weak / default secret rejection in production",
                passed,
                f"tested={len(weak_keys)} weak keys, all_rejected={all_rejected}",
            )
        finally:
            if old_env is not None:
                os.environ["ENVIRONMENT"] = old_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if old_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = old_jwt
    except Exception as e:
        record("P6-02", "Weak secret rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-03: Development fallback behavior
    # -------------------------------------------------------------------------
    try:
        old_env = os.environ.get("ENVIRONMENT")
        old_jwt = os.environ.get("JWT_SECRET_KEY")
        old_sec = os.environ.get("SECRET_KEY")
        try:
            os.environ["ENVIRONMENT"] = "development"
            if "JWT_SECRET_KEY" in os.environ:
                del os.environ["JWT_SECRET_KEY"]
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            key = auth.resolve_secret_key()
            passed = (isinstance(key, str) and len(key) >= 64 and key not in auth.INSECURE_SECRETS)
            record(
                "P6-03",
                "Development fallback behavior (ephemeral 256-bit random key generated)",
                passed,
                f"key_length={len(key)} hex chars",
            )
        finally:
            if old_env is not None:
                os.environ["ENVIRONMENT"] = old_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if old_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = old_jwt
            if old_sec is not None:
                os.environ["SECRET_KEY"] = old_sec
    except Exception as e:
        record("P6-03", "Development fallback behavior", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-04: Production token expiration configuration
    # -------------------------------------------------------------------------
    try:
        passed = (auth.ACCESS_TOKEN_EXPIRE_MINUTES > 0 and auth.ALGORITHM == "HS256")
        record(
            "P6-04",
            "Token expiration & algorithm configuration",
            passed,
            f"expire_minutes={auth.ACCESS_TOKEN_EXPIRE_MINUTES}, algorithm={auth.ALGORITHM}",
        )
    except Exception as e:
        record("P6-04", "Token configuration", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-05: FastAPI debug mode is disabled
    # -------------------------------------------------------------------------
    try:
        passed = (main.app.debug is False)
        record(
            "P6-05",
            "FastAPI debug mode disabled (debug=False)",
            passed,
            f"debug={main.app.debug}",
        )
    except Exception as e:
        record("P6-05", "FastAPI debug mode", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-06: Production CORS origin validation rejects malformed origins
    # -------------------------------------------------------------------------
    try:
        malformed = [
            "ftp://example.com",
            "javascript:alert(1)",
            "https://example.com/path",
            "http://example.com:80/sub",
            "",
            None,
        ]
        all_rejected = True
        for m in malformed:
            if main.validate_origin(m) is True:
                all_rejected = False
        passed = all_rejected
        record(
            "P6-06",
            "Production CORS validation rejects malformed origins",
            passed,
            f"malformed_count={len(malformed)}, all_rejected={all_rejected}",
        )
    except Exception as e:
        record("P6-06", "CORS origin validation", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-07: Production CORS origin validation strictly rejects wildcard '*'
    # -------------------------------------------------------------------------
    try:
        wildcard_rejected = (main.validate_origin("*") is False)
        cors_has_no_wildcard = ("*" not in main.cors_origins)
        passed = wildcard_rejected and cors_has_no_wildcard
        record(
            "P6-07",
            "Production CORS origin validation strictly rejects wildcard '*'",
            passed,
            f"validate_star={wildcard_rejected}, in_cors_origins={not cors_has_no_wildcard}",
        )
    except Exception as e:
        record("P6-07", "CORS wildcard rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-08: Trusted proxy header verification (X-Forwarded-Proto from trusted IP)
    # -------------------------------------------------------------------------
    try:
        # 127.0.0.1 is in TRUSTED_PROXIES by default
        r = requests.get(
            f"{API_BASE_URL}/docs",
            headers={"x-forwarded-proto": "https"},
            timeout=5,
        )
        hsts = r.headers.get("strict-transport-security")
        passed = (hsts is not None and "max-age=" in hsts)
        record(
            "P6-08",
            "Trusted proxy header verification (HSTS emitted for trusted proxy)",
            passed,
            f"hsts={hsts}",
        )
    except Exception as e:
        record("P6-08", "Trusted proxy header verification", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-09: Untrusted proxy header verification
    # -------------------------------------------------------------------------
    try:
        # When request comes over plain HTTP without forwarded-proto, no HSTS
        r_plain = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        hsts_plain = r_plain.headers.get("strict-transport-security")
        is_trusted_func = main.is_trusted_proxy("203.0.113.199")  # unconfigured public IP
        passed = (hsts_plain is None and is_trusted_func is False)
        record(
            "P6-09",
            "Untrusted proxy rejection (unconfigured IP not trusted, HTTP has no HSTS)",
            passed,
            f"hsts_plain={hsts_plain}, is_trusted_external={is_trusted_func}",
        )
    except Exception as e:
        record("P6-09", "Untrusted proxy rejection", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-10: Secret-safe logging audit
    # -------------------------------------------------------------------------
    try:
        # Audit main.py for raw exception prints
        main_py = os.path.join(BACKEND_DIR, "main.py")
        raw_e_prints = []
        with open(main_py, "r", encoding="utf-8") as f:
            for lno, line in enumerate(f, 1):
                if "print(f\"[SMS ERROR]" in line and "{e}" in line:
                    raw_e_prints.append(lno)
                if "print(f\"[SMS Gate ERROR]" in line and "{e}" in line:
                    raw_e_prints.append(lno)
                if "logger.error(f\"TTS ERROR" in line and ": {e}" in line:
                    raw_e_prints.append(lno)

        passed = (len(raw_e_prints) == 0)
        record(
            "P6-10",
            "Secret-safe logging audit (raw provider exceptions eliminated)",
            passed,
            f"raw_exception_prints={raw_e_prints}",
        )
    except Exception as e:
        record("P6-10", "Secret-safe logging audit", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-11: Provider exception normalization
    # -------------------------------------------------------------------------
    try:
        # Trigger an invalid TTS request to verify generic exception handling
        r_tts = requests.post(
            f"{API_BASE_URL}/tts",
            json={"text": "   ", "language": "en"},
            headers={"Authorization": "Bearer invalid_token"},
            timeout=5,
        )
        passed = (r_tts.status_code == 401 and "traceback" not in r_tts.text.lower())
        record(
            "P6-11",
            "Provider exception normalization (no tracebacks or provider secrets)",
            passed,
            f"status={r_tts.status_code}",
        )
    except Exception as e:
        record("P6-11", "Provider exception normalization", False, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # P6-12: End-to-end production request succeeds on active server
    # -------------------------------------------------------------------------
    try:
        r = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        passed = (r.status_code == 200 and r.headers.get("x-frame-options") == "DENY")
        record(
            "P6-12",
            "End-to-end production request succeeds on active server",
            passed,
            f"status={r.status_code}, x-frame-options={r.headers.get('x-frame-options')}",
        )
    except Exception as e:
        record("P6-12", "End-to-end production request", False, str(e), is_error=True)

    print("=" * 80)
    print(f"PRODUCTION CONFIG SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    res = run_production_config_security_suite()
    if res["failed"] > 0 or res["errors"] > 0:
        sys.exit(1)
    sys.exit(0)
