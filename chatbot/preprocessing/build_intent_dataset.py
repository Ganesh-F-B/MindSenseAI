import pandas as pd

from intent_mapping import INTENT_MAPPING

# Load counseling dataset
df = pd.read_csv("chatbot/datasets/counseling/counselchat-data.csv")

rows = []

for _, row in df.iterrows():

    question = str(row["questionText"]).strip()

    topics = str(row["topics"]).split(",")

    for topic in topics:

        topic = topic.strip()

        if topic in INTENT_MAPPING:

            rows.append({
                "text": question,
                "intent": INTENT_MAPPING[topic]
            })

intent_df = pd.DataFrame(rows)

# Remove duplicates
intent_df = intent_df.drop_duplicates()

# Shuffle dataset
intent_df = intent_df.sample(frac=1, random_state=42).reset_index(drop=True)

# Save
intent_df.to_csv(
    "chatbot/datasets/raw/intent_dataset.csv",
    index=False
)

print("=" * 60)
print("Intent dataset created successfully!")
print("=" * 60)

print("Total Samples :", len(intent_df))
print("\nIntent Distribution:\n")
print(intent_df["intent"].value_counts())