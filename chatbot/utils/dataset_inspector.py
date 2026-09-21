from pathlib import Path
import pandas as pd


class DatasetInspector:

    @staticmethod
    def inspect(file_path):

        print("=" * 70)
        print(f"Dataset : {file_path.name}")
        print("=" * 70)

        df = pd.read_csv(file_path)

        print(f"Rows        : {len(df)}")
        print(f"Columns     : {len(df.columns)}")

        print("\nColumn Names")

        for column in df.columns:
            print(f"   • {column}")

        print("\nMissing Values")

        print(df.isnull().sum())

        print("\nDuplicate Rows :", df.duplicated().sum())

        print("\nFirst 3 Rows\n")

        print(df.head(3))

        print("\n")