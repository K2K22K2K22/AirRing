#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

constexpr uint8_t PIN_LEFT_CONTACT = 32;
constexpr uint8_t PIN_RIGHT_CONTACT = 33;
Adafruit_MPU6050 mpu;
uint32_t lastSample = 0;

struct ContactState {
  uint8_t pin;
  bool raw;
  bool stable;
  uint32_t changedAt;

  explicit ContactState(uint8_t inputPin)
      : pin(inputPin), raw(false), stable(false), changedAt(0) {}
};

ContactState leftContact(PIN_LEFT_CONTACT);
ContactState rightContact(PIN_RIGHT_CONTACT);

bool readContact(ContactState &contact, uint32_t now) {
  const bool reading = digitalRead(contact.pin) == LOW;
  if (reading != contact.raw) {
    contact.raw = reading;
    contact.changedAt = now;
  }
  if (now - contact.changedAt >= 20) contact.stable = contact.raw;
  return contact.stable;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LEFT_CONTACT, INPUT_PULLUP);
  pinMode(PIN_RIGHT_CONTACT, INPUT_PULLUP);
  Wire.begin(21, 22);

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found");
    while (true) delay(1000);
  }

  mpu.setGyroRange(MPU6050_RANGE_250_DEG);
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  Serial.println("timestamp,ax,ay,az,gx,gy,gz,left,right");
}

void loop() {
  if (millis() - lastSample < 20) return;
  lastSample = millis();

  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);
  Serial.printf("%lu,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d\n",
      static_cast<unsigned long>(lastSample),
      a.acceleration.x / 9.80665f,
      a.acceleration.y / 9.80665f,
      a.acceleration.z / 9.80665f,
      g.gyro.x * 57.29578f,
      g.gyro.y * 57.29578f,
      g.gyro.z * 57.29578f,
      readContact(leftContact, lastSample),
      readContact(rightContact, lastSample));
}
