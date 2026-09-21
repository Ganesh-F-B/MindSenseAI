import json
from pathlib import Path

CLINC_PATH = Path("chatbot/datasets/raw/clinc150/data_full.json")

with open(CLINC_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("CLINC150 Dataset Analysis")
print("=" * 80)

print("\nKeys:")
print(data.keys())

print("\nFirst Training Sample:")
print(data["train"][0])

print("\nTotal Training Samples:")
print(len(data["train"]))