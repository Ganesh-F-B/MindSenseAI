import csv
import os
import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "sign_language/models/hand_landmarker.task"
DATA_FILE = "sign_language/data/landmarks.csv"

# Collect 100 samples for each sign.
SAMPLES_PER_SIGN = 100

# Change this to the sign you are currently collecting.
SIGN_NAME = "hello"


def create_detector():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    return vision.HandLandmarker.create_from_options(options)


def extract_landmarks(hand_landmarks):
    """
    Convert 21 hand landmarks into 63 values:
    x1,y1,z1,...,x21,y21,z21
    """

    values = []

    for landmark in hand_landmarks:
        values.extend(
            [
                landmark.x,
                landmark.y,
                landmark.z,
            ]
        )

    return values


def main():

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    detector = create_detector()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        detector.close()
        return

    # Create CSV header if the file doesn't exist.
    file_exists = os.path.exists(DATA_FILE)

    header = ["label"]

    for i in range(1, 22):
        header.extend(
            [
                f"x{i}",
                f"y{i}",
                f"z{i}",
            ]
        )

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as csv_file:

        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(header)

        print("=" * 60)
        print("MindSenseAI - Sign Language Data Collector")
        print("=" * 60)
        print(f"Sign: {SIGN_NAME}")
        print(f"Target samples: {SAMPLES_PER_SIGN}")
        print()
        print("Show the sign clearly to the camera.")
        print("Press SPACE to capture a sample.")
        print("Press Q to quit.")
        print("=" * 60)

        collected = 0

        while collected < SAMPLES_PER_SIGN:

            success, frame = camera.read()

            if not success:
                print("ERROR: Could not read webcam frame.")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            result = detector.detect(mp_image)

            # Draw detected landmarks.
            if result.hand_landmarks:

                hand = result.hand_landmarks[0]

                for landmark in hand:

                    x = int(landmark.x * frame.shape[1])

                    y = int(landmark.y * frame.shape[0])

                    cv2.circle(
                        frame,
                        (x, y),
                        5,
                        (0, 255, 0),
                        -1,
                    )

            # Display progress.
            cv2.putText(
                frame,
                f"Sign: {SIGN_NAME}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                f"Samples: {collected}/{SAMPLES_PER_SIGN}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            cv2.imshow("MindSenseAI - Sign Data Collector", frame)

            key = cv2.waitKey(1) & 0xFF

            # SPACE = capture
            if key == 32:

                if not result.hand_landmarks:

                    print("No hand detected. " "Show your hand first.")

                    continue

                landmarks = extract_landmarks(result.hand_landmarks[0])

                writer.writerow([SIGN_NAME, *landmarks])

                csv_file.flush()

                collected += 1

                print(f"Captured {collected}/{SAMPLES_PER_SIGN}")

            # Q = quit
            elif key == ord("q"):

                print("Collection stopped.")

                break

    camera.release()
    cv2.destroyAllWindows()
    detector.close()

    print()
    print("=" * 60)
    print("Data collection finished.")
    print(f"Saved to: {DATA_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
