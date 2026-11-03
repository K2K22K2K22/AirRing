#include <Arduino.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

namespace {
constexpr char DEVICE_NAME[] = "AIRRING";
constexpr char SERVICE_UUID[] = "a14d0001-7f5a-4d10-9a20-7b9c00000001";
constexpr char SENSOR_UUID[] = "a14d0002-7f5a-4d10-9a20-7b9c00000001";
constexpr uint8_t PIN_LEFT_CONTACT = 32;
constexpr uint8_t PIN_RIGHT_CONTACT = 33;
constexpr uint8_t MPU_ADDRESS = 0x68;
constexpr uint8_t MPU_REG_WHO_AM_I = 0x75;
constexpr uint8_t MPU_REG_CONFIG = 0x1A;
constexpr uint8_t MPU_REG_GYRO_CONFIG = 0x1B;
constexpr uint8_t MPU_REG_ACCEL_CONFIG = 0x1C;
constexpr uint8_t MPU_REG_DATA = 0x3B;
constexpr uint8_t MPU_REG_PWR_MGMT_1 = 0x6B;
constexpr uint8_t MPU_WHO_AM_I_VALUE = 0x68;
constexpr uint8_t MPU_ACCEL_RANGE_8G = 0x02;
constexpr uint8_t MPU_GYRO_RANGE_250 = 0x00;
constexpr uint8_t MPU_DLPF_21_HZ = 0x04;
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

BLECharacteristic *sensorCharacteristic = nullptr;
bool sensorReady = false;
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
  void onDisconnect(BLEServer *server) override {
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

static bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

static bool readRegisters(uint8_t reg, uint8_t count, uint8_t *buffer) {
  Wire.beginTransmission(MPU_ADDRESS);
  Wire.write(reg);
  if (Wire.endTransmission() != 0) return false;
  if (Wire.requestFrom(MPU_ADDRESS, count) != count) return false;
  for (uint8_t i = 0; i < count; ++i) buffer[i] = Wire.read();
  return true;
}

static bool initializeImu() {
  uint8_t whoAmI = 0;
  if (!readRegisters(MPU_REG_WHO_AM_I, 1, &whoAmI)) return false;
  if (whoAmI != MPU_WHO_AM_I_VALUE) return false;

  if (!writeRegister(MPU_REG_PWR_MGMT_1, 0x01)) return false;
  if (!writeRegister(MPU_REG_CONFIG, MPU_DLPF_21_HZ)) return false;
  if (!writeRegister(MPU_REG_ACCEL_CONFIG, MPU_ACCEL_RANGE_8G << 3)) return false;
  if (!writeRegister(MPU_REG_GYRO_CONFIG, MPU_GYRO_RANGE_250 << 3)) return false;

  uint8_t config[2] = {0, 0};
  if (!readRegisters(MPU_REG_ACCEL_CONFIG, 1, &config[0])) return false;
  if (!readRegisters(MPU_REG_GYRO_CONFIG, 1, &config[1])) return false;
  if ((config[0] & 0x18) != (MPU_ACCEL_RANGE_8G << 3)) return false;
  if ((config[1] & 0x18) != (MPU_GYRO_RANGE_250 << 3)) return false;
  return true;
}

static void tryImuReinit(uint32_t now) {
  if (sensorReady || now - lastImuAttemptAt < IMU_RETRY_INTERVAL_MS) return;
  lastImuAttemptAt = now;
  sensorReady = initializeImu();
  Serial.println(sensorReady ? "MPU6050 ready" : "MPU6050 unavailable. Retrying");
}

static bool readMotion(SensorPacket &packet) {
  uint8_t buffer[14] = {0};
  if (!readRegisters(MPU_REG_DATA, sizeof(buffer), buffer)) return false;

  const int16_t ax = static_cast<int16_t>(buffer[0] << 8 | buffer[1]);
  const int16_t ay = static_cast<int16_t>(buffer[2] << 8 | buffer[3]);
  const int16_t az = static_cast<int16_t>(buffer[4] << 8 | buffer[5]);
  const int16_t gx = static_cast<int16_t>(buffer[8] << 8 | buffer[9]);
  const int16_t gy = static_cast<int16_t>(buffer[10] << 8 | buffer[11]);
  const int16_t gz = static_cast<int16_t>(buffer[12] << 8 | buffer[13]);

  packet.axMg = clampInt16(ax / 4096.0f * 1000.0f);
  packet.ayMg = clampInt16(ay / 4096.0f * 1000.0f);
  packet.azMg = clampInt16(az / 4096.0f * 1000.0f);
  packet.gxCentiDps = clampInt16(gx / 131.0f * 100.0f);
  packet.gyCentiDps = clampInt16(gy / 131.0f * 100.0f);
  packet.gzCentiDps = clampInt16(gz / 131.0f * 100.0f);
  return true;
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
    if (readMotion(packet)) {
      packet.status |= STATUS_SENSOR_READY;
    } else {
      sensorReady = false;
      lastImuAttemptAt = nowMs;
    }
  }

  if (sensorCharacteristic != nullptr) {
    sensorCharacteristic->setValue(
        reinterpret_cast<uint8_t *>(&packet), sizeof(packet));
    sensorCharacteristic->notify();
  }

  if (packet.sequence % 50 == 0) {
    Serial.printf("seq=%u ax=%d ay=%d az=%d gx=%d gy=%d gz=%d buttons=%u status=%u\n",
                  static_cast<unsigned>(packet.sequence), packet.axMg, packet.ayMg,
                  packet.azMg, packet.gxCentiDps, packet.gyCentiDps,
                  packet.gzCentiDps, static_cast<unsigned>(packet.contacts),
                  static_cast<unsigned>(packet.status));
  }
}
