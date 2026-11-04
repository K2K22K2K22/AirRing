import json
from pathlib import Path

DIAGRAM = Path(__file__).resolve().parents[2] / "hardware" / "wokwi" / "diagram.json"


def test_wokwi_diagram_has_required_parts_and_connections():
    diagram = json.loads(DIAGRAM.read_text(encoding="utf-8"))
    parts = {part["id"]: part["type"] for part in diagram["parts"]}
    connections = [tuple(connection[:2]) for connection in diagram["connections"]]

    assert parts == {
        "esp": "board-esp32-devkit-c-v4",
        "imu": "wokwi-mpu6050",
        "left": "wokwi-pushbutton",
        "right": "wokwi-pushbutton",
    }
    assert ("esp:21", "imu:SDA") in connections
    assert ("esp:22", "imu:SCL") in connections
    assert ("esp:32", "left:1.l") in connections
    assert ("esp:33", "right:1.l") in connections
    assert ("esp:TX", "$serialMonitor:RX") in connections
