import os
import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import models, transforms


# ============================================================
# CONFIGURATION
# ============================================================

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

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

MODEL_PATH = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "models",
    "video_emotion",
    "video_emotion_model_final.pth"
)


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

        # Temporal sequence model
        self.lstm = nn.LSTM(
            input_size=512,
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

        # x shape:
        # [batch, frames, channels, height, width]

        batch_size, frames, channels, height, width = x.shape

        # Process every frame through ResNet18
        x = x.view(
            batch_size * frames,
            channels,
            height,
            width
        )

        features = self.cnn(x)

        # Restore temporal sequence
        features = features.view(
            batch_size,
            frames,
            512
        )

        # Process frame sequence using LSTM
        lstm_out, _ = self.lstm(features)

        # Use final timestep
        x = lstm_out[:, -1, :]

        x = self.dropout(x)

        return self.classifier(x)


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not os.path.exists(MODEL_PATH):

        raise FileNotFoundError(
            f"Video emotion model not found:\n{MODEL_PATH}"
        )

    model = VideoEmotionModel(
        num_classes=len(EMOTIONS)
    )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    # Checkpoint format 1
    if (
        isinstance(checkpoint, dict)
        and "model_state_dict" in checkpoint
    ):

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

    # Checkpoint format 2
    elif (
        isinstance(checkpoint, dict)
        and "state_dict" in checkpoint
    ):

        model.load_state_dict(
            checkpoint["state_dict"]
        )

    # Direct state dictionary
    else:

        model.load_state_dict(
            checkpoint
        )

    model.to(DEVICE)

    model.eval()

    return model


model = load_model()


# ============================================================
# IMAGE TRANSFORMATION
# ============================================================

transform = transforms.Compose([

    transforms.ToPILImage(),

    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],
        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# ============================================================
# READ VIDEO
# ============================================================

def load_video(video_path):

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            f"Could not open video:\n{video_path}"
        )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    if total_frames <= 0:

        cap.release()

        raise RuntimeError(
            "Video contains no frames."
        )

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

        # OpenCV BGR -> RGB
        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        # Resize + normalize
        frame = transform(frame)

        frames.append(frame)

    cap.release()

    if len(frames) == 0:

        raise RuntimeError(
            "Could not read frames from video."
        )

    # If fewer than 16 frames were read,
    # duplicate the last valid frame.
    while len(frames) < FRAMES_PER_VIDEO:

        frames.append(
            frames[-1].clone()
        )

    frames = frames[:FRAMES_PER_VIDEO]

    return torch.stack(frames)


# ============================================================
# VIDEO PREDICTION
# ============================================================

def predict_video(video_path):

    if not os.path.exists(video_path):

        raise FileNotFoundError(
            f"Video not found:\n{video_path}"
        )

    # Load video frames
    frames = load_video(
        video_path
    )

    # Add batch dimension
    frames = frames.unsqueeze(0)

    # Move to GPU/CPU
    frames = frames.to(DEVICE)

    # Inference
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

    # Predicted emotion
    emotion = EMOTIONS[
        predicted.item()
    ]

    # Confidence percentage
    confidence = (
        confidence.item() * 100
    )

    # All emotion probabilities
    all_probabilities = {}

    for i, emotion_name in enumerate(EMOTIONS):

        all_probabilities[
            emotion_name
        ] = (
            probabilities[0][i].item()
            * 100
        )

    # ========================================================
    # STRUCTURED RESULT
    # ========================================================

    result = {

        "emotion": emotion,

        "confidence": confidence,

        "probabilities": all_probabilities
    }

    return result