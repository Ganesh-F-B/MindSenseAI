import pandas as pd

print("LOADING DATASET...")

df = pd.read_csv("mental_heath_feature_engineered.csv")

print("\nDATASET SHAPE:")
print(df.shape)

print("\nCOLUMNS:")
print(df.columns)

print("\nFIRST 5 ROWS:")
print(df.head())

print("\nNULL VALUES:")
print(df.isnull().sum())