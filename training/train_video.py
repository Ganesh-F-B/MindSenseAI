import os
import random
import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms

from sklearn.metrics import classification_report, confusion_matrix


# ============================================================
# CONFIGURATION
# ============================================================

CSV_PATH = "datasets/video_emotion/processed/metadata.csv"
MODEL_DIR = "models/video_emotion"

os.makedirs(MODEL_DIR, exist_ok=True)

SEED = 42
NUM_FRAMES = 16
IMAGE_SIZE = 224

BATCH_SIZE = 4
EPOCHS = 15
LEARNING_RATE = 1e-4

NUM_CLASSES = 8

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("MINDsense AI - VIDEO EMOTION TRAINING")
print("=" * 70)
print(f"Device: {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Reproducibility
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# LOAD METADATA
# ============================================================

df = pd.read_csv(CSV_PATH)

print("\nTotal frame records:", len(df))
print("Total videos:", df["video"].nunique())
print("Actors:", sorted(df["actor"].unique()))

# ------------------------------------------------------------
# IMPORTANT:
# Split by VIDEO, not individual frames.
# This prevents frames from the same video appearing in
# both training and validation/test sets.
# ------------------------------------------------------------

video_info = df[["video", "emotion", "emotion_id", "actor"]].drop_duplicates()

videos = video_info["video"].unique().tolist()

random.shuffle(videos)

n = len(videos)

train_end = int(n * 0.70)
val_end = int(n * 0.85)

train_videos = videos[:train_end]
val_videos = videos[train_end:val_end]
test_videos = videos[val_end:]

train_df = df[df["video"].isin(train_videos)].copy()
val_df = df[df["video"].isin(val_videos)].copy()
test_df = df[df["video"].isin(test_videos)].copy()

print("\nDataset split:")
print(f"Train videos: {len(train_videos)}")
print(f"Validation videos: {len(val_videos)}")
print(f"Test videos: {len(test_videos)}")


# ============================================================
# TRANSFORMS
# ============================================================

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
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

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# VIDEO DATASET
# ============================================================

class VideoEmotionDataset(Dataset):

    def __init__(self, dataframe, transform=None):

        self.transform = transform

        self.videos = []

        grouped = dataframe.groupby("video")

        for video_name, group in grouped:

            group = group.sort_values("frame")

            frame_paths = group["frame_path"].tolist()

            emotion_id = int(group["emotion_id"].iloc[0])-1
            emotion = group["emotion"].iloc[0]

            # We require NUM_FRAMES frames.
            if len(frame_paths) >= NUM_FRAMES:

                frame_paths = frame_paths[:NUM_FRAMES]

                self.videos.append({
                    "video": video_name,
                    "frames": frame_paths,
                    "label": emotion_id,
                    "emotion": emotion
                })

        print(f"Valid videos: {len(self.videos)}")

    def __len__(self):
        return len(self.videos)

    def __getitem__(self, index):

        item = self.videos[index]

        frames = []

        for path in item["frames"]:

            image = Image.open(path).convert("RGB")

            if self.transform:
                image = self.transform(image)

            frames.append(image)

        frames = torch.stack(frames)

        label = torch.tensor(
            item["label"],
            dtype=torch.long
        )

        return frames, label


# ============================================================
# DATASETS
# ============================================================

print("\nCreating datasets...")

train_dataset = VideoEmotionDataset(
    train_df,
    train_transform
)

val_dataset = VideoEmotionDataset(
    val_df,
    eval_transform
)

test_dataset = VideoEmotionDataset(
    test_df,
    eval_transform
)


# ============================================================
# DATALOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)


# ============================================================
# MODEL
# CNN + LSTM
# ============================================================

class VideoEmotionModel(nn.Module):

    def __init__(self, num_classes=8):

        super().__init__()

        # ResNet18 extracts facial features from each frame.
        backbone = models.resnet18(
            weights=models.ResNet18_Weights.DEFAULT
        )

        feature_size = backbone.fc.in_features

        backbone.fc = nn.Identity()

        self.cnn = backbone

        # Temporal model
        self.lstm = nn.LSTM(
            input_size=feature_size,
            hidden_size=256,
            num_layers=2,
            batch_first=True,
            dropout=0.3
        )

        self.dropout = nn.Dropout(0.4)

        self.classifier = nn.Linear(
            256,
            num_classes
        )

    def forward(self, x):

        # x:
        # [batch, frames, channels, height, width]

        batch_size, frames, C, H, W = x.shape

        # Flatten frames so CNN processes them
        # independently.
        x = x.view(
            batch_size * frames,
            C,
            H,
            W
        )

        features = self.cnn(x)

        # Restore temporal dimension
        features = features.view(
            batch_size,
            frames,
            -1
        )

        # LSTM learns temporal emotion changes.
        output, _ = self.lstm(features)

        # Last timestep
        output = output[:, -1, :]

        output = self.dropout(output)

        output = self.classifier(output)

        return output


# ============================================================
# INITIALIZE MODEL
# ============================================================

model = VideoEmotionModel(NUM_CLASSES)

model = model.to(DEVICE)

print("\nModel:")
print(model)


# ============================================================
# LOSS / OPTIMIZER
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
# TRAINING FUNCTION
# ============================================================

def train_one_epoch():

    model.train()

    total_loss = 0
    correct = 0
    total = 0

    for videos, labels in train_loader:

        videos = videos.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(videos)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()

        total_loss += loss.item()

        predictions = outputs.argmax(dim=1)

        correct += (
            predictions == labels
        ).sum().item()

        total += labels.size(0)

    accuracy = 100 * correct / total

    return total_loss / len(train_loader), accuracy


# ============================================================
# VALIDATION
# ============================================================

def evaluate(loader):

    model.eval()

    total_loss = 0
    correct = 0
    total = 0

    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for videos, labels in loader:

            videos = videos.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(videos)

            loss = criterion(
                outputs,
                labels
            )

            total_loss += loss.item()

            predictions = outputs.argmax(dim=1)

            correct += (
                predictions == labels
            ).sum().item()

            total += labels.size(0)

            all_predictions.extend(
                predictions.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    accuracy = 100 * correct / total

    return (
        total_loss / len(loader),
        accuracy,
        all_labels,
        all_predictions
    )


# ============================================================
# TRAIN
# ============================================================

best_val_accuracy = 0

print("\n" + "=" * 70)
print("STARTING TRAINING")
print("=" * 70)

for epoch in range(EPOCHS):

    train_loss, train_acc = train_one_epoch()

    val_loss, val_acc, _, _ = evaluate(
        val_loader
    )

    scheduler.step(val_acc)

    print(
        f"\nEpoch [{epoch + 1}/{EPOCHS}]"
    )

    print(
        f"Train Loss: {train_loss:.4f} | "
        f"Train Accuracy: {train_acc:.2f}%"
    )

    print(
        f"Val Loss: {val_loss:.4f} | "
        f"Val Accuracy: {val_acc:.2f}%"
    )

    # Save best model
    if val_acc > best_val_accuracy:

        best_val_accuracy = val_acc

        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "val_accuracy": val_acc,
                "num_classes": NUM_CLASSES
            },
            os.path.join(
                MODEL_DIR,
                "best_video_emotion_model.pth"
            )
        )

        print("✓ Best model saved!")


