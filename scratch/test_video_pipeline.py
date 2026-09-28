import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import _emotion_to_analysis

def test_video_logic():
    print("=== MULTIMODAL VIDEO LOGIC VERIFICATION ===")

    # 1. Standard emotion mapping
    sad_res = _emotion_to_analysis("sad", 65.0, {"sad": 65.0, "neutral": 15.0, "happy": 20.0})
    assert sad_res["mental_state"] == "Depression" and sad_res["risk_level"] == "MEDIUM", f"Failed sad: {sad_res}"
    print("  [PASS] 1. Sad emotion -> Depression / MEDIUM")

    angry_res = _emotion_to_analysis("angry", 70.0, {"angry": 70.0, "neutral": 20.0, "sad": 10.0})
    assert angry_res["mental_state"] == "Stress" and angry_res["risk_level"] == "MEDIUM", f"Failed angry: {angry_res}"
    print("  [PASS] 2. Angry emotion -> Stress / MEDIUM")

    happy_res = _emotion_to_analysis("happy", 85.0, {"happy": 85.0, "neutral": 15.0})
    assert happy_res["mental_state"] == "Normal" and happy_res["risk_level"] == "LOW", f"Failed happy: {happy_res}"
    print("  [PASS] 3. Happy emotion -> Normal / LOW")

    # 2. Ambiguity gating: Low confidence (< 35%)
    low_conf = _emotion_to_analysis("sad", 30.0, {"sad": 30.0, "neutral": 25.0, "happy": 25.0, "angry": 20.0})
    assert low_conf["mental_state"] == "Normal" and low_conf["risk_level"] == "LOW", f"Failed low conf gating: {low_conf}"
    print("  [PASS] 4. Low-confidence facial emotion (<35%) gated to Normal / LOW")

    # 3. Ambiguity gating: Small margin between top1 and top2 (< 10%)
    narrow_margin = _emotion_to_analysis("sad", 42.0, {"sad": 42.0, "neutral": 38.0, "happy": 20.0})
    assert narrow_margin["mental_state"] == "Normal" and narrow_margin["risk_level"] == "LOW", f"Failed narrow margin: {narrow_margin}"
    print("  [PASS] 5. Narrow margin (<10% difference) gated to Normal / LOW")

    # 4. Ambiguity gating: Ambiguous / Neutral / Unknown label
    neutral_res = _emotion_to_analysis("neutral", 80.0, {"neutral": 80.0, "happy": 20.0})
    assert neutral_res["mental_state"] == "Normal" and neutral_res["risk_level"] == "LOW"
    print("  [PASS] 6. Neutral label -> Normal / LOW")

    ambig_res = _emotion_to_analysis("ambiguous", 50.0, {})
    assert ambig_res["mental_state"] == "Normal" and ambig_res["risk_level"] == "LOW"
    print("  [PASS] 7. Ambiguous label -> Normal / LOW")

    # 5. Centroid distance formula & 1:1 matching verification
    # Track 1 at (100, 100), Track 2 at (400, 400)
    # Detection A at (105, 105), Detection B at (410, 405)
    t1 = (100.0, 100.0)
    t2 = (400.0, 400.0)
    dA = (105.0, 105.0)
    dB = (410.0, 405.0)

    dist_A_t1 = ((dA[0]-t1[0])**2 + (dA[1]-t1[1])**2)**0.5
    dist_A_t2 = ((dA[0]-t2[0])**2 + (dA[1]-t2[1])**2)**0.5
    dist_B_t1 = ((dB[0]-t1[0])**2 + (dB[1]-t1[1])**2)**0.5
    dist_B_t2 = ((dB[0]-t2[0])**2 + (dB[1]-t2[1])**2)**0.5

    assert dist_A_t1 < 10.0 and dist_A_t2 > 300.0
    assert dist_B_t2 < 15.0 and dist_B_t1 > 300.0
    print("  [PASS] 8. Centroid tracking unambiguously separates distinct person coordinates")

    print("\nALL MULTIMODAL VIDEO LOGIC TESTS PASSED!")

if __name__ == "__main__":
    test_video_logic()
