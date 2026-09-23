import React from 'react';
import { Play, Pause, RotateCcw, Camera, MapPin, Eye, FastForward } from 'lucide-react';

export default function ControlDeck({
  routes,
  selectedRouteId,
  onRouteChange,
  hpFraction,
  onHpChange,
  batteryWh,
  onBatteryWhChange,
  ambientDelta,
  onAmbientDeltaChange,
  cameraMode,
  onCameraModeChange,
  isDualMode,
  onDualModeToggle,
  isPlaying,
  onPlayPauseToggle,
  onReset,
  playbackIndex,
  totalFrames,
  onScrub,
  playbackSpeed,
  onSpeedChange,
  onJumpToPhase,
  currentPhase,
}) {
  const currentRoute = routes?.find((r) => r.route_id === selectedRouteId) || routes?.[0];

  return (
    <div className="card-panel">
      {/* Top Row: Route & Cam Selection */}
      <div className="controls-top-row">
        {/* Route Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MapPin style={{ width: 16, height: 16, color: 'var(--electric-blue)' }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Route:</span>
          <select
            value={selectedRouteId}
            onChange={(e) => onRouteChange(e.target.value)}
            className="select-route"
          >
            {routes?.map((r) => (
              <option key={r.route_id} value={r.route_id}>
                {r.name} ({r.stage_distance_km} km)
              </option>
            ))}
          </select>
          {currentRoute && (
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              Elev: {currentRoute.origin.elevation_ft} ft | Rwy: {currentRoute.origin.runway_m} m
            </span>
          )}
        </div>

        {/* Camera Perspectives */}
        <div className="cam-buttons-group">
          <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '0 4px', color: 'var(--text-muted)' }}>
            <Camera style={{ width: 12, height: 12, display: 'inline', verticalAlign: 'middle', marginRight: 2 }} />
            CAM:
          </span>
          {[
            { id: 'chase', label: 'Chase' },
            { id: 'tower', label: 'Tower' },
            { id: 'cockpit', label: 'Cockpit' },
            { id: 'orbit', label: 'Orbit (Drag)' },
          ].map((c) => (
            <button
              key={c.id}
              onClick={() => onCameraModeChange(c.id)}
              className={`cam-btn ${cameraMode === c.id ? 'active' : ''}`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Dual Mode Button */}
        <button
          onClick={onDualModeToggle}
          className={`cam-btn ${isDualMode ? 'active' : ''}`}
          style={{ border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <Eye style={{ width: 14, height: 14 }} />
          <span>Dual Ghost: {isDualMode ? 'ON' : 'OFF'}</span>
        </button>
      </div>

      {/* Flight Phase Jump Shortcuts */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderBottom: '1px solid var(--border-light)', overflowX: 'auto' }}>
        <span style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Jump Phase:
        </span>
        {[
          { label: 'Takeoff Roll (0m)', phase: 'takeoff' },
          { label: 'Climb Boost (FL100)', phase: 'climb' },
          { label: 'Cruise (FL200)', phase: 'cruise' },
          { label: 'Descent / Landing', phase: 'descent' },
        ].map((p) => (
          <button
            key={p.phase}
            onClick={() => onJumpToPhase(p.phase)}
            className={`cam-btn ${currentPhase === p.phase ? 'active' : ''}`}
            style={{ border: '1px solid var(--border-light)', fontSize: '0.68rem', whiteSpace: 'nowrap' }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Middle Row: Engineering Scenario Sliders */}
      <div className="sliders-grid">
        {/* Slider 1: Battery Specific Energy */}
        <div className="slider-group">
          <div className="slider-header">
            <span>Battery Specific Energy</span>
            <strong>{batteryWh} Wh/kg</strong>
          </div>
          <input
            type="range"
            min="250"
            max="600"
            step="25"
            value={batteryWh}
            onChange={(e) => onBatteryWhChange(parseFloat(e.target.value))}
            className="slider-input"
          />
          <div className="slider-ticks">
            <span>250 (Current Li-ion)</span>
            <span>400 (Solid State)</span>
            <span>600 (Advanced)</span>
          </div>
        </div>

        {/* Slider 2: Hybrid Power Split */}
        <div className="slider-group">
          <div className="slider-header">
            <span>Climb Power Boost (H_P)</span>
            <strong>{(hpFraction * 100).toFixed(0)}%</strong>
          </div>
          <input
            type="range"
            min="0"
            max="0.50"
            step="0.05"
            value={hpFraction}
            onChange={(e) => onHpChange(parseFloat(e.target.value))}
            className="slider-input"
          />
          <div className="slider-ticks">
            <span>0% (Conventional)</span>
            <span>30% (RTX Target)</span>
            <span>50% (Heavy Boost)</span>
          </div>
        </div>

        {/* Slider 3: Ambient Summer Delta T */}
        <div className="slider-group">
          <div className="slider-header">
            <span>Indian Summer Offset (ΔT)</span>
            <strong style={{ color: 'var(--kerosene-amber)' }}>+{ambientDelta}°C</strong>
          </div>
          <input
            type="range"
            min="0"
            max="25"
            step="5"
            value={ambientDelta}
            onChange={(e) => onAmbientDeltaChange(parseFloat(e.target.value))}
            className="slider-input"
          />
          <div className="slider-ticks">
            <span>+0°C (Std 15°C)</span>
            <span>+15°C (30°C OAT)</span>
            <span>+25°C (40°C Delhi)</span>
          </div>
        </div>
      </div>

      {/* Bottom Row: Realistic Pacing Playback Controls */}
      <div className="timeline-row">
        <button
          onClick={onPlayPauseToggle}
          className="btn-circle primary"
          title={isPlaying ? 'Pause' : 'Play Flight'}
        >
          {isPlaying ? <Pause style={{ width: 14, height: 14 }} /> : <Play style={{ width: 14, height: 14, marginLeft: 2 }} />}
        </button>

        <button
          onClick={onReset}
          className="btn-circle"
          title="Reset to Runway Threshold"
        >
          <RotateCcw style={{ width: 14, height: 14 }} />
        </button>

        {/* Scrubber */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Frame {playbackIndex + 1} / {totalFrames}
          </span>
          <input
            type="range"
            min="0"
            max={Math.max(0, totalFrames - 1)}
            value={playbackIndex}
            onChange={(e) => onScrub(parseInt(e.target.value))}
            className="slider-input"
            style={{ flex: 1 }}
          />
        </div>

        {/* Pacing Speed Multiplier */}
        <div className="cam-buttons-group">
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', padding: '0 4px' }}>SPEED:</span>
          {[0.5, 1, 2, 4].map((spd) => (
            <button
              key={spd}
              onClick={() => onSpeedChange(spd)}
              className={`cam-btn ${playbackSpeed === spd ? 'active' : ''}`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
