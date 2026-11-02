from airring.controller import AirMouseController
from airring.packet import SensorSample


class FakeMouse:
    def __init__(self):
        self.events = []

    def moveRel(self, x, y, duration=0):
        self.events.append(("move", x, y))

    def mouseDown(self, button="left"):
        self.events.append(("down", button))

    def mouseUp(self, button="left"):
        self.events.append(("up", button))

    def click(self, button="left"):
        self.events.append(("click", button))

    def scroll(self, clicks):
        self.events.append(("scroll", clicks))

    def press(self, key):
        self.events.append(("press", key))


def sample(sequence, contacts=0, gx=0, gy=0, gz=0, status=1):
    return SensorSample(sequence, (0, 0, 1000), (gx, gy, gz), contacts, status)


def test_left_contact_holds_and_releases():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    controller.process_sample(sample(2, contacts=1), now=0.02)
    controller.process_sample(sample(3, contacts=1), now=0.04)
    controller.process_sample(sample(4, contacts=0), now=0.06)
    assert mouse.events.count(("down", "left")) == 1
    assert mouse.events.count(("up", "left")) == 1


def test_right_contact_clicks_once_per_press():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    controller.process_sample(sample(2, contacts=2), now=0.02)
    controller.process_sample(sample(3, contacts=2), now=0.04)
    controller.process_sample(sample(4), now=0.06)
    assert mouse.events.count(("click", "right")) == 1


def test_gesture_mapping():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse)
    controller.handle_gesture("circle_cw")
    assert ("scroll", 4) in mouse.events


def test_gyro_moves_pointer_after_calibration():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    controller.process_sample(sample(2, gz=10000), now=0.02)
    assert any(event[0] == "move" for event in mouse.events)


def test_disconnect_releases_drag_and_requires_recalibration():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    controller.process_sample(sample(2, contacts=1), now=0.02)

    controller.disconnect()

    assert ("up", "left") in mouse.events
    assert controller.state.calibrated is False
    assert controller.state.calibration_samples == 0
    assert controller._left_down is False


def test_paused_pointer_does_not_trigger_contacts():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    assert controller.toggle_cursor() is False

    controller.process_sample(sample(2, contacts=3), now=0.02)
    assert not any(event[0] in {"down", "click"} for event in mouse.events)

    assert controller.toggle_cursor() is True
    controller.process_sample(sample(3, contacts=3), now=0.04)
    assert not any(event[0] in {"down", "click"} for event in mouse.events)

    controller.process_sample(sample(4), now=0.06)
    controller.process_sample(sample(5, contacts=3), now=0.08)
    assert ("down", "left") in mouse.events
    assert ("click", "right") in mouse.events


def test_sample_sequence_drives_timing_across_counter_wrap():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(65534))
    controller.process_sample(sample(1, gz=10000))
    assert any(event[0] == "move" for event in mouse.events)


def test_all_discrete_gesture_mappings():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse)

    controller.handle_gesture("swipe_left")
    controller.handle_gesture("swipe_right")
    controller.handle_gesture("circle_cw")
    controller.handle_gesture("circle_ccw")

    assert ("press", "left") in mouse.events
    assert ("press", "right") in mouse.events
    assert ("scroll", 4) in mouse.events
    assert ("scroll", -4) in mouse.events
    assert controller.state.last_gesture == "circle_ccw"


def test_calibration_averages_gyro_bias():
    controller = AirMouseController(mouse=FakeMouse(), calibration_samples=2)
    controller.process_sample(sample(1, gx=0), now=0.0)
    controller.process_sample(sample(2, gx=1000), now=0.02)

    assert controller.state.calibrated is True
    assert controller._gyro_bias[0] == 5.0


def test_deadzone_setting_is_clamped():
    controller = AirMouseController(mouse=FakeMouse())
    controller.set_deadzone(100)
    assert controller.deadzone_dps == 20.0
    controller.set_deadzone(-1)
    assert controller.deadzone_dps == 0.0


def test_invalid_sensor_status_blocks_control_and_releases_drag():
    mouse = FakeMouse()
    controller = AirMouseController(mouse=mouse, calibration_samples=1)
    controller.process_sample(sample(1), now=0.0)
    controller.process_sample(sample(2, contacts=1), now=0.02)
    controller.process_sample(sample(3, contacts=1, status=0), now=0.04)

    assert mouse.events.count(("down", "left")) == 1
    assert mouse.events.count(("up", "left")) == 1
    assert controller.state.sensor_ready is False

    controller.process_sample(sample(4, gz=10000), now=0.06)
    assert not any(event[0] == "move" for event in mouse.events)
