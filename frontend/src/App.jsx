import React, { useState, useEffect, useRef } from 'react';
import { Plane, Compass, LayoutGrid, Eye, Radio } from 'lucide-react';
import AviationScene3D from './components/AviationScene3D';
import JetCockpitView from './components/JetCockpitView';
import PrimaryFlightDisplay from './components/PrimaryFlightDisplay';
import PowertrainPanel from './components/PowertrainPanel';
import MathPanel from './components/MathPanel';
import ControlDeck from './components/ControlDeck';
import AnalystPanel from './components/AnalystPanel';

const DEFAULT_ROUTES = [
  {
    route_id: 'BLR-IXG',
    name: 'Bengaluru (BLR) ➔ Belagavi (IXG)',
    origin: { iata: 'BLR', name: "Kempegowda Int'l", elevation_ft: 3000, runway_m: 4000, oat_c: 34 },
    destination: { iata: 'IXG', name: 'Belagavi Airport', elevation_ft: 2488, runway_m: 2300 },
    stage_distance_km: 462,
    nominal_cruise_alt_ft: 20000,
  },
  {
    route_id: 'BOM-PNQ',
    name: 'Mumbai (BOM) ➔ Pune (PNQ)',
    origin: { iata: 'BOM', name: 'CSMIA Mumbai', elevation_ft: 39, runway_m: 3660, oat_c: 35 },
    destination: { iata: 'PNQ', name: 'Pune Airport', elevation_ft: 1942, runway_m: 2540 },
    stage_distance_km: 122,
    nominal_cruise_alt_ft: 14000,
  },
  {
    route_id: 'DEL-DED',
    name: 'Delhi (DEL) ➔ Dehradun (DED)',
    origin: { iata: 'DEL', name: 'Indira Gandhi Int', elevation_ft: 777, runway_m: 4430, oat_c: 42 },
    destination: { iata: 'DED', name: 'Jolly Grant Dehradun', elevation_ft: 1827, runway_m: 2140 },
    stage_distance_km: 208,
    nominal_cruise_alt_ft: 16000,
  },
  {
    route_id: 'MAA-TIR',
    name: 'Chennai (MAA) ➔ Tirupati (TIR)',
    origin: { iata: 'MAA', name: 'Chennai Int', elevation_ft: 52, runway_m: 3658, oat_c: 39 },
    destination: { iata: 'TIR', name: 'Tirupati Airport', elevation_ft: 350, runway_m: 2286 },
    stage_distance_km: 115,
    nominal_cruise_alt_ft: 12000,
  },
];

