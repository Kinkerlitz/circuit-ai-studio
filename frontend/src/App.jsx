import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const TRACKS = [
  { id: 'synth1', name: 'Synth 1', color: 'synth1', channel: 0, defaultNote: 60 },
  { id: 'synth2', name: 'Synth 2', color: 'synth2', channel: 1, defaultNote: 64 },
  { id: 'midi1', name: 'MIDI 1', color: 'midi1', channel: 2, defaultNote: 60 },
  { id: 'midi2', name: 'MIDI 2', color: 'midi2', channel: 3, defaultNote: 60 },
  { id: 'drum1', name: 'Drum 1', color: 'drum1', channel: 9, defaultNote: 60 },
  { id: 'drum2', name: 'Drum 2', color: 'drum2', channel: 9, defaultNote: 62 },
  { id: 'drum3', name: 'Drum 3', color: 'drum3', channel: 9, defaultNote: 64 },
  { id: 'drum4', name: 'Drum 4', color: 'drum4', channel: 9, defaultNote: 65 },
];

const NUM_STEPS = 16;
const NUM_NOTE_PADS = 16;

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Verbinde zu Bridge auf Port 8770...');
  const [logs, setLogs] = useState([]);
  
  const [activeTrackId, setActiveTrackId] = useState('synth1');
  const [patternLength, setPatternLength] = useState(16);
  const [isPlaying, setIsPlaying] = useState(false);
  const [macros, setMacros] = useState(Array(8).fill(64));
  
  const [grid, setGrid] = useState(() => {
    const initialGrid = {};
    TRACKS.forEach(t => {
      initialGrid[t.id] = Array(NUM_STEPS).fill(false);
    });
    return initialGrid;
  });

  const [prompt, setPrompt] = useState('');
  const [agentOutput, setAgentOutput] = useState('{\n  "status": "waiting for prompt..."\n}');
  const [isPushing, setIsPushing] = useState(false);

  const audioCtxRef = useRef(null);

  const playWebAudioTone = (freq = 440) => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.15);
    } catch {
      // Audio context might be restricted before user gesture
    }
  };

  const addLog = (msg) => {
    setLogs((prev) => [
      `[${new Date().toLocaleTimeString()}] ${msg}`,
      ...prev.slice(0, 40),
    ]);
  };

  useEffect(() => {
    let ws;
    let timer;

    const connectWs = () => {
      const wsUrl = `ws://${window.location.hostname}:8770/ws`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        setStatusMsg('Verbunden mit Port 8770');
        addLog('WebSocket-Verbindung hergestellt');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          addLog(`Event: ${data.type || 'msg'} ${JSON.stringify(data.data || {})}`);
        } catch {
          addLog(`WS: ${event.data}`);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setStatusMsg('Getrennt. Neuer Versuch...');
        timer = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWs();
    return () => {
      if (ws) ws.close();
      if (timer) clearTimeout(timer);
    };
  }, []);

  const toggleStep = (stepIdx) => {
    if (stepIdx >= patternLength) return;
    
    setGrid((prev) => {
      const newTrackGrid = [...prev[activeTrackId]];
      newTrackGrid[stepIdx] = !newTrackGrid[stepIdx];
      return { ...prev, [activeTrackId]: newTrackGrid };
    });
  };

  const playNotePad = async (noteIdx) => {
    const track = TRACKS.find((t) => t.id === activeTrackId);
    if (!track) return;

    const note = track.defaultNote + noteIdx;
    const freq = 130 * Math.pow(1.05946, note - 48);
    playWebAudioTone(freq);

    try {
      await fetch('http://localhost:8770/midi/note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: track.channel,
          note: note,
          velocity: 100,
          duration_s: 0.1,
        }),
      });
    } catch {
      // Bridge may be in mock or offline
    }
  };

  const handleTransport = async (cmd) => {
    setIsPlaying(cmd === 'start' || cmd === 'continue');
    try {
      await fetch('http://localhost:8770/midi/realtime', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
    } catch {
      // Ignore
    }
  };

  const handleMacroChange = async (idx, val) => {
    const newMacros = [...macros];
    newMacros[idx] = val;
    setMacros(newMacros);
    
    const track = TRACKS.find((t) => t.id === activeTrackId);
    if (!track) return;
    
    try {
      await fetch('http://localhost:8770/midi/cc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: track.channel,
          control: 70 + idx, // Example CC mapping
          value: val,
        }),
      });
    } catch {
      // Ignore
    }
  };

  const pushToSlot64 = async () => {
    setIsPushing(true);
    addLog('Erstelle Song-Payload für Safe-Slot 64...');

    const compiledTracks = {};
    TRACKS.forEach((track) => {
      const steps = {};
      grid[track.id].forEach((isActive, idx) => {
        if (isActive && idx < patternLength) {
          steps[String(idx)] = {
            note: track.defaultNote,
            velocity: 100,
            gate: 0.5,
          };
        }
      });
      compiledTracks[track.id] = {
        length: patternLength,
        steps,
      };
    });

    const songPayload = {
      name: 'Slot64Push',
      bpm: 124,
      patterns: {
        p1: {
          tracks: compiledTracks,
        },
      },
    };

    try {
      const response = await fetch('http://localhost:8770/session/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slot: 64,
          song_dict: songPayload,
          verify: true,
        }),
      });

      const resData = await response.json();
      if (response.ok) {
        addLog(`✔ Erfolgreich auf Slot 64 gepusht! (Verified: ${resData.verified})`);
      } else {
        addLog(`✘ Fehler beim Upload: ${JSON.stringify(resData)}`);
      }
    } catch (err) {
      addLog(`✘ Netzwerkfehler beim Push: ${err.message}`);
    } finally {
      setIsPushing(false);
    }
  };

  const handlePromptSubmit = () => {
    addLog(`Agent Prompt: ${prompt}`);
    setAgentOutput(JSON.stringify({
      action: "generate_pattern",
      parameters: {
        style: "acid",
        key: "A minor",
        prompt: prompt
      },
      status: "mocked_response"
    }, null, 2));
    setPrompt('');
  };

  const activeTrackColor = TRACKS.find(t => t.id === activeTrackId)?.color || 'synth1';

  return (
    <div className="app-container">
      <div className="split-layout">
        
        {/* LEFT: HARDWARE DECK */}
        <div className="hardware-deck">
          <div className="deck-header">
            <h2>CIRCUIT TRACKS</h2>
            <div className="transport-controls">
              <button className={`btn-transport ${isPlaying ? 'active' : ''}`} onClick={() => handleTransport('start')}>▶</button>
              <button className="btn-transport" onClick={() => handleTransport('stop')}>■</button>
            </div>
          </div>

          <div className="macros-section">
            {macros.map((val, idx) => (
              <div key={idx} className="macro-knob-container">
                <input 
                  type="range" 
                  min="0" max="127" 
                  value={val} 
                  onChange={(e) => handleMacroChange(idx, parseInt(e.target.value))}
                  className={`macro-slider ${activeTrackColor}`}
                />
                <div className="macro-label">M{idx + 1}</div>
              </div>
            ))}
          </div>

          <div className="track-selector">
            {TRACKS.map(track => (
              <button 
                key={track.id}
                className={`track-btn ${track.color} ${activeTrackId === track.id ? 'active' : ''}`}
                onClick={() => setActiveTrackId(track.id)}
              >
                {track.name}
              </button>
            ))}
          </div>

          <div className="pads-section">
            <div className="pads-label">Sequencer (Steps 1-16)</div>
            <div className="pads-grid sequencer-grid">
              {Array.from({ length: NUM_STEPS }).map((_, idx) => {
                const isActive = grid[activeTrackId][idx];
                const isAvailable = idx < patternLength;
                return (
                  <button
                    key={`seq-${idx}`}
                    className={`pad seq-pad ${activeTrackColor} ${isActive ? 'active' : ''} ${!isAvailable ? 'disabled' : ''}`}
                    onClick={() => toggleStep(idx)}
                    disabled={!isAvailable}
                  />
                );
              })}
            </div>

            <div className="pads-label" style={{marginTop: '16px'}}>Note / Drum Triggers</div>
            <div className="pads-grid note-grid">
              {Array.from({ length: NUM_NOTE_PADS }).map((_, idx) => (
                <button
                  key={`note-${idx}`}
                  className={`pad note-pad ${activeTrackColor}`}
                  onMouseDown={() => playNotePad(idx)}
                />
              ))}
            </div>
          </div>
          
          <div className="pattern-length-selector">
            <span>Length: {patternLength}</span>
            <input 
              type="range" min="1" max="32" 
              value={patternLength} 
              onChange={(e) => setPatternLength(parseInt(e.target.value))}
            />
          </div>
        </div>

        {/* RIGHT: AI STUDIO PANEL */}
        <div className="ai-studio-panel">
          <div className="panel-header">
            <h2>AI STUDIO WORKSPACE</h2>
            <div className={`badge ${wsConnected ? 'connected' : 'disconnected'}`}>
              <span style={{ fontSize: '10px' }}>●</span>
              {wsConnected ? 'PORT 8770 ONLINE' : 'BRIDGE OFFLINE'}
            </div>
          </div>

          <div className="agent-prompt-section">
            <h3>Agent Prompt</h3>
            <div className="prompt-input-group">
              <input 
                type="text" 
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="z.B. Generiere düstere Acid-Bassline in A-Moll..."
                onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
              />
              <button onClick={handlePromptSubmit}>Senden</button>
            </div>
          </div>

          <div className="agent-inspect-section">
            <h3>Status & Inspect Widget</h3>
            <pre className="inspect-box">
              {agentOutput}
            </pre>
          </div>

          <div className="sync-section">
            <button
              className="btn-push-slot64"
              onClick={pushToSlot64}
              disabled={isPushing}
            >
              {isPushing ? 'Übertrage...' : '⚡ Push to Slot 64'}
            </button>
            <div className="status-msg">{statusMsg}</div>
          </div>

          <div className="log-section">
            <h3>Live Event-Monitor</h3>
            <div className="log-box">
              {logs.length === 0 ? (
                <div style={{ color: 'var(--text-dim)' }}>Warte auf Events...</div>
              ) : (
                logs.map((log, index) => <div key={index}>{log}</div>)
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
