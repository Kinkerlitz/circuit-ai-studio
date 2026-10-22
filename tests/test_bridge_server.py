"""Tests for FastAPI/WebSocket Hardware Bridge Server and Safe-Slot-64 verification."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.bridge.server import SAFE_VERIFY_SLOT, app, bridge
from src.core.wrapper import build_default_patch, create_empty_ncs, song_to_ncs_bytes


@pytest.fixture(autouse=True)
def setup_bridge():
    bridge.force_mock = True
    bridge.initialize()
    yield
    bridge.shutdown()


def test_status_endpoint():
    with TestClient(app) as client:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert data["connected"] is True
        assert data["is_mock"] is True


def test_midi_note_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/midi/note",
            json={"channel": 0, "note": 60, "velocity": 110, "duration_s": 0.05},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_midi_cc_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/midi/cc",
            json={"channel": 0, "control": 74, "value": 85},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_midi_realtime_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/midi/realtime",
            json={"command": "start"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_session_upload_safe_slot_64_verified():
    empty_ncs = create_empty_ncs()
    ncs_bytes = empty_ncs.save_to_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/session/upload",
            json={
                "slot": SAFE_VERIFY_SLOT,
                "ncs_hex": ncs_bytes.hex(),
                "verify": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["slot"] == 64
        assert data["verified"] is True
        assert data["bytes_length"] == 160780


def test_session_upload_with_song_dict():
    empty_ncs = create_empty_ncs()
    song_dict = empty_ncs.song.to_dict()

    with TestClient(app) as client:
        response = client.post(
            "/session/upload",
            json={
                "slot": 1,
                "song_dict": song_dict,
                "verify": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["slot"] == 1


def test_session_upload_invalid_bytes():
    with TestClient(app) as client:
        # Invalid corrupt data failing offline RAM validation
        response = client.post(
            "/session/upload",
            json={
                "slot": 1,
                "ncs_hex": "deadbeefcafebabe",
                "verify": True,
            },
        )
        assert response.status_code == 422


def test_patch_upload():
    patch_bytes = build_default_patch(name="BassInit", preset="bass")
    with TestClient(app) as client:
        response = client.post(
            "/patch/upload",
            json={
                "synth": 1,
                "slot": 5,
                "patch_hex": patch_bytes.hex(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["synth"] == 1
        assert data["slot"] == 5
        assert data["bytes"] == 340


def test_websocket_connection_and_broadcast():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            initial = ws.receive_json()
            assert initial["type"] == "status"
            assert initial["data"]["connected"] is True

            # Trigger a CC event via HTTP and assert WebSocket receives broadcast
            post_res = client.post(
                "/midi/cc",
                json={"channel": 1, "control": 19, "value": 100},
            )
            assert post_res.status_code == 200

            event = ws.receive_json()
            assert event["type"] == "control_change"
            assert event["data"]["control"] == 19
            assert event["data"]["value"] == 100
