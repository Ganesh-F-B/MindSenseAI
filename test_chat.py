from chatbot.conversation.chat_engine import ChatEngine

bot = ChatEngine()

print("=" * 60)
print("MindSenseAI Chat")
print("Type 'exit' to quit")
print("=" * 60)

while True:

    user = input("\nYou : ")

    if user.lower() == "exit":
        break

    result = bot.chat(user)

    print("\nMindSenseAI :", result["response"])

    print("\n[Developer View]")
    print("Intent    :", result["intent"])
    print("Emotion   :", result["emotion"])