#!/usr/bin/env python3
"""Circuit Tracks AI Studio - Interactive Terminal CLI.

Provides an interactive console interface to:
1. Preview and compile DSL patterns with a step-sequencer grid view.
2. Scan and monitor CoreMIDI ports / Circuit Tracks connections.
3. Synthesize and inspect 340-byte SysEx synth patches.
4. Run the full pytest test suite directly from the menu.
5. Live playback of compiled DSL patterns over CoreMIDI.

Includes non-blocking keyboard polling with instant cancel / emergency MIDI panic.
"""

from __future__ import annotations

import select
import sys
import termios
import threading
import time
import tty
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root and vendor/circuit-tracks-tools are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
VENDOR_ROOT = PROJECT_ROOT / "vendor" / "circuit-tracks-tools"
VENDOR_SRC = VENDOR_ROOT / "src"
SRC_ROOT = PROJECT_ROOT / "src"

for path_to_add in (PROJECT_ROOT, SRC_ROOT, VENDOR_SRC, VENDOR_ROOT):
    if path_to_add.exists() and str(path_to_add) not in sys.path:
        sys.path.insert(0, str(path_to_add))

# ANSI Color codes for rich terminal styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_header() -> None:
    print(f"{CYAN}{BOLD}=========================================================={RESET}")
    print(f"{CYAN}{BOLD}         CIRCUIT TRACKS AI STUDIO - CONTROL CLI           {RESET}")
    print(f"{CYAN}{BOLD}=========================================================={RESET}")
    print(f"{DIM}macOS CoreMIDI | In-Memory Validation | Instant Cancel (ESC/q){RESET}\n")


class NonBlockingInput:
    """Context manager to read single keypresses non-blockingly on Unix/macOS."""

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    @staticmethod
    def check_key(timeout: float = 0.0) -> Optional[str]:
        """Check if a key is available within timeout seconds without blocking."""
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            char = sys.stdin.read(1)
            # Check for ESC sequence or single keys
            if char == "\x1b":  # ESC
                return "ESC"
            elif char == "\x03":  # Ctrl+C
                return "CANCEL"
            return char
        return None


def safe_cancel_midi() -> None:
    """Emergency MIDI silence to ensure Circuit Tracks does not freeze or hang."""
    try:
        from src.bridge.midi_detector import get_midi_connection
        conn = get_midi_connection()
        if hasattr(conn, "send_realtime"):
            conn.send_realtime("stop")
        for ch in {0, 1, 2, 3, 9}:
            try:
                conn.all_notes_off(ch)
                conn.control_change(channel=ch, control=120, value=0)  # All Sound Off
                conn.control_change(channel=ch, control=123, value=0)  # All Notes Off
            except Exception:
                pass
    except Exception as exc:
        sys.stderr.write(f"\nHinweis bei MIDI-Abschaltung: {exc}\n")


def wait_for_enter_or_cancel() -> None:
    """Wait for user ENTER or ESC/q/Ctrl+C to cancel promptly."""
    print(f"\nDrücke {BOLD}[ENTER]{RESET} oder {RED}[ESC / q]{RESET} zum Abbrechen...", end="", flush=True)
    with NonBlockingInput():
        while True:
            key = NonBlockingInput.check_key(timeout=0.1)
            if key in ("\n", "\r", " ", "ESC", "q", "Q", "CANCEL"):
                if key in ("ESC", "q", "Q", "CANCEL"):
                    safe_cancel_midi()
                break
    print()


def get_demo_dsl() -> Dict[str, Any]:
    return {
        "name": "StudioGroove",
        "bpm": 126,
        "tracks": {
            "synth1": {
                "length": 16,
                "mini": "C3 . . . Eb3 . . . G3 . . . Bb3 . C4 .",
            },
            "synth2": {
                "length": 12,
                "mini": "G4 . . G4 . . Bb4 . . D5 . .",
            },
            "drum1": {
                "length": 16,
                "mini": "x . . . x . . . x . . . x . . .",
            },
            "drum2": {
                "length": 16,
                "mini": ". . . . x . . . . . . . x . . .",
            },
            "drum3": {
                "length": 16,
                "mini": ". . x . . . x . . . x . . . x .",
            },
            "drum4": {
                "length": 16,
                "mini": "x x x x x x x x x x x x x x x x",
            },
        },
    }


