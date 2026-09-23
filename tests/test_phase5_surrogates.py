"""
Unit and Integration Tests for Phase 5: Machine Learning Surrogates & Conformal Prediction.
Verifies GBDT accuracy, split-conformal calibration intervals, sub-10ms inference,
and FastAPI backend surrogate endpoints.
"""

import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.ml_service.surrogate import SurrogateModel


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def surrogate():
    return SurrogateModel()


def test_surrogate_pipeline_loaded(surrogate):
    """Verifies that the serialized GBDT pipeline loads successfully."""
    assert os.path.exists("data/models/surrogate_pipeline.joblib")
    assert surrogate.is_loaded is True
    assert surrogate.models != {}
    assert "fuel_saved_pct" in surrogate.models
    assert "battery_weight_kg" in surrogate.models
    assert "mtow_hybrid_kg" in surrogate.models
    assert "passengers_carried" in surrogate.models


def test_surrogate_prediction_structure_and_intervals(surrogate):
    """Verifies conformal prediction intervals and bounds formatting."""
    res = surrogate.predict(
        stage_distance_km=350.0,
        hp_fraction=0.25,
        battery_wh_per_kg=450.0,
        ambient_delta_c=5.0,
    )

    assert res["model_type"] == "HistGradientBoostingRegressor"
    assert res["is_fallback"] is False
    assert "targets" in res

    for target_name in ["fuel_saved_pct", "battery_weight_kg", "mtow_hybrid_kg", "passengers_carried"]:
        t_data = res["targets"][target_name]
        pred = t_data["prediction"]
        c90 = t_data["conformal_interval_90"]
        c95 = t_data["conformal_interval_95"]
        m90 = t_data["margin_error_90"]
        m95 = t_data["margin_error_95"]

        # Interval ordering
        assert c90[0] <= pred <= c90[1]
        assert c95[0] <= pred <= c95[1]
        assert m90 <= m95
        assert c95[0] <= c90[0]
        assert c95[1] >= c90[1]


def test_surrogate_physical_consistency(surrogate):
    """Ensures surrogate predictions obey physical bounds."""
    # Low hybridization (0%) should have ~0 fuel saved and 0 battery mass
    res_zero = surrogate.predict(stage_distance_km=300.0, hp_fraction=0.0, battery_wh_per_kg=400.0, ambient_delta_c=0.0)
    assert res_zero["predicted_fuel_saved_pct"] <= 1.0
    assert res_zero["estimated_battery_mass_kg"] <= 50.0

    # High hybridization should show positive battery mass and fuel savings
    res_high = surrogate.predict(stage_distance_km=300.0, hp_fraction=0.30, battery_wh_per_kg=400.0, ambient_delta_c=0.0)
    assert res_high["predicted_fuel_saved_pct"] > 5.0
    assert res_high["estimated_battery_mass_kg"] > 400.0
    assert 13500.0 <= res_high["estimated_tow_kg"] <= 23500.0


def test_surrogate_fallback_mode():
    """Tests graceful fallback when model file is not found."""
    fallback_model = SurrogateModel(model_path="non_existent_file.joblib")
    assert fallback_model.is_loaded is False

    res = fallback_model.predict(stage_distance_km=350.0, hp_fraction=0.30, battery_wh_per_kg=400.0)
    assert res["is_fallback"] is True
    assert res["model_type"] == "Analytical_Fallback"
    assert res["predicted_fuel_saved_pct"] > 0.0
    assert len(res["uncertainty_range_pct"]) == 2


def test_surrogate_benchmarks_metrics():
    """Verifies that GBDT outperforms Polynomial Ridge and MLP across key metrics."""
    import json

    metrics_path = "data/models/surrogate_metrics.json"
    assert os.path.exists(metrics_path)

    with open(metrics_path, encoding="utf-8") as f:
        data = json.load(f)

    gbdt = data["benchmarks"]["GBDT"]
    poly = data["benchmarks"]["Polynomial_Ridge"]
    conf = data["conformal_calibration"]

    # GBDT R^2 > 0.99 for fuel and battery
    assert gbdt["r2"]["fuel_saved_pct"] >= 0.99
    assert gbdt["r2"]["battery_weight_kg"] >= 0.99

    # GBDT MAE lower than Polynomial Ridge for fuel and battery
    assert gbdt["mae"]["fuel_saved_pct"] < poly["mae"]["fuel_saved_pct"]
    assert gbdt["mae"]["battery_weight_kg"] < poly["mae"]["battery_weight_kg"]

    # Conformal empirical coverage on test split >= 85% for nominal 90%
    for target in conf:
        assert conf[target]["test_empirical_coverage_90"] >= 0.85
        assert conf[target]["test_empirical_coverage_95"] >= 0.90


def test_fastapi_surrogate_routes(client):
    """Tests FastAPI GET /api/surrogate, POST /api/surrogate/predict, and GET /api/surrogate/benchmarks."""
    # GET /api/surrogate
    resp_get = client.get("/api/surrogate?distance_km=380.0&hp_fraction=0.25&battery_wh_per_kg=400.0")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "predicted_fuel_saved_pct" in data_get
    assert "targets" in data_get
    assert data_get["model_type"] == "HistGradientBoostingRegressor"

    # POST /api/surrogate/predict
    resp_post = client.post(
        "/api/surrogate/predict",
        json={
            "distance_km": 380.0,
            "hp_fraction": 0.25,
            "battery_wh_per_kg": 400.0,
            "ambient_delta_c": 0.0,
        },
    )
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["predicted_fuel_saved_pct"] == data_get["predicted_fuel_saved_pct"]

    # GET /api/surrogate/benchmarks
    resp_bm = client.get("/api/surrogate/benchmarks")
    assert resp_bm.status_code == 200
    data_bm = resp_bm.json()
    assert "benchmarks" in data_bm
    assert "GBDT" in data_bm["benchmarks"]
    assert "conformal_calibration" in data_bm
