import os
import glob
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CURATED_DIR = os.path.join(BASE_DIR, "curated_data")

ORIGINAL_DATASET = os.path.join(
    BASE_DIR,
    "..",
    "datasets",
    "raw",
    "intent_dataset.csv"
)

OUTPUT_DATASET = os.path.join(
    BASE_DIR,
    "..",
    "datasets",
    "raw",
    "intent_dataset_v2.csv"
)


def load_curated_data():
    csv_files = glob.glob(os.path.join(CURATED_DIR, "*.csv"))

    dataframes = []

    for file in csv_files:
        print(f"Loading {os.path.basename(file)}")
        df = pd.read_csv(file)
        dataframes.append(df)

    if not dataframes:
        return pd.DataFrame(columns=["text", "intent", "source", "domain"])

    return pd.concat(dataframes, ignore_index=True)


def main():

    print("=" * 60)
    print("Loading Original Dataset...")
    print("=" * 60)

    original = pd.read_csv(ORIGINAL_DATASET)

    if "source" not in original.columns:
        original["source"] = "original"

    if "domain" not in original.columns:
        original["domain"] = "general"

    print(f"Original Samples : {len(original)}")

    print()

    print("=" * 60)
    print("Loading Curated Dataset...")
    print("=" * 60)

    curated = load_curated_data()

    print(f"Curated Samples : {len(curated)}")

    print()

    print("=" * 60)
    print("Merging...")
    print("=" * 60)

    merged = pd.concat(
        [original, curated],
        ignore_index=True
    )

    before = len(merged)

    merged.drop_duplicates(
        subset=["text", "intent"],
        inplace=True
    )

    after = len(merged)

    print(f"Removed {before-after} duplicate rows")

    merged = merged.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_DATASET), exist_ok=True)

    merged.to_csv(
        OUTPUT_DATASET,
        index=False
    )

    print()
    print("=" * 60)
    print("Dataset Saved")
    print("=" * 60)

    print(OUTPUT_DATASET)

    print()

    print("=" * 60)
    print("Class Distribution")
    print("=" * 60)

    print(
        merged["intent"]
        .value_counts()
        .sort_index()
    )

    print()

    print(f"Total Samples : {len(merged)}")


if __name__ == "__main__":
    main()