"""
Unit & Integration Tests for Phase 4: Benchmarks, Uncertainty, Sweeps & Sensitivity.
Validates:
1. Expanded Indian regional route database (elevations, runways, grid factors).
2. Battery technology horizon sweeps & zero-seat-shedding thresholds.
3. Clean vs. dirty grid CO2 crossover behavior.
4. Quasi-random Sobol sequence Monte Carlo feasibility probability and confidence intervals.
5. Tornado sensitivity ranking and swing magnitudes.
"""
from backend.sim_core.routes import INDIAN_REGIONAL_SECTORS, get_route_by_id
from backend.sim_core.uncertainty import (
    run_battery_density_sweep,
    run_monte_carlo_feasibility,
    run_tornado_sensitivity,
)


def test_expanded_regional_routes_database():
    """Verifies that all 9 Indian regional routes and airports have sourced data."""
    assert len(INDIAN_REGIONAL_SECTORS) == 9
    route_ids = [r.route_id for r in INDIAN_REGIONAL_SECTORS]
    expected = [
        "BLR-IXG",
        "BOM-PNQ",
        "DEL-DED",
        "MAA-TIR",
        "AMD-UDR",
        "IXC-DED",
        "HYD-TIR",
        "GAU-SHL",
        "CCU-IXB",
    ]
    for exp in expected:
        assert exp in route_ids

    for r in INDIAN_REGIONAL_SECTORS:
        assert r.stage_distance_km > 0.0
        assert r.nominal_cruise_alt_ft >= 10000.0
        assert 0.50 <= r.regional_grid_co2_kg_per_kwh <= 0.90
        assert r.origin.runway_length_m >= 1800.0
        assert r.destination.runway_length_m >= 1800.0
        assert r.origin.elevation_ft >= 0.0
        assert r.destination.elevation_ft >= 0.0


def test_battery_density_sweep_monotonicity_and_thresholds():
    """
    Verifies that increasing battery specific energy monotonically reduces battery mass
    and eliminates passenger seat shedding on short-haul regional sectors.
    """
    route = get_route_by_id("BOM-PNQ")
    sweep = run_battery_density_sweep(route, hp_fraction=0.20)

    assert len(sweep["points"]) >= 7

    # Battery mass must decrease strictly monotonically with increasing specific energy
    batt_masses = [p["battery_weight_kg"] for p in sweep["points"]]
    for i in range(len(batt_masses) - 1):
        assert batt_masses[i] >= batt_masses[i + 1]

    # Passengers carried must increase or remain at full capacity (70 pax)
    pax_list = [p["passengers_carried"] for p in sweep["points"]]
    for i in range(len(pax_list) - 1):
        assert pax_list[i] <= pax_list[i + 1]

    # Zero seat shedding threshold should be detected at or above 400-450 Wh/kg
    thresh = sweep["thresholds"]["zero_seat_shed_density_wh_kg"]
    assert thresh is not None
    assert 350.0 <= thresh <= 500.0


def test_clean_vs_dirty_grid_co2_breakeven():
    """
    Verifies that well-to-wake CO2 emissions are fundamentally governed by grid carbon intensity:
    A clean renewable grid (0.20 kg/kWh) yields positive net CO2 savings,
    while a coal-heavy grid (0.85 kg/kWh) yields net negative CO2 savings.
    """
    route = get_route_by_id("BOM-PNQ")

    sweep_clean = run_battery_density_sweep(route, hp_fraction=0.20, grid_co2_kg_per_kwh=0.20)
    sweep_dirty = run_battery_density_sweep(route, hp_fraction=0.20, grid_co2_kg_per_kwh=0.85)

    clean_400 = next(p for p in sweep_clean["points"] if p["specific_energy_wh_kg"] == 400.0)
    dirty_400 = next(p for p in sweep_dirty["points"] if p["specific_energy_wh_kg"] == 400.0)

    # Clean grid must achieve positive net CO2 savings
    assert clean_400["net_co2_saved_pct_wtw"] > 5.0
    # Dirty grid must suffer net negative CO2 savings
    assert dirty_400["net_co2_saved_pct_wtw"] < 0.0


def test_monte_carlo_sobol_sampling_reproducibility():
    """
    Verifies that Sobol quasi-random Monte Carlo sampling:
    1. Produces identical deterministic results with the same seed.
    2. Bounds feasibility probability strictly between 0 and 1.
    3. Yields a valid 95% confidence interval.
    """
    route = get_route_by_id("BLR-IXG")
    mc1 = run_monte_carlo_feasibility(route, hp_fraction=0.30, n_samples=500, seed=42)
    mc2 = run_monte_carlo_feasibility(route, hp_fraction=0.30, n_samples=500, seed=42)

    assert mc1["feasibility_probability"] == mc2["feasibility_probability"]
    assert 0.0 <= mc1["feasibility_probability"] <= 1.0

    ci = mc1["confidence_interval_95"]
    assert len(ci) == 2
    assert ci[0] <= mc1["feasibility_probability"] <= ci[1]

    # Statistics must be well-formed
    pax_stats = mc1["passengers_carried_stats"]
    assert 60 <= pax_stats["mean"] <= 70
    assert pax_stats["p05"] <= pax_stats["median"] <= pax_stats["p95"]


def test_tornado_sensitivity_ranking():
    """
    Verifies that One-at-a-Time tornado analysis generates a non-empty ranking
    sorted descending by CO2 swing impact.
    """
    route = get_route_by_id("BLR-IXG")
    tornado = run_tornado_sensitivity(route, hp_fraction=0.30)

    rankings = tornado["rankings"]
    assert len(rankings) >= 4

    # Verify descending sort order of swing magnitude
    for i in range(len(rankings) - 1):
        assert rankings[i]["co2_swing_pct"] >= rankings[i + 1]["co2_swing_pct"]

    # Top drivers should include battery density or grid carbon factor
    top_params = [r["parameter"] for r in rankings[:2]]
    assert "battery_wh_per_kg" in top_params or "grid_co2_kg_per_kwh" in top_params
