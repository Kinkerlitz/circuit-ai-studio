"""Tests for MIDI Pattern Playback Engine."""

import pytest
from src.bridge.midi_detector import MockCircuitTracksConnection
from src.bridge.player import MidiPatternPlayer, TRACK_CHANNELS, DRUM_NOTES


@pytest.fixture
def mock_connection():
    return MockCircuitTracksConnection()


@pytest.fixture
def player(mock_connection):
    return MidiPatternPlayer(connection=mock_connection)


def test_track_channel_mapping():
    assert TRACK_CHANNELS["synth1"] == 0
    assert TRACK_CHANNELS["synth2"] == 1
    assert TRACK_CHANNELS["drum1"] == 9
    assert TRACK_CHANNELS["drum4"] == 9
    assert DRUM_NOTES["drum1"] == 60


def test_play_step_triggers_notes(player, mock_connection):
    tracks = {
        "synth1": {
            "length": 16,
            "steps": {"0": {"note": 60, "velocity": 100}},
        },
        "drum1": {
            "length": 16,
            "steps": {"0": {"velocity": 120}},
        },
    }

    events = player.play_step(tracks, step_idx=0)
    assert len(events) == 2

    synth_event = next(e for e in events if e["track"] == "synth1")
    assert synth_event["channel"] == 0
    assert synth_event["note"] == 60
    assert synth_event["velocity"] == 100

    drum_event = next(e for e in events if e["track"] == "drum1")
    assert drum_event["channel"] == 9
    assert drum_event["note"] == 60
    assert drum_event["velocity"] == 120

    # Ensure messages reached mock connection
    note_ons = [m for m in mock_connection.sent_messages if m.get("type") == "note_on"]
    assert len(note_ons) == 2


def test_play_song_loops(player, mock_connection):
    song = {
        "bpm": 600,  # fast BPM for quick unit test execution
        "patterns": {
            "p1": {
                "tracks": {
                    "synth1": {
                        "length": 4,
                        "steps": {
                            "0": {"note": 60},
                            "2": {"note": 64},
                        },
                    }
                }
            }
        },
    }

    step_records = []

    def on_step(loop, step):
        step_records.append((loop, step))

    player.play_song(song, pattern_name="p1", loops=2, on_step=on_step, blocking=True)

    assert len(step_records) == 8  # 4 steps x 2 loops
    assert player.is_playing is False

    # Check all_notes_off was called at the end
    all_offs = [m for m in mock_connection.sent_messages if m.get("type") == "all_notes_off"]
    assert len(all_offs) > 0


def test_player_stop(player, mock_connection):
    player.stop()
    assert player.is_playing is False


def test_player_silence_all_sends_stop_and_sound_off(player, mock_connection):
    player.stop()

    # Check that realtime stop was dispatched
    realtime_msgs = [
        m for m in mock_connection.sent_messages
        if m.get("type") == "realtime" and m.get("msg_type") == "stop"
    ]
    assert len(realtime_msgs) >= 1

    # Check that CC 120 (All Sound Off) and CC 123 (All Notes Off) were sent
    cc_msgs = [m for m in mock_connection.sent_messages if m.get("type") == "control_change"]
    cc_120 = [m for m in cc_msgs if m.get("control") == 120]
    cc_123 = [m for m in cc_msgs if m.get("control") == 123]
    assert len(cc_120) > 0
    assert len(cc_123) > 0
