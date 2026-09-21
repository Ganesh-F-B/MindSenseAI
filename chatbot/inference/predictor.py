import torch
from transformers import AutoTokenizer

from chatbot.config.config import *
from chatbot.config.emotions import LABEL_TO_EMOTION
from chatbot.training.model import EmotionClassifier


class EmotionPredictor:

    def __init__(self):

        print("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

        print("Loading model...")
        self.model = EmotionClassifier().to(DEVICE)

        checkpoint = torch.load(
            BEST_MODEL_PATH,
            map_location=DEVICE
        )

        self.model.load_state_dict(checkpoint["model_state_dict"])

        self.model.eval()

        print("Emotion model loaded successfully!")

    @torch.no_grad()
    def predict(self, text):

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(DEVICE)
        attention_mask = encoding["attention_mask"].to(DEVICE)

        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs["logits"]

        probabilities = torch.softmax(logits, dim=1)

        confidence, prediction = torch.max(probabilities, dim=1)

        emotion = LABEL_TO_EMOTION[prediction.item()]

        return emotion, confidence.item()