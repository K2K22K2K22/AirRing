import test from "node:test";
import assert from "node:assert/strict";
import { decodeSensorPacket, sequenceGap, PACKET_SIZE } from "../src/protocol.js";

function packet({ sequence = 7, acceleration = [0, 0, 1000], gyro = [100, -250, 350], contacts = 3, status = 1 } = {}) {
  const buffer = new ArrayBuffer(PACKET_SIZE);
  const view = new DataView(buffer);
  view.setUint16(0, sequence, true);
  acceleration.forEach((value, index) => view.setInt16(2 + index * 2, value, true));
  gyro.forEach((value, index) => view.setInt16(8 + index * 2, value, true));
  view.setUint8(14, contacts);
  view.setUint8(15, status);
  return view;
}

test("decodes the fixed 16-byte AirRing packet", () => {
  const sample = decodeSensorPacket(packet());
  assert.equal(sample.sequence, 7);
  assert.deepEqual(sample.accelerationG, [0, 0, 1]);
  assert.deepEqual(sample.gyroscopeDps, [1, -2.5, 3.5]);
  assert.equal(sample.indexContact, true);
  assert.equal(sample.middleContact, true);
  assert.equal(sample.sensorReady, true);
});

test("marks a failed sensor sample as not ready", () => {
  const sample = decodeSensorPacket(packet({ status: 0, contacts: 0 }));
  assert.equal(sample.sensorReady, false);
  assert.equal(sample.indexContact, false);
  assert.equal(sample.middleContact, false);
});

test("rejects packet sizes that do not match the firmware contract", () => {
  assert.throws(() => decodeSensorPacket(new DataView(new ArrayBuffer(15))), /Expected 16 bytes/);
});

test("counts sequence gaps and handles uint16 wraparound", () => {
  assert.equal(sequenceGap(10, 11), 0);
  assert.equal(sequenceGap(10, 14), 3);
  assert.equal(sequenceGap(65535, 0), 0);
});
