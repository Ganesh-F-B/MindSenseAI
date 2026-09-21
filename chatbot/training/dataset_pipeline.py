from pathlib import Path

from chatbot.utils.dataset_inspector import DatasetInspector

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FOLDER = BASE_DIR / "datasets" / "raw"

def main():

    csv_files = RAW_FOLDER.glob("*.csv")

    for file in csv_files:

        DatasetInspector.inspect(file)


if __name__ == "__main__":
    main()