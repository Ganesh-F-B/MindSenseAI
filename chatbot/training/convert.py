from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = BASE_DIR / "datasets" / "processed"
FINAL_DIR = BASE_DIR / "datasets" / "final"

FINAL_DIR.mkdir(exist_ok=True)

conversation_data = []
emotion_data = []


def convert_train():
    print("Converting train.csv...")

    df = pd.read_csv(PROCESSED_DIR / "train.csv")

    for _, row in df.iterrows():
        conversation_data.append({
            "input": row["Context"],
            "response": row["Response"],
            "source": "train"
        })
def convert_counselchat():

    print("Converting counselchat-data.csv...")

    df = pd.read_csv(PROCESSED_DIR / "counselchat-data.csv")

    for _, row in df.iterrows():

        conversation_data.append({
            "input": row["questionText"],
            "response": row["answerText"],
            "source": "counselchat"
        })
def convert_counselchat2():

    print("Converting counsel_chat2.csv...")

    df = pd.read_csv(PROCESSED_DIR / "counsel_chat2.csv")

    for _, row in df.iterrows():

        conversation_data.append({
            "input": row["questionText"],
            "response": row["answerText"],
            "source": "counselchat2"
        })
def convert_oasst():

    print("Converting oasst1.csv...")

    df = pd.read_csv(PROCESSED_DIR / "oasst1.csv")

    # Keep only required columns
    df = df[["message_id", "parent_id", "role", "text"]]

    # Fast lookup by message_id
    messages = df.set_index("message_id").to_dict("index")

    pairs = 0

    for _, row in df.iterrows():

        # We only want assistant replies
        if row["role"] != "assistant":
            continue

        parent = row["parent_id"]

        if pd.isna(parent):
            continue

        if parent not in messages:
            continue

        parent_msg = messages[parent]

        # Parent must be the user
        if parent_msg["role"] != "prompter":
            continue

        conversation_data.append({
            "input": parent_msg["text"],
            "response": row["text"],
            "source": "oasst"
        })

        pairs += 1

    print(f"Added {pairs} conversation pairs.")

def convert_emotion():

    print("Converting emotion.csv...")

    df = pd.read_csv(PROCESSED_DIR / "emotion.csv")

    for _, row in df.iterrows():

        emotion_data.append({
            "text": row["text"],
            "emotion": row["label"],
            "source": "emotion"
        })
def convert_go_emotions():

    print("Converting go_emotions.csv...")

    df = pd.read_csv(PROCESSED_DIR / "go_emotions.csv")

    for _, row in df.iterrows():

        emotion_data.append({
            "text": row["text"],
            "emotion": row["labels"],
            "source": "go_emotions"
        })

def save_files():

    conversation_df = pd.DataFrame(conversation_data)

    emotion_df = pd.DataFrame(emotion_data)

    conversation_df.insert(0, "id", range(1, len(conversation_df) + 1))
    emotion_df.insert(0, "id", range(1, len(emotion_df) + 1))

    conversation_df.to_csv(
        FINAL_DIR / "conversation.csv",
        index=False
    )

    emotion_df.to_csv(
        FINAL_DIR / "emotion.csv",
        index=False
    )

    print("\nConversation Dataset")
    print(conversation_df.head())

    print("\nEmotion Dataset")
    print(emotion_df.head())

    print("\nSaved:")
    print("conversation.csv")
    print("emotion.csv")


def main():

    convert_train()

    convert_counselchat()

    convert_counselchat2()

    convert_oasst()

    convert_emotion()

    convert_go_emotions()

    save_files()


if __name__ == "__main__":
    main()