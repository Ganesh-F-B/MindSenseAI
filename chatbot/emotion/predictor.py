import torch
import torch.nn.functional as F

try:
    from transformers import AutoTokenizer
except Exception:  # pragma: no cover - offline fallback
    AutoTokenizer = None

from chatbot.emotion.config import (
    MODEL_NAME,
    MAX_LENGTH,
    DEVICE,
    BEST_MODEL_PATH,
    ID2LABEL
)

try:
    from chatbot.emotion.model import EmotionClassifier
except Exception:  # pragma: no cover - offline fallback
    EmotionClassifier = None


import math
from typing import Dict, Any, List, Optional


def interpret_emotion_distribution(
    distribution: Dict[str, float],
    is_fallback: bool = False,
    primary: Optional[str] = None,
    primary_confidence: Optional[float] = None
) -> Dict[str, Any]:
    """
    Interprets a 6-class emotion probability distribution using a generalized relative-signal approach.
    
    Distinguishes:
    1. 'concentrated': Clearly dominant single emotion (is_mixed=False)
    2. 'competing': Meaningfully ambiguous/mixed model output (is_mixed=True)
    3. 'diffuse': Diffuse/uncertain prediction without clear consensus (is_mixed=False)
    4. 'fallback': Heuristic or placeholder values (is_mixed=False)
    
    Does NOT use a single fixed threshold (e.g. >20%).
    Does NOT alter the original distribution, primary emotion, or primary confidence.
    """
    if not distribution or not isinstance(distribution, dict):
        return {
            "primary": primary or "sadness",
            "primary_confidence": primary_confidence if primary_confidence is not None else 20.0,
            "secondary": [],
            "distribution": distribution or {},
            "is_mixed": False,
            "pattern": "fallback" if is_fallback else "diffuse",
        }

    # Normalize values if in 0-1 range rather than 0-100
    total_val = sum(distribution.values())
    scale = 100.0 / total_val if 0 < total_val <= 1.5 else 1.0

    scaled_dist = {k: v * scale for k, v in distribution.items()}
    
    # Sort items descending by probability
    sorted_items = sorted(scaled_dist.items(), key=lambda item: item[1], reverse=True)
    if not sorted_items:
        return {
            "primary": primary or "sadness",
            "primary_confidence": primary_confidence if primary_confidence is not None else 20.0,
            "secondary": [],
            "distribution": distribution,
            "is_mixed": False,
            "pattern": "fallback",
        }

    # Identify primary
    p1_label, p1_val = sorted_items[0]
    actual_primary = primary if (primary in distribution) else p1_label
    actual_primary_conf = distribution.get(actual_primary, p1_val)

    # Detect fallback signature if not explicitly set
    # Heuristic fallback: 1 class at 35.0, 5 classes at 13.0 (or all identical)
    unique_vals = set(round(v, 1) for v in scaled_dist.values())
    if is_fallback or (len(unique_vals) <= 2 and (13.0 in unique_vals or len(unique_vals) == 1)):
        return {
            "primary": actual_primary,
            "primary_confidence": actual_primary_conf,
            "secondary": [],
            "distribution": distribution,
            "is_mixed": False,
            "pattern": "fallback",
        }

    num_classes = len(sorted_items)
    uniform_prob = 100.0 / num_classes  # 16.67% for 6 classes

    # Compute normalized entropy: H(p) / ln(K)
    entropy = 0.0
    for _, p in sorted_items:
        prob_norm = (p / 100.0) if total_val > 0 else 0.0
        if prob_norm > 1e-9:
            entropy -= prob_norm * math.log(prob_norm)
    max_entropy = math.log(num_classes) if num_classes > 1 else 1.0
    norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    p2_val = sorted_items[1][1] if num_classes > 1 else 0.0
    top2_concentration = p1_val + p2_val
    tail_items = sorted_items[2:] if num_classes > 2 else []
    tail_mean = (sum(v for _, v in tail_items) / len(tail_items)) if tail_items else 0.0

    # 1. Check for Diffuse / High Uncertainty
    # If entropy is extremely high (norm_entropy >= 0.90) OR top-1 is below 25% (less than 1.5x uniform)
    # OR top-2 concentration is below 45% (more than 55% scattered in tail)
    if norm_entropy >= 0.90 or p1_val < 25.0 or top2_concentration < 45.0:
        return {
            "primary": actual_primary,
            "primary_confidence": actual_primary_conf,
            "secondary": [],
            "distribution": distribution,
            "is_mixed": False,
            "pattern": "diffuse",
        }

    # 2. Candidate Secondary Identification using Relative Signal
    candidate_secondaries = []
    for lbl, p in sorted_items[1:]:
        if lbl == actual_primary:
            continue
        rel_ratio = p / p1_val if p1_val > 0 else 0.0
        margin = p1_val - p
        tail_contrast = p / (tail_mean + 1e-5) if tail_mean > 0 else 2.0

        # Multi-factor relative signal criteria:
        # - Must exceed uniform random probability (p > 16.67%)
        # - Must have substantial relative strength to primary (rel_ratio >= 0.33)
        # - Margin must not be overwhelmingly large (margin < 50.0%)
        # - Must stand out distinctly from tail noise (tail_contrast >= 1.8)
        if p > uniform_prob and rel_ratio >= 0.33 and margin < 50.0 and tail_contrast >= 1.8:
            candidate_secondaries.append({
                "emotion": lbl,
                "confidence": round(distribution.get(lbl, p), 2),
                "relative_ratio": round(rel_ratio, 2),
            })

    # 3. Dominant / Concentrated vs Competing / Mixed
    dominance_ratio = p1_val / (p2_val + 1e-5) if p2_val > 0 else 999.0
    margin_top2 = p1_val - p2_val

    # Concentrated if:
    # - Primary is very dominant (p1 >= 80.0%)
    # - OR dominance ratio >= 3.0
    # - OR margin >= 50.0%
    # - OR no candidate secondaries meet the criteria
    if p1_val >= 80.0 or dominance_ratio >= 3.0 or margin_top2 >= 50.0 or not candidate_secondaries:
        return {
            "primary": actual_primary,
            "primary_confidence": actual_primary_conf,
            "secondary": [],
            "distribution": distribution,
            "is_mixed": False,
            "pattern": "concentrated",
        }

    # Competing / Meaningfully mixed
    return {
        "primary": actual_primary,
        "primary_confidence": actual_primary_conf,
        "secondary": candidate_secondaries,
        "distribution": distribution,
        "is_mixed": True,
        "pattern": "competing",
    }


