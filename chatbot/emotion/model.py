import torch
import torch.nn as nn

from transformers import AutoModel

from chatbot.emotion.config import *


class EmotionClassifier(nn.Module):

    def __init__(self):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(
            MODEL_NAME,
            return_dict=True,
            torch_dtype=torch.float32
        )

        hidden_size = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(DROPOUT)

        self.classifier = nn.Linear(
            hidden_size,
            NUM_LABELS
        )

    def forward(self, input_ids, attention_mask):

        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        cls_embedding = outputs.last_hidden_state[:, 0, :]

        cls_embedding = cls_embedding.float()

        cls_embedding = self.dropout(cls_embedding)

        logits = self.classifier(cls_embedding)

        return {
            "logits": logits,
            "embedding": cls_embedding
        }

    @torch.no_grad()
    def extract_embedding(self, input_ids, attention_mask):

        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        return outputs.last_hidden_state[:, 0, :].float()