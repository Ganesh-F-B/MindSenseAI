import cv2
import json
import numpy as np
import onnxruntime as ort
import mediapipe as mp

# ============================================================
# Paths
# ============================================================

MODEL_PATH = "sign_language/pretrained/mlp_asl.onnx"
CLASSES_PATH = "sign_language/pretrained/mlp_classes.json"
HAND_MODEL_PATH = "sign_language/models/hand_landmarker.task"


# ============================================================
# Load pretrained ASL model
# ============================================================

print("Loading pretrained ASL model...")

session = ort.InferenceSession(MODEL_PATH)

input_name = session.get_inputs()[0].name

with open(CLASSES_PATH, "r") as f:
    classes = json.load(f)

print("Model loaded successfully.")
print(f"Classes: {len(classes)}")
print(f"Input: {session.get_inputs()[0].shape}")


# ============================================================
# MediaPipe Hand Landmarker
# ============================================================

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = mp.tasks.vision.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=HAND_MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=1,
)

landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)


# ============================================================
# Normalize landmarks
# ============================================================


def normalize_landmarks(hand):
    """
    Convert MediaPipe hand landmarks into the normalized
    63-feature representation expected by the pretrained
    ASL landmark MLP.

    21 landmarks × (x, y, z) = 63 values.
    """

    # --------------------------------------------------------
    # Convert MediaPipe landmarks to NumPy
    # --------------------------------------------------------

    points = np.array(
        [[landmark.x, landmark.y, landmark.z] for landmark in hand], dtype=np.float32
    )

    # Safety check
    if points.shape != (21, 3):
        return None

    # --------------------------------------------------------
    # 1. Move wrist to origin
    #
    # Landmark 0 = wrist
    # --------------------------------------------------------

    wrist = points[0].copy()

    points = points - wrist

    # --------------------------------------------------------
    # 2. Scale normalization
    #
    # Landmark 9 = middle finger MCP
    #
    # Distance from wrist to landmark 9 is used as
    # the normalization scale.
    # --------------------------------------------------------

    scale = np.linalg.norm(points[9])

    if scale < 1e-6:
        return None

    points = points / scale

    # --------------------------------------------------------
    # 3. Flatten 21 × 3 → 63
    # --------------------------------------------------------

    features = points.reshape(1, 63)

    return features.astype(np.float32)


# ============================================================
# Prediction
# ============================================================


def predict_landmarks(hand):
    """
    Predict ASL alphabet/digit from normalized hand landmarks.
    """

    # Normalize landmarks
    input_data = normalize_landmarks(hand)

    if input_data is None:
        return "Unknown", 0.0

    # --------------------------------------------------------
    # ONNX inference
    # --------------------------------------------------------

    output = session.run(None, {input_name: input_data})

    logits = output[0][0]

    # --------------------------------------------------------
    # Softmax
    # --------------------------------------------------------

    exp_logits = np.exp(logits - np.max(logits))

    probabilities = exp_logits / np.sum(exp_logits)

    # --------------------------------------------------------
    # Best prediction
    # --------------------------------------------------------

    predicted_index = int(np.argmax(probabilities))

    confidence = float(probabilities[predicted_index])

    # Safety check
    if predicted_index >= len(classes):
        return "Unknown", confidence

    predicted_class = classes[predicted_index]

    return predicted_class, confidence


# ============================================================
# Webcam
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("ERROR: Could not open webcam.")

    landmarker.close()

    raise SystemExit


print()
print("=" * 60)
print("MindSenseAI - Pretrained ASL Test")
print("=" * 60)
print()
print("Show one hand to the camera.")
print()
print("Try these static ASL signs:")
print("A")
print("B")
print("C")
print("F")
print("I")
print("Y")
print()
print("Press Q to quit.")
print("=" * 60)


# ============================================================
# Main webcam loop
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print("Could not read webcam frame.")

        break

    # --------------------------------------------------------
    # Mirror webcam
    # --------------------------------------------------------

    frame = cv2.flip(frame, 1)

    # --------------------------------------------------------
    # Convert BGR → RGB
    # --------------------------------------------------------

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # --------------------------------------------------------
    # Create MediaPipe image
    # --------------------------------------------------------

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    # --------------------------------------------------------
    # Detect hand
    # --------------------------------------------------------

    result = landmarker.detect(mp_image)

    detected_text = "No hand detected"
    confidence_text = ""

    # --------------------------------------------------------
    # If hand detected
    # --------------------------------------------------------

    if result.hand_landmarks:

        hand = result.hand_landmarks[0]

        # ----------------------------------------------------
        # Predict
        # ----------------------------------------------------

        predicted_class, confidence = predict_landmarks(hand)

        detected_text = f"Sign: {predicted_class}"

        confidence_text = f"Confidence: {confidence * 100:.1f}%"

        # ----------------------------------------------------
        # Draw hand landmarks
        # ----------------------------------------------------

        for landmark in hand:

            x = int(landmark.x * frame.shape[1])

            y = int(landmark.y * frame.shape[0])

            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    # ========================================================
    # Display prediction
    # ========================================================

    cv2.putText(
        frame, detected_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3
    )

    # --------------------------------------------------------
    # Display confidence
    # --------------------------------------------------------

    if confidence_text:

        cv2.putText(
            frame,
            confidence_text,
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

    # ========================================================
    # Show webcam
    # ========================================================

    cv2.imshow("MindSenseAI - Pretrained ASL Test", frame)

    # --------------------------------------------------------
    # Keyboard
    # --------------------------------------------------------

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# Cleanup
# ============================================================

cap.release()

cv2.destroyAllWindows()

landmarker.close()

print()
print("Test finished.")
