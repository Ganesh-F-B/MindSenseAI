import torch
import torch.nn.functional as F

from transformers import AutoTokenizer

from chatbot.config.config import *
from chatbot.training.model import EmotionClassifier
from chatbot.config.emotions import LABEL_TO_EMOTION


class EmotionPredictor:

    def __init__(self):

        self.device = DEVICE

        self.tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

        self.model = EmotionClassifier().to(self.device)

        checkpoint = torch.load(
            BEST_MODEL_PATH,
            map_location=self.device
        )

        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        self.model.eval()

    @torch.no_grad()
    def predict(self, text):

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs["logits"]

        probabilities = F.softmax(logits, dim=1)

        confidence, prediction = torch.max(probabilities, dim=1)

        emotion = LABEL_TO_EMOTION[prediction.item()]

        return {
            "emotion": emotion,
            "confidence": round(confidence.item() * 100, 2),
            "embedding": outputs["embedding"].cpu().numpy()
        }


if __name__ == "__main__":

    predictor = EmotionPredictor()

    while True:

        text = input("\nYou: ")

        if text.lower() == "exit":
            break

        result = predictor.predict(text)

        print(result)