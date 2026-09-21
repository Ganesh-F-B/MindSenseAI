import cv2
import csv
import re
from pathlib import Path
from collections import Counter

# ============================================================
# CONFIGURATION
# ============================================================

DATASET_DIR = Path("datasets/video_emotion/RAVDESS")
OUTPUT_DIR = Path("datasets/video_emotion/processed")

FRAMES_PER_VIDEO = 16
IMAGE_SIZE = 224

# RAVDESS emotion IDs
EMOTIONS = {
    "01": "neutral",
    "02": "calm",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fear",
    "07": "disgust",
    "08": "surprise",
}

# ============================================================
# DIRECTORIES
# ============================================================

FRAMES_DIR = OUTPUT_DIR / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

METADATA_FILE = OUTPUT_DIR / "metadata.csv"

# ============================================================
# FACE DETECTOR
# ============================================================

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

face_detector = cv2.CascadeClassifier(CASCADE_PATH)

if face_detector.empty():
    raise RuntimeError("Could not load OpenCV Haar face detector.")

# ============================================================
# FIND VIDEOS
# ============================================================

videos = sorted(DATASET_DIR.rglob("*.mp4"))

print("=" * 70)
print("MindSense AI - RAVDESS Video Preprocessing")
print("=" * 70)
print(f"Dataset: {DATASET_DIR}")
print(f"Videos found: {len(videos)}")
print(f"Frames per video: {FRAMES_PER_VIDEO}")
print(f"Image size: {IMAGE_SIZE}x{IMAGE_SIZE}")
print("=" * 70)

if len(videos) == 0:
    raise RuntimeError("No .mp4 files found.")

# ============================================================
# METADATA
# ============================================================

rows = []

processed = 0
failed = 0
total_frames = 0
face_found = 0

emotion_counter = Counter()
actor_counter = Counter()

# ============================================================
# PROCESS EACH VIDEO
# ============================================================

for video_index, video_path in enumerate(videos, start=1):

    filename = video_path.stem

    # Example:
    # 01-01-06-01-02-01-12
    parts = filename.split("-")

    if len(parts) != 7:
        print(f"[SKIP] Invalid filename: {video_path.name}")
        failed += 1
        continue

    modality = parts[0]
    vocal_channel = parts[1]
    emotion_id = parts[2]
    intensity = parts[3]
    statement = parts[4]
    repetition = parts[5]
    actor_id = parts[6]

    if emotion_id not in EMOTIONS:
        print(f"[SKIP] Unknown emotion: {video_path.name}")
        failed += 1
        continue

    emotion = EMOTIONS[emotion_id]

    # --------------------------------------------------------
    # Open video
    # --------------------------------------------------------

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"[FAILED] Cannot open: {video_path.name}")
        failed += 1
        continue

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if frame_count <= 0:
        print(f"[FAILED] No frames: {video_path.name}")
        cap.release()
        failed += 1
        continue

    # --------------------------------------------------------
    # Select evenly spaced frames
    # --------------------------------------------------------

    frame_indices = [
        int(i * (frame_count - 1) / (FRAMES_PER_VIDEO - 1))
        for i in range(FRAMES_PER_VIDEO)
    ]

    video_output_dir = FRAMES_DIR / f"actor_{actor_id}" / emotion / filename
    video_output_dir.mkdir(parents=True, exist_ok=True)

    video_faces = 0

    for frame_number, frame_index in enumerate(frame_indices):

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        success, frame = cap.read()

        if not success:
            continue

        total_frames += 1

        # ----------------------------------------------------
        # Convert to grayscale for face detection
        # ----------------------------------------------------

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) == 0:
            continue

        # ----------------------------------------------------
        # Select largest detected face
        # ----------------------------------------------------

        x, y, w, h = max(
            faces,
            key=lambda box: box[2] * box[3]
        )

        # Add a small margin around face
        margin = int(0.20 * max(w, h))

        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(frame.shape[1], x + w + margin)
        y2 = min(frame.shape[0], y + h + margin)

        face = frame[y1:y2, x1:x2]

        if face.size == 0:
            continue

        # ----------------------------------------------------
        # Resize
        # ----------------------------------------------------

        face = cv2.resize(
            face,
            (IMAGE_SIZE, IMAGE_SIZE),
            interpolation=cv2.INTER_AREA
        )

        # ----------------------------------------------------
        # Save JPEG
        # ----------------------------------------------------

        output_file = video_output_dir / f"frame_{frame_number:02d}.jpg"

        cv2.imwrite(
            str(output_file),
            face,
            [cv2.IMWRITE_JPEG_QUALITY, 95]
        )

        video_faces += 1
        face_found += 1

        rows.append({
            "frame_path": str(output_file).replace("\\", "/"),
            "emotion": emotion,
            "emotion_id": emotion_id,
            "actor": actor_id,
            "video": filename,
            "frame": frame_number,
        })

    cap.release()

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    if video_faces > 0:

        processed += 1
        emotion_counter[emotion] += 1
        actor_counter[actor_id] += 1

    else:
        failed += 1

    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    if video_index % 25 == 0 or video_index == len(videos):

        print(
            f"[{video_index}/{len(videos)}] "
            f"Processed: {processed} | "
            f"Failed: {failed} | "
            f"Faces saved: {face_found}"
        )

# ============================================================
# SAVE METADATA
# ============================================================

with open(
    METADATA_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "frame_path",
            "emotion",
            "emotion_id",
            "actor",
            "video",
            "frame",
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("PREPROCESSING COMPLETE")
print("=" * 70)

print(f"Videos found       : {len(videos)}")
print(f"Videos processed   : {processed}")
print(f"Videos failed      : {failed}")
print(f"Frames examined    : {total_frames}")
print(f"Face frames saved  : {face_found}")
print(f"Metadata           : {METADATA_FILE}")

print()
print("Emotion distribution:")

for emotion in EMOTIONS.values():
    print(
        f"  {emotion:<10} : "
        f"{emotion_counter.get(emotion, 0)} videos"
    )

print()
print("Actor distribution:")

for actor in sorted(actor_counter):
    print(
        f"  Actor {actor:<3} : "
        f"{actor_counter[actor]} videos"
    )

print()
print("=" * 70)