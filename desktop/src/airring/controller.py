from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

from . import config
from .packet import SensorSample


class MouseBackend(Protocol):
    def moveRel(self, x: int, y: int, duration: float = 0) -> None: ...
    def mouseDown(self, button: str = "left") -> None: ...
    def mouseUp(self, button: str = "left") -> None: ...
    def click(self, button: str = "left") -> None: ...
    def scroll(self, clicks: int) -> None: ...
    def press(self, key: str) -> None: ...


@dataclass
class ControllerState:
    calibrated: bool = False
    calibration_samples: int = 0
    cursor_enabled: bool = True
    sensor_ready: bool = False
    last_gesture: str = "None"


class AirMouseController:
    def __init__(
        self,
        mouse: MouseBackend | None = None,
        sensitivity: float = config.DEFAULT_SENSITIVITY,
        deadzone_dps: float = config.DEFAULT_DEADZONE_DPS,
        calibration_samples: int = 100,
    ) -> None:
        self.mouse = mouse or self._load_mouse_backend()
        self.sensitivity = sensitivity
        self.deadzone_dps = deadzone_dps
        self.calibration_target = calibration_samples
        self.state = ControllerState()
        self._gyro_sum = [0.0, 0.0, 0.0]
        self._gyro_bias = [0.0, 0.0, 0.0]
        self._last_time: float | None = None
        self._last_sequence: int | None = None
        self._filtered = [0.0, 0.0, 0.0]
        self._left_down = False
        self._left_contact_active = False
        self._right_down = False
        self._fraction_x = 0.0
        self._fraction_y = 0.0

    @staticmethod
    def _load_mouse_backend() -> MouseBackend:
        try:
            import pyautogui
        except Exception as exc:
            raise RuntimeError(
                "PyAutoGUI could not initialize. Check desktop input permissions and display session."
            ) from exc
        pyautogui.FAILSAFE = True
        return pyautogui

    @staticmethod
    def _apply_deadzone(value: float, threshold: float) -> float:
        if abs(value) <= threshold:
            return 0.0
        return value - threshold if value > 0 else value + threshold

    def begin_calibration(self) -> None:
        self.state.calibrated = False
        self.state.calibration_samples = 0
        self.state.sensor_ready = False
        self._gyro_sum = [0.0, 0.0, 0.0]
        self._gyro_bias = [0.0, 0.0, 0.0]
        self._last_time = None
        self._last_sequence = None
        self._filtered = [0.0, 0.0, 0.0]
        self._fraction_x = 0.0
        self._fraction_y = 0.0
        self._release_left()
        self._left_contact_active = False
        self._right_down = False

    def set_sensitivity(self, value: float) -> None:
        self.sensitivity = max(0.2, min(float(value), 8.0))

    def set_deadzone(self, value: float) -> None:
        self.deadzone_dps = max(0.0, min(float(value), 20.0))

    def toggle_cursor(self) -> bool:
        self.state.cursor_enabled = not self.state.cursor_enabled
        if not self.state.cursor_enabled:
            self._release_left()
        return self.state.cursor_enabled

    def process_sample(self, sample: SensorSample, now: float | None = None) -> None:
        self.state.sensor_ready = sample.sensor_ready
        if not sample.sensor_ready:
            self.begin_calibration()
            return

        if now is None:
            if self._last_sequence is None:
                dt = 1.0 / config.SAMPLE_RATE_HZ
            else:
                sequence_delta = (sample.sequence - self._last_sequence) & 0xFFFF
                dt = max(1, sequence_delta) / config.SAMPLE_RATE_HZ
            self._last_time = time.monotonic()
        else:
            dt = 1.0 / config.SAMPLE_RATE_HZ if self._last_time is None else now - self._last_time
            self._last_time = now
        self._last_sequence = sample.sequence
        dt = max(0.001, min(dt, 0.06))

        gyro = [value / 100.0 for value in sample.gyroscope_centi_dps]
        if not self.state.calibrated:
            for index, value in enumerate(gyro):
                self._gyro_sum[index] += value
            self.state.calibration_samples += 1
            if self.state.calibration_samples >= self.calibration_target:
                self._gyro_bias = [value / self.calibration_target for value in self._gyro_sum]
                self.state.calibrated = True
            return

        if not self.state.cursor_enabled:
            self._left_contact_active = sample.left_contact
            self._right_down = sample.right_contact
            return

        self._process_contacts(sample)

        x_axis = config.CURSOR_X_GYRO_AXIS
        y_axis = config.CURSOR_Y_GYRO_AXIS
        x_rate = self._apply_deadzone(gyro[x_axis] - self._gyro_bias[x_axis], self.deadzone_dps)
        y_rate = self._apply_deadzone(gyro[y_axis] - self._gyro_bias[y_axis], self.deadzone_dps)

        alpha = 0.45
        self._filtered[0] = alpha * x_rate + (1.0 - alpha) * self._filtered[0]
        self._filtered[1] = alpha * y_rate + (1.0 - alpha) * self._filtered[1]

        self._fraction_x += self._filtered[0] * dt * self.sensitivity * config.CURSOR_X_SIGN
        self._fraction_y += self._filtered[1] * dt * self.sensitivity * config.CURSOR_Y_SIGN
        dx = int(self._fraction_x)
        dy = int(self._fraction_y)
        self._fraction_x -= dx
        self._fraction_y -= dy
        if dx or dy:
            self.mouse.moveRel(dx, dy, duration=0)

    def _process_contacts(self, sample: SensorSample) -> None:
        left = sample.left_contact
        right = sample.right_contact

        if left and not self._left_contact_active:
            self.mouse.mouseDown(button="left")
            self._left_down = True
        elif not left and self._left_down:
            self._release_left()
        self._left_contact_active = left

        if right and not self._right_down:
            self.mouse.click(button="right")
        self._right_down = right

    def _release_left(self) -> None:
        if self._left_down:
            self.mouse.mouseUp(button="left")
            self._left_down = False

    def handle_gesture(self, label: str) -> None:
        actions = {
            "swipe_left": lambda: self.mouse.press("left"),
            "swipe_right": lambda: self.mouse.press("right"),
            "circle_cw": lambda: self.mouse.scroll(4),
            "circle_ccw": lambda: self.mouse.scroll(-4),
            "double_flick": self.toggle_cursor,
        }
        action = actions.get(label)
        if action is not None:
            action()
            self.state.last_gesture = label

    def disconnect(self) -> None:
        self.begin_calibration()
