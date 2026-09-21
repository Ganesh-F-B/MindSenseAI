from chatbot.intent.predictor import IntentPredictor

predictor = IntentPredictor()

texts = [

    "I can't sleep at night.",

    "My parents fight every day.",

    "I feel very anxious about tomorrow.",

    "My girlfriend left me.",

    "I have no confidence in myself."

]

for text in texts:

    result = predictor.predict(text)

    print("-" * 60)
    print(text)
    print(result)