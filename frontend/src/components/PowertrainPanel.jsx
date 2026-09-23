import React from 'react';
import { Zap, Fuel, Flame, Scale, Users } from 'lucide-react';

export default function PowertrainPanel({ telemetry, summary }) {
  const turboshaftKw = telemetry?.turboshaft_power_kw || 1435;
  const electricKw = telemetry?.electric_power_kw || 615;
  const totalPowerKw = turboshaftKw + electricKw;
  const hpPct = totalPowerKw > 0 ? Math.round((electricKw / totalPowerKw) * 100) : 0;

  const fuelBurnedKg = telemetry?.fuel_burned_kg || 0;
  const fuelFlowKgHr = telemetry?.fuel_flow_kg_hr || 0;
  const batterySoc = telemetry?.battery_soc_pct ?? 100;
  const wasteHeatKw = telemetry?.waste_heat_kw || 0;

  const isFeasible = summary?.is_feasible ?? true;
  const fuelSavedPct = summary?.fuel_saved_pct ?? 7.1;
  const netCo2Pct = summary?.net_co2_saved_pct ?? 0.0;
  const mtowKg = summary?.mtow_hybrid_kg || 22277;
  const pax = summary?.passengers_carried ?? 70;

  return (
    <div className="card-panel">
      {/* Header */}
      <div className="card-header">
        <div className="card-title">
          <Zap style={{ width: 16, height: 16, color: 'var(--electric-blue)' }} />
          <span>Powertrain Telemetry</span>
        </div>
        <span className={`badge-item ${isFeasible ? 'highlight-green' : 'badge-item'}`}>
          {isFeasible ? 'FEASIBLE' : 'LIMIT EXCEEDED'}
        </span>
      </div>

      {/* 1. Real-Time Power Split */}
      <div className="pt-progress-wrapper">
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
          <span style={{ color: 'var(--text-body)', fontWeight: 600 }}>Total Shaft Power</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800 }}>{Math.round(totalPowerKw)} kW</span>
        </div>

        <div className="pt-stacked-bar">
          <div className="pt-bar-gas" style={{ width: `${100 - hpPct}%` }} />
          <div className="pt-bar-elec" style={{ width: `${hpPct}%` }} />
        </div>

        <div className="pt-legend">
          <span style={{ color: 'var(--kerosene-amber)', fontWeight: 700 }}>
            Gas: {Math.round(turboshaftKw)} kW ({100 - hpPct}%)
          </span>
          <span style={{ color: 'var(--electric-blue)', fontWeight: 700 }}>
            Elec: {Math.round(electricKw)} kW ({hpPct}%)
          </span>
        </div>
      </div>

      {/* 2. Dual Reservoirs */}
      <div className="pt-grid-reservoirs">
        <div className="reservoir-card">
          <div className="reservoir-title">
            <span>KEROSENE</span>
            <span>{Math.round(fuelFlowKgHr)} kg/h</span>
          </div>
          <div className="reservoir-value">
            {fuelBurnedKg.toFixed(1)} <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>kg</span>
          </div>
        </div>

        <div className="reservoir-card">
          <div className="reservoir-title">
            <span>BATTERY SOC</span>
            <span>{summary?.battery_capacity_kwh || 271} kWh</span>
          </div>
          <div className="reservoir-value">
            {batterySoc.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 3. Waste Heat TMS */}
      <div className="pt-stat-row" style={{ padding: '6px 0' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-body)' }}>
          <Flame style={{ width: 14, height: 14, color: 'var(--kerosene-amber)' }} />
          <span>TMS Heat Rejection</span>
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
          {wasteHeatKw.toFixed(1)} kW(th)
        </span>
      </div>

      {/* 4. Sizing Feasibility Stats */}
      <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-light)' }}>
        <div className="pt-stat-row">
          <span style={{ color: 'var(--text-body)' }}>Block Fuel Saved</span>
          <span style={{ color: 'var(--telemetry-green)', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
            -{fuelSavedPct}%
          </span>
        </div>
        <div className="pt-stat-row">
          <span style={{ color: 'var(--text-body)' }}>Net Well-to-Wake CO₂</span>
          <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: netCo2Pct >= 0 ? 'var(--telemetry-green)' : 'var(--kerosene-amber)' }}>
            {netCo2Pct >= 0 ? `-${netCo2Pct}%` : `+${Math.abs(netCo2Pct)}%`}
          </span>
        </div>
        <div className="pt-stat-row">
          <span style={{ color: 'var(--text-body)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Scale style={{ width: 12, height: 12 }} /> Takeoff Weight (MTOW)
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
            {Math.round(mtowKg).toLocaleString()} / 23,000 kg
          </span>
        </div>
        <div className="pt-stat-row">
          <span style={{ color: 'var(--text-body)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Users style={{ width: 12, height: 12 }} /> Payload (Passengers)
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
            {pax} / 70 Seats
          </span>
        </div>
      </div>
    </div>
  );
}
