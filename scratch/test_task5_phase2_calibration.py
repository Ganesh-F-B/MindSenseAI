import sys
import math
import json
from collections import defaultdict
from chatbot.emotion.predictor import EmotionPredictor, interpret_emotion_distribution

def run_calibration_inspection():
    predictor = EmotionPredictor()
    
    # 15 semantic categories with ~5-7 diverse unseen sentences each (~90 total)
    dataset = [
        # 1. ordinary_factual
        ("ordinary_factual", "The train arrives at platform 4 at 5:30 PM."),
        ("ordinary_factual", "Water freezes at zero degrees Celsius under standard atmospheric pressure."),
        ("ordinary_factual", "The meeting has been rescheduled for Thursday afternoon."),
        ("ordinary_factual", "I received an email from the HR department regarding the holiday schedule."),
        ("ordinary_factual", "The library opens at 8 AM and closes at 9 PM on weekdays."),
        ("ordinary_factual", "The distance between the two cities is approximately 250 miles."),

        # 2. greetings
        ("greetings", "Good morning! How are you doing today?"),
        ("greetings", "Hello there, hope you are having a wonderful day."),
        ("greetings", "Hi, I just wanted to drop by and say hello."),
        ("greetings", "Good evening, everyone."),
        ("greetings", "Hey, what's up?"),

        # 3. gratitude
        ("gratitude", "Thank you so much for your assistance with my project."),
        ("gratitude", "I truly appreciate your thoughtful guidance and support."),
        ("gratitude", "Thanks a lot for listening to me today."),
        ("gratitude", "I am very thankful for the opportunity you gave me."),
        ("gratitude", "Many thanks for your prompt response."),

        # 4. positive_statements
        ("positive_statements", "I had such a pleasant afternoon walking in the sunshine."),
        ("positive_statements", "The concert last night was fantastic and full of energy."),
        ("positive_statements", "I am feeling refreshed and optimistic about the upcoming week."),
        ("positive_statements", "Our team achieved our quarterly goal ahead of schedule."),
        ("positive_statements", "I really enjoyed reading this fascinating book."),

        # 5. negative_statements
        ("negative_statements", "I feel completely drained and exhausted today."),
        ("negative_statements", "Everything seems so difficult and overwhelming right now."),
        ("negative_statements", "I am having such a horrible, frustrating day."),
        ("negative_statements", "It broke my heart when they canceled the community center."),
        ("negative_statements", "I am deeply disappointed with the outcome of the vote."),

        # 6. single_emotion_strong
        ("single_emotion_strong", "I am absolutely thrilled and overjoyed by this promotion!"),
        ("single_emotion_strong", "I am in tears, devastated and utterly heartbroken."),
        ("single_emotion_strong", "I am furious, enraged, and disgusted by this blatant lie!"),
        ("single_emotion_strong", "I am terrified, trembling with uncontrollable fear."),
        ("single_emotion_strong", "I love my family with every fiber of my being."),
        ("single_emotion_strong", "What an astonishing and completely unexpected shock!"),

        # 7. mixed_pos_neg
        ("mixed_pos_neg", "I got the job offer which is amazing, but moving across the country terrifies me."),
        ("mixed_pos_neg", "I am so happy for my sister's wedding, but I feel lonely about my own life."),
        ("mixed_pos_neg", "I am thrilled to start this venture, but scared of financial ruin."),
        ("mixed_pos_neg", "It was a bittersweet celebration saying goodbye to our dear colleagues."),
        ("mixed_pos_neg", "I won the competition, yet I feel sorrow for my opponent who worked so hard."),
        ("mixed_pos_neg", "I am proud of my graduation, but mourn the end of my youth."),

        # 8. two_negative
        ("two_negative", "I am furious that they lied to me, and it hurts so much that I can't stop crying."),
        ("two_negative", "I feel paralyzed with terror and simultaneously filled with bitter resentment."),
        ("two_negative", "I am disgusted by their cruelty and terrified of what they might do next."),
        ("two_negative", "A wave of grief and burning anger washed over me at once."),
        ("two_negative", "I am so stressed about my finances and panicked about losing my home."),

        # 9. two_positive
        ("two_positive", "I feel immense love and overwhelming joy holding my newborn daughter."),
        ("two_positive", "I was astonished and completely delighted by the surprise anniversary party."),
        ("two_positive", "A sense of deep gratitude and ecstatic joy filled the room."),
        ("two_positive", "I adore my friends and feel so wonderfully happy whenever we gather."),
        ("two_positive", "It was a magical evening filled with romantic love and pure happiness."),

        # 10. emotional_contrast
        ("emotional_contrast", "I loved the beautiful scenery, but the hotel staff treated us terribly."),
        ("emotional_contrast", "The presentation started out nerve-wracking, but finished on a triumphant high note."),
        ("emotional_contrast", "He is wonderfully charming in public, but frightfully mean behind closed doors."),
        ("emotional_contrast", "The dinner tasted delicious, but the shocking bill infuriated me."),
        ("emotional_contrast", "We were having so much fun until the sudden tragic phone call arrived."),

        # 11. temporal_change
        ("temporal_change", "Yesterday I was stressed and weeping, but today I feel excited and full of life."),
        ("temporal_change", "Last month was filled with terror, but now I feel completely calm and relieved."),
        ("temporal_change", "I used to hate my job with a passion, but lately I genuinely enjoy it."),
        ("temporal_change", "Earlier this morning I was raging with anger, but now I just feel peaceful."),
        ("temporal_change", "At first I was devastated by the rejection, but now I feel hopeful about new paths."),

        # 12. negated_emotional
        ("negated_emotional", "I am not sad at all, in fact I feel quite cheerful."),
        ("negated_emotional", "I do not feel any fear or anxiety about speaking in public."),
        ("negated_emotional", "I'm not angry with you, I just need some quiet time to think."),
        ("negated_emotional", "There is no hatred or bitterness in my heart."),
        ("negated_emotional", "I am certainly not depressed, just physically tired after the marathon."),

        # 13. neutral_routine
        ("neutral_routine", "I need to pick up groceries after finishing work today."),
        ("neutral_routine", "Please make sure to turn off the lights before leaving the office."),
        ("neutral_routine", "The thermostat is set to 72 degrees."),
        ("neutral_routine", "I have an appointment with the dentist next Tuesday at 10 AM."),
        ("neutral_routine", "The flight departs from Terminal 2 at gate B14."),

        # 14. ambiguous_statements
        ("ambiguous_statements", "I honestly don't know what to feel anymore, everything is just floating."),
        ("ambiguous_statements", "It is what it is, whatever happens will happen."),
        ("ambiguous_statements", "Life has just been strange lately, neither good nor bad."),
        ("ambiguous_statements", "I feel sort of disconnected from everything around me."),
        ("ambiguous_statements", "Things are just different now, hard to describe."),

        # 15. unseen_paraphrases
        ("unseen_paraphrases", "A bittersweet warmth enveloped me as we exchanged our final embraces."),
        ("unseen_paraphrases", "I find myself torn between exhilarating anticipation and creeping dread."),
        ("unseen_paraphrases", "His abrupt departure left behind an unsettling void of melancholy and disbelief."),
        ("unseen_paraphrases", "I am dancing with glee on the outside while mourning my lost solitude within."),
        ("unseen_paraphrases", "A tempest of conflicting sensations is swirling through my thoughts today.")
    ]

    records = []
    category_summary = defaultdict(lambda: {"total": 0, "concentrated": 0, "competing": 0, "diffuse": 0, "fallback": 0})
    pattern_counts = {"concentrated": 0, "competing": 0, "diffuse": 0, "fallback": 0}

    # Boundary proximity trackers
    # 1. Entropy boundary: norm_entropy in [0.85, 0.95] (threshold = 0.90)
    near_entropy_boundary = []
    # 2. Top-2 concentration boundary: top2_conc in [40.0, 50.0] (threshold = 45.0)
    near_top2_conc_boundary = []
    # 3. Primary confidence boundary: p1 in [75.0, 85.0] (threshold = 80.0) or [22.0, 28.0] (threshold = 25.0)
    near_p1_80_boundary = []
    near_p1_25_boundary = []
    # 4. Relative ratio boundary: r21 in [0.28, 0.38] (threshold = 0.33)
    near_rel_ratio_boundary = []
    # 5. Margin boundary: margin in [45.0, 55.0] (threshold = 50.0)
    near_margin_boundary = []
    # 6. Tail contrast boundary: tail_contrast in [1.5, 2.1] (threshold = 1.8)
    near_tail_contrast_boundary = []

    # Distribution integrity checks
    distribution_integrity_passed = True

    print("=" * 80)
    print("TASK 5 PHASE 2 CALIBRATION / ROBUSTNESS INSPECTION (REAL MODEL OUTPUTS)")
    print("=" * 80)

    for category, text in dataset:
        res = predictor.predict(text)
        dist = res.get("distribution", {})
        
        # Check distribution integrity
        top_dist_label = max(dist, key=dist.get) if dist else None
        top_dist_conf = dist.get(top_dist_label) if top_dist_label else None
        if res.get("emotion") != top_dist_label or res.get("confidence") != top_dist_conf:
            distribution_integrity_passed = False

        # Sorted probabilities
        sorted_p = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        p1_label, p1 = sorted_p[0]
        p2_label, p2 = sorted_p[1] if len(sorted_p) > 1 else ("", 0.0)
        
        top2_conc = p1 + p2
        margin = p1 - p2
        rel_ratio = p2 / p1 if p1 > 0 else 0.0
        
        tail = sorted_p[2:]
        tail_mean = (sum(v for _, v in tail) / len(tail)) if tail else 0.0
        tail_contrast = p2 / (tail_mean + 1e-5) if tail_mean > 0 else 999.0

        # Compute normalized entropy
        entropy = 0.0
        for _, p in sorted_p:
            p_norm = p / 100.0
            if p_norm > 1e-9:
                entropy -= p_norm * math.log(p_norm)
        norm_entropy = entropy / math.log(len(sorted_p))

        pattern = res.get("pattern", "unknown")
        is_mixed = res.get("is_mixed", False)
        secondaries = res.get("secondary", [])

        pattern_counts[pattern] += 1
        category_summary[category]["total"] += 1
        category_summary[category][pattern] += 1

        # Check boundary proximity
        if 0.85 <= norm_entropy <= 0.95:
            near_entropy_boundary.append((text, norm_entropy))
        if 40.0 <= top2_conc <= 50.0:
            near_top2_conc_boundary.append((text, top2_conc))
        if 75.0 <= p1 <= 85.0:
            near_p1_80_boundary.append((text, p1))
        if 22.0 <= p1 <= 28.0:
            near_p1_25_boundary.append((text, p1))
        if 0.28 <= rel_ratio <= 0.38:
            near_rel_ratio_boundary.append((text, rel_ratio))
        if 45.0 <= margin <= 55.0:
            near_margin_boundary.append((text, margin))
        if 1.5 <= tail_contrast <= 2.1:
            near_tail_contrast_boundary.append((text, tail_contrast))

        records.append({
            "category": category,
            "text": text,
            "primary": res.get("emotion"),
            "primary_confidence": res.get("confidence"),
            "distribution": dist,
            "secondary": secondaries,
            "is_mixed": is_mixed,
            "pattern": pattern,
            "norm_entropy": round(norm_entropy, 4),
            "top2_concentration": round(top2_conc, 2),
            "margin": round(margin, 2),
            "relative_ratio": round(rel_ratio, 2),
            "tail_contrast": round(tail_contrast, 2)
        })

    # Test Fallback Distributions specifically
    fb_text = "Testing fallback heuristic"
    fb_res = predictor._fallback_predict(fb_text)
    fb_interp = interpret_emotion_distribution(fb_res["distribution"], is_fallback=True)
    fb_pattern = fb_interp["pattern"]
    fb_is_mixed = fb_interp["is_mixed"]

    # Compile final results
    total_evaluated = len(dataset)
    results = {
        "total_evaluated": total_evaluated,
        "pattern_counts": pattern_counts,
        "pattern_percentages": {k: round(v / total_evaluated * 100, 2) for k, v in pattern_counts.items()},
        "category_summary": category_summary,
        "boundary_proximity": {
            "near_entropy_0_90": len(near_entropy_boundary),
            "near_top2_conc_45": len(near_top2_conc_boundary),
            "near_p1_80": len(near_p1_80_boundary),
            "near_p1_25": len(near_p1_25_boundary),
            "near_rel_ratio_0_33": len(near_rel_ratio_boundary),
            "near_margin_50": len(near_margin_boundary),
            "near_tail_contrast_1_8": len(near_tail_contrast_boundary),
            "details": {
                "near_entropy": near_entropy_boundary,
                "near_top2_conc": near_top2_conc_boundary,
                "near_p1_80": near_p1_80_boundary,
                "near_p1_25": near_p1_25_boundary,
                "near_rel_ratio": near_rel_ratio_boundary,
                "near_margin": near_margin_boundary,
                "near_tail_contrast": near_tail_contrast_boundary
            }
        },
        "fallback_test": {
            "pattern": fb_pattern,
            "is_mixed": fb_is_mixed
        },
        "distribution_integrity_passed": distribution_integrity_passed,
        "records": records
    }

    # Save to scratch directory
    output_path = "C:/Users/ganes/.gemini/antigravity/brain/8c3811fe-a6e1-4f58-965b-8945e3ca6f0f/scratch/task5_phase2_calibration_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Total Evaluated: {total_evaluated}")
    print(f"Pattern Counts: {pattern_counts}")
    print(f"Pattern %: {results['pattern_percentages']}")
    print(f"Distribution Integrity Passed: {distribution_integrity_passed}")
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    run_calibration_inspection()
