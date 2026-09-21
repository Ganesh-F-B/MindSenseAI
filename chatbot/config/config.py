from pathlib import Path
import torch

# ==========================================================
# Project Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "datasets" / "processed"
FINAL_DATA_DIR = BASE_DIR / "datasets" / "final"

MODEL_DIR = BASE_DIR / "models"
CHECKPOINT_DIR = MODEL_DIR / "checkpoints"

CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Model Configuration
# ==========================================================

MODEL_NAME = "microsoft/deberta-v3-base"

TOKENIZER_NAME = MODEL_NAME

NUM_LABELS = 6

MAX_LENGTH = 128

DROPOUT = 0.3

# ==========================================================
# Training Configuration
# ==========================================================

TRAIN_BATCH_SIZE = 8
VALID_BATCH_SIZE = 8

LEARNING_RATE = 2e-5

WEIGHT_DECAY = 0.01

EPOCHS = 5

GRADIENT_CLIP = 1.0

RANDOM_SEED = 42

# ==========================================================
# Device
# ==========================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==========================================================
# Saving
# ==========================================================

BEST_MODEL_NAME = "emotion_deberta_v3_best.pt"
LAST_MODEL_NAME = "emotion_deberta_v3_last.pt"

BEST_MODEL_PATH = CHECKPOINT_DIR / BEST_MODEL_NAME
LAST_MODEL_PATH = CHECKPOINT_DIR / LAST_MODEL_NAME