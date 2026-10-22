"""Tests for core modules (DSL, validator, wrapper)."""

import pytest

from circuit_tracks.ncs_parser import serialize_ncs
from src.core.dsl import FirmwareProfile, PatternDSLCompiler, compile_dsl_to_song
from src.core.validator import validate_ncs_roundtrip, validate_patch_roundtrip
from src.core.wrapper import build_default_patch, create_empty_ncs


def test_dsl_mini_notation():
    """Test parsing of tidal-style mini notation."""
    compiler = PatternDSLCompiler()
    steps = compiler.parse_mini_notation("x . C4 [E4,G4] x@2", 5)
    
    assert 0 in steps
    assert steps[0]["note"] == 60
    assert 1 not in steps  # Rest
    assert 2 in steps
    assert steps[2]["note"] == 60  # C4
    assert 3 in steps
    assert "notes" in steps[3]
    assert steps[3]["notes"] == [64, 67]  # E4, G4
    assert 4 in steps
    assert steps[4]["micro_step"] == 2


def test_dsl_compile_song():
    """Test compiling a high-level DSL dict into a song dict."""
    dsl = {
        "name": "TestSong",
        "tracks": {
            "synth1": {"mini": "C4 D4 E4 F4", "length": 4},
            "drum1": {"mini": "x . x .", "length": 4}
        }
    }
    song = compile_dsl_to_song(dsl)
    
    assert song["name"] == "TestSong"
    assert "p1" in song["patterns"]
    assert "synth1" in song["patterns"]["p1"]["tracks"]
    assert "drum1" in song["patterns"]["p1"]["tracks"]
    
    # Verify drum note stripping in stock firmware
    drum_steps = song["patterns"]["p1"]["tracks"]["drum1"]["steps"]
    assert "0" in drum_steps
    assert "note" not in drum_steps["0"]


def test_dsl_compile_hacks_rc0s():
    """Test custom firmware profile for chromatic drums."""
    dsl = {
        "tracks": {
            "drum1": {"mini": "C4 D4", "length": 2}
        }
    }
    song = compile_dsl_to_song(dsl, firmware_profile=FirmwareProfile.HACKS_RC0S)
    drum_steps = song["patterns"]["p1"]["tracks"]["drum1"]["steps"]
    
    assert "0" in drum_steps
    assert drum_steps["0"]["sample_pitch"] == 64  # C4 mapped to center pitch
    assert "1" in drum_steps
    assert drum_steps["1"]["sample_pitch"] == 66  # D4 mapped to +2


def test_validator_patch_roundtrip():
    """Test in-memory validation of a generated patch."""
    patch_bytes = build_default_patch("TestBass", "bass")
    result = validate_patch_roundtrip(patch_bytes)
    
    assert result.is_valid
    assert result.patch_size == 340
    assert result.name.strip("\x00").strip() == "TestBass"


def test_validator_ncs_roundtrip():
    """Test in-memory validation of an NCS session."""
    ncs = create_empty_ncs()
    ncs_bytes = serialize_ncs(ncs)
    result = validate_ncs_roundtrip(ncs_bytes)
    
    assert result.is_valid
    assert result.byte_size == 160780
