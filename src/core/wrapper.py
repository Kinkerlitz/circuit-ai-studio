"""Thin wrapper around vendor.circuit_tracks for project and patch handling."""

from __future__ import annotations

from pathlib import Path

from circuit_tracks.constants import (
    SYSEX_CMD_REPLACE_CURRENT_PATCH,
    SYSEX_MANUFACTURER_ID,
    SYSEX_PRODUCT_NUMBER,
    SYSEX_PRODUCT_TYPE,
)
from circuit_tracks.ncs_parser import (
    NCS_FILE_SIZE,
    NCSFile,
    parse_ncs_from_bytes,
    serialize_ncs,
)
from circuit_tracks.patch import _PATCH_SIZE, parse_patch_data
from circuit_tracks.patch_builder import PatchBuilder
from circuit_tracks.song import SongData, parse_song, song_to_ncs

VENDOR_TEMPLATE = Path(__file__).resolve().parents[2] / "vendor" / "circuit-tracks-tools" / "src" / "circuit_tracks" / "data" / "Empty.ncs"


def get_template_path() -> Path:
    """Return path to Empty.ncs template."""
    return VENDOR_TEMPLATE


def create_empty_ncs() -> NCSFile:
    """Create a default NCSFile instance from the vendor template."""
    raw = VENDOR_TEMPLATE.read_bytes()
    return parse_ncs_from_bytes(raw)


def load_ncs_from_bytes(data: bytes) -> NCSFile:
    """Parse raw bytes into an NCSFile object."""
    if len(data) != NCS_FILE_SIZE:
        raise ValueError(f"Invalid NCS file size: {len(data)} (expected {NCS_FILE_SIZE})")
    return parse_ncs_from_bytes(data)


def song_to_ncs_bytes(song: SongData | dict) -> bytes:
    """Compile a SongData object or valid dictionary to 160,780-byte NCS binary."""
    if isinstance(song, dict):
        song = parse_song(song)
    return song_to_ncs(song, template_path=get_template_path())


def patch_to_syx(patch_bytes: bytes, synth: int = 1) -> bytes:
    """Wrap 340-byte patch binary into Replace Current Patch SysEx format."""
    if len(patch_bytes) != _PATCH_SIZE:
        raise ValueError(f"Patch data must be {_PATCH_SIZE} bytes, got {len(patch_bytes)}")
    synth_index = synth - 1
    header = bytes(
        [0xF0]
        + SYSEX_MANUFACTURER_ID
        + [SYSEX_PRODUCT_TYPE, SYSEX_PRODUCT_NUMBER, SYSEX_CMD_REPLACE_CURRENT_PATCH, synth_index, 0x00]
    )
    return header + patch_bytes + bytes([0xF7])


def load_syx_patch_from_bytes(syx_data: bytes) -> dict:
    """Parse .syx patch bytes into parameter dictionary."""
    if len(syx_data) < 10 or syx_data[0] != 0xF0 or syx_data[-1] != 0xF7:
        raise ValueError("Invalid SysEx frame: Missing F0 or F7 boundary.")
    raw_payload = list(syx_data[1:-1])
    return parse_patch_data(raw_payload)


def build_default_patch(name: str = "Init", preset: str = "pad") -> bytes:
    """Build a default synth patch binary."""
    from circuit_tracks.patch_builder import preset_bass, preset_lead, preset_pad, preset_pluck

    presets = {
        "pad": preset_pad,
        "bass": preset_bass,
        "lead": preset_lead,
        "pluck": preset_pluck,
    }
    builder_fn = presets.get(preset.lower(), PatchBuilder)
    builder = builder_fn(name) if builder_fn is not PatchBuilder else PatchBuilder(name)
    return builder.build()


def read_ncs_file(connection, slot: int) -> bytes | None:
    """Read NCS file from connection state."""
    if hasattr(connection, "state"):
        return connection.state.get("slots", {}).get(slot)
    return None


def write_ncs_file(connection, ncs_bytes: bytes, slot: int) -> None:
    """Write NCS file to connection state."""
    if hasattr(connection, "state"):
        if "slots" not in connection.state:
            connection.state["slots"] = {}
        connection.state["slots"][slot] = ncs_bytes


def parse_syx_patch(syx_data: bytes) -> dict:
    """Alias for load_syx_patch_from_bytes."""
    return load_syx_patch_from_bytes(syx_data)


def ncs_bytes_to_song(ncs_bytes: bytes) -> dict:
    """Load NCS bytes and parse into SongData dictionary."""
    ncs = load_ncs_from_bytes(ncs_bytes)
    # Assuming a function ncs_to_song exists or we just return a dict representation
    # For now, returning a basic dict structure
    return {"name": ncs.header.name.strip(), "bpm": ncs.timing.tempo}
