# Project Specification: Circuit Tracks AI Studio (macOS)

## 1. System-Kontext & Arbeitsweise in Aider
Du arbeitest lokal im Verzeichnis ~/circuit-ai-studio auf einem Mac mini (macOS).
- Im Ordner vendor/circuit-tracks-tools liegt bereits die vollstaendige Python-Referenz fuer das .ncs-Binaerformat, .syx-Patches und SysEx-Kommunikation. Analysiere und nutze diese Dateien!
- Nach jeder Code-Aenderung fuehrt Aider automatisch Tests aus. Der korrekte Testaufruf lautet immer: `PYTHONPATH="vendor/circuit-tracks-tools/src:src:." uv run pytest`
- WICHTIG: Schreibe zu JEDEM Modul sofort passende pytest-Tests in tests/. Wenn pytest fehlschlaegt, analysiere den Stacktrace und repariere den Code selbststaendig, bis pytest mit Exit-Code 0 durchlaeuft!
- Aktueller Stand: 41/41 Pytest-Tests grün. Das System läuft nahtlos lokal auf macOS (CoreMIDI) sowie headless in Linux/Cloud Shell (MockCircuitTracksConnection).

## 2. Eiserne Architektur-Regeln
1. Single-Hardware-Owner: Nur der Python-Daemon (src/bridge/server.py auf Port 8770) darf ueber python-rtmidi / mido mit dem Circuit Tracks sprechen. Browser-UI und MCP-Server kommunizieren ausschliesslich per WebSocket/REST mit Port 8770.
2. Offline-First Validation: Jede generierte .ncs-Session und jeder 340-Byte .syx-Patch muss vor dem Hardware-Versand im RAM validiert werden (`validate_ncs_roundtrip()` und `validate_patch_roundtrip()` müssen vor jedem Hardware-Push aufgerufen werden).
3. Mock-Fallback: Wenn kein physischer Circuit Tracks per USB angeschlossen ist, muss die Hardware-Bridge automatisch in einen MockCircuitTracks-Modus schalten, damit alle Unit- und Integrationstests fehlerfrei durchlaufen.
4. High-Level Pattern-DSL: Implementiere einen kompakten Pattern-Parser (src/core/dsl.py), der deklarative JSON/Mini-Notation-Strukturen (Polyrhythmik mit unterschiedlichen Step-Laengen 1-32, Microsteps, Probability, Gate, Synth-Makros) in einem Aufruf in eine valide .ncs-Struktur uebersetzt.
5. Custom Firmware Support: Unterstuetze das Flag firmware_profile: "stock" | "hacks_rc0s", um fuer CIRCUITS-HACKS-RC chromatisches Sample-Playback auf Drum 1-4 sowie die erweiterten MIDI-CCs freizuschalten.
6. Safe Slot 64: Scratchpad-Regel bleibt strikt aktiv (nur Slot 64 für automatisierte Schreib-/Lese-Tests und Verifizierungen nutzen, um Live-Sessions nicht zu überschreiben).

## 3. Core Wrapper Schnittstellen (src/core/wrapper.py & src/core/__init__.py)
Folgende Funktionen sind verbindlich implementiert und dürfen in zukünftigen Iterationen nicht entfernt oder in ihrer Signatur verändert werden:
- `read_ncs_file(connection, slot: int) -> bytes | None`
- `write_ncs_file(connection, ncs_bytes: bytes, slot: int) -> None`
- `parse_syx_patch(syx_data: bytes) -> dict`
- `ncs_bytes_to_song(ncs_bytes: bytes) -> dict`
- `song_to_ncs_bytes(song: dict | SongData) -> bytes` (exakt 160.780 Bytes)
- `patch_to_syx(patch_bytes: bytes, synth: int) -> bytes` (348/350 Bytes SysEx Frame)
- `build_default_patch(name: str, preset: str) -> bytes` (exakt 340 Bytes)

## 4. Meilensteine
- ✅ Meilenstein 1: Python-Setup pruefen + erster Basis-Test in tests/test_setup.py + CoreMIDI-Detektor (src/bridge/midi_detector.py inkl. Mock-Fallback).
- ✅ Meilenstein 2: .ncs & .syx Wrapper um vendor/circuit-tracks-tools in src/core/ + In-Memory Roundtrip-Validator + Pattern-DSL-Compiler (src/core/dsl.py) + CIRCUITS-HACKS-RC Profil.
- ✅ Meilenstein 3: FastAPI/WebSocket Hardware-Bridge Daemon (src/bridge/server.py auf Port 8770) mit Sende-Queue (Mutex) und Safe-Slot-64 Read-Back-Verifikation.
- ✅ Meilenstein 4: Lokaler MCP-Server (src/mcp/server.py) mit High-Level Batch-Tools (compose_pattern_batch, design_synth_patch, configure_mix_and_fx, hardware_sync).
- ✅ Meilenstein 5: Live MIDI-Playback Engine (src/bridge/player.py) & Basis React + Vite Frontend.
- 🔄 Meilenstein 6: Frontend-Erweiterung (Split-View: Hardware Deck mit 4x8 Pads & Makro-Reglern + AI Agent Workspace).
