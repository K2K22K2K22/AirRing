# Desktop Companion

The desktop application connects to AirRing over BLE, converts IMU rotation into pointer movement, handles foil-contact clicks, and optionally runs the local LSTM gesture model.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install the optional AI dependencies for gesture training and recognition:

```bash
pip install -e ".[ai]"
```

## Run

```bash
python -m airring
```

## Train gestures

```bash
python tools/collect_gestures.py --repetitions 25
python tools/train_gestures.py --epochs 60
```

Training data is stored in `data/` and the model is saved in `models/`. Both are ignored by Git. See `../docs/GESTURE_TRAINING.md` for the collection procedure.

## Tests

```bash
pip install -e ".[dev]"
pytest
```
