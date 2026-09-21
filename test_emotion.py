from chatbot.emotion.predictor import EmotionPredictor

predictor = EmotionPredictor()

texts = [
    "I am very happy today.",
    "I feel lonely.",
    "I am scared of my future.",
    "I am so angry.",
    "I love my parents."
]

for text in texts:
    result = predictor.predict(text)

    print("-" * 50)
    print("Input :", text)
    print("Output:", result)