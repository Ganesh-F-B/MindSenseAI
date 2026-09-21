import cv2
import torch
import numpy as np
from collections import deque
import mediapipe as mp

from sign_language.pretrained2.asl_model import ImprovedASLModel


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = "sign_language/pretrained2/best_model.pth"
CLASSES_PATH = "sign_language/pretrained2/label_encoder_classes.npy"
HAND_MODEL_PATH = "sign_language/models/hand_landmarker.task"


# ============================================================
# SETTINGS
# ============================================================

SEQUENCE_LENGTH = 10
NUM_HANDS = 2
NUM_LANDMARKS = 21
NUM_COORDINATES = 3

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
# LOAD CLASSES
# ============================================================

classes = np.load(
    CLASSES_PATH,
    allow_pickle=True
)

classes = classes.tolist()

print("=" * 65)
print("MindSenseAI - 77 CLASS TWO-HAND WEBCAM TEST")
print("=" * 65)

print(f"Device: {DEVICE}")
print(f"Number of classes: {len(classes)}")


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading model...")

model = ImprovedASLModel(
    num_classes=len(classes)
)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False
)


# Handle checkpoint format
if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
    state_dict = checkpoint["model_state_dict"]
elif isinstance(checkpoint, dict) and "model_state" in checkpoint:
    state_dict = checkpoint["model_state"]
else:
    state_dict = checkpoint


model.load_state_dict(state_dict)

model.to(DEVICE)
model.eval()

print("Model loaded successfully!")
print()


# ============================================================
# MEDIAPIPE
# ============================================================

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = mp.tasks.vision.HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=HAND_MODEL_PATH
    ),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=2
)

landmarker = mp.tasks.vision.HandLandmarker.create_from_options(
    options
)


# ============================================================
# WEBCAM
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam.")
    raise SystemExit


# ============================================================
# SEQUENCE BUFFER
# ============================================================

sequence = deque(
    maxlen=SEQUENCE_LENGTH
)


# ============================================================
# PREDICTION VARIABLES
# ============================================================

predicted_class = "Waiting..."
confidence = 0.0

left_detected = False
right_detected = False


# ============================================================
# HELPER FUNCTION
# ============================================================

def extract_hand_landmarks(hand):
    """
    Convert MediaPipe 21 landmarks into:
    [21, 3]
    """

    data = []

    for landmark in hand:
        data.append([
            landmark.x,
            landmark.y,
            landmark.z
        ])

    return np.array(
        data,
        dtype=np.float32
    )


# ============================================================
# START
# ============================================================

print("=" * 65)
print("WEBCAM TEST STARTED")
print("=" * 65)
print()
print("Show one or two hands.")
print("Keep the hand visible for a moment.")
print()
print("LEFT  = Left hand detected")
print("RIGHT = Right hand detected")
print("BOTH  = Both hands detected")
print()
print("Press Q to quit.")
print("=" * 65)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Could not read webcam frame.")
        break


    # --------------------------------------------------------
    # Mirror camera
    # --------------------------------------------------------

    frame = cv2.flip(frame, 1)


    # --------------------------------------------------------
    # BGR -> RGB
    # --------------------------------------------------------

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # --------------------------------------------------------
    # MediaPipe image
    # --------------------------------------------------------

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )


    # --------------------------------------------------------
    # Detect hands
    # --------------------------------------------------------

    result = landmarker.detect(mp_image)


    # Reset
    left_hand = np.zeros(
        (21, 3),
        dtype=np.float32
    )

    right_hand = np.zeros(
        (21, 3),
        dtype=np.float32
    )

    left_detected = False
    right_detected = False


    # --------------------------------------------------------
    # Process detected hands
    # --------------------------------------------------------

    if result.hand_landmarks:

        for i, hand in enumerate(result.hand_landmarks):

            landmarks = extract_hand_landmarks(hand)


            # ------------------------------------------------
            # Get handedness
            # ------------------------------------------------

            if (
                result.handedness
                and i < len(result.handedness)
                and len(result.handedness[i]) > 0
            ):

                handedness = (
                    result.handedness[i][0].category_name
                )


                # ------------------------------------------------
                # MediaPipe handedness
                # ------------------------------------------------

                if handedness == "Left":

                    left_hand = landmarks
                    left_detected = True

                elif handedness == "Right":

                    right_hand = landmarks
                    right_detected = True


            # ------------------------------------------------
            # Draw landmarks
            # ------------------------------------------------

            for landmark in hand:

                x = int(
                    landmark.x * frame.shape[1]
                )

                y = int(
                    landmark.y * frame.shape[0]
                )

                cv2.circle(
                    frame,
                    (x, y),
                    5,
                    (0, 255, 0),
                    -1
                )


    # ========================================================
    # HAND STATUS
    # ========================================================

    if left_detected and right_detected:

        hand_status = "BOTH HANDS"

    elif left_detected:

        hand_status = "LEFT HAND"

    elif right_detected:

        hand_status = "RIGHT HAND"

    else:

        hand_status = "NO HAND"


    # ========================================================
    # CREATE CURRENT FRAME
    # ========================================================

    current_frame = np.stack(
        [
            left_hand,
            right_hand
        ],
        axis=0
    )


    # Shape:

    # [2, 21, 3]


    # ========================================================
    # ADD TO SEQUENCE
    # ========================================================

    sequence.append(
        current_frame
    )


    # ========================================================
    # MODEL PREDICTION
    # ========================================================

    if len(sequence) == SEQUENCE_LENGTH:

        input_sequence = np.array(
            sequence,
            dtype=np.float32
        )


        # Shape:
        #
        # [10, 2, 21, 3]


        input_tensor = torch.tensor(
            input_sequence,
            dtype=torch.float32
        )


        # Add batch dimension
        #
        # [1, 10, 2, 21, 3]

        input_tensor = input_tensor.unsqueeze(0)


        input_tensor = input_tensor.to(
            DEVICE
        )


        # ----------------------------------------------------
        # Inference
        # ----------------------------------------------------

        with torch.no_grad():

            output = model(
                input_tensor
            )


        # ----------------------------------------------------
        # Softmax
        # ----------------------------------------------------

        probabilities = torch.softmax(
            output,
            dim=1
        )


        # ----------------------------------------------------
        # Best class
        # ----------------------------------------------------

        confidence_tensor, index_tensor = torch.max(
            probabilities,
            dim=1
        )


        predicted_index = int(
            index_tensor.item()
        )

        confidence = float(
            confidence_tensor.item()
        )


        if (
            predicted_index >= 0
            and predicted_index < len(classes)
        ):

            predicted_class = str(
                classes[predicted_index]
            )


    # ========================================================
    # DISPLAY
    # ========================================================

    # Model prediction

    cv2.putText(
        frame,
        f"Sign: {predicted_class}",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 255, 0),
        3
    )


    # Confidence

    cv2.putText(
        frame,
        f"Confidence: {confidence * 100:.1f}%",
        (30, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )


    # Hand status

    cv2.putText(
        frame,
        f"Hands: {hand_status}",
        (30, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )


    # Sequence progress

    cv2.putText(
        frame,
        f"Frames: {len(sequence)}/{SEQUENCE_LENGTH}",
        (30, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SHOW
    # ========================================================

    cv2.imshow(
        "MindSenseAI - 77 Class ASL",
        frame
    )


    # ========================================================
    # QUIT
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# ============================================================
# CLEANUP
# ============================================================

cap.release()

cv2.destroyAllWindows()

landmarker.close()

print()
print("=" * 65)
print("ASL TEST FINISHED")
print("=" * 65)