from __future__ import annotations

import argparse
import asyncio
import queue
import threading
import tkinter as tk
from tkinter import ttk

from . import config
from .ai.recognizer import GestureRecognizer
from .ble import run_ble_client
from .controller import AirMouseController
from .packet import SensorSample


class AirRingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AirRing")
        self.root.geometry("470x370")
        self.root.minsize(420, 340)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.ble_thread: threading.Thread | None = None
        self.connected = False
        self.controller = AirMouseController()
        self.recognizer = GestureRecognizer()
        self.ai_enabled = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="Starting Bluetooth scan")
        self.calibration_var = tk.StringVar(value="Keep the device still while calibrating")
        self.gesture_var = tk.StringVar(value="None")
        self.ai_var = tk.StringVar(value=self._ai_status())
        self.pointer_var = tk.StringVar(value="Pointer enabled")

        self._build_ui()
        self._start_ble()
        self.root.after(20, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="AirRing", font=("TkDefaultFont", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Wearable mouse and gesture controller").pack(anchor="w", pady=(0, 14))

        status = ttk.LabelFrame(outer, text="Device", padding=10)
        status.pack(fill="x", pady=5)
        ttk.Label(status, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(status, textvariable=self.calibration_var).pack(anchor="w", pady=(5, 0))

        controls = ttk.LabelFrame(outer, text="Pointer", padding=10)
        controls.pack(fill="x", pady=5)
        row = ttk.Frame(controls)
        row.pack(fill="x")
        ttk.Label(row, text="Sensitivity").pack(side="left")
        self.sensitivity = tk.DoubleVar(value=self.controller.sensitivity)
        ttk.Scale(
            row, from_=0.5, to=7.0, variable=self.sensitivity,
            command=self._change_sensitivity,
        ).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(row, text="Recalibrate", command=self._recalibrate).pack(side="right")
        deadzone_row = ttk.Frame(controls)
        deadzone_row.pack(fill="x", pady=(8, 0))
        ttk.Label(deadzone_row, text="Dead zone").pack(side="left")
        self.deadzone = tk.DoubleVar(value=self.controller.deadzone_dps)
        ttk.Scale(
            deadzone_row, from_=0, to=15, variable=self.deadzone,
            command=self._change_deadzone,
        ).pack(side="left", fill="x", expand=True, padx=10)
        self.pointer_button = ttk.Button(controls, textvariable=self.pointer_var, command=self._toggle_pointer)
        self.pointer_button.pack(anchor="w", pady=(8, 0))

        ai_frame = ttk.LabelFrame(outer, text="Gesture recognition", padding=10)
        ai_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(
            ai_frame, text="Enable trained LSTM model", variable=self.ai_enabled,
            command=self._toggle_ai,
        ).pack(anchor="w")
        ttk.Label(ai_frame, textvariable=self.ai_var).pack(anchor="w", pady=(4, 0))
        ttk.Label(ai_frame, text="Last gesture:").pack(anchor="w", pady=(7, 0))
        ttk.Label(ai_frame, textvariable=self.gesture_var, font=("TkDefaultFont", 12, "bold")).pack(anchor="w")

        footer = ttk.Label(outer, text="Index contact: left click and drag   |   Middle contact: right click")
        footer.pack(anchor="w", pady=(12, 0))

    def _ai_status(self) -> str:
        if self.recognizer.enabled:
            return "Model loaded"
        if self.recognizer.error and self.recognizer.error != "No trained model":
            return self.recognizer.error
        return "Train a model to enable AI gestures"

    def _toggle_ai(self) -> None:
        if not self.ai_enabled.get():
            self.recognizer.reset()

    def _start_ble(self) -> None:
        def worker() -> None:
            asyncio.run(
                run_ble_client(
                    on_sample=lambda sample: self.events.put(("sample", sample)),
                    on_status=lambda status: self.events.put(("status", status)),
                    stop_event=self.stop_event,
                )
            )

        self.ble_thread = threading.Thread(target=worker, name="AirRingBLE", daemon=True)
        self.ble_thread.start()

    def _poll_events(self) -> None:
        processed = 0
        while processed < 100:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            processed += 1

            if kind == "status":
                status = str(value)
                self.status_var.set(status)
                if status.startswith("Connected"):
                    self.connected = True
                elif status.startswith(("Disconnected", "BLE error", "Stopped")) and self.connected:
                    self.connected = False
                    self.controller.disconnect()
                    self.recognizer.reset()
                    self.calibration_var.set("Disconnected")
            elif kind == "sample" and isinstance(value, SensorSample):
                self._handle_sample(value)

        self.root.after(20, self._poll_events)

    def _handle_sample(self, sample: SensorSample) -> None:
        self.controller.process_sample(sample)

        if not self.controller.state.sensor_ready:
            self.calibration_var.set("MPU6050 unavailable. Check wiring.")
        elif self.controller.state.calibrated:
            self.calibration_var.set("Calibrated")
        else:
            count = self.controller.state.calibration_samples
            target = self.controller.calibration_target
            self.calibration_var.set(f"Calibrating: {count}/{target}. Keep still.")

        if self.ai_enabled.get() and self.controller.state.calibrated:
            prediction = self.recognizer.add_sample(sample.features)
            if prediction is not None:
                label, confidence = prediction
                self.controller.handle_gesture(label)
                self.gesture_var.set(f"{label} ({confidence:.0%})")
        self.pointer_var.set("Pointer enabled" if self.controller.state.cursor_enabled else "Pointer paused")

    def _change_sensitivity(self, _value: str) -> None:
        self.controller.set_sensitivity(self.sensitivity.get())

    def _change_deadzone(self, _value: str) -> None:
        self.controller.set_deadzone(self.deadzone.get())

    def _toggle_pointer(self) -> None:
        enabled = self.controller.toggle_cursor()
        self.pointer_var.set("Pointer enabled" if enabled else "Pointer paused")

    def _recalibrate(self) -> None:
        self.controller.begin_calibration()
        self.calibration_var.set("Keep still while recalibrating")

    def close(self) -> None:
        self.stop_event.set()
        self.connected = False
        self.controller.disconnect()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="AirRing desktop companion")
    parser.parse_args()
    root = tk.Tk()
    AirRingApp(root)
    root.mainloop()
