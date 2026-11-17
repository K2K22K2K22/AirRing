import test from "node:test";
import assert from "node:assert/strict";
import { summarizeGyro, detectDominantAxis, applyDeadzone, validateCursorMapping } from "../src/calibration.js";
import { createProfile, validateProfile } from "../src/profile.js";

const samples = (values, count = 100) => Array.from({ length: count }, (_, index) => ({
  gyroscopeDps: values.map((value, axis) => value + Math.sin(index * .37 + axis) * .05),
}));

test("calculates stationary gyro bias and stability", () => {
  const result = summarizeGyro(samples([1.2, -2.4, .8]));
  assert.equal(result.count, 100);
  assert.equal(result.stable, true);
  assert.ok(Math.abs(result.biasDps[0] - 1.2) < .01);
  assert.ok(result.stddevDps.every(value => value < .1));
});

test("rejects a moving sensor during stationary calibration", () => {
  const moving = Array.from({ length: 100 }, (_, index) => ({ gyroscopeDps: [Math.sin(index) * 8, 0, 0] }));
  assert.equal(summarizeGyro(moving).stable, false);
});

test("detects the strongest available orientation axis and sign", () => {
  const motion = samples([2, -32, 6], 80);
  const result = detectDominantAxis(motion, [0, 0, 0]);
  assert.equal(result.detected, true);
  assert.equal(result.axis, 1);
  assert.equal(result.sign, -1);
  const vertical = detectDominantAxis(samples([28, 2, -3], 80), [0, 0, 0], 1);
  assert.equal(vertical.axis, 0);
});

test("returns an undetected result for a movement below the threshold", () => {
  const result = detectDominantAxis(samples([1, 2, 3], 80), [0, 0, 0]);
  assert.equal(result.detected, false);
});

test("applies a dead zone without changing sign", () => {
  assert.equal(applyDeadzone(4, 5), 0);
  assert.equal(applyDeadzone(8, 5), 3);
  assert.equal(applyDeadzone(-8, 5), -3);
});

test("validates a unique horizontal and vertical axis", () => {
  assert.deepEqual(validateCursorMapping({ xGyroAxis: 2, yGyroAxis: 0, xSign: 1, ySign: -1, sensitivity: 2.8, deadzoneDps: 5 }).xGyroAxis, 2);
  assert.throws(() => validateCursorMapping({ xGyroAxis: 2, yGyroAxis: 2, xSign: 1, ySign: 1, sensitivity: 2, deadzoneDps: 5 }), /different gyro axes/);
});

test("creates and validates a complete AirRing profile", () => {
  const calibration = summarizeGyro(samples([.2, -.4, 1.1]));
  const profile = createProfile({
    calibration,
    cursor: { xGyroAxis: 2, yGyroAxis: 0, xSign: 1, ySign: -1, sensitivity: 2.8, deadzoneDps: 5 },
  });
  const checked = validateProfile(profile);
  assert.equal(checked.device.packetBytes, 16);
  assert.equal(checked.cursor.xGyroAxis, 2);
  assert.equal(checked.sensorCalibration.stationarySamples, 100);
});

test("rejects profiles for a different BLE protocol", () => {
  const calibration = summarizeGyro(samples([0, 0, 0]));
  const profile = createProfile({
    calibration,
    cursor: { xGyroAxis: 2, yGyroAxis: 0, xSign: 1, ySign: -1, sensitivity: 2.8, deadzoneDps: 5 },
  });
  profile.device.sensorCharacteristicUuid = "00000000-0000-0000-0000-000000000000";
  assert.throws(() => validateProfile(profile), /different BLE device protocol/);
});
