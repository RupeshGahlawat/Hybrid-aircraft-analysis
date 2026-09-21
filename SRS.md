# Software Requirements Specification (SRS)
## AeroHybrid: Regional Aircraft Hybrid-Electric Propulsion Digital Twin & Feasibility System
**Document Identifier**: SRS-AEROHYBRID-2026-V1  
**Status**: DRAFT / ENGINEERING BASELINE  
**Classification**: Research & Engineering Specification  

---

## 1. System Purpose
The purpose of the AeroHybrid platform is to provide a deterministic, physics-grounded simulation, statistical surrogate inference engine, and interactive digital twin for evaluating the mission performance, mass convergence, and net emissions of Parallel Hybrid-Electric Propulsion (HEP) architectures applied to 50–70 seat commercial regional turboprops (ATR 72-600 baseline).

---

## 2. System Scope
* **In Scope**:
  * Point-mass 2D/3D kinematic flight trajectory integration (Takeoff Roll, Climb, Cruise, Descent).
  * International Standard Atmosphere (ISA) with hot-day density altitude lapse ($\Delta T \le +25^\circ\text{C}$).
  * Mass balance sizing conforming to FAR Part 25/121 kerosene reserve mandates (45 min hold + 100 km diversion).
  * Indian regional connectivity (UDAN) operational airport benchmarking (elevation, runway length, CEA grid emissions).
  * Microsecond polynomial regression surrogate for fast design-space exploration.
  * Real-time 60 FPS WebGL digital twin with glass-cockpit Primary Flight Display (PFD).
* **Out of Scope (Current Release)**:
  * Full 6-DOF aerodynamic stability and control derivative simulation (lateral/directional Dutch roll, roll damping).
  * Electrochemical cell-level electrochemical degradation (SEI layer formation kinetics) [PLANNED].
  * High-voltage aero-electrical arcing and Paschen's law dielectric breakdown modeling [ASSUMED/PLANNED].
  * Local weight-loaded Gemma 3 270M PyTorch model inference (currently implemented as deterministic verified template service) [PLANNED].

---

## 3. System Actors
1. **Research Aeronautical Engineer**: Configures technological horizon parameters (battery $Wh/kg$, $H_P$ ratio, motor $kW/kg$) and inspects governing math equations.
2. **Airline Fleet Analyst**: Evaluates stage lengths, passenger seat-shedding risks, block fuel burn deltas, and grid recharge emissions.
3. **Academic / Defense Evaluator**: Validates model assumptions, certification limits, and test repeatability.
4. **Automated Client / Frontend**: Vite React single-page application consuming REST endpoints and WebSocket telemetry frames.

---

## 4. System Context & Interfaces
```
 [User Browser (Vite/React)] 
      │ (HTTP / JSON)
      ├──> GET  /api/routes         ──> [UDAN Routes Database]
      ├──> POST /api/simulate       ──> [Mission Simulator Core] ──> [Weight Loop] ──> [Propulsion Model]
      ├──> GET  /api/surrogate      ──> [Surrogate Regression Model]
      └──> WS   /ws/telemetry       ──> [Telemetry Frame Streamer]
```

---

## 5. Functional Requirements (Traceable)

### 5.1 Atmospheric & Environmental Physics
* **SRS-FR-001**: The system shall compute ambient atmospheric pressure $p(h)$, air density $\rho(h)$, temperature $T(h)$, and speed of sound $a(h)$ for geopotential altitudes between $0\text{ m}$ and $11,000\text{ m}$ according to the 1976 International Standard Atmosphere.
* **SRS-FR-002**: The system shall accept an ambient temperature offset $\Delta T \in [-10^\circ\text{C}, +30^\circ\text{C}]$ above standard ISA temperature, calculating actual air density as $\rho = p / (R_{\text{air}} \cdot (T_{\text{isa}} + \Delta T))$.

### 5.2 Airframe & Aerodynamics
* **SRS-FR-003**: The system shall model the ATR 72-600 baseline with reference wing area $S = 61.0\text{ m}^2$, aspect ratio $AR = 12.0$, and clean Oswald efficiency $e = 0.84$.
* **SRS-FR-004**: The system shall compute total aerodynamic drag using the parabolic drag polar:
  $$C_D = C_{D0} + \frac{C_L^2}{\pi \cdot AR \cdot e}$$
  Where $C_{D0,\text{clean}} = 0.0242$, $C_{D0,\text{takeoff}} = 0.0385$, and $C_{D0,\text{landing}} = 0.0550$.

### 5.3 Hybrid Propulsion & Energy Management
* **SRS-FR-005**: The system shall support a Degree of Hybridization of Power $H_P \in [0.0, 0.50]$, defining the electric motor share of installed takeoff power ($P_{\text{total}} = 4,100\text{ kW}$).
* **SRS-FR-006**: The system shall enforce a minimum usable battery State of Charge ($\text{SOC}_{\text{min}} = 0.20$), cutting off electric boost when $\text{SOC} \le 0.20$.
* **SRS-FR-007**: The system shall calculate instantaneous fuel flow rate as:
  $$\dot{m}_{\text{fuel}} = \frac{P_{\text{shaft, turboshaft}} \cdot \text{BSFC}}{3600}$$
  Where $\text{BSFC}_{\text{takeoff}} = 0.275\text{ kg/(kW}\cdot\text{h)}$ and $\text{BSFC}_{\text{cruise}} = 0.295\text{ kg/(kW}\cdot\text{h)}$.
