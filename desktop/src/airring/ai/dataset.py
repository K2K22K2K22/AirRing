from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ..config import (
    DEFAULT_TRAINING_SEED,
    DEFAULT_VALIDATION_FRACTION,
    GESTURE_CLASSES,
    MIN_RECORDINGS_PER_CLASS,
    MODEL_INPUT_SIZE,
    PACKET_WINDOW,
)


def stratified_split(
    labels: np.ndarray,
    validation_fraction: float = DEFAULT_VALIDATION_FRACTION,
    seed: int = DEFAULT_TRAINING_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between zero and one")

    rng = np.random.default_rng(seed)
    train_indices: list[int] = []
    validation_indices: list[int] = []
    for label in np.unique(labels):
        indices = np.flatnonzero(labels == label)
        if len(indices) < 2:
            raise ValueError(f"Class {label} needs at least two recordings to split")
        rng.shuffle(indices)
        holdout = max(1, int(round(len(indices) * validation_fraction)))
        holdout = min(holdout, len(indices) - 1)
        validation_indices.extend(indices[:holdout].tolist())
        train_indices.extend(indices[holdout:].tolist())

    train = np.asarray(train_indices, dtype=np.int64)
    validation = np.asarray(validation_indices, dtype=np.int64)
    rng.shuffle(train)
    rng.shuffle(validation)
    return train, validation


def validate_dataset(data: Mapping[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    missing = {"X", "y", "classes"} - set(data.files if hasattr(data, "files") else data)
    if missing:
        raise ValueError(f"Dataset is missing: {', '.join(sorted(missing))}")

    features = np.asarray(data["X"], dtype=np.float32)
    labels_text = np.asarray(data["y"]).astype(str)
    stored_classes = np.asarray(data["classes"]).astype(str).tolist()

    if features.ndim != 3 or features.shape[1:] != (PACKET_WINDOW, MODEL_INPUT_SIZE):
        raise ValueError(f"Expected features with shape (recordings, {PACKET_WINDOW}, {MODEL_INPUT_SIZE})")
    if not np.isfinite(features).all():
        raise ValueError("Dataset contains non-finite sensor values")
    if stored_classes != list(GESTURE_CLASSES):
        raise ValueError(f"Dataset classes must be {list(GESTURE_CLASSES)}")
    if labels_text.ndim != 1 or len(labels_text) != len(features):
        raise ValueError("Labels must contain one entry per recording")
    if set(labels_text.tolist()) != set(GESTURE_CLASSES):
        raise ValueError("Dataset labels do not match the expected gesture classes")

    label_map = {label: index for index, label in enumerate(GESTURE_CLASSES)}
    labels = np.asarray([label_map[label] for label in labels_text], dtype=np.int64)
    for label in GESTURE_CLASSES:
        count = int(np.sum(labels_text == label))
        if count < MIN_RECORDINGS_PER_CLASS:
            raise ValueError(f"Class {label} has {count} recordings; need at least {MIN_RECORDINGS_PER_CLASS}")
    return features, labels, np.asarray(GESTURE_CLASSES)
