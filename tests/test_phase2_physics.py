"""
Phase 2 Physics Upgrades Unit & Validation Tests:
1. Propeller advance ratio J-curve and takeoff distance to 35 ft screen height vs ATR published 1,279 m.
2. Turboshaft PW127M engine map: flat-rating up to 30°C and part-load BSFC penalty.
3. Battery dual-sizing (energy vs power constraint), C-rate limits, and EOL degradation buffer.
4. Thermal Management System (TMS) waste heat dissipation and active cooling sizing.
5. Safety envelope checks: OEI climb gradient at APR (CS-25.121) and electrical boost failure.
6. Direct Operating Cost (DOC) and ground turnaround charging power constraint.
"""
import pytest

from backend.sim_core.aircraft_specs import get_aircraft_specs
from backend.sim_core.battery import BatteryConfig, size_battery_pack
from backend.sim_core.costs import compute_direct_operating_costs
from backend.sim_core.engine_map import TurboshaftEngineMap
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.propeller import PropellerModel, integrate_takeoff_distance
from backend.sim_core.routes import get_route_by_id
from backend.sim_core.safety import evaluate_safety_envelope
from backend.sim_core.thermal import compute_instantaneous_heat_load_kw, size_tms_mass


# 1. Propeller and Takeoff Model
def test_propeller_j_curve_and_static_thrust():
    prop = PropellerModel()

    # Static regime (V = 0)
    t_static = prop.compute_thrust_n(shaft_power_kw_per_engine=1845.6, true_airspeed_mps=0.0)
    # Total twin static thrust ~ 44 kN (22 kN per engine)
    assert pytest.approx(t_static, rel=0.05) == 22000.0

    # Advance ratio in climb (V = 85 m/s, n = 20 rev/s, D = 3.93 m => J ~ 1.08)
    j_climb = prop.compute_advance_ratio(85.0)
    eta_climb = prop.compute_efficiency(j_climb)
    assert 0.75 < eta_climb <= 0.85

    # Advance ratio in cruise (V = 141.5 m/s => J ~ 1.80)
    j_cruise = prop.compute_advance_ratio(141.5)
    eta_cruise = prop.compute_efficiency(j_cruise)
    assert 0.78 <= eta_cruise <= 0.85

def test_takeoff_distance_comparison_against_atr_fcom():
    """
    ATR published Takeoff Distance to 35 ft screen height at basic MTOW (22,800 kg),
    sea level, standard ISA is 1,279 m (Flaps 15).
    """
    basic_specs = get_aircraft_specs("basic")
    p_total_kw = basic_specs.num_engines * basic_specs.takeoff_power_kw_per_engine # 3,691.2 kW

    tod = integrate_takeoff_distance(
        mass_kg=22800.0,
        total_shaft_power_kw=p_total_kw,
        specs=basic_specs,
        altitude_m=0.0,
        ambient_delta_c=0.0
    )

    published_fcom_m = 1279.0
    simulated_tod_m = tod["total_takeoff_distance_m"]
    error_pct = abs(simulated_tod_m - published_fcom_m) / published_fcom_m * 100.0

    # Simulated takeoff distance must match ATR 72-600 FCOM within 5%
    assert error_pct < 5.0
    assert 1200.0 < simulated_tod_m < 1350.0
    assert 700.0 < tod["ground_roll_m"] < 950.0

# 2. Engine Map & Part-Load BSFC Penalty
def test_engine_flat_rating_and_hot_day_lapse():
    eng = TurboshaftEngineMap()

    # At sea level 15°C (standard ISA): full rated power available
    p_std = eng.compute_available_power_kw(altitude_m=0.0, ambient_delta_c=0.0)
    assert pytest.approx(p_std, rel=1e-3) == 1845.6

    # At 30°C (ISA + 15°C): still flat-rated at 100%
    p_30c = eng.compute_available_power_kw(altitude_m=0.0, ambient_delta_c=15.0)
    assert pytest.approx(p_30c, rel=1e-3) == 1845.6

    # At 42°C (Delhi summer hot day, ISA + 27°C): 12°C above flat-rating
    # Derates by 0.9% per °C => ~10.8% reduction
    p_42c = eng.compute_available_power_kw(altitude_m=0.0, ambient_delta_c=27.0)
    assert p_42c < p_std
    derate_pct = (p_std - p_42c) / p_std * 100.0
    assert pytest.approx(derate_pct, rel=0.1) == 10.8

