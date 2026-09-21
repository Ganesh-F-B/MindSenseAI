import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay


def plot_confusion_matrix(cm, class_names, save_path=None):
    """
    Plot and save confusion matrix.
    """

    fig, ax = plt.subplots(figsize=(8, 6))

    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=class_names
    )

    disp.plot(ax=ax, cmap="Blues", colorbar=False)

    plt.title("Confusion Matrix")
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)

    plt.show()
    plt.close()


def plot_training_history(history, save_dir=None):
    """
    Plot training and validation curves.
    """

    epochs = np.arange(1, len(history["train_loss"]) + 1)

    # Loss Plot
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, history["train_loss"], label="Train Loss")
    plt.plot(epochs, history["val_loss"], label="Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training vs Validation Loss")
    plt.legend()
    plt.grid(True)

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        plt.savefig(os.path.join(save_dir, "loss_curve.png"), dpi=300)

    plt.show()
    plt.close()

    # Accuracy Plot
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, history["train_accuracy"], label="Train Accuracy")
    plt.plot(epochs, history["val_accuracy"], label="Validation Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Training vs Validation Accuracy")
    plt.legend()
    plt.grid(True)

    if save_dir:
        plt.savefig(os.path.join(save_dir, "accuracy_curve.png"), dpi=300)

    plt.show()
    plt.close()