class EmotionPredictor:
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
        self._load_model()

    def _load_model(self):
        try:
            if AutoTokenizer is None or EmotionClassifier is None:
                raise RuntimeError("transformers or local emotion model unavailable")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.model = EmotionClassifier()
            checkpoint = torch.load(BEST_MODEL_PATH, map_location=DEVICE)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.to(DEVICE)
            self.model.eval()
        except Exception as exc:
            print(f"[EmotionPredictor] fallback mode: {exc}")
            self.tokenizer = None
            self.model = None

    def interpret_distribution(self, distribution: Dict[str, float], is_fallback: bool = False) -> Dict[str, Any]:
        """Expose distribution interpretation on EmotionPredictor instance."""
        return interpret_emotion_distribution(distribution, is_fallback=is_fallback)

    def _fallback_predict(self, text: str):
        lower = (text or "").lower()
        if any(term in lower for term in ["angry", "annoyed", "frustrated"]):
            emotion = "anger"
        elif any(term in lower for term in ["happy", "great", "wonderful", "excited"]):
            emotion = "joy"
        elif any(term in lower for term in ["scared", "fear", "worried", "afraid"]):
            emotion = "fear"
        elif any(term in lower for term in ["love", "loving", "adore"]):
            emotion = "love"
        elif any(term in lower for term in ["surprise", "unexpected", "wow"]):
            emotion = "surprise"
        else:
            emotion = "sadness"

        # Fallback distribution: Heuristic match receives 35.0% (matching top-1 confidence).
        # The remaining 65.0% is distributed uniformly across the other 5 classes (13.0% each)
        # to ensure all 6 classes exist without falsely implying model-calibrated probabilities.
        fallback_conf = 35.0
        fallback_dist = {
            lbl: (fallback_conf if lbl == emotion else 13.0)
            for lbl in ID2LABEL.values()
        }

        interpretation = self.interpret_distribution(fallback_dist, is_fallback=True)

        return {
            "emotion": emotion,
            "confidence": fallback_conf,
            "distribution": fallback_dist,
            "secondary": interpretation["secondary"],
            "is_mixed": interpretation["is_mixed"],
            "pattern": interpretation["pattern"],
        }

    @torch.no_grad()
    def predict(self, text: str):
        if not self.model or self.tokenizer is None:
            return self._fallback_predict(text)

        try:
            encoding = self.tokenizer(
                text,
                max_length=MAX_LENGTH,
                padding="max_length",
                truncation=True,
                return_tensors="pt"
            )
            input_ids = encoding["input_ids"].to(DEVICE)
            attention_mask = encoding["attention_mask"].to(DEVICE)
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            logits = outputs["logits"]
            probabilities = F.softmax(logits, dim=1)
            confidence, prediction = torch.max(probabilities, dim=1)

            # Preserve full probability distribution across all 6 emotion classes
            probs_tensor = probabilities[0]
            distribution = {
                ID2LABEL[idx]: round(probs_tensor[idx].item() * 100, 2)
                for idx in range(len(ID2LABEL))
            }

            interpretation = self.interpret_distribution(distribution, is_fallback=False)

            return {
                "emotion": ID2LABEL[prediction.item()],
                "confidence": round(confidence.item() * 100, 2),
                "distribution": distribution,
                "secondary": interpretation["secondary"],
                "is_mixed": interpretation["is_mixed"],
                "pattern": interpretation["pattern"],
            }
        except Exception as exc:
            print(f"[EmotionPredictor] prediction error: {exc}")
            return self._fallback_predict(text)