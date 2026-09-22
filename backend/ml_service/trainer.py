"""
Surrogate Model Training, Comparative Benchmark & Conformal Prediction Engine.
Generates space-filling Sobol training data, trains and compares:
1. Gradient Boosted Decision Trees (GBDT via HistGradientBoostingRegressor)
2. Multi-Layer Perceptron (MLPRegressor)
3. Polynomial Ridge Regression Baseline
Computes split-conformal calibration quantiles (90% and 95%) with distribution-free coverage guarantees.
"""
import json
import os
import time
from typing import Any

import joblib
import numpy as np
from scipy.stats import qmc
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.routes import Airport, Route

TARGET_NAMES = [
    "fuel_saved_pct",
    "net_co2_saved_pct_wtw",
    "battery_weight_kg",
    "mtow_hybrid_kg",
    "passengers_carried",
]


def generate_sobol_dataset(n_samples: int = 1500, seed: int = 42) -> dict[str, np.ndarray]:
    """
    Generates a space-filling dataset across the operational flight envelope using Sobol sequences.
    """
    sampler = qmc.Sobol(d=4, seed=seed)
    m_power = int(np.ceil(np.log2(n_samples)))
    raw = sampler.random_base2(m=m_power)[:n_samples]

    # Domain bounds
    distances = 80.0 + raw[:, 0] * (600.0 - 80.0)
    hps = 0.0 + raw[:, 1] * 0.45
    whs = 250.0 + raw[:, 2] * (600.0 - 250.0)
    dts = -10.0 + raw[:, 3] * 35.0  # -10°C to +25°C

    X = np.column_stack([distances, hps, whs, dts])
    Y_dict: dict[str, list[float]] = {name: [] for name in TARGET_NAMES}

    origin_apt = Airport("VZZZ", "ZZZ", "Origin", "CityA", 100.0, 3000.0, 35.0)
    dest_apt = Airport("VZZY", "ZZY", "Dest", "CityB", 100.0, 3000.0, 35.0)

    for i in range(n_samples):
        dist = float(distances[i])
        hp = float(hps[i])
        wh = float(whs[i])
        dt = float(dts[i])

        r = Route(
            route_id=f"SYNTH-{i}",
            name="Synthetic Route",
            origin=origin_apt,
            destination=dest_apt,
            stage_distance_km=dist,
            nominal_cruise_alt_ft=18000.0,
            description="Synthetic Sobol training route",
            regional_grid_co2_kg_per_kwh=0.74,
        )

        sim = MissionSimulator(r, hp_fraction=hp, battery_wh_per_kg=wh, ambient_delta_c=dt, physics_mode="phase2")
        res = sim.run_simulation()["summary"]

        Y_dict["fuel_saved_pct"].append(float(res["fuel_saved_pct"]))
        Y_dict["net_co2_saved_pct_wtw"].append(float(res["net_co2_saved_pct_wtw"]))
        Y_dict["battery_weight_kg"].append(float(res["battery_weight_kg"]))
        Y_dict["mtow_hybrid_kg"].append(float(res["mtow_hybrid_kg"]))
        Y_dict["passengers_carried"].append(float(res["passengers_carried"]))

    Y = np.column_stack([np.array(Y_dict[name]) for name in TARGET_NAMES])
    return {"X": X, "Y": Y}


