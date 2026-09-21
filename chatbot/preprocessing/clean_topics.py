import pandas as pd

# Load dataset
df = pd.read_csv("chatbot/datasets/counseling/counselchat-data.csv")

# Get all unique topics
all_topics = set()

for topic in df["topics"].dropna():

    for item in str(topic).split(","):

        item = item.strip()

        if item:
            all_topics.add(item)

# Sort alphabetically
all_topics = sorted(all_topics)

print("=" * 60)
print("Unique Topics")
print("=" * 60)

for topic in all_topics:
    print(topic)

print("\nTotal Unique Topics:", len(all_topics))
