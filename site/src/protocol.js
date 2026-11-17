export const DEVICE_NAME = "AIRRING";
export const SERVICE_UUID = "a14d0001-7f5a-4d10-9a20-7b9c00000001";
export const SENSOR_UUID = "a14d0002-7f5a-4d10-9a20-7b9c00000001";
export const PACKET_SIZE = 16;
export const SAMPLE_RATE_HZ = 50;
export const CONTACT_INDEX = 0x01;
export const CONTACT_MIDDLE = 0x02;
export const STATUS_SENSOR_READY = 0x01;

export function decodeSensorPacket(input) {
  const view = input instanceof DataView
    ? input
    : new DataView(input.buffer ?? input, input.byteOffset ?? 0, input.byteLength);

  if (view.byteLength !== PACKET_SIZE) {
    throw new RangeError(`Expected ${PACKET_SIZE} bytes, received ${view.byteLength}`);
  }

  const sequence = view.getUint16(0, true);
  const accelerationMg = [
    view.getInt16(2, true),
    view.getInt16(4, true),
    view.getInt16(6, true),
  ];
  const gyroscopeCentiDps = [
    view.getInt16(8, true),
    view.getInt16(10, true),
    view.getInt16(12, true),
  ];
  const contacts = view.getUint8(14);
  const status = view.getUint8(15);

  return {
    sequence,
    accelerationMg,
    accelerationG: accelerationMg.map(value => value / 1000),
    gyroscopeCentiDps,
    gyroscopeDps: gyroscopeCentiDps.map(value => value / 100),
    contacts,
    indexContact: Boolean(contacts & CONTACT_INDEX),
    middleContact: Boolean(contacts & CONTACT_MIDDLE),
    sensorReady: Boolean(status & STATUS_SENSOR_READY),
    status,
    receivedAt: performance.now(),
  };
}

export function sequenceGap(previous, current) {
  if (previous === null || previous === undefined) return 0;
  const delta = (current - previous + 65536) & 0xffff;
  return Math.max(0, delta - 1);
}
