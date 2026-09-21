# Model Card: AeroHybrid ML Surrogates & Language Services
**Document Identifier**: MC-AEROHYBRID-2026-V2  
**Last Updated**: 2026-09-19  

---

## 1. Model 1: Rapid Feasibility Surrogate Model (GBDT + Conformal)

### 1.1 Model Overview
* **Model Name**: AeroHybrid Gradient Boosted Decision Tree Surrogate (`SurrogateModel`)
* **Version**: 2.0.0
* **Architecture**: Ensemble of `HistGradientBoostingRegressor` pipelines (one per target output) coupled with exact finite-sample split-conformal prediction calibration ($90\%$ and $95\%$ marginal coverage).
* **Parameters**: 5 multi-target boosted tree ensembles (max leaf nodes: 31, max iterations: 150).
* **File Location**: [`backend/ml_service/surrogate.py`](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/backend/ml_service/surrogate.py) (pipeline serialized in `data/models/surrogate_pipeline.joblib`)
* **Status**: **IMPLEMENTED / OPERATIONAL**

### 1.2 Inputs and Outputs
* **Inputs**:
  1. `stage_distance_km`: Float $\in [80.0, 600.0]$
  2. `hp_fraction`: Float $\in [0.0, 0.45]$
  3. `battery_wh_per_kg`: Float $\in [250.0, 600.0]$
  4. `ambient_delta_c`: Float $\in [-10.0, 25.0]^\circ\text{C}$
* **Outputs**:
  1. `predicted_fuel_saved_pct`: Estimated percentage fuel burn reduction with conformal intervals.
  2. `predicted_co2_saved_pct_wtw`: Well-to-wake net $\text{CO}_2$ percentage reduction.
  3. `estimated_battery_mass_kg`: Dual-constrained pack mass with conformal intervals.
  4. `estimated_tow_kg`: Hybrid takeoff weight (kg).
  5. `passengers_carried`: Realistic seat-shedding payload capacity.
  6. `uncertainty_range_pct`: 90% split-conformal prediction confidence band.
  7. `is_feasible`: Boolean airworthiness flag ($m_{\text{TOW}} \le 23,000\text{ kg} \land \text{pax} \ge 70$).
  8. `inference_time_ms`: Sub-10ms latency ($5.9\text{ ms}$ warm on CPU).

### 1.3 Training & Validation Benchmarks (Test Split $N=180$)
* **Training Dataset**: $N=1,200$ Sobol 4D quasi-random synthetic missions (70% train, 15% calibration, 15% test).
* **Accuracy Metrics**:
  * Fuel saved (%): $R^2 = 0.9979$, $\text{MAE} = 0.219\%$, $\text{RMSE} = 0.345\%$.
  * Battery mass (kg): $R^2 = 0.9983$, $\text{MAE} = 9.93\text{ kg}$, $\text{RMSE} = 14.94\text{ kg}$.
  * MTOW (kg): $R^2 = 0.9923$, $\text{MAE} = 24.40\text{ kg}$, $\text{RMSE} = 29.40\text{ kg}$.
  * Passengers carried: $R^2 = 0.9928$, $\text{MAE} = 0.21\text{ pax}$.
* **Conformal Empirical Coverage (Nominal 90%)**:
  * Fuel: $93.3\%$ ($q_{90} = \pm 0.518\%$)
  * Battery: $89.4\%$ ($q_{90} = \pm 23.56\text{ kg}$)
  * MTOW: $94.4\%$ ($q_{90} = \pm 52.01\text{ kg}$)

---

## 2. Model 2: Gemma 3 270M Feasibility Analyst (Pure PyTorch + LoRA)

### 2.1 Model Overview
* **Model Name**: Gemma 3 270M Fine-Tuned Feasibility Analyst (`Gemma3AnalystModel` + `FeasibilityAnalyst`)
* **Version**: 2.0.0-finetuned
* **Architecture**: Pure PyTorch transformer with RMSNorm, RoPE rotary embeddings, SwiGLU Gated MLP, Multi-Head Attention, and Low-Rank Adaptation (LoRA rank $r=8, \alpha=16$) on query/value projection matrices.
* **Parameter Count**: 270 Million (170M embeddings + 100M transformer blocks).
* **Hardware Support**: Pure PyTorch CPU/CUDA automatic acceleration.
* **Checkpoint**: `data/models/gemma_analyst_lora.pt`.
* **Status**: **IMPLEMENTED / OPERATIONAL / BENCHMARKED**

### 2.2 Dual Task Formulation
1. **Task A (Natural Language Query to Simulator JSON)**:
   * Maps unconstrained English queries to validated JSON schemas (`route_id`, `hp_fraction`, `battery_wh_per_kg`, `ambient_delta_c`).
   * Enforces airworthiness bounds: automatically refuses unphysical battery densities, unsupported routes, or excessive hybridization ratios.
2. **Task B (Simulation Results to Technical Explanation)**:
   * Translates simulation output dictionaries into concise, professional flight narratives.

### 2.3 Numerical Consistency Check & Safety Gate
* **Mechanism**: Replaced `assert` statements with explicit `GroundingVerificationError` and `InputValidationError` exceptions to eliminate `python -O` bypass vulnerabilities.
* **Tolerance Model**: Uses normalized percentage tolerances ($\pm 0.02$ relative or $\pm 0.3$ absolute).
* **Measured Adversarial Catch Rate**: **100.0%** (200 out of 200 adversarial samples with corrupted numbers intercepted and rejected).
* **Fallback Safety**: If any figure fails consistency verification, the analyst immediately rejects candidate text and falls back to a certified deterministic template narrative.

### 2.4 Evaluation Harness Benchmarks (`data/models/gemma_eval_metrics.json`)
* Task A NL-to-JSON Exact-Match Rate: **100.0%** ($N=56$ test queries).
* Task A Out-of-Range Refusal Rate: **100.0%** ($N=5$ boundary-violating queries).
* Task B Number-Faithfulness Rate: **100.0%** ($N=40$ validation flight narratives).
* Adversarial Hallucination Catch Rate: **100.0%** ($N=200$ corrupted adversarial trials).
* Evaluation Latency: $7\text{ ms}$.

---

## 3. Intended and Non-Intended Uses

* **Intended Use**:
  * Rapid parameter sweeps during preliminary aircraft sizing and fleet evaluation.
  * Natural language querying of regional aircraft digital twin parameters.
  * Technical decision support for airline fleet decarbonization teams.
  * Academic demonstration of distribution-free conformal prediction and LLM numerical grounding.
* **Non-Intended Use**:
  * Real-time flight control, fly-by-wire actuation, or autopilot navigation.
  * Critical flight crew dispatch documentation.
  * Airworthiness certification approval without formal wind-tunnel and flight test validation.
