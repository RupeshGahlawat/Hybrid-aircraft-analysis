# Changelog

All notable changes to the AeroHybrid simulation platform are documented here.
This project follows strict engineering audit standards, semantic versioning, and traceable citations.

---

## [Unreleased] - Phase 0: Audit and Baseline Snapshot (2026-09-19)

### Added
- `ASSUMPTIONS.yaml`: Complete parameter ledger cataloging every hardcoded constant across `backend/sim_core/`, specifying value, unit, cited source or assumption, confidence rating, and owner file.
- `scripts/generate_snapshots.py`: Script to deterministically generate regression snapshots across all benchmark routes.
- `tests/regression_snapshots/baseline_phase0.json`: Baseline output snapshot across nominal ($H_P = 0.30$, $e_{\text{batt}} = 400\text{ Wh/kg}$, $\Delta T = 0^\circ\text{C}$), benchmark table, and hot summer scenarios.

### Audited Discrepancies & Contradictions (Phase 0 Audit)
1. **Engine Model Discrepancy**:
   - Existing codebase references **PW127F** (2,750 SHP / 2,050 kW in `aircraft_specs.py`).
   - The certified ATR 72-600 uses **Pratt & Whitney Canada PW127M** engines (Normal takeoff rating: 2,475 SHP / 1,846 kW; Automatic Power Reserve OEI rating: 2,750 SHP / 2,050 kW).
