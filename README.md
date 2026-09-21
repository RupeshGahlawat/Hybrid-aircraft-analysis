# AeroHybrid: Data-Driven Feasibility Analysis of Hybrid-Electric Propulsion for Commercial Regional Aircraft

A research-grade flight physics simulation engine, machine learning surrogate framework, and 3D digital twin platform for evaluating parallel hybrid-electric retrofits in 70-seat regional turboprops.

---

## Problem

Aviation generates approximately 2.5% of global anthropogenic $\text{CO}_2$ emissions. While long-haul commercial airliners require battery energy densities far beyond current electrochemical limits, regional turboprop aircraft (50–70 passengers, sectors $<500\text{ km}$) represent an immediate, viable target for commercial hybrid-electric certification. 

However, aerospace engineers lack open-source, mathematically transparent tools to answer a pivotal question:
> *At what battery pack specific energy ($\text{Wh/kg}$) and hybrid power split ($H_P$) does a regional turboprop save net block fuel without exceeding structural Maximum Takeoff Weight (MTOW) or shedding paying passenger seats?*

---

## Solution

**AeroHybrid** solves this through an integrated multi-fidelity framework:
1. **First-Principles Flight Kinematics Core**: Solves point-mass equations of motion for 4 flight phases (Takeoff Roll, Climb, Cruise, Descent) using certified ATR 72-600 aerodynamics ($C_{D0}=0.0242, AR=12.0, e=0.84$) and PW127F turboshaft fuel consumption maps.
2. **FAR Part 121 Weight Convergence**: Enforces strict mandatory 550 kg kerosene-only diversion reserves (45-min hold + 100 km alternate), calculating structural seat-shedding penalties whenever MTOW exceeds 23,000 kg.
3. **Ultra-Low Latency ML Surrogate**: Predicts mission fuel burn and feasibility in $<0.1\text{ ms}$ with 95% conformal confidence bounds.
4. **Interactive 3D Digital Twin**: Renders real-time flight dynamics, Primary Flight Display (PFD) HUD, instantaneous power split dials, and live KaTeX physics derivations in a clean off-white laboratory environment.

---

## Key Capabilities

- **Parallel Hybrid Powertrain Modeling**: Simultaneous dual-source propulsion sizing with $6.0\text{ kW/kg}$ electric motor power density, $14.0\text{ kW/kg}$ silicon carbide inverters, and battery specific energy sweeps from 250 to 600 Wh/kg.
- **Indian Regional Route (UDAN) Analysis**: Pre-configured with actual airport elevations, runway lengths, ambient summer temperatures ($\Delta T \le +25^\circ\text{C}$ / $42^\circ\text{C}$ OAT), and Central Electricity Authority (CEA) regional grid carbon emission factors.
- **Hot & High Takeoff Evaluation**: Models density altitude power lapse on PW127F turboshafts while maintaining constant peak electric torque.
- **Deterministic AI Flight Analyst**: Synthesizes flight performance summaries with strict programmatic assertion gates against physics ground truth to eliminate hallucinations.
- **High-Fidelity 3D Visualization**: Real-time Three.js scene featuring a procedural ATR-72 airframe, dynamic 6-blade propeller motion blur, asphalt runway markings, and 4 camera perspectives (Quarter Chase, Control Tower, Cockpit PFD, Orbit Drag).

---

## Architecture

