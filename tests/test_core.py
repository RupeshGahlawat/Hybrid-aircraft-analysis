"""
Unit and Integration Tests for AeroHybrid Physics and Simulation Core.
"""

import pytest

from backend.ml_service.analyst import ANALYST
from backend.ml_service.surrogate import SURROGATE
from backend.sim_core.aircraft_specs import ATR72_BASELINE
from backend.sim_core.atmosphere import get_atmosphere
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.propulsion import HybridPowertrain
from backend.sim_core.routes import UDAN_ROUTES, get_route_by_id
from backend.sim_core.weight_loop import size_aircraft_mass


# 1. Atmospheric Model Tests
def test_atmosphere_sea_level():
    atm = get_atmosphere(0.0)
    assert pytest.approx(atm["density_kg_m3"], rel=1e-2) == 1.225
    assert pytest.approx(atm["temperature_c"], abs=0.5) == 15.0
    assert pytest.approx(atm["pressure_pa"], rel=1e-2) == 101325.0


def test_atmosphere_hot_day_lapse():
    atm_std = get_atmosphere(200.0, delta_t_c=0.0)
    atm_hot = get_atmosphere(200.0, delta_t_c=25.0)
    # Density must decrease on hot days
    assert atm_hot["density_kg_m3"] < atm_std["density_kg_m3"]
    assert atm_hot["temperature_c"] > atm_std["temperature_c"]


# 2. Aircraft Baseline Constants
def test_atr72_baseline_constants():
    assert ATR72_BASELINE.mtow_basic_kg == 22800.0
    assert ATR72_BASELINE.mtow_option_kg == 23000.0
    assert ATR72_BASELINE.aspect_ratio == 12.0
    assert ATR72_BASELINE.wing_area_m2 == 61.0
    assert ATR72_BASELINE.num_engines == 2
    assert ATR72_BASELINE.engine_model == "PW127M"


# 3. Hybrid Powertrain Sizing
def test_powertrain_zero_hybrid():
    pt = HybridPowertrain(hp_fraction=0.0)
    weights = pt.weights
    assert weights["motors_kg"] == 0.0
    assert weights["inverters_kg"] == 0.0


def test_powertrain_active_hybrid():
    pt = HybridPowertrain(hp_fraction=0.30)
    weights = pt.weights
    assert weights["motors_kg"] > 0.0
    assert weights["inverters_kg"] > 0.0
    assert weights["tms_kg"] > 0.0


# 4. Weight Loop & Reserve Compliance
def test_weight_loop_far_reserves():
    res = size_aircraft_mass(hp_fraction=0.30, battery_wh_per_kg=400.0, stage_distance_km=462.0)
    # Mass-scaled reserve fuel per FAR Part 121 / DGCA rules (~550 kg nominal)
    assert 520.0 < res.reserve_fuel_kg < 580.0
    assert res.total_fuel_kg == pytest.approx(res.mission_fuel_kg + res.reserve_fuel_kg + res.taxi_fuel_kg, rel=1e-3)
    assert res.mtow_calculated_kg <= res.mtow_limit_kg


def test_weight_loop_excessive_battery():
    # At very low battery density and high boost, weight must cause seat shedding
    res = size_aircraft_mass(hp_fraction=0.50, battery_wh_per_kg=150.0, stage_distance_km=600.0)
    assert res.payload_penalty_pax > 0


# 5. Route Database Integrity
def test_routes_database():
    assert len(UDAN_ROUTES) >= 5
    blr_ixg = get_route_by_id("BLR-IXG")
    assert blr_ixg.stage_distance_km == 462.0
    assert blr_ixg.origin.elevation_ft == 3000.0


# 6. Mission Simulation Execution
def test_mission_simulation_run():
    route = get_route_by_id("BOM-PNQ")  # 122 km short-haul
    sim = MissionSimulator(route, hp_fraction=0.30, battery_wh_per_kg=400.0)
    res = sim.run_simulation()

    assert "summary" in res
    assert "telemetry_hybrid" in res
    assert "telemetry_conv" in res

    summary = res["summary"]
    # BOM-PNQ short haul must achieve > 15% fuel savings
    assert summary["fuel_saved_pct"] > 15.0
    assert summary["is_feasible"] is True


# 7. ML Surrogate Tests
def test_surrogate_prediction():
    pred = SURROGATE.predict(stage_distance_km=462.0, hp_fraction=0.30, battery_wh_per_kg=400.0)
    assert "predicted_fuel_saved_pct" in pred
    assert "uncertainty_range_pct" in pred
    assert pred["inference_time_ms"] < 50.0


# 8. AI Analyst Grounding Verification
def test_analyst_grounding_audit():
    route = get_route_by_id("BLR-IXG")
    sim = MissionSimulator(route, hp_fraction=0.30, battery_wh_per_kg=400.0)
    res = sim.run_simulation()
    analysis = ANALYST.analyze_simulation(res)

    assert "PASSED" in analysis["model_metadata"]["verification_status"]
    assert "Numerical Consistency Check" in analysis["model_metadata"]["verification_status"]
    assert len(analysis["summary_bullet_points"]) >= 3
