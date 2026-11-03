from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from airring.ai.dataset import stratified_split, validate_dataset
from airring.ai.model import GestureLSTM
from airring.config import (
    DATASET_PATH,
    DEFAULT_TRAINING_SEED,
    DEFAULT_VALIDATION_FRACTION,
    MODEL_HIDDEN_SIZE,
    MODEL_INPUT_SIZE,
    MODEL_NUM_LAYERS,
    MODEL_PATH,
    PACKET_WINDOW,
    SAMPLE_RATE_HZ,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the AirRing LSTM gesture model")
    parser.add_argument("--data", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, default=MODEL_PATH)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--seed", type=int, default=DEFAULT_TRAINING_SEED)
    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error("epochs, batch size and learning rate must be positive")

    if not args.data.exists():
        raise FileNotFoundError(f"Dataset not found: {args.data}")

    with np.load(args.data, allow_pickle=False) as data:
        features, labels, classes = validate_dataset(data)

    train_idx, val_idx = stratified_split(labels, args.validation_fraction, args.seed)
    x_train = torch.from_numpy(features[train_idx])
    y_train = torch.from_numpy(labels[train_idx])
    x_val = torch.from_numpy(features[val_idx])
    y_val = torch.from_numpy(labels[val_idx])

    torch.manual_seed(args.seed)
    loader_generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        TensorDataset(x_train, y_train),
        batch_size=args.batch_size,
        shuffle=True,
        generator=loader_generator,
    )
    model = GestureLSTM(num_classes=len(classes))
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.CrossEntropyLoss()
    best_accuracy = -1.0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item())

        model.eval()
        with torch.no_grad():
            predictions = model(x_val).argmax(dim=1)
            accuracy = float((predictions == y_val).float().mean().item())

        print(f"Epoch {epoch:03d} loss={total_loss / len(train_loader):.4f} val_accuracy={accuracy:.3f}")
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            args.output.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "classes": classes.tolist(),
                    "input_size": MODEL_INPUT_SIZE,
                    "hidden_size": MODEL_HIDDEN_SIZE,
                    "num_layers": MODEL_NUM_LAYERS,
                    "sequence_length": PACKET_WINDOW,
                    "sample_rate": SAMPLE_RATE_HZ,
                },
                args.output,
            )

    print(f"Best validation accuracy: {best_accuracy:.3f}")
    print(f"Saved model: {args.output}")
    print("Use recordings from a separate session for a more reliable evaluation.")


if __name__ == "__main__":
    main()
