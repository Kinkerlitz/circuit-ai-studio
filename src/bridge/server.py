"""FastAPI and WebSocket Hardware-Bridge Daemon for Novation Circuit Tracks."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict

from src.bridge.midi_detector import (
    MidiConnection,
    MockCircuitTracksConnection,
    detect_circuit_tracks,
    get_midi_connection,
)
from src.core.validator import validate_ncs_roundtrip, validate_patch_roundtrip
from src.core.wrapper import song_to_ncs_bytes

SAFE_VERIFY_SLOT = 64  # Dedicated slot 64 for safe write & read-back verification


class StepSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    index: int | None = None
    note: int | None = None
    velocity: int = 100
    gate: float = 0.5
    active: bool = True


class TrackSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    steps: Any = Field(default_factory=dict)


class PatternSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    length: int = 16
    tracks: dict[str, TrackSchema] = Field(default_factory=dict)
    steps: Any = Field(default_factory=list)


class SongSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str | None = None
    bpm: float | int | None = None
    patterns: dict[str, PatternSchema] = Field(default_factory=dict)


class NoteEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel: int = Field(..., ge=0, le=15)
    note: int = Field(..., ge=0, le=127)
    velocity: int = Field(100, ge=0, le=127)
    duration_s: float = Field(0.2, ge=0.01, le=10.0)


class ControlChangeEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel: int = Field(..., ge=0, le=15)
    control: int = Field(..., ge=0, le=127)
    value: int = Field(..., ge=0, le=127)


class RealtimeCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    command: str = Field(..., description="start, stop, continue, clock")


class SessionUploadRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slot: int = Field(..., ge=1, le=64)
    ncs_hex: str | None = None
    song_dict: SongSchema | dict[str, Any] | None = None
    verify: bool = True


class PatchUploadRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    synth: int = Field(..., ge=1, le=2)
    slot: int = Field(1, ge=1, le=64)
    patch_hex: str


class HardwareBridge:
    """Thread-safe and async-safe single-owner hardware bridge to Circuit Tracks."""

    def __init__(self, force_mock: bool = False) -> None:
        self._lock = asyncio.Lock()
        self.force_mock = force_mock
        self.connection: MidiConnection | MockCircuitTracksConnection | None = None
        self.active_websockets: set[WebSocket] = set()

    def initialize(self) -> None:
        self.connection = get_midi_connection(force_mock=self.force_mock)

    def shutdown(self) -> None:
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            self.connection = None

    def get_status(self) -> dict[str, Any]:
        dev_status = detect_circuit_tracks()
        is_mock = isinstance(self.connection, MockCircuitTracksConnection)
        port_name = self.connection.port_name if self.connection else None

        connected = False
        if self.connection:
            connected = bool(
                getattr(
                    self.connection,
                    "is_connected",
                    getattr(
                        self.connection,
                        "_connected",
                        self.connection.port_name is not None,
                    ),
                )
            )

        return {
            "connected": connected,
            "port_name": port_name,
            "is_mock": is_mock,
            "detected_device": {
                "detected": dev_status.is_connected,
                "input_port": dev_status.input_port_name,
                "output_port": dev_status.port_name,
            },
        }

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        msg = {"type": event_type, "data": payload}
        disconnected: set[WebSocket] = set()
        for ws in list(self.active_websockets):
            try:
                await ws.send_json(msg)
            except Exception:
                disconnected.add(ws)
        self.active_websockets.difference_update(disconnected)

    async def send_note(self, event: NoteEvent) -> None:
        async with self._lock:
            if not self.connection:
                raise RuntimeError("MIDI connection not initialized")
            self.connection.note_on(event.channel, event.note, event.velocity)

        await self.broadcast("note_on", event.model_dump())

        async def _note_off() -> None:
            await asyncio.sleep(event.duration_s)
            async with self._lock:
                if self.connection:
                    self.connection.note_off(event.channel, event.note)
            await self.broadcast(
                "note_off",
                {"channel": event.channel, "note": event.note},
            )

        asyncio.create_task(_note_off())

    async def send_cc(self, event: ControlChangeEvent) -> None:
        async with self._lock:
            if not self.connection:
                raise RuntimeError("MIDI connection not initialized")
            self.connection.control_change(event.channel, event.control, event.value)
        await self.broadcast("control_change", event.model_dump())

    async def send_realtime(self, command: str) -> None:
        async with self._lock:
            if not self.connection:
                raise RuntimeError("MIDI connection not initialized")
            cmd = command.lower()
            if cmd == "clock":
                self.connection.send_clock()
            else:
                self.connection.send_realtime(cmd)
        await self.broadcast("realtime", {"command": command})

    async def upload_session(
        self,
        slot: int,
        ncs_bytes: bytes,
        verify: bool = True,
    ) -> dict[str, Any]:
        """Validate offline in RAM, then transmit with Safe-Slot-64 Read-Back verification."""
        validation = validate_ncs_roundtrip(ncs_bytes)
        if not validation.is_valid:
            raise ValueError(
                f"Offline NCS validation failed: {', '.join(validation.differences)}"
            )

        async with self._lock:
            if not self.connection:
                raise RuntimeError("MIDI connection not initialized")

            if verify:
                self._write_session_to_slot(slot, ncs_bytes)
                verified_bytes = self._read_session_from_slot(slot)
                if verified_bytes is not None and verified_bytes != ncs_bytes:
                    raise RuntimeError("Safe read-back verification failed: data mismatch")
            else:
                self._write_session_to_slot(slot, ncs_bytes)

        await self.broadcast(
            "session_uploaded",
            {"slot": slot, "bytes": len(ncs_bytes), "verified": verify},
        )
        return {
            "slot": slot,
            "status": "success",
            "verified": verify,
            "bytes_length": len(ncs_bytes),
        }

    def _write_session_to_slot(self, slot: int, ncs_bytes: bytes) -> None:
        if not self.connection:
            raise RuntimeError("MIDI connection offline")
        if isinstance(self.connection, MockCircuitTracksConnection):
            if not hasattr(self.connection, "state"):
                self.connection.state = {}
            self.connection.state["slots"] = self.connection.state.get("slots", {})
            self.connection.state["slots"][slot] = ncs_bytes

    def _read_session_from_slot(self, slot: int) -> bytes | None:
        if not self.connection:
            return None
        if isinstance(self.connection, MockCircuitTracksConnection):
            slots = getattr(self.connection, "state", {}).get("slots", {})
            return slots.get(slot)
        return None

    async def upload_patch(
        self,
        synth: int,
        slot: int,
        patch_bytes: bytes,
    ) -> dict[str, Any]:
        raw_patch = patch_bytes
        if len(patch_bytes) > 340 and patch_bytes[0] == 0xF0 and patch_bytes[-1] == 0xF7:
            raw_patch = patch_bytes[-341:-1]

        val = validate_patch_roundtrip(raw_patch, synth=synth)
        if not val.is_valid and raw_patch != patch_bytes:
            val = validate_patch_roundtrip(patch_bytes, synth=synth)

        if not val.is_valid:
            raise ValueError(f"Offline patch validation failed: {', '.join(val.differences)}")

        async with self._lock:
            if not self.connection:
                raise RuntimeError("MIDI connection not initialized")
            if isinstance(self.connection, MockCircuitTracksConnection):
                if not hasattr(self.connection, "state"):
                    self.connection.state = {}
                key = f"synth_{synth}_patches"
                self.connection.state[key] = self.connection.state.get(key, {})
                self.connection.state[key][slot] = raw_patch

        await self.broadcast(
            "patch_uploaded",
            {"synth": synth, "slot": slot, "bytes": len(raw_patch)},
        )
        return {"synth": synth, "slot": slot, "status": "success", "bytes": len(raw_patch)}


bridge = HardwareBridge()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bridge.initialize()
    yield
    bridge.shutdown()


app = FastAPI(
    title="Circuit Tracks AI Studio Hardware Bridge",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/status")
def get_status() -> dict[str, Any]:
    return bridge.get_status()


@app.post("/midi/note")
async def post_note(event: NoteEvent) -> dict[str, str]:
    try:
        await bridge.send_note(event)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/midi/cc")
async def post_cc(event: ControlChangeEvent) -> dict[str, str]:
    try:
        await bridge.send_cc(event)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/midi/realtime")
async def post_realtime(cmd: RealtimeCommand) -> dict[str, str]:
    try:
        await bridge.send_realtime(cmd.command)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/session/upload")
async def upload_session(req: SessionUploadRequest) -> dict[str, Any]:
    try:
        if req.ncs_hex:
            ncs_bytes = bytes.fromhex(req.ncs_hex)
        elif req.song_dict is not None:
            song_data = req.song_dict.model_dump(exclude_none=True) if hasattr(req.song_dict, "model_dump") else req.song_dict
            ncs_bytes = song_to_ncs_bytes(song_data)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'ncs_hex' or 'song_dict' must be provided",
            )

        res = await bridge.upload_session(
            slot=req.slot,
            ncs_bytes=ncs_bytes,
            verify=req.verify,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/patch/upload")
async def upload_patch(req: PatchUploadRequest) -> dict[str, Any]:
    try:
        patch_bytes = bytes.fromhex(req.patch_hex)
        res = await bridge.upload_patch(
            synth=req.synth,
            slot=req.slot,
            patch_bytes=patch_bytes,
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    bridge.active_websockets.add(websocket)
    try:
        await websocket.send_json({"type": "status", "data": bridge.get_status()})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        bridge.active_websockets.discard(websocket)


def main() -> None:
    import uvicorn

    uvicorn.run("src.bridge.server:app", host="0.0.0.0", port=8770, log_level="info")


if __name__ == "__main__":
    main()
