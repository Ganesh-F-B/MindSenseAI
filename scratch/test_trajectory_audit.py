import os
import sys
import time
import uuid
import requests

API_BASE = "http://127.0.0.1:8000"

def run_trajectory():
    print("=== RUNNING FULL CONVERSATION TRAJECTORY (15 TURNS) ===")
    test_id = str(uuid.uuid4())[:8]
    email = f"trajectory_user_{test_id}@mindsenseai.org"
    password = f"TrajectoryPass123!_{test_id}"

    # 1. Sign up
    signup = requests.post(f"{API_BASE}/signup", json={
        "email": email,
        "password": password,
        "full_name": "Trajectory Student",
        "phone_number": "+919999000050",
        "emergency_contacts": [
            {"name": "Contact A1", "phone_number": "+919999000051"},
            {"name": "Contact A2", "phone_number": "+919999000052"},
        ]
    })
    assert signup.status_code == 200, f"Signup failed: {signup.text}"

    # 2. Token
    login = requests.post(f"{API_BASE}/token", data={"username": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 15 Conversation turns
    turns = [
        ("1. College normal", "Hey, college was okay today, just finished my morning lecture."),
        ("2. Project pressure", "Our professor just announced our final year project deadline is moved up by two weeks, and there is so much to build."),
        ("3. Stress", "I am feeling so stressed about getting everything working before the presentation."),
        ("4. Nervousness", "My hands are actually shaking a bit because I'm nervous about presenting in front of the department panel."),
        ("5. Friend support", "My project partner Alex said he will help me debug the backend tonight though, which feels supportive."),
        ("6. Positive emotion", "We actually got the first module working cleanly and that made me feel so relieved and happy!"),
        ("7. Disagreement/Conflict", "Then later we had a huge disagreement over the database schema and Alex got mad and stopped responding."),
        ("8. Low mood", "Now I feel really low and disheartened, like everything is falling apart again."),
        ("9. Overwhelm", "It just feels completely overwhelming having to carry the whole workload alone under this deadline."),
        ("10. Recovery", "I took a walk, drank some water, and realized I can handle the remaining tasks one step at a time."),
        ("11. Positive coping", "Even though I'm still stressed about tomorrow, I know I have a clear plan and I'm ready to tackle it."),
        ("12. Crisis statement", "For a brief moment during the argument I felt like dying because the pressure was too much."),
        ("13. Safety / De-escalation", "Don't worry though, I don't want to hurt myself at all. I am in a safe place, I want to live and finish this project."),
        ("14. Reflection", "Reflecting back, it's been an intense rollercoaster of a day."),
        ("15. Reflection test", "Do you remember everything I told you throughout our conversation? Based on everything I shared, can you tell me what I was going through, how my feelings changed from the beginning to the end, what seemed to be causing my stress, what helped me feel better, and how I am feeling now?")
    ]

    session_id = 0
    history = []

    for idx, (label, msg) in enumerate(turns, 1):
        payload = {
            "message": msg,
            "session_id": session_id,
            "history": history
        }
        resp = requests.post(f"{API_BASE}/chat", headers=headers, json=payload)
        assert resp.status_code == 200, f"Turn {idx} failed: {resp.text}"
        data = resp.json()
        reply = data.get("response", "")
        analysis = data.get("analysis", {})
        session_id = data.get("session_id", session_id)

        # Append to client-side history (last 10 turns maintained by client)
        history.append({"user": msg, "bot": reply})
        if len(history) > 10:
            history.pop(0)

        print(f"\n[TURN {idx}] {label}")
        print(f"  User: {msg}")
        print(f"  MindSense ({analysis.get('mental_state')}, Risk: {analysis.get('risk_level')}): {reply[:120]}...")
        time.sleep(1.3)

    print("\n--- Turn 15 Final Evaluation Response ---")
    print(reply)

if __name__ == "__main__":
    run_trajectory()
