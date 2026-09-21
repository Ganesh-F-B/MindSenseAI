import sys
from chatbot.emotion.predictor import EmotionPredictor

p = EmotionPredictor()
test_sentences = [
    "I am feeling bittersweet about graduating and leaving all my close friends.",
    "I am so grateful and relieved, but part of me is still so anxious and worried.",
    "It was an emotional day, full of smiles and tears.",
    "I love him but I hate the way he treats me.",
    "I am not sure how I feel, everything is just numb and flat.",
    "Today is Tuesday and the weather is partly cloudy with a chance of rain.",
    "Hello there, how are you doing today?",
    "I got the job offer which is amazing, but moving across the country terrifies me.",
    "I feel happy and sad.",
    "I'm terrified yet thrilled at the same time."
]

for s in test_sentences:
    res = p.predict(s)
    dist = sorted(res.get("distribution", {}).items(), key=lambda x: x[1], reverse=True)
    print(f"Text: {s}")
    print(f"  Top: {res['emotion']} ({res['confidence']}%)")
    print(f"  Dist: {dist}")
    print()
