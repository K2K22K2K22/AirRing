from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

from bleak import BleakClient, BleakScanner

from .config import DEVICE_NAME_PREFIX, SENSOR_UUID
from .packet import SensorSample, decode_packet

SampleCallback = Callable[[SensorSample], None]
StatusCallback = Callable[[str], None]


async def run_ble_client(
    on_sample: SampleCallback,
    on_status: StatusCallback,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        try:
            on_status("Searching for AirRing")
            device = await BleakScanner.find_device_by_filter(
                lambda d, advertisement: (
                    (advertisement.local_name or d.name or "").startswith(DEVICE_NAME_PREFIX)
                ),
                timeout=8.0,
            )
            if device is None:
                on_status("AirRing not found. Retrying")
                await asyncio.sleep(2)
                continue

            on_status(f"Connecting to {device.name or DEVICE_NAME_PREFIX}")
            async with BleakClient(device, timeout=10.0) as client:
                def notification_handler(_sender: int, data: bytearray) -> None:
                    try:
                        on_sample(decode_packet(data))
                    except ValueError:
                        on_status("Invalid sensor packet")

                await client.start_notify(SENSOR_UUID, notification_handler)
                on_status("Connected. Hold still for calibration")
                while client.is_connected and not stop_event.is_set():
                    await asyncio.sleep(0.1)

        except Exception as exc:
            on_status(f"BLE error: {exc}")
        else:
            on_status("Disconnected. Retrying")

        if not stop_event.is_set():
            await asyncio.sleep(1)

    on_status("Stopped")