def train_and_evaluate_surrogates(
    n_samples: int = 1200,
    seed: int = 42,
    output_dir: str = "data/models"
) -> dict[str, Any]:
    """
    Trains GBDT, MLP, and Polynomial baselines; computes split-conformal prediction intervals;
    and saves the production model pipeline.
    """
    os.makedirs(output_dir, exist_ok=True)
    data = generate_sobol_dataset(n_samples=n_samples, seed=seed)
    X, Y = data["X"], data["Y"]

    # 70% Train, 15% Conformal Calibration, 15% Test
    n_total = len(X)
    n_train = int(n_total * 0.70)
    n_cal = int(n_total * 0.15)

    X_train, Y_train = X[:n_train], Y[:n_train]
    X_cal, Y_cal = X[n_train:n_train + n_cal], Y[n_train:n_train + n_cal]
    X_test, Y_test = X[n_train + n_cal:], Y[n_train + n_cal:]

    model_benchmarks: dict[str, dict[str, Any]] = {
        "GBDT": {"mae": {}, "rmse": {}, "r2": {}, "inference_time_us": 0.0},
        "MLP": {"mae": {}, "rmse": {}, "r2": {}, "inference_time_us": 0.0},
        "Polynomial_Ridge": {"mae": {}, "rmse": {}, "r2": {}, "inference_time_us": 0.0},
    }

    gbdt_models = {}
    mlp_models = {}
    poly_models = {}
    conformal_quantiles = {}

    for idx, target_name in enumerate(TARGET_NAMES):
        y_tr = Y_train[:, idx]
        y_c = Y_cal[:, idx]
        y_te = Y_test[:, idx]

        # 1. GBDT (HistGradientBoostingRegressor)
        gbdt = HistGradientBoostingRegressor(max_iter=150, max_leaf_nodes=31, random_state=seed)
        gbdt.fit(X_train, y_tr)
        gbdt_models[target_name] = gbdt

        # 2. MLP (MLPRegressor)
        mlp = Pipeline([
            ("scaler", StandardScaler()),
            ("nn", MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=250, early_stopping=True, random_state=seed)),
        ])
        mlp.fit(X_train, y_tr)
        mlp_models[target_name] = mlp

        # 3. Polynomial Ridge
        poly = Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ])
        poly.fit(X_train, y_tr)
        poly_models[target_name] = poly

        # Evaluate on Test Set
        pred_gbdt = gbdt.predict(X_test)
        pred_mlp = mlp.predict(X_test)
        pred_poly = poly.predict(X_test)

        model_benchmarks["GBDT"]["mae"][target_name] = round(float(mean_absolute_error(y_te, pred_gbdt)), 3)
        model_benchmarks["GBDT"]["rmse"][target_name] = round(float(np.sqrt(mean_squared_error(y_te, pred_gbdt))), 3)
        model_benchmarks["GBDT"]["r2"][target_name] = round(float(r2_score(y_te, pred_gbdt)), 4)

        model_benchmarks["MLP"]["mae"][target_name] = round(float(mean_absolute_error(y_te, pred_mlp)), 3)
        model_benchmarks["MLP"]["rmse"][target_name] = round(float(np.sqrt(mean_squared_error(y_te, pred_mlp))), 3)
        model_benchmarks["MLP"]["r2"][target_name] = round(float(r2_score(y_te, pred_mlp)), 4)

        model_benchmarks["Polynomial_Ridge"]["mae"][target_name] = round(float(mean_absolute_error(y_te, pred_poly)), 3)
        model_benchmarks["Polynomial_Ridge"]["rmse"][target_name] = round(float(np.sqrt(mean_squared_error(y_te, pred_poly))), 3)
        model_benchmarks["Polynomial_Ridge"]["r2"][target_name] = round(float(r2_score(y_te, pred_poly)), 4)

        # Conformal Calibration on held-out Calibration Split (Split-Conformal)
        pred_cal = gbdt.predict(X_cal)
        residuals_cal = np.abs(y_c - pred_cal)
        n_c = len(residuals_cal)

        # 90% quantile (alpha = 0.10) and 95% quantile (alpha = 0.05)
        # Using exact finite-sample adjustment: ceil((n+1)*(1-alpha)) / n
        k_90 = int(np.ceil((n_c + 1) * 0.90))
        q_90 = float(np.sort(residuals_cal)[min(k_90 - 1, n_c - 1)])

        k_95 = int(np.ceil((n_c + 1) * 0.95))
        q_95 = float(np.sort(residuals_cal)[min(k_95 - 1, n_c - 1)])

        # Empirical coverage on test set
        cov_90 = float(np.mean(np.abs(y_te - pred_gbdt) <= q_90))
        cov_95 = float(np.mean(np.abs(y_te - pred_gbdt) <= q_95))

        conformal_quantiles[target_name] = {
            "q_90": round(q_90, 3),
            "q_95": round(q_95, 3),
            "test_empirical_coverage_90": round(cov_90, 4),
            "test_empirical_coverage_95": round(cov_95, 4),
        }

    # Measure latency on single-point inference
    x_single = X_test[:1]
    t0 = time.perf_counter()
    for _ in range(500):
        for name in TARGET_NAMES:
            _ = gbdt_models[name].predict(x_single)
    gbdt_lat_us = ((time.perf_counter() - t0) / 500.0) * 1e6
    model_benchmarks["GBDT"]["inference_time_us"] = round(gbdt_lat_us, 1)

    t0 = time.perf_counter()
    for _ in range(500):
        for name in TARGET_NAMES:
            _ = mlp_models[name].predict(x_single)
    mlp_lat_us = ((time.perf_counter() - t0) / 500.0) * 1e6
    model_benchmarks["MLP"]["inference_time_us"] = round(mlp_lat_us, 1)

    t0 = time.perf_counter()
    for _ in range(500):
        for name in TARGET_NAMES:
            _ = poly_models[name].predict(x_single)
    poly_lat_us = ((time.perf_counter() - t0) / 500.0) * 1e6
    model_benchmarks["Polynomial_Ridge"]["inference_time_us"] = round(poly_lat_us, 1)

    # Serialize trained GBDT production pipeline and conformal intervals
    bundle = {
        "models": gbdt_models,
        "conformal_quantiles": conformal_quantiles,
        "target_names": TARGET_NAMES,
        "feature_names": ["stage_distance_km", "hp_fraction", "battery_wh_per_kg", "ambient_delta_c"],
    }
    model_path = os.path.join(output_dir, "surrogate_pipeline.joblib")
    joblib.dump(bundle, model_path)

    metrics_path = os.path.join(output_dir, "surrogate_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump({
            "benchmarks": model_benchmarks,
            "conformal_calibration": conformal_quantiles,
            "sample_sizes": {"total": n_total, "train": n_train, "cal": n_cal, "test": len(X_test)},
        }, f, indent=2)

    return {
        "status": "SUCCESS",
        "model_path": model_path,
        "benchmarks": model_benchmarks,
        "conformal": conformal_quantiles,
    }
