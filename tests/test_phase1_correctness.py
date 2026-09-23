"""
Phase 1 Correctness Unit & Regression Tests:
1. Engine: PW127M ratings (2,475 SHP normal / 2,750 SHP APR).
2. Weight: MTOW, MZFW, MLW multi-constraint checking & mass-scaled reserve fuel.
3. Airport: Verified AIP elevations (Dehradun 1,857 ft, Udaipur 1,683 ft) & return legs.
4. Schedule: Per-phase hybrid schedule and energy accounting by phase.
5. Reconciliation: CO2 emission intensity per kWh shaft (kerosene vs grid electricity).
"""

import pytest

from backend.sim_core.aircraft_specs import get_aircraft_specs
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.propulsion import HybridPhaseSchedule
from backend.sim_core.routes import AIRPORTS, get_route_by_id
from backend.sim_core.weight_loop import compute_mass_scaled_reserve_fuel, size_aircraft_mass


# 1. Engine Specs
def test_pw127m_engine_specifications():
    specs_basic = get_aircraft_specs("basic")
    assert specs_basic.engine_model == "PW127M"
    # Normal takeoff power is 2,475 SHP (~1,845.6 kW)
    assert specs_basic.takeoff_power_shp_per_engine == 2475.0
    assert pytest.approx(specs_basic.takeoff_power_kw_per_engine, rel=1e-2) == 1845.6
    # Automatic Power Reserve (APR / OEI) is 2,750 SHP (~2,050.7 kW)
    assert specs_basic.apr_power_shp_per_engine == 2750.0
    assert pytest.approx(specs_basic.apr_power_kw_per_engine, rel=1e-2) == 2050.7


# 2. Structural Weight Limits & Tri-Boundary Checks
def test_weight_limits_basic_vs_option():
    basic = get_aircraft_specs("basic")
    option = get_aircraft_specs("option")

    assert basic.mtow_kg == 22800.0
    assert basic.mzfw_kg == 20800.0
    assert basic.mlw_kg == 22350.0

    assert option.mtow_kg == 23000.0
    assert option.mzfw_kg == 21000.0
    assert option.mlw_kg == 22350.0


def test_tri_boundary_mass_convergence():
    # Option weight package (MTOW 23,000 kg, MZFW 21,000 kg) carries all 70 passengers
    res_opt = size_aircraft_mass(
        hp_fraction=0.20, battery_wh_per_kg=400.0, stage_distance_km=200.0, nominal_pax=70, weight_option="option"
    )
    assert res_opt.mtow_calculated_kg <= res_opt.mtow_limit_kg
    assert res_opt.mzfw_calculated_kg <= res_opt.mzfw_limit_kg
    assert res_opt.mlw_calculated_kg <= res_opt.mlw_limit_kg
    assert res_opt.passengers_carried == 70
    assert res_opt.payload_penalty_pax == 0
    assert res_opt.iterations_to_converge < 30

    # Basic weight package (MZFW 20,800 kg) sheds 1 seat due to battery EOL sizing margin
    res_basic = size_aircraft_mass(
        hp_fraction=0.20, battery_wh_per_kg=400.0, stage_distance_km=200.0, nominal_pax=70, weight_option="basic"
    )
    assert res_basic.mzfw_calculated_kg <= res_basic.mzfw_limit_kg
    assert res_basic.passengers_carried in [69, 70]
    assert res_basic.iterations_to_converge < 30


def test_mass_scaled_reserve_fuel():
    # Light aircraft reserve vs heavy aircraft reserve
    res_light = compute_mass_scaled_reserve_fuel(18000.0)
    res_heavy = compute_mass_scaled_reserve_fuel(22800.0)
    assert res_heavy > res_light
    assert 500.0 < res_light < 600.0
    assert 540.0 < res_heavy < 620.0


def test_seat_shedding_inside_loop_on_excess_battery():
    # Severe battery burden (e.g. heavy low-density battery 180 Wh/kg with 45% boost)
    res = size_aircraft_mass(hp_fraction=0.45, battery_wh_per_kg=180.0, stage_distance_km=300.0, nominal_pax=70)
    assert res.payload_penalty_pax > 0
    assert res.passengers_carried < 70
    # Must still satisfy all three limits after shedding
    assert res.mtow_calculated_kg <= res.mtow_limit_kg + 0.1
    assert res.mzfw_calculated_kg <= res.mzfw_limit_kg + 0.1
    assert res.mlw_calculated_kg <= res.mlw_limit_kg + 0.1