* **SRS-FR-008**: The system shall calculate thermal management waste heat as $\dot{Q}_{\text{waste}} = P_{\text{battery}} - P_{\text{shaft, electric}}$.

### 5.4 Mass Balance & Certification Reserves
* **SRS-FR-009**: The system shall enforce FAR Part 121 reserve fuel rules by adding a fixed $550\text{ kg}$ kerosene reserve (45 min holding fuel + 100 km alternate diversion fuel) on top of calculated mission fuel.
* **SRS-FR-010**: If calculated Takeoff Weight exceeds Maximum Takeoff Weight ($\text{MTOW} = 23,000\text{ kg}$), the system shall shed passenger seats at $95\text{ kg/seat}$ until $\text{TOW} \le \text{MTOW}$, reporting `is_feasible = False` if passenger capacity drops below 50 seats.

### 5.5 Flight Mission Simulation
* **SRS-FR-011**: The system shall numerically integrate 4 discrete flight phases: Takeoff Ground Roll ($0 \to V_R$), Climb ($V_R \to \text{FL Cruise}$), Cruise (constant altitude), and Descent (flight idle).
* **SRS-FR-012**: The output trajectory profile shall emit second-by-second records containing: `time_s`, `distance_km`, `altitude_ft`, `airspeed_kt`, `pitch_deg`, `turboshaft_power_kw`, `electric_power_kw`, `fuel_burned_kg`, and `battery_soc_pct`.

### 5.6 Machine Learning Surrogate & Language Services
* **SRS-FR-013**: The system shall provide an analytical surrogate model predicting fuel savings percentage, fuel savings mass, and MTOW with a 95% confidence interval in $< 1.0\text{ ms}$.
* **SRS-FR-014**: The system shall generate structured technical summaries where 100% of reported numerical values are audited against the physics simulation dictionary.

---

## 6. Non-Functional Requirements (NFR)

* **SRS-NFR-001 (Latency)**: The `/api/simulate` endpoint shall complete execution in $< 200\text{ ms}$ for any supported route under single-client load.
* **SRS-NFR-002 (Inference Latency)**: The `/api/surrogate` endpoint shall complete execution in $< 5\text{ ms}$ (measured local baseline: $0.08\text{ ms}$).
* **SRS-NFR-003 (Rendering Performance)**: The 3D viewport shall sustain $\ge 55\text{ FPS}$ on WebGL 2.0 compatible hardware.
* **SRS-NFR-004 (Theme Compliance)**: The UI design shall strictly adhere to the off-white clean-room palette (`#F8FAFC`, `#FFFFFF`, `#E2E8F0`, `#0F172A`) with zero dark-theme stylesheets.
* **SRS-NFR-005 (Reliability)**: The backend shall return standardized HTTP error responses (`400`, `422`, `500`) with structured JSON error bodies on invalid input parameters.
* **SRS-NFR-006 (Zero-Cloud Autonomy)**: The entire simulation, backend, and 3D frontend shall operate fully offline without external API dependencies.

---

## 7. Input / Output Requirements

### 7.1 Input Specification
```json
{
  "route_id": "BLR-IXG",
  "hp_fraction": 0.30,
  "battery_wh_per_kg": 400.0,
  "ambient_delta_c": 0.0
}
```
* `route_id`: String, must exist in `UDAN_ROUTES` (`BLR-IXG`, `BOM-PNQ`, `DEL-DED`, `MAA-TIR`, `AMD-UDR`).
* `hp_fraction`: Float $\in [0.0, 0.50]$.
* `battery_wh_per_kg`: Float $\in [200.0, 700.0]$.
* `ambient_delta_c`: Float $\in [-10.0, 30.0]$.

### 7.2 Output Specification
Structured JSON containing:
* `route`: Metadata of origin/destination.
* `parameters`: Echo of normalized inputs.
* `summary`: Aggregate metrics (fuel burn delta, CO2 delta, MTOW, passenger capacity).
* `telemetry_hybrid`: Time-series array of state vectors.
* `telemetry_conv`: Time-series array of baseline conventional flight.
* `ai_analyst`: Verified analytical report card.

---

## 8. Safety & Failure Behavior
* **SRS-SAF-001**: Simulation outputs must be explicitly labeled as "Conceptual Feasibility Estimates - Not for Direct Flight Planning or Certification Dispatch".
* **SRS-SAF-002**: If input parameters exceed physical stability envelopes (e.g., $H_P > 0.60$ or $W_{\text{batt}} < 150\text{ Wh/kg}$), the system shall clamp values to physical limits and emit a warning flag.
* **SRS-SAF-003**: The AI analyst component shall never perform direct actuation or bypass mathematical sizing limits; its outputs are strictly informational decision support.

---

## 9. Acceptance Criteria
* **AC-01**: Running a simulation on route `BOM-PNQ` at $H_P = 0.30, 400\text{ Wh/kg}$ must output a positive fuel savings $> 15\%$ with `passengers_carried = 70`.
* **AC-02**: All 3D aircraft components (high wing, twin nacelles, 6-blade props, T-tail, runway) must render visibly on initial page load without console exceptions.
* **AC-03**: All unit tests under `tests/` must pass cleanly via `pytest`.