# ============================================================
# LOAD BEST MODEL
# ============================================================

best_model_path = os.path.join(
    MODEL_DIR,
    "best_video_emotion_model.pth"
)

checkpoint = torch.load(
    best_model_path,
    map_location=DEVICE
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)


# ============================================================
# FINAL TEST
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST")
print("=" * 70)

test_loss, test_accuracy, labels, predictions = evaluate(
    test_loader
)

print(f"\nTest Loss: {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy:.2f}%")

emotion_names = [
    "neutral",
    "calm",
    "happy",
    "sad",
    "angry",
    "fear",
    "disgust",
    "surprise"
]

print("\nClassification Report:")

print(
    classification_report(
        labels,
        predictions,
        labels=list(range(NUM_CLASSES)),
        target_names=emotion_names,
        zero_division=0
    )
)

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        labels,
        predictions
    )
)


# ============================================================
# SAVE FINAL MODEL
# ============================================================

final_path = os.path.join(
    MODEL_DIR,
    "video_emotion_model_final.pth"
)

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "test_accuracy": test_accuracy,
        "emotion_names": emotion_names
    },
    final_path
)

print("\n" + "=" * 70)
print("VIDEO EMOTION TRAINING COMPLETE")
print("=" * 70)

print(f"Best validation accuracy: {best_val_accuracy:.2f}%")
print(f"Final test accuracy: {test_accuracy:.2f}%")
print(f"Model saved: {final_path}")