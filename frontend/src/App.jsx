import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const TRACKS = [
  { id: 'synth1', name: 'Synth 1', color: 'synth1', channel: 0, defaultNote: 60 },
  { id: 'synth2', name: 'Synth 2', color: 'synth2', channel: 1, defaultNote: 64 },
  { id: 'drum1', name: 'Drum 1', color: 'drum1', channel: 9, defaultNote: 60 },
  { id: 'drum2', name: 'Drum 2', color: 'drum2', channel: 9, defaultNote: 62 },
];

const NUM_STEPS = 8; // 4 rows x 8 pads = 32 pads

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Verbinde zu Bridge auf Port 8770...');
  const [logs, setLogs] = useState([]);
  const [grid, setGrid] = useState({
    synth1: [true, false, false, false, true, false, false, false],
    synth2: [false, false, true, false, false, false, true, false],
    drum1: [true, false, false, false, true, false, false, false],
    drum2: [false, false, true, false, false, false, true, false],
  });
  const [isPushing, setIsPushing] = useState(false);

  const audioCtxRef = useRef(null);

  // Web Audio API Synth Bleep for live preview
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

  // WebSocket Connection to Bridge (ws://localhost:8770/ws)
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

  const togglePad = async (trackId, stepIdx) => {
    const track = TRACKS.find((t) => t.id === trackId);
    const nextState = !grid[trackId][stepIdx];

    setGrid((prev) => ({
      ...prev,
      [trackId]: prev[trackId].map((val, idx) => (idx === stepIdx ? nextState : val)),
    }));

    if (nextState && track) {
      // Audio Preview
      const freq = 130 * Math.pow(1.05946, track.defaultNote - 48);
      playWebAudioTone(freq);

      // Trigger Note on Hardware Bridge
      try {
        await fetch('http://localhost:8770/midi/note', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channel: track.channel,
            note: track.defaultNote,
            velocity: 100,
            duration_s: 0.1,
          }),
        });
      } catch {
        // Bridge may be in mock or offline
      }
    }
  };

  // Push to Safe Slot 64
  const pushToSlot64 = async () => {
    setIsPushing(true);
    addLog('Erstelle Song-Payload für Safe-Slot 64...');

    const compiledTracks = {};
    TRACKS.forEach((track) => {
      const steps = {};
      grid[track.id].forEach((isActive, idx) => {
        if (isActive) {
          steps[String(idx)] = {
            note: track.defaultNote,
            velocity: 100,
            gate: 0.5,
          };
        }
      });
      compiledTracks[track.id] = {
        length: NUM_STEPS,
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

  const clearAll = () => {
    const emptyGrid = {};
    TRACKS.forEach((t) => {
      emptyGrid[t.id] = Array(NUM_STEPS).fill(false);
    });
    setGrid(emptyGrid);
    addLog('Grid geleert.');
  };

  return (
    <div className="studio-container">
      <div className="studio-header">
        <div className="studio-title">
          <h1>CIRCUIT TRACKS AI STUDIO</h1>
          <div className="studio-subtitle">
            Meilenstein 5: 4x8 Pad Grid & Live WebSocket Synchronisation
          </div>
        </div>
        <div className={`badge ${wsConnected ? 'connected' : 'disconnected'}`}>
          <span style={{ fontSize: '10px' }}>●</span>
          {wsConnected ? 'PORT 8770 ONLINE' : 'BRIDGE OFFLINE'}
        </div>
      </div>

      <div className="controls-bar">
        <button
          className="btn-push-slot64"
          onClick={pushToSlot64}
          disabled={isPushing}
        >
          {isPushing ? 'Übertrage...' : '⚡ Push to Slot 64'}
        </button>
        <button className="btn-clear" onClick={clearAll}>
          Pads leeren
        </button>
        <div style={{ marginLeft: 'auto', fontSize: '0.85rem', color: 'var(--text-dim)' }}>
          {statusMsg}
        </div>
      </div>

      <div className="grid-panel">
        {TRACKS.map((track) => (
          <div key={track.id} className="track-row">
            <div className="track-label" style={{ color: `var(--accent-${track.color === 'drum1' ? 'yellow' : track.color === 'drum2' ? 'magenta' : track.color === 'synth2' ? 'blue' : 'cyan'})` }}>
              {track.name}
            </div>
            <div className="pads-row">
              {grid[track.id].map((active, stepIdx) => (
                <button
                  key={stepIdx}
                  className={`pad ${track.color} ${active ? 'active' : ''}`}
                  onClick={() => togglePad(track.id, stepIdx)}
                  title={`${track.name} Step ${stepIdx + 1}`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '8px', fontSize: '0.85rem', fontWeight: 600 }}>
        Live Event-Monitor (WebSocket ws://localhost:8770/ws):
      </div>
      <div className="log-box">
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)' }}>Warte auf Events...</div>
        ) : (
          logs.map((log, index) => <div key={index}>{log}</div>)
        )}
      </div>
    </div>
  );
}
