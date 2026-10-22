"""MIDI port detector with automatic mock fallback for Novation Circuit Tracks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import mido

try:
    from circuit_tracks.midi import MidiConnection
except (ImportError, ModuleNotFoundError):
    # Fallback definition if vendor midi module is not directly importable
    MidiConnection = None  # type: ignore

logger = logging.getLogger(__name__)

CIRCUIT_TRACKS_KEYWORD = "circuit tracks"


@dataclass
class MidiDeviceStatus:
    is_connected: bool
    is_mock: bool
    port_name: str | None
    input_port_name: str | None
    device_name: str | None = None
    available_outputs: list[str] = field(default_factory=list)
    available_inputs: list[str] = field(default_factory=list)


class MockCircuitTracksConnection:
    """Mock fallback connection behaving like MidiConnection when hardware is offline."""

    def __init__(self, port_name: str = "Mock Circuit Tracks MIDI") -> None:
        self._port_name = port_name
        self._input_port_name = port_name
        self.is_connected = True
        self.has_input = True
        self.is_mock = True
        self.sent_messages: list[Any] = []
        self.sysex_requests: list[list[int]] = []

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def connect(self, port_name: str) -> None:
        self._port_name = port_name
        self._input_port_name = port_name
        self.is_connected = True

    def disconnect(self) -> None:
        self.is_connected = False

    def send(self, msg: Any) -> None:
        self.sent_messages.append(msg)

    def note_on(self, channel: int, note: int, velocity: int = 100) -> None:
        self.sent_messages.append(
            {"type": "note_on", "channel": channel, "note": note, "velocity": velocity}
        )

    def note_off(self, channel: int, note: int) -> None:
        self.sent_messages.append(
            {"type": "note_off", "channel": channel, "note": note, "velocity": 0}
        )

    def play_note(
        self, channel: int, note: int, velocity: int = 100, duration_s: float = 0.5
    ) -> None:
        self.note_on(channel, note, velocity)
        self.note_off(channel, note)

    def control_change(self, channel: int, control: int, value: int) -> None:
        self.sent_messages.append(
            {"type": "control_change", "channel": channel, "control": control, "value": value}
        )

    def nrpn(self, channel: int, msb: int, lsb: int, value: int) -> None:
        self.sent_messages.append(
            {"type": "nrpn", "channel": channel, "msb": msb, "lsb": lsb, "value": value}
        )

    def program_change(self, channel: int, program: int) -> None:
        self.sent_messages.append(
            {"type": "program_change", "channel": channel, "program": program}
        )

    def send_sysex(self, data: list[int]) -> None:
        self.sent_messages.append({"type": "sysex", "data": list(data)})

    def send_clock(self) -> None:
        self.sent_messages.append({"type": "clock"})

    def all_notes_off(self, channel: int) -> None:
        self.sent_messages.append({"type": "all_notes_off", "channel": channel})

    def send_realtime(self, msg_type: str) -> None:
        self.sent_messages.append({"type": "realtime", "msg_type": msg_type})

    def sysex_request(
        self,
        request_data: list[int],
        timeout_s: float = 3.0,
        match_fn: Any = None,
    ) -> list[int] | None:
        self.sysex_requests.append(list(request_data))
        # Default mock response for patch dump if requested
        if len(request_data) >= 7 and request_data[5] == 0x40:
            synth_idx = request_data[6]
            from circuit_tracks.patch_builder import PatchBuilder

            patch_bytes = list(PatchBuilder(f"MockSynth{synth_idx + 1}").build())
            from circuit_tracks.constants import (
                SYSEX_MANUFACTURER_ID,
                SYSEX_PRODUCT_NUMBER,
                SYSEX_PRODUCT_TYPE,
            )

            response = (
                SYSEX_MANUFACTURER_ID
                + [SYSEX_PRODUCT_TYPE, SYSEX_PRODUCT_NUMBER, 0x00, synth_idx, 0x00]
                + patch_bytes
            )
            return response
        return None


def detect_circuit_tracks() -> MidiDeviceStatus:
    """Scan MIDI input/output ports for Novation Circuit Tracks."""
    try:
        out_ports = mido.get_output_names()
    except Exception as exc:
        logger.warning("Failed to query MIDI output ports: %s", exc)
        out_ports = []

    try:
        in_ports = mido.get_input_names()
    except Exception as exc:
        logger.warning("Failed to query MIDI input ports: %s", exc)
        in_ports = []

    matched_out = next(
        (p for p in out_ports if CIRCUIT_TRACKS_KEYWORD in p.lower()), None
    )
    matched_in = next(
        (p for p in in_ports if CIRCUIT_TRACKS_KEYWORD in p.lower()), None
    )

    if matched_out:
        return MidiDeviceStatus(
            is_connected=True,
            is_mock=False,
            port_name=matched_out,
            input_port_name=matched_in,
            device_name=matched_out,
            available_outputs=out_ports,
            available_inputs=in_ports,
        )

    return MidiDeviceStatus(
        is_connected=False,
        is_mock=True,
        port_name=None,
        input_port_name=None,
        device_name=None,
        available_outputs=out_ports,
        available_inputs=in_ports,
    )


def get_midi_connection(force_mock: bool = False) -> Any:
    """Obtain a connected hardware MIDI connection or return MockCircuitTracksConnection."""
    if force_mock or MidiConnection is None:
        if MidiConnection is None:
            logger.debug("MidiConnection class not available. Defaulting to mock.")
        else:
            logger.info("Mock connection requested explicitly.")
        return MockCircuitTracksConnection()

    status = detect_circuit_tracks()
    if status.is_connected and status.port_name:
        try:
            conn = MidiConnection()
            conn.connect(status.port_name)
            logger.info("Connected to physical hardware on %s", status.port_name)
            return conn
        except Exception as exc:
            logger.warning(
                "Failed to open physical MIDI port %s (%s). Falling back to mock.",
                status.port_name,
                exc,
            )

    logger.info("No physical Circuit Tracks found. Using MockCircuitTracksConnection.")
    return MockCircuitTracksConnection()