# 3. Airport Data & Return Leg
def test_airport_elevations_sourced_aip():
    assert AIRPORTS["VIDN"].elevation_ft == 1857.0  # Dehradun AIP
    assert AIRPORTS["VAUD"].elevation_ft == 1683.0  # Udaipur AIP
    assert AIRPORTS["VAPO"].elevation_ft == 1942.0  # Pune AIP
    assert AIRPORTS["VABB"].elevation_ft == 39.0  # Mumbai AIP


def test_return_leg_swapping():
    route_outbound = get_route_by_id("DEL-DED", return_leg=False)
    route_return = get_route_by_id("DEL-DED", return_leg=True)

    assert route_outbound.origin.iata == "DEL"
    assert route_outbound.destination.iata == "DED"

    assert route_return.origin.iata == "DED"
    assert route_return.destination.iata == "DEL"
    assert route_return.origin.elevation_ft == 1857.0
    assert route_return.is_return_leg is True


# 4. Hybrid Phase Schedule & Energy by Phase
def test_per_phase_schedule_energy():
    sched = HybridPhaseSchedule(takeoff=0.35, climb=0.25, cruise=0.0, descent=0.0)
    route = get_route_by_id("BOM-PNQ")
    sim = MissionSimulator(route, hp_fraction=sched, battery_wh_per_kg=400.0)
    res = sim.run_simulation()

    energy = res["summary"]["energy_kwh_by_phase"]
    assert energy["takeoff"] > 0.0
    assert energy["climb"] > 0.0
    assert energy["cruise"] == 0.0
    assert energy["descent"] == 0.0
    assert res["summary"]["battery_energy_consumed_kwh"] == pytest.approx(energy["takeoff"] + energy["climb"], rel=1e-2)


# 5. CO2 Reconciliation Test (Phase 1 Item 7)
def test_co2_reconciliation_math():
    """
    Reconciliation:
    - Kerosene: BSFC ~0.295 kg/kWh shaft * 3.16 kg CO2/kg fuel = ~0.9322 kg CO2 per kWh shaft.
    - Grid electricity: at 0.74 kg/kWh grid intensity,
      with ~0.8085 to 0.875 chain efficiency, electricity is ~0.846 to 0.915 kg CO2 per kWh shaft.
    """
    bsfc = 0.295  # kg/kWh
    ef_kerosene = 3.16  # kg CO2/kg Jet-A1
    co2_per_kwh_shaft_kerosene = bsfc * ef_kerosene
    assert pytest.approx(co2_per_kwh_shaft_kerosene, rel=1e-2) == 0.9322

    # Plug-to-shaft chain efficiency:
    # eta_charger = 0.90, eta_batt = 0.95, eta_inv = 0.985, eta_motor = 0.96
    eta_chain = 0.90 * 0.95 * 0.985 * 0.96
    assert pytest.approx(eta_chain, rel=1e-2) == 0.8085

    grid_factor = 0.74  # kg CO2/kWh (Western Grid BOM-PNQ)
    co2_per_kwh_shaft_elec = grid_factor / eta_chain
    assert pytest.approx(co2_per_kwh_shaft_elec, rel=1e-2) == 0.9153

    # If using nominal 0.875 terminal-to-shaft chain efficiency:
    co2_at_0875 = grid_factor / 0.875
    assert pytest.approx(co2_at_0875, rel=1e-2) == 0.8457

    # Crucial scientific takeaway:
    # Electric CO2 (0.85 - 0.92 kg/kWh) is only 2% to 9% lower than Kerosene CO2 (0.93 kg/kWh).
    # Therefore, carrying a 670+ kg battery pack increases total flight energy, which causes
    # NET CO2 to be negative (i.e. net emissions increase) on a 0.74 kg/kWh grid!
    assert co2_per_kwh_shaft_elec < co2_per_kwh_shaft_kerosene
    margin_pct = (co2_per_kwh_shaft_kerosene - co2_per_kwh_shaft_elec) / co2_per_kwh_shaft_kerosene * 100.0
    assert margin_pct < 10.0  # less than 10% shaft advantage before factoring battery weight!
