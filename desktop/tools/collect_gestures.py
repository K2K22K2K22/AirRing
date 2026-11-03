from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import numpy as np
from bleak import BleakClient, BleakScanner

from airring.config import (
    DEVICE_NAME_PREFIX,
    GESTURE_CLASSES,
    SAMPLE_RATE_HZ,
    SENSOR_UUID,
    DATASET_PATH,
    PACKET_WINDOW,
)
from airring.packet import decode_packet


async def collect(repetitions: int, output: Path) -> None:
    device = await BleakScanner.find_device_by_filter(
        lambda d, a: (a.local_name or d.name or "").startswith(DEVICE_NAME_PREFIX),
        timeout=12.0,
    )
    if device is None:
        raise RuntimeError("AirRing was not found. Power it on and keep it nearby.")

    recordings: list[np.ndarray] = []
    labels: list[str] = []

    async with BleakClient(device, timeout=10.0) as client:
        active = False
        frames: list[tuple[float, ...]] = []
        ready = asyncio.Event()

        def on_notify(_sender: int, data: bytearray) -> None:
            nonlocal active
            if not active:
                return
            try:
                sample = decode_packet(data)
                frames.append(sample.features)
                if len(frames) >= PACKET_WINDOW:
                    ready.set()
            except ValueError:
                return

        await client.start_notify(SENSOR_UUID, on_notify)
        print(f"Connected to {device.name}. Each recording lasts about one second.")

        for label in GESTURE_CLASSES:
            print(f"\nGesture: {label}")
            for index in range(repetitions):
                await asyncio.to_thread(
                    input,
                    f"Trial {index + 1}/{repetitions}. Press Enter and perform {label}: ",
                )
                frames.clear()
                ready.clear()
                active = True
                print("Recording...")
                try:
                    await asyncio.wait_for(ready.wait(), timeout=2.5)
                except asyncio.TimeoutError:
                    print("Not enough sensor samples. Repeat this trial.")
                    continue
                finally:
                    active = False
                recordings.append(np.asarray(frames[:PACKET_WINDOW], dtype=np.float32))
                labels.append(label)
                print("Recorded")

        await client.stop_notify(SENSOR_UUID)

    if not recordings:
        raise RuntimeError("No recordings were collected.")

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        X=np.stack(recordings),
        y=np.asarray(labels),
        classes=np.asarray(GESTURE_CLASSES),
        sequence_length=np.asarray(PACKET_WINDOW),
        sample_rate=np.asarray(SAMPLE_RATE_HZ),
    )
    print(f"Saved {len(recordings)} recordings to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect AirRing LSTM training data")
    parser.add_argument("--repetitions", type=int, default=25)
    parser.add_argument("--output", type=Path, default=DATASET_PATH)
    args = parser.parse_args()
    if args.repetitions < 5:
        parser.error("Use at least five repetitions per gesture")
    asyncio.run(collect(args.repetitions, args.output))


if __name__ == "__main__":
    main()
