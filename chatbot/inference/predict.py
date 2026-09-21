from chatbot.inference.predictor import EmotionPredictor

predictor = EmotionPredictor()

while True:

    text = input("\nYou: ")

    if text.lower() == "exit":
        break

    emotion, confidence = predictor.predict(text)

    print(f"Emotion   : {emotion}")
    print(f"Confidence: {confidence:.4f}")