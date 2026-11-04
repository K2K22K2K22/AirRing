# Wokwi Sensor Test

This circuit checks MPU6050 sampling and the two contact inputs. The pushbuttons represent the foil contacts.

1. Open a new [Wokwi ESP32 project](https://wokwi.com/projects/new/esp32).
2. Replace `sketch.ino` and `diagram.json` with the files in this folder.
3. Add the libraries listed in `libraries.txt`.
4. Start the simulation and open Serial Monitor at 115200 baud.
5. Change the MPU6050 acceleration and rotation controls. Press `L` for left contact and `R` for right contact.

The output is CSV. BLE is not emulated in this circuit. Use the physical firmware for the BLE connection test.
