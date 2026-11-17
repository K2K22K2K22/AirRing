import { DEVICE_NAME, SERVICE_UUID, SENSOR_UUID, decodeSensorPacket } from "./protocol.js";

export class AirRingBle {
  constructor(onSample, onStatus) {
    this.onSample = onSample;
    this.onStatus = onStatus;
    this.device = null;
    this.server = null;
    this.characteristic = null;
    this.connected = false;
    this.handleNotification = this.handleNotification.bind(this);
    this.handleDisconnect = this.handleDisconnect.bind(this);
  }

  static isSupported() {
    return Boolean(window.isSecureContext && navigator.bluetooth?.requestDevice);
  }

  async connect() {
    if (!AirRingBle.isSupported()) {
      throw new Error("Web Bluetooth is unavailable here. Open this page in Chrome or Edge over HTTPS, or use the desktop app.");
    }

    this.onStatus("Choose AIRRING in the browser dialog");
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: DEVICE_NAME }],
      optionalServices: [SERVICE_UUID],
    });
    this.device = device;
    this.device.addEventListener("gattserverdisconnected", this.handleDisconnect);

    this.onStatus(`Connecting to ${device.name || DEVICE_NAME}`);
    this.server = await device.gatt.connect();
    const service = await this.server.getPrimaryService(SERVICE_UUID);
    this.characteristic = await service.getCharacteristic(SENSOR_UUID);
    this.characteristic.addEventListener("characteristicvaluechanged", this.handleNotification);
    await this.characteristic.startNotifications();
    this.connected = true;
    this.onStatus(`Connected to ${device.name || DEVICE_NAME}`);
    return device.name || DEVICE_NAME;
  }

  handleNotification(event) {
    try {
      const sample = decodeSensorPacket(event.target.value);
      this.onSample(sample);
    } catch (error) {
      this.onStatus(`Packet error: ${error.message}`);
    }
  }

  handleDisconnect() {
    this.connected = false;
    this.characteristic?.removeEventListener("characteristicvaluechanged", this.handleNotification);
    this.characteristic = null;
    this.server = null;
    this.onStatus("Device disconnected");
  }

  disconnect() {
    if (this.characteristic) {
      this.characteristic.removeEventListener("characteristicvaluechanged", this.handleNotification);
    }
    if (this.device?.gatt?.connected) this.device.gatt.disconnect();
    this.connected = false;
    this.characteristic = null;
    this.server = null;
    this.device = null;
    this.onStatus("Disconnected");
  }
}
