import joblib

# Load model and vectorizer
model = joblib.load("mental_health_model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")

print("MENTAL HEALTH PREDICTION SYSTEM READY")

while True:

    user_input = input("\nEnter message (type quit to exit): ")

    if user_input.lower() == "quit":
        break

    # Convert input into TF-IDF vector
    input_vector = vectorizer.transform([user_input])

    # Predict mental state
    prediction = model.predict(input_vector)[0]

    # Get confidence scores
    probabilities = model.predict_proba(input_vector)[0]
    confidence = max(probabilities) * 100

    # Positive override logic
    positive_words = [
        "happy",
        "great",
        "excited",
        "good",
        "awesome",
        "fantastic",
        "joy",
        "love my life"
    ]

    lower_input = user_input.lower()

    if any(word in lower_input for word in positive_words):
        prediction = "Normal"
        confidence = 95.00

    # Risk level logic
    risk_level = "LOW"

    if prediction == "Depression":
        risk_level = "MEDIUM"

    elif prediction == "Anxiety":
        risk_level = "MEDIUM"

    elif prediction == "Suicidal":
        risk_level = "HIGH"

    # Output
    print("\n======================")
    print("PREDICTION RESULT")
    print("======================")
    print(f"Mental State : {prediction}")
    print(f"Confidence   : {confidence:.2f}%")
    print(f"Risk Level   : {risk_level}")

    # Alert logic
    if risk_level == "HIGH":
        print("\n⚠️ ALERT: Emergency support may be needed!")