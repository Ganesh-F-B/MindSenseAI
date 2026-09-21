import random

INTENT_TEMPLATES = {

    "greeting": {
        "templates": [
            "{greeting}",
            "{greeting}, how are you?",
            "{greeting}, can we talk?",
            "{greeting}, I need your help.",
            "{greeting}! Nice to meet you.",
            "{greeting}! Are you there?",
            "{greeting}, I want to ask something.",
            "{greeting}, hope you're doing well.",
            "{greeting}! Can you help me today?"
        ],

        "greeting": [
            "Hello",
            "Hi",
            "Hey",
            "Good morning",
            "Good afternoon",
            "Good evening",
            "Greetings",
            "Hi there",
            "Hello there",
            "Hey buddy",
            "Hey AI",
            "Hello MindSense"
        ]
    },

    "goodbye": {
        "templates": [
            "{bye}",
            "{bye}, take care.",
            "{bye}, see you later.",
            "{bye}, have a nice day.",
            "{bye}! Talk to you soon.",
            "{bye}, I'll come back later."
        ],

        "bye": [
            "Bye",
            "Goodbye",
            "See you",
            "Take care",
            "Catch you later",
            "Talk to you later",
            "See you tomorrow",
            "Bye for now"
        ]
    },

    "thanks": {
        "templates": [
            "{thanks}",
            "{thanks} so much.",
            "I really appreciate it.",
            "{thanks}, you helped me a lot.",
            "Thanks for your support.",
            "I appreciate your help."
        ],

        "thanks": [
            "Thanks",
            "Thank you",
            "Many thanks",
            "Thank you very much",
            "Thanks a lot",
            "Really thanks"
        ]
    }

}