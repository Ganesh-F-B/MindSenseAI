import pandas as pd
from pathlib import Path

DATASET_DIR = Path("chatbot/datasets")

folders = [
    "emotion",
    "counseling",
    "conversation",
    "processed",
    "final"
]

print("=" * 80)
print("MindSenseAI Dataset Analysis")
print("=" * 80)

for folder in folders:

    folder_path = DATASET_DIR / folder

    if not folder_path.exists():
        continue

    print(f"\nFolder : {folder}")
    print("-" * 80)

    for file in folder_path.glob("*.csv"):

        try:
            df = pd.read_csv(file)

            print(f"\nFile : {file.name}")
            print(f"Rows    : {len(df)}")
            print(f"Columns : {len(df.columns)}")
            print("Column Names:")
            print(list(df.columns))

            print("\nFirst 3 Rows:")
            print(df.head(3))

            print("\nMissing Values:")
            print(df.isnull().sum())

            print("=" * 80)

        except Exception as e:
            print(f"Could not read {file.name}")
            print(e)