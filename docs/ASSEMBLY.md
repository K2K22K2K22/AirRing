# Assembly

## MPU6050

| MPU6050 | ESP32 |
|---|---|
| VIN | 3V3 |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

Use short I2C wires. Secure the MPU6050 so it does not move independently of the hand strap.

## Conductive contacts

Use three small conductive foil or metal contacts.

- Thumb contact: GND
- Index contact: GPIO32
- Middle-finger contact: GPIO33

The firmware configures GPIO32 and GPIO33 as `INPUT_PULLUP`. Touching the thumb contact to the index contact pulls GPIO32 low and holds the left mouse button. Touching the thumb contact to the middle contact pulls GPIO33 low and triggers a right click.

Keep the contacts electrically isolated from the battery and USB power wiring. They connect only to the ESP32 ground and GPIO inputs.

## Wearable mounting

For the first prototype, attach the ESP32 and MPU6050 to a small wrist or finger strap. Run flexible wires to the three contact pads. A compact enclosure can be made after cursor mapping and contact placement are comfortable.

USB power is recommended during development. For portable use, add a protected LiPo battery and a suitable 3.3 V regulator or a development board designed for battery input. Do not connect a bare LiPo cell to the board's 5 V pin.
