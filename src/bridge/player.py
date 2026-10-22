"""MIDI pattern playback engine for streaming DSL sequences to Circuit Tracks hardware."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from src.bridge.midi_detector import get_midi_connection

logger = logging.getLogger(__name__)

# Standard Circuit Tracks MIDI Channels (0-indexed: 0..15)
# Synth 1 = Ch 1 (0), Synth 2 = Ch 2 (1), Drums 1-4 = Ch 10 (9)
TRACK_CHANNELS: Dict[str, int] = {
    "synth1": 0,
    "synth2": 1,
    "drum1": 9,
    "drum2": 9,
    "drum3": 9,
    "drum4": 9,
    "midi1": 2,
    "midi2": 3,
}

# Default MIDI note triggers for drum tracks on channel 10
DRUM_NOTES: Dict[str, int] = {
    "drum1": 60,  # C3
    "drum2": 62,  # D3
    "drum3": 64,  # E3
    "drum4": 65,  # F3
}


class MidiPatternPlayer:
    """Streams compiled Song/Pattern steps to Circuit Tracks or mock connection."""

    def __init__(self, connection: Any = None):
        self.connection = connection or get_midi_connection()
        self._is_playing = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def stop(self) -> None:
        """Stop playback and send all-notes-off to active channels."""
        self._stop_event.set()
        self._is_playing = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._silence_all()

    def _silence_all(self) -> None:
        for ch in {0, 1, 9}:
            try:
                self.connection.all_notes_off(ch)
            except Exception as exc:
                logger.debug("Error sending all_notes_off on channel %d: %s", ch, exc)

    def play_step(
        self,
        tracks: Dict[str, Any],
        step_idx: int,
        duration_s: float = 0.1,
    ) -> list[Dict[str, Any]]:
        """Trigger notes for a specific 16th step index across tracks.

        Returns:
            List of triggered note events.
        """
        triggered_events = []
        for track_name, track_data in tracks.items():
            track_length = track_data.get("length", 16)
            effective_step = step_idx % track_length
            steps_dict = track_data.get("steps", {})
            step_key = str(effective_step)

            if step_key not in steps_dict:
                continue

            step = steps_dict[step_key]
            channel = TRACK_CHANNELS.get(track_name.lower(), 0)

            # Determine note
            if "notes" in step and isinstance(step["notes"], list):
                notes_to_play = step["notes"]
            elif "note" in step:
                notes_to_play = [step["note"]]
            elif track_name.lower() in DRUM_NOTES:
                notes_to_play = [DRUM_NOTES[track_name.lower()]]
            else:
                notes_to_play = [60]

            velocity = int(step.get("velocity", 100))

            for n in notes_to_play:
                try:
                    self.connection.note_on(channel=channel, note=int(n), velocity=velocity)
                except Exception as exc:
                    logger.warning("Failed to send note_on: %s", exc)

                triggered_events.append(
                    {
                        "track": track_name,
                        "channel": channel,
                        "note": int(n),
                        "velocity": velocity,
                        "step": effective_step,
                    }
                )

        return triggered_events

    def play_song(
        self,
        song: Dict[str, Any],
        pattern_name: str = "p1",
        loops: int = 1,
        on_step: Optional[Callable[[int, int], None]] = None,
        blocking: bool = False,
    ) -> None:
        """Start streaming a song pattern in a background thread or blocking."""
        self.stop()
        self._stop_event.clear()

        def _worker() -> None:
            self._is_playing = True
            try:
                bpm = float(song.get("bpm", 120))
                # 16th-note interval in seconds: (60.0 / bpm) / 4
                step_duration = (60.0 / bpm) / 4.0
                tracks = (
                    song.get("patterns", {})
                    .get(pattern_name, {})
                    .get("tracks", {})
                )

                # Determine overall sequence length (max length among tracks or 16)
                max_len = max(
                    (t.get("length", 16) for t in tracks.values()),
                    default=16,
                )

                loop_count = 0
                while not self._stop_event.is_set():
                    for current_step in range(max_len):
                        if self._stop_event.is_set():
                            break

                        step_start = time.perf_counter()
                        self.play_step(tracks, current_step, duration_s=step_duration * 0.8)

                        if on_step:
                            try:
                                on_step(loop_count, current_step)
                            except Exception:
                                pass

                        # Precise wait for next 16th-note step
                        elapsed = time.perf_counter() - step_start
                        remaining = step_duration - elapsed
                        if remaining > 0:
                            time.sleep(remaining)

                        # Turn notes off before next step
                        for ch in {0, 1, 9}:
                            try:
                                self.connection.all_notes_off(ch)
                            except Exception:
                                pass

                    loop_count += 1
                    if loops > 0 and loop_count >= loops:
                        break
            finally:
                self._silence_all()
                self._is_playing = False

        if blocking:
            _worker()
        else:
            self._thread = threading.Thread(target=_worker, daemon=True)
            self._thread.start()
