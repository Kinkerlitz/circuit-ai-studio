"""Tests for Pattern DSL compiler, polyrhythms, and firmware profiles."""

from src.core.dsl import (
    FirmwareProfile,
    PatternDSLCompiler,
    compile_dsl_to_ncs_bytes,
    compile_dsl_to_song,
)
from src.core.validator import validate_ncs_roundtrip


def test_dsl_mini_notation_parsing():
    compiler = PatternDSLCompiler()
    notation = "C4 . [E4,G4]@2 x(vel=95,gate=1.5,m1=80)"
    steps = compiler.parse_mini_notation(notation, length=4)

    assert 0 in steps
    assert steps[0]["note"] == 60

    # Step 1 was a dot (silence)
    assert 1 not in steps

    # Step 2 was a chord with microstep @2
    assert 2 in steps
    assert steps[2]["notes"] == [64, 67]
    assert steps[2]["micro_step"] == 2

    # Step 3 was parameterized
    assert 3 in steps
    assert steps[3]["velocity"] == 95
    assert steps[3]["gate"] == 1.5
    assert steps[3]["macros"] == {"1": 80}


def test_dsl_polyrhythmic_compilation():
    dsl = {
        "name": "PolyBeat",
        "bpm": 130,
        "tracks": {
            "synth1": {
                "length": 12,  # Polyrhythmic 12 steps
                "mini": "C3 . Eb3 . G3 . Bb3 . C4 . G3 .",
                "macros": {"5": {"0": 30, "6": 100}},
            },
            "drum1": {
                "length": 16,  # 16 steps kick
                "mini": "x . . . x . . . x . . . x . . .",
            },
        },
    }

    song_dict = compile_dsl_to_song(dsl)
    assert "p1" in song_dict["patterns"]
    pat = song_dict["patterns"]["p1"]
    assert "synth1" in pat["tracks"]
    assert "drum1" in pat["tracks"]
    assert len(pat["tracks"]["synth1"]["steps"]) == 6
    assert len(pat["tracks"]["drum1"]["steps"]) == 4

    # Ensure full NCS generation and validation
    ncs_bytes = compile_dsl_to_ncs_bytes(dsl)
    val = validate_ncs_roundtrip(ncs_bytes)
    assert val.is_valid, f"Roundtrip failed: {val.differences}"
    assert val.header_name == "PolyBeat"
    assert val.tempo == 130


def test_dsl_firmware_profiles():
    dsl = {
        "tracks": {
            "drum1": {
                "length": 4,
                "steps": {
                    "0": {"note": 62, "velocity": 100},
                },
            }
        }
    }

    # Stock strips note from drum steps
    stock_song = compile_dsl_to_song(dsl, firmware_profile=FirmwareProfile.STOCK)
    drum_step_stock = stock_song["patterns"]["p1"]["tracks"]["drum1"]["steps"]["0"]
    assert "note" not in drum_step_stock

    # Hacks RC0s converts chromatic note to sample_pitch
    hacks_song = compile_dsl_to_song(dsl, firmware_profile=FirmwareProfile.HACKS_RC0S)
    drum_step_hacks = hacks_song["patterns"]["p1"]["tracks"]["drum1"]["steps"]["0"]
    assert "sample_pitch" in drum_step_hacks
    assert drum_step_hacks["sample_pitch"] == 66  # 64 + (62 - 60)
