from __future__ import annotations

from dataclasses import dataclass
import struct

PACKET = struct.Struct("<HhhhhhhBB")
PACKET_SIZE = PACKET.size
CONTACT_LEFT = 0x01
CONTACT_RIGHT = 0x02
SENSOR_READY = 0x01


@dataclass(frozen=True)
class SensorSample:
    sequence: int
    acceleration_mg: tuple[int, int, int]
    gyroscope_centi_dps: tuple[int, int, int]
    contacts: int
    status: int = SENSOR_READY

    @property
    def sensor_ready(self) -> bool:
        return bool(self.status & SENSOR_READY)

    @property
    def left_contact(self) -> bool:
        return bool(self.contacts & CONTACT_LEFT)

    @property
    def right_contact(self) -> bool:
        return bool(self.contacts & CONTACT_RIGHT)

    @property
    def features(self) -> tuple[float, float, float, float, float, float]:
        ax, ay, az = self.acceleration_mg
        gx, gy, gz = self.gyroscope_centi_dps
        return (
            ax / 1000.0,
            ay / 1000.0,
            az / 1000.0,
            gx / 25000.0,
            gy / 25000.0,
            gz / 25000.0,
        )


def decode_packet(payload: bytes | bytearray) -> SensorSample:
    if len(payload) != PACKET_SIZE:
        raise ValueError(f"Expected {PACKET_SIZE} bytes, received {len(payload)}")
    values = PACKET.unpack(payload)
    return SensorSample(
        sequence=values[0],
        acceleration_mg=(values[1], values[2], values[3]),
        gyroscope_centi_dps=(values[4], values[5], values[6]),
        contacts=values[7],
        status=values[8],
    )


def encode_packet(sample: SensorSample) -> bytes:
    return PACKET.pack(
        sample.sequence,
        *sample.acceleration_mg,
        *sample.gyroscope_centi_dps,
        sample.contacts,
        sample.status,
    )
