print("ROBERTA TRAINING STARTED")
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import pandas as pd
import numpy as np
import re
import json
from datasets import Dataset
from transformers import (RobertaTokenizerFast,RobertaForSequenceClassification,Trainer,TrainingArguments)
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.utils.class_weight import compute_class_weight
import torch

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("mental_health_dataset.csv")

# Adjust columns if needed
TEXT_COLUMN = df.columns[1]
LABEL_COLUMN = df.columns[2]

df = df[[TEXT_COLUMN, LABEL_COLUMN]]
df.columns = ["text", "label"]

# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    text = str(text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

df["text"] = df["text"].apply(clean_text)

# Remove bad rows
df = df[df["text"].str.len() > 30]

# =========================
# LABEL ENCODING
# =========================
label_encoder = LabelEncoder()
df["label"] = label_encoder.fit_transform(df["label"])

num_labels = len(label_encoder.classes_)
print("Classes:", label_encoder.classes_)

# =========================
# CLASS WEIGHTS (IMPORTANT)
# =========================
class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(df["label"]),
    y=df["label"]
)

class_weights = torch.tensor(class_weights, dtype=torch.float)

# =========================
# DATASET
# =========================
dataset = Dataset.from_pandas(df)
dataset = dataset.train_test_split(test_size=0.1)

# =========================
# TOKENIZER
# =========================
tokenizer = RobertaTokenizerFast.from_pretrained("roberta-base")

def tokenize(example):
    return tokenizer(
        example["text"],
        truncation=True,
        padding="max_length",
        max_length=128
    )

dataset = dataset.map(tokenize, batched=True)
dataset = dataset.remove_columns(["text"])
dataset.set_format("torch")

# =========================
# MODEL
# =========================
model = RobertaForSequenceClassification.from_pretrained(
    "roberta-base",
    num_labels=num_labels
)

# =========================
# CUSTOM LOSS (CLASS WEIGHTS)
# =========================
from torch.nn import CrossEntropyLoss

def compute_loss(model, inputs, return_outputs=False):
    labels = inputs.get("labels")
    outputs = model(**inputs)
    logits = outputs.get("logits")

    loss_fct = CrossEntropyLoss(weight=class_weights.to(logits.device))
    loss = loss_fct(logits, labels)

    return (loss, outputs) if return_outputs else loss

# =========================
# METRICS
# =========================
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted"
    )
    acc = accuracy_score(labels, preds)

    return {
        "accuracy": acc,
        "f1": f1,
        "precision": precision,
        "recall": recall
    }

# =========================
# TRAINING CONFIG
# =========================
training_args = TrainingArguments(
    output_dir="./roberta_results",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=2,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="no",
    logging_dir="./logs",
    fp16=True
)

# =========================
# TRAINER
# =========================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

# override loss
trainer.compute_loss = compute_loss

# =========================
# TRAIN
# =========================
trainer.train()

# =========================
# SAVE MODEL
# =========================
trainer.save_model("./roberta_model")
tokenizer.save_pretrained("./roberta_model")

# Save label mapping
with open("label_map.json", "w") as f:
    json.dump(dict(enumerate(label_encoder.classes_)), f)

print("✅ RoBERTa training complete!")