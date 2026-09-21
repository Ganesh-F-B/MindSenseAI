import cv2
import json
import numpy as np
import torch
import torch.nn as nn
import onnxruntime as ort
import mediapipe as mp
from collections import deque

# ============================================================
# PATHS
# ============================================================

ONNX_MODEL_PATH = "sign_language/pretrained/mlp_asl.onnx"
ONNX_CLASSES_PATH = "sign_language/pretrained/mlp_classes.json"

PTH_MODEL_PATH = "sign_language/pretrained2/best_model.pth"
PTH_CLASSES_PATH = "sign_language/pretrained2/label_encoder_classes.npy"

HAND_MODEL_PATH = "sign_language/models/hand_landmarker.task"


# ============================================================
# SETTINGS
# ============================================================

SEQUENCE_LENGTH = 10

# Minimum confidence before accepting a prediction
SINGLE_HAND_THRESHOLD = 0.55
TWO_HAND_THRESHOLD = 0.60

# Require the same hand-count mode for a few frames before switching.
# This prevents a brief MediaPipe detection flicker from switching models.
MODE_STABILITY_FRAMES = 3

# Number of stable frames before changing displayed prediction
STABLE_FRAMES = 3


# ============================================================
# ATTENTION MODEL
# ============================================================


class Attention(nn.Module):

    def __init__(self, hidden_size):
        super().__init__()

        self.attention = nn.Sequential(
            nn.Linear(hidden_size, 128), nn.Tanh(), nn.Linear(128, 1)
        )

    def forward(self, x):

        scores = self.attention(x)

        weights = torch.softmax(scores, dim=1)

        context = torch.sum(weights * x, dim=1)

        return context


