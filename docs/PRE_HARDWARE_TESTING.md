# Testing AirRing Before Hardware Arrives

This checklist covers the work that can be completed without an ESP32 or MPU6050.

## 1. Prepare the Fedora development environment

Install the desktop packages:

```bash
sudo dnf install python3 python3-pip python3-tkinter git make pipx
```

Install PlatformIO in an isolated environment:

```bash
pipx install platformio
pipx ensurepath
pio --version
```

Enable Bluetooth for later hardware testing:

```bash
sudo systemctl enable --now bluetooth
bluetoothctl show
```

Clone the repository and prepare the desktop environment:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd AirRing/desktop
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
```

The AI extra installs PyTorch and is not required for the basic mouse controller. Add it
later when you have real sensor recordings and are ready to train gestures:

```bash
pip install -e "[ai]"
```

## 2. Run automated checks

From the repository root:

```bash
make test
make simulate
make firmware
```

`make firmware` compiles the production ESP32 firmware and does not require a board to
be connected. It downloads the PlatformIO platform and libraries on the first run.

The tests cover packet encoding and decoding, sensor status, calibration bias,
deadzone limits, pointer movement, button behaviour, gesture mappings, pointer pause,
disconnect recovery, BLE reconnection, dataset validation, Wokwi JSON structure and
sequence-counter wraparound.

The simulation uses a fake mouse backend. It exercises the desktop control pipeline
without moving the real pointer, connecting to BLE or requiring hardware.

## 3. Check the sensor circuit in Wokwi

1. Open the [Wokwi ESP32 project](https://wokwi.com/projects/new/esp32).
2. Copy `hardware/wokwi/sketch.ino` into the editor.
3. Replace the diagram with `hardware/wokwi/diagram.json`.
4. Add the libraries from `hardware/wokwi/libraries.txt`.
5. Start the simulation and open Serial Monitor at 115200 baud.
6. Change the MPU6050 acceleration and rotation properties.
7. Press `L` to simulate the index contact and `R` to simulate the middle contact.

Expected serial columns:

```text
timestamp,ax,ay,az,gx,gy,gz,left,right
```

Acceleration is printed in g, gyroscope readings in degrees per second, and contact
states as 0 or 1.

Wokwi validates the simulated sensor and contact-input sketch. It does not run the
production BLE firmware or connect the desktop app to a simulated BLE peripheral.

## 4. Check the ESP32 firmware build in GitHub Actions

Push the repository contents to GitHub. The `AirRing checks` workflow runs the desktop
tests and builds `firmware/airring` with PlatformIO. After a successful run, the workflow
also publishes an `airring-esp32-firmware` artifact containing `firmware.bin`.

A successful CI build proves that the firmware compiles against the configured
PlatformIO toolchain. It does not prove that the firmware works on a physical board.

## 5. Work that must wait for hardware

The following checks cannot be completed by desktop tests or Wokwi:

- Confirm the actual ESP32 board and USB serial port.
- Verify the physical MPU6050 I2C connection.
- Flash and boot the production firmware on the board.
- Connect to the real `AIRRING` BLE service from the desktop app.
- Confirm sensor axes and tune cursor sensitivity for the actual mounting position.
- Verify conductive contacts, sustained left-click/drag and right-click behaviour.
- Collect real gesture recordings and evaluate the trained LSTM model.

Do not create a gesture dataset from random or fabricated values. Gesture training should
use sensor recordings from the intended wearing position.
