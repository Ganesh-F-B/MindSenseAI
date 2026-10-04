"""
tests/security/test_upload_security.py

Comprehensive security test suite for MindSenseAI Upload Remediations (Phase 1).
Tests U-01 through U-16:
- Path traversal prevention (../, ..\\, absolute paths, Windows drive paths, NUL bytes)
- Format and signature enforcement (magic-byte validation)
- Streaming file size enforcement (413 Request Entity Too Large, chunked & Content-Length)
- User isolation and collision prevention
- Malicious filename sanitization
- Executable binary rejection
- Authentication enforcement (401)
- Temporary file lifecycle and cleanup guarantees
- Video resource constraints
"""

import os
import sys
import time
import uuid
import requests
import concurrent.futures
from typing import Dict, Any

# Target API base URL
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Test users credentials
USER_A = {
    "username": f"upload_sec_a_{uuid.uuid4().hex[:6]}@example.com",
    "password": "Password123!",
    "full_name": "Upload Sec User A",
}
USER_B = {
    "username": f"upload_sec_b_{uuid.uuid4().hex[:6]}@example.com",
    "password": "Password123!",
    "full_name": "Upload Sec User B",
}


def get_token(user_data: Dict[str, str]) -> str:
    # Attempt signup first
    try:
        requests.post(
            f"{BASE_URL}/signup",
            json={
                "email": user_data["username"],
                "password": user_data["password"],
                "full_name": user_data["full_name"],
                "phone_number": "+919999000010",
                "emergency_contacts": [
                    {"name": "Contact 1", "phone_number": "+919999000001"},
                    {"name": "Contact 2", "phone_number": "+919999000002"},
                ],
            },
            timeout=5,
        )
    except Exception:
        pass

    res = requests.post(
        f"{BASE_URL}/token",
        data={"username": user_data["username"], "password": user_data["password"]},
        timeout=5,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Failed to get token for {user_data['username']}: {res.text}")
    return res.json()["access_token"]


def run_upload_security_suite():
    results = {
        "suite": "MindSenseAI Upload Security Suite (Phase 1)",
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
    print("RUNNING MINDSENSEAI UPLOAD SECURITY TEST SUITE (U-01 through U-16)")
    print("=" * 80)

    _orig_post = requests.post
    def paced_post(url, **kwargs):
        res = _orig_post(url, **kwargs)
        if res.status_code == 429:
            retry = int(res.headers.get("Retry-After", 5))
            time.sleep(retry + 0.2)
            res = _orig_post(url, **kwargs)
        return res
    requests.post = paced_post

    # 1. Setup Auth
    try:
        token_a = get_token(USER_A)
        token_b = get_token(USER_B)
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("  [Setup] Test users A and B authenticated successfully.")
    except Exception as e:
        requests.post = _orig_post
        print(f"  [Setup Error] Authentication failed: {e}")
        record("U-00", "Authentication Setup", False, str(e), is_error=True)
        return results

    # Helper: Check if canary file exists outside temp dir
    canary_paths = [
        os.path.abspath("backend/canary.txt"),
        os.path.abspath("canary.txt"),
        os.path.abspath("backend/uploads/canary.txt"),
        os.path.abspath("uploads/canary.txt"),
    ]
    for p in canary_paths:
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    # -------------------------------------------------------------
    # U-01: ../canary.txt cannot escape temporary directory
    # -------------------------------------------------------------
    try:
        files = {"file": ("../canary.txt", b"Canary content for traversal probe", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        # Verify canary was not created anywhere on the filesystem
        canary_created = any(os.path.exists(p) for p in canary_paths)
        passed = (not canary_created) and (res.status_code == 200 or res.status_code == 400)
        record("U-01", "../canary.txt Traversal Probe", passed, f"status={res.status_code}, canary_created={canary_created}")
    except Exception as e:
        record("U-01", "../canary.txt Traversal Probe", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-02: ../../x traversal without valid extension
    # -------------------------------------------------------------
    try:
        files = {"file": ("../../x", b"raw content", "application/octet-stream")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code == 400 or (res.status_code == 200 and "Unsupported" in res.text)
        record("U-02", "../../x Multi-level Traversal Without Extension", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-02", "../../x Multi-level Traversal", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-02b: ..\\..\\x Windows backslash traversal
    # -------------------------------------------------------------
    try:
        files = {"file": ("..\\..\\x.txt", b"safe text content", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        # Even if accepted as text, must NOT write outside temp dir
        canary_created = any(os.path.exists(p) for p in canary_paths)
        passed = not canary_created
        record("U-02b", "..\\..\\x.txt Windows Backslash Traversal", passed, f"status={res.status_code}, escaped={canary_created}")
    except Exception as e:
        record("U-02b", "..\\..\\x.txt Windows Backslash Traversal", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-02c: Absolute path traversal (/etc/passwd.txt)
    # -------------------------------------------------------------
    try:
        files = {"file": ("/etc/passwd.txt", b"plain text content", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code in (200, 400)
        record("U-02c", "Absolute Unix Path In Filename", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-02c", "Absolute Unix Path In Filename", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-02d: Windows drive path (C:\\test.txt)
    # -------------------------------------------------------------
    try:
        files = {"file": ("C:\\test.txt", b"plain text content", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code in (200, 400)
        record("U-02d", "Windows Drive Path In Filename", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-02d", "Windows Drive Path In Filename", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-02e: NUL byte in filename
    # -------------------------------------------------------------
    try:
        files = {"file": ("test\x00evil.txt", b"content", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code == 400
        record("U-02e", "NUL Byte In Filename", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-02e", "NUL Byte In Filename", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-03: .mp4 containing plain text -> rejected
    # -------------------------------------------------------------
    try:
        files = {"file": ("fake_video.mp4", b"This is merely plain text masquerading as an MP4.", "video/mp4")}
        res = requests.post(f"{BASE_URL}/upload-video", headers=headers_a, files=files, timeout=5)
        # Should be rejected with 400 due to magic byte mismatch
        passed = res.status_code == 400 or (res.status_code == 200 and "error" in res.json())
        record("U-03", ".mp4 Containing Plain Text", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-03", ".mp4 Containing Plain Text", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-04: .txt containing PDF bytes -> rejected
    # -------------------------------------------------------------
    try:
        pdf_bytes = b"%PDF-1.4\n%fake pdf header\n1 0 obj\n<<>>\nendobj\n"
        files = {"file": ("fake_text.txt", pdf_bytes, "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code == 400
        record("U-04", ".txt Containing PDF Signature", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-04", ".txt Containing PDF Signature", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-05: File just above size limit -> 413
    # -------------------------------------------------------------
    try:
        # Text size limit is 1 MB (1048576 bytes). Generate 1.2 MB of text.
        oversized_text = b"A" * (1024 * 1024 + 200 * 1024)
        files = {"file": ("oversized.txt", oversized_text, "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=10)
        passed = res.status_code == 413
        record("U-05", "Text File Exceeding 1MB Limit -> 413", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-05", "Text File Exceeding 1MB Limit", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-06: Chunked upload without Content-Length exceeding limit -> 413
    # -------------------------------------------------------------
    try:
        def chunk_generator():
            chunk = b"B" * 65536
            # Yield 18 chunks = ~1.18 MB (exceeds 1 MB)
            for _ in range(18):
                yield chunk

        # Streaming upload with Transfer-Encoding: chunked (no Content-Length header)
        boundary = "----MindSenseChunkedBoundary"
        headers_chunked = {
            "Authorization": f"Bearer {token_a}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Transfer-Encoding": "chunked",
        }

        # Use requests with data generator
        def multipart_chunked():
            yield f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"chunked_over.txt\"\r\nContent-Type: text/plain\r\n\r\n".encode("utf-8")
            for c in chunk_generator():
                yield c
            yield f"\r\n--{boundary}--\r\n".encode("utf-8")

        res = requests.post(f"{BASE_URL}/upload", headers=headers_chunked, data=multipart_chunked(), timeout=10)
        passed = res.status_code == 413
        record("U-06", "Chunked Upload Without Content-Length -> 413", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-06", "Chunked Upload Without Content-Length", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-07: Empty / tiny audio -> existing safe behavior preserved
    # -------------------------------------------------------------
    try:
        # Less than 1KB audio file
        tiny_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 200
        files = {"file": ("silent.webm", tiny_audio, "audio/webm")}
        res = requests.post(f"{BASE_URL}/transcribe", headers=headers_a, files=files, timeout=5)
        # Should preserve safe behavior: returns {"text": ""}
        passed = res.status_code == 200 and res.json().get("text") == ""
        record("U-07", "Tiny / Silent Audio (<1KB) Safe Behavior", passed, f"status={res.status_code}, json={res.json()}")
    except Exception as e:
        record("U-07", "Tiny / Silent Audio Safe Behavior", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-08: Same filename twice by one user -> no collision
    # -------------------------------------------------------------
    try:
        files1 = {"file": ("notes.txt", b"First version of notes", "text/plain")}
        res1 = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files1, timeout=5)
        files2 = {"file": ("notes.txt", b"Second version of notes", "text/plain")}
        res2 = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files2, timeout=5)
        passed = (
            res1.status_code == 200
            and res2.status_code == 200
            and "First version" in res1.json().get("content", "")
            and "Second version" in res2.json().get("content", "")
        )
        record("U-08", "Same Filename Twice By One User", passed, f"res1={res1.status_code}, res2={res2.status_code}")
    except Exception as e:
        record("U-08", "Same Filename Twice By One User", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-09: Same filename by USER_A and USER_B concurrently -> no collision
    # -------------------------------------------------------------
    try:
        def upload_user(headers, content):
            f = {"file": ("shared_name.txt", content.encode("utf-8"), "text/plain")}
            return requests.post(f"{BASE_URL}/upload", headers=headers, files=f, timeout=5)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(upload_user, headers_a, "USER_A PRIVATE NOTE")
            future_b = executor.submit(upload_user, headers_b, "USER_B PRIVATE NOTE")
            ra = future_a.result()
            rb = future_b.result()

        content_a = ra.json().get("content", "")
        content_b = rb.json().get("content", "")

        passed = (
            ra.status_code == 200
            and rb.status_code == 200
            and "USER_A PRIVATE NOTE" in content_a
            and "USER_B PRIVATE NOTE" in content_b
            and "USER_B" not in content_a
            and "USER_A" not in content_b
        )
        record("U-09", "Concurrent Duplicate Filename Cross-User Isolation", passed, f"UserA len={len(content_a)}, UserB len={len(content_b)}")
    except Exception as e:
        record("U-09", "Concurrent Duplicate Filename Isolation", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-10: Malicious filename containing HTML, semicolon, unicode, spaces
    # -------------------------------------------------------------
    try:
        malicious_filename = "<script>alert(1)</script>;rm -rf;..test..file \u2603.txt"
        files = {"file": (malicious_filename, b"Valid safe text content inside.", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code == 200 and "Valid safe text" in res.json().get("content", "")
        record("U-10", "Malicious / XSS / Unicode Filename Sanitization", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-10", "Malicious Filename Sanitization", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-11: Executable-looking content renamed to allowed extension
    # -------------------------------------------------------------
    try:
        # Windows MZ header in a .txt file
        mz_binary = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 100
        files = {"file": ("malware.txt", mz_binary, "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)
        passed = res.status_code == 400
        record("U-11", "Executable MZ Binary Renamed to .txt", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-11", "Executable MZ Binary Renamed to .txt", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-12: Unauthenticated upload -> 401
    # -------------------------------------------------------------
    try:
        files = {"file": ("anonymous.txt", b"plain text", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", files=files, timeout=5)
        passed = res.status_code == 401
        record("U-12", "Unauthenticated /upload -> 401", passed, f"status={res.status_code}")
    except Exception as e:
        record("U-12", "Unauthenticated /upload", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-13: Successful upload leaves no temporary file
    # -------------------------------------------------------------
    try:
        import tempfile
        tmp_base = os.getenv(
            "UPLOAD_TMP_DIR",
            os.path.abspath(os.path.join(tempfile.gettempdir(), "mindsense_secure_uploads"))
        )
        files = {"file": ("cleanup_check.txt", b"Content that must be removed after handling.", "text/plain")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)

        # Check tmp_base: no active subdirectories should remain for this completed request
        time.sleep(0.1)
        subdirs_after = []
        if os.path.exists(tmp_base):
            for root, dirs, files_in_dir in os.walk(tmp_base):
                for f in files_in_dir:
                    subdirs_after.append(os.path.join(root, f))

        passed = res.status_code == 200 and len(subdirs_after) == 0
        record("U-13", "Successful Upload Lifecycle Cleanup", passed, f"status={res.status_code}, lingering_files={len(subdirs_after)}")
    except Exception as e:
        record("U-13", "Successful Upload Lifecycle Cleanup", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-14: Failed upload leaves no temporary file
    # -------------------------------------------------------------
    try:
        files = {"file": ("bad_sig.pdf", b"NOT A VALID PDF FILE AT ALL", "application/pdf")}
        res = requests.post(f"{BASE_URL}/upload", headers=headers_a, files=files, timeout=5)

        time.sleep(0.1)
        lingering = []
        if os.path.exists(tmp_base):
            for root, dirs, files_in_dir in os.walk(tmp_base):
                for f in files_in_dir:
                    lingering.append(os.path.join(root, f))

        passed = res.status_code == 400 and len(lingering) == 0
        record("U-14", "Failed Upload Lifecycle Cleanup", passed, f"status={res.status_code}, lingering_files={len(lingering)}")
    except Exception as e:
        record("U-14", "Failed Upload Lifecycle Cleanup", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-15: Oversized / corrupt video safely rejected
    # -------------------------------------------------------------
    try:
        # Corrupt video header (starts with ftyp but has 0 valid frames)
        corrupt_video = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 500
        files = {"file": ("corrupt.mp4", corrupt_video, "video/mp4")}
        res = requests.post(f"{BASE_URL}/upload-video", headers=headers_a, files=files, timeout=10)
        # Should be safely rejected with error message or 400
        passed = (res.status_code == 200 and "error" in res.json()) or res.status_code == 400
        record("U-15", "Corrupt Video Safely Rejected", passed, f"status={res.status_code}, response={res.text[:80]}")
    except Exception as e:
        record("U-15", "Corrupt Video Safely Rejected", False, str(e), is_error=True)

    # -------------------------------------------------------------
    # U-16: Multiple simultaneous uploads respect isolation & cleanup
    # -------------------------------------------------------------
    try:
        def perform_upload(idx):
            content = f"Simultaneous upload test payload index={idx}".encode("utf-8")
            f = {"file": (f"concurrent_{idx}.txt", content, "text/plain")}
            return requests.post(f"{BASE_URL}/upload", headers=headers_a, files=f, timeout=5)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(perform_upload, i) for i in range(5)]
            responses = [f.result() for f in futures]

        all_ok = all(r.status_code == 200 for r in responses)
        time.sleep(0.1)
        lingering = []
        if os.path.exists(tmp_base):
            for root, dirs, files_in_dir in os.walk(tmp_base):
                for f in files_in_dir:
                    lingering.append(os.path.join(root, f))

        passed = all_ok and len(lingering) == 0
        record("U-16", "Multiple Simultaneous Uploads Isolation & Cleanup", passed, f"all_200={all_ok}, lingering={len(lingering)}")
    except Exception as e:
        record("U-16", "Multiple Simultaneous Uploads", False, str(e), is_error=True)

    print("=" * 80)
    print(f"UPLOAD SECURITY SUITE SUMMARY: Total={results['total']}, Passed={results['passed']}, Failed={results['failed']}, Errors={results['errors']}")
    print("=" * 80)
    requests.post = _orig_post
    return results


if __name__ == "__main__":
    res = run_upload_security_suite()
    sys.exit(0 if res["failed"] == 0 and res["errors"] == 0 else 1)
