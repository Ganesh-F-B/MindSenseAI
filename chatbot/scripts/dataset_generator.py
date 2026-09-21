import random
import pandas as pd


OUTPUT_FILE = "chatbot/datasets/raw/intent_dataset.csv"
SAMPLES_PER_INTENT = 500

# -------------------------
# Intent Templates
# -------------------------

INTENTS = {

    "greeting": {
        "templates": [
            "Hello",
            "Hi",
            "Hey",
            "Good morning",
            "Good evening",
            "Good afternoon",
            "Hi there",
            "Hello there",
            "Hey buddy",
            "Greetings",
            "Can we talk?",
            "Is anyone there?",
            "Hello MindSense",
            "Hi AI",
            "Nice to meet you"
        ]
    },

    "goodbye": {
        "templates": [
            "Bye",
            "Goodbye",
            "See you",
            "Talk to you later",
            "Take care",
            "Have a nice day",
            "Catch you later",
            "See you tomorrow",
            "I'm leaving now",
            "Bye for now"
        ]
    },

    "thanks": {
        "templates": [
            "Thank you",
            "Thanks",
            "Thank you so much",
            "I appreciate your help",
            "Many thanks",
            "Thanks a lot",
            "You helped me",
            "Thanks buddy",
            "Thank you AI",
            "Really appreciate it"
        ]
    }

}
rows = []

for intent, data in INTENTS.items():

    templates = data["templates"]

    for _ in range(SAMPLES_PER_INTENT):

        sentence = random.choice(templates)

        rows.append({
            "text": sentence,
            "intent": intent
        })

df = pd.DataFrame(rows)

df = df.sample(frac=1).reset_index(drop=True)

df.to_csv(OUTPUT_FILE, index=False)

print(f"Dataset saved to {OUTPUT_FILE}")
print(df.head())