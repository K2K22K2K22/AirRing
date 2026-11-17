import { AirRingBle } from "./ble.js";
import { sequenceGap } from "./protocol.js";
import {
  STATIONARY_SAMPLE_TARGET,
  MOTION_SAMPLE_TARGET,
  summarizeGyro,
  detectDominantAxis,
  applyDeadzone,
  validateCursorMapping,
} from "./calibration.js";
import { createProfile, validateProfile, downloadProfile } from "./profile.js";
import { MotionChart } from "./visuals.js";

const byId = id => document.getElementById(id);
const state = {
  ble: null,
  connected: false,
  sensorReady: false,
  demoMode: false,
  samples: [],
  rateWindow: [],
  previousSequence: null,
  missedPackets: 0,
  validCount: 0,
  latestSample: null,
  calibration: null,
  capture: null,
  xCapture: null,
  yCapture: null,
  demoTimer: null,
  demoSequence: 0,
  previewX: 50,
  previewY: 50,
  lastPreviewAt: null,
  importedProfile: null,
  seenIndex: false,
  seenMiddle: false,
};

const chart = new MotionChart(byId("motionChart"));

function toast(message) {
  const node = byId("toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2600);
}

function setText(id, value) {
  byId(id).textContent = value;
}

function setConnectionPill(connected) {
  byId("connectionPill").classList.toggle("connected", connected);
  setText("connectionLabel", connected ? "AirRing connected" : state.demoMode ? "Demo stream" : "Not connected");
  byId("deviceIndicator").classList.toggle("connected", connected);
  setText("deviceStatus", connected ? "Connected and receiving notifications" : state.demoMode ? "Demo stream is active" : "Waiting for a connection");
  byId("connectButton").disabled = connected || !AirRingBle.isSupported();
  byId("disconnectButton").disabled = !connected;
  byId("streamDot").classList.toggle("live", connected || state.demoMode);
  setText("streamLabel", connected ? "LIVE STREAM" : state.demoMode ? "DEMO STREAM" : "STREAM OFF");
  byId("chartLive").classList.toggle("live", connected || state.demoMode);
  setText("chartLive", connected ? "LIVE" : state.demoMode ? "DEMO" : "NO DATA");
}

function updateControls() {
  const hardwareReady = state.connected && state.sensorReady && !state.demoMode;
  byId("calibrateButton").disabled = !hardwareReady || Boolean(state.capture);
  byId("captureXButton").disabled = !hardwareReady || !state.calibration?.stable || Boolean(state.capture);
  byId("captureYButton").disabled = !hardwareReady || !state.calibration?.stable || !state.xCapture?.detected || Boolean(state.capture);
  byId("downloadProfileButton").disabled = !hardwareReady || !state.calibration?.stable;
  byId("previewReady").classList.toggle("active", hardwareReady && Boolean(state.calibration?.stable));
  setText("previewReady", hardwareReady && state.calibration?.stable ? "CALIBRATED" : state.demoMode ? "DEMO" : "WAITING");
  if (state.demoMode) setText("previewHint", "DEMO STREAM · NO SENSOR CONNECTED");
  else if (hardwareReady && state.calibration?.stable) setText("previewHint", "Move your wrist to move the dot");
  else setText("previewHint", "Connect and calibrate to test motion");
  updateProfileCard();
}

function updateProfileCard() {
  const ready = state.connected && state.calibration?.stable;
  setText("profileStatus", ready ? "Ready to export" : "Waiting for calibration");
  if (ready) {
    const axes = `X: ${["X", "Y", "Z"][Number(byId("xAxis").value)]} · Y: ${["X", "Y", "Z"][Number(byId("yAxis").value)]}`;
    setText("profileSummary", `${axes}. Sensitivity ${Number(byId("sensitivityRange").value).toFixed(1)} and dead zone ${Number(byId("deadzoneRange").value).toFixed(1)} °/s.`);
  } else if (state.demoMode) {
    setText("profileSummary", "Demo readings cannot be exported as a hardware calibration.");
  } else {
    setText("profileSummary", "Connect the device and complete the stationary calibration to enable export.");
  }
}

function updateSidebar() {
  const completed = new Set();
  if ([...document.querySelectorAll("[data-check]")].every(input => input.checked)) completed.add("parts");
  if (state.connected && state.sensorReady) completed.add("readings");
  if (state.calibration?.stable) completed.add("calibration");
  if (state.xCapture?.detected && state.yCapture?.detected) completed.add("cursor-lab");
  if (state.seenIndex && state.seenMiddle) completed.add("contacts");
  if (state.connected && state.calibration?.stable) completed.add("finish");
  document.querySelectorAll(".step-link").forEach(link => {
    const stateNode = link.querySelector(".step-state");
    const done = completed.has(link.dataset.step);
    stateNode.textContent = done ? "✓" : "";
    stateNode.style.opacity = done ? "1" : "";
  });
}

function setSensorStatus(ready) {
  state.sensorReady = ready;
  const node = byId("sensorReadyValue");
  node.textContent = ready ? "READY" : "NO DATA";
  node.classList.toggle("good", ready);
  node.classList.toggle("bad", !ready && state.connected);
  updateControls();
}

function formatValue(value, digits = 2) {
  return Number(value).toFixed(digits);
}

function updateReadings(sample) {
  const [ax, ay, az] = sample.accelerationG;
  const [gx, gy, gz] = sample.gyroscopeDps;
  setText("axValue", formatValue(ax, 3));
  setText("ayValue", formatValue(ay, 3));
  setText("azValue", formatValue(az, 3));
  setText("gxValue", formatValue(gx));
  setText("gyValue", formatValue(gy));
  setText("gzValue", formatValue(gz));
  [["axBar", ax, 2], ["ayBar", ay, 2], ["azBar", az, 2], ["gxBar", gx, 250], ["gyBar", gy, 250], ["gzBar", gz, 250]].forEach(([id, value, range]) => {
    byId(id).style.width = `${Math.max(1, Math.min(100, Math.abs(value) / range * 100))}%`;
  });
  chart.push(sample.gyroscopeDps);
  updateContactState("indexLive", "indexTestState", sample.indexContact, "Index contact active", "Thumb + index detected");
  updateContactState("middleLive", "middleTestState", sample.middleContact, "Middle contact active", "Thumb + middle detected");
  setText("sequenceValue", String(sample.sequence).padStart(5, "0"));
}

function updateContactState(liveId, testId, active, activeMessage, testMessage) {
  const live = byId(liveId);
  live.classList.toggle("active", active);
  if (liveId === "indexLive" && active) state.seenIndex = true;
  if (liveId === "middleLive" && active) state.seenMiddle = true;
  live.querySelector("b").textContent = active ? "ACTIVE" : "OPEN";
  const test = byId(testId);
  test.classList.toggle("active", active);
  test.querySelector("strong").textContent = active ? testMessage : "Waiting for contact";
}

function updatePacketRate(sample) {
  const now = sample.receivedAt ?? performance.now();
  state.rateWindow.push(now);
  state.rateWindow = state.rateWindow.filter(time => now - time <= 1500);
  const rate = state.rateWindow.length > 1
    ? (state.rateWindow.length - 1) * 1000 / (state.rateWindow.at(-1) - state.rateWindow[0])
    : 0;
  setText("rateValue", `${rate.toFixed(1)} Hz`);
}

function movePreview(sample) {
  if (!state.calibration?.stable || !state.connected || state.demoMode) return;
  const cursor = currentCursorSettings();
  const axes = sample.gyroscopeDps;
  const xRate = applyDeadzone(axes[cursor.xGyroAxis] - state.calibration.biasDps[cursor.xGyroAxis], cursor.deadzoneDps) * cursor.xSign;
  const yRate = applyDeadzone(axes[cursor.yGyroAxis] - state.calibration.biasDps[cursor.yGyroAxis], cursor.deadzoneDps) * cursor.ySign;
  const now = sample.receivedAt ?? performance.now();
  const dt = state.lastPreviewAt === null ? .02 : Math.max(.001, Math.min((now - state.lastPreviewAt) / 1000, .06));
  state.lastPreviewAt = now;
  state.previewX = Math.max(4, Math.min(96, state.previewX + xRate * dt * cursor.sensitivity * .62));
  state.previewY = Math.max(4, Math.min(96, state.previewY + yRate * dt * cursor.sensitivity * .62));
  byId("previewCursor").style.left = `${state.previewX}%`;
  byId("previewCursor").style.top = `${state.previewY}%`;
  setText("previewCoordinates", `X ${String(Math.round(state.previewX * 10)).padStart(3, "0")} · Y ${String(Math.round(state.previewY * 10)).padStart(3, "0")}`);
}

function currentCursorSettings() {
  return {
    xGyroAxis: Number(byId("xAxis").value),
    yGyroAxis: Number(byId("yAxis").value),
    xSign: byId("invertX").checked ? -1 : 1,
    ySign: byId("invertY").checked ? -1 : 1,
    sensitivity: Number(byId("sensitivityRange").value),
    deadzoneDps: Number(byId("deadzoneRange").value),
  };
}

function processSample(sample) {
  state.latestSample = sample;
  updateReadings(sample);
  updatePacketRate(sample);
  if (state.previousSequence !== null) {
    state.missedPackets += sequenceGap(state.previousSequence, sample.sequence);
    setText("missedValue", String(state.missedPackets));
  }
  state.previousSequence = sample.sequence;
  setSensorStatus(sample.sensorReady);

  if (!sample.sensorReady) {
    state.validCount = 0;
    if (state.capture) finishCapture(false, "The sensor-ready flag went low during capture. Check wiring and try again.");
    updateSidebar();
    return;
  }

  state.validCount += 1;
  if (state.capture) {
    state.capture.samples.push(sample);
    updateCaptureProgress();
    if (state.capture.samples.length >= state.capture.target) finishCapture(true);
  }
  movePreview(sample);
  updateSidebar();
}

function startCapture(type, target) {
  if (!state.connected || !state.sensorReady || state.demoMode) {
    toast("Connect a real AirRing before capturing calibration data.");
    return;
  }
  state.capture = { type, target, samples: [] };
  if (type === "stationary") {
    state.calibration = null;
    state.xCapture = null;
    state.yCapture = null;
    setText("calibrationTitle", "Collecting stationary samples");
    setText("calibrationDescription", "Keep the sensor completely still until all 100 readings arrive.");
    setText("calibrationState", "COLLECTING");
  }
  updateCaptureProgress();
  updateControls();
  toast(type === "stationary" ? "Calibration started. Keep still." : "Motion capture started. Move smoothly now.");
}

function updateCaptureProgress() {
  if (!state.capture) return;
  const count = state.capture.samples.length;
  const percent = Math.min(100, count / state.capture.target * 100);
  if (state.capture.type === "stationary") {
    byId("calibrationProgress").style.width = `${percent}%`;
    setText("calibrationCount", `${count} / ${state.capture.target} samples`);
    setText("calibrationTime", `${Math.max(0, Math.ceil((state.capture.target - count) / 50))} sec left`);
  }
}

function finishCapture(completed, message = "") {
  const capture = state.capture;
  if (!capture) return;
  state.capture = null;
  if (!completed) {
    if (capture.type === "stationary") {
      state.calibration = null;
      setText("calibrationTitle", "Calibration interrupted");
      setText("calibrationDescription", message);
      setText("calibrationState", "FAILED");
      byId("calibrationState").className = "result-state failed";
    } else {
      toast(message);
    }
    updateControls();
    return;
  }

  if (capture.type === "stationary") {
    const result = summarizeGyro(capture.samples);
    state.calibration = result;
    setText("biasX", formatValue(result.biasDps[0], 3));
    setText("biasY", formatValue(result.biasDps[1], 3));
    setText("biasZ", formatValue(result.biasDps[2], 3));
    setText("calibrationCount", `${result.count} / ${STATIONARY_SAMPLE_TARGET} samples`);
    byId("calibrationProgress").style.width = "100%";
    const check = document.querySelector(".stability-check");
    check.classList.toggle("pass", result.stable);
    check.classList.toggle("fail", !result.stable);
    setText("stabilityIcon", result.stable ? "✓" : "!");
    setText("stabilityTitle", result.stable ? "Sensor is stable" : "Movement detected");
    setText("stabilityDetail", `Gyro standard deviation: X ${formatValue(result.stddevDps[0])}, Y ${formatValue(result.stddevDps[1])}, Z ${formatValue(result.stddevDps[2])} °/s.`);
    setText("calibrationTitle", result.stable ? "Calibration complete." : "Try the calibration again.");
    setText("calibrationDescription", result.stable ? "The gyro bias is recorded. Next, map the wrist rotations you want to use for pointer movement." : "The sensor moved too much during the sample window. Secure it and keep still while repeating the check.");
    setText("calibrationState", result.stable ? "PASSED" : "UNSTABLE");
    byId("calibrationState").className = `result-state ${result.stable ? "passed" : "failed"}`;
    if (result.stable) {
      toast("Stationary calibration passed.");
      state.lastPreviewAt = null;
      state.previewX = 50;
      state.previewY = 50;
    } else {
      toast("Calibration was not stable. Repeat while the sensor is still.");
    }
  } else if (capture.type === "cursor-x") {
    const result = detectDominantAxis(capture.samples, state.calibration.biasDps);
    state.xCapture = result;
    if (result.detected) {
      byId("xAxis").value = String(result.axis);
      byId("invertX").checked = result.sign < 0;
      byId("captureXResult").classList.add("done");
      setText("captureXResult", `Gyro ${["X", "Y", "Z"][result.axis]} detected · ${result.sign > 0 ? "positive" : "negative"} direction · ${result.magnitude.toFixed(1)} °/s`);
      toast("Horizontal motion mapped.");
    } else {
      byId("captureXResult").classList.remove("done");
      setText("captureXResult", "No clear rotation found. Repeat with a slower, larger wrist motion.");
    }
  } else if (capture.type === "cursor-y") {
    const xAxis = Number(byId("xAxis").value);
    const result = detectDominantAxis(capture.samples, state.calibration.biasDps, xAxis);
    state.yCapture = result;
    if (result.detected) {
      byId("yAxis").value = String(result.axis);
      byId("invertY").checked = result.sign < 0;
      byId("captureYResult").classList.add("done");
      setText("captureYResult", `Gyro ${["X", "Y", "Z"][result.axis]} detected · ${result.sign > 0 ? "positive" : "negative"} direction · ${result.magnitude.toFixed(1)} °/s`);
      toast("Vertical motion mapped.");
    } else {
      byId("captureYResult").classList.remove("done");
      setText("captureYResult", "No second axis detected. Use a clearer movement on a different axis.");
    }
  }

  updateControls();
  updateSidebar();
}

function setManualMapping() {
  const xAxis = Number(byId("xAxis").value);
  const yAxis = Number(byId("yAxis").value);
  if (xAxis === yAxis) {
    byId("yAxis").value = String((xAxis + 1) % 3);
    toast("Horizontal and vertical axes must be different.");
  }
  state.xCapture = null;
  state.yCapture = null;
  byId("captureXResult").classList.remove("done");
  byId("captureYResult").classList.remove("done");
  setText("captureXResult", "Horizontal axis set manually");
  setText("captureYResult", "Vertical axis set manually");
  updateProfileCard();
  updateControls();
}

function exportCurrentProfile() {
  try {
    const profile = createProfile({ calibration: state.calibration, cursor: currentCursorSettings() });
    downloadProfile(profile);
    toast("Calibration profile downloaded.");
  } catch (error) {
    toast(error.message);
  }
}

async function importProfile(file) {
  const status = byId("importStatus");
  try {
    const raw = JSON.parse(await file.text());
    const profile = validateProfile(raw);
    state.importedProfile = profile;
    byId("xAxis").value = String(profile.cursor.xGyroAxis);
    byId("yAxis").value = String(profile.cursor.yGyroAxis);
    byId("invertX").checked = profile.cursor.xSign < 0;
    byId("invertY").checked = profile.cursor.ySign < 0;
    byId("sensitivityRange").value = profile.cursor.sensitivity;
    byId("deadzoneRange").value = profile.cursor.deadzoneDps;
    updateTuningLabels();
    setManualMapping();
    status.textContent = "Profile validated and loaded into this page. Run the desktop importer to apply it to the Python app.";
    toast("Profile loaded for review.");
  } catch (error) {
    status.textContent = `Could not load profile: ${error.message}`;
    status.style.color = "#b86d58";
  }
}

function updateTuningLabels() {
  setText("sensitivityValue", Number(byId("sensitivityRange").value).toFixed(1));
  setText("deadzoneValue", Number(byId("deadzoneRange").value).toFixed(1));
  updateProfileCard();
}

function handleStatus(message) {
  const failed = message.toLowerCase().includes("error") || message.toLowerCase().includes("unavailable");
  byId("connectError").classList.toggle("hidden", !failed);
  if (failed) setText("connectError", message);
  setText("deviceStatus", message);
  if (message === "Disconnected" || message === "Device disconnected") {
    state.connected = false;
    setConnectionPill(false);
    setSensorStatus(false);
    state.calibration = null;
    if (state.capture) finishCapture(false, "The BLE connection ended during capture.");
    updateControls();
  }
}

function stopDemo() {
  if (state.demoTimer) clearInterval(state.demoTimer);
  state.demoTimer = null;
  state.demoMode = false;
  state.sensorReady = false;
  state.seenIndex = false;
  state.seenMiddle = false;
  setSensorStatus(false);
  byId("demoButton").innerHTML = '<span class="play-icon">▶</span> Try the interface';
  setConnectionPill(state.connected);
  toast("Demo stream stopped.");
}

function startDemo() {
  if (state.connected) {
    toast("Disconnect the hardware before starting the demo stream.");
    return;
  }
  if (state.demoMode) {
    stopDemo();
    return;
  }
  state.demoMode = true;
  state.demoSequence = 0;
  setConnectionPill(false);
  setConnectionPill(false);
  setText("deviceStatus", "Demo stream is active. No physical device is connected.");
  setSensorStatus(true);
  byId("demoButton").innerHTML = "Stop demo <span>■</span>";
  state.demoTimer = setInterval(() => {
    const t = state.demoSequence / 50;
    const sample = {
      sequence: state.demoSequence & 0xffff,
      accelerationG: [Math.sin(t * 1.3) * .04, Math.cos(t * 1.1) * .03, .998],
      gyroscopeDps: [Math.sin(t * 2.2) * 13, Math.cos(t * 1.8) * 8, Math.sin(t * 1.2) * 5],
      indexContact: Math.floor(t / 4) % 2 === 1 && t % 4 < 1.3,
      middleContact: Math.floor(t / 6) % 2 === 1 && t % 6 < 1.2,
      sensorReady: true,
      receivedAt: performance.now(),
    };
    processSample(sample);
    state.demoSequence += 1;
  }, 20);
  updateControls();
  toast("Demo stream active. These values are simulated.");
}

function setupPartsChecklist() {
  const inputs = [...document.querySelectorAll("[data-check]")];
  const update = () => {
    const count = inputs.filter(input => input.checked).length;
    setText("partsCount", `${count} / ${inputs.length} ready`);
    byId("partsProgress").style.width = `${count / inputs.length * 100}%`;
    updateSidebar();
  };
  inputs.forEach(input => input.addEventListener("change", update));
  update();
}

function setupPlatformTabs() {
  const commands = {
    fedora: {
      title: "Fedora packages",
      command: "sudo dnf install python3 python3-pip git make",
      text: "Use a data USB cable. If the board does not appear, check your USB serial driver and user permissions.",
    },
    ubuntu: {
      title: "Ubuntu and Debian packages",
      command: "sudo apt install python3 python3-pip git make",
      text: "Add your user to the serial-port group if needed, then sign out and back in before flashing.",
    },
    windows: {
      title: "Windows setup",
      command: "py -m pip install --user platformio",
      text: "Install the USB-to-UART driver required by your ESP32 board. Open PowerShell in the firmware folder before running PlatformIO.",
    },
  };
  document.querySelectorAll(".platform-tab").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll(".platform-tab").forEach(item => item.classList.toggle("selected", item === button));
    const item = commands[button.dataset.platform];
    byId("platformInfo").innerHTML = `<strong>${item.title}</strong><code>${item.command}</code><p>${item.text}</p>`;
  }));
}

