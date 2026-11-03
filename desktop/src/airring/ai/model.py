from __future__ import annotations

import torch
from torch import nn

from ..config import MODEL_HIDDEN_SIZE, MODEL_INPUT_SIZE, MODEL_NUM_LAYERS


class GestureLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = MODEL_INPUT_SIZE,
        hidden_size: int = MODEL_HIDDEN_SIZE,
        num_layers: int = MODEL_NUM_LAYERS,
        num_classes: int = 6,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0,
        )
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs, _ = self.lstm(inputs)
        return self.classifier(outputs[:, -1, :])
