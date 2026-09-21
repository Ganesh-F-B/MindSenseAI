import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
)

from chatbot.intent.config import *
from chatbot.intent.dataset import create_dataloaders
from chatbot.intent.model import IntentClassifier


def evaluate():

    print("=" * 60)
    print("MindSenseAI Intent Evaluation")
    print("=" * 60)

    _, _, test_loader = create_dataloaders()

    model = IntentClassifier().to(DEVICE)

    checkpoint = torch.load(
        BEST_MODEL_PATH,
        map_location=DEVICE
    )

    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model.eval()

    criterion = nn.CrossEntropyLoss()

    all_predictions = []
    all_labels = []

    total_loss = 0.0

    with torch.no_grad():

        for batch in test_loader:

            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["label"].to(DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            logits = outputs["logits"]

            loss = criterion(logits, labels)

            total_loss += loss.item()

            predictions = torch.argmax(logits, dim=1)

            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_predictions)

    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels,
        all_predictions,
        average="weighted",
        zero_division=0
    )

    print(f"\nTest Loss      : {total_loss / len(test_loader):.4f}")
    print(f"Test Accuracy  : {accuracy * 100:.2f}%")
    print(f"Precision      : {precision:.4f}")
    print(f"Recall         : {recall:.4f}")
    print(f"F1-Score       : {f1:.4f}")

    print("\nClassification Report")
    print("=" * 60)
    print(
        classification_report(
            all_labels,
            all_predictions,
            target_names=LABELS,
            zero_division=0
        )
    )

    print("\nConfusion Matrix")
    print("=" * 60)
    print(confusion_matrix(all_labels, all_predictions))


if __name__ == "__main__":
    evaluate()