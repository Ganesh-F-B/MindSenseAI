from training.dataset import create_dataloaders

train_loader, val_loader, test_loader = create_dataloaders()

print("=" * 60)

print("Train batches :", len(train_loader))
print("Validation batches :", len(val_loader))
print("Test batches :", len(test_loader))

batch = next(iter(train_loader))

print("\nBatch Keys")

print(batch.keys())

print("\nInput Shape")

print(batch["input_ids"].shape)

print("\nAttention Shape")

print(batch["attention_mask"].shape)

print("\nLabels Shape")

print(batch["label"].shape)

print("=" * 60)