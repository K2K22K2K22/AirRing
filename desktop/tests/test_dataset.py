import numpy as np
import pytest

from airring.ai.dataset import stratified_split, validate_dataset
from airring.config import GESTURE_CLASSES, PACKET_WINDOW


def make_dataset(counts=None):
    counts = counts or {label: 5 for label in GESTURE_CLASSES}
    features = np.zeros((sum(counts.values()), PACKET_WINDOW, 6), dtype=np.float32)
    labels = np.concatenate([np.repeat(label, count) for label, count in counts.items()])
    return {
        "X": features,
        "y": labels,
        "classes": np.asarray(GESTURE_CLASSES),
    }


def test_validate_dataset_accepts_complete_dataset():
    features, labels, classes = validate_dataset(make_dataset())
    assert features.shape == (30, PACKET_WINDOW, 6)
    assert labels.shape == (30,)
    assert classes.tolist() == list(GESTURE_CLASSES)


def test_validate_dataset_rejects_missing_class():
    counts = {label: 5 for label in GESTURE_CLASSES[:-1]}
    with pytest.raises(ValueError, match="labels do not match"):
        validate_dataset(make_dataset(counts))


def test_validate_dataset_rejects_short_recording():
    data = make_dataset()
    data["X"] = np.zeros((30, PACKET_WINDOW - 1, 6), dtype=np.float32)
    with pytest.raises(ValueError, match="Expected features"):
        validate_dataset(data)


def test_stratified_split_is_reproducible_and_keeps_each_class():
    data = make_dataset({label: 10 for label in GESTURE_CLASSES})
    _features, labels, _classes = validate_dataset(data)

    first_train, first_validation = stratified_split(labels, seed=7)
    second_train, second_validation = stratified_split(labels, seed=7)

    assert np.array_equal(first_train, second_train)
    assert np.array_equal(first_validation, second_validation)
    assert len(first_train) == 48
    assert len(first_validation) == 12
    assert set(labels[first_validation].tolist()) == set(range(len(GESTURE_CLASSES)))
