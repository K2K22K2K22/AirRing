import asyncio
import threading

from airring import ble
from airring.packet import SensorSample, encode_packet


class FakeDevice:
    name = "AIRRING"


class FakeScanner:
    calls = 0

    @classmethod
    async def find_device_by_filter(cls, filter_func, timeout):
        cls.calls += 1
        return FakeDevice()


class FakeClient:
    instances = []
    disconnect_after_start = True

    def __init__(self, device, timeout):
        self.handler = None
        self.connected = True
        self.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        self.connected = False
        return None

    async def start_notify(self, uuid, handler):
        self.handler = handler
        if self.disconnect_after_start and len(self.instances) == 1:
            self.connected = False

    @property
    def is_connected(self):
        return self.connected


def test_ble_reconnects_after_disconnect(monkeypatch):
    FakeScanner.calls = 0
    FakeClient.instances = []
    FakeClient.disconnect_after_start = True
    monkeypatch.setattr(ble, "BleakScanner", FakeScanner)
    monkeypatch.setattr(ble, "BleakClient", FakeClient)

    events = []
    stop_event = threading.Event()

    def on_status(status):
        events.append(status)
        if len(FakeClient.instances) == 2 and status.startswith("Connected"):
            stop_event.set()

    asyncio.run(ble.run_ble_client(lambda _sample: None, on_status, stop_event))

    assert FakeScanner.calls == 2
    assert len(FakeClient.instances) == 2
    assert sum(status.startswith("Connected") for status in events) == 2
    assert "Disconnected. Retrying" in events
    assert events[-1] == "Stopped"


def test_notification_decodes_packet(monkeypatch):
    FakeScanner.calls = 0
    FakeClient.instances = []
    FakeClient.disconnect_after_start = False
    monkeypatch.setattr(ble, "BleakScanner", FakeScanner)
    monkeypatch.setattr(ble, "BleakClient", FakeClient)

    received = []
    stop_event = threading.Event()
    sample = SensorSample(7, (0, 0, 1000), (0, 0, 120), 1, 1)

    def on_status(_status):
        return None

    def on_sample(value):
        received.append(value)
        stop_event.set()

    async def exercise():
        task = asyncio.create_task(ble.run_ble_client(on_sample, on_status, stop_event))
        while not FakeClient.instances or FakeClient.instances[0].handler is None:
            await asyncio.sleep(0.01)
        FakeClient.instances[0].handler(1, bytearray(encode_packet(sample)))
        await task

    asyncio.run(exercise())

    assert received == [sample]
