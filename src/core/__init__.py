"""Core module for Circuit Tracks NCS/SYX compilation and validation."""

from src.core.dsl import (
    FirmwareProfile,
    PatternDSLCompiler,
    PatternDSLTrack,
    compile_dsl_to_song,
)
from src.core.validator import (
    NCSValidationResult,
    PatchValidationResult,
    validate_ncs_roundtrip,
    validate_patch_roundtrip,
)
from src.core.wrapper import (
    create_empty_ncs,
    load_ncs_from_bytes,
    load_syx_patch_from_bytes,
    patch_to_syx,
    song_to_ncs_bytes,
)

__all__ = [
    "FirmwareProfile",
    "NCSValidationResult",
    "PatchValidationResult",
    "PatternDSLCompiler",
    "PatternDSLTrack",
    "compile_dsl_to_song",
    "create_empty_ncs",
    "load_ncs_from_bytes",
    "load_syx_patch_from_bytes",
    "patch_to_syx",
    "song_to_ncs_bytes",
    "validate_ncs_roundtrip",
    "validate_patch_roundtrip",
]
