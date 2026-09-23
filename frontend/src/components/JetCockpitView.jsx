import React, { useMemo } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2, Zap, Fuel, Activity, Compass, Gauge } from 'lucide-react';

/**
 * JetCockpitView
 * Authentic Jet Flight Deck with dynamic out-the-window horizon, Head-Up Display (HUD),
 * dual glass MFD/EICAS instrumentation, glare-shield annunciators, and animated controls deck.
 */
export default function JetCockpitView({ telemetry, summary, isDualMode = true }) {
  // Extract and sanitize live calculation telemetry
  const altFt = Math.round(telemetry?.altitude_ft || 0);
  const aglFt = Math.round(telemetry?.agl_ft || Math.max(0, altFt - 3000));
  const iasKt = Math.round(telemetry?.airspeed_kt || 0);
  const tasKt = Math.round(telemetry?.tas_kt || Math.round(iasKt * (1 + altFt * 0.000015)));
  const pitchDeg = Math.max(-20, Math.min(25, Number((telemetry?.pitch_deg || 0).toFixed(1))));
  const vsiFpm = Math.round(telemetry?.vertical_speed_fpm || 0);
  const phase = (telemetry?.phase || 'TAKEOFF').toUpperCase();
  const socPct = Math.round(telemetry?.battery_soc_pct ?? 100);
  const batTempC = Number((telemetry?.battery_temp_c || 28.5).toFixed(1));
  const pTotalKw = Math.round(telemetry?.p_shaft_total_kw || 0);
  const pIceKw = Math.round(telemetry?.p_ice_kw || 0);
  const pEmKw = Math.round(telemetry?.p_em_kw || 0);
  const isGearDown = telemetry?.gear_extended ?? (altFt < 400 || phase === 'TAKEOFF' || phase === 'LANDING');

  // Computed Engine & Control Values
  const maxKw = 3500; // Reference maximum continuous shaft power
  const throttlePct = Math.min(100, Math.max(10, Math.round((pTotalKw / maxKw) * 100)));
  const trqPct = Math.min(110, Math.max(15, Math.round((pIceKw / 2500) * 100)));
  const npPct = iasKt < 30 ? 70 : phase === 'TAKEOFF' ? 100 : phase === 'CLIMB' ? 95 : 82; // Prop RPM %
  const ittC = Math.round(520 + (trqPct / 100) * 290); // Interstage Turbine Temp (°C)
  const fuelFlowKgh = Math.round(pIceKw * 0.22); // Approximate fuel burn kg/h

  // Electric split percentage
  const electricSplitPct = pTotalKw > 0 ? Math.round((pEmKw / pTotalKw) * 100) : 0;
  const keroseneSplitPct = 100 - electricSplitPct;

  // Flaps angle based on phase
  const flapsDeg = phase === 'LANDING' ? 30 : phase === 'TAKEOFF' || phase === 'APPROACH' ? 15 : 0;

  // CWP Caution & Warnings
  const isMasterWarning = socPct < 15 || batTempC > 48;
  const isMasterCaution = (socPct >= 15 && socPct < 25) || batTempC > 42;

  // Horizon displacement calculation (-1° pitch shifts horizon ~3.5px)
  const horizonPitchOffset = pitchDeg * 4.2;

  // Autopilot Status
  const apActive = phase === 'CLIMB' || phase === 'CRUISE' || phase === 'DESCENT';
  const lnavActive = apActive;
  const vnavActive = apActive;
  const spdHold = phase === 'CRUISE';

  return (
    <div className="jet-cockpit-container">
      {/* 1. OUT-THE-WINDSHIELD DYNAMIC SCENERY */}
      <div className="windshield-viewport">
        {/* Dynamic Sky & Horizon */}
        <div
          className="sky-ground-world"
          style={{
            transform: `translateY(${horizonPitchOffset}px)`,
          }}
        >
          <div className="sky-layer">
            <div className="sun-glare" />
            <div className="cloud-haze" />
          </div>
          <div className="horizon-line" />
          <div className="ground-layer">
            <div className="runway-perspective-grid" />
          </div>
        </div>

        {/* Cockpit Canopy Struts & Glass Reflections */}
        <div className="canopy-glass-overlay">
          <div className="windshield-frame-left" />
          <div className="windshield-frame-center" />
          <div className="windshield-frame-right" />
          <div className="wiper-blade" />
          <div className="glass-specular-sheen" />
        </div>

        {/* 2. COLLIMATED HEAD-UP DISPLAY (HUD) */}
        <div className="hud-projection-layer">
          <div className="hud-frame">
            {/* Top Compass Heading Tape */}
            <div className="hud-compass-tape">
              <span>080</span>
              <span>090</span>
              <span className="hud-heading-current">▲ 095°</span>
              <span>100</span>
              <span>110</span>
            </div>

            {/* Center Pitch Ladder & Boresight */}
            <div className="hud-pitch-ladder" style={{ transform: `translateY(${pitchDeg * 3}px)` }}>
              <div className="pitch-bar plus-10">+10 ─── ─── +10</div>
              <div className="pitch-bar plus-05">+05 ──   ── +05</div>
              <div className="hud-boresight">
                <div className="crosshair-dot" />
                <div className="flight-path-vector" title="Flight Path Vector" />
              </div>
              <div className="pitch-bar minus-05">-05 ╌╌   ╌╌ -05</div>
              <div className="pitch-bar minus-10">-10 ╌╌╌ ╌╌╌ -10</div>
            </div>

            {/* Left Airspeed Tape */}
            <div className="hud-speed-tape">
              <span className="tape-label">IAS</span>
              <div className="tape-digital-box">{iasKt}</div>
              <span className="tape-unit">KT</span>
              <span className="tape-sub-tas">TAS {tasKt}</span>
            </div>

            {/* Right Altitude & VSI Tape */}
            <div className="hud-alt-tape">
              <span className="tape-label">ALT</span>
              <div className="tape-digital-box">{altFt}</div>
              <span className="tape-unit">FT</span>
              <div className="tape-radalt">AGL {aglFt} FT</div>
              <div className="hud-vsi-indicator">
                {vsiFpm >= 0 ? `▲ +${vsiFpm}` : `▼ ${vsiFpm}`} <small>FPM</small>
              </div>
            </div>

            {/* Bottom HUD Telemetry Status */}
            <div className="hud-bottom-status">
              <span className="hud-phase-flag">MODE: {phase}</span>
              <span className="hud-powertrain-flag">
                HYBRID PWR: {pTotalKw} kW ({electricSplitPct}% ELEC)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. GLARESHIELD & MASTER ANNUNCIATOR PANEL */}
      <div className="cockpit-glareshield">
        {/* Master Warning / Caution */}
        <div className="annunciator-group">
          <button
            className={`annunciator-btn warning-light ${isMasterWarning ? 'active-pulse' : ''}`}
            title="Master Warning: Critical Thermal or Voltage Trigger"
          >
            <ShieldAlert size={14} />
            <span>MSTR WARN</span>
          </button>
          <button
            className={`annunciator-btn caution-light ${isMasterCaution ? 'active-pulse' : ''}`}
            title="Master Caution: Reserve Threshold"
          >
            <AlertTriangle size={14} />
            <span>MSTR CAUT</span>
          </button>
        </div>

        {/* Autopilot Flight Guidance MCP (Mode Control Panel) */}
        <div className="mcp-autopilot-bar">
          <div className={`mcp-btn ${apActive ? 'mcp-engaged' : ''}`}>AP 1</div>
          <div className={`mcp-btn ${lnavActive ? 'mcp-engaged' : ''}`}>LNAV</div>
          <div className={`mcp-btn ${vnavActive ? 'mcp-engaged' : ''}`}>VNAV</div>
          <div className={`mcp-btn ${spdHold ? 'mcp-engaged' : ''}`}>SPD HOLD</div>
          <div className="mcp-readout">
            <span className="mcp-label">HDG</span>
            <span className="mcp-val">095°</span>
          </div>
          <div className="mcp-readout">
            <span className="mcp-label">CRZ ALT</span>
            <span className="mcp-val">20,000</span>
          </div>
        </div>

        {/* Flight Director & Phase Status */}
        <div className="glareshield-status">
          <span className="flight-deck-tag">FLIGHT DIRECTOR: ACTIVE</span>
          <span className="flight-deck-route">
            STATUS: <strong style={{ color: '#38BDF8' }}>{phase}</strong>
          </span>
        </div>
      </div>

      {/* 4. MAIN INSTRUMENT PANEL: DUAL GLASS MFD & EICAS SCREENS */}
      <div className="main-instrument-deck">
        {/* MFD 1: Primary Flight Display (PFD) Electronic Screen */}
        <div className="glass-mfd-display">
          <div className="mfd-screen-bezel">
            <div className="mfd-top-bar">
              <span className="mfd-title">PFD 1 • ATR 72-600 EFIS</span>
              <span className="mfd-clock">UTC 12:45:10</span>
            </div>

            {/* Artificial Horizon Instrument Graphic */}
            <div className="pfd-attitude-indicator">
              <div
                className="attitude-sphere"
                style={{
                  transform: `translateY(${pitchDeg * 3.5}px)`,
                }}
              >
                <div className="attitude-sky" />
                <div className="attitude-horizon-bar" />
                <div className="attitude-ground" />
              </div>
              <div className="attitude-fixed-aircraft" />
              <div className="attitude-pitch-ticks">
                <div className="tick-p10">10</div>
                <div className="tick-zero">───</div>
                <div className="tick-m10">-10</div>
              </div>
            </div>

            {/* PFD Bottom Data Grid */}
            <div className="pfd-data-grid">
              <div className="pfd-metric">
                <span className="lbl">IAS / TAS</span>
                <span className="val">{iasKt} / {tasKt} <small>KT</small></span>
              </div>
              <div className="pfd-metric">
                <span className="lbl">ALTITUDE</span>
                <span className="val">{altFt.toLocaleString()} <small>FT</small></span>
              </div>
              <div className="pfd-metric">
                <span className="lbl">V/S RATE</span>
                <span className="val" style={{ color: vsiFpm >= 0 ? '#4ADE80' : '#F87171' }}>
                  {vsiFpm > 0 ? `+${vsiFpm}` : vsiFpm} <small>FPM</small>
                </span>
              </div>
              <div className="pfd-metric">
                <span className="lbl">RADIO ALT</span>
                <span className="val">{aglFt} <small>FT AGL</small></span>
              </div>
            </div>
          </div>
        </div>

        {/* MFD 2: Engine & Hybrid Powertrain EICAS */}
        <div className="glass-mfd-display">
          <div className="mfd-screen-bezel">
            <div className="mfd-top-bar">
              <span className="mfd-title">EICAS • PW127M & HYBRID BUS</span>
              <span className="mfd-status-tag">BUS: 800V OK</span>
            </div>

            {/* Dual Engine Gauges Grid */}
            <div className="eicas-gauges-grid">
              {/* Turboprop ICE Engines */}
              <div className="eicas-gauge-card">
                <div className="gauge-header">
                  <Fuel size={13} style={{ color: '#F59E0B' }} />
                  <span>PW127M TURBOPROPS (L & R)</span>
                </div>
                <div className="gauge-metrics-row">
                  <div className="gauge-item">
                    <span className="gauge-lbl">TORQUE</span>
                    <span className="gauge-num">{trqPct}%</span>
                    <div className="gauge-mini-bar">
                      <div className="gauge-fill-ice" style={{ width: `${Math.min(100, trqPct)}%` }} />
                    </div>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">NP RPM</span>
                    <span className="gauge-num">{npPct}%</span>
                    <div className="gauge-mini-bar">
                      <div className="gauge-fill-np" style={{ width: `${Math.min(100, npPct)}%` }} />
                    </div>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">ITT</span>
                    <span className="gauge-num">{ittC}°C</span>
                    <div className="gauge-mini-bar">
                      <div className="gauge-fill-itt" style={{ width: `${Math.min(100, (ittC / 900) * 100)}%` }} />
                    </div>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">FF</span>
                    <span className="gauge-num">{fuelFlowKgh} <small>kg/h</small></span>
                  </div>
                </div>
              </div>

              {/* Electric Motor & Battery Gauges */}
              <div className="eicas-gauge-card">
                <div className="gauge-header">
                  <Zap size={13} style={{ color: '#38BDF8' }} />
                  <span>HYBRID EM & BATTERY PACK</span>
                </div>
                <div className="gauge-metrics-row">
                  <div className="gauge-item">
                    <span className="gauge-lbl">EM SHAFT</span>
                    <span className="gauge-num" style={{ color: '#38BDF8' }}>{pEmKw} kW</span>
                    <div className="gauge-mini-bar">
                      <div className="gauge-fill-em" style={{ width: `${Math.min(100, (pEmKw / 1000) * 100)}%` }} />
                    </div>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">BATTERY SOC</span>
                    <span
                      className="gauge-num"
                      style={{ color: socPct > 35 ? '#4ADE80' : socPct > 20 ? '#FBBF24' : '#F87171' }}
                    >
                      {socPct}%
                    </span>
                    <div className="gauge-mini-bar">
                      <div
                        className="gauge-fill-soc"
                        style={{
                          width: `${socPct}%`,
                          backgroundColor: socPct > 35 ? '#4ADE80' : socPct > 20 ? '#FBBF24' : '#F87171',
                        }}
                      />
                    </div>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">CELL TEMP</span>
                    <span className="gauge-num">{batTempC}°C</span>
                  </div>
                  <div className="gauge-item">
                    <span className="gauge-lbl">PWR SPLIT</span>
                    <span className="gauge-num">{keroseneSplitPct}% / {electricSplitPct}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Total Power & Fuel Savings Banner */}
            <div className="eicas-bottom-banner">
              <span>TOTAL COMBINED POWER: <strong>{pTotalKw.toLocaleString()} kW</strong></span>
              <span className="fuel-saved-pill">
                TRIP FUEL REDUCTION: -{summary?.fuel_saved_pct || 7.1}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. CENTER PEDESTAL & COCKPIT PHYSICAL CONTROLS DECK */}
      <div className="cockpit-pedestal-deck">
        {/* Animated Throttle Quadrant */}
        <div className="pedestal-quadrant">
          <div className="quadrant-header">
            <span>POWER LEVERS (THROTTLE)</span>
            <span className="throttle-val">{throttlePct}% COMMAND</span>
          </div>
          <div className="throttle-track-housing">
            <div className="throttle-detents">
              <span>MAX</span>
              <span>CLB</span>
              <span>CRZ</span>
              <span>IDLE</span>
            </div>
            <div className="throttle-levers-wrapper">
              {/* Engine 1 Lever */}
              <div className="throttle-lever-slot">
                <div
                  className="throttle-lever-handle ice-handle"
                  style={{ bottom: `${throttlePct * 0.75}%` }}
                >
                  <span className="lever-tag">ENG 1</span>
                </div>
              </div>
              {/* Electric Boost Lever */}
              <div className="throttle-lever-slot">
                <div
                  className="throttle-lever-handle electric-handle"
                  style={{ bottom: `${Math.min(90, Math.max(10, electricSplitPct * 2))}%` }}
                >
                  <span className="lever-tag">EM BOOST</span>
                </div>
              </div>
              {/* Engine 2 Lever */}
              <div className="throttle-lever-slot">
                <div
                  className="throttle-lever-handle ice-handle"
                  style={{ bottom: `${throttlePct * 0.75}%` }}
                >
                  <span className="lever-tag">ENG 2</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Flaps & Landing Gear Indicators */}
        <div className="pedestal-subsystems">
          {/* Landing Gear Position Indicator */}
          <div className="gear-panel-box">
            <span className="gear-panel-title">LANDING GEAR</span>
            <div className="gear-lights-row">
              <div className={`gear-light ${isGearDown ? 'gear-green' : 'gear-up'}`}>
                <span>NOSE</span>
                <div className="indicator-bulb" />
              </div>
              <div className={`gear-light ${isGearDown ? 'gear-green' : 'gear-up'}`}>
                <span>LEFT</span>
                <div className="indicator-bulb" />
              </div>
              <div className={`gear-light ${isGearDown ? 'gear-green' : 'gear-up'}`}>
                <span>RIGHT</span>
                <div className="indicator-bulb" />
              </div>
            </div>
            <div className="gear-handle-position">
              <span>LEVER: <strong>{isGearDown ? 'DOWN' : 'UP & LOCKED'}</strong></span>
            </div>
          </div>

          {/* Flaps Lever Indicator */}
          <div className="flaps-panel-box">
            <span className="flaps-panel-title">WING FLAPS</span>
            <div className="flaps-scale">
              <div className={`flaps-step ${flapsDeg === 0 ? 'flaps-active' : ''}`}>
                <span>0°</span>
                <small>CRUISE</small>
              </div>
              <div className={`flaps-step ${flapsDeg === 15 ? 'flaps-active' : ''}`}>
                <span>15°</span>
                <small>T/O • APPR</small>
              </div>
              <div className={`flaps-step ${flapsDeg === 30 ? 'flaps-active' : ''}`}>
                <span>30°</span>
                <small>LANDING</small>
              </div>
            </div>
            <div className="flaps-current-readout">
              POSITION: <strong>{flapsDeg}°</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
