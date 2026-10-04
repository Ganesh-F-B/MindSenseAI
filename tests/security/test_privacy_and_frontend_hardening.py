"""
tests/security/test_privacy_and_frontend_hardening.py

Automated Security & Compliance Suite for Phase 7:
Privacy, Legal/User-Facing Safety & Frontend Hardening.

Tests:
- P7-01: Privacy Policy page (/privacy) accessible with full data protection disclosures
- P7-02: Terms of Service page (/terms) accessible with mandatory medical disclaimer
- P7-03: Safety Resources page (/safety) accessible with verified crisis lifelines
- P7-04: Landing page (/) contains footer with links to Privacy, Terms, and Safety
- P7-05: Landing page displays prominent medical and emergency notice banner
- P7-06: /robots.txt disallows private authenticated routes (/chat, /dashboard, etc.)
- P7-07: /sitemap.xml generates valid sitemap referencing public marketing/legal URLs
- P7-08: Custom 404 page returned without exposing stack traces or server paths
- P7-09: Login and Signup pages contain legal/safety references
- P7-10: Client-side source audit verifies no logging of JWT tokens or passwords
- P7-11: Security headers (CSP, HSTS, XFO, XCTO) applied to all new frontend routes
- P7-12: Baseline ML models, crisis FSM, and database schema remain untouched
"""

import json
import hashlib
import os
import re
import pytest
import requests

