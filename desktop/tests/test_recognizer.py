import sys
import types

import pytest

from airring.ai.recognizer import GestureRecognizer
from airring.config import GESTURE_CLASSES


def test_missing_model_keeps_gestures_disabled(tmp_path):
    recognizer = GestureRecognizer(model_path=tmp_path / "missing.pt")
    for _ in range(60):
        assert recognizer.add_sample((0.0, 0.0, 1.0, 0.0, 0.0, 0.0)) is None

    assert recognizer.enabled is False
    assert recognizer.error == "No trained model"


def test_reset_clears_motion_window(tmp_path):
    recognizer = GestureRecognizer(model_path=tmp_path / "missing.pt")
    for _ in range(10):
        recognizer.add_sample((0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    recognizer.reset()

    assert len(recognizer.window) == 0
    assert recognizer.samples_since_inference == 0
    assert recognizer.last_fired == "idle"


def valid_checkpoint():
    return {
        "model_state_dict": {},
        "classes": list(GESTURE_CLASSES),
        "input_size": 6,
        "hidden_size": 64,
        "num_layers": 2,
        "sequence_length": 50,
        "sample_rate": 50,
    }


@pytest.fixture
def checkpoint_file(monkeypatch, tmp_path):
    checkpoint = valid_checkpoint()

    torch_module = types.ModuleType("torch")
    torch_module.load = lambda *args, **kwargs: checkpoint

    class FakeModel:
        def __init__(self, num_classes=6):
            self.num_classes = num_classes

        def load_state_dict(self, state, strict=True):
            if state != checkpoint["model_state_dict"]:
                raise ValueError("bad state")

        def eval(self):
            return self

    model_module = types.ModuleType("airring.ai.model")
    model_module.GestureLSTM = FakeModel

    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "airring.ai.model", model_module)

    path = tmp_path / "model.pt"
    path.write_bytes(b"fake")
    return path, checkpoint


def test_valid_checkpoint_enables_recognizer(checkpoint_file):
    path, _checkpoint = checkpoint_file
    recognizer = GestureRecognizer(model_path=path)

    assert recognizer.enabled is True
    assert recognizer.error is None
    assert recognizer.classes == list(GESTURE_CLASSES)


def test_missing_checkpoint_fields_are_rejected(checkpoint_file):
    path, checkpoint = checkpoint_file
    del checkpoint["sample_rate"]
    recognizer = GestureRecognizer(model_path=path)

    assert recognizer.enabled is False
    assert "missing checkpoint fields" in recognizer.error
    assert recognizer.model is None


def test_permuted_checkpoint_classes_are_rejected(checkpoint_file):
    path, checkpoint = checkpoint_file
    checkpoint["classes"] = list(reversed(GESTURE_CLASSES))
    recognizer = GestureRecognizer(model_path=path)

    assert recognizer.enabled is False
    assert "in order" in recognizer.error


def test_wrong_checkpoint_window_is_rejected(checkpoint_file):
    path, checkpoint = checkpoint_file
    checkpoint["sequence_length"] = 25
    recognizer = GestureRecognizer(model_path=path)

    assert recognizer.enabled is False
    assert "sequence_length must be 50" in recognizer.error


def test_wrong_checkpoint_sample_rate_is_rejected(checkpoint_file):
    path, checkpoint = checkpoint_file
    checkpoint["sample_rate"] = 100
    recognizer = GestureRecognizer(model_path=path)

    assert recognizer.enabled is False
    assert "sample_rate must be 50" in recognizer.error


def test_invalid_checkpoint_clears_previous_model(checkpoint_file):
    path, checkpoint = checkpoint_file
    recognizer = GestureRecognizer(model_path=path)
    assert recognizer.enabled is True

    checkpoint["hidden_size"] = 999
    recognizer._load()

    assert recognizer.enabled is False
    assert recognizer.model is None
    assert recognizer.classes == []
