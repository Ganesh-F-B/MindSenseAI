import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from torchvision.models import EfficientNet_B0_Weights
from sklearn.metrics import classification_report
from tqdm import tqdm

# ============================================================
# CONFIG
# ============================================================

TRAIN_DIR = "datasets/image/train"
TEST_DIR = "datasets/image/test"

MODEL_DIR = "models/image"
os.makedirs(MODEL_DIR, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 1e-4
IMAGE_SIZE = 224

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 60)
print("MindSense - EfficientNet-B0 Facial Emotion Training")
print("=" * 60)
print(f"Device: {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA: {torch.version.cuda}")
else:
    print("WARNING: CUDA is not available. Training will use CPU.")

# ============================================================
# DATA AUGMENTATION
# ============================================================

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(
        brightness=0.15,
        contrast=0.15
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

test_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ============================================================
# DATASET
# ============================================================

print("\nLoading datasets...")

train_dataset = datasets.ImageFolder(
    TRAIN_DIR,
    transform=train_transform
)

test_dataset = datasets.ImageFolder(
    TEST_DIR,
    transform=test_transform
)

class_names = train_dataset.classes
num_classes = len(class_names)

print(f"Classes: {class_names}")
print(f"Number of classes: {num_classes}")
print(f"Training images: {len(train_dataset)}")
print(f"Testing images: {len(test_dataset)}")

# Save class names
with open(
    os.path.join(MODEL_DIR, "class_names.json"),
    "w"
) as f:
    json.dump(class_names, f, indent=4)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)

# ============================================================
# MODEL
# ============================================================

print("\nLoading EfficientNet-B0...")

weights = EfficientNet_B0_Weights.DEFAULT

model = models.efficientnet_b0(weights=weights)

# Replace classifier
in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    num_classes
)

model = model.to(DEVICE)

# ============================================================
# LOSS + OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=2
)

# ============================================================
# TRAINING
# ============================================================

best_accuracy = 0.0

print("\nStarting training...")
print("=" * 60)

for epoch in range(EPOCHS):

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    progress = tqdm(
        train_loader,
        desc=f"Epoch {epoch + 1}/{EPOCHS}"
    )

    for images, labels in progress:

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        labels = labels.to(
            DEVICE,
            non_blocking=True
        )

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

        _, predicted = torch.max(
            outputs,
            1
        )

        total += labels.size(0)

        correct += (
            predicted == labels
        ).sum().item()

        accuracy = 100.0 * correct / total

        progress.set_postfix(
            loss=f"{loss.item():.4f}",
            acc=f"{accuracy:.2f}%"
        )

    train_accuracy = 100.0 * correct / total

    # ========================================================
    # VALIDATION
    # ========================================================

    model.eval()

    val_correct = 0
    val_total = 0

    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for images, labels in test_loader:

            images = images.to(
                DEVICE,
                non_blocking=True
            )

            labels = labels.to(
                DEVICE,
                non_blocking=True
            )

            outputs = model(images)

            _, predicted = torch.max(
                outputs,
                1
            )

            val_total += labels.size(0)

            val_correct += (
                predicted == labels
            ).sum().item()

            all_predictions.extend(
                predicted.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    val_accuracy = (
        100.0 * val_correct / val_total
    )

    scheduler.step(val_accuracy)

    print(
        f"\nEpoch {epoch + 1}/{EPOCHS}"
    )

    print(
        f"Train Accuracy: {train_accuracy:.2f}%"
    )

    print(
        f"Validation Accuracy: {val_accuracy:.2f}%"
    )

    print(
        f"Learning Rate: "
        f"{optimizer.param_groups[0]['lr']:.6f}"
    )

    # ========================================================
    # SAVE BEST MODEL
    # ========================================================

    if val_accuracy > best_accuracy:

        best_accuracy = val_accuracy

        checkpoint = {
            "model_state_dict": model.state_dict(),
            "class_names": class_names,
            "num_classes": num_classes,
            "image_size": IMAGE_SIZE,
            "best_accuracy": best_accuracy
        }

        torch.save(
            checkpoint,
            os.path.join(
                MODEL_DIR,
                "efficientnet_b0_emotion_best.pth"
            )
        )

        print(
            f"✓ Best model saved "
            f"({best_accuracy:.2f}%)"
        )

# ============================================================
# FINAL REPORT
# ============================================================

print("\n" + "=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)

print(
    f"Best Validation Accuracy: "
    f"{best_accuracy:.2f}%"
)

print("\nClassification Report:")

print(
    classification_report(
        all_labels,
        all_predictions,
        target_names=class_names,
        digits=4
    )
)

print("\nModel saved to:")

print(
    os.path.abspath(
        os.path.join(
            MODEL_DIR,
            "efficientnet_b0_emotion_best.pth"
        )
    )
)

print("\nClass names saved to:")

print(
    os.path.abspath(
        os.path.join(
            MODEL_DIR,
            "class_names.json"
        )
    )
)

print("\nMindSense image emotion training finished.")