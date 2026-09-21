import sys
import copy
import json
from chatbot.emotion.predictor import EmotionPredictor, interpret_emotion_distribution

def run_task5_phase2_verification():
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

    # ==========================================================
    # 1. SYNTHETIC DISTRIBUTION TESTS (Statistical Regimes)
    # ==========================================================

    # A. Strongly Concentrated (Dominant single emotion)
    dist_concentrated_1 = {"joy": 96.95, "sadness": 2.7, "anger": 0.27, "fear": 0.07, "love": 0.01, "surprise": 0.0}
    dist_copy = copy.deepcopy(dist_concentrated_1)
    interp_c1 = interpret_emotion_distribution(dist_concentrated_1)
    record(
        "Concentrated: Dominant joy (96.95%) is not mixed",
        interp_c1["is_mixed"] is False and interp_c1["pattern"] == "concentrated" and len(interp_c1["secondary"]) == 0,
        f"is_mixed={interp_c1['is_mixed']}, pattern={interp_c1['pattern']}"
    )
    record(
        "Concentrated: Raw distribution not mutated",
        dist_concentrated_1 == dist_copy,
        "Distribution untouched"
    )

    dist_concentrated_2 = {"sadness": 85.0, "anger": 8.0, "fear": 3.0, "joy": 2.0, "love": 1.0, "surprise": 1.0}
    interp_c2 = interpret_emotion_distribution(dist_concentrated_2)
    record(
        "Concentrated: 85% sadness is not mixed",
        interp_c2["is_mixed"] is False and interp_c2["pattern"] == "concentrated",
        f"is_mixed={interp_c2['is_mixed']}, pattern={interp_c2['pattern']}"
    )

    # B. Meaningfully Competing Signals (Bimodal / Trimodal)
    dist_competing_1 = {"joy": 65.59, "fear": 33.64, "anger": 0.59, "sadness": 0.12, "surprise": 0.04, "love": 0.02}
    interp_comp1 = interpret_emotion_distribution(dist_competing_1)
    record(
        "Competing: Joy 65.59% + Fear 33.64% is mixed",
        interp_comp1["is_mixed"] is True and interp_comp1["pattern"] == "competing" and len(interp_comp1["secondary"]) == 1 and interp_comp1["secondary"][0]["emotion"] == "fear",
        f"is_mixed={interp_comp1['is_mixed']}, secondary={interp_comp1['secondary']}"
    )

    dist_competing_2 = {"anger": 53.14, "fear": 43.69, "joy": 1.51, "sadness": 0.8, "love": 0.56, "surprise": 0.3}
    interp_comp2 = interpret_emotion_distribution(dist_competing_2)
    record(
        "Competing: Anger 53.14% + Fear 43.69% is mixed",
        interp_comp2["is_mixed"] is True and interp_comp2["pattern"] == "competing" and len(interp_comp2["secondary"]) == 1 and interp_comp2["secondary"][0]["emotion"] == "fear",
        f"is_mixed={interp_comp2['is_mixed']}, secondary={interp_comp2['secondary']}"
    )

    dist_competing_3 = {"fear": 71.41, "joy": 25.51, "anger": 1.41, "surprise": 1.36, "love": 0.16, "sadness": 0.15}
    interp_comp3 = interpret_emotion_distribution(dist_competing_3)
    record(
        "Competing: Fear 71.41% + Joy 25.51% is mixed",
        interp_comp3["is_mixed"] is True and interp_comp3["pattern"] == "competing" and any(s["emotion"] == "joy" for s in interp_comp3["secondary"]),
        f"is_mixed={interp_comp3['is_mixed']}, secondary={interp_comp3['secondary']}"
    )

    dist_competing_trimodal = {"sadness": 40.0, "anger": 30.0, "fear": 25.0, "joy": 2.0, "love": 2.0, "surprise": 1.0}
    interp_trimodal = interpret_emotion_distribution(dist_competing_trimodal)
    record(
        "Competing: Trimodal (40/30/25) identifies both secondaries",
        interp_trimodal["is_mixed"] is True and len(interp_trimodal["secondary"]) == 2,
        f"secondaries={[s['emotion'] for s in interp_trimodal['secondary']]}"
    )

    # C. Diffuse / High Uncertainty
    dist_diffuse_1 = {"sadness": 18.0, "joy": 17.0, "love": 16.0, "anger": 17.0, "fear": 16.0, "surprise": 16.0}
    interp_diff1 = interpret_emotion_distribution(dist_diffuse_1)
    record(
        "Diffuse: [18, 17, 16, 17, 16, 16] is NOT marked mixed",
        interp_diff1["is_mixed"] is False and interp_diff1["pattern"] == "diffuse" and len(interp_diff1["secondary"]) == 0,
        f"is_mixed={interp_diff1['is_mixed']}, pattern={interp_diff1['pattern']}"
    )

    dist_diffuse_uniform = {"sadness": 16.67, "joy": 16.67, "love": 16.67, "anger": 16.67, "fear": 16.67, "surprise": 16.67}
    interp_uniform = interpret_emotion_distribution(dist_diffuse_uniform)
    record(
        "Diffuse: Uniform 16.67% is NOT marked mixed",
        interp_uniform["is_mixed"] is False and interp_uniform["pattern"] in ["diffuse", "fallback"],
        f"is_mixed={interp_uniform['is_mixed']}, pattern={interp_uniform['pattern']}"
    )

    # D. Fallback Distributions (Structural Placeholders)
    dist_fallback_heuristic = {"anger": 35.0, "sadness": 13.0, "joy": 13.0, "fear": 13.0, "love": 13.0, "surprise": 13.0}
    interp_fb1 = interpret_emotion_distribution(dist_fallback_heuristic, is_fallback=True)
    record(
        "Fallback: Heuristic fallback (35 / 13) is NOT marked mixed",
        interp_fb1["is_mixed"] is False and interp_fb1["pattern"] == "fallback" and len(interp_fb1["secondary"]) == 0,
        f"is_mixed={interp_fb1['is_mixed']}, pattern={interp_fb1['pattern']}"
    )

    interp_fb_autodetect = interpret_emotion_distribution(dist_fallback_heuristic, is_fallback=False)
    record(
        "Fallback: Heuristic fallback auto-detected without flag",
        interp_fb_autodetect["is_mixed"] is False and interp_fb_autodetect["pattern"] == "fallback",
        f"is_mixed={interp_fb_autodetect['is_mixed']}, pattern={interp_fb_autodetect['pattern']}"
    )

    # ==========================================================
    # 2. MODEL PREDICTION TESTS ACROSS SEMANTIC CATEGORIES
    # ==========================================================
    test_cases = [
        # A. Strong single emotion
        ("I am absolutely ecstatic and thrilled beyond words!", "Strong Joy", False),
        ("I am heartbroken, devastated, and completely hopeless.", "Strong Sadness", False),
        ("I am completely furious and enraged at this betrayal!", "Strong Anger", False),
        ("I am utterly terrified and shaking with extreme panic.", "Strong Fear", False),

        # B. Clear competing emotions / Positive + Negative
        ("I am so grateful and relieved, but part of me is still so anxious and worried.", "Relief + Anxiety", True),
        ("I got the job offer which is amazing, but moving across the country terrifies me.", "Joy + Fear", True),

        # C. Love + Sadness
        ("I miss my late mother so much and love her with all my heart.", "Love + Sadness", None),

        # D. Ordinary factual statements
        ("The report is due tomorrow morning at nine o'clock.", "Factual", None),
        ("Water boils at 100 degrees Celsius under standard pressure.", "Factual Science", None),

        # E. Negated emotional statements
        ("I am not sad at all, actually I feel quite good.", "Negated Sadness", None),
        ("I am not afraid of failing.", "Negated Fear", None),

        # F. Unseen paraphrases
        ("I'm experiencing a whirlwind of conflicting emotions right now.", "Unseen Complex", None),
        ("Everything went great today, but a sudden dread keeps haunting me.", "Unseen Mixed", None)
    ]

    for text, label, expected_mixed in test_cases:
        res = predictor.predict(text)
        
        # 1. Verify Phase 1 completeness
        has_dist = "distribution" in res and len(res["distribution"]) == 6
        record(
            f"Model [{label}]: Phase 1 6-class distribution present",
            has_dist,
            f"classes={list(res.get('distribution', {}).keys())}"
        )
        
        # 2. Verify primary consistency
        top_from_dist = max(res["distribution"], key=res["distribution"].get)
        record(
            f"Model [{label}]: Primary emotion matches distribution max",
            res["emotion"] == top_from_dist,
            f"emotion={res['emotion']}, max_dist={top_from_dist}"
        )
        record(
            f"Model [{label}]: Primary confidence matches distribution max",
            res["confidence"] == res["distribution"][top_from_dist],
            f"confidence={res['confidence']}, max_conf={res['distribution'][top_from_dist]}"
        )

        # 3. Verify Phase 2 metadata present
        record(
            f"Model [{label}]: Secondary metadata present and well-formed",
            "secondary" in res and isinstance(res["secondary"], list) and "is_mixed" in res and isinstance(res["is_mixed"], bool) and "pattern" in res,
            f"is_mixed={res['is_mixed']}, pattern={res['pattern']}, secondary_count={len(res['secondary'])}"
        )

        # 4. If expected_mixed was specified, check it
        if expected_mixed is not None:
            record(
                f"Model [{label}]: Mixed emotion state matches expected ({expected_mixed})",
                res["is_mixed"] == expected_mixed,
                f"actual is_mixed={res['is_mixed']}, secondary={res['secondary']}"
            )

    # Save results
    with open("C:/Users/ganes/.gemini/antigravity/brain/8c3811fe-a6e1-4f58-965b-8945e3ca6f0f/scratch/task5_phase2_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nTASK 5 PHASE 2 VERIFICATION SUMMARY: Passed={results['passed']}, Failed={results['failed']}, Total={len(results['tests'])}")
    return results["failed"] == 0

if __name__ == "__main__":
    success = run_task5_phase2_verification()
    sys.exit(0 if success else 1)
