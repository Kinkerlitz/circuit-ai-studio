"""Base setup and import verification tests."""

import pytest


def test_core_imports():
    """Verify that all vendor and src modules can be cleanly imported."""
    import circuit_tracks
    from circuit_tracks.constants import SYNTH1_CHANNEL
    from circuit_tracks.ncs_parser import NCS_FILE_SIZE
    from circuit_tracks.patch_builder import PatchBuilder
    from src.bridge.midi_detector import detect_circuit_tracks, get_midi_connection
    from src.core.dsl import PatternDSLCompiler
    from src.core.validator import validate_ncs_roundtrip
    from src.core.wrapper import create_empty_ncs

    assert SYNTH1_CHANNEL == 0
    assert NCS_FILE_SIZE == 160780
    assert PatchBuilder is not None


def test_empty_template_existence():
    """Verify vendor template Empty.ncs is present and has the exact required size."""
    from src.core.wrapper import VENDOR_TEMPLATE

    assert VENDOR_TEMPLATE.exists()
    assert VENDOR_TEMPLATE.stat().st_size == 160780