def render_pattern_grid() -> None:
    """Load a sample DSL polyrhythmic pattern and render terminal sequencer grid."""
    from src.core.dsl import compile_dsl_to_song

    print(f"\n{BOLD}{MAGENTA}--- [1] DSL PATTERN GRID SEQUENCER ---{RESET}\n")

    dsl_sample = get_demo_dsl()
    song = compile_dsl_to_song(dsl_sample)
    tracks = song["patterns"]["p1"]["tracks"]

    print(f"{BOLD}Session:{RESET} {dsl_sample['name']} | {BOLD}Tempo:{RESET} {dsl_sample['bpm']} BPM\n")

    header = f"{'Track':<10} | " + " ".join(f"{i:02d}" for i in range(1, 17))
    print(f"{DIM}{header}{RESET}")
    print(f"{DIM}{'-' * len(header)}{RESET}")

    track_colors = {
        "synth1": CYAN,
        "synth2": CYAN,
        "drum1": YELLOW,
        "drum2": YELLOW,
        "drum3": MAGENTA,
        "drum4": MAGENTA,
    }

    for track_name, track_data in tracks.items():
        length = track_data.get("length", 16)
        steps_dict = track_data.get("steps", {})
        color = track_colors.get(track_name, GREEN)

        cells = []
        for step_idx in range(16):
            if step_idx < length:
                str_idx = str(step_idx)
                if str_idx in steps_dict:
                    cells.append(f"{color}{BOLD}[X]{RESET}")
                else:
                    cells.append(f"{DIM}[·]{RESET}")
            else:
                cells.append(f"{DIM} - {RESET}")

        poly_info = f"({length} steps)" if length != 16 else ""
        row = f"{color}{track_name:<10}{RESET} | " + " ".join(cells) + f" {DIM}{poly_info}{RESET}"
        print(row)

    print(f"\n{GREEN}✔ Pattern erfolgreich in NCS-kompatibles Song-Modell kompiliert!{RESET}")
    wait_for_enter_or_cancel()


def scan_midi_ports() -> None:
    """Scan and print MIDI devices with responsive cancel support."""
    from src.bridge.midi_detector import detect_circuit_tracks

    print(f"\n{BOLD}{MAGENTA}--- [2] MIDI PORT & HARDWARE STATUS SCAN ---{RESET}\n")
    print("Scanne CoreMIDI-Schnittstellen (Drücke jederzeit ESC zum Abbrechen)...\n")

    result = {}

    def _worker():
        try:
            result["status"] = detect_circuit_tracks()
        except Exception as err:
            result["error"] = err

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    with NonBlockingInput():
        while t.is_alive():
            key = NonBlockingInput.check_key(timeout=0.05)
            if key in ("ESC", "q", "Q", "CANCEL"):
                print(f"\n{YELLOW}Scan vom Benutzer abgebrochen.{RESET}")
                safe_cancel_midi()
                return

    status = result.get("status")
    if not status:
        print(f"{RED}Fehler beim Ermitteln der Ports: {result.get('error')}{RESET}")
        wait_for_enter_or_cancel()
        return

    if status.is_connected and not status.is_mock:
        display_name = status.device_name or status.port_name or "Circuit Tracks"
        print(f"Status: {GREEN}{BOLD}● HARDWARE ONLINE{RESET}")
        print(f"Gerät : {BOLD}{display_name}{RESET}")
        print(f"Port  : {status.port_name}")
    else:
        print(f"Status: {YELLOW}{BOLD}○ MOCK-MODUS AKTIV{RESET} (Kein physischer Circuit Tracks erkannt)")
        print(f"{DIM}Hinweis: Alle Systemtests, DSL-Generierungen und SysEx-Erstellungen laufen ohne Einschränkungen im RAM.{RESET}")

    print(f"\n{BOLD}Verfügbare MIDI-Ausgänge (CoreMIDI):{RESET}")
    if status.available_outputs:
        for idx, out_name in enumerate(status.available_outputs, start=1):
            is_ct = "circuit" in out_name.lower()
            tag = f" {GREEN}(Circuit Tracks){RESET}" if is_ct else ""
            print(f"  [{idx}] {out_name}{tag}")
    else:
        print(f"  {DIM}(Keine physischen CoreMIDI-Ausgänge gelistet){RESET}")

    print(f"\n{BOLD}Verfügbare MIDI-Eingänge (CoreMIDI):{RESET}")
    if status.available_inputs:
        for idx, in_name in enumerate(status.available_inputs, start=1):
            is_ct = "circuit" in in_name.lower()
            tag = f" {GREEN}(Circuit Tracks){RESET}" if is_ct else ""
            print(f"  [{idx}] {in_name}{tag}")
    else:
        print(f"  {DIM}(Keine physischen CoreMIDI-Eingänge gelistet){RESET}")

    wait_for_enter_or_cancel()


