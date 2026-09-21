import torch
from transformers import AutoTokenizer

from chatbot.intent.config import *
from chatbot.intent.model import IntentClassifier


class IntentPredictor:

    def __init__(self):

        self.tokenizer = AutoTokenizer.from_pretrained(
            TOKENIZER_NAME,
            use_fast=False
        )

        self.model = IntentClassifier()

        checkpoint = torch.load(
            BEST_MODEL_PATH,
            map_location=DEVICE
        )

        # Support both checkpoint formats
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model.to(DEVICE)
        self.model.eval()

        self.id2label = {
            0: "relationship",
            1: "family",
            2: "depression",
            3: "anxiety",
            4: "self_esteem",
            5: "friendship",
            6: "breakup",
            7: "anger",
            8: "trauma",
            9: "stress",
            10: "addiction",
            11: "substance_abuse",
            12: "sleep_problem",
            13: "grief",
            14: "career_confusion",
            15: "suicidal_thought"
        }

    @torch.no_grad()
    def predict(self, text):

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(DEVICE)
        attention_mask = encoding["attention_mask"].to(DEVICE)

        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        probabilities = torch.softmax(outputs["logits"], dim=1)

        confidence, prediction = torch.max(
            probabilities,
            dim=1
        )

        return {
            "intent": self.id2label[prediction.item()],
            "confidence": round(confidence.item(), 4)
        }