# Product & Engineering Roadmap
## AeroHybrid Platform Phased Evolution

**Document Identifier**: ROADMAP-AEROHYBRID-2026-V1  
**Status**: ACTIVE ROADMAP  

---

## 1. Roadmap Classification & Prioritization Matrix

| Horizon | Phase | Target Horizon | Primary Deliverables | Risk Level |
| :--- | :--- | :---: | :--- | :---: |
| **CURRENT** | Baseline System | Q3 2026 | Point-mass kinematics, ISA atmosphere, FAR 121 reserves, UDAN routes, 3D WebGL digital twin, PFD HUD, surrogate model. | *Delivered* |
| **NEXT** | Engineering Hardening | Q4 2026 | Multi-cycle battery aging module, part-load turboshaft compressor maps, Docker containerization, CI/CD GitHub Actions. | Low |
| **FUTURE** | High-Fidelity Physics | Q1 2027 | Blade Element Momentum Theory (BEMT) for propellers, 6-DOF aerodynamic stability derivatives, DuckDB scenario telemetry cache. | Medium |
| **RESEARCH** | Certification & Aero-Electrical | Q2 2027 | Paschen's law partial discharge insulation model, cryogenic motor scaling studies, well-to-wake SAF (Sustainable Aviation Fuel) blends. | High |
| **PRODUCTION**| Enterprise Fleet Suite | Q3 2027 | Multi-tenant airline dispatch tool, ADS-B live flight route ingestion (OpenSky API integration), PDF executive report export. | High |

---

## 2. Detailed Phase Breakdown

### Phase 1: CURRENT (Delivered Baseline)
* [x] Certified ATR 72-600 aerodynamic drag polar and mass baseline.
* [x] ISA atmospheric lapse with $+25^\circ\text{C}$ Indian summer density altitude adjustments.
* [x] FAR Part 121 / DGCA CAR kerosene reserve sizing ($550\text{ kg}$).
* [x] Indian regional UDAN route database with airport elevations, runway lengths, and CEA grid carbon factors.
* [x] 4-phase point-mass kinematics trajectory integrator.
* [x] 60 FPS Three.js moving digital twin with spinning 6-blade props, runway, and dual ghost comparison.
* [x] Glass cockpit Primary Flight Display (PFD) and live KaTeX mathematical physics formulas.
* [x] Microsecond ($0.08\text{ ms}$) ML surrogate and grounded Gemma 3 270M analyst interface.

### Phase 2: NEXT (Engineering Hardening - Months 1–2)
* [ ] **Multi-Cycle Arrhenius Battery Aging**:
  * *Impact*: High | *Effort*: Medium | *Risk*: Low
  * Add `battery_aging.py` to calculate battery replacement costs ($/flight) over 1,500 flight cycles.
* [ ] **Gas Turbine Part-Load Efficiency Correction**:
  * *Impact*: Medium | *Effort*: Medium | *Risk*: Low
  * Replace static BSFC constants with quadratic throttle-dependent thermal efficiency curves.
* [ ] **Containerization & CI/CD**:
  * *Impact*: High | *Effort*: Low | *Risk*: Low
  * Multi-stage `Dockerfile` and automated GitHub Actions running `pytest` and `npm run build` on push.

### Phase 3: FUTURE (High-Fidelity Dynamics - Months 3–4)
* [ ] **Blade Element Momentum Theory (BEMT)**:
  * *Impact*: Medium | *Effort*: High | *Risk*: Medium
  * Resolve local blade angle of attack and compressibility across 3.93 m Hamilton Sundstrand propeller blades.
* [ ] **DuckDB Scenario Telemetry Warehouse**:
  * *Impact*: High | *Effort*: Medium | *Risk*: Low
  * Store and query 100,000+ Sobol Monte Carlo runs locally using Parquet and DuckDB.

### Phase 4: RESEARCH (Aero-Electrical & Certification - Months 5–6)
* [ ] **Altitude Paschen's Law Insulation Sizing**:
  * *Impact*: High | *Effort*: High | *Risk*: High
  * Model dielectric breakdown voltage drops at 20,000 ft and size pressurized cable conduits.
* [ ] **Local Gemma 3 270M Model Serving**:
  * *Impact*: Medium | *Effort*: High | *Risk*: Medium
  * Serve fine-tuned Gemma 3 270M ONNX/GGUF weights locally via llama.cpp or ONNX Runtime.

### Phase 5: PRODUCTION (Enterprise Fleet Tool - Month 7+)
* [ ] **OpenSky Network Live Flight Track Validation**:
  * *Impact*: High | *Effort*: High | *Risk*: Medium
  * Ingest real-world ADS-B commercial flight profiles from OpenSky Network to compare against simulation predictions.
* [ ] **Executive Feasibility PDF Export**:
  * *Impact*: Medium | *Effort*: Low | *Risk*: Low
  * Automated one-click PDF generation of airframe sizing and economic trade studies.
