LABEL_TO_EMOTION = {
    0: "sadness",
    1: "joy",
    2: "love",
    3: "anger",
    4: "fear",
    5: "surprise"
}

EMOTION_TO_LABEL = {
    emotion: label
    for label, emotion in LABEL_TO_EMOTION.items()
}