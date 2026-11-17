export const STATIONARY_SAMPLE_TARGET = 100;
export const MOTION_SAMPLE_TARGET = 80;
export const STATIONARY_STDDEV_LIMIT_DPS = 2.8;
export const ORIENTATION_MIN_RATE_DPS = 6;

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values, average) {
  const variance = values.reduce((sum, value) => sum + ((value - average) ** 2), 0) / values.length;
  return Math.sqrt(variance);
}

export function summarizeGyro(samples) {
  if (!Array.isArray(samples) || samples.length === 0) {
    throw new TypeError("At least one valid sample is required");
  }

  const axes = [0, 1, 2].map(axis => samples.map(sample => sample.gyroscopeDps[axis]));
  const biasDps = axes.map(values => mean(values));
  const stddevDps = axes.map((values, index) => standardDeviation(values, biasDps[index]));
  const stable = stddevDps.every(value => Number.isFinite(value) && value <= STATIONARY_STDDEV_LIMIT_DPS);

  return { count: samples.length, biasDps, stddevDps, stable };
}

export function detectDominantAxis(samples, biasDps, excludedAxis = -1) {
  if (!Array.isArray(samples) || samples.length < 10) {
    throw new TypeError("Not enough motion samples to detect an axis");
  }

  const averages = [0, 1, 2].map(axis => {
    const corrected = samples.map(sample => sample.gyroscopeDps[axis] - biasDps[axis]);
    return mean(corrected);
  });
  const candidates = averages
    .map((value, axis) => ({ axis, value, magnitude: Math.abs(value) }))
    .filter(candidate => candidate.axis !== excludedAxis)
    .sort((left, right) => right.magnitude - left.magnitude);

  const best = candidates[0];
  if (!best || best.magnitude < ORIENTATION_MIN_RATE_DPS) {
    return { detected: false, averages, axis: null, sign: null, magnitude: best?.magnitude ?? 0 };
  }

  return {
    detected: true,
    averages,
    axis: best.axis,
    sign: best.value >= 0 ? 1 : -1,
    magnitude: best.magnitude,
  };
}

export function applyDeadzone(value, deadzone) {
  if (Math.abs(value) <= deadzone) return 0;
  return value > 0 ? value - deadzone : value + deadzone;
}

export function validateCursorMapping(mapping) {
  const xAxis = Number(mapping.xGyroAxis);
  const yAxis = Number(mapping.yGyroAxis);
  const sensitivity = Number(mapping.sensitivity);
  const deadzoneDps = Number(mapping.deadzoneDps);
  const xSign = Number(mapping.xSign);
  const ySign = Number(mapping.ySign);

  if (![0, 1, 2].includes(xAxis) || ![0, 1, 2].includes(yAxis) || xAxis === yAxis) {
    throw new RangeError("Choose two different gyro axes for horizontal and vertical movement");
  }
  if (![1, -1].includes(xSign) || ![1, -1].includes(ySign)) {
    throw new RangeError("Direction values must be either 1 or -1");
  }
  if (!Number.isFinite(sensitivity) || sensitivity < 0.2 || sensitivity > 8) {
    throw new RangeError("Sensitivity must be between 0.2 and 8.0");
  }
  if (!Number.isFinite(deadzoneDps) || deadzoneDps < 0 || deadzoneDps > 20) {
    throw new RangeError("Dead zone must be between 0 and 20 degrees per second");
  }
  return { xGyroAxis: xAxis, yGyroAxis: yAxis, xSign, ySign, sensitivity, deadzoneDps };
}
