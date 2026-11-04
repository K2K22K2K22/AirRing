# Setup

## Fedora and Linux

Install build and Bluetooth tools:

```bash
sudo dnf install python3 python3-pip python3-tkinter git make bluez bluez-tools
sudo systemctl enable --now bluetooth
bluetoothctl show
```

On Debian or Ubuntu:

```bash
sudo apt install python3 python3-pip python3-tkinter git make bluetooth bluez
sudo systemctl enable --now bluetooth
```

Install PlatformIO with pipx:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install platformio
pio --version
```

If the ESP32 USB port is not accessible to your user, add a udev rule for the board's USB vendor ID, reload udev, then unplug and reconnect the board. Do not flash with `sudo` as the default workflow.

## Python desktop app

Use Python 3.10 or newer.

```bash
cd desktop
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m airring
```

Optional gesture training and recognition:

```bash
python -m pip install -e ".[ai]"
```

Automated tests only:

```bash
python -m pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Firmware

Connect the ESP32 by USB, then run:

```bash
cd firmware/airring
pio run
pio run -t upload
pio device monitor
```

The serial monitor runs at 115200 baud. The firmware advertises as `AIRRING`. It starts BLE even if MPU6050 initialization fails, sends zero motion values and clears the sensor-ready status bit while it retries initialization every two seconds.

## BLE connection

1. Power the ESP32 and confirm `AIRRING` is advertised.
2. Start `python -m airring`.
3. Keep the computer Bluetooth enabled and the device nearby.
4. The app scans for names starting with `AIRRING` and connects automatically.
5. OS pairing is usually not required for BLE GATT notifications. If the OS asks, pair with the device and accept the request.
6. The app reconnects automatically if the link drops.

The service and characteristic UUIDs are listed in [PROTOCOL.md](PROTOCOL.md).

## Cursor calibration

1. Keep the device still when the app reports calibration. The default window is two seconds at 50 Hz.
2. Watch the status field. It reports `Calibrated`, the sample count, or an MPU6050 wiring error.
3. Adjust Sensitivity for comfortable pointer speed.
4. Increase Dead zone if the pointer drifts while the hand is still.
5. Press Recalibrate after changing the mounting position.
6. If an axis moves in the wrong direction, change `CURSOR_X_SIGN` or `CURSOR_Y_SIGN` in `desktop/src/airring/config.py`.
7. If the wrong axis moves the pointer, change `CURSOR_X_GYRO_AXIS` or `CURSOR_Y_GYRO_AXIS` in the same file.

Pointer automation requires desktop input permission. X11 is the most reliable Linux session type. Wayland compositors may block synthetic pointer events. On macOS, grant Accessibility permission to the terminal or app running AirRing.
