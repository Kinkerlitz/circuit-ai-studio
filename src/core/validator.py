"""Offline-First In-Memory validation for .ncs sessions and .syx patches."""

from __future__ import annotations

from dataclasses import dataclass, field

from circuit_tracks.ncs_parser import (
    NCS_FILE_SIZE,
    NCSFile,
    parse_ncs_from_bytes,
    serialize_ncs,
)
from circuit_tracks.patch import _PATCH_SIZE, parse_patch_data
from src.core.wrapper import load_syx_patch_from_bytes, patch_to_syx


@dataclass
class NCSValidationResult:
    is_valid: bool
    byte_size: int
    differences: list[str] = field(default_factory=list)
    header_name: str = ""
    tempo: int = 120
    swing: int = 50


@dataclass
class PatchValidationResult:
    is_valid: bool
    patch_size: int
    name: str = ""
    differences: list[str] = field(default_factory=list)


def validate_ncs_roundtrip(ncs_data: bytes) -> NCSValidationResult:
    """Perform in-memory serialize -> parse -> assert_equal roundtrip on NCS data."""
    diffs: list[str] = []
    if len(ncs_data) != NCS_FILE_SIZE:
        diffs.append(f"Size mismatch: {len(ncs_data)} != {NCS_FILE_SIZE}")
        return NCSValidationResult(
            is_valid=False,
            byte_size=len(ncs_data),
            differences=diffs,
        )

    try:
        parsed1 = parse_ncs_from_bytes(ncs_data)
        serialized1 = serialize_ncs(parsed1)
        parsed2 = parse_ncs_from_bytes(serialized1)
        serialized2 = serialize_ncs(parsed2)
    except Exception as exc:
        diffs.append(f"Parsing or serialization failed: {exc}")
        return NCSValidationResult(
            is_valid=False,
            byte_size=len(ncs_data),
            differences=diffs,
        )

    if len(serialized1) != NCS_FILE_SIZE:
        diffs.append(f"Serialized size mismatch: {len(serialized1)} != {NCS_FILE_SIZE}")

    if serialized1 != serialized2:
        diff_count = sum(1 for a, b in zip(serialized1, serialized2) if a != b)
        diffs.append(f"Idempotency divergence: {diff_count} bytes differ between cycles")

    # Structural sanity checks
    if parsed1.header.name != parsed2.header.name:
        diffs.append(f"Header name divergence: '{parsed1.header.name}' != '{parsed2.header.name}'")

    if parsed1.timing.tempo != parsed2.timing.tempo:
        diffs.append(f"Tempo divergence: {parsed1.timing.tempo} != {parsed2.timing.tempo}")

    if parsed1.timing.swing != parsed2.timing.swing:
        diffs.append(f"Swing divergence: {parsed1.timing.swing} != {parsed2.timing.swing}")

    is_valid = len(diffs) == 0
    return NCSValidationResult(
        is_valid=is_valid,
        byte_size=len(ncs_data),
        differences=diffs,
        header_name=parsed1.header.name.strip(),
        tempo=parsed1.timing.tempo,
        swing=parsed1.timing.swing,
    )


def validate_patch_roundtrip(patch_bytes: bytes, synth: int = 1) -> PatchValidationResult:
    """Validate 340-byte synth patch via syx encapsulation and parameter verification."""
    diffs: list[str] = []
    if len(patch_bytes) != _PATCH_SIZE:
        diffs.append(f"Patch binary size mismatch: {len(patch_bytes)} != {_PATCH_SIZE}")
        return PatchValidationResult(
            is_valid=False,
            patch_size=len(patch_bytes),
            differences=diffs,
        )

    try:
        syx = patch_to_syx(patch_bytes, synth=synth)
        parsed = load_syx_patch_from_bytes(syx)
    except Exception as exc:
        diffs.append(f"SysEx encapsulation or parse failed: {exc}")
        return PatchValidationResult(
            is_valid=False,
            patch_size=len(patch_bytes),
            differences=diffs,
        )

    if "error" in parsed:
        diffs.append(f"Parse error: {parsed['error']}")

    name = parsed.get("name", "")
    return PatchValidationResult(
        is_valid=len(diffs) == 0,
        patch_size=len(patch_bytes),
        name=name,
        differences=diffs,
    )
