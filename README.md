# Circuit Tracks AI Studio (macOS)

Circuit Tracks AI Studio ist eine professionelle Entwicklungs- und Steuerungsumgebung für die Novation Circuit Tracks Groovebox unter macOS. Es verbindet direkte CoreMIDI- und SysEx-Hardware-Kommunikation mit deklarativer Pattern-DSL, strikter Offline-First-Validierung und einem schnellen FastAPI/WebSocket-Daemon.

---

## 🚀 Projektstatus (Meilensteine 1–3 abgeschlossen)

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

---

## 🛠 Voraussetzungen & Installation

- **macOS** (Mac mini / Apple Silicon oder Intel)
- **Python >= 3.10**
- **uv** (empfohlener schneller Python-Paketmanager)

Repository clonen und Abhängigkeiten installieren:
- `git clone https://github.com/<dein-github-username>/circuit-ai-studio.git`
- `cd circuit-ai-studio`
- `uv sync`

---

## 🧪 Tests ausführen

Das Projekt verfügt über 20 Unit- und Integrationstests, die alle Meilensteine ohne physische Hardware (über Mocks und In-Memory-Validierung) abdecken:

Befehl zum Ausführen aller Tests:
- `uv run pytest`

Ausgewählte Testbereiche gezielt ausführen:
- Meilenstein 1 & Setup: `uv run pytest tests/test_setup.py tests/test_midi_detector.py`
- Meilenstein 2: In-Memory Roundtrip & DSL-Compiler: `uv run pytest tests/test_core_roundtrip.py tests/test_dsl.py`
- Meilenstein 3: FastAPI Server & WebSockets: `uv run pytest tests/test_bridge_server.py`

---

## 🔌 Hardware-Bridge Daemon starten

Der Bridge-Server kann direkt gestartet werden und bindet standardmäßig auf Port 8770:
- `uv run python -m src.bridge.server`

Interaktive OpenAPI-Dokumentation (Swagger UI):
- Öffne `http://localhost:8770/docs` im Browser.

---

## 💡 Beispiel: Pattern-DSL zu NCS kompilieren

Verwendung in Python:
- Importiere `FirmwareProfile` und `compile_dsl_to_ncs_bytes` aus `src.core.dsl`.
- Definiere deine Polyrhythmen und Tracks deklarativ.
- Erhalte fertige, im RAM validierte NCS-Bytes für den Hardware-Upload.

---

## 🗺 Ausblick: Meilensteine 4 & 5

- **Meilenstein 4**: Lokaler MCP-Server (`src/mcp/server.py`) zur KI-gestützten Komposition (`compose_pattern_batch`, `design_synth_patch`, `configure_mix_and_fx`, `hardware_sync`).
- **Meilenstein 5**: Modernes Web-Frontend (React + Vite + Web Audio API) mit 4x8 Pad-Grid, interaktivem Microstep-Inspektor und bidirektionalem WebSocket-Sync zu Port 8770.