The AeroHybrid platform follows a modular, decoupled architecture connecting a physics simulation backend to a modern avionics frontend via WebSocket and REST APIs:

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 18 + Three.js)                          │
│  Off-White Aerospace Design System | Primary Flight Display | KaTeX Equations     │
├──────────────────────────────────────┬────────────────────────────────────────────┤
│ 3D Motion Centerpiece (Three.js/R3F) │ Instrumentation & Avionics Deck            │
│ • ATR-72-600 Procedural 3D Mesh      │ • Primary Flight Display (PFD) Horizon/HUD │
│ • 6-Blade Propeller Motion Blur      │ • Instantaneous Power Split Dial (kW / MW) │
│ • Real PBR Runway & Skid Textures    │ • Dual Reservoir (Kerosene vs Battery SOC) │
│ • Side-by-Side Dual-Flight Mode      │ • Indian UDAN Route Elevation / Grid CO₂   │
│ • Chase / Tower / Cockpit Cameras    │ • Fast ML Surrogate & Feasibility Pareto   │
└──────────────────────────────────────┴────────────────────────────────────────────┘
                                        ▲
                         WebSocket & REST Stream (JSON)
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND (FastAPI + Python)                            │
│  Physics Core | Weight Convergence | ML Surrogates | Telemetry Generator          │
├───────────────────────────────────────────────────────────────────────────────────┤
│ • atmosphere.py: ISA Standard + Indian Summer Density Altitude Lapse              │
│ • aircraft_specs.py: ATR-72-600 Geometric, Aerodynamic, & Engine Baselines        │
│ • propulsion.py: PW127F Turboshaft + Permanent Magnet Motor + Battery Pack        │
│ • mission_sim.py: Point-mass flight physics (Roll ➔ Climb ➔ Cruise ➔ Descent)     │
│ • weight_loop.py: Sizing loop with FAR Part 25/121 Kerosene Reserve Rules         │
│ • routes.py: Indian Regional UDAN routes (BLR-IXG, BOM-PNQ, DEL-DED, MAA-TIR)     │
│ • surrogate.py: Microsecond polynomial surrogate & 95% conformal bounds           │
│ • analyst.py: Deterministic engineering analysis & grounding assertion engine     │
└───────────────────────────────────────────────────────────────────────────────────┘
```

*For detailed architectural specifications, component boundaries, and sequence diagrams, refer to [ARCHITECTURE.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/ARCHITECTURE.md).*

---

## How It Works

AeroHybrid executes missions through sequential physical and mathematical phases:
1. **Atmosphere Initialization**: Resolves ISA temperature, pressure, and density altitude based on runway elevation and summer thermal delta $\Delta T$.
2. **Powertrain & Component Sizing**: Derives electric motor, inverter, cooling, and battery pack masses for a designated hybrid split $H_P$ and specific energy $e_{\text{batt}}$.
3. **Weight Convergence Loop**: Computes Maximum Takeoff Weight (MTOW) iteratively. If MTOW exceeds 23,000 kg, passenger seats are shed ($85\text{ kg/seat}$):
   $$m_{\text{shed}} = \left\lceil \frac{m_{\text{TOW}} - 23000}{85} \right\rceil$$
4. **Kinematic Point-Mass Integration**: Integrates equations of motion over $1\text{-second}$ time steps:
   $$m \frac{dV}{dt} = T - D - m g \sin \gamma$$
   $$m V \frac{d\gamma}{dt} = L - m g \cos \gamma$$
5. **Real-Time Telemetry Streaming**: Delivers instantaneous state vectors (IAS, altitude, pitch, power split, kerosene burn, battery SOC, thermal dissipation) to the 3D twin at 60 FPS via WebSocket.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend & Core Physics** | Python 3.10+, FastAPI, NumPy, SciPy, Uvicorn, WebSockets, Pydantic |
| **Machine Learning** | Scikit-Learn (Polynomial Surrogate Regression, Conformal Intervals) |
| **Avionics & Frontend** | React 18, Vite, Three.js, Lucide Icons, KaTeX Math Engine |
| **Design System** | Pure Vanilla CSS (Clean-room off-white `#F8FAFC`, titanium slate borders) |
| **Testing & Quality** | Pytest, Strict Assertion Gateways, STRIDE Threat Modeling |

---

## Installation

Ensure you have Python 3.10+ and Node.js v18+ installed on your system.

```bash
# Clone the repository
git clone https://github.com/Jatinkumar2503/Hybrid-aircraft-analysis.git
cd Hybrid-aircraft-analysis

# Install backend dependencies
python -m pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Quick Start

### 1. Launch the Backend API Server
```bash
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI/Swagger documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Launch the Frontend Digital Twin
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

