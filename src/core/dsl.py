"""High-Level Pattern DSL Compiler for Novation Circuit Tracks."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from circuit_tracks.song import parse_song
from src.core.wrapper import song_to_ncs_bytes


class FirmwareProfile(str, Enum):
    STOCK = "stock"
    HACKS_RC0S = "hacks_rc0s"


@dataclass
class PatternDSLTrack:
    name: str
    length: int = 16  # Polyrhythmic track length (1-32)
    mini_notation: str | None = None
    steps: dict[int, dict[str, Any]] = field(default_factory=dict)
    macros: dict[str, dict[str, int]] = field(default_factory=dict)
    mixer: dict[str, dict[str, int]] = field(default_factory=dict)
    params: dict[str, dict[str, int]] = field(default_factory=dict)


class PatternDSLCompiler:
    """Translates declarative compact DSL structures into validated Circuit Tracks sessions."""

    def __init__(self, firmware_profile: FirmwareProfile = FirmwareProfile.STOCK) -> None:
        self.firmware_profile = firmware_profile

    def parse_mini_notation(self, notation: str, length: int) -> dict[int, dict[str, Any]]:
        """Parse tidal-style mini notation strings into discrete steps.

        Syntax:
        - '.' or '~' : Rest / silence
        - 'x' / 'X' : Default trigger
        - '60' or 'C4' : Explicit note
        - 'x(vel=80,gate=1.5,prob=0.8)' : Parameterized step
        - '[C4,E4,G4]' : Polyphonic chord
        - Tokens can have microstep suffix '@m' where m is 0..5
        """
        raw_tokens = [tok for tok in notation.strip().split() if tok]
        if not raw_tokens:
            return {}

        steps: dict[int, dict[str, Any]] = {}
        token_count = len(raw_tokens)

        for step_idx in range(length):
            # Map step_idx to mini token if token count differs (wrap or stretch)
            token = raw_tokens[step_idx % token_count]
            if token in (".", "~", "-"):
                continue

            parsed_step = self._parse_single_token(token)
            if parsed_step:
                steps[step_idx] = parsed_step

        return steps

    def _parse_note_str(self, note_val: str) -> int:
        if note_val.isdigit():
            return int(note_val)

        match = re.match(r"^([A-Ga-g])(#|b)?(-?\d+)$", note_val)
        if not match:
            return 60

        name, accidental, octave_str = match.groups()
        base_notes = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
        semi = base_notes[name.lower()]
        if accidental == "#":
            semi += 1
        elif accidental == "b":
            semi -= 1
        octave = int(octave_str)
        # MIDI note: C-1=0, C0=12, C4=60
        midi_note = (octave + 1) * 12 + semi
        return max(0, min(127, midi_note))

    def _parse_single_token(self, token: str) -> dict[str, Any]:
        """Extract note, chord, micro_step, velocity, gate, probability, and p-locks."""
        step: dict[str, Any] = {"velocity": 100, "enabled": True}

        # Check for microstep suffix e.g. x@2 or C4@3
        if "@" in token:
            token, micro_s = token.split("@", 1)
            try:
                step["micro_step"] = max(0, min(5, int(micro_s)))
            except ValueError:
                pass

        # Check for parameters inside parenthesis e.g. token(...)
        param_dict: dict[str, str] = {}
        paren_match = re.search(r"\((.*?)\)", token)
        if paren_match:
            params_str = paren_match.group(1)
            token = token[: paren_match.start()]
            for item in params_str.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    param_dict[k.strip().lower()] = v.strip()

        # Parse chord notation [N1,N2,N3]
        if token.startswith("[") and token.endswith("]"):
            chord_str = token[1:-1]
            notes = [self._parse_note_str(n.strip()) for n in chord_str.split(",") if n.strip()]
            step["notes"] = notes
        elif token.lower() in ("x", "hit"):
            step["note"] = 60
        elif token:
            step["note"] = self._parse_note_str(token)

        # Apply parameters
        if "vel" in param_dict:
            step["velocity"] = max(0, min(127, int(param_dict["vel"])))
        if "velocity" in param_dict:
            step["velocity"] = max(0, min(127, int(param_dict["velocity"])))
        if "gate" in param_dict:
            step["gate"] = max(0.0, min(16.0, float(param_dict["gate"])))
        if "prob" in param_dict:
            step["probability"] = max(0.0, min(1.0, float(param_dict["prob"])))
        if "tie" in param_dict:
            step["tie"] = param_dict["tie"].lower() in ("true", "1", "yes")
        if "sample" in param_dict:
            step["sample"] = max(0, min(63, int(param_dict["sample"])))

        # Synth macro p-locks inside token parameters, e.g. m1=80, m5=120
        macro_locks: dict[str, int] = {}
        for k, v in param_dict.items():
            if k.startswith("m") and k[1:].isdigit():
                num = k[1:]
                if 1 <= int(num) <= 8:
                    macro_locks[num] = max(0, min(127, int(v)))
            elif k.startswith("macro") and k[5:].isdigit():
                num = k[5:]
                if 1 <= int(num) <= 8:
                    macro_locks[num] = max(0, min(127, int(v)))

        if macro_locks:
            step["macros"] = macro_locks

        return step

    def compile(self, session_def: dict[str, Any]) -> dict[str, Any]:
        """Compile high-level DSL structure into standard circuit_tracks song dict."""
        name = session_def.get("name", "DSL_Pattern")
        bpm = session_def.get("bpm", 120)
        swing = session_def.get("swing", 50)
        color = session_def.get("color", 8)
        scale_root = session_def.get("scale_root", "C")
        scale_type = session_def.get("scale_type", "chromatic")

        patterns_in = session_def.get("patterns", {})
        if not patterns_in:
            # Single implicit pattern from tracks root
            tracks_root = session_def.get("tracks", {})
            patterns_in = {"p1": {"tracks": tracks_root, "length": session_def.get("length", 16)}}

        compiled_patterns: dict[str, Any] = {}

        for pat_name, pat_content in patterns_in.items():
            pat_length = pat_content.get("length", 16)
            pat_tracks = pat_content.get("tracks", {})
            compiled_tracks: dict[str, Any] = {}

            for track_name, track_val in pat_tracks.items():
                is_drum = track_name.startswith("drum")
                track_len = track_val.get("length", pat_length)

                # Steps resolution
                steps_out: dict[str, Any] = {}
                mini_str = track_val.get("mini") or track_val.get("mini_notation")
                if mini_str:
                    mini_steps = self.parse_mini_notation(mini_str, track_len)
                    for k, v in mini_steps.items():
                        steps_out[str(k)] = copy.deepcopy(v)

                explicit_steps = track_val.get("steps", {})
                for k, v in explicit_steps.items():
                    steps_out[str(k)] = copy.deepcopy(v)

                # Handle Custom Firmware (hacks_rc0s): Chromatic Drum support
                if is_drum:
                    for s_k, s_v in list(steps_out.items()):
                        # In stock firmware, drum steps do not support 'note'
                        if self.firmware_profile == FirmwareProfile.STOCK:
                            s_v.pop("note", None)
                            s_v.pop("notes", None)
                            s_v.pop("gate", None)
                            s_v.pop("tie", None)
                        elif self.firmware_profile == FirmwareProfile.HACKS_RC0S:
                            # hacks_rc0s allows pitch offsets / chromatic mapping via sample pitch
                            note_val = None
                            if "note" in s_v:
                                raw_n = s_v.pop("note")
                                note_val = self._parse_note_str(str(raw_n)) if not isinstance(raw_n, int) else raw_n
                            elif "notes" in s_v and s_v["notes"]:
                                raw_n = s_v.pop("notes")[0]
                                note_val = self._parse_note_str(str(raw_n)) if not isinstance(raw_n, int) else raw_n

                            if note_val is not None:
                                # Map note 60 (C4 center) to pitch 64
                                s_v["sample_pitch"] = max(0, min(127, 64 + (note_val - 60)))
                            s_v.pop("notes", None)
                            s_v.pop("gate", None)
                            s_v.pop("tie", None)

                compiled_track: dict[str, Any] = {
                    "steps": {k: v for k, v in steps_out.items() if int(k) < 32}
                }

                if not is_drum:
                    if "macros" in track_val:
                        compiled_track["macros"] = track_val["macros"]
                    if "mixer" in track_val:
                        compiled_track["mixer"] = track_val["mixer"]
                else:
                    if "params" in track_val:
                        compiled_track["params"] = track_val["params"]

                compiled_tracks[track_name] = compiled_track

            compiled_patterns[pat_name] = {
                "length": max(1, min(32, pat_length)),
                "tracks": compiled_tracks,
            }

        result_song: dict[str, Any] = {
            "name": name,
            "bpm": bpm,
            "swing": swing,
            "color": color,
            "scale": {"root": scale_root, "type": scale_type},
            "patterns": compiled_patterns,
        }

        if "sounds" in session_def:
            result_song["sounds"] = session_def["sounds"]
        if "fx" in session_def:
            result_song["fx"] = session_def["fx"]
        if "mixer" in session_def:
            result_song["mixer"] = session_def["mixer"]
        if "song" in session_def:
            result_song["song"] = session_def["song"]
        else:
            result_song["song"] = list(compiled_patterns.keys())[:16]

        return result_song


def compile_dsl_to_song(
    dsl_definition: dict[str, Any],
    firmware_profile: FirmwareProfile = FirmwareProfile.STOCK,
) -> dict[str, Any]:
    """Compile DSL dictionary into fully validated Circuit Tracks song schema dictionary."""
    compiler = PatternDSLCompiler(firmware_profile=firmware_profile)
    return compiler.compile(dsl_definition)


def compile_dsl_to_ncs_bytes(
    dsl_definition: dict[str, Any],
    firmware_profile: FirmwareProfile = FirmwareProfile.STOCK,
) -> bytes:
    """Compile DSL dictionary directly to validated 160,780-byte NCS binary."""
    song_dict = compile_dsl_to_song(dsl_definition, firmware_profile=firmware_profile)
    return song_to_ncs_bytes(song_dict)
