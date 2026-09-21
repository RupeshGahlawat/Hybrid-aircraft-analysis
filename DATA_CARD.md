# Data Card: AeroHybrid Datasets
**Document Identifier**: DC-AEROHYBRID-2026-V1  
**Last Updated**: 2026-09-19  

---

## 1. Dataset Overview

AeroHybrid uses a **hybrid real-and-synthetic dataset architecture**:
1. **Certified Aircraft & Engine Engineering Baseline (Real)**
2. **Indian Regional Aviation (UDAN) Operational Routes (Real)**
3. **Point-Mass Trajectory Simulation Telemetry (Synthetic / Physics-Generated)**

---

## 2. Dataset 1: ATR 72-600 Engineering Baseline

* **Dataset Name**: ATR 72-600 Certified Operational Baseline
* **Source**:
  * EASA Type Certificate Data Sheet (TCDS No. A.084)
  * ATR 72-600 Flight Crew Operating Manual (FCOM)
  * Pratt & Whitney Canada PW127F Engine Performance Manual
* **Size**: 28 structural, aerodynamic, and thermodynamic scalar parameters.
* **Format**: Immutable Python Dataclass (`backend/sim_core/aircraft_specs.py`).
* **Key Features**:
  * Maximum Takeoff Weight (MTOW): $23,000\text{ kg}$
  * Operating Empty Weight (OEW): $13,500\text{ kg}$
  * Wing Reference Area ($S$): $61.0\text{ m}^2$
  * Aspect Ratio ($AR$): $12.0$
  * Zero-Lift Drag Coefficient ($C_{D0}$ clean): $0.0242$
  * Engine Takeoff Power: $2 \times 2,050\text{ kW}$ ($2,750\text{ shp}$ each)
  * Brake Specific Fuel Consumption (BSFC): $0.275\text{ kg/(kW}\cdot\text{h)}$ (takeoff), $0.295\text{ kg/(kW}\cdot\text{h)}$ (cruise)
* **Collection Method**: Extracted from certified aerospace manufacturer documentation.
* **Preprocessing**: Units converted from imperial (shp, lbs) to SI standards (kW, kg, m).
* **Known Limitations & Biases**:
  * Assumes clean airframe without ice accretion or surface roughness degradation.
  * Engine fuel burn is modeled using linearized BSFC rather than dynamic dual-spool compressor maps.
* **Intended Use**: Benchmark baseline against which hybrid-electric retrofits are evaluated.
* **Non-Intended Use**: Operational flight dispatch, payload manifests, or airline flight planning.

---

## 3. Dataset 2: Indian UDAN Regional Routes Database

* **Dataset Name**: Indian Regional UDAN Sector Operational Profiles
* **Source**:
  * Directorate General of Civil Aviation (DGCA) India Airport Directory
  * Central Electricity Authority (CEA) of India CO2 Baseline Database (Version 19)
  * OpenStreetMap / ICAO Airport Charts
* **Size**: 5 representative regional routes connecting 10 certified Indian airports.
* **Format**: Structured Python Dictionary (`backend/sim_core/routes.py`).
* **Features per Route**:
  * `route_id`: String identifier (e.g. `BOM-PNQ`)
  * `stage_distance_km`: Great-circle stage length (115 km to 462 km)
  * `origin.elevation_ft`: Runway elevation above sea level (39 ft to 3,000 ft)
  * `origin.runway_length_m`: Available Takeoff Run (TORA) (2,140 m to 4,430 m)
  * `origin.avg_summer_oat_c`: Typical peak summer ambient temperature (33°C to 43°C)
  * `regional_grid_co2_kg_per_kwh`: CEA regional carbon factor ($0.68\text{--}0.79\text{ kg CO}_2\text{/kWh}$)
* **Collection Method**: Compiled from official government publications.
* **Known Biases**: Routes represent a curated sample of high-traffic UDAN feeder corridors and do not represent the entirety of India's 100+ domestic airports.
* **Licensing**: Public sector government reference data.

---

## 4. Dataset 3: Simulated Mission Telemetry Stream (Synthetic)

* **Dataset Name**: AeroHybrid Synthetic Flight Mission Telemetry
* **Source**: Deterministic point-mass trajectory numerical integrator (`backend/sim_core/mission_sim.py`).
* **Size**: Dynamic; ~150 to ~250 time-series records per simulated flight route.
* **Features per Record**:
  * `time_s`: Elapsed mission time (seconds)
  * `phase`: Flight segment (`takeoff`, `climb`, `cruise`, `descent`, `landing`)
  * `distance_km`: Distance traveled along route
  * `altitude_ft`: Altitude above mean sea level
  * `airspeed_kt`: Calibrated Indicated Airspeed (KIAS)
  * `pitch_deg`: Aircraft body pitch attitude angle
  * `turboshaft_power_kw`: Instantaneous mechanical power from gas turbines
  * `electric_power_kw`: Instantaneous mechanical boost from electric motors
  * `fuel_flow_kg_hr`: Instantaneous fuel consumption rate
  * `fuel_burned_kg`: Cumulative fuel consumed
  * `battery_soc_pct`: Remaining usable battery State of Charge
  * `waste_heat_kw`: Thermal heat rejected by power electronics & motors
* **Collection Method**: Forward numerical Euler integration at variable time steps ($\Delta t = 1.0\text{ s}$ to $30.0\text{ s}$).
* **Data Leakage Risks**: Zero data leakage; telemetry is generated strictly using physical differential equations.
* **Validation & Quality Checks**:
  * Total fuel burn verified against published ATR-72 FCOM trip fuel figures (~1,200 kg for 450 km).
  * Takeoff roll distance verified against ATR-72 takeoff field length charts (~1,300 m at MTOW).
