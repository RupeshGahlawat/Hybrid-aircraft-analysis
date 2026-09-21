# Engineering Limitations & Scope Boundaries
## AeroHybrid Platform Assumptions and Known Limitations

**Document Identifier**: LIM-AEROHYBRID-2026-V1  
**Status**: ACTIVE ENGINEERING ASSESSMENT  

---

## 1. Aerodynamic & Kinematic Limitations

1. **Point-Mass vs. 6-DOF Dynamics**:
   * *Limitation*: The trajectory integrator treats the aircraft as a 2D/3D point mass governed by forward acceleration $\dot{V}$ and vertical climb rate $\dot{h}$. 
   * *What Is Missing*: Full 6-Degree-of-Freedom (6-DOF) cross-axis coupling, Dutch roll damping, elevator deflection moments, and aileron roll control derivatives are not modeled.
   * *Impact on Feasibility*: Minimal for macro fuel burn and energy sizing; significant for flight control law certification.
2. **Linearized Parabolic Drag Polar**:
   * *Limitation*: Aerodynamic drag is evaluated using $C_D = C_{D0} + K C_L^2$ with constant Oswald efficiency $e=0.84$.
   * *What Is Missing*: Compressibility wave drag divergence, aeroelastic wing flex under heavy nacelle/motor mass, and propeller slipstream blown-wing lift amplification.
3. **Propeller Efficiency Constant**:
   * *Limitation*: Propeller efficiency is discretized into three fixed operating points: $\eta_{\text{takeoff}} = 0.72$, $\eta_{\text{climb}} = 0.81$, and $\eta_{\text{cruise}} = 0.85$.
   * *What Is Missing*: Continuous Blade Element Momentum Theory (BEMT) resolving local Mach number and advance ratio $J = V / (n D)$.

---

## 2. Propulsion & Battery Electrochemical Limitations

1. **Cell-Level Electrochemical Aging**:
   * *Limitation*: Battery degradation is currently modeled as a conservative operational depth-of-discharge buffer ($\text{SOC}_{\text{min}} = 20\%$).
   * *What Is Missing*: Dynamic solid electrolyte interphase (SEI) layer growth, active lithium loss, and thermal runaway propagation kinetics across multi-thousand flight cycles are not yet integrated into the active simulation loop.
2. **Linearized Brake Specific Fuel Consumption (BSFC)**:
   * *Limitation*: Turboshaft fuel burn uses static BSFC constants ($0.275\text{ kg/kWh}$ takeoff, $0.295\text{ kg/kWh}$ cruise).
   * *What Is Missing*: Realistic off-design turbine compressor maps where throttling down a gas turbine severely degrades thermal efficiency (the "part-load penalty").
3. **Lumped-Parameter Thermal Management System (TMS)**:
   * *Limitation*: TMS mass is sized using a linear specific mass coefficient ($0.15\text{ kg/kW}_{\text{thermal}}$).
   * *What Is Missing*: Dynamic ram-air heat exchanger CFD sizing, radiator cooling momentum drag increments, and high-temperature ambient cooling limits at FL200.

---

## 3. High-Voltage Electrical & Certification Limitations

1. **Paschen's Law & Dielectric Breakdown**:
   * *Limitation*: Electrical wiring mass includes an assumed +12% weight margin for insulation and switchgear.
   * *What Is Missing*: Altitude-dependent partial discharge simulation. At cruising altitudes (20,000 ft), lower atmospheric pressure drops the dielectric breakdown voltage of air significantly. Megawatt-class distribution ($>800\text{V}$) requires pressurized conduits or specialized polyimide insulation that could add higher weight penalties.
2. **Certification & Emergency Reserves**:
   * *Limitation*: Reserve kerosene is fixed at 550 kg (FAR Part 121 compliance).
   * *What Is Missing*: EASA/FAA Special Conditions for hybrid aircraft have not yet been formalized into international law; battery dispatch reliability credit remains uncertified.

---

## 4. Machine Learning & Language Model Boundaries

1. **Surrogate Domain Boundaries**:
   * *Limitation*: The surrogate is calibrated on regional turboprop mission sweeps ($100\text{--}600\text{ km}$, $H_P \le 0.50$, $e_{\text{batt}} \le 700\text{ Wh/kg}$).
   * *What Is Missing*: It cannot be applied to narrow-body jets (A320/B737) or supersonic aircraft without complete recalibration.
2. **Gemma 3 270M Analyst Service**:
   * *Limitation*: Currently executed as a deterministic structured template service with programmatic assertion audits.
   * *What Is Missing*: Full local weight-loaded neural inference via PyTorch is planned for Phase 3.
