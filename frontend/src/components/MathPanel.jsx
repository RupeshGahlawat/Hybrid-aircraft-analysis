import React, { useEffect, useRef } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { BookOpen } from 'lucide-react';

export default function MathPanel({ telemetry }) {
  const eq1Ref = useRef(null);
  const eq2Ref = useRef(null);
  const eq3Ref = useRef(null);

  const turboshaftKw = telemetry?.turboshaft_power_kw || 1435;
  const electricKw = telemetry?.electric_power_kw || 615;
  const totalKw = turboshaftKw + electricKw;
  const fuelFlowKgHr = telemetry?.fuel_flow_kg_hr || 410.0;

  useEffect(() => {
    if (eq1Ref.current) {
      const eq1Tex = `P_{\\text{req}} = \\frac{(D + mg\\sin\\gamma)V}{\\eta_{\\text{prop}}} = \\mathbf{${Math.round(totalKw)}\\text{ kW}}`;
      katex.render(eq1Tex, eq1Ref.current, { throwOnError: false });
    }
    if (eq2Ref.current) {
      const eq2Tex = `P_{\\text{gas}} = \\mathbf{${Math.round(turboshaftKw)}\\text{ kW}}, \\quad P_{\\text{elec}} = \\mathbf{${Math.round(electricKw)}\\text{ kW}}`;
      katex.render(eq2Tex, eq2Ref.current, { throwOnError: false });
    }
    if (eq3Ref.current) {
      const eq3Tex = `\\dot{m}_{\\text{fuel}} = \\text{BSFC} \\cdot P_{\\text{gas}} = \\mathbf{${fuelFlowKgHr.toFixed(1)}\\text{ kg/h}}`;
      katex.render(eq3Tex, eq3Ref.current, { throwOnError: false });
    }
  }, [totalKw, turboshaftKw, electricKw, fuelFlowKgHr]);

  return (
    <div className="card-panel">
      <div className="card-header">
        <div className="card-title">
          <BookOpen style={{ width: 15, height: 15, color: 'var(--electric-blue)' }} />
          <span>Physics Governing Math</span>
        </div>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          LIVE
        </span>
      </div>

      <div className="math-container">
        <div className="math-row" ref={eq1Ref} />
        <div className="math-row" ref={eq2Ref} />
        <div className="math-row" ref={eq3Ref} />
      </div>
    </div>
  );
}
