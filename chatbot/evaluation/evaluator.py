import torch

from chatbot.config.config import *
from chatbot.training.dataset import create_dataloaders
from chatbot.training.model import EmotionClassifier

from chatbot.evaluation.metrics import (
    calculate_metrics,
    get_classification_report,
    get_confusion_matrix,
)

from chatbot.evaluation.plots import plot_confusion_matrix


CLASS_NAMES = [
    "sadness",
    "joy",
    "love",
    "anger",
    "fear",
    "surprise"
]


def evaluate():

    print("=" * 60)
    print("MindSenseAI Emotion Evaluation")
    print("=" * 60)

    _, _, test_loader = create_dataloaders()

    model = EmotionClassifier().to(DEVICE)

    checkpoint = torch.load(
        BEST_MODEL_PATH,
        map_location=DEVICE
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.eval()

    y_true = []
    y_pred = []

    with torch.no_grad():

        for batch in test_loader:

            input_ids = batch["input_ids"].to(DEVICE)

            attention_mask = batch["attention_mask"].to(DEVICE)

            labels = batch["label"].to(DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            predictions = torch.argmax(
                outputs["logits"],
                dim=1
            )

            y_true.extend(labels.cpu().numpy())

            y_pred.extend(predictions.cpu().numpy())

    metrics = calculate_metrics(
        y_true,
        y_pred
    )

    print("\nEvaluation Results")
    print("-" * 60)

    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall   : {metrics['recall']:.4f}")
    print(f"F1 Score : {metrics['f1_score']:.4f}")

    print("\nClassification Report")

    print(
        get_classification_report(
            y_true,
            y_pred,
            CLASS_NAMES
        )
    )

    cm = get_confusion_matrix(
        y_true,
        y_pred
    )

    plot_confusion_matrix(
        cm,
        CLASS_NAMES,
        save_path="results/confusion_matrix.png"
    )

    print("\nConfusion Matrix saved.")

    print("=" * 60)


if __name__ == "__main__":
    evaluate()