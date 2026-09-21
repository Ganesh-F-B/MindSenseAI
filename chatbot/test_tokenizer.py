from transformers import AutoTokenizer

MODEL_NAME = "distilbert-base-uncased"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

text = "I feel lonely today."

encoded = tokenizer(text)

print("=" * 50)
print("Input:")
print(text)

print("\nToken IDs:")
print(encoded["input_ids"])

print("\nTokens:")
print(tokenizer.convert_ids_to_tokens(encoded["input_ids"]))
print("=" * 50)