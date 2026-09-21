import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "sign_language/models/hand_landmarker.task"


def main():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    detector = vision.HandLandmarker.create_from_options(options)

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        detector.close()
        return

    print("=" * 50)
    print("MindSenseAI - Hand Detection Test")
    print("=" * 50)
    print("Show your hand to the camera.")
    print("Press Q to quit.")
    print("=" * 50)

    while True:
        success, frame = camera.read()

        if not success:
            print("ERROR: Could not read frame.")
            break

        # OpenCV uses BGR; MediaPipe expects RGB.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        result = detector.detect(mp_image)

        hand_count = len(result.hand_landmarks)

        # Draw a simple status on the screen.
        if hand_count > 0:
            text = f"Hand detected: YES | Hands: {hand_count}"
        else:
            text = "Hand detected: NO | Hands: 0"

        cv2.putText(
            frame,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        # Draw the 21 landmarks for each detected hand.
        for hand_landmarks in result.hand_landmarks:
            for landmark in hand_landmarks:
                x = int(landmark.x * frame.shape[1])
                y = int(landmark.y * frame.shape[0])

                cv2.circle(
                    frame,
                    (x, y),
                    5,
                    (0, 255, 0),
                    -1,
                )

        cv2.imshow("MindSenseAI - Hand Detection Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
    detector.close()

    print("Hand detection test stopped.")


if __name__ == "__main__":
    main()
