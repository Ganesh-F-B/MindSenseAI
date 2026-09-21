import sys
import json
from chatbot.conversation.chat_engine import ChatEngine
from backend.deberta_predictor import predict_mental_state
from chatbot.emotion.predictor import EmotionPredictor

def run_task5_phase3_verification():
    engine = ChatEngine()
    predictor = EmotionPredictor()

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    def record(name, condition, details=""):
        status = "PASSED" if condition else "FAILED"
        if condition:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append({
            "name": name,
            "status": status,
            "details": details
        })
        print(f"[{status}] {name} - {details}")

    print("=" * 80)
    print("TASK 5 PHASE 3 VERIFICATION: DOWNSTREAM MIXED-EMOTION INTEGRATION")
    print("=" * 80)

    # ---------------------------------------------------------
    # A. STRONG SINGLE EMOTION
    # ---------------------------------------------------------
    res_joy = predict_mental_state("I am absolutely thrilled and overjoyed today!")
    record(
        "A. Strong Joy -> Normal / LOW, is_mixed=False",
        res_joy["mental_state"] == "Normal" and res_joy["risk_level"] == "LOW" and res_joy["is_mixed"] is False,
        f"state={res_joy['mental_state']}, risk={res_joy['risk_level']}, is_mixed={res_joy['is_mixed']}"
    )

    res_sad = predict_mental_state("I am so sad, heartbroken, and completely depressed.")
    record(
        "A. Strong Sadness -> Depression / MEDIUM",
        res_sad["mental_state"] == "Depression" and res_sad["risk_level"] == "MEDIUM",
        f"state={res_sad['mental_state']}, risk={res_sad['risk_level']}"
    )

    # ---------------------------------------------------------
    # B. MIXED POSITIVE / NEGATIVE EMOTION
    # ---------------------------------------------------------
    # "I got the job offer which is amazing, but moving across the country terrifies me."
    # In Phase 2: Fear 71.41%, Joy 25.51%, is_mixed=True
    text_b = "I got the job offer which is amazing, but moving across the country terrifies me."
    an_b = engine.analyze(text_b)
    res_b = predict_mental_state(text_b)
    record(
        "B. Mixed Pos/Neg -> Secondary emotions preserved in ChatEngine",
        "secondary_emotions" in an_b and isinstance(an_b["secondary_emotions"], list),
        f"secondaries={an_b.get('secondary_emotions')}"
    )
    record(
        "B. Mixed Pos/Neg -> Secondary emotions preserved in predict_mental_state",
        "secondary_emotions" in res_b and isinstance(res_b["secondary_emotions"], list) and "is_mixed" in res_b,
        f"secondaries={res_b.get('secondary_emotions')}, is_mixed={res_b.get('is_mixed')}"
    )

    # ---------------------------------------------------------
    # C. MIXED EMOTION WITH NO CLINICAL DISTRESS
    # ---------------------------------------------------------
    # Joy + Sadness mixture in non-clinical context ("happy about promotion, sad to leave team")
    text_c = "I am happy about the promotion, but sad to leave my team."
    res_c = predict_mental_state(text_c)
    record(
        "C. Mixed with no clinical cue -> Must remain Normal / LOW",
        res_c["mental_state"] == "Normal" and res_c["risk_level"] == "LOW",
        f"state={res_c['mental_state']}, risk={res_c['risk_level']}"
    )

    # ---------------------------------------------------------
    # D. MIXED EMOTIONS WITH EXPLICIT DEPRESSION CUES
    # ---------------------------------------------------------
    # User has depression cues + mixed emotional elements
    text_d = "I am so deeply depressed and hopeless, even though my family tried to cheer me up."
    res_d = predict_mental_state(text_d)
    record(
        "D. Depression cue + mixed signals -> Retains Depression / MEDIUM",
        res_d["mental_state"] == "Depression" and res_d["risk_level"] == "MEDIUM",
        f"state={res_d['mental_state']}, risk={res_d['risk_level']}"
    )

    # ---------------------------------------------------------
    # E. MIXED EMOTIONS WITH EXPLICIT ANXIETY CUES
    # ---------------------------------------------------------
    text_e = "I am having severe anxiety and panic attacks about my future, but I try to smile."
    res_e = predict_mental_state(text_e)
    record(
        "E. Anxiety cue + mixed signals -> Retains Anxiety / MEDIUM",
        res_e["mental_state"] == "Anxiety" and res_e["risk_level"] == "MEDIUM",
        f"state={res_e['mental_state']}, risk={res_e['risk_level']}"
    )

    # ---------------------------------------------------------
    # F. MIXED EMOTIONS WITH EXPLICIT STRESS CUES
    # ---------------------------------------------------------
    text_f = "I am so stressed out with three exams and overloaded with work this week."
    res_f = predict_mental_state(text_f)
    record(
        "F. Stress cue + mixed signals -> Retains Stress / MEDIUM",
        res_f["mental_state"] == "Stress" and res_f["risk_level"] == "MEDIUM",
        f"state={res_f['mental_state']}, risk={res_f['risk_level']}"
    )

    # ---------------------------------------------------------
    # G. EXPLICIT CRISIS + MIXED EMOTION
    # ---------------------------------------------------------
    # Suicidal statement with mixed words
    text_g = "I want to die, even though today was a nice sunny day."
    res_g = predict_mental_state(text_g)
    record(
        "G. Crisis + mixed -> MUST remain Suicidal / HIGH (highest priority)",
        res_g["mental_state"] == "Suicidal" and res_g["risk_level"] == "HIGH",
        f"state={res_g['mental_state']}, risk={res_g['risk_level']}"
    )

    # ---------------------------------------------------------
    # H. CRISIS NEGATION + MIXED EMOTION
    # ---------------------------------------------------------
    text_h = "I do not want to die, but I have a lot of mixed feelings."
    res_h = predict_mental_state(text_h)
    record(
        "H. Crisis negation + mixed -> MUST remain Normal / LOW (no crisis)",
        res_h["mental_state"] == "Normal" and res_h["risk_level"] == "LOW",
        f"state={res_h['mental_state']}, risk={res_h['risk_level']}"
    )

    # ---------------------------------------------------------
    # I. POSITIVE / LIFE AFFIRMATION + MIXED EMOTION
    # ---------------------------------------------------------
    text_i = "I choose to keep living and fighting, despite feeling scared."
    res_i = predict_mental_state(text_i)
    record(
        "I. Life affirmation + mixed -> MUST remain Normal / LOW",
        res_i["mental_state"] == "Normal" and res_i["risk_level"] == "LOW",
        f"state={res_i['mental_state']}, risk={res_i['risk_level']}"
    )

    # ---------------------------------------------------------
    # J. ORDINARY / FACTUAL INPUT
    # ---------------------------------------------------------
    text_j = "Water freezes at zero degrees Celsius."
    an_j = engine.analyze(text_j)
    res_j = predict_mental_state(text_j)
    record(
        "J. Factual input -> ChatEngine emotion is neutral, is_mixed=False",
        an_j["emotion"] == "neutral" and an_j["is_mixed"] is False and len(an_j["secondary_emotions"]) == 0,
        f"emotion={an_j['emotion']}, is_mixed={an_j['is_mixed']}"
    )
    record(
        "J. Factual input -> predict_mental_state is Normal / LOW",
        res_j["mental_state"] == "Normal" and res_j["risk_level"] == "LOW",
        f"state={res_j['mental_state']}, risk={res_j['risk_level']}"
    )

    # ---------------------------------------------------------
    # K. UNSEEN PARAPHRASES & INVARIANCE ASSERTIONS
    # ---------------------------------------------------------
    # 1. Phase 2 distribution remains untouched
    raw_pred = predictor.predict("I feel bittersweet today.")
    record(
        "K1. Phase 2 predictor distribution intact (6 classes, sum ~100)",
        "distribution" in raw_pred and len(raw_pred["distribution"]) == 6 and 99.8 <= sum(raw_pred["distribution"].values()) <= 100.2,
        f"sum={sum(raw_pred.get('distribution', {}).values())}"
    )

    # 2. Primary emotion and confidence unchanged
    top_label = max(raw_pred["distribution"], key=raw_pred["distribution"].get)
    record(
        "K2. Primary emotion and confidence strictly match distribution max",
        raw_pred["emotion"] == top_label and raw_pred["confidence"] == raw_pred["distribution"][top_label],
        f"emotion={raw_pred['emotion']}, conf={raw_pred['confidence']}"
    )

    # 3. Mixed emotion alone cannot create HIGH risk
    mixed_sentences = [
        "I am feeling bittersweet about graduating and leaving all my close friends.",
        "I am so grateful and relieved, but part of me is still so anxious and worried.",
        "It was an emotional day, full of smiles and tears.",
        "Life has just been strange lately, neither good nor bad."
    ]
    for s in mixed_sentences:
        res_m = predict_mental_state(s)
        record(
            f"K3. Mixed sentence '{s[:30]}...' cannot be HIGH risk",
            res_m["risk_level"] != "HIGH",
            f"risk={res_m['risk_level']}, state={res_m['mental_state']}"
        )

    # Save results
    with open("C:/Users/ganes/.gemini/antigravity/brain/8c3811fe-a6e1-4f58-965b-8945e3ca6f0f/scratch/task5_phase3_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nTASK 5 PHASE 3 VERIFICATION SUMMARY: Passed={results['passed']}, Failed={results['failed']}, Total={len(results['tests'])}")
    return results["failed"] == 0

if __name__ == "__main__":
    success = run_task5_phase3_verification()
    sys.exit(0 if success else 1)
