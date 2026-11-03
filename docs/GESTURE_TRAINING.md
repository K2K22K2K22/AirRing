# Gesture Training

The desktop mouse works without a trained model. The LSTM adds discrete gestures for slide navigation, scrolling and pointer pause.

## Classes

| Class | Action |
|---|---|
| `idle` | No action |
| `swipe_left` | Left arrow |
| `swipe_right` | Right arrow |
| `circle_cw` | Scroll up |
| `circle_ccw` | Scroll down |
| `double_flick` | Toggle pointer movement |

## Collect recordings

Keep the sensor in the normal wearing position. Do not change the orientation between classes.

```bash
cd desktop
pip install -e ".[ai]"
python tools/collect_gestures.py --repetitions 25
```

The collector captures one-second windows at 50 samples per second. Each trial should contain one clear gesture centred in the capture window. For `idle`, keep the hand still.

Collect more examples if two classes are frequently confused. Include natural variations in movement speed, but avoid changing the mounting orientation during a collection session.

## Train

```bash
python tools/train_gestures.py --epochs 60
```

Useful options:

```bash
python tools/train_gestures.py \
  --data data/gesture_dataset.npz \
  --output models/gesture_lstm.pt \
  --epochs 80 \
  --batch-size 16 \
  --learning-rate 0.0005 \
  --validation-fraction 0.25 \
  --seed 17
```

The script validates the six classes, window shape, finite values and minimum recording count. It makes a seeded stratified validation split and saves the checkpoint with the best validation accuracy. The desktop app rejects checkpoints whose classes, window length, sample rate or model shape do not match this repository. It does not create fake training data.

## Evaluate

For a meaningful evaluation, collect a second dataset in a separate session and compare predictions against the labels. Do not report training accuracy as real-world recognition accuracy.

The model runs locally on the computer. No external model API is used.
