"""Tests for in-memory roundtrip validation of sessions and patches."""

from circuit_tracks.patch_builder import PatchBuilder, preset_pad
from src.core.validator import validate_ncs_roundtrip, validate_patch_roundtrip
from src.core.wrapper import create_empty_ncs, patch_to_syx, song_to_ncs_bytes


def test_empty_ncs_roundtrip_validation():
    from src.core.wrapper import get_template_path

    raw_data = get_template_path().read_bytes()
    result = validate_ncs_roundtrip(raw_data)
    assert result.is_valid, f"Validation failed: {result.differences}"
    assert result.byte_size == 160780


def test_generated_song_ncs_roundtrip_validation():
    song = {
        "name": "TestTrip",
        "bpm": 128,
        "patterns": {
            "pat1": {
                "length": 16,
                "tracks": {
                    "synth1": {
                        "steps": {
                            "0": {"note": 60, "velocity": 100, "gate": 0.5},
                            "4": {"note": 64, "velocity": 100, "gate": 1.0},
                        }
                    },
                    "drum1": {
                        "steps": {
                            "0": {"velocity": 120},
                            "8": {"velocity": 110},
                        }
                    },
                },
            }
        },
    }

    ncs_bytes = song_to_ncs_bytes(song)
    result = validate_ncs_roundtrip(ncs_bytes)
    assert result.is_valid, f"Roundtrip errors: {result.differences}"
    assert result.header_name == "TestTrip"
    assert result.tempo == 128


def test_patch_roundtrip_validation():
    patch_bytes = preset_pad("PadA").build()
    result = validate_patch_roundtrip(patch_bytes)
    assert result.is_valid, f"Patch errors: {result.differences}"
    assert result.name == "PadA"
    assert result.patch_size == 340
