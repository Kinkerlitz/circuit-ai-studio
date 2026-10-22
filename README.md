# Circuit Tracks AI Studio (macOS)

Circuit Tracks AI Studio ist eine professionelle Entwicklungs- und Steuerungsumgebung für die Novation Circuit Tracks Groovebox unter macOS. Es verbindet direkte CoreMIDI- und SysEx-Hardware-Kommunikation mit deklarativer Pattern-DSL, strikter Offline-First-Validierung, einem schnellen FastAPI/WebSocket-Daemon und einem lokalen Model Context Protocol (MCP) Server für KI-gestützte Komposition und Patch-Design.

---

## 🚀 Projektstatus (Meilensteine 1–4 abgeschlossen)

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

---

## 🖥 Interaktives Terminal-Studio (`studio_cli.py`)

Das Projekt beinhaltet eine interaktive Konsole mit ANSI-Farbdarstellung zur einfachen Bedienung und Inspektion:

Starten über:
