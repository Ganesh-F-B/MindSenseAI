import os
import sys
import requests
from jose import jwt

SECRET_KEY = "cf05de79b2a81364"
ALGORITHM = "HS256"

token = jwt.encode({"sub": "ganeshfb2908@gmail.com"}, SECRET_KEY, algorithm=ALGORITHM)
headers = {"Authorization": f"Bearer {token}"}

inputs = [
    "i am streessed but",
    "feeling low today",
    "i am not low at all",
    "i feel completely stressed out",
]

BASE_URL = "http://127.0.0.1:8000"

print(f"{'Input':<32} | {'Mental State':<15} | {'Risk':<8} | {'Conf':<6}")
print("-" * 65)

for text in inputs:
    try:
        res = requests.post(
            f"{BASE_URL}/chat",
            json={"message": text, "language": "en"},
            headers=headers,
            timeout=30,
        )
        if res.status_code == 200:
            data = res.json()
            analysis = data.get("analysis", {})
            m_state = analysis.get("mental_state", "N/A")
            risk = analysis.get("risk_level", "N/A")
            conf = analysis.get("confidence", "N/A")
            print(f"{text:<32} | {m_state:<15} | {risk:<8} | {str(conf):<6}")
        else:
            print(f"{text:<32} | ERROR {res.status_code}")
    except Exception as e:
        print(f"{text:<32} | EXCEPTION: {e}")
