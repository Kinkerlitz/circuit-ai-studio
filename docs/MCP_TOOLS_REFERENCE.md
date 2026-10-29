# MCP Tools Reference (Compact)

> 30+ tools for controlling Novation Circuit Tracks via LLM

## Connection & Setup

| Tool | Description |
|------|-------------|
| `list_midi_ports()` | List available MIDI input/output ports |
| `connect(port_name)` | Connect to Circuit Tracks MIDI port |
| `disconnect()` | Disconnect from device |
| `connection_status()` | Check current MIDI connection status |

## Live Performance

| Tool | Description |
|------|-------------|
| `play_notes(channel, notes, velocity, duration_ms)` | Play MIDI notes/chords |
| `play_drum(drum, velocity)` | Trigger drum hit (1-4) |
| `set_macro(synth, macro, value)` | Set macro knob (1-8, value 0-127) |
| `get_macros()` | Get current macro layout |

## Pattern Sequencer

| Tool | Description |
|------|-------------|
| `set_pattern(name, tracks, length)` | Define named pattern with tracks/steps |
| `set_track(pattern_name, track, steps, clear_existing)` | Update single track in pattern |
| `clear_pattern(name)` | Clear all steps from pattern |
| `get_pattern(name)` | Get pattern data |
| `list_patterns()` | List all pattern names |
| `start_sequencer(pattern, bpm, send_clock)` | Start pattern playback |
| `stop_sequencer()` | Stop sequencer |
| `set_bpm(bpm)` | Change tempo while running |
| `queue_patterns(patterns)` | Queue patterns for sequential playback |
| `set_song(patterns)` | Replace entire pattern queue |
| `clear_queue()` | Clear queue (current pattern loops) |
| `mute_track(track, muted)` | Mute/unmute track |
| `get_sequencer_status()` | Get running state, pattern, step, BPM |

## Sound Design

| Tool | Description |
|------|-------------|
| `set_synth_params(synth, params)` | Set synth parameters (1-2) |
| `set_drum_params(drum, params)` | Set drum parameters (1-4) |
| `select_patch(synth, patch_number)` | Select patch (0-63) |
| `select_project(project_number, queued)` | Select project (0-63) |
| `set_project_params(params)` | Set project-level params (reverb, delay, etc.) |
| `list_drum_samples(page)` | List available drum samples |
| `set_drum_sample_names(samples)` | Set custom drum sample names |

## Reference

| Tool | Description |
|------|-------------|
| `get_parameter_reference(section)` | Get parameter docs (synth/patch/drums/project/etc.) |

---

## Quick Start Workflow

```
1. list_midi_ports() → find Circuit Tracks
2. connect("Circuit Tracks") → establish connection
3. get_parameter_reference("song_format") → learn structure
4. set_pattern("intro", {...}) → create pattern
5. start_sequencer("intro", 120.0) → preview
6. export_song_to_project(...) → save to hardware
```

## Best Practices

- **Pattern Length**: All patterns must use same length (16 or 32 steps)
- **Macros**: Set base values LOW for params macros sweep upward
- **Standard Layout**: Macro 1=Osc, 2=OscMod, 3=AmpEnv, 4=FilterEnv, 5=Filter, 6=Res, 7=Mod, 8=FX
- **Always Include Sounds**: Use "sounds" key with full patch configs
- **Safe Slot**: Use Slot 64 for non-destructive testing