def test_engine_part_load_bsfc_penalty():
    eng = TurboshaftEngineMap()

    # 100% rated takeoff power: lowest BSFC (high cycle pressure ratio)
    bsfc_takeoff = eng.compute_bsfc_kg_per_kwh(shaft_power_demanded_kw=1845.6)
    assert pytest.approx(bsfc_takeoff, rel=1e-2) == 0.275

    # 60% cruise load: nominal BSFC ~ 0.295 - 0.315 kg/kWh accounting for part-load lapse
    bsfc_cruise = eng.compute_bsfc_kg_per_kwh(shaft_power_demanded_kw=1100.0)
    assert 0.295 <= bsfc_cruise <= 0.315
    assert bsfc_cruise > bsfc_takeoff

    # Deep throttled part-load (35% power during hybrid assist): BSFC increases due to off-design penalty
    bsfc_throttled = eng.compute_bsfc_kg_per_kwh(shaft_power_demanded_kw=600.0)
    assert bsfc_throttled > bsfc_cruise
    assert bsfc_throttled >= 0.320

# 3. Battery Dual Sizing & C-Rate
def test_battery_dual_sizing_energy_vs_power():
    cfg = BatteryConfig(specific_energy_pack_wh_kg=280.0)

    # Long duration low-power draw: should be energy-constrained
    res_energy = size_battery_pack(
        energy_demanded_usable_kwh=150.0,
        peak_power_demanded_kw=300.0,
        config=cfg
    )
    assert res_energy["sizing_driver"] == "ENERGY"
    assert res_energy["is_c_rate_compliant"] is True

    # High burst power draw: should be power-constrained
    res_power = size_battery_pack(
        energy_demanded_usable_kwh=20.0,
        peak_power_demanded_kw=1200.0,
        config=cfg
    )
    assert res_power["sizing_driver"] == "POWER"
    assert res_power["is_c_rate_compliant"] is True
    assert res_power["actual_peak_c_rate"] <= cfg.max_c_rate_peak

# 4. Thermal Management System
def test_thermal_dissipation_and_tms_mass():
    heat = compute_instantaneous_heat_load_kw(
        shaft_power_electric_kw=1000.0,
        battery_draw_power_kw=1100.0,
        motor_efficiency=0.96,
        inverter_efficiency=0.985,
        battery_efficiency=0.95
    )
    assert heat["total_heat_load_kw"] > 0.0
    assert heat["motor_heat_kw"] > 0.0
    assert heat["inverter_heat_kw"] > 0.0
    assert heat["battery_heat_kw"] > 0.0

    tms_mass = size_tms_mass(heat["total_heat_load_kw"])
    assert 10.0 < tms_mass < 50.0

# 5. Safety Checks
def test_safety_envelope_oei_and_electrical_failure():
    safety = evaluate_safety_envelope(takeoff_mass_kg=22800.0)

    # Second-segment OEI climb gradient must meet CS-25 2.4% requirement
    assert safety.oei_required_gradient_pct == 2.4
    assert safety.oei_climb_gradient_pct >= 2.4
    assert safety.oei_check_passed is True

    # In-flight complete electrical failure case must maintain safe positive climb
    assert safety.elec_failure_climb_gradient_pct >= 1.5
    assert safety.elec_failure_check_passed is True

# 6. Direct Operating Costs & Charging Infrastructure
def test_direct_operating_costs_and_turnaround_charging():
    doc = compute_direct_operating_costs(
        fuel_burned_conv_kg=220.0,
        fuel_burned_hybrid_kg=170.0,
        battery_recharge_kwh=120.0,
        battery_capacity_kwh=150.0,
        flight_duration_hours=0.75,
        seats_shed=0
    )
    assert doc["fuel_saving_usd"] > 0.0
    assert doc["electricity_cost_usd"] > 0.0
    assert doc["battery_amortization_usd"] > 0.0

    # Required turnaround charger power for 120 kWh in 30 minutes at 90% efficiency:
    # 120 / (0.5 * 0.90) = 266.7 kW
    assert pytest.approx(doc["required_charger_power_kw"], rel=1e-2) == 266.7

# 7. Full Phase 2 Mission Simulator Integration
def test_phase2_full_mission_integration():
    route = get_route_by_id("BOM-PNQ")
    sim = MissionSimulator(route, hp_fraction=0.25, battery_wh_per_kg=280.0, physics_mode="phase2")
    res = sim.run_simulation()

    summary = res["summary"]
    assert "takeoff_distance_35ft_conv_m" in summary
    assert "takeoff_distance_35ft_hybrid_m" in summary
    assert "safety_oei_check_passed" in summary
    assert summary["safety_oei_check_passed"] is True
    assert "operating_costs" in summary
    assert summary["operating_costs"]["required_charger_power_kw"] > 0.0
