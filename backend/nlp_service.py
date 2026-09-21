import os
import joblib

# ──────────────────────────────────────────────────────────────────────────────
# Resolve absolute paths relative to this file so the service works regardless
# of the working directory when the backend is launched (e.g. via uvicorn).
# ──────────────────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ML_DIR   = os.path.join(_BASE_DIR, "..", "ml_module")

MODEL_PATH      = os.path.join(_ML_DIR, "mental_health_model.pkl")
VECTORIZER_PATH = os.path.join(_ML_DIR, "tfidf_vectorizer.pkl")

# Load model and vectorizer once at module-import time
model      = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)

# ──────────────────────────────────────────────────────────────────────────────
# Positive-override keyword list
# ──────────────────────────────────────────────────────────────────────────────
POSITIVE_WORDS = [
    "happy",
    "great",
    "excited",
    "awesome",
    "fantastic",
    "joy",
]

# ──────────────────────────────────────────────────────────────────────────────
# Risk-level mapping
# ──────────────────────────────────────────────────────────────────────────────
RISK_LEVEL_MAP = {
    "Normal":     "LOW",
    "Anxiety":    "MEDIUM",
    "Depression": "MEDIUM",
    "Suicidal":   "HIGH",
}


def analyze_mental_state(user_message: str) -> dict:
    """
    Analyse the mental state expressed in *user_message* using the trained
    TF-IDF + Logistic-Regression model.

    Returns
    -------
    dict
        {
            "mental_state": str,   # "Normal" | "Anxiety" | "Depression" | "Suicidal"
            "confidence":   float, # 0–100, rounded to 2 decimal places
            "risk_level":   str,   # "LOW" | "MEDIUM" | "HIGH"
        }
    """
    # 1. Vectorize input text
    input_vector = vectorizer.transform([user_message])

    # 2. Predict mental state
    prediction = model.predict(input_vector)[0]

    # 3. Calculate confidence score (0–100)
    probabilities = model.predict_proba(input_vector)[0]
    confidence    = round(float(max(probabilities)) * 100, 2)

    # 4. Positive-override logic
    lower_message = user_message.lower()
    if any(word in lower_message for word in POSITIVE_WORDS):
        prediction = "Normal"
        confidence = 95.00

    # 5. Assign risk level (defaults to LOW for any unrecognised label)
    risk_level = RISK_LEVEL_MAP.get(prediction, "LOW")

    return {
        "mental_state": prediction,
        "confidence":   confidence,
        "risk_level":   risk_level,
    }