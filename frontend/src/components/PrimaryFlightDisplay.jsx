import React from 'react';

/**
 * Primary Flight Display (PFD) component with Vanilla CSS.
 */
export default function PrimaryFlightDisplay({ telemetry }) {
  const pitchDeg = telemetry?.pitch_deg || 0;
  const rollDeg = telemetry?.roll_deg || 0;
  const speedKt = telemetry?.airspeed_kt || 0;
  const altFt = telemetry?.altitude_ft || 0;
  const vsiFpm = telemetry?.climb_rate_fpm || 0;
  const phase = (telemetry?.phase || 'TAKEOFF ROLL').toUpperCase();
  const hpPct = Math.round((telemetry?.actual_hp || 0.3) * 100);

  // Pitch translation clamped
  const pitchOffset = Math.max(-60, Math.min(60, pitchDeg * 3.2));

  return (
    <div className="pfd-container">
      {/* Flight Mode Annunciator (FMA) */}
      <div className="pfd-fma">
        <span className="badge-item highlight-blue">HEP {hpPct}%</span>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)', letterSpacing: '0.04em' }}>
          {phase}
        </span>
        <span className="badge-item highlight-green">VNAV ON</span>
      </div>

      {/* Center Attitude Director Indicator */}
      <div className="pfd-screen">
        {/* Horizon Rotator */}
        <div
          className="pfd-horizon-rotator"
          style={{
            transform: `translateY(${pitchOffset}px) rotate(${-rollDeg}deg)`,
          }}
        >
          <div className="pfd-sky">
            <div className="pfd-pitch-line">
              <span className="pfd-pitch-label" style={{ left: '-18px' }}>+10</span>
              <span className="pfd-pitch-label" style={{ right: '-18px' }}>+10</span>
            </div>
          </div>
          <div className="pfd-ground">
            <div className="pfd-pitch-line">
              <span className="pfd-pitch-label" style={{ left: '-18px' }}>-10</span>
              <span className="pfd-pitch-label" style={{ right: '-18px' }}>-10</span>
            </div>
          </div>
        </div>

        {/* Aircraft Center Reticle */}
        <div className="pfd-crosshair">
          <div className="crosshair-wing" />
          <div className="crosshair-dot" />
          <div className="crosshair-wing" />
        </div>

        {/* Airspeed Tape (KIAS) */}
        <div className="pfd-tape-left">
          <span className="tape-label">IAS</span>
          <span className="tape-value">{Math.round(speedKt)}</span>
          <span className="tape-sub">VR 108</span>
        </div>

        {/* Altitude Tape (ft MSL) */}
        <div className="pfd-tape-right">
          <span className="tape-label">ALT</span>
          <span className="tape-value">{Math.round(altFt)}</span>
          <span className="tape-sub">{vsiFpm >= 0 ? `+${Math.round(vsiFpm)}` : Math.round(vsiFpm)}</span>
        </div>
      </div>

      {/* Compass Bar */}
      <div className="pfd-compass-bar">
        <span>HDG 085°</span>
        <span style={{ color: 'var(--text-muted)' }}>|</span>
        <span style={{ color: 'var(--electric-blue)' }}>PITCH {pitchDeg.toFixed(1)}°</span>
        <span style={{ color: 'var(--text-muted)' }}>|</span>
        <span>GS {Math.round(speedKt * 1.05)}kt</span>
      </div>
    </div>
  );
}
