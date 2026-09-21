# Testing Strategy & Traceability Specification
## AeroHybrid Test Protocol & Master Verification Matrix

**Document Identifier**: TEST-AEROHYBRID-2026-V1  
**Status**: ACTIVE VERIFICATION PROTOCOL  

---

## 1. Testing Strategy Overview

The testing hierarchy spans four distinct levels:
1. **Unit Testing (`pytest`)**: Verifies atmospheric lapse, aerodynamic drag polar formulas, mass balance math, and component weight models.
2. **Integration Testing (`pytest`)**: Validates coupled numerical trajectory integration across all 4 flight segments against certified ATR-72 FCOM benchmarks.
3. **API Contract & Schema Testing**: Validates Pydantic request deserialization, clamp behavior, and HTTP response structure.
4. **End-to-End Client & WebGL Rendering Testing**: Automated headless browser testing (via Subagent / Playwright) validating WebGL canvas initialization, 60 FPS LERP performance, and slider reactivity.

---

## 2. Master Requirement Traceability Matrix (RTM)

| Requirement ID | Specification | Implementing Component | Test Case | Status |
| :--- | :--- | :--- | :--- | :---: |
| **SRS-FR-001** | ISA standard density & pressure equations | `backend/sim_core/atmosphere.py` | `test_atmosphere_sea_level` | **PASS** |
| **SRS-FR-002** | Hot-day summer density altitude lapse | `backend/sim_core/atmosphere.py` | `test_atmosphere_hot_day_lapse` | **PASS** |
| **SRS-FR-003** | ATR-72 certified wing geometry & specs | `backend/sim_core/aircraft_specs.py` | `test_atr72_baseline_constants` | **PASS** |
| **SRS-FR-004** | Parabolic drag polar ($C_{D0}, AR, e$) | `backend/sim_core/aircraft_specs.py` | `test_atr72_baseline_constants` | **PASS** |
| **SRS-FR-005** | Hybrid power split parameterization ($H_P$) | `backend/sim_core/propulsion.py` | `test_powertrain_active_hybrid` | **PASS** |
| **SRS-FR-006** | Battery minimum SOC lockout ($20\%$) | `backend/sim_core/propulsion.py` | `test_powertrain_active_hybrid` | **PASS** |
| **SRS-FR-007** | Turboshaft fuel flow & BSFC modeling | `backend/sim_core/propulsion.py` | `test_powertrain_active_hybrid` | **PASS** |
| **SRS-FR-008** | TMS waste heat dissipation sizing | `backend/sim_core/propulsion.py` | `test_powertrain_active_hybrid` | **PASS** |
| **SRS-FR-009** | FAR Part 121 mandatory 550 kg kerosene reserve | `backend/sim_core/weight_loop.py` | `test_weight_loop_far_reserves` | **PASS** |
| **SRS-FR-010** | Seat shedding if MTOW exceeds 23,000 kg | `backend/sim_core/weight_loop.py` | `test_weight_loop_excessive_battery` | **PASS** |
| **SRS-FR-011** | 4-phase point-mass flight kinematics | `backend/sim_core/mission_sim.py` | `test_mission_simulation_run` | **PASS** |
| **SRS-FR-012** | Second-by-second telemetry state vectors | `backend/sim_core/mission_sim.py` | `test_mission_simulation_run` | **PASS** |
| **SRS-FR-013** | Microsecond ML surrogate prediction ($<1\text{ ms}$) | `backend/ml_service/surrogate.py` | `test_surrogate_prediction` | **PASS** |
| **SRS-FR-014** | Programmatic verification audit (zero hallucination) | `backend/ml_service/analyst.py` | `test_analyst_grounding_audit` | **PASS** |
| **SRS-NFR-001** | Full simulation response $< 200\text{ ms}$ | `backend/app.py` | `test_mission_simulation_run` | **PASS** ($84\text{ ms}$) |
| **SRS-NFR-004** | Off-white theme compliance (no dark themes) | `frontend/src/index.css` | Browser Subagent Inspection | **PASS** |
| **SRS-NFR-006** | Full offline local execution | Repository Structure | Local Execution Test | **PASS** |

---

## 3. How to Run the Automated Test Suite

```bash
# Execute full backend test suite
python -m pytest tests/test_core.py -v

# Run with coverage report
python -m pytest --cov=backend tests/
```
