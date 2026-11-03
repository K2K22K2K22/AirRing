from __future__ import annotations

from collections import deque
from pathlib import Path
import time

import numpy as np

from ..config import (
    DEFAULT_GESTURE_CONFIDENCE,
    GESTURE_CLASSES,
    GESTURE_COOLDOWN_S,
    MODEL_HIDDEN_SIZE,
    MODEL_INPUT_SIZE,
    MODEL_NUM_LAYERS,
    MODEL_PATH,
    PACKET_WINDOW,
    SAMPLE_RATE_HZ,
)


class GestureRecognizer:
    def __init__(self, model_path: Path = MODEL_PATH, confidence: float = DEFAULT_GESTURE_CONFIDENCE):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence
        self.window: deque[tuple[float, ...]] = deque(maxlen=PACKET_WINDOW)
        self.model = None
        self.classes: list[str] = []
        self.last_fired = "idle"
        self.last_fired_at = 0.0
        self.cooldown_s = GESTURE_COOLDOWN_S
        self.samples_since_inference = 0
        self.enabled = False
        self.error: str | None = None
        self._load()

    def reset(self) -> None:
        self.window.clear()
        self.samples_since_inference = 0
        self.last_fired = "idle"
        self.last_fired_at = 0.0

    def _load(self) -> None:
        if not self.model_path.exists():
            self.error = "No trained model"
            return
        try:
            import torch
            from .model import GestureLSTM

            checkpoint = torch.load(self.model_path, map_location="cpu", weights_only=True)
            if not isinstance(checkpoint, dict):
                raise ValueError("checkpoint is not a mapping")

            required = {
                "model_state_dict", "classes", "input_size", "hidden_size",
                "num_layers", "sequence_length", "sample_rate",
            }
            missing = required - set(checkpoint)
            if missing:
                raise ValueError(f"missing checkpoint fields: {', '.join(sorted(missing))}")

            classes = list(checkpoint["classes"])
            if tuple(classes) != tuple(GESTURE_CLASSES):
                raise ValueError("checkpoint classes must match GESTURE_CLASSES in order")
            expected = {
                "input_size": MODEL_INPUT_SIZE,
                "hidden_size": MODEL_HIDDEN_SIZE,
                "num_layers": MODEL_NUM_LAYERS,
                "sequence_length": PACKET_WINDOW,
                "sample_rate": SAMPLE_RATE_HZ,
            }
            for name, value in expected.items():
                if checkpoint[name] != value:
                    raise ValueError(f"checkpoint {name} must be {value}")

            model = GestureLSTM(num_classes=len(classes))
            model.load_state_dict(checkpoint["model_state_dict"], strict=True)
            model.eval()
            self.classes = classes
            self.model = model
            self.enabled = True
            self.error = None
        except Exception as exc:
            self.model = None
            self.classes = []
            self.enabled = False
            self.error = f"Invalid checkpoint: {exc}"

    def add_sample(self, features: tuple[float, ...]) -> tuple[str, float] | None:
        self.window.append(features)
        self.samples_since_inference += 1
        if not self.enabled or len(self.window) < PACKET_WINDOW or self.samples_since_inference < 5:
            return None
        self.samples_since_inference = 0

        import torch

        values = np.asarray(self.window, dtype=np.float32)[None, :, :]
        with torch.no_grad():
            logits = self.model(torch.from_numpy(values))
            probabilities = torch.softmax(logits, dim=1)[0].numpy()
        index = int(np.argmax(probabilities))
        label = self.classes[index]
        confidence = float(probabilities[index])
        now = time.monotonic()

        if label == "idle":
            if now - self.last_fired_at >= self.cooldown_s:
                self.last_fired = "idle"
            return label, confidence

        ready = now - self.last_fired_at >= self.cooldown_s
        if confidence >= self.confidence_threshold and ready and self.last_fired == "idle":
            self.last_fired = label
            self.last_fired_at = now
            return label, confidence
        return None
