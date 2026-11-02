#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <cstring>

namespace {
constexpr char DEVICE_NAME[] = "AIRRING";
constexpr char SERVICE_UUID[] = "a14d0001-7f5a-4d10-9a20-7b9c00000001";
constexpr char SENSOR_UUID[] = "a14d0002-7f5a-4d10-9a20-7b9c00000001";
constexpr uint8_t PIN_LEFT_CONTACT = 32;
constexpr uint8_t PIN_RIGHT_CONTACT = 33;
constexpr uint8_t CONTACT_LEFT = 0x01;
constexpr uint8_t CONTACT_RIGHT = 0x02;
constexpr uint8_t STATUS_SENSOR_READY = 0x01;
constexpr uint32_t SAMPLE_INTERVAL_US = 20000;
constexpr uint32_t IMU_RETRY_INTERVAL_MS = 2000;

struct __attribute__((packed)) SensorPacket {
  uint16_t sequence;
  int16_t axMg;
  int16_t ayMg;
  int16_t azMg;
  int16_t gxCentiDps;
  int16_t gyCentiDps;
  int16_t gzCentiDps;
  uint8_t contacts;
  uint8_t status;
};

static_assert(sizeof(SensorPacket) == 16, "SensorPacket must remain 16 bytes");

Adafruit_MPU6050 mpu;
BLECharacteristic *sensorCharacteristic = nullptr;
volatile bool clientConnected = false;
volatile bool sensorReady = false;
uint16_t sequenceNumber = 0;
uint32_t nextSampleAt = 0;
uint32_t lastImuAttemptAt = 0;

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
}

class ServerCallbacks final : public BLEServerCallbacks {
  void onConnect(BLEServer *) override {
    clientConnected = true;
  }

  void onDisconnect(BLEServer *server) override {
    clientConnected = false;
    server->startAdvertising();
  }
};

static int16_t clampInt16(float value) {
  if (value > 32767.0f) return 32767;
  if (value < -32768.0f) return -32768;
  return static_cast<int16_t>(lroundf(value));
}

static bool readContact(ContactState &contact, uint32_t now) {
  const bool reading = digitalRead(contact.pin) == LOW;
  if (reading != contact.raw) {
    contact.raw = reading;
    contact.changedAt = now;
  }
  if (now - contact.changedAt >= 20) contact.stable = contact.raw;
  return contact.stable;
}

static uint8_t readContacts(uint32_t now) {
  uint8_t state = 0;
  if (readContact(leftContact, now)) state |= CONTACT_LEFT;
  if (readContact(rightContact, now)) state |= CONTACT_RIGHT;
  return state;
}

static bool initializeImu() {
  if (!mpu.begin()) return false;
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_250_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  return true;
}

static void tryImuReinit(uint32_t now) {
  if (sensorReady || now - lastImuAttemptAt < IMU_RETRY_INTERVAL_MS) return;
  lastImuAttemptAt = now;
  for (uint8_t attempt = 0; attempt < 3; ++attempt) {
    sensorReady = initializeImu();
    if (sensorReady) break;
    delay(100);
  }
  Serial.println(sensorReady ? "MPU6050 ready" : "MPU6050 unavailable. Retrying");
}

static void initializeBle() {
  BLEDevice::init(DEVICE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService *service = server->createService(SERVICE_UUID);
  sensorCharacteristic = service->createCharacteristic(
      SENSOR_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  sensorCharacteristic->addDescriptor(new BLE2902());
  service->start();

  BLEAdvertising *advertising = server->getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LEFT_CONTACT, INPUT_PULLUP);
  pinMode(PIN_RIGHT_CONTACT, INPUT_PULLUP);
  Wire.begin(21, 22);

  lastImuAttemptAt = millis() - IMU_RETRY_INTERVAL_MS;
  tryImuReinit(millis());
  initializeBle();
  Serial.println(sensorReady
                     ? "AirRing ready. Connect to AIRRING over BLE."
                     : "AirRing advertising with MPU6050 unavailable. Check SDA, SCL, power and ground.");
}

void loop() {
  const uint32_t nowMs = millis();
  tryImuReinit(nowMs);
  const uint8_t contacts = readContacts(nowMs);

  const uint32_t now = micros();
  if (static_cast<int32_t>(now - nextSampleAt) < 0) return;
  nextSampleAt += SAMPLE_INTERVAL_US;
  if (static_cast<int32_t>(now - nextSampleAt) >= 0) {
    nextSampleAt = now + SAMPLE_INTERVAL_US;
  }

  SensorPacket packet{};
  packet.sequence = sequenceNumber++;
  packet.contacts = contacts;

  if (sensorReady) {
    sensors_event_t acceleration;
    sensors_event_t gyroscope;
    sensors_event_t temperature;
    mpu.getEvent(&acceleration, &gyroscope, &temperature);

    packet.axMg = clampInt16(acceleration.acceleration.x / 9.80665f * 1000.0f);
    packet.ayMg = clampInt16(acceleration.acceleration.y / 9.80665f * 1000.0f);
    packet.azMg = clampInt16(acceleration.acceleration.z / 9.80665f * 1000.0f);
    packet.gxCentiDps = clampInt16(gyroscope.gyro.x * 5729.57795f);
    packet.gyCentiDps = clampInt16(gyroscope.gyro.y * 5729.57795f);
    packet.gzCentiDps = clampInt16(gyroscope.gyro.z * 5729.57795f);
    packet.status |= STATUS_SENSOR_READY;
  }

  if (clientConnected && sensorCharacteristic != nullptr) {
    sensorCharacteristic->setValue(
        reinterpret_cast<uint8_t *>(&packet), sizeof(packet));
    sensorCharacteristic->notify();
  }

  if (packet.sequence % 50 == 0) {
    Serial.printf("seq=%u ax=%d ay=%d az=%d gx=%d gy=%d gz=%d buttons=%u status=%u\n",
                  packet.sequence, packet.axMg, packet.ayMg, packet.azMg,
                  packet.gxCentiDps, packet.gyCentiDps, packet.gzCentiDps,
                  packet.contacts, packet.status);
  }
}
