# Troubleshooting

## Device not found

- Confirm the ESP32 is powered and the serial monitor reports `AirRing ready` or `AirRing advertising with MPU6050 unavailable`.
- Check that Bluetooth is enabled on the computer.
- Keep the device close during the first connection.
- Confirm the firmware advertises `AIRRING`. Another nearby device with the same name can be selected by mistake.
- Restart the desktop app to repeat discovery. It retries automatically while running.

## MPU6050 unavailable

- Verify VIN, GND, SDA and SCL against [ASSEMBLY.md](ASSEMBLY.md).
- Confirm SDA is GPIO21 and SCL is GPIO22.
- Use short wires and a stable 3.3 V supply.
- Check the serial monitor for retry messages. The firmware retries every two seconds.
- The desktop status field reports `MPU6050 unavailable. Check wiring.` and blocks pointer control until valid samples return.

## Pointer drifts

- Hold the device still and press Recalibrate.
- Increase Dead zone gradually. A small value removes slow drift; a large value reduces responsiveness.
- Reduce Sensitivity if small motions jump across the screen.
- Secure the MPU6050 so it cannot move independently of the hand.
- Change the gyro axis or sign settings in `desktop/src/airring/config.py` if the wrong axis moves the pointer.

## Clicks do not work

- Confirm the thumb contact is connected to GND and the index or middle contact to GPIO32 or GPIO33.
- Check that the index contact holds the left button and that the middle contact produces a single right click.
- Recalibrate after changing contacts. The controller ignores contacts while uncalibrated.
- Check that pointer control is not paused. The pointer button toggles pause and resume.
- Verify that the desktop session allows synthetic input. Wayland and restricted accessibility settings can block pointer events.

## Gesture model unavailable

- The model is optional. Basic mouse control must work before training gestures.
- Install the AI extra with `pip install -e ".[ai]"` from `desktop`.
- Train a checkpoint from real recordings with the tools in [GESTURE_TRAINING.md](GESTURE_TRAINING.md).
- If the app reports an invalid checkpoint, retrain with the current training tool. The checkpoint metadata must match the six AirRing classes and the configured window size.
- No pretrained model is shipped with the repository.

## Build or test failures

- Run `make test` and `make firmware` from the repository root.
- Use Python 3.10 or newer.
- Install desktop test dependencies with `pip install -e "./desktop[dev]"`.
- Install PlatformIO with `pipx install platformio`.
- Remove stale `desktop/build` directories before reinstalling the desktop package.
- GitHub Actions runs the same Python checks, simulation and firmware build on every push and pull request.

## Wokwi limitations

Wokwi simulates MPU6050 values and contact buttons. It does not run the production BLE firmware or connect to the desktop app. Physical BLE behavior, real contact hardware and actual cursor feel require the ESP32 and sensor.
