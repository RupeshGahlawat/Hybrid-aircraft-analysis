# Hostile Engineering & Research Technical Audit
## Independent Assessment of the AeroHybrid Feasibility Platform

**Document Identifier**: AUDIT-AEROHYBRID-2026-V1  
**Auditor Persona**: Hostile but Fair Principal Aerospace Systems Reviewer & Peer Reviewer  
**Status**: FORMAL ENGINEERING AUDIT  

---

## 1. Executive Reviewer Verdict

AeroHybrid is an **impressively integrated, technically coherent conceptual design demonstrator** that bridges first-principles aerospace flight physics with real-time WebGL visualization. Its focus on regional turboprops (ATR 72-600) rather than commercial jets is scientifically sound. 

However, beneath its polished digital twin interface lie **several critical engineering assumptions, unverified claims, and simplification risks** that an expert aerospace certification or academic panel would immediately challenge. This audit documents those vulnerabilities with unvarnished technical honesty.

---

## 2. Hostile Question-by-Question Interrogation

### Q1: What can be challenged immediately by an aerospace panel?
* **The Static BSFC Assumption**: When a gas turbine is throttled down because an electric motor is assisting it, the turbine does NOT maintain its peak thermal efficiency. Turbomachinery operating off-design suffers severe thermal efficiency drops ("part-load penalty"). Assuming a flat $0.275\text{ kg/kWh}$ BSFC artificially flatters the hybrid's fuel savings by an estimated $3\text{--}6\%$.
* **Radiator Momentum Cooling Drag**: Rejecting 50 kW of waste heat from megawatt inverters at 20,000 ft requires significant cooling airflow. The aerodynamic momentum drag of cooling air intakes and radiators is omitted, which increases actual airframe cruise drag.

### Q2: What claims are unsupported or unverified?
* **Gemma 3 270M Local Inference**: The UI displays "Gemma 3 270M (Fine-Tuned Feasibility Analyst)". In reality, the current codebase executes a **deterministic Python template service** that formats simulation values into structured sentences with an assertion audit. No 270M neural network weights are currently loaded in PyTorch or ONNX Runtime. This must be honestly classified as a **template service with planned model execution**, rather than an active neural inference pipeline.

### Q3: What is actually novel vs. what is merely implementation?
* **Implementation**: The 3D Three.js renderer, FastAPI REST endpoints, and UI dashboard are solid engineering implementations, but they are not scientifically novel.
* **Novelty**: The coupling of **real Indian regional UDAN operational constraints** (airport elevation lapse + CEA grid emissions) with dynamic hybrid power splits and FAR 121 reserve fuel sizing represents a novel, regionally grounded application study.

### Q4: What assumptions are unrealistic?
* **Battery Replacement Costs**: The model demonstrates a $22.1\%$ fuel burn reduction on Mumbai–Pune. However, aviation batteries subjected to rapid 4C takeoff discharge may degrade to $80\%$ capacity in fewer than 1,000 flight cycles. If a 677 kg battery pack costs $\$150,000$ and must be replaced every 8 months, the capital depreciation cost could completely wipe out the $40\text{ kg}$ of jet fuel saved per flight.

### Q5: Is there unnecessary AI?
* **Surrogate Model**: **Justified**. The polynomial/GBDT surrogate provides a verified $1,000\times$ speed-up ($0.08\text{ ms}$ vs. $84\text{ ms}$), enabling instant slider interactivity without locking the browser.
* **Language Model for Numbers**: **Unnecessary & Dangerous**. Using a language model to report numerical flight results introduces hallucination risks. The project's programmatic assertion guardrail (`analyst.py`) is an essential defense, but an engineer would ask why a structured JSON scorecard is not used directly.

---

## 3. Risk Breakdown Matrix

| Risk Category | Identified Vulnerability | Severity | Mitigation Strategy |
| :--- | :--- | :---: | :--- |
| **Technical Risk** | Turbine part-load efficiency degradation ignored. | High | Implement throttle-dependent quadratic BSFC correction curves. |
| **Technical Risk** | In-flight battery cell temperature thermal runaway unmodeled. | High | Add lumped-parameter dynamic cell temperature ODE solver. |
| **Research Risk** | No experimental wind-tunnel or flight-test validation data. | Medium | Benchmark directly against published NASA STARC-ABL and RTX flight demonstrator data. |
| **Economic Risk** | Battery cycle life replacement cost omitted from ROI. | High | Incorporate Direct Operating Cost (DOC) equation including battery amortized cost per flight. |
| **Safety Risk** | High-voltage partial discharge / Paschen's law breakdown at FL200. | Medium | Add empirical insulation mass scaling factor for buses $>800\text{V}$. |

---

## 4. Strengths of the Project

1. **Aeronautical Realism**: Selecting the ATR 72-600 rather than a fighter jet or narrow-body airliner shows genuine domain competence.
2. **FAR Part 121 Reserve Compliance**: Sizing kerosene-only reserves (550 kg) proves that the model does not cheat by assuming empty-tank landings.
3. **Pristine Off-White UI**: The interface strictly adheres to aerospace clean-room laboratory design standards with zero toy colors or dark themes.
4. **Reproducibility**: The entire suite runs locally in seconds with 100% passing automated unit tests.

---

## 5. Recommended Concrete Improvements

1. **Implement Throttle-Dependent BSFC Curve**: Update `propulsion.py` with an off-design penalty: $\text{BSFC}(P) = \text{BSFC}_{\text{ref}} \cdot \left[1 + 0.15 \cdot (1 - P / P_{\text{max}})^2\right]$.
2. **Add Direct Operating Cost (DOC) Calculator**: Calculate net airline profit/loss including both fuel saved and battery cell depreciation per flight.
3. **Clarify Model Card Status**: Ensure documentation explicitly classifies Gemma 3 270M as a verified template service awaiting local checkpoint loading in Phase 3.
