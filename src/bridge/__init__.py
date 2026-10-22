"""Hardware bridge package for Circuit Tracks."""

from src.bridge.midi_detector import (
    MidiDeviceStatus,
    MockCircuitTracksConnection,
    detect_circuit_tracks,
    get_midi_connection,
)

__all__ = [
    "MidiDeviceStatus",
    "MockCircuitTracksConnection",
    "detect_circuit_tracks",
    "get_midi_connection",
]
