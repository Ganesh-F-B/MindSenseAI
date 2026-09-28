import os
import sys
import json
import re

# Setup paths
PROJECT_ROOT = os.path.abspath(".")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from chatbot.conversation.chat_engine import ChatEngine
from backend.deberta_predictor import (
    predict_mental_state,
    _is_crisis,
    _is_negated_distress,
    _is_temporal_coping_context,
    _is_positive_context,
    _is_general_casual_context,
    _is_anxiety_context,
    _is_depression_context,
    _is_stress_context,
    _is_physical_health_context,
    _is_tired_context,
)

engine = ChatEngine()
intent_pred, emotion_pred = engine._get_predictors()

inputs = [
    "i am stressed but",
    "i feel low",
    "i am stressed",
    "i feel sad",
    "i am not stressed",
    "i am not low",
    "i feel like dying",
    "i will not die",
]

results = {}

for text in inputs:
    lower = text.lower().strip()
    clean = re.sub(r"['’`]", "", lower)
    clean = re.sub(r"[^\w\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Rule based analysis
    rule_res = engine._rule_based_analysis(text)

    # Raw model predictions
    raw_intent = intent_pred.predict(text)
    raw_emotion = emotion_pred.predict(text)

    # ChatEngine analyze
    engine_analysis = engine.analyze(text)

    # Check deberta_predictor flags
    flags = {
        "_is_crisis": _is_crisis(lower),
        "_is_negated_distress": _is_negated_distress(lower),
        "_is_temporal_coping_context": _is_temporal_coping_context(lower),
        "_is_positive_context": _is_positive_context(lower),
        "_is_general_casual_context": _is_general_casual_context(lower),
        "_is_anxiety_context": _is_anxiety_context(lower),
        "_is_depression_context": _is_depression_context(lower),
        "_is_stress_context": _is_stress_context(lower),
        "_is_physical_health_context": _is_physical_health_context(lower),
        "_is_tired_context": _is_tired_context(lower),
    }

    # Predict mental state as main.py calls it:
    # Notice in main.py:
    # analysis = predict_mental_state(translated_input, facial_emotion=..., facial_confidence=...)
    # without passing validated_emotion or validated_intent explicitly!
    pred_res_without_args = predict_mental_state(text)

    # And with validated args from engine_analysis:
    pred_res_with_args = predict_mental_state(
        text,
        validated_emotion=engine_analysis.get("emotion"),
        validated_intent=engine_analysis.get("intent"),
        secondary_emotions=engine_analysis.get("secondary_emotions"),
        is_mixed=engine_analysis.get("is_mixed"),
        pattern=engine_analysis.get("pattern"),
    )

    results[text] = {
        "text": text,
        "clean_text": clean,
        "rule_analysis": rule_res,
        "raw_intent": raw_intent,
        "raw_emotion": {
            "emotion": raw_emotion.get("emotion"),
            "confidence": raw_emotion.get("confidence"),
            "secondary": raw_emotion.get("secondary"),
            "is_mixed": raw_emotion.get("is_mixed"),
            "pattern": raw_emotion.get("pattern"),
            "distribution": raw_emotion.get("distribution"),
        },
        "engine_analysis": engine_analysis,
        "flags": flags,
        "pred_res_without_args": pred_res_without_args,
        "pred_res_with_args": pred_res_with_args,
    }

print(json.dumps(results, indent=2))
with open(os.path.join(PROJECT_ROOT, "scratch", "investigation_results.json"), "w") as f:
    json.dump(results, f, indent=2)