export default function App() {
  const [routes, setRoutes] = useState(DEFAULT_ROUTES);
  const [selectedRouteId, setSelectedRouteId] = useState('BLR-IXG');
  const [hpFraction, setHpFraction] = useState(0.30);
  const [batteryWh, setBatteryWh] = useState(400);
  const [ambientDelta, setAmbientDelta] = useState(0);

  const [cameraMode, setCameraMode] = useState('chase');
  const [isDualMode, setIsDualMode] = useState(true);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'cockpit' | 'external'

  const [simResult, setSimResult] = useState(null);
  const [surrogatePrediction, setSurrogatePrediction] = useState(null);

  // Playback with realistic pacing
  const [isPlaying, setIsPlaying] = useState(true);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // Default to calm 1x
  const timerRef = useRef(null);

  // Fetch routes from backend on mount
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/routes')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setRoutes(data);
        }
      })
      .catch(() => console.log('Using default routes'));
  }, []);

  // Run simulation whenever parameters change
  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        route_id: selectedRouteId,
        hp_fraction: hpFraction,
        battery_wh_per_kg: batteryWh,
        ambient_delta_c: ambientDelta,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        setSimResult(data);
        setPlaybackIndex(0);
      })
      .catch((err) => console.error('Simulation fetch error:', err));

    const currentRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];
    const dist = currentRoute?.stage_distance_km || 462;
    fetch(`http://127.0.0.1:8000/api/surrogate?distance_km=${dist}&hp_fraction=${hpFraction}&battery_wh_per_kg=${batteryWh}&ambient_delta_c=${ambientDelta}`)
      .then((res) => res.json())
      .then((pred) => setSurrogatePrediction(pred))
      .catch(() => {});
  }, [selectedRouteId, hpFraction, batteryWh, ambientDelta]);

  // Telemetry frames
  const hybridFrames = simResult?.telemetry_hybrid || [];
  const convFrames = simResult?.telemetry_conv || [];
  const totalFrames = hybridFrames.length;

  // Realistic Pacing Animation Timer
  useEffect(() => {
    if (!isPlaying || totalFrames === 0) return;

    // Realistic base interval: 650ms per frame divided by playback speed
    const stepInterval = Math.max(80, Math.round(650 / playbackSpeed));

    timerRef.current = setInterval(() => {
      setPlaybackIndex((prev) => {
        if (prev >= totalFrames - 1) {
          setIsPlaying(false); // Pause at destination landing instead of looping abruptly
          return totalFrames - 1;
        }
        return prev + 1;
      });
    }, stepInterval);

    return () => clearInterval(timerRef.current);
  }, [isPlaying, totalFrames, playbackSpeed]);

  // Jump to Flight Phase Handler
  const handleJumpToPhase = (targetPhase) => {
    if (totalFrames === 0) return;
    const targetIdx = hybridFrames.findIndex((f) => f.phase === targetPhase);
    if (targetIdx !== -1) {
      setPlaybackIndex(targetIdx);
      setIsPlaying(true);
    }
  };

  const currentHybridTelemetry = hybridFrames[playbackIndex] || null;
  const currentConvTelemetry = convFrames[playbackIndex] || null;

  return (
    <div className="app-container">
      {/* Top Header Bar */}
      <header className="header-bar">
        <div className="brand-section">
          <div className="brand-icon">
            <Plane style={{ width: 22, height: 22 }} />
          </div>
          <div>
            <div className="brand-title">
              <span>AEROHYBRID FEASIBILITY PLATFORM</span>
              <span className="badge-item highlight-blue">ATR 72-600 CLASS</span>
            </div>
            <div className="brand-subtitle">
              Parallel Hybrid-Electric Propulsion Digital Twin & Indian UDAN Route Benchmarking
            </div>
          </div>
        </div>

        {/* Live Status Badges */}
        <div className="status-badges">
          <div className="badge-item">
            PHASE: <strong>{(currentHybridTelemetry?.phase || 'TAKEOFF').toUpperCase()}</strong>
          </div>
          <div className="badge-item">
            ALT: <strong>{Math.round(currentHybridTelemetry?.altitude_ft || 0)} FT</strong>
          </div>
          <div className="badge-item">
            IAS: <strong>{Math.round(currentHybridTelemetry?.airspeed_kt || 0)} KT</strong>
          </div>
          <div className="badge-item highlight-green">
            FUEL SAVED: -{simResult?.summary?.fuel_saved_pct || 7.1}%
          </div>
        </div>
      </header>

      {/* Main Dashboard Layout */}
      <main className="dashboard-main">
        {/* Cockpit Deck: Left HUD, Center 3D Stage, Right Powertrain */}
        <div className="cockpit-deck">
          {/* Left Column: PFD + Math Panel */}
          <div className="side-hud-column">
            <PrimaryFlightDisplay telemetry={currentHybridTelemetry} />
            <MathPanel telemetry={currentHybridTelemetry} />
          </div>

          {/* Center Stage: Dual-View Flight Deck (Split Screen: Internal Jet Cockpit + External 3D) */}
          <div className="scene-centerpiece">
            {/* View Mode Selector Header Bar */}
            <div className="centerpiece-view-bar">
              <div className="view-mode-selector-group">
                <button
                  className={`view-mode-pill-btn ${viewMode === 'split' ? 'active' : ''}`}
                  onClick={() => setViewMode('split')}
                  title="Side-by-side Dual View: Jet Cockpit + External 3D"
                >
                  <LayoutGrid size={13} />
                  <span>Dual Split (50/50)</span>
                </button>
                <button
                  className={`view-mode-pill-btn ${viewMode === 'cockpit' ? 'active' : ''}`}
                  onClick={() => setViewMode('cockpit')}
                  title="Full Jet Cockpit & Glass Avionics View"
                >
                  <Radio size={13} />
                  <span>Jet Cockpit</span>
                </button>
                <button
                  className={`view-mode-pill-btn ${viewMode === 'external' ? 'active' : ''}`}
                  onClick={() => setViewMode('external')}
                  title="Full External 3D Flight View"
                >
                  <Eye size={13} />
                  <span>External 3D</span>
                </button>
              </div>

              <div className="view-bar-telemetry-summary">
                <span>PHASE: <strong>{(currentHybridTelemetry?.phase || 'TAKEOFF').toUpperCase()}</strong></span>
                <span>ALT: <strong>{Math.round(currentHybridTelemetry?.altitude_ft || 0)} FT</strong></span>
                <span>IAS: <strong>{Math.round(currentHybridTelemetry?.airspeed_kt || 0)} KT</strong></span>
              </div>
            </div>

            {/* Split Screen Dynamic Panes */}
            <div className={`centerpiece-split-container view-${viewMode}`}>
              {/* Left Pane: Jet Glass Cockpit View */}
              {(viewMode === 'split' || viewMode === 'cockpit') && (
                <div className="split-pane split-pane-cockpit">
                  <div className="split-pane-header">
                    <span>🛩️ JET FLIGHT DECK (INTERNAL HUD & GLASS MFD)</span>
                  </div>
                  <JetCockpitView
                    telemetry={currentHybridTelemetry}
                    summary={simResult?.summary}
                    isDualMode={isDualMode}
                  />
                </div>
              )}

              {/* Right Pane: External 3D Aircraft Motion Model */}
              {(viewMode === 'split' || viewMode === 'external') && (
                <div className="split-pane split-pane-external">
                  <div className="split-pane-header external-header">
                    <span>🌐 EXTERNAL 3D MOTION VIEW (ATR-72 DIGITAL TWIN)</span>
                  </div>
                  <AviationScene3D
                    currentTelemetry={currentHybridTelemetry}
                    convTelemetry={currentConvTelemetry}
                    cameraMode={cameraMode}
                    isDualMode={isDualMode}
                  />

                  {/* In-Scene Floating Overlays */}
                  <div className="scene-overlay-top-left">
                    <Compass style={{ width: 13, height: 13, color: 'var(--electric-blue)' }} />
                    <span>
                      <b>CAM:</b> {cameraMode.toUpperCase()} | <b>DUAL:</b> {isDualMode ? 'ON' : 'OFF'}
                    </span>
                  </div>

                  {isDualMode && (
                    <div className="scene-overlay-top-right">
                      <span style={{ color: 'var(--electric-blue)', fontWeight: 700 }}>
                        <span className="legend-dot-hybrid" /> Hybrid (Electric Boost)
                      </span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        <span className="legend-dot-conv" /> Baseline (Kerosene)
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Powertrain Telemetry */}
          <div className="side-hud-column">
            <PowertrainPanel
              telemetry={currentHybridTelemetry}
              summary={simResult?.summary}
            />
          </div>
        </div>

        {/* Bottom Section: Scenario Control Deck & AI Feasibility Analyst */}
        <div className="bottom-controls-grid">
          <ControlDeck
            routes={routes}
            selectedRouteId={selectedRouteId}
            onRouteChange={setSelectedRouteId}
            hpFraction={hpFraction}
            onHpChange={setHpFraction}
            batteryWh={batteryWh}
            onBatteryWhChange={setBatteryWh}
            ambientDelta={ambientDelta}
            onAmbientDeltaChange={setAmbientDelta}
            cameraMode={cameraMode}
            onCameraModeChange={setCameraMode}
            isDualMode={isDualMode}
            onDualModeToggle={() => setIsDualMode((prev) => !prev)}
            isPlaying={isPlaying}
            onPlayPauseToggle={() => setIsPlaying((prev) => !prev)}
            onReset={() => {
              setPlaybackIndex(0);
              setIsPlaying(true);
            }}
            playbackIndex={playbackIndex}
            totalFrames={totalFrames}
            onScrub={setPlaybackIndex}
            playbackSpeed={playbackSpeed}
            onSpeedChange={setPlaybackSpeed}
            onJumpToPhase={handleJumpToPhase}
            currentPhase={currentHybridTelemetry?.phase || 'takeoff'}
          />

          <AnalystPanel
            analysis={simResult?.ai_analyst}
            surrogatePrediction={surrogatePrediction}
          />
        </div>
      </main>
    </div>
  );
}
