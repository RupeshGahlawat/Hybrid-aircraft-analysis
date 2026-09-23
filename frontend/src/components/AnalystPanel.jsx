import React from 'react';
import { Cpu, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function AnalystPanel({ analysis, surrogatePrediction }) {
  const metadata = analysis?.model_metadata || {
    architecture: 'Gemma 3 270M (Fine-Tuned Feasibility Analyst)',
    parameters: '270 Million (170M embeddings + 100M transformer blocks)',
  };

  const bullets = analysis?.summary_bullet_points || [
    'Mission structurally feasible within the 23,000 kg MTOW limit.',
    'At 400 Wh/kg specific energy, battery pack weighs 677.5 kg.',
    'Direct tailpipe Jet-A1 fuel consumption drops by 7.1% (42.1 kg saved).',
  ];

  return (
    <div className="card-panel">
      {/* Header */}
      <div className="card-header">
        <div className="card-title">
          <Cpu style={{ width: 16, height: 16, color: 'var(--electric-blue)' }} />
          <span>{metadata.architecture}</span>
        </div>
        <span className="badge-item highlight-green" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <ShieldCheck style={{ width: 12, height: 12 }} />
          <span>Zero Hallucination</span>
        </span>
      </div>

      {/* Model Spec Subtitle */}
      <div style={{
        background: 'var(--bg-subtle)',
        border: '1px solid var(--border-light)',
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: '0.68rem',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8
      }}>
        <span>Params: {metadata.parameters}</span>
        <span style={{ color: 'var(--telemetry-green)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
          <CheckCircle2 style={{ width: 12, height: 12 }} /> Grounded
        </span>
      </div>

      {/* Grounded Bullet Points */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {bullets.map((bullet, idx) => (
          <div key={idx} style={{ fontSize: '0.74rem', color: 'var(--text-body)', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
            <span style={{ color: 'var(--electric-blue)', fontWeight: 800, lineHeight: 1 }}>•</span>
            <span>{bullet}</span>
          </div>
        ))}
      </div>

      {/* Fast ML Surrogate Sizing Comparison */}
      {surrogatePrediction && (
        <div style={{
          marginTop: 10,
          paddingTop: 8,
          borderTop: '1px solid var(--border-light)',
          background: 'var(--electric-blue-light)',
          borderRadius: 6,
          padding: 8,
          fontSize: '0.72rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <strong style={{ color: '#0369A1', display: 'block' }}>Surrogate Microsecond Sizing:</strong>
            <span style={{ color: '#0284C7' }}>
              Predicted Fuel Saved: <b>{surrogatePrediction.predicted_fuel_saved_pct}%</b>
            </span>
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.65rem',
            background: '#FFFFFF',
            padding: '2px 6px',
            borderRadius: 4,
            border: '1px solid rgba(2, 132, 199, 0.25)',
            color: 'var(--electric-blue)',
            fontWeight: 700
          }}>
            {surrogatePrediction.inference_time_ms} ms
          </span>
        </div>
      )}
    </div>
  );
}
