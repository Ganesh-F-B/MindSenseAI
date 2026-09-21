import torch

from chatbot.intent.config import *

try:
    from transformers import AutoTokenizer
except Exception:  # pragma: no cover - offline fallback
    AutoTokenizer = None

try:
    from chatbot.intent.model import IntentClassifier
except Exception:  # pragma: no cover - offline fallback
    IntentClassifier = None


class IntentPredictor:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self.tokenizer = None
        self.model = None
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
        self._load_model()

    def _load_model(self):
        try:
            if AutoTokenizer is None or IntentClassifier is None:
                raise RuntimeError("transformers or local intent model unavailable")
            self.tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME, use_fast=False)
            self.model = IntentClassifier()
            checkpoint = torch.load(BEST_MODEL_PATH, map_location=DEVICE)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                self.model.load_state_dict(checkpoint["model_state_dict"])
            else:
                self.model.load_state_dict(checkpoint)
            self.model.to(DEVICE)
            self.model.eval()
        except Exception as exc:
            print(f"[IntentPredictor] fallback mode: {exc}")
            self.tokenizer = None
            self.model = None

    def _fallback_predict(self, text: str):
        lower = (text or "").lower()
        if any(term in lower for term in ["sad", "depress", "hopeless", "worthless"]):
            intent = "depression"
        elif any(term in lower for term in ["angry", "furious", "annoyed"]):
            intent = "anger"
        elif any(term in lower for term in ["sleep", "tired", "insomnia"]):
            intent = "sleep_problem"
        elif any(term in lower for term in ["family", "mother", "father", "brother", "sister"]):
            intent = "family"
        elif any(term in lower for term in ["love", "relationship", "partner", "boyfriend", "girlfriend"]):
            intent = "relationship"
        elif any(term in lower for term in ["stress", "overwhelmed", "pressure"]):
            intent = "stress"
        else:
            intent = "stress"
        return {"intent": intent, "confidence": 0.35}

    @torch.no_grad()
    def predict(self, text):
        if not self.model or self.tokenizer is None:
            return self._fallback_predict(text)

        try:
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
            confidence, prediction = torch.max(probabilities, dim=1)
            return {
                "intent": self.id2label[prediction.item()],
                "confidence": round(confidence.item(), 4)
            }
        except Exception as exc:
            print(f"[IntentPredictor] prediction error: {exc}")
            return self._fallback_predict(text)