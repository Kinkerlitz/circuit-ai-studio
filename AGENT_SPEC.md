# Project Specification: Circuit Tracks AI Studio (macOS)

## 1. System-Kontext & Arbeitsweise in Aider
Du arbeitest lokal im Verzeichnis ~/circuit-ai-studio auf einem Mac mini (macOS).
- Im Ordner vendor/circuit-tracks-tools liegt bereits die vollstaendige Python-Referenz fuer das .ncs-Binaerformat, .syx-Patches und SysEx-Kommunikation. Analysiere und nutze diese Dateien!
- Nach jeder Code-Aenderung fuehrt Aider automatisch "uv run pytest" aus (auto-test: true).
- WICHTIG: Schreibe zu JEDEM Modul sofort passende pytest-Tests in tests/. Wenn pytest fehlschlaegt, analysiere den Stacktrace und repariere den Code selbststaendig, bis pytest mit Exit-Code 0 durchlaeuft!

## 2. Eiserne Architektur-Regeln
1. Single-Hardware-Owner: Nur der Python-Daemon (src/bridge/server.py auf Port 8770) darf ueber python-rtmidi / mido mit dem Circuit Tracks sprechen. Browser-UI und MCP-Server kommunizieren ausschliesslich per WebSocket/REST mit Port 8770.
2. Offline-First Validation: Jede generierte .ncs-Session und jeder 340-Byte .syx-Patch muss vor dem Hardware-Versand im RAM validiert werden (serialize -> parse -> assert_equal).
3. Mock-Fallback: Wenn kein physischer Circuit Tracks per USB angeschlossen ist, muss die Hardware-Bridge automatisch in einen MockCircuitTracks-Modus schalten, damit alle Unit- und Integrationstests fehlerfrei durchlaufen.
4. High-Level Pattern-DSL: Implementiere einen kompakten Pattern-Parser (src/core/dsl.py), der deklarative JSON/Mini-Notation-Strukturen (Polyrhythmik mit unterschiedlichen Step-Laengen 1-32, Microsteps, Probability, Gate, Synth-Makros) in einem Aufruf in eine valide .ncs-Struktur uebersetzt.
5. Custom Firmware Support: Unterstuetze das Flag firmware_profile: "stock" | "hacks_rc0s", um fuer CIRCUITS-HACKS-RC chromatisches Sample-Playback auf Drum 1-4 sowie die erweiterten MIDI-CCs freizuschalten.

## 3. Meilensteine
- Meilenstein 1: Python-Setup pruefen + erster Basis-Test in tests/test_setup.py + CoreMIDI-Detektor (src/bridge/midi_detector.py inkl. Mock-Fallback).
- Meilenstein 2: .ncs & .syx Wrapper um vendor/circuit-tracks-tools in src/core/ + In-Memory Roundtrip-Validator + Pattern-DSL-Compiler (src/core/dsl.py) + CIRCUITS-HACKS-RC Profil.
- Meilenstein 3: FastAPI/WebSocket Hardware-Bridge Daemon (src/bridge/server.py auf Port 8770) mit Sende-Queue (Mutex) und Safe-Slot-64 Read-Back-Verifikation.
- Meilenstein 4: Lokaler MCP-Server (src/mcp/server.py) mit High-Level Batch-Tools (compose_pattern_batch, design_synth_patch, configure_mix_and_fx, hardware_sync).
- Meilenstein 5: React + Vite + Web Audio API Frontend (frontend/) mit 4x8 Pad-Grid, Step-/Microstep-Inspektor und Live-WebSocket-Sync zu Port 8770.
