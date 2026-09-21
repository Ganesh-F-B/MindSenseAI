from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(exist_ok=True)

report = []


def clean_train(df):
    df = df.drop_duplicates()
    df = df.dropna(subset=["Context", "Response"])
    return df


def clean_emotion(df):
    text_col = "text"

    label_col = "label" if "label" in df.columns else "labels"

    df = df.drop_duplicates()
    df = df.dropna(subset=[text_col, label_col])

    return df


def clean_counselchat(df):

    df = df.drop_duplicates()

    if "questionText" in df.columns and "questionTitle" in df.columns:

        df["questionText"] = df["questionText"].fillna(df["questionTitle"])

    if "answerText" in df.columns:

        df = df.dropna(subset=["answerText"])

    return df


def clean_oasst(df):

    df = df.drop_duplicates()

    if "lang" in df.columns:

        df = df[df["lang"] == "en"]

    df = df.dropna(subset=["text"])

    return df


def process_dataset(file_path):

    print("=" * 70)
    print(f"Processing: {file_path.name}")

    df = pd.read_csv(file_path)

    before = len(df)

    name = file_path.name.lower()

    if name == "train.csv":

        df = clean_train(df)

    elif "emotion" in name:

        df = clean_emotion(df)

    elif "counsel" in name:

        df = clean_counselchat(df)

    elif "oasst" in name:

        df = clean_oasst(df)

    else:

        df = df.drop_duplicates()

    after = len(df)

    output = PROCESSED_DIR / file_path.name

    df.to_csv(output, index=False)

    removed = before - after

    report.append({
        "Dataset": file_path.name,
        "Before": before,
        "After": after,
        "Removed": removed
    })

    print(f"Rows Before : {before}")
    print(f"Rows After  : {after}")
    print(f"Removed     : {removed}")


def main():

    for file in sorted(RAW_DIR.glob("*.csv")):

        if "backup" in file.name.lower():

            print(f"Skipping backup: {file.name}")
            continue

        process_dataset(file)

    report_df = pd.DataFrame(report)

    report_path = PROCESSED_DIR / "cleaning_report.csv"

    report_df.to_csv(report_path, index=False)

    print("\nCleaning Report")
    print(report_df)

    print(f"\nSaved report -> {report_path}")


if __name__ == "__main__":
    main()