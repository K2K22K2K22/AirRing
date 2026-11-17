import { SERVICE_UUID, SENSOR_UUID, SAMPLE_RATE_HZ, DEVICE_NAME } from "./protocol.js";
import { validateCursorMapping } from "./calibration.js";

export const PROFILE_SCHEMA = "airring-calibration-profile";
export const PROFILE_VERSION = 1;

export function createProfile({ calibration, cursor }) {
  if (!calibration || !calibration.stable || calibration.count < 100) {
    throw new Error("A stable 100-sample stationary calibration is required before exporting a profile");
  }

  const mapping = validateCursorMapping(cursor);
  return {
    schema: PROFILE_SCHEMA,
    schemaVersion: PROFILE_VERSION,
    device: {
      name: DEVICE_NAME,
      serviceUuid: SERVICE_UUID,
      sensorCharacteristicUuid: SENSOR_UUID,
      packetBytes: 16,
    },
    sampleRateHz: SAMPLE_RATE_HZ,
    cursor: {
      xGyroAxis: mapping.xGyroAxis,
      yGyroAxis: mapping.yGyroAxis,
      xSign: mapping.xSign,
      ySign: mapping.ySign,
      sensitivity: mapping.sensitivity,
      deadzoneDps: mapping.deadzoneDps,
    },
    sensorCalibration: {
      gyroBiasDps: calibration.biasDps.map(value => Number(value.toFixed(5))),
      gyroStdDevDps: calibration.stddevDps.map(value => Number(value.toFixed(5))),
      stationarySamples: calibration.count,
      capturedAt: new Date().toISOString(),
    },
    notes: "The desktop app takes a fresh gyro bias when it connects. This saved bias is retained as a calibration record.",
  };
}

export function validateProfile(profile) {
  if (!profile || typeof profile !== "object") throw new TypeError("Profile must be a JSON object");
  if (profile.schema !== PROFILE_SCHEMA || profile.schemaVersion !== PROFILE_VERSION) {
    throw new Error("This file is not a supported AirRing calibration profile");
  }
  if (profile.device?.serviceUuid !== SERVICE_UUID || profile.device?.sensorCharacteristicUuid !== SENSOR_UUID) {
    throw new Error("This profile uses a different BLE device protocol");
  }
  if (profile.device?.packetBytes !== 16 || profile.sampleRateHz !== SAMPLE_RATE_HZ) {
    throw new Error("The profile does not match the current AirRing sensor packet format");
  }
  const cursor = validateCursorMapping(profile.cursor ?? {});
  const bias = profile.sensorCalibration?.gyroBiasDps;
  const deviation = profile.sensorCalibration?.gyroStdDevDps;
  const count = profile.sensorCalibration?.stationarySamples;
  if (!Array.isArray(bias) || bias.length !== 3 || !bias.every(Number.isFinite)) {
    throw new Error("The profile is missing its three-axis gyro bias record");
  }
  if (!Array.isArray(deviation) || deviation.length !== 3 || !deviation.every(Number.isFinite)) {
    throw new Error("The profile is missing its three-axis stability record");
  }
  if (!Number.isInteger(count) || count < 100) {
    throw new Error("The profile does not contain a complete stationary calibration");
  }
  if (deviation.some(value => value < 0 || value > 2.8)) {
    throw new Error("The profile failed the stationary stability check");
  }
  return { ...profile, cursor };
}

export function downloadProfile(profile) {
  const blob = new Blob([`${JSON.stringify(profile, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "airring-profile.json";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
