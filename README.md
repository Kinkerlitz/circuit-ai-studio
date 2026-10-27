# Circuit Tracks AI Studio (macOS)

Circuit Tracks AI Studio ist eine professionelle Entwicklungs- und Steuerungsumgebung für die Novation Circuit Tracks Groovebox unter macOS. Es verbindet direkte CoreMIDI- und SysEx-Hardware-Kommunikation mit deklarativer Pattern-DSL, strikter Offline-First-Validierung, einem schnellen FastAPI/WebSocket-Daemon, einem lokalen Model Context Protocol (MCP) Server für KI-gestützte Komposition, einer echtzeitfähigen MIDI-Playback-Engine sowie einem modernen React/Vite Studio Frontend.

---

## 🚀 Projektstatus (Meilensteine 1–6 abgeschlossen)

### ✅ Meilenstein 1: Basis-Setup & CoreMIDI-Detektor
- **CoreMIDI-Hardwareerkennung** (`src/bridge/midi_detector.py`): Automatische Erkennung von USB-Circuit-Tracks-Ports für MIDI-In und Out.
- **Mock-Fallback-Architektur** (`MockCircuitTracksConnection`): Bei nicht angeschlossener Hardware schaltet das System nahtlos in den Mock-Modus um, sodass sämtliche Unit- und Integrationstests sowie Offline-Workflows ohne Hardware lauffähig bleiben.
- **SysEx-Request/Response-Engine**: Unterstützung synchroner und asynchroner SysEx-Handshakes (inkl. Timeouts und Pattern-Matching).

### ✅ Meilenstein 2: In-Memory Roundtrip-Validator, Wrapper & Pattern-DSL
- **NCS- & SYX-Wrapper** (`src/core/wrapper.py`): High-Level-Wrapper um das `.ncs`-Dateiformat (Session-Dateien) und Novation 340-Byte `.syx`-Synth-Patches.
- **Offline-First Validation** (`src/core/validator.py`): Jede generierte Session und jeder Patch wird vor dem Hardware-Versand im RAM durch Re-Parsing validiert (`validate_ncs_roundtrip`, `validate_patch_roundtrip`).
- **High-Level Pattern-DSL & Mini-Notation** (`src/core/dsl.py`):
  - Kompakte Mini-Notation für Steps (z. B. Note, Chords, Rest, Parameter).
  - Native Polyrhythmik: Unabhängige Track-Längen (1–32 Steps) pro Synth (1 & 2) und Drum-Track (1–4).
  - Microsteps (0–5), Probability, Velocity und Gate-Längen.
- **Custom-Firmware-Profile**:
  - `stock`: Standard Novation Circuit Tracks Verhalten.
  - `hacks_rc0s`: Aktiviert erweitertes chromatisches Sample-Playback für die Drum-Tracks 1–4 und erweiterte MIDI-CC-Parametrisierung (`CIRCUITS-HACKS-RC`).

### ✅ Meilenstein 3: FastAPI & WebSocket Hardware-Bridge Daemon
- **Single-Hardware-Owner-Daemon** (`src/bridge/server.py` auf Port `8770`):
  - Zentraler Zugriffspunkt zur physischen Hardware via Mutex (`asyncio.Lock`) zur Vermeidung von MIDI-Buffer-Kollisionen.
- **REST-API-Endpunkte**:
  - `GET /status`: Hardware-Verbindungsstatus, Mock-Modus und Port-Details.
  - `POST /midi/note`: Senden von Note-On/Off mit automatischer Note-Off-Verzögerung.
  - `POST /midi/cc`: Senden von MIDI-Control-Change-Befehlen.
  - `POST /midi/realtime`: Start/Stop/Continue/Clock Realtime-Kommandos.
  - `POST /session/upload`: Upload von `.ncs`-Sessions (Hex-String oder Song-Dict) mit **Safe-Slot-64 Read-Back-Verifikation**.
  - `POST /patch/upload`: Upload von 340-Byte Synth-Patches (`.syx`).
- **Live-WebSocket-Verbindung** (`/ws`):
  - Echtzeit-Event-Broadcasting (z. B. `note_on`, `control_change`, `session_uploaded`, `patch_uploaded`) für Frontends und MCP-Tools.

