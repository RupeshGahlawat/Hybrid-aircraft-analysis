"""
Safety & Failure Mode Envelope Checks (CS-25 / FAR Part 25 Commuter Regulations).
Models:
1. One-Engine-Inoperative (OEI) Second-Segment Climb Gradient Check (CS-25.121):
   Verifies that with one engine inoperative, the surviving PW127M operating at
   Automatic Power Reserve (APR = 2,750 SHP / 2,050.7 kW) meets the mandatory 2.4% net climb gradient.
2. In-Flight Complete Electrical Boost Failure Check:
   Verifies that if all hybrid electric boost is lost during takeoff or climb,
   the twin turboshafts operating at maximum continuous rating can safely maintain positive climb gradient.
"""
import math
from dataclasses import dataclass

from .aircraft_specs import ATR72_BASELINE, AircraftBaseline
from .atmosphere import G0, get_atmosphere
from .propeller import PropellerModel


@dataclass(frozen=True)
class SafetyCheckResult:
    oei_climb_gradient_pct: float
    oei_required_gradient_pct: float
    oei_check_passed: bool
    elec_failure_climb_gradient_pct: float
    elec_failure_check_passed: bool
    excess_power_oei_kw: float
    details: dict[str, float]

def evaluate_safety_envelope(
    takeoff_mass_kg: float,
    altitude_m: float = 0.0,
    ambient_delta_c: float = 0.0,
    specs: AircraftBaseline = ATR72_BASELINE,
    prop_model: PropellerModel = PropellerModel()
) -> SafetyCheckResult:
    """
    Evaluates regulatory climb gradient safety margins under engine-out and electric-out failure conditions.
    """
    atm = get_atmosphere(altitude_m, ambient_delta_c)
    rho = atm["density_kg_m3"]

    # Takeoff safety speed V2 = 1.20 * V_stall
    cl_max_to = specs.cl_max_takeoff
    v_stall = math.sqrt((2.0 * takeoff_mass_kg * G0) / (rho * specs.wing_area_m2 * cl_max_to))
    v2 = 1.20 * v_stall
    q_v2 = 0.5 * rho * (v2 ** 2)

    # Clean aerodynamics + gear retracted + flaps 15
    cl_v2 = (takeoff_mass_kg * G0) / (q_v2 * specs.wing_area_m2)
    cd_base = specs.cd0_clean + 0.012 + (cl_v2 ** 2) / (math.pi * specs.aspect_ratio * specs.oswald_efficiency)

    # 1. OEI Case: 1 engine inoperative with propeller feathered (feathered prop drag delta CD ~ +0.0025)
    cd_oei = cd_base + 0.0025
    drag_oei_n = q_v2 * specs.wing_area_m2 * cd_oei

    # Surviving engine at APR power (2,050.7 kW)
    p_apr_kw = specs.apr_power_kw_per_engine
    thrust_oei_n = prop_model.compute_thrust_n(p_apr_kw, v2, rho) # Single engine thrust

    gamma_oei = (thrust_oei_n - drag_oei_n) / (takeoff_mass_kg * G0)
    gamma_oei_pct = gamma_oei * 100.0
    oei_required_pct = 2.4 # CS-25.121(b) second-segment climb requirement for twin-engine
    oei_passed = gamma_oei_pct >= oei_required_pct

    # 2. Complete Electrical Failure Case: Both turboshafts operational at normal continuous rating (1,635 kW each)
    thrust_mcp_n = prop_model.compute_thrust_n(specs.max_continuous_power_kw, v2, rho) * specs.num_engines
    drag_normal_n = q_v2 * specs.wing_area_m2 * cd_base

    gamma_elec_fail = (thrust_mcp_n - drag_normal_n) / (takeoff_mass_kg * G0)
    gamma_elec_fail_pct = gamma_elec_fail * 100.0
    elec_fail_passed = gamma_elec_fail_pct >= 1.5 # Positive safe climb gradient

    return SafetyCheckResult(
        oei_climb_gradient_pct=round(gamma_oei_pct, 2),
        oei_required_gradient_pct=oei_required_pct,
        oei_check_passed=oei_passed,
        elec_failure_climb_gradient_pct=round(gamma_elec_fail_pct, 2),
        elec_failure_check_passed=elec_fail_passed,
        excess_power_oei_kw=round((thrust_oei_n - drag_oei_n) * v2 / 1000.0, 1),
        details={
            "v2_mps": round(v2, 1),
            "v2_kias": round(v2 * 1.94384, 1),
            "thrust_oei_n": round(thrust_oei_n, 0),
            "drag_oei_n": round(drag_oei_n, 0)
        }
    )
