from chatbot.nlp.pipeline import NLPPipeline


def main():

    pipeline = NLPPipeline()

    print("\nMindSenseAI NLP Pipeline")
    print("-" * 40)

    while True:

        text = input("\nYou: ")

        if text.lower() == "exit":
            break

        result = pipeline.predict(text)

        print("\nPrediction")
        print("-" * 40)

        print(f"Emotion : {result['emotion']['emotion']}")
        print(f"Confidence : {result['emotion']['confidence']}%")

        print()

        print(f"Intent : {result['intent']['intent']}")
        print(f"Confidence : {result['intent']['confidence']}")


if __name__ == "__main__":
    main()