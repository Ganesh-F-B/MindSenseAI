from chatbot.training.predictor import EmotionPredictor
from chatbot.intent.predictor import IntentPredictor


class NLPPipeline:

    def __init__(self):
        print("Loading Emotion Model...")
        self.emotion_predictor = EmotionPredictor()

        print("Loading Intent Model...")
        self.intent_predictor = IntentPredictor()

        print("NLP Pipeline Ready!")

    def predict(self, text):

        emotion_result = self.emotion_predictor.predict(text)
        intent_result = self.intent_predictor.predict(text)

        return {
            "text": text,
            "emotion": emotion_result,
            "intent": intent_result
        }