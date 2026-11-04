# AirRing

AirRing is an open-source wearable air mouse. An ESP32 reads an MPU6050 and three conductive contacts, then streams sensor packets to a Python desktop app over Bluetooth Low Energy. Wrist rotation moves the pointer and finger contacts act as mouse buttons. An optional locally trained LSTM recognizes custom gestures.

No cloud service or external AI API is used. Mouse control works without a trained model.

## Features

- 50 Hz IMU streaming over BLE.
- Cursor control from gyroscope rotation.
- Thumb to index contact for left click and drag.
- Thumb to middle contact for right click.
- Runtime sensitivity and deadzone adjustment.
- Gyroscope bias calibration and automatic reconnection.
- Optional six-class LSTM gesture recognition with confidence thresholds and cooldown.
- Hardware-free desktop simulation and automated tests.

## Repository

```text
AirRing/
├── .github/workflows/         Python and firmware CI
├── desktop/
│   ├── src/airring/           Desktop application, protocol, controls and AI
│   ├── tests/                 Hardware-free automated tests
│   ├── tools/                 Gesture collection, training and simulation
│   ├── models/                Local checkpoints, ignored by Git
│   └── data/                  Local recordings, ignored by Git
├── docs/                      Setup, wiring, protocol, usage and training guides
├── firmware/airring/          PlatformIO ESP32 firmware
├── hardware/wokwi/            Simulated circuit and contact inputs
├── Makefile                   Local build and test shortcuts
└── LICENSE                    MIT
```

## Hardware

Required parts:

- ESP32 development board with BLE, such as ESP32 DevKit V1.
- MPU6050 breakout.
- Three conductive foil or metal contacts.
- Jumper wires.
- Wrist or finger strap.
- USB cable for flashing.
- Optional protected LiPo battery and 3.3 V regulator for portable use.

| MPU6050 | ESP32 |
|---|---|
| VIN | 3V3 |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

| Contact | ESP32 |
|---|---|
| Thumb | GND |
| Index | GPIO32 with internal pull-up |
| Middle | GPIO33 with internal pull-up |

GPIO32 and GPIO33 use the ESP32 internal pull-ups. AirRing does not require extra sensors.

## Quick start

Firmware:

```bash
cd firmware/airring
pio run
pio run -t upload
pio device monitor
```

Desktop, Python 3.10 or newer:

```bash
cd desktop
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m airring
```

See [docs/SETUP.md](docs/SETUP.md) for Fedora and Linux setup, BLE pairing and platform notes. See [docs/ASSEMBLY.md](docs/ASSEMBLY.md) for wiring details.

## Controls

| Input | Action |
|---|---|
| Wrist rotation | Move pointer |
| Thumb to index | Left click |
| Keep thumb on index | Drag |
| Thumb to middle | Right click |
| Swipe left | Previous item or slide |
| Swipe right | Next item or slide |
| Clockwise circle | Scroll up |
| Counterclockwise circle | Scroll down |
| Double flick | Pause or resume pointer |

The discrete gestures require a trained model. See [docs/GESTURE_TRAINING.md](docs/GESTURE_TRAINING.md).

## Tests and simulation

From the repository root:

```bash
make test
make simulate
make firmware
```

`make test` runs pytest and compiles Python sources. `make simulate` exercises the desktop controller with a fake mouse backend and no BLE device. Wokwi simulates MPU6050 readings and contact buttons only. It does not simulate the BLE connection to the desktop app. See [docs/PRE_HARDWARE_TESTING.md](docs/PRE_HARDWARE_TESTING.md) for the full hardware-free checklist and [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common failures.

## License

MIT. See [LICENSE](LICENSE).
