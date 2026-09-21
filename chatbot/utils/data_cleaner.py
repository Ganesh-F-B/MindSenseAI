import re
import pandas as pd


class DataCleaner:

    @staticmethod
    def clean_text(text):
        if pd.isna(text):
            return ""

        text = str(text)

        # Remove URLs
        text = re.sub(r"http\\S+|www\\S+", "", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def remove_empty_rows(df, input_col, output_col):
        df = df.dropna(subset=[input_col, output_col])
        df = df[
            (df[input_col].str.strip() != "") &
            (df[output_col].str.strip() != "")
        ]
        return df

    @staticmethod
    def remove_duplicates(df):
        return df.drop_duplicates()

    @staticmethod
    def clean_dataframe(df, input_col, output_col):

        df[input_col] = df[input_col].apply(DataCleaner.clean_text)
        df[output_col] = df[output_col].apply(DataCleaner.clean_text)

        df = DataCleaner.remove_empty_rows(df, input_col, output_col)
        df = DataCleaner.remove_duplicates(df)

        return df