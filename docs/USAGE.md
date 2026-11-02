# Usage

1. Power the ESP32 and wait for BLE advertising.
2. Start `python -m airring` from the desktop environment.
3. The app connects to `AIRRING` automatically. Pair only if the operating system requests it.
4. Keep the device still during the two-second gyroscope calibration.
5. Confirm the status field says `Calibrated`. If it says `MPU6050 unavailable`, check wiring.
6. Move the wrist to move the pointer.
7. Touch thumb to index for left click. Keep contact for dragging.
8. Touch thumb to middle for right click.
9. Train and install an LSTM checkpoint to enable the additional gestures.

## Tuning pointer movement

Use the Sensitivity and Dead zone sliders in the desktop application. If one axis moves in the wrong direction, edit the axis or sign settings in `desktop/src/airring/config.py`, then restart the application.

If the pointer drifts while the hand is still, increase Dead zone slightly, then press Recalibrate and hold the device still until calibration completes.

Use the pointer button to pause and resume pointer movement. Contacts never produce clicks while pointer movement is paused.

## Desktop permissions

On macOS, grant Accessibility permission to the terminal or application running AirRing. On Linux, global pointer automation is most reliable under X11. Wayland compositors may restrict synthetic mouse events.
