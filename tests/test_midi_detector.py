"""Tests for MIDI port detection and mock fallback."""

from src.bridge.midi_detector import (
    MockCircuitTracksConnection,
    detect_circuit_tracks,
    get_midi_connection,
)


def test_midi_detector_detection_status():
    status = detect_circuit_tracks()
    assert hasattr(status, "is_connected")
    assert hasattr(status, "is_mock")
    assert isinstance(status.available_outputs, list)


def test_mock_fallback_connection():
    conn = get_midi_connection(force_mock=True)
    assert isinstance(conn, MockCircuitTracksConnection)
    assert conn.is_connected
    assert conn.has_input

    # Verify sending commands does not crash and logs messages
    conn.note_on(channel=0, note=60, velocity=100)
    conn.control_change(channel=0, control=74, value=80)
    conn.send_sysex([0xF0, 0x00, 0xF7])
    conn.all_notes_off(0)

    assert len(conn.sent_messages) == 4
    assert conn.sent_messages[0]["type"] == "note_on"
    assert conn.sent_messages[1]["type"] == "control_change"


def test_mock_sysex_request():
    from circuit_tracks.constants import (
        SYSEX_MANUFACTURER_ID,
        SYSEX_PRODUCT_NUMBER,
        SYSEX_PRODUCT_TYPE,
    )

    conn = MockCircuitTracksConnection()
    req = SYSEX_MANUFACTURER_ID + [SYSEX_PRODUCT_TYPE, SYSEX_PRODUCT_NUMBER, 0x40, 0x00, 0x00]
    res = conn.sysex_request(req)
    assert res is not None
    assert len(res) == 8 + 340
