import torch
from tqdm import tqdm

from chatbot.intent.config import GRADIENT_CLIP


def train_one_epoch(
    model,
    dataloader,
    optimizer,
    scheduler,
    criterion,
    device,
):

    model.train()

    total_loss = 0.0
    correct = 0
    total = 0

    progress = tqdm(
        dataloader,
        desc="Training",
        leave=False
    )

    for batch in progress:

        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        labels = batch["label"].to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs["logits"]

        loss = criterion(logits, labels)

        loss.backward()

        # Prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            GRADIENT_CLIP
        )

        optimizer.step()
        if scheduler is not None:

             scheduler.step()

        total_loss += loss.item()

        predictions = torch.argmax(logits, dim=1)

        correct += (predictions == labels).sum().item()

        total += labels.size(0)

        accuracy = 100.0 * correct / total

        progress.set_postfix(
            loss=f"{loss.item():.4f}",
            acc=f"{accuracy:.2f}%"
        )

    average_loss = total_loss / max(len(dataloader), 1)
    accuracy = 100.0 * correct / total

    return average_loss, accuracy


@torch.no_grad()
def validate_one_epoch(
    model,
    dataloader,
    criterion,
    device,
):

    model.eval()

    total_loss = 0.0
    correct = 0
    total = 0

    progress = tqdm(
        dataloader,
        desc="Validation",
        leave=False
    )

    for batch in progress:

        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        labels = batch["label"].to(device, non_blocking=True)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs["logits"]

        loss = criterion(logits, labels)

        total_loss += loss.item()

        predictions = torch.argmax(logits, dim=1)

        correct += (predictions == labels).sum().item()

        total += labels.size(0)

    average_loss = total_loss / max(len(dataloader), 1)
    accuracy = 100.0 * correct / total

    return average_loss, accuracy