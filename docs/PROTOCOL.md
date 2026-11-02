# BLE Sensor Protocol

AirRing sends one fixed-length sensor packet through BLE notifications at 50 Hz.
The payload is 16 bytes and uses little-endian integer fields.

| Offset | Size | Field | Unit / meaning |
|---:|---:|---|---|
| 0 | 2 | Sequence | Unsigned 16-bit sample counter |
| 2 | 2 | Acceleration X | Signed milligravity (mg) |
| 4 | 2 | Acceleration Y | Signed milligravity (mg) |
| 6 | 2 | Acceleration Z | Signed milligravity (mg) |
| 8 | 2 | Gyroscope X | Signed centidegrees per second |
| 10 | 2 | Gyroscope Y | Signed centidegrees per second |
| 12 | 2 | Gyroscope Z | Signed centidegrees per second |
| 14 | 1 | Contacts | Bit 0: index contact, bit 1: middle contact |
| 15 | 1 | Status | Bit 0: MPU6050 data is valid |

The gyroscope values are converted from the MPU6050 library's radians-per-second
values into centidegrees per second. The configured gyro range is 250 degrees per
second. Contact bits are active high in the packet: a set bit means the corresponding
GPIO input is being pulled low by a contact.

If MPU6050 initialization fails, advertising continues, motion fields stay zero and
the status bit remains clear. The firmware retries initialization every two seconds.
The desktop client ignores motion and calibration samples until the status bit is set.

## BLE identifiers

- Device name: `AIRRING`
- Service UUID: `a14d0001-7f5a-4d10-9a20-7b9c00000001`
- Sensor characteristic UUID: `a14d0002-7f5a-4d10-9a20-7b9c00000001`

The packet definition must remain synchronized between `firmware/airring/src/main.cpp`
and `desktop/src/airring/packet.py`. The firmware includes a compile-time size check.
