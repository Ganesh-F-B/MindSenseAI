import pandas as pd

df = pd.read_csv("chatbot/datasets/counseling/counsel_chat2.csv")

print("=" * 70)
print("Counsel Chat 2 Analysis")
print("=" * 70)

print("\nColumns:")
print(df.columns.tolist())

print("\nTopic Distribution:")
print(df["topic"].value_counts())

print("\nFirst 5 Rows:")
print(df[["questionText", "topic"]].head())