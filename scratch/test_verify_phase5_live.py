import time
import requests

time.sleep(3)

print("Checking Backend (http://127.0.0.1:8000)...")
try:
    r_back = requests.get("http://127.0.0.1:8000/chat/sessions", timeout=5)
    print("Backend status:", r_back.status_code)
    print("Backend headers:")
    for k in ["x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy", "content-security-policy", "access-control-allow-origin"]:
        print(f"  {k}: {r_back.headers.get(k)}")
except Exception as e:
    print("Backend error:", e)

print("\nChecking Frontend (http://localhost:3000)...")
try:
    r_front = requests.get("http://localhost:3000", timeout=5)
    print("Frontend status:", r_front.status_code)
    print("Frontend headers:")
    for k in ["x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy", "content-security-policy", "x-powered-by"]:
        print(f"  {k}: {r_front.headers.get(k)}")
except Exception as e:
    print("Frontend error:", e)
