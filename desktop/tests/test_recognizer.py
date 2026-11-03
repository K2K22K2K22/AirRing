from airring.ai.recognizer import GestureRecognizer


def test_missing_model_keeps_gestures_disabled(tmp_path):
    recognizer = GestureRecognizer(model_path=tmp_path / "missing.pt")
    for _ in range(60):
        assert recognizer.add_sample((0.0, 0.0, 1.0, 0.0, 0.0, 0.0)) is None

    assert recognizer.enabled is False
    assert recognizer.error == "No trained model"


def test_reset_clears_motion_window(tmp_path):
    recognizer = GestureRecognizer(model_path=tmp_path / "missing.pt")
    for _ in range(10):
        recognizer.add_sample((0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    recognizer.reset()

    assert len(recognizer.window) == 0
    assert recognizer.samples_since_inference == 0
    assert recognizer.last_fired == "idle"
