from datasets import load_dataset
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path("../datasets/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_dataset(dataset_name, split, filename):
    print(f"\nDownloading {dataset_name} ({split})...")

    ds = load_dataset(dataset_name, split=split)

    df = pd.DataFrame(ds)

    path = OUTPUT_DIR / filename

    df.to_csv(path, index=False)

    print(f"Saved -> {path}")


def main():

    datasets = [

        ("facebook/empathetic_dialogues", "train", "empathetic_dialogues.csv"),

        ("google-research-datasets/go_emotions", "train", "go_emotions.csv"),

        ("daily_dialog", "train", "daily_dialog.csv"),

        ("dair-ai/emotion", "train", "emotion.csv"),

        ("OpenAssistant/oasst1", "train", "oasst1.csv")

    ]

    for dataset in datasets:

        try:
            save_dataset(*dataset)

        except Exception as e:

            print(f"Failed: {dataset[0]}")
            print(e)


if __name__ == "__main__":
    main()