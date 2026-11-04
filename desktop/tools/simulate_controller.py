from __future__ import annotations

from collections import Counter

from airring.controller import AirMouseController
from airring.packet import SensorSample


class RecordingMouse:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def moveRel(self, x: int, y: int, duration: float = 0) -> None:
        self.events.append(("move", x, y))

    def mouseDown(self, button: str = "left") -> None:
        self.events.append(("down", button))

    def mouseUp(self, button: str = "left") -> None:
        self.events.append(("up", button))

    def click(self, button: str = "left") -> None:
        self.events.append(("click", button))

    def scroll(self, clicks: int) -> None:
        self.events.append(("scroll", clicks))

    def press(self, key: str) -> None:
        self.events.append(("press", key))


def make_sample(sequence: int, contacts: int = 0, gyro_z: int = 0) -> SensorSample:
    return SensorSample(
        sequence=sequence,
        acceleration_mg=(0, 0, 1000),
        gyroscope_centi_dps=(0, 0, gyro_z),
        contacts=contacts,
    )


def main() -> None:
    mouse = RecordingMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=10)
    sequence = 0
    timestamp = 0.0

    def feed(count: int, contacts: int = 0, gyro_z: int = 0) -> None:
        nonlocal sequence, timestamp
        for _ in range(count):
            controller.process_sample(
                make_sample(sequence, contacts, gyro_z), now=timestamp
            )
            sequence += 1
            timestamp += 0.02

    feed(10)
    assert controller.state.calibrated

    feed(20, gyro_z=12000)
    assert any(event[0] == "move" for event in mouse.events)

    feed(2, contacts=1)
    feed(1)
    assert ("down", "left") in mouse.events
    assert ("up", "left") in mouse.events

    feed(1, contacts=2)
    assert ("click", "right") in mouse.events

    for gesture in ("swipe_left", "swipe_right", "circle_cw", "circle_ccw"):
        controller.handle_gesture(gesture)

    controller.handle_gesture("double_flick")
    assert controller.state.cursor_enabled is False
    controller.toggle_cursor()

    feed(1, contacts=1)
    controller.disconnect()
    assert controller.state.calibrated is False
    assert controller._left_down is False

    feed(10)
    assert controller.state.calibrated is True

    counts = Counter(event[0] for event in mouse.events)
    total_x = sum(int(event[1]) for event in mouse.events if event[0] == "move")
    total_y = sum(int(event[2]) for event in mouse.events if event[0] == "move")

    print("AirRing desktop input simulation")
    print(f"Calibration completed: {controller.state.calibrated}")
    print(f"Recorded mouse events: {len(mouse.events)}")
    print(f"Cursor movement: x={total_x}, y={total_y}")
    print(f"Event counts: {dict(counts)}")
    print("No real mouse, BLE device or MPU6050 was used.")


if __name__ == "__main__":
    main()
