from chatbot.conversation.chat_engine import ChatEngine


def test_chat_engine_defers_predictor_initialization():
    engine = ChatEngine()

    assert engine.intent_predictor is None
    assert engine.emotion_predictor is None
