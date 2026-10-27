import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const TRACKS = [
  { id: 'synth1', name: 'Synth 1', color: 'synth1', hex: '#00d2d3', channel: 0, defaultNote: 60 },
  { id: 'synth2', name: 'Synth 2', color: 'synth2', hex: '#54a0ff', channel: 1, defaultNote: 64 },
  { id: 'midi1', name: 'MIDI 1', color: 'midi1', hex: '#a29bfe', channel: 2, defaultNote: 60 },
  { id: 'midi2', name: 'MIDI 2', color: 'midi2', hex: '#6c5ce7', channel: 3, defaultNote: 60 },
  { id: 'drum1', name: 'Drum 1', color: 'drum1', hex: '#feca57', channel: 9, defaultNote: 60 },
  { id: 'drum2', name: 'Drum 2', color: 'drum2', hex: '#ff9f43', channel: 9, defaultNote: 62 },
  { id: 'drum3', name: 'Drum 3', color: 'drum3', hex: '#ff9ff3', channel: 9, defaultNote: 64 },
  { id: 'drum4', name: 'Drum 4', color: 'drum4', hex: '#ff6b6b', channel: 9, defaultNote: 65 },
];

const NUM_STEPS = 16;
const NUM_NOTE_PADS = 16;

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Verbinde zu Bridge...');
  const [logs, setLogs] = useState([]);
  
  const [activeTrackId, setActiveTrackId] = useState('synth1');
  const [patternLength, setPatternLength] = useState(16);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [macros, setMacros] = useState(Array(8).fill(64));
  
  // Master Controls
  const [masterVol, setMasterVol] = useState(100);
  const [masterFilter, setMasterFilter] = useState(64);
  const [bpm, setBpm] = useState(120);
  const [swing, setSwing] = useState(50);
  
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
    let isMounted = true;

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!isMounted) return;
          setWsConnected(true);
          setStatusMsg('Verbunden mit Bridge');
          addLog('WebSocket-Verbindung hergestellt');
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            addLog(`Event: ${data.type || 'msg'} ${JSON.stringify(data.data || {})}`);
          } catch {
            addLog(`WS: ${event.data}`);
          }
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setWsConnected(false);
          setStatusMsg('Getrennt. Neuer Versuch...');
          timer = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (err) {
        if (!isMounted) return;
        setWsConnected(false);
        setStatusMsg('Bridge offline (Mock)');
        addLog(`WS Error: ${err.message}`);
      }
    };

    connectWs();
    
    return () => {
      isMounted = false;
      if (ws) {
        ws.onclose = null; // Prevent reconnect timer from firing on unmount
        ws.close();
      }
      if (timer) clearTimeout(timer);
    };
  }, []);

  // Sequencer Clock
  useEffect(() => {
    let intervalId;
    if (isPlaying) {
      const stepTimeMs = (60 / bpm / 4) * 1000;
      intervalId = setInterval(() => {
        setCurrentStep((prev) => (prev + 1) % patternLength);
      }, stepTimeMs);
    } else {
      setCurrentStep(0);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPlaying, bpm, patternLength]);

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
      await fetch('/midi/note', {
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
      await fetch('/midi/realtime', {
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
      await fetch('/midi/cc', {
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
        steps, // Removed 'length' to comply with backend schema
      };
    });

    const songPayload = {
      name: 'Slot64Push',
      bpm: bpm,
      patterns: {
        p1: {
          tracks: compiledTracks,
        },
      },
    };

    try {
      const response = await fetch('/session/upload', {
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

  const activeTrack = TRACKS.find(t => t.id === activeTrackId);
  const activeTrackColor = activeTrack?.color || 'synth1';
  const activeTrackHex = activeTrack?.hex || '#00d2d3';

  return (
    <div className="app-container">
      <div className="split-layout">
        
        {/* LEFT: HARDWARE DECK (65%) */}
        <div className="hardware-deck">
          <div className="hardware-chassis">
            
            {/* Top Section: Master & Macros */}
            <div className="deck-top-section">
              <div className="master-controls">
                <div className="knob-group">
                  <div className="knob-label">Master Vol</div>
                  <input type="range" min="0" max="127" value={masterVol} onChange={e => setMasterVol(e.target.value)} className="master-knob" />
                </div>
                <div className="knob-group">
                  <div className="knob-label">Master Filter</div>
                  <input type="range" min="0" max="127" value={masterFilter} onChange={e => setMasterFilter(e.target.value)} className="master-knob filter-knob" />
                </div>
                <div className="bpm-display">
                  <div className="bpm-value">{bpm} BPM</div>
                  <div className="bpm-controls">
                    <button onClick={() => setBpm(b => b + 1)}>▲</button>
                    <button onClick={() => setBpm(b => b - 1)}>▼</button>
                  </div>
                </div>
                <div className="knob-group">
                  <div className="knob-label">Swing</div>
                  <input type="range" min="0" max="100" value={swing} onChange={e => setSwing(e.target.value)} className="master-knob" />
                </div>
              </div>

              <div className="macros-grid">
                {macros.map((val, idx) => (
                  <div key={idx} className="macro-knob-container">
                    <div className="macro-ring" style={{ borderColor: activeTrackHex, opacity: val / 127 + 0.2 }}></div>
                    <input 
                      type="range" 
                      min="0" max="127" 
                      value={val} 
                      onChange={(e) => handleMacroChange(idx, parseInt(e.target.value))}
                      className="macro-slider"
                    />
                    <div className="macro-label">Macro {idx + 1}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Middle Section: Track Selector */}
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

            {/* Bottom Section: 32-Pad Matrix & Transport */}
            <div className="deck-bottom-section">
              <div className="transport-sidebar">
                <button className={`btn-transport play ${isPlaying ? 'active' : ''}`} onClick={() => handleTransport('start')}>▶</button>
                <button className="btn-transport stop" onClick={() => handleTransport('stop')}>■</button>
                
                <div className="pattern-length-control">
                  <div className="length-label">Length: {patternLength}</div>
                  <input 
                    type="range" min="1" max="32" 
                    value={patternLength} 
                    onChange={(e) => setPatternLength(parseInt(e.target.value))}
                    className="length-slider"
                  />
                </div>
              </div>

              <div className="pad-matrix">
                {/* Rows 1 & 2: Sequencer */}
                <div className="matrix-section-label">Sequencer</div>
                <div className="pads-grid">
                  {Array.from({ length: NUM_STEPS }).map((_, idx) => {
                    const isActive = grid[activeTrackId][idx];
                    const isAvailable = idx < patternLength;
                    const isPlayhead = isPlaying && currentStep === idx;
                    return (
                      <button
                        key={`seq-${idx}`}
                        className={`pad seq-pad ${activeTrackColor} ${isActive ? 'active' : ''} ${!isAvailable ? 'disabled' : ''} ${isPlayhead ? 'current-playhead' : ''}`}
                        onClick={() => toggleStep(idx)}
                        disabled={!isAvailable}
                      />
                    );
                  })}
                </div>

                {/* Rows 3 & 4: Notes / Triggers */}
                <div className="matrix-section-label" style={{marginTop: '12px'}}>Notes / Triggers</div>
                <div className="pads-grid">
                  {Array.from({ length: NUM_NOTE_PADS }).map((_, idx) => (
                    <button
                      key={`note-${idx}`}
                      className={`pad note-pad ${activeTrackColor}`}
                      onMouseDown={() => playNotePad(idx)}
                    />
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* RIGHT: AI STUDIO PANEL (35%) */}
        <div className="ai-studio-panel">
          <div className="panel-header">
            <h2>AI STUDIO WORKSPACE</h2>
            <div className={`badge ${wsConnected ? 'connected' : 'disconnected'}`}>
              <span style={{ fontSize: '10px' }}>●</span>
              {wsConnected ? 'BRIDGE ONLINE' : 'BRIDGE OFFLINE'}
            </div>
          </div>

          <div className="agent-prompt-section">
            <h3>Agent Prompt</h3>
            <div className="prompt-input-group">
              <input 
                type="text" 
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="z.B. Acid Bassline in Am..."
                onKeyDown={(e) => e.key === 'Enter' && handlePromptSubmit()}
              />
              <button onClick={handlePromptSubmit}>Generate</button>
            </div>
          </div>

          <div className="agent-inspect-section">
            <h3>DSL / Pattern Inspector</h3>
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
