import os
import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import models, transforms


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "models/video_emotion/video_emotion_model_final.pth"

FRAMES_PER_VIDEO = 16
IMAGE_SIZE = 224

EMOTIONS = [
    "neutral",
    "calm",
    "happy",
    "sad",
    "angry",
    "fear",
    "disgust",
    "surprise"
]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
# MODEL
# ============================================================

class VideoEmotionModel(nn.Module):

    def __init__(self, num_classes=8):
        super().__init__()

        # ResNet18 feature extractor
        self.cnn = models.resnet18(weights=None)

        # Remove final classification layer
        self.cnn.fc = nn.Identity()

        # ResNet18 output = 512 features
        self.lstm = nn.LSTM(
            input_size=512,
            hidden_size=256,
            num_layers=2,
            batch_first=True,
            dropout=0.3
        )

        self.dropout = nn.Dropout(0.4)

        self.classifier = nn.Linear(256, num_classes)

    def forward(self, x):

        # x shape:
        # [batch, frames, channels, height, width]

        batch_size, frames, channels, height, width = x.shape

        # Process every frame through ResNet
        x = x.view(
            batch_size * frames,
            channels,
            height,
            width
        )

        features = self.cnn(x)

        # Restore sequence
        features = features.view(
            batch_size,
            frames,
            512
        )

        # LSTM
        lstm_out, _ = self.lstm(features)

        # Last timestep
        x = lstm_out[:, -1, :]

        x = self.dropout(x)

        return self.classifier(x)


# ============================================================
# LOAD MODEL
# ============================================================

print("=" * 60)
print("MINDsense AI - VIDEO EMOTION PREDICTION")
print("=" * 60)

print(f"Device: {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")


model = VideoEmotionModel(num_classes=8)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE
)

# Handle different checkpoint formats
if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
    model.load_state_dict(checkpoint["model_state_dict"])
elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
    model.load_state_dict(checkpoint["state_dict"])
else:
    model.load_state_dict(checkpoint)

model.to(DEVICE)
model.eval()

print("Model loaded successfully.")


# ============================================================
# IMAGE TRANSFORMATION
# ============================================================

transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# READ VIDEO
# ============================================================

def load_video(video_path):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {video_path}"
        )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    if total_frames <= 0:
        cap.release()
        raise RuntimeError("Video contains no frames.")

    # Select 16 evenly spaced frames
    indices = np.linspace(
        0,
        total_frames - 1,
        FRAMES_PER_VIDEO
    ).astype(int)

    frames = []

    for index in indices:

        cap.set(
            cv2.CAP_PROP_POS_FRAMES,
            int(index)
        )

        ret, frame = cap.read()

        if not ret:
            continue

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        frame = transform(frame)

        frames.append(frame)

    cap.release()

    if len(frames) == 0:
        raise RuntimeError(
            "Could not read frames from video."
        )

    # If fewer than 16 frames were read,
    # duplicate the last frame.
    while len(frames) < FRAMES_PER_VIDEO:
        frames.append(frames[-1].clone())

    frames = frames[:FRAMES_PER_VIDEO]

    return torch.stack(frames)


# ============================================================
# PREDICT
# ============================================================

def predict(video_path):

    print("\n" + "=" * 60)
    print("INPUT VIDEO")
    print("=" * 60)

    print(video_path)

    frames = load_video(video_path)

    # Add batch dimension
    frames = frames.unsqueeze(0)

    frames = frames.to(DEVICE)

    with torch.no_grad():

        outputs = model(frames)

        probabilities = torch.softmax(
            outputs,
            dim=1
        )

        confidence, predicted = torch.max(
            probabilities,
            dim=1
        )

    emotion = EMOTIONS[predicted.item()]

    confidence = confidence.item() * 100

    print("\n" + "=" * 60)
    print("PREDICTION")
    print("=" * 60)

    print(f"Emotion    : {emotion.upper()}")
    print(f"Confidence : {confidence:.2f}%")

    print("\nAll probabilities:")

    for i, emotion_name in enumerate(EMOTIONS):

        probability = (
            probabilities[0][i].item() * 100
        )

        print(
            f"{emotion_name:10s}: "
            f"{probability:6.2f}%"
        )

    print("=" * 60)

    return emotion, confidence


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    video_path = input(
        "\nEnter path to MP4 video: "
    ).strip().strip('"')

    if not os.path.exists(video_path):

        print(
            f"\nERROR: Video not found:\n{video_path}"
        )

        raise SystemExit(1)

    predict(video_path)