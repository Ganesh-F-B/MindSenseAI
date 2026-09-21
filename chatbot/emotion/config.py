from pathlib import Path
import torch

# ==========================================================
# Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "datasets" / "emotion"

MODEL_DIR = BASE_DIR / "models" / "emotion"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Model
# ==========================================================

MODEL_NAME = "microsoft/deberta-v3-base"

TOKENIZER_NAME = MODEL_NAME

# Basic emotion classes
LABELS = [
    "sadness",
    "joy",
    "love",
    "anger",
    "fear",
    "surprise"
]

NUM_LABELS = len(LABELS)

LABEL2ID = {
    label: idx
    for idx, label in enumerate(LABELS)
}

ID2LABEL = {
    idx: label
    for idx, label in enumerate(LABELS)
}

MAX_LENGTH = 128

DROPOUT = 0.3

# ==========================================================
# Training
# ==========================================================

TRAIN_BATCH_SIZE = 16

VALID_BATCH_SIZE = 16

LEARNING_RATE = 2e-5

WEIGHT_DECAY = 0.01

EPOCHS = 10

RANDOM_SEED = 42

# ==========================================================
# Device
# ==========================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# ==========================================================
# Saving
# ==========================================================

BEST_MODEL_PATH = MODEL_DIR / "emotion_best.pt"

LAST_MODEL_PATH = MODEL_DIR / "emotion_last.pt"