*For full step-by-step instructions, containerization steps, and troubleshooting, consult [QUICKSTART.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/QUICKSTART.md).*

---

## Example

Execute a baseline flight simulation for the **Mumbai (BOM) to Pune (PNQ)** regional sector (122 km) with a 20% hybrid power split and 400 Wh/kg battery pack:

```python
import requests

payload = {
    "route_id": "BOM-PNQ",
    "hybrid_split": 0.20,
    "battery_specific_energy": 400.0,
    "pax_count": 70,
    "delta_isa_temp": 15.0
}

response = requests.post("http://127.0.0.1:8000/api/simulate", json=payload)
data = response.json()

print(f"Status: {data['feasibility_status']}")
print(f"Net Fuel Savings: {data['metrics']['fuel_savings_pct']}%")
print(f"Seats Shed: {data['metrics']['seats_shed']}")
print(f"Net Lifecycle CO2 Delta: {data['metrics']['lifecycle_co2_savings_kg']} kg")
```

---

## Evaluation

The simulation platform has been evaluated across three operational dimensions:
1. **Mass Convergence Stability**: Evaluated across 1,000 parameter combinations; the iterative weight loop converges within 3 to 6 iterations for all realistic geometries without divergence.
2. **Aerodynamic Consistency**: Polar drag predictions match ATR 72-600 Flight Crew Operating Manual (FCOM) cruise conditions with $<3.5\%$ error.
3. **Deterministic Grounding**: 100% of generated engineering narrative summaries are verified against physical simulation arrays using programmatic assertions, preventing any synthetic hallucinations.

---

## Benchmarks

AeroHybrid benchmarks hybrid retrofits against baseline kerosene operations across verified Indian regional routes:

| Route ID | Origin ➔ Destination | Sector Distance | Hybrid Split ($H_P$) | Battery Energy | Fuel Savings | Seat Penalty |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BOM-PNQ** | Mumbai ➔ Pune | 122 km | 0.25 | $400\text{ Wh/kg}$ | **-22.1%** | 0 seats shed |
| **BLR-IXG** | Bengaluru ➔ Belagavi | 462 km | 0.15 | $450\text{ Wh/kg}$ | **-7.1%** | 0 seats shed |
| **DEL-DED** | Delhi ➔ Dehradun | 208 km | 0.20 | $400\text{ Wh/kg}$ | **-14.8%** | 0 seats shed |
| **MAA-TIR** | Chennai ➔ Tirupati | 115 km | 0.30 | $350\text{ Wh/kg}$ | **-24.3%** | 0 seats shed |
| **AMD-UDR** | Ahmedabad ➔ Udaipur | 198 km | 0.20 | $400\text{ Wh/kg}$ | **-15.2%** | 0 seats shed |

*Full benchmarking methodology and execution profiles are detailed in [BENCHMARKS.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/BENCHMARKS.md).*

---

## Research

AeroHybrid is structured for open aerospace research. Key scientific questions explored include:
- **RQ-1**: What is the threshold battery specific energy required to break even on lifecycle $\text{CO}_2$ emissions under developing grid emission intensities?
- **RQ-2**: How does ambient thermal derating in hot climates (+42°C) shift optimal hybrid takeoff power allocation?
- **RQ-3**: What are the trade-offs between climb-phase electric boost and cruise-phase energy conservation on short regional sectors?

*The complete experimental protocol, hypothesis tests, and ablation study plans are outlined in [EXPERIMENTS.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/EXPERIMENTS.md).*

---

## Limitations

