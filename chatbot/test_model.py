import torch

from training.model import EmotionClassifier

model = EmotionClassifier()

print("=" * 60)

print(model)

print("=" * 60)

dummy_input = torch.randint(
    0,
    1000,
    (2, 128)
)

dummy_mask = torch.ones(
    (2, 128),
    dtype=torch.long
)

output = model(
    dummy_input,
    dummy_mask
)

print("Logits Shape :")

print(output["logits"].shape)

print()

print("Embedding Shape :")

print(output["embedding"].shape)

print("=" * 60)