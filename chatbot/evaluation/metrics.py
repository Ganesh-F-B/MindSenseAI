from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


def calculate_metrics(y_true, y_pred):
    """
    Calculate evaluation metrics.
    """

    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0
        ),
        "recall": recall_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0
        ),
        "f1_score": f1_score(
            y_true,
            y_pred,
            average="weighted",
            zero_division=0
        )
    }

    return metrics


def get_classification_report(y_true, y_pred, class_names):
    """
    Generate classification report.
    """

    return classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=4,
        zero_division=0
    )


def get_confusion_matrix(y_true, y_pred):
    """
    Generate confusion matrix.
    """

    return confusion_matrix(y_true, y_pred)