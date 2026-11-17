from __future__ import annotations

import unittest

from desktop.tools.apply_calibration_profile import apply_settings, validate_profile


class SetupProfileImportTests(unittest.TestCase):
    def make_profile(self):
        return {
            "schema": "airring-calibration-profile",
            "schemaVersion": 1,
            "device": {
                "name": "AIRRING",
                "serviceUuid": "a14d0001-7f5a-4d10-9a20-7b9c00000001",
                "sensorCharacteristicUuid": "a14d0002-7f5a-4d10-9a20-7b9c00000001",
                "packetBytes": 16,
            },
            "sampleRateHz": 50,
            "cursor": {
                "xGyroAxis": 2,
                "yGyroAxis": 0,
                "xSign": 1,
                "ySign": -1,
                "sensitivity": 3.1,
                "deadzoneDps": 4.5,
            },
            "sensorCalibration": {
                "gyroBiasDps": [0.1, -0.2, 0.05],
                "gyroStdDevDps": [0.1, 0.12, 0.08],
                "stationarySamples": 100,
            },
        }

    def test_valid_profile_returns_desktop_settings(self):
        settings = validate_profile(self.make_profile())
        self.assertEqual(settings["CURSOR_X_GYRO_AXIS"], 2)
        self.assertEqual(settings["CURSOR_Y_GYRO_AXIS"], 0)
        self.assertEqual(settings["CURSOR_Y_SIGN"], -1.0)
        self.assertEqual(settings["DEFAULT_SENSITIVITY"], 3.1)
        self.assertEqual(settings["DEFAULT_DEADZONE_DPS"], 4.5)

    def test_profile_with_reused_axes_is_rejected(self):
        profile = self.make_profile()
        profile["cursor"]["yGyroAxis"] = 2
        with self.assertRaisesRegex(ValueError, "must be different"):
            validate_profile(profile)

    def test_profile_with_wrong_protocol_is_rejected(self):
        profile = self.make_profile()
        profile["device"]["packetBytes"] = 20
        with self.assertRaisesRegex(ValueError, "16-byte"):
            validate_profile(profile)

    def test_profile_that_failed_stationary_check_is_rejected(self):
        profile = self.make_profile()
        profile["sensorCalibration"]["gyroStdDevDps"][1] = 4.0
        with self.assertRaisesRegex(ValueError, "stability check"):
            validate_profile(profile)

    def test_config_assignments_are_updated_without_touching_other_values(self):
        source = (
            "CURSOR_X_GYRO_AXIS = 2\n"
            "CURSOR_Y_GYRO_AXIS = 0\n"
            "CURSOR_X_SIGN = 1.0\n"
            "CURSOR_Y_SIGN = -1.0\n"
            "DEFAULT_SENSITIVITY = 2.8\n"
            "DEFAULT_DEADZONE_DPS = 5.0\n"
            "OTHER_SETTING = True\n"
        )
        changed = apply_settings(source, validate_profile(self.make_profile()))
        self.assertIn("DEFAULT_SENSITIVITY = 3.1", changed)
        self.assertIn("DEFAULT_DEADZONE_DPS = 4.5", changed)
        self.assertIn("OTHER_SETTING = True", changed)


if __name__ == "__main__":
    unittest.main()
