import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer

from chatbot.intent.config import *


class IntentDataset(Dataset):

    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, index):

        text = str(self.texts[index]).strip()

        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_attention_mask=True,
            return_token_type_ids=False,
            return_tensors="pt"
        )

        return {
            "text": text,
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(self.labels[index], dtype=torch.long)
        }


def load_data():

    df = pd.read_csv(RAW_DATA_DIR / "intent_dataset_v2.csv")

    print(f"\nOriginal Samples : {len(df)}")

    # Remove empty rows
    df = df.dropna(subset=["text", "intent"])

    # Remove empty strings
    df["text"] = df["text"].astype(str).str.strip()
    df["intent"] = df["intent"].astype(str).str.strip()

    df = df[df["text"] != ""]
    df = df[df["intent"] != ""]

    # Keep only supported intents
    df = df[df["intent"].isin(LABEL2ID.keys())]

    print(f"Valid Samples : {len(df)}")

    texts = df["text"].tolist()

    labels = df["intent"].map(LABEL2ID).tolist()

    print("\nIntent Distribution")

    print(df["intent"].value_counts())

    return texts, labels


def create_datasets():

    texts, labels = load_data()

    train_texts, temp_texts, train_labels, temp_labels = train_test_split(
        texts,
        labels,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=labels
    )
    from collections import Counter

    print("\nTraining Distribution")
    print(Counter(train_labels))

    val_texts, test_texts, val_labels, test_labels = train_test_split(
        temp_texts,
        temp_labels,
        test_size=0.50,
        random_state=RANDOM_SEED,
        stratify=None
    )

    tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_NAME,
        use_fast=False
    )

    train_dataset = IntentDataset(
        train_texts,
        train_labels,
        tokenizer,
        MAX_LENGTH
    )

    val_dataset = IntentDataset(
        val_texts,
        val_labels,
        tokenizer,
        MAX_LENGTH
    )

    test_dataset = IntentDataset(
        test_texts,
        test_labels,
        tokenizer,
        MAX_LENGTH
    )

    return train_dataset, val_dataset, test_dataset


def create_dataloaders():

    train_dataset, val_dataset, test_dataset = create_datasets()

    train_loader = DataLoader(
        train_dataset,
        batch_size=TRAIN_BATCH_SIZE,
        shuffle=True,
        num_workers=2,
        pin_memory=torch.cuda.is_available()
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=VALID_BATCH_SIZE,
        shuffle=False,
        num_workers=2,
        pin_memory=torch.cuda.is_available()
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=VALID_BATCH_SIZE,
        shuffle=False,
        num_workers=2,
        pin_memory=torch.cuda.is_available()
    )

    return train_loader, val_loader, test_loader