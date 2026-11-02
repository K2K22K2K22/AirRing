from airring.packet import SensorSample, decode_packet, encode_packet, PACKET_SIZE


def test_packet_round_trip():
    sample = SensorSample(
        sequence=65530,
        acceleration_mg=(10, -20, 1000),
        gyroscope_centi_dps=(150, -250, 300),
        contacts=3,
        status=1,
    )
    payload = encode_packet(sample)
    assert len(payload) == PACKET_SIZE
    assert decode_packet(payload) == sample


def test_feature_scaling():
    sample = SensorSample(1, (0, 0, 1000), (0, 0, 25000), 0)
    assert sample.features == (0.0, 0.0, 1.0, 0.0, 0.0, 1.0)


def test_decode_rejects_incorrect_packet_size():
    import pytest

    with pytest.raises(ValueError, match="Expected 16 bytes"):
        decode_packet(b"too short")


def test_sensor_status_marks_failed_imu():
    sample = SensorSample(1, (0, 0, 0), (0, 0, 0), 0, status=0)
    assert sample.sensor_ready is False
    assert decode_packet(encode_packet(sample)).sensor_ready is False
