from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FINAL_DIR = BASE_DIR / "datasets" / "final"


def validate_conversation():

    print("=" * 70)
    print("Conversation Dataset")
    print("=" * 70)

    df = pd.read_csv(FINAL_DIR / "conversation.csv")

    print("Total Conversations :", len(df))
    print("Duplicate Rows      :", df.duplicated().sum())

    print("Missing Input       :", df["input"].isna().sum())
    print("Missing Response    :", df["response"].isna().sum())

    print()

    print("Average Input Length")

    print(df["input"].astype(str).str.split().str.len().mean())

    print()

    print("Average Response Length")

    print(df["response"].astype(str).str.split().str.len().mean())

    print()

    print("Sources")

    print(df["source"].value_counts())


def validate_emotion():

    print("\n")
    print("=" * 70)
    print("Emotion Dataset")
    print("=" * 70)

    df = pd.read_csv(FINAL_DIR / "emotion.csv")

    print("Total Samples :", len(df))

    print("Duplicate Rows :", df.duplicated().sum())

    print("Missing Text :", df["text"].isna().sum())

    print("Missing Emotion :", df["emotion"].isna().sum())

    print()

    print("Average Text Length")

    print(df["text"].astype(str).str.split().str.len().mean())

    print()

    print("Top 20 Labels")

    print(df["emotion"].value_counts().head(20))


def main():

    validate_conversation()

    validate_emotion()


if __name__ == "__main__":
    main()