### ✅ Meilenstein 4: Lokaler MCP-Server (Model Context Protocol)
- **MCP-Server & Tool-Registry** (`src/mcp/server.py`):
  - Exponiert High-Level Batch-Tools für LLMs und Entwicklungsumgebungen (z. B. Claude Desktop / Cursor / Windsurf / Aider).
  - Kommuniziert mit dem Hardware-Daemon auf Port `8770` und unterstützt nahtloses Mock-Fallback, falls der Daemon offline ist.
- **High-Level Tools**:
  - `compose_pattern_batch`: Generiert Tracks und Steps für Synth 1–2 und Drum 1–4 mit Polyrhythmik, Microsteps, Gate und Probability inklusive Firmware-Profil-Validierung (`stock` vs. `hacks_rc0s`).
  - `design_synth_patch`: Erstellt und validiert Novation-kompatible 340-Byte `.syx`-Patches im RAM inklusive Makro-Zuweisungen (Macro 1–8).
  - `configure_mix_and_fx`: Konfiguriert Lautstärken der Tracks sowie Master-Effekte (Reverb, Delay, Sidechain-Tiefe).
  - `hardware_sync`: Überträgt Sessions oder Patches an die Hardware mit automatischer Slot-64-Sicherheit und Read-Back-Verifikation.

### ✅ Meilenstein 5: Live MIDI-Playback & React Studio Frontend
- **Echtzeit-Step-Player** (`src/bridge/player.py`):
  - Streamt DSL-kompilierte Sequenzen über CoreMIDI präzise im 16tel-Raster an die Circuit Tracks Hardware oder Mocks.
  - Korrekte Kanalzuordnung: Synth 1 (Ch 1), Synth 2 (Ch 2), Drums 1–4 (Ch 10 mit C3, D3, E3, F3).
  - Zuverlässiger Panik-Schutz bei Abbruch (ESC / q / Strg+C): Sendet MIDI-Realtime-Stop, All-Notes-Off (CC 123) und All-Sound-Off (CC 120).
- **React + Vite Frontend** (`frontend/`):
  - 4x8 Pad-Grid-Ansicht für Synth 1, Synth 2, Drum 1 und Drum 2.
  - Bidirektionale WebSocket-Verbindung zu `ws://localhost:8770/ws` mit Live Event-Monitor.
  - "Push to Slot 64"-Funktion für nahtlose Übertragung ins Scratchpad des Circuit Tracks.
  - Web Audio API Sound-Vorschau beim Antippen der Pads.

### ✅ Meilenstein 6: Frontend & Bridge (End-to-End)
- **Vollständige End-to-End-Pipeline**: React Hardware Deck (Circuit Tracks Nachbildung) <-> FastAPI Bridge Server <-> In-Memory Core & SysEx Validator.
- **Test-Abdeckung**: 41/41 Pytest-Tests grün.
- **Sichere Übertragung & Verifikation**: Uploads auf Safe Slot 64 (exakt 160.780 Bytes) mit Read-Back-Verifikation.
- **Taktgenaues Lauflicht**: Playhead Clock synchronisiert mit BPM für visuelles Feedback im Frontend.
- **Live-Monitor & Schema**: Integrierter WebSocket-Live-Monitor und flexibles Step-/Pattern-Schema für komplexe Sequenzen.

---

## Startanleitung (Getting Started / How to Run)

Diese Anleitung beschreibt, wie das Gesamtsystem (FastAPI-Bridge und React-Frontend) gestartet wird. Dies ist besonders für Google Cloud Shell und Headless-Linux-Umgebungen relevant, da das System automatisch auf den Mock-Modus zurückfällt, wenn keine physische Circuit Tracks per USB angeschlossen ist.

---

### Terminal 1 – FastAPI Bridge Server

Startet den zentralen Hardware-Daemon (inkl. automatischem Mock-Fallback) auf Port 8770:

```bash
cd ~/circuit-ai-studio
PYTHONPATH="vendor/circuit-tracks-tools/src:src:." uv run uvicorn src.bridge.server:app --host 0.0.0.0 --port 8770 --reload