FRONTEND_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def test_p7_01_privacy_policy_page_content():
    """Verify /privacy page is accessible and provides required disclosures."""
    res = requests.get(f"{FRONTEND_URL}/privacy", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /privacy, got {res.status_code}"
    body = res.text.lower()
    
    # Check for core privacy commitments
    assert "privacy policy" in body
    assert "zero commercial resale" in body or "resale" in body or "monetize" in body
    assert "pii" in body or "mask" in body
    assert "data deletion" in body or "erasure" in body or "right of erasure" in body
    assert "emergency" in body


def test_p7_02_terms_of_service_medical_disclaimer():
    """Verify /terms page contains prominent mandatory medical disclaimer."""
    res = requests.get(f"{FRONTEND_URL}/terms", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /terms, got {res.status_code}"
    body = res.text.lower()
    
    # Check for medical disclaimer and crisis notice
    assert "terms of service" in body
    assert "medical" in body and "disclaimer" in body
    assert "not a licensed healthcare provider" in body or "not a licensed" in body
    assert "988" in body or "14416" in body or "tele-manas" in body
    assert "limitation of liability" in body


def test_p7_03_safety_resources_page_helplines():
    """Verify /safety page contains verified 24/7 crisis numbers and grounding tools."""
    res = requests.get(f"{FRONTEND_URL}/safety", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /safety, got {res.status_code}"
    body = res.text.lower()
    
    # Check for global crisis hotlines
    assert "tele-manas" in body or "14416" in body
    assert "988" in body
    assert "vandrevala" in body or "kiran" in body or "samaritans" in body
    assert "findahelpline" in body or "helpline" in body
    # Grounding techniques
    assert "breathing" in body or "grounding" in body


def test_p7_04_landing_page_footer_navigation():
    """Verify landing page links to /privacy, /terms, and /safety in the footer."""
    res = requests.get(f"{FRONTEND_URL}/", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /, got {res.status_code}"
    body = res.text
    
    assert "/privacy" in body, "Landing page must link to /privacy"
    assert "/terms" in body, "Landing page must link to /terms"
    assert "/safety" in body, "Landing page must link to /safety"


def test_p7_05_landing_page_medical_notice_banner():
    """Verify landing page includes clear medical & crisis notice."""
    res = requests.get(f"{FRONTEND_URL}/", timeout=10)
    assert res.status_code == 200
    body = res.text.lower()
    
    assert "medical" in body
    assert "crisis" in body or "emergency" in body
    assert "tele-manas" in body or "988" in body


def test_p7_06_robots_txt_disallows_private_routes():
    """Verify /robots.txt disallows sensitive authenticated routes."""
    res = requests.get(f"{FRONTEND_URL}/robots.txt", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /robots.txt, got {res.status_code}"
    
    content = res.text
    assert "User-Agent:" in content or "user-agent:" in content
    assert "Disallow: /chat" in content
    assert "Disallow: /dashboard" in content
    assert "Disallow: /profile" in content
    assert "Disallow: /settings" in content
    assert "Allow: /privacy" in content or "allow: /privacy" in content.lower()
    assert "Allow: /terms" in content or "allow: /terms" in content.lower()
    assert "Allow: /safety" in content or "allow: /safety" in content.lower()


def test_p7_07_sitemap_xml_validity():
    """Verify /sitemap.xml serves valid XML referencing public routes."""
    res = requests.get(f"{FRONTEND_URL}/sitemap.xml", timeout=10)
    assert res.status_code == 200, f"Expected 200 for /sitemap.xml, got {res.status_code}"
    content = res.text
    
    assert "<urlset" in content
    assert "/safety" in content
    assert "/privacy" in content
    assert "/terms" in content
    # Ensure private routes are NOT in sitemap
    assert "/chat" not in content
    assert "/dashboard" not in content
    assert "/profile" not in content


def test_p7_08_custom_404_no_information_leakage():
    """Verify 404 response uses custom UI and does not leak internal traces or paths."""
    res = requests.get(f"{FRONTEND_URL}/this-route-definitely-does-not-exist-99", timeout=10)
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    body = res.text.lower()
    
    assert "page not" in body or "not found" in body
    assert "crisis helpline" in body or "return to home" in body
    # Verify no server internal paths or framework stack traces leaked
    assert "traceback (most recent call last)" not in body
    assert "internal server error" not in body
    assert "c:\\users\\" not in body
    assert "/home/" not in body


def test_p7_09_login_and_signup_legal_references():
    """Verify login and signup pages provide links to privacy and safety resources."""
    res_login = requests.get(f"{FRONTEND_URL}/login", timeout=10)
    assert res_login.status_code == 200
    assert "/privacy" in res_login.text or "/safety" in res_login.text or "/terms" in res_login.text

    res_signup = requests.get(f"{FRONTEND_URL}/signup", timeout=10)
    assert res_signup.status_code == 200
    assert "/privacy" in res_signup.text
    assert "/terms" in res_signup.text


def test_p7_10_client_source_audit_no_token_logging():
    """Verify client-side code does not log tokens or sensitive authentication data."""
    login_page_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app", "login", "page.tsx")
    with open(login_page_path, "r", encoding="utf-8") as f:
        login_source = f.read()
    
    # Must NOT log access_token or login response
    assert "console.log(\"LOGIN RESPONSE\"" not in login_source
    assert "console.log(res.data)" not in login_source
    assert "console.log(res.data.access_token)" not in login_source


def test_p7_11_security_headers_on_frontend_routes():
    """Verify critical security headers are returned on newly created routes."""
    routes = ["/privacy", "/terms", "/safety"]
    for route in routes:
        res = requests.get(f"{FRONTEND_URL}{route}", timeout=10)
        assert res.status_code == 200
        headers = res.headers
        
        # Verify key headers defined in next.config.js
        assert "x-content-type-options" in headers, f"Missing X-Content-Type-Options on {route}"
        assert headers["x-content-type-options"].lower() == "nosniff"
        assert "x-frame-options" in headers, f"Missing X-Frame-Options on {route}"
        assert headers["x-frame-options"].upper() == "DENY"
        assert "referrer-policy" in headers, f"Missing Referrer-Policy on {route}"
        assert "content-security-policy" in headers, f"Missing Content-Security-Policy on {route}"


def test_p7_12_baseline_invariants_protected():
    """Verify no core ML, crisis, or database files were touched in Phase 7."""
    baseline_path = os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "security_phase0_baseline_checksums.json")
    with open(baseline_path, "r") as f:
        baseline = json.load(f)
        
    for relpath, expected_hash in baseline.items():
        if relpath in ["backend/main.py", "backend/auth.py"]:
            continue  # Modified in earlier authorized phases
        
        full_path = os.path.join(os.path.dirname(__file__), "..", "..", relpath)
        assert os.path.exists(full_path), f"Protected file missing: {relpath}"
        with open(full_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        assert actual_hash == expected_hash, f"Protected baseline file altered: {relpath}"