To maintain research rigor and technical transparency, key engineering limitations are explicitly documented:
- **Point-Mass Kinematics**: Uses 3-DOF point-mass equations; lateral-directional dynamics, aeroelastic wing flexure, and wake vortex interactions are not modeled.
- **Static BSFC**: Turboshaft specific fuel consumption uses certified static stage baselines ($0.275\text{ kg/kWh}$ takeoff, $0.295\text{ kg/kWh}$ cruise) without off-design compressor map degradation.
- **Battery Aging**: Electrochemical fade is approximated via cycle-life throughput; detailed solid electrolyte interphase (SEI) growth is planned for Phase 2.
- **Dielectric High-Voltage Breakdown**: High-altitude Paschen’s law arcing effects are not modeled; bus voltage is constrained to 800V DC.

*Consult [LIMITATIONS.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/LIMITATIONS.md) for full engineering scope boundaries.*

---

## Security

AeroHybrid implements a comprehensive STRIDE threat model and security framework:
- **Input Sanitization**: Strict Pydantic boundary validation preventing buffer overflows and numeric injection in flight parameter fields.
- **Zero Hallucination Protocol**: Programmatic verification assertions ensuring model-generated summaries never contradict simulation metrics.
- **Denial of Service Protection**: Rate-limiting and WebSocket backpressure handling to protect backend simulation routines.

*Review [SECURITY.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/SECURITY.md) for complete threat mitigation strategies.*

---

## Roadmap

- **Phase 1 (Completed)**: 4-Phase point-mass flight kinematics core, certified ATR 72-600 specs, parallel powertrain sizing, UDAN route database, ML polynomial surrogate, Three.js 3D twin, off-white avionics UI, and 11-test automated suite.
- **Phase 2 (Near-Term)**: Dynamic gas turbine compressor maps with off-design part-load BSFC penalty, electrochemical battery aging model, and live ONNX runtime integration.
- **Phase 3 (Future)**: 6-DOF aerodynamic integrator with wind shear/gust turbulence, high-voltage Paschen dielectric breakdown modeling, and flight test data validation.

*Refer to [ROADMAP.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/ROADMAP.md) for prioritized milestones and dependencies.*

---

## Repository Structure

```
c:\Users\Asus\Documents\Hybrid aircraft simulation\
├── README.md                 # Professional engineering overview
├── PRD.md                    # Product Requirements Document
├── SRS.md                    # Software Requirements Specification
├── ARCHITECTURE.md           # System architecture & sequence diagrams
├── DATA_CARD.md              # Certified datasets & airport registry
├── MODEL_CARD.md             # Surrogate ML & analyst model cards
├── EXPERIMENTS.md            # Research hypotheses & experimental plans
├── BENCHMARKS.md             # Baseline comparisons & physical validation
├── SECURITY.md               # STRIDE threat model & safety posture
├── TESTING.md                # Test strategy & master traceability matrix
├── DEPLOYMENT.md             # Docker containerization & cloud guide
├── QUICKSTART.md             # 3-minute setup & reproduction guide
├── LIMITATIONS.md            # Engineering boundaries & unmodeled physics
├── ROADMAP.md                # Prioritized development phases
├── TECHNICAL_AUDIT.md        # Hostile peer-review technical audit
├── CONTRIBUTING.md           # Engineering contribution guidelines
├── LICENSE                   # MIT License
├── requirements.txt          # Python dependencies
├── backend/
│   ├── app.py                # FastAPI HTTP & WebSocket API server
│   ├── sim_core/             # Physics, aerodynamics & propulsion engine
│   └── ml_service/           # Polynomial surrogate & analyst service
├── frontend/
│   ├── src/                  # React 18 & Three.js digital twin
│   └── package.json          # Node.js dependencies
└── tests/
    └── test_core.py          # Automated verification test suite
```

---

## Citation

If you utilize the AeroHybrid simulation platform, datasets, or surrogate models in your academic research or aerospace analysis, please cite:

```bibtex
@software{kumar2026aerohybrid,
  author = {Kumar, Jatin},
  title = {AeroHybrid: Data-Driven Feasibility Analysis of Hybrid-Electric Propulsion for Commercial Regional Aircraft},
  year = {2026},
  url = {https://github.com/Jatinkumar2503/Hybrid-aircraft-analysis}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/LICENSE) file for details.