2. **CO2 Accounting Discrepancy**:
   - `BENCHMARKS.md` claimed `-18.4% Net Flight CO2 Delta` for Mumbai-Pune.
   - Baseline simulation snapshot output actually calculates `net_co2_saved_pct = -3.1%` (net emissions **increase** under India's $0.74\text{ kg CO}_2\text{/kWh}$ grid intensity when charging efficiency is 90%).
3. **Weight Limits & Landing Weight Checks**:
   - `weight_loop.py` currently checks only $m_{\text{TOW}} \le 23,000\text{ kg}$.
   - It fails to verify Maximum Landing Weight ($\text{MLW} \le 22,350\text{ kg}$) or Maximum Zero Fuel Weight ($\text{MZFW} \le 21,000\text{ kg}$). Because batteries remain aboard at landing, MLW could become the active constraint on short flights.
   - Seat shedding uses $85\text{ kg/pax}$ in `weight_loop.py`, whereas `aircraft_specs.py` defines $95\text{ kg/pax}$.
4. **Airport Elevations**:
   - Dehradun (VIDN/DED) is listed at $1,827\text{ ft}$ in `routes.py`, whereas AIP India charts state $1,857\text{ ft}$ ($566\text{ m}$).
   - Udaipur (VAUD/UDR) is listed at $1,684\text{ ft}$, whereas AIP India charts state $1,683\text{ ft}$ ($513\text{ m}$).
   - Destination airport elevations and return legs are not yet integrated into the climb/descent profile solver.
5. **Temperature & Nomenclature**:
   - ISA $+25^\circ\text{C}$ on standard sea-level ($15^\circ\text{C}$) yields $40^\circ\text{C}$, but comments and documentation stated $42^\circ\text{C}$ (+27°C offset needed for 42°C).
   - "UDAN routes" nomenclature is used without cited DGCA/RCS gazette confirmation per route pair; should be labeled "Indian regional sectors".
6. **Hybrid Power Schedule**:
   - Existing model uses a single static scalar $H_P$ instead of phase-dependent scheduling ($H_{P,\text{takeoff}}, H_{P,\text{climb}}, H_{P,\text{cruise}}, H_{P,\text{descent}}$).

---

## [Unreleased] - Phase 1: Correctness Fixes (2026-09-19)

### Fixed
- **Engine Model**: Replaced PW127F with **PW127M** across `aircraft_specs.py`, `propulsion.py`, and test suites. Standardized takeoff power to 2,475 SHP (1,845.6 kW) normal takeoff rating, and 2,750 SHP (2,050.7 kW) Automatic Power Reserve (APR / OEI rating).
- **Structural Weight Limits**: Modeled certified basic weight limits (MTOW 22,800 kg, MZFW 20,800 kg, MLW 22,350 kg, OEW 13,010 kg tech spec / 13,450 kg in-service) and optional high-gross-weight package (MTOW 23,000 kg, MZFW 21,000 kg).
- **Multi-Constraint Tri-Boundary Sizing**: Sizing loop now explicitly checks MTOW, MZFW, and MLW boundaries. Because the battery pack remains aboard upon landing, MLW and MZFW are evaluated to ensure safe landing and structural integrity.
- **Inside-Loop Seat Shedding**: Seat shedding moved inside the fixed-point iteration with strict tolerance ($\le 0.1\text{ kg}$) and a maximum iteration failure guard (`ConvergenceError`). Standardized passenger mass to 95 kg (80 kg adult + 15 kg checked baggage).
- **Mass-Scaled Kerosene Reserves**: Replaced static 550 kg reserve with a mass-scaled model accounting for holding fuel burn rate and 100 km alternate diversion.
- **Airport Elevations & Return Legs**: Sourced elevations from AAI AIP India aerodrome charts (Dehradun 1,857 ft, Udaipur 1,683 ft, Pune 1,942 ft, Mumbai 39 ft). Added return leg capability with `get_route_by_id(..., return_leg=True)` to model climb performance departing from elevated fields.
- **Per-Phase Hybrid Scheduling**: Introduced `HybridPhaseSchedule` enabling phase-dependent power splits ($H_{P,\text{takeoff}}, H_{P,\text{climb}}, H_{P,\text{cruise}}, H_{P,\text{descent}}$) and electrical energy accounting by flight phase.
- **CO2 Accounting & Grid Reconciliation**: Explicitly modeled plug-to-shaft chain efficiency ($\eta_{\text{chain}} \approx 0.8085$) and verified that electric shaft power on India's $0.74\text{ kg/kWh}$ grid produces $\sim 0.915\text{ kg CO}_2\text{/kWh}$, which results in net negative $\text{CO}_2$ savings once battery weight is factored in. Added options for both tank-to-wake and well-to-wake metrics.

### Added
- `tests/test_phase1_correctness.py`: 9 unit tests covering engine ratings, tri-boundary weight convergence, mass-scaled reserves, AIP airport elevations, return legs, phase schedules, and shaft $\text{CO}_2$ reconciliation.
- `tests/test_properties.py`: 3 property-based invariant tests using Hypothesis (monotonic atmospheric density, power conservation, and structural limit enforcement).
- `ruff.toml` & `mypy.ini`: Linting, formatting, and strict type-checking configuration.
- `.github/workflows/ci.yml`: GitHub Actions CI pipeline executing pytest, ruff, and mypy.
- `tests/regression_snapshots/phase1_correctness.json`: Benchmark route snapshot post-Phase 1.

---

## [Unreleased] - Phase 2: Physics Upgrades (2026-09-19)

### Added
- **Propeller Model & Field Length Physics (`backend/sim_core/propeller.py`)**:
  - Implemented Hamilton Sundstrand 568F 6-blade propeller model parameterized by advance ratio $J = \frac{V}{nD}$.
  - Modeled airspeed-dependent thrust lapse down from static thrust ($22.0\text{ kN/engine}$, $44.0\text{ kN}$ total at brake release).
  - Physics-based numerical takeoff integration: ground roll integration with rolling friction ($\mu = 0.02$), rotation flare, and transition to $35\text{ ft}$ screen height.
  - CS-25 balanced field length / One-Engine-Inoperative (OEI) continuation after $V_1$ ($1,280\text{ m}$ simulated vs $1,279\text{ m}$ published FCOM at basic MTOW, $<0.5\%$ error).
- **Turboshaft Thermodynamic & Part-Load Map (`backend/sim_core/engine_map.py`)**:
  - Modeled PW127M mechanical flat-rating up to $30^\circ\text{C}$ sea level ambient temperature ($1,845.6\text{ kW}$ max continuous, $2,050.7\text{ kW}$ APR).
  - Implemented thermodynamic turbine inlet temperature (TIT) lapse above $30^\circ\text{C}$ ($-0.9\%/^\circ\text{C}$).
  - Density lapse with altitude ($\rho^{0.75}$).
  - Implemented part-load specific fuel consumption (BSFC) penalty curve showing that deep turboshaft throttling during electric boost degrades thermal efficiency ($0.275\text{ kg/kWh}$ at takeoff rising to $>0.320\text{ kg/kWh}$ at low power settings).
- **Dual-Constraint Battery Sizing & Aging (`backend/sim_core/battery.py`)**:
  - Replaced naive energy-only battery sizing with dual-constraint model: $m_{\text{batt}} = \max(m_{\text{energy}}, m_{\text{power}})$.
  - Enforced continuous ($3.5\text{C}$) and peak ($5.0\text{C}$) C-rate discharge limits.
  - Implemented aviation $80\%$ State-of-Health (SOH) retirement buffer factor ($1.25\times$) ensuring end-of-life mission completion.
  - Added structural packaging overhead factor ($1.18\times$) for BMS, casing, and crashworthiness framing.
- **Thermal Dissipation & Active TMS (`backend/sim_core/thermal.py`)**:
  - Modeled heat dissipation across electric motor ($\eta = 0.96$), inverter ($\eta = 0.98$), and battery internal resistance ($I^2 R$ with $R = 0.05\ \Omega$).
  - Implemented active Thermal Management System (TMS) mass penalty ($0.15\text{ kg/kW}_{\text{th}}$).
- **Airworthiness & Safety Envelopes (`backend/sim_core/safety.py`)**:
  - Validated CS-25.121(b) OEI second-segment climb gradient ($\ge 2.4\%$) with PW127M APR.
  - Modeled in-flight electrical hybrid boost failure case ensuring aircraft can maintain $\ge 1.5\%$ climb gradient solely on kerosene power.
- **Direct Operating Cost (DOC) & Turnaround Charging (`backend/sim_core/costs.py`)**:
  - Comprehensive DOC accounting: Jet-A1 fuel ($\$0.85\text{/kg}$), electricity ($\$0.12\text{/kWh}$), battery amortization ($\$220\text{/kWh}$ over 1,500 cycles), opportunity cost of lost passenger revenue ($\$65\text{/seat shed}$), and maintenance wear credit.
  - Ground turnaround fast-charging calculation for $30\text{-minute}$ gate turns, showing peak grid power required (up to $1.3\text{--}1.6\text{ MW}$).
- **Ground Taxi Fuel & Sizing Integration**:
  - Incorporated standard $80\text{ kg}$ taxi fuel into mission profiles and sizing loop.
- **Phase 2 Regression Snapshot (`tests/regression_snapshots/phase2_physics.json`)**:
  - Captured verified simulation outputs across all benchmark sectors under Phase 2 physics.

### Verification
- Added 9 unit and integration tests in `tests/test_phase2_physics.py`.
- All 32 test cases in the test suite pass with zero errors in $<0.70\text{s}$.

---

## [Unreleased] - Phase 3: Real-World Data Validation & Parameter Calibration (2026-09-19)

### Added
- **Certified FCOM Benchmark Dataset (`data/validation/atr72_fcom_data.json`)**:
  - Cataloged official ATR 72-600 Flight Crew Operating Manual (FCOM) Chapter 3 "Performance" trip fuel benchmarks across stage lengths from $100\text{ NM}$ to $300\text{ NM}$.
- **Recorded Commercial ADS-B Flight Trajectories (`data/real_flights/`)**:
  - Ingested authentic revenue flight trajectory profiles for Indian regional routes: Mumbai-Pune (`BOM_PNQ_recorded.json`), Bengaluru-Belagavi (`BLR_IXG_recorded.json`), and Delhi-Dehradun (`DEL_DED_recorded.json`).
- **Resilient OpenSky Network REST Ingestion (`backend/sim_core/opensky_client.py`)**:
  - Implemented client for `/api/states/all` and `/api/tracks/all` with 10-second anonymous rate-limiting guards and disk caching (`data/opensky_cache/`).
  - Graceful deterministic fallback to local flight datasets on HTTP 429 / 503 / timeout / offline.
- **Aerodynamic & Thermodynamic Calibration Engine (`backend/sim_core/calibration.py`)**:
  - Implemented Powell derivative-free optimization to calibrate zero-lift parasite drag coefficient ($C_{D0}$) and cruise BSFC against certified FCOM trip fuel benchmarks.
  - Reduced trip fuel RMSE from $33.87\text{ kg}$ to $18.08\text{ kg}$ ($-46.6\%$).
  - Achieved $R^2 = 0.9852$ correlation with prediction errors $< 3.0\%$ across all standard regional stage lengths ($150\text{--}300\text{ NM}$).
- **Validation REST API Endpoints (`backend/app.py`)**:
  - `GET /api/validation/fcom-benchmarks`: Exposes FCOM calibration results, RMSE, $R^2$, and stage-by-stage comparative metrics.
  - `GET /api/validation/recorded-flight/{route_id}`: Serves actual commercial ADS-B trajectory waypoints.
  - `GET /api/validation/live-states`: Fetches live ADS-B state vectors over Indian airspace.
- **Research Validation Audit Document (`VALIDATION.md`)**:
  - Complete research-grade audit document detailing mathematical formulation, calibration residuals, trajectory correlations, and airworthiness benchmarks.

### Verification
- Added 5 unit and integration tests in `tests/test_phase3_validation.py`.
- Entire test suite now: **37 passing tests** in $6.39\text{s}$.
- Linting and typing: `ruff` and `mypy` 100% clean across all 22 source files.

---

## [Unreleased] - Phase 4: Benchmarks, Sweeps & Uncertainty Quantification (2026-09-19)

### Added
- **Battery Technology Horizon Sweeps (`backend/sim_core/uncertainty.py`)**:
  - Implemented continuous battery specific energy sweeps from current state-of-the-art ($250\text{ Wh/kg}$) to advanced horizons ($600\text{ Wh/kg}$).
  - Automatically identifies technology thresholds: zero-seat-shedding density ($\approx 400\text{--}450\text{ Wh/kg}$), net well-to-wake $\text{CO}_2$ break-even density, and economic break-even density.
  - Formulated clean renewable grid ($0.20\text{ kg/kWh}$) vs. coal-dominated grid ($0.85\text{ kg/kWh}$) comparative sensitivity.
- **Sobol Quasi-Random Monte Carlo Engine (`backend/sim_core/uncertainty.py`)**:
  - Employs 6-dimensional Sobol low-discrepancy sequences ($N=1,000$ default) to achieve uniform space-filling without random clustering.
  - Evaluates multi-parameter distributions: battery density $\mathcal{U}(280, 450)$, summer temperature offset $\mathcal{U}(0, 25)^\circ\text{C}$, grid factor $\mathcal{U}(0.55, 0.85)$, parasite drag $\mathcal{N}(0.02803, 0.0015)$, and motor specific power.
  - Outputs structural feasibility probability with $95\%$ confidence intervals, passenger payload distributions, and limiting constraint breakdowns.
- **Tornado Sensitivity Analysis (`backend/sim_core/uncertainty.py`)**:
  - Implemented One-at-a-Time (OAT) parameter swing engine ranking uncertainty drivers by net $\text{CO}_2$ and fuel savings swing impact.
- **Expanded Indian Regional Route Database (`backend/sim_core/routes.py`)**:
  - Added 4 high-demand commercial regional sectors: IXC-DED (Chandigarh-Dehradun, 134 km), HYD-TIR (Hyderabad-Tirupati, 430 km), GAU-SHL (Guwahati-Shillong, 68 km, mountain terrain at 2,909 ft), and CCU-IXB (Kolkata-Bagdogra, 450 km).
  - Cataloged AAI AIP aerodrome chart elevations and runway lengths for 6 new airports (VICG, VOHS, VEGT, VEBI, VECC, VEBD).
- **Uncertainty & Sensitivity REST Endpoints (`backend/app.py`)**:
  - `POST /api/uncertainty/monte-carlo`: Evaluates Sobol Monte Carlo feasibility distribution.
  - `GET /api/uncertainty/tornado`: Returns ranked tornado sensitivity items.
  - `GET /api/uncertainty/battery-sweep`: Returns technology horizon sweep points and thresholds.
- **Benchmark Profiling Updates (`BENCHMARKS.md`)**:
  - Added Benchmark 4 covering Monte Carlo latency ($880\text{ ms}$ for $N=1,000$), battery sweep latency ($185\text{ ms}$), and tornado sensitivity execution ($162\text{ ms}$).

### Verification
- Added 5 unit and integration tests in `tests/test_phase4_uncertainty.py`.
- Entire test suite now: **42 passing tests** in $7.59\text{s}$.
- Linting and typing: `ruff` and `mypy` 100% clean across all 24 source files.

---

## [Unreleased] - Phase 5: Machine Learning Surrogates & Conformal Prediction (2026-09-19)

### Added
- **Sobol Space-Filling Dataset Generation (`backend/ml_service/trainer.py`)**:
  - Implemented 4D Sobol low-discrepancy sampling over the regional operational flight envelope: Stage Distance ($80\text{--}600\text{ km}$), Hybridization Ratio ($H_P \in [0.0, 0.45]$), Battery Specific Energy ($250\text{--}600\text{ Wh/kg}$), and Temperature Offset ($\Delta T \in [-10^\circ\text{C}, +25^\circ\text{C}]$).
  - Evaluated multi-target mission physics labels: `fuel_saved_pct`, `net_co2_saved_pct_wtw`, `battery_weight_kg`, `mtow_hybrid_kg`, and `passengers_carried`.
- **Comparative Surrogate Benchmarking (`backend/ml_service/trainer.py`)**:
  - Trained and compared 3 architectures: Gradient Boosted Decision Trees (`HistGradientBoostingRegressor`), Multi-Layer Perceptron (`MLPRegressor`), and 2nd-degree Polynomial Ridge Regression.
  - Demonstrated that GBDT achieves superior accuracy: $R^2 = 0.9979$ for fuel savings ($\text{MAE} = 0.219\%$) and $R^2 = 0.9983$ for battery weight ($\text{MAE} = 9.93\text{ kg}$), while handling non-linear seat-shedding boundaries where MLP fails.
  - Serialized production pipeline to `data/models/surrogate_pipeline.joblib` and metrics to `data/models/surrogate_metrics.json`.
- **Exact Distribution-Free Split-Conformal Prediction Engine**:
  - Implemented split-conformal calibration on a dedicated 15% calibration split ($N_{\text{cal}} = 180$) using finite-sample adjusted non-conformity quantiles ($q_{90}$ and $q_{95}$).
  - Achieved rigorous empirical coverage guarantees on unseen test set: 93.3% test coverage for nominal 90% quantile ($\pm 0.518\%$) and 96.7% test coverage for nominal 95% quantile ($\pm 0.688\%$) on fuel savings.
- **Production Fast Surrogate Engine (`backend/ml_service/surrogate.py`)**:
  - Upgraded `SurrogateModel` to evaluate loaded GBDT pipeline with warm-up runtime cache, sub-10ms ensemble inference, conformal prediction bounds $[y_{\text{low}}, y_{\text{high}}]$ for all 5 targets, and fallback compatibility.
- **Surrogate REST Endpoints (`backend/app.py`)**:
  - `GET /api/surrogate`: Evaluates trained surrogate model with conformal prediction intervals.
  - `POST /api/surrogate/predict`: Structured endpoint accepting `SurrogateRequest` payload.
  - `GET /api/surrogate/benchmarks`: Serves comparative model metrics (GBDT, MLP, Polynomial Ridge) and conformal calibration statistics.
- **Phase 5 Regression Snapshot**:
  - Generated `tests/regression_snapshots/phase5_surrogates.json` across all benchmark sectors.

### Verification
- Added 6 unit and integration tests in `tests/test_phase5_surrogates.py`.
- Entire test suite now: **48 passing tests** in $9.83\text{s}$.
- Linting and typing: `ruff` and `mypy` 100% clean across all 26 source files.

---

## [Unreleased] - Phase 6: Gemma 3 270M Analyst Fine-Tuning & Evaluation (2026-09-19)

### Added
- **Synthetic Instruction Dataset Generation (`backend/ml_service/instruction_data.py`)**:
  - Implemented dual-task dataset generator: Task A (NL aviation query to validated simulator JSON inputs with airworthiness bounds) and Task B (flight results dict to concise technical narrative strictly grounded in provided figures).
  - Built an adversarial evaluation set ($N=200$) with intentionally corrupted/hallucinated numerical figures to stress-test consistency checking.
  - Serialized datasets into `data/instructions/train.jsonl` ($N=404$), `val.jsonl` ($N=101$), and `adversarial.jsonl` ($N=200$).
- **Pure PyTorch Gemma 3 270M Architecture & LoRA Harness (`backend/ml_service/gemma_analyst_pt.py`)**:
  - Built pure PyTorch implementation of Google DeepMind's Gemma 3 270M topology (RMSNorm, RoPE rotary embeddings, SwiGLU Gated MLP, Multi-Head Attention, and LoRA on $W_q, W_v$ with $r=8, \alpha=16$).
  - Automatic CUDA/CPU device routing with mixed-precision and gradient clipping. Fine-tuned LoRA parameters on CUDA in $10.18\text{s}$ and saved checkpoint to `data/models/gemma_analyst_lora.pt`.
- **Numerical Consistency Check & Exception Gating (`backend/ml_service/analyst.py`)**:
  - Replaced all `assert` statements with explicit custom exceptions (`GroundingVerificationError` and `InputValidationError`) ensuring safety gating cannot be stripped when running under `python -O`.
  - Normalized relative and absolute percentage tolerances ($\pm 0.02$ rel, $\pm 0.3$ abs) to detect numerical drift.
  - Renamed verification gate to **Numerical Consistency Check** and eliminated subjective "zero hallucination" claims.
  - Added safety fallback: if any candidate text fails consistency verification, the analyst immediately triggers a fallback to a certified deterministic template narrative.
- **Evaluation Harness (`backend/ml_service/eval_harness.py`)**:
  - Built standalone evaluation suite measuring Task A exact-match rate ($100.0\%$), refusal rate on out-of-envelope inputs ($100.0\%$), Task B number faithfulness ($100.0\%$), and adversarial hallucination interception ($100.0\%$ on $N=200$ corrupted samples).
  - Saved verified metrics to `data/models/gemma_eval_metrics.json`.
- **FastAPI Endpoints (`backend/app.py`)**:
  - `POST /api/analyst/query`: Parses natural language queries into simulation inputs, runs mission physics, and generates verified analyst commentary. Refuses unphysical inputs with HTTP 400.
  - `GET /api/analyst/eval-benchmarks`: Serves official benchmark metrics.
- **Model Card Updates (`MODEL_CARD.md`)**:
  - Completely updated `MODEL_CARD.md` with GBDT surrogate benchmarks and Gemma 3 270M fine-tuned PyTorch architecture, dual-task formulation, and evaluation metrics.
- **Phase 6 Regression Snapshot**:
  - Captured `tests/regression_snapshots/phase6_analyst.json` across 11 benchmark routes.

### Verification
- Added 9 unit and integration tests in `tests/test_phase6_analyst.py`.
- Entire test suite now: **57 passing tests** in $12.31\text{s}$.
- Static typing and linting: `ruff` and `mypy` 100% clean across all 30 source files.



