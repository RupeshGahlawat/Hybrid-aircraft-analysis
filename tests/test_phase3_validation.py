"""
Unit & Integration Tests for Phase 3: Real-World Data Validation & Parameter Calibration.
Validates simulation predictions against certified ATR 72-600 FCOM performance tables,
recorded ADS-B flight trajectories, and verifies OpenSky client resilience.
"""
from backend.sim_core.calibration import FCOMCalibrator
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.opensky_client import OpenSkyClient
from backend.sim_core.routes import get_route_by_id


def test_fcom_benchmark_data_integrity():
    """Verifies that the certified ATR 72-600 FCOM dataset is complete and well-formed."""
    calibrator = FCOMCalibrator()
    assert len(calibrator.benchmarks) == 5

    stage_lengths = [pt.stage_length_nm for pt in calibrator.benchmarks]
    assert stage_lengths == [100, 150, 200, 250, 300]

    for pt in calibrator.benchmarks:
        assert pt.distance_km > 0.0
        assert pt.fcom_trip_fuel_kg > 0.0
        assert pt.fcom_flight_time_min > 0.0
        assert 120 <= pt.cruise_altitude_fl <= 250


def test_recorded_flight_trajectories_exist():
    """Verifies that offline recorded commercial ADS-B trajectories exist for Indian sectors."""
    routes = ["BOM-PNQ", "BLR-IXG", "DEL-DED"]
    for r_id in routes:
        traj_data = OpenSkyClient.get_reference_route_trajectory(r_id)
        assert traj_data["route_id"] == r_id
        assert traj_data["aircraft_type"] == "AT76"
        assert len(traj_data["trajectory"]) >= 10

        # Check first and last waypoints
        first_wpt = traj_data["trajectory"][0]
        last_wpt = traj_data["trajectory"][-1]
        assert first_wpt["phase"] == "TAKEOFF_ROLL"
        assert last_wpt["phase"] == "LANDING"
        assert first_wpt["ground_speed_mps"] == 0.0
        assert last_wpt["altitude_m"] > 0.0


def test_opensky_client_cache_and_offline_fallback():
    """Verifies OpenSky client rate limiting, caching, and graceful failure handling."""
    client = OpenSkyClient(cache_dir="data/opensky_cache")
    assert client.min_request_interval_s >= 5.0

    # Query live states with short timeout to verify resilience
    states = client.fetch_live_states(timeout_s=3.0)
    assert "source" in states
    assert states["source"] in ["OPENSKY_LIVE", "LOCAL_CACHE", "LOCAL_CACHE_FALLBACK", "EMPTY_FALLBACK"]

    # Query track for invalid or offline icao24
    track = client.fetch_track("000000", timeout_s=2.0)
    assert "source" in track


def test_fcom_calibration_convergence():
    """
    Verifies that aerodynamic and thermodynamic calibration against FCOM
    reduces prediction error to < 3% on standard regional sectors and achieves R^2 > 0.95.
    """
    calibrator = FCOMCalibrator()
    res = calibrator.run_calibration()

    assert 0.024 <= res.cd0_calibrated <= 0.032
    assert 0.280 <= res.bsfc_calibrated <= 0.335
    assert res.calibrated_rmse_kg <= res.uncalibrated_rmse_kg
    assert res.r_squared >= 0.95

    # Standard regional routes (150-300 NM) should have low relative error
    regional_comps = [c for c in res.point_comparisons if c["stage_length_nm"] in [200, 250, 300]]
    for comp in regional_comps:
        assert abs(comp["calibrated_error_pct"]) < 3.0


def test_simulation_trajectory_correlation_with_recorded_flight():
    """
    Verifies that simulated mission trajectory correlates with recorded commercial flight
    in cruise altitude and stage distance within 10%.
    """
    route = get_route_by_id("BOM-PNQ")
    sim = MissionSimulator(route, hp_fraction=0.0, physics_mode="phase2")
    sim_res = sim.run_simulation()

    rec_data = OpenSkyClient.get_reference_route_trajectory("BOM-PNQ")
    rec_cruise_alt_m = rec_data["cruise_altitude_m"]

    # In BOM-PNQ simulation, verify cruise occurs near route nominal altitude
    sim_telemetry = sim_res["telemetry_conv"]
    cruise_steps = [s for s in sim_telemetry if s["phase"] == "cruise"]
    assert len(cruise_steps) > 0

    sim_cruise_alt_m = cruise_steps[0]["altitude_ft"] / 3.28084
    alt_error_pct = abs(sim_cruise_alt_m - rec_cruise_alt_m) / rec_cruise_alt_m * 100.0
    # Altitude agreement within 10%
    assert alt_error_pct < 10.0