def generate_patch_preview() -> None:
    """Generate a default synth patch and inspect SysEx bytes."""
    from src.core.wrapper import build_default_patch
    from src.core.validator import validate_patch_roundtrip

    print(f"\n{BOLD}{MAGENTA}--- [3] SYNTH PATCH GENERATOR & SYSEX INSPECTOR ---{RESET}\n")

    patch_name = "SuperBass"
    preset_type = "bass"
    print(f"Erzeuge Patch: {BOLD}{patch_name}{RESET} (Preset: {preset_type})...")

    patch_bytes = build_default_patch(name=patch_name, preset=preset_type)
    val = validate_patch_roundtrip(patch_bytes)

    print(f"Byte-Größe   : {BOLD}{len(patch_bytes)} Bytes{RESET} {'(Exakt 340 Bytes Novation-Standard)' if len(patch_bytes) == 340 else RED + 'FEHLER!' + RESET}")
    print(f"Patch-Name   : {BOLD}{val.name}{RESET}")
    print(f"Validierung  : {GREEN}✔ Gültig (Roundtrip OK){RESET}" if val.is_valid else f"{RED}✘ Ungültig: {val.differences}{RESET}")
    print(f"SysEx-Header : F0 {patch_bytes[1:7].hex().upper()} ... F7")

    print(f"\n{BOLD}Hex-Dump Vorschau (Erste 64 Bytes):{RESET}")
    for offset in range(0, min(64, len(patch_bytes)), 16):
        chunk = patch_bytes[offset : offset + 16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"  {offset:04X}:  {hex_str:<48}  {DIM}|{ascii_str}|{RESET}")

    wait_for_enter_or_cancel()


def run_all_tests() -> None:
    """Execute pytest suite and display formatted results with abort capability."""
    import pytest

    print(f"\n{BOLD}{MAGENTA}--- [4] PYTEST SUITE AUSFÜHREN ---{RESET}\n")
    print("Starte Test-Runner über alle Test-Dateien...\n")

    t_start = time.perf_counter()
    exit_code = pytest.main(["-q", "--tb=short"])
    duration = time.perf_counter() - t_start

    print(f"\n{DIM}{'-' * 50}{RESET}")
    if exit_code == 0:
        print(f"{GREEN}{BOLD}✔ ERFOLG: Alle Tests erfolgreich bestanden!{RESET}")
    else:
        print(f"{RED}{BOLD}✘ FEHLER: Test-Suite meldete Fehler (Exit-Code {exit_code}){RESET}")

    print(f"Dauer: {duration:.2f} Sekunden")
    wait_for_enter_or_cancel()


