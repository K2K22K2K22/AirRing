from pathlib import Path

DEVICE_NAME_PREFIX = "AIRRING"
SERVICE_UUID = "a14d0001-7f5a-4d10-9a20-7b9c00000001"
SENSOR_UUID = "a14d0002-7f5a-4d10-9a20-7b9c00000001"
SAMPLE_RATE_HZ = 50
PACKET_WINDOW = 50

GESTURE_CLASSES = (
    "idle",
    "swipe_left",
    "swipe_right",
    "circle_cw",
    "circle_ccw",
    "double_flick",
)
MODEL_INPUT_SIZE = 6
MODEL_HIDDEN_SIZE = 64
MODEL_NUM_LAYERS = 2
DEFAULT_TRAINING_SEED = 42
DEFAULT_VALIDATION_FRACTION = 0.2
MIN_RECORDINGS_PER_CLASS = 5

# Adjust for your mounting orientation.
CURSOR_X_GYRO_AXIS = 2
CURSOR_Y_GYRO_AXIS = 0
CURSOR_X_SIGN = 1.0
CURSOR_Y_SIGN = -1.0

DEFAULT_SENSITIVITY = 2.8
DEFAULT_DEADZONE_DPS = 5.0
DEFAULT_GESTURE_CONFIDENCE = 0.85
GESTURE_COOLDOWN_S = 0.9
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "gesture_lstm.pt"
DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "gesture_dataset.npz"
