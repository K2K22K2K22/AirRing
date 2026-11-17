#!/usr/bin/env python3
"""Validate an AirRing web profile and apply its cursor settings to config.py."""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "airring-calibration-profile"
PROFILE_VERSION = 1
SERVICE_UUID = "a14d0001-7f5a-4d10-9a20-7b9c00000001"
SENSOR_UUID = "a14d0002-7f5a-4d10-9a20-7b9c00000001"


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def validate_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("The profile root must be a JSON object")
    if profile.get("schema") != PROFILE_SCHEMA or profile.get("schemaVersion") != PROFILE_VERSION:
        raise ValueError("Unsupported profile format. Export a profile from the AirRing Setup page")

    device = profile.get("device")
    if not isinstance(device, dict):
        raise ValueError("The profile is missing its device information")
    if device.get("serviceUuid") != SERVICE_UUID or device.get("sensorCharacteristicUuid") != SENSOR_UUID:
        raise ValueError("The profile does not match the AirRing BLE service")
    if device.get("packetBytes") != 16 or profile.get("sampleRateHz") != 50:
        raise ValueError("The profile does not match the 16-byte, 50 Hz AirRing packet")

    cursor = profile.get("cursor")
    if not isinstance(cursor, dict):
        raise ValueError("The profile is missing cursor settings")

    x_axis = cursor.get("xGyroAxis")
    y_axis = cursor.get("yGyroAxis")
    if isinstance(x_axis, bool) or x_axis not in (0, 1, 2):
        raise ValueError("Horizontal gyro axis must be 0, 1 or 2")
    if isinstance(y_axis, bool) or y_axis not in (0, 1, 2):
        raise ValueError("Vertical gyro axis must be 0, 1 or 2")
    if x_axis == y_axis:
        raise ValueError("Horizontal and vertical axes must be different")

    x_sign = _number(cursor.get("xSign"), "xSign")
    y_sign = _number(cursor.get("ySign"), "ySign")
    if x_sign not in (-1, 1) or y_sign not in (-1, 1):
        raise ValueError("Cursor direction values must be either -1 or 1")

    sensitivity = _number(cursor.get("sensitivity"), "sensitivity")
    deadzone = _number(cursor.get("deadzoneDps"), "deadzoneDps")
    if not 0.2 <= sensitivity <= 8.0:
        raise ValueError("Sensitivity must be between 0.2 and 8.0")
    if not 0.0 <= deadzone <= 20.0:
        raise ValueError("Dead zone must be between 0 and 20 degrees per second")

    sensor = profile.get("sensorCalibration")
    if not isinstance(sensor, dict):
        raise ValueError("The profile is missing its stationary sensor calibration")
    bias = sensor.get("gyroBiasDps")
    deviation = sensor.get("gyroStdDevDps")
    count = sensor.get("stationarySamples")
    if not isinstance(bias, list) or len(bias) != 3:
        raise ValueError("The profile must contain three gyro bias values")
    if not all(math.isfinite(_number(value, "gyroBiasDps")) for value in bias):
        raise ValueError("The gyro bias values must be finite numbers")
    if not isinstance(deviation, list) or len(deviation) != 3:
        raise ValueError("The profile must contain three gyro stability values")
    deviations = [_number(value, "gyroStdDevDps") for value in deviation]
    if any(value < 0 or value > 2.8 for value in deviations):
        raise ValueError("The stationary stability check did not pass")
    if isinstance(count, bool) or not isinstance(count, int) or count < 100:
        raise ValueError("At least 100 stationary samples are required")

    return {
        "CURSOR_X_GYRO_AXIS": int(x_axis),
        "CURSOR_Y_GYRO_AXIS": int(y_axis),
        "CURSOR_X_SIGN": float(int(x_sign)),
        "CURSOR_Y_SIGN": float(int(y_sign)),
        "DEFAULT_SENSITIVITY": sensitivity,
        "DEFAULT_DEADZONE_DPS": deadzone,
    }


def format_value(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.6g}"


def apply_settings(config_text: str, settings: dict[str, float | int]) -> str:
    updated = config_text
    for key, value in settings.items():
        pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=\s*[^\r\n]*$")
        replacement = f"{key} = {format_value(value)}"
        updated, count = pattern.subn(replacement, updated)
        if count != 1:
            raise ValueError(f"Expected exactly one {key} assignment in config.py, found {count}")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply an AirRing Setup profile to the existing Python desktop configuration."
    )
    parser.add_argument("profile", type=Path, help="Path to airring-profile.json")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src" / "airring" / "config.py",
        help="Path to desktop/src/airring/config.py",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the changes without writing files")
    parser.add_argument("--no-backup", action="store_true", help="Do not create config.py.bak")
    args = parser.parse_args()

    try:
        profile_data = json.loads(args.profile.read_text(encoding="utf-8"))
        settings = validate_profile(profile_data)
        original = args.config.read_text(encoding="utf-8")
        updated = apply_settings(original, settings)

        print("Validated AirRing calibration profile")
        for key, value in settings.items():
            print(f"  {key} = {format_value(value)}")

        if args.dry_run:
            print("\nDry run only. No files were changed.")
            return 0

        backup = args.config.with_suffix(args.config.suffix + ".bak")
        if not args.no_backup:
            if backup.exists():
                raise FileExistsError(
                    f"Backup already exists at {backup}. Move it first or use --no-backup after checking it."
                )
            shutil.copy2(args.config, backup)

        args.config.write_text(updated, encoding="utf-8")
        print(f"\nUpdated {args.config}")
        if not args.no_backup:
            print(f"Backup saved to {backup}")
        print("The desktop app takes a fresh gyro bias when it connects. Restart it to use these cursor settings.")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Profile import failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