class ImprovedASLModel(nn.Module):

    def __init__(self, num_classes=77):

        super().__init__()

        # IMPORTANT:
        # These names MUST match best_model.pth

        self.conv_layers = nn.Sequential(
            # 126 = 2 hands × 21 landmarks × 3 coordinates
            nn.Conv1d(126, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Conv1d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
        )

        self.lstm = nn.LSTM(
            input_size=256,
            hidden_size=256,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.3,
        )

        # IMPORTANT:
        # Checkpoint contains:
        # attention.0
        # attention.2

        self.attention = nn.Sequential(
            nn.Linear(512, 128), nn.Tanh(), nn.Linear(128, 1)
        )

        # IMPORTANT:
        # Checkpoint contains:
        # classifier.0
        # classifier.1
        # classifier.4
        # classifier.5
        # classifier.8

        self.classifier = nn.Sequential(
            nn.Linear(512, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x, mask=None):

        # Expected:
        #
        # [batch, sequence, 2, 21, 3]

        batch_size, seq_len, hands, landmarks, coords = x.shape

        # ----------------------------------------------------
        # Flatten
        # ----------------------------------------------------

        x = x.reshape(batch_size, seq_len, 126)

        # Conv1D expects:
        #
        # [batch, channels, sequence]

        x = x.transpose(1, 2)

        # ----------------------------------------------------
        # CNN
        # ----------------------------------------------------

        x = self.conv_layers(x)

        # Back to:
        #
        # [batch, sequence, features]

        x = x.transpose(1, 2)

        # ----------------------------------------------------
        # LSTM
        # ----------------------------------------------------

        x, _ = self.lstm(x)

        # ----------------------------------------------------
        # Attention
        # ----------------------------------------------------

        scores = self.attention(x)

        weights = torch.softmax(scores, dim=1)

        x = torch.sum(weights * x, dim=1)

        # ----------------------------------------------------
        # Classifier
        # ----------------------------------------------------

        x = self.classifier(x)

        return x


# ============================================================
# LOAD SINGLE-HAND ONNX MODEL
# ============================================================

print("=" * 65)
print("MindSenseAI - HYBRID SIGN LANGUAGE SYSTEM")
print("=" * 65)

print("\nLoading single-hand model...")

onnx_session = ort.InferenceSession(ONNX_MODEL_PATH, providers=["CPUExecutionProvider"])

onnx_input_name = onnx_session.get_inputs()[0].name

with open(ONNX_CLASSES_PATH, "r") as f:
    onnx_classes = json.load(f)

print(f"Single-hand model loaded: " f"{len(onnx_classes)} classes")


# ============================================================
# LOAD 77 CLASS MODEL
# ============================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("\nLoading 77-class model...")
print("Device:", device)

# Load classes
two_hand_classes = np.load(PTH_CLASSES_PATH, allow_pickle=True)

two_hand_classes = list(two_hand_classes)

print(f"Two-hand model classes: " f"{len(two_hand_classes)}")

# Create model
two_hand_model = ImprovedASLModel(num_classes=len(two_hand_classes))

# Load checkpoint
checkpoint = torch.load(PTH_MODEL_PATH, map_location=device, weights_only=False)

if "model_state_dict" in checkpoint:

    state_dict = checkpoint["model_state_dict"]

else:

    state_dict = checkpoint

two_hand_model.load_state_dict(state_dict)

two_hand_model.to(device)

two_hand_model.eval()

print("Two-hand model loaded successfully!")


# ============================================================
# MEDIAPIPE
# ============================================================

print("\nLoading MediaPipe...")

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = mp.tasks.vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=HAND_MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)

landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

print("MediaPipe loaded successfully!")


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("ERROR: Could not open webcam.")

    raise SystemExit


# ============================================================
# VARIABLES
# ============================================================

sequence = deque(maxlen=SEQUENCE_LENGTH)

last_prediction = ""
stable_prediction = ""

prediction_counter = 0

last_hand_count = 0
mode_candidate = 0
mode_candidate_frames = 0
active_mode = 0


# ============================================================
# HELPER: LANDMARK EXTRACTION
# ============================================================


def get_landmark_array(hand):

    values = []

    for landmark in hand:

        values.extend([landmark.x, landmark.y, landmark.z])

    return np.array(values, dtype=np.float32)


# ============================================================
# HELPER: SINGLE HAND PREDICTION
# ============================================================


def normalize_single_hand(landmarks):
    """
    Preprocessing required by the pretrained ASL landmark model:

    1. Reshape 63 values -> 21 x 3 landmarks.
    2. Move the wrist (landmark 0) to the origin.
    3. Scale using the distance from wrist to middle-finger MCP (landmark 9).
    4. Flatten back to 63 values.

    Without this normalization the pretrained ONNX model can become
    extremely confident in the wrong class (for example, constantly 0).
    """
    pts = landmarks.reshape(21, 3).astype(np.float32)

    # Wrist-centered coordinates
    pts = pts - pts[0]

    # Scale using wrist -> middle-finger MCP
    scale = float(np.linalg.norm(pts[9]))

    if scale < 1e-6:
        return None

    pts = pts / scale

    return pts.reshape(63).astype(np.float32)


def predict_single_hand(hand):

    raw_landmarks = get_landmark_array(hand)

    landmarks = normalize_single_hand(raw_landmarks)

    if landmarks is None:
        return "Uncertain", 0.0

    input_data = np.expand_dims(landmarks, axis=0).astype(np.float32)

    output = onnx_session.run(None, {onnx_input_name: input_data})

    logits = np.asarray(output[0][0], dtype=np.float32)

    # Stable softmax
    logits = logits - np.max(logits)
    probabilities = np.exp(logits)
    probabilities = probabilities / np.sum(probabilities)

    # The pretrained model contains letters plus other classes.
    # For ONE-HAND mode we intentionally select only A-Z.
    letter_indices = [
        i
        for i, label in enumerate(onnx_classes)
        if isinstance(label, str)
        and len(label.strip()) == 1
        and label.strip().upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ]

    if not letter_indices:
        index = int(np.argmax(probabilities))
    else:
        index = max(letter_indices, key=lambda i: float(probabilities[i]))

    confidence = float(probabilities[index])
    label = str(onnx_classes[index]).strip().upper()

    if confidence < SINGLE_HAND_THRESHOLD:
        return "Uncertain", confidence

    return label, confidence


# ============================================================
# HELPER: ORDER TWO HANDS
# ============================================================


def order_hands(hands):

    if len(hands) == 1:

        return [get_landmark_array(hands[0]), np.zeros(63, dtype=np.float32)]

    hand_data = []

    for hand in hands:

        landmarks = get_landmark_array(hand)

        # Use average X position
        avg_x = np.mean(landmarks[0::3])

        hand_data.append((avg_x, landmarks))

    # Left-to-right ordering
    hand_data.sort(key=lambda x: x[0])

    return [hand_data[0][1], hand_data[1][1]]


# ============================================================
# HELPER: TWO-HAND PREDICTION
# ============================================================


def predict_two_hands():

    if len(sequence) < SEQUENCE_LENGTH:

        return None, 0.0

    input_sequence = np.array(sequence, dtype=np.float32)

    # Expected:
    # [sequence, 2, 21, 3]

    input_sequence = input_sequence.reshape(SEQUENCE_LENGTH, 2, 21, 3)

    input_tensor = torch.tensor(input_sequence, dtype=torch.float32).unsqueeze(0)

    input_tensor = input_tensor.to(device)

    with torch.no_grad():

        output = two_hand_model(input_tensor)

        probabilities = torch.softmax(output, dim=1)

        confidence, index = torch.max(probabilities, dim=1)

    confidence = float(confidence.item())

    index = int(index.item())

    if confidence < TWO_HAND_THRESHOLD:

        return "Uncertain", confidence

    return (two_hand_classes[index], confidence)


# ============================================================
# START
# ============================================================

print("\n" + "=" * 65)
print("HYBRID MODE READY")
print("=" * 65)

print("""
ONE HAND
  -> Single-hand ASL model
  -> A-Z letters

TWO HANDS
  -> 77-class temporal model
  -> words / signs
  -> hold/perform the complete sign sequence

NO HAND
  -> No prediction

Press Q to quit.
""")


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print("Could not read webcam frame.")

        break

    # Mirror camera
    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    result = landmarker.detect(mp_image)

    # ========================================================
    # HAND COUNT / MODE STABILITY
    # ========================================================

    hands = result.hand_landmarks
    raw_hand_count = len(hands)

    # Stabilize the mode so one missed/detected hand does not
    # immediately switch between the two models.
    if raw_hand_count != mode_candidate:
        mode_candidate = raw_hand_count
        mode_candidate_frames = 1
    else:
        mode_candidate_frames += 1

    if mode_candidate_frames >= MODE_STABILITY_FRAMES:
        active_mode = mode_candidate

    # ========================================================
    # NO HAND
    # ========================================================

    if active_mode == 0:

        sequence.clear()

        detected_text = "No hand detected"
        confidence_text = ""
        mode_text = "MODE: WAITING"

        last_hand_count = 0

    # ========================================================
    # ONE HAND -> PRETRAINED STATIC A-Z MODEL
    # ========================================================

    elif active_mode == 1 and raw_hand_count >= 1:

        # A one-hand mode must never feed stale two-hand frames.
        sequence.clear()

        last_hand_count = 1

        predicted_class, confidence = predict_single_hand(hands[0])

        mode_text = "MODE: SINGLE HAND (A-Z)"

        detected_text = f"Sign: {predicted_class}"
        confidence_text = f"Confidence: {confidence * 100:.1f}%"

    # ========================================================
    # TWO HANDS -> 77-CLASS TEMPORAL MODEL
    # ========================================================

    else:

        # Only use the two-hand model when two hands are actually
        # available. If MediaPipe briefly drops one hand, wait.
        if raw_hand_count < 2:

            detected_text = "Hold both hands..."
            confidence_text = ""
            mode_text = "MODE: TWO HANDS - WAITING"

        else:

            last_hand_count = 2
            mode_text = "MODE: TWO HANDS (77-CLASS)"

            ordered = order_hands(hands)

            frame_landmarks = np.array(ordered, dtype=np.float32).reshape(2, 21, 3)

            sequence.append(frame_landmarks)

            if len(sequence) < SEQUENCE_LENGTH:

                detected_text = "Collecting sign..."
                confidence_text = f"Frames: {len(sequence)}/{SEQUENCE_LENGTH}"

            else:

                predicted_class, confidence = predict_two_hands()

                if predicted_class is None:

                    detected_text = "Collecting sign..."
                    confidence_text = ""

                elif predicted_class == "Uncertain":

                    detected_text = "Hold / perform the sign..."
                    confidence_text = f"Confidence: {confidence * 100:.1f}%"

                else:

                    detected_text = f"Sign: {predicted_class}"
                    confidence_text = f"Confidence: {confidence * 100:.1f}%"

    # ========================================================
    # DRAW LANDMARKS
    # ========================================================

    for hand in hands:

        for landmark in hand:

            x = int(landmark.x * frame.shape[1])
            y = int(landmark.y * frame.shape[0])

            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.putText(
        frame, detected_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3
    )

    if confidence_text:

        cv2.putText(
            frame,
            confidence_text,
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
        )

    cv2.putText(
        frame, mode_text, (30, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2
    )

    cv2.putText(
        frame,
        f"Hands: {raw_hand_count}",
        (30, 155),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )

    cv2.imshow("MindSenseAI - Hybrid Sign Language", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()

landmarker.close()

print("\nHybrid sign language test finished.")