function setupNavigation() {
  const links = [...document.querySelectorAll(".step-link")];
  const sections = links.map(link => byId(link.dataset.step)).filter(Boolean);
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach(link => link.classList.toggle("active", link.dataset.step === visible.target.id));
  }, { rootMargin: "-20% 0px -65% 0px", threshold: [0, .1, .3, .6] });
  sections.forEach(section => observer.observe(section));
}

function setupControls() {
  byId("connectButton").addEventListener("click", async () => {
    byId("connectError").classList.add("hidden");
    byId("connectButton").disabled = true;
    try {
      if (state.demoMode) stopDemo();
      const ble = new AirRingBle(processSample, handleStatus);
      state.ble = ble;
      await ble.connect();
      state.connected = true;
      setConnectionPill(true);
      state.previousSequence = null;
      state.missedPackets = 0;
      state.rateWindow = [];
      setText("missedValue", "0");
      state.calibration = null;
      setText("calibrationTitle", "Ready when you are.");
      setText("calibrationDescription", "Keep the sensor still. Calibration begins when you start the 100-sample check.");
      setText("calibrationState", "NOT RUN");
      byId("calibrationState").className = "result-state";
      updateControls();
      toast("AirRing connected.");
    } catch (error) {
      byId("connectButton").disabled = false;
      setText("connectError", error.message || "Could not connect to AirRing.");
      byId("connectError").classList.remove("hidden");
      handleStatus(error.message || "Bluetooth connection failed");
    }
  });

  byId("disconnectButton").addEventListener("click", () => {
    state.ble?.disconnect();
    state.connected = false;
    setConnectionPill(false);
    updateControls();
  });
  byId("demoButton").addEventListener("click", startDemo);
  byId("calibrateButton").addEventListener("click", () => startCapture("stationary", STATIONARY_SAMPLE_TARGET));
  byId("captureXButton").addEventListener("click", () => startCapture("cursor-x", MOTION_SAMPLE_TARGET));
  byId("captureYButton").addEventListener("click", () => startCapture("cursor-y", MOTION_SAMPLE_TARGET));
  byId("downloadProfileButton").addEventListener("click", exportCurrentProfile);
  byId("profileImportInput").addEventListener("change", event => {
    const file = event.target.files?.[0];
    if (file) importProfile(file);
    event.target.value = "";
  });
  ["xAxis", "yAxis", "invertX", "invertY"].forEach(id => byId(id).addEventListener("change", setManualMapping));
  byId("sensitivityRange").addEventListener("input", updateTuningLabels);
  byId("deadzoneRange").addEventListener("input", updateTuningLabels);
  document.querySelectorAll("[data-copy]").forEach(button => button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      toast("Commands copied.");
    } catch {
      toast("Clipboard access is unavailable in this browser.");
    }
  }));
}

function checkBrowser() {
  const supported = AirRingBle.isSupported();
  if (!window.isSecureContext) {
    setText("browserNotice", "This page is not in a secure context. Use the GitHub Pages HTTPS address or localhost.");
  } else if (!navigator.bluetooth?.requestDevice) {
    setText("browserNotice", "Web Bluetooth is not available in this browser. Use Chrome or Edge on desktop, or use the Python desktop app.");
  } else {
    setText("browserNotice", "Bluetooth permission is requested only after you press Connect AirRing.");
  }
  byId("connectButton").disabled = !supported;
  if (!supported) {
    setText("deviceStatus", "This browser cannot open a Web Bluetooth connection.");
    byId("connectError").textContent = "Use a supported browser over HTTPS. Firefox and Safari do not currently expose the Web Bluetooth connection flow used here.";
    byId("connectError").classList.remove("hidden");
  }
}

function setupPage() {
  setupPartsChecklist();
  setupPlatformTabs();
  setupNavigation();
  setupControls();
  checkBrowser();
  setConnectionPill(false);
  updateControls();
  updateTuningLabels();
}

setupPage();
