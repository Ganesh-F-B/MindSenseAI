import time
import json

import torch
import torch.nn as nn
import torch.optim as optim
from transformers import get_linear_schedule_with_warmup

from chatbot.emotion.config import *
from chatbot.emotion.dataset import create_dataloaders
from chatbot.emotion.model import EmotionClassifier
from chatbot.training.engine import train_one_epoch, validate_one_epoch

LINE = "=" * 60


def train():

    start_time = time.time()

    print(LINE)
    print("MindSenseAI Emotion Training")
    print(LINE)

    print(f"Model         : {MODEL_NAME}")
    print(f"Epochs        : {EPOCHS}")
    print(f"Batch Size    : {TRAIN_BATCH_SIZE}")
    print(f"Learning Rate : {LEARNING_RATE}")
    print(f"Device        : {DEVICE}")

    print(LINE)

    print("Loading Dataset...")
    train_loader, val_loader, test_loader = create_dataloaders()

    print("Loading Model...")
    model = EmotionClassifier().to(DEVICE)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    criterion = nn.CrossEntropyLoss()

    total_steps = len(train_loader) * EPOCHS

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps
    )

    best_accuracy = 0.0

    history = {
        "train_loss": [],
        "train_accuracy": [],
        "val_loss": [],
        "val_accuracy": []
    }

    print(LINE)
    print("Training Started")
    print(LINE)

    for epoch in range(EPOCHS):

        print(f"\nEpoch {epoch + 1}/{EPOCHS}")

        train_loss, train_acc = train_one_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            criterion,
            DEVICE
        )

        val_loss, val_acc = validate_one_epoch(
            model,
            val_loader,
            criterion,
            DEVICE
        )

        history["train_loss"].append(train_loss)
        history["train_accuracy"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_accuracy"].append(val_acc)

        print(f"Train Loss : {train_loss:.4f}")
        print(f"Train Acc  : {train_acc:.2f}%")
        print(f"Val Loss   : {val_loss:.4f}")
        print(f"Val Acc    : {val_acc:.2f}%")

        if val_acc > best_accuracy:

            best_accuracy = val_acc

            torch.save(
                {
                    "epoch": epoch + 1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "best_accuracy": best_accuracy,
                },
                BEST_MODEL_PATH,
            )

            print("✅ Best model saved!")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_DIR / "training_history.json", "w") as f:
        json.dump(history, f, indent=4)

    end_time = time.time()

    print(LINE)
    print("Training Finished")
    print(LINE)

    print(f"Best Validation Accuracy : {best_accuracy:.2f}%")
    print(f"Training Time : {(end_time - start_time) / 60:.2f} minutes")