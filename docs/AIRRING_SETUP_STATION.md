# AirRing Setup Station

The AirRing Setup Station is a static companion for assembling, connecting, checking and calibrating an AirRing wearable air mouse.

## What it does

- Guides the hardware build from parts selection through final desktop setup.
- Connects directly to the ESP32 over Bluetooth Low Energy in browsers that support Web Bluetooth.
- Decodes the current 16-byte AirRing sensor packet.
- Displays acceleration, gyroscope, contact inputs, sequence numbers, sensor state and the measured notification rate.
- Captures a 100-sample stationary gyro calibration and checks sample stability.
- Detects horizontal and vertical gyro axes from guided wrist movements.
- Previews pointer movement inside the page and lets the user tune sensitivity and dead zone.
- Exports a validated `airring-profile.json` file.
- Includes a Python utility that applies the cursor settings to the desktop app configuration.

The page cannot move the operating-system pointer. System-wide pointer control remains in the Python desktop application.

## Run locally

From the `site` directory:

```bash
python3 -m http.server 4173
```

Open `http://localhost:4173` in Chrome or Edge. Localhost is treated as a secure context by supporting browsers. The browser asks for Bluetooth permission only after the Connect button is pressed.

The page is static and has no build step. Its JavaScript modules run in the browser. It does not need a server, account, database, telemetry endpoint or external API.

## Publish on GitHub Pages

Pages must be enabled before the workflow can publish. The default `GITHUB_TOKEN` cannot enable it, so do this once in repository settings:

1. Open repository Settings, then Pages.
2. Set **Build and deployment > Source** to **GitHub Actions**.

Then push the `site` directory and `.github/workflows/deploy-pages.yml` to `main`. The **Deploy AirRing Setup** run publishes `site/` and leaves the desktop and firmware checks workflow alone. Once it finishes, the site is at `https://k2k22k2k22.github.io/AirRing/`.

## Browser requirements

Web Bluetooth requires a secure context and explicit user permission. Use a current Chrome or Edge browser on a computer with Bluetooth LE support. Firefox and Safari do not currently expose the Web Bluetooth flow used by this page. On unsupported browsers, use the Python desktop app for the BLE connection.

## Profile format

The JSON profile includes:

- AirRing service and characteristic UUIDs.
- Packet size and sample rate.
- Horizontal and vertical gyro axis selection.
- Axis direction signs.
- Pointer sensitivity and dead zone.
- The measured three-axis stationary gyro bias and standard deviation.

The desktop importer applies axis selection, direction, sensitivity and dead zone to `desktop/src/airring/config.py`. The desktop app takes a fresh gyro bias when it connects. The bias captured in the browser is retained in the profile as a diagnostic record and is not forced into a later session.

From the repository root:

```bash
python desktop/tools/apply_calibration_profile.py airring-profile.json --dry-run
python desktop/tools/apply_calibration_profile.py airring-profile.json
```

The importer validates the profile against the AirRing UUIDs and packet format. It creates `config.py.bak` before writing. It does not change firmware or BLE protocol files.

To restore the original settings:

```bash
cp desktop/src/airring/config.py.bak desktop/src/airring/config.py
```

## Tests

From the `site` directory:

```bash
npm test
```

The tests use Node's built-in test runner and have no third-party dependencies. They cover packet decoding, sequence wraparound, stationary stability, axis detection, dead zone handling and profile validation.

Python importer tests are in `desktop/tests/test_setup_profile_import.py` and run with the repository test command:

```bash
make test
```

## Hardware limitations

A successful website connection and calibration do not prove the wearable is assembled correctly for every use. Physical wiring, contact pressure, mounting position, battery safety and real pointer feel still need to be checked with the actual board and sensor.