def play_live_pattern() -> None:
    """Stream DSL pattern over MIDI in realtime with non-blocking key abort."""
    from src.core.dsl import compile_dsl_to_song
    from src.bridge.player import MidiPatternPlayer

    print(f"\n{BOLD}{MAGENTA}--- [5] LIVE PATTERN PLAYBACK (MIDI ENGINE) ---{RESET}\n")

    dsl_data = get_demo_dsl()
    song = compile_dsl_to_song(dsl_data)
    player = MidiPatternPlayer()

    mode_label = "MOCK CONNECTION" if getattr(player.connection, "is_mock", False) else "CIRCUIT TRACKS HARDWARE"
    print(f"Ziel-Ausgang : {BOLD}{mode_label}{RESET}")
    print(f"Pattern-Name : {BOLD}{dsl_data['name']}{RESET} | BPM: {dsl_data['bpm']}")
    print(f"{YELLOW}Spielt Sequenz ab. Beliebige Taste oder [ESC / q / Strg+C] bricht SOFORT ab!{RESET}\n")

    # Start playback asynchronously in background thread
    player.play_song(song, pattern_name="p1", loops=4, blocking=False)

    canceled = False
    with NonBlockingInput():
        while player.is_playing:
            key = NonBlockingInput.check_key(timeout=0.03)
            if key is not None:
                canceled = True
                print(f"\n\n{YELLOW}Abbruch angefordert ({key}). Stoppe MIDI sofort...{RESET}")
                player.stop()
                safe_cancel_midi()
                break

    if not canceled:
        print(f"\n\n{GREEN}✔ Playback regulär abgeschlossen!{RESET}")
    else:
        print(f"{GREEN}✔ Panik-Signal & All-Notes-Off erfolgreich an Circuit Tracks gesendet.{RESET}")

    wait_for_enter_or_cancel()


def main_menu() -> None:
    """Main interactive terminal loop with instant responsive keystrokes."""
    while True:
        clear_screen()
        print_header()
        print("Bitte wähle eine Option:\n")
        print(f"  {CYAN}{BOLD}[1]{RESET} Test-Pattern (DSL) laden & als Step-Grid visualisieren")
        print(f"  {CYAN}{BOLD}[2]{RESET} MIDI-Verbindung & CoreMIDI-Ports scannen")
        print(f"  {CYAN}{BOLD}[3]{RESET} 340-Byte Synth-Patch erzeugen & SysEx inspizieren")
        print(f"  {CYAN}{BOLD}[4]{RESET} Alle Pytest-Tests ausführen")
        print(f"  {CYAN}{BOLD}[5]{RESET} Test-Pattern live über MIDI abspielen (mit Sofort-Abbruch)")
        print(f"  {RED}{BOLD}[q / ESC]{RESET} Beenden\n")
        print(f"{DIM}(Tastendruck genügt, kein [ENTER] erforderlich){RESET}\n")
        print(f"{BOLD}Auswahl: {RESET}", end="", flush=True)

        with NonBlockingInput():
            while True:
                choice = NonBlockingInput.check_key(timeout=0.1)
                if choice is not None:
                    break

        choice_clean = choice.strip().lower() if choice else ""

        if choice_clean == "1":
            render_pattern_grid()
        elif choice_clean == "2":
            scan_midi_ports()
        elif choice_clean == "3":
            generate_patch_preview()
        elif choice_clean == "4":
            run_all_tests()
        elif choice_clean == "5":
            play_live_pattern()
        elif choice_clean in ("q", "escape", "esc", "cancel") or choice == "ESC":
            safe_cancel_midi()
            print(f"\n{CYAN}Auf Wiedersehen!{RESET}\n")
            break
        else:
            print(f"\n{YELLOW}Ungültige Taste '{choice}'. Bitte 1-5 oder q wählen.{RESET}")
            time.sleep(0.6)


if __name__ == "__main__":
    try:
        main_menu()
    except (KeyboardInterrupt, SystemExit):
        safe_cancel_midi()
        print(f"\n\n{CYAN}Abbruch durch Benutzer. Sichere MIDI-Stummschaltung ausgeführt!{RESET}\n")
        sys.exit(0)
