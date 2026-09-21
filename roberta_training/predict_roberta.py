from transformers import RobertaTokenizerFast, RobertaForSequenceClassification
import torch
import json

# =========================
# LOAD MODEL
# =========================
MODEL_PATH = "./roberta_model"

tokenizer = RobertaTokenizerFast.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)

# =========================
# LOAD LABEL MAP
# =========================
with open("label_map.json", "r") as f:
    label_map = json.load(f)

# Convert keys to int
label_map = {int(k): v for k, v in label_map.items()}

# =========================
# DEVICE
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model.to(device)
model.eval()

print("✅ RoBERTa Mental Health Predictor Ready!")

# =========================
# LIVE PREDICTION LOOP
# =========================
while True:

    text = input("\nEnter message (type quit to exit): ")

    if text.lower() == "quit":
        break

    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    # Move to GPU
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Prediction
    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)

    predicted_class = torch.argmax(probabilities, dim=1).item()
    confidence = probabilities[0][predicted_class].item()

    label = label_map[predicted_class]

    print("\n======================")
    print("PREDICTION RESULT")
    print("======================")
    print(f"Mental State : {label}")
    print(f"Confidence   : {confidence * 100:.2f}%")