"""
Fast Machine Learning Surrogate and Feasibility Boundary Predictor.
Trained on synthetic physics sweeps (Sobol sequence sampling),
providing microsecond/millisecond predictions of fuel burn delta, payload penalties, and exact conformal intervals.
"""

import os
import time
from typing import Any

import joblib
import numpy as np


class SurrogateModel:
    """
    Trained surrogate model with HistGradientBoostingRegressor pipelines and split-conformal prediction.
    Features: [stage_distance_km, hp_fraction, battery_wh_per_kg, ambient_delta_c]
    Outputs: fuel_saved_pct, net_co2_saved_pct_wtw, battery_weight_kg, mtow_hybrid_kg, passengers_carried.
    """

    def __init__(self, model_path: str = "data/models/surrogate_pipeline.joblib"):
        self.model_path = model_path
        self.is_loaded = False
        self.models: dict[str, Any] = {}
        self.conformal_quantiles: dict[str, dict[str, float]] = {}
        self.target_names: list[str] = []
        self.feature_names: list[str] = []
        self._load_model()

    def _load_model(self) -> None:
        if os.path.exists(self.model_path):
            try:
                bundle = joblib.load(self.model_path)
                self.models = bundle.get("models", {})
                self.conformal_quantiles = bundle.get("conformal_quantiles", {})
                self.target_names = bundle.get("target_names", [])
                self.feature_names = bundle.get("feature_names", [])
                self.is_loaded = bool(self.models)
                if self.is_loaded:
                    # Warm-up scikit-learn threadpool and Cython tree traversal
                    dummy_X = np.array([[300.0, 0.25, 400.0, 0.0]])
                    for m in self.models.values():
                        _ = m.predict(dummy_X)
            except Exception:
                self.is_loaded = False

    def predict(
        self,
        stage_distance_km: float,
        hp_fraction: float,
        battery_wh_per_kg: float,
        ambient_delta_c: float = 0.0,
    ) -> dict[str, Any]:
        """
        Instantaneous prediction with 90% and 95% distribution-free split-conformal confidence intervals.
        """
        t0 = time.perf_counter()

        dist = float(np.clip(stage_distance_km, 80.0, 1000.0))
        hp = float(np.clip(hp_fraction, 0.0, 0.50))
        wh = float(np.clip(battery_wh_per_kg, 200.0, 700.0))
        dt = float(np.clip(ambient_delta_c, -10.0, 35.0))

        if self.is_loaded:
            X = np.array([[dist, hp, wh, dt]])
            preds: dict[str, float] = {}
            target_details: dict[str, dict[str, Any]] = {}

            for target in self.target_names:
                model = self.models[target]
                pred_val = float(model.predict(X)[0])
                preds[target] = pred_val

                cq = self.conformal_quantiles.get(target, {"q_90": 0.5, "q_95": 1.0})
                q_90 = cq.get("q_90", 0.5)
                q_95 = cq.get("q_95", 1.0)

                target_details[target] = {
                    "prediction": round(pred_val, 2),
                    "conformal_interval_90": [round(pred_val - q_90, 2), round(pred_val + q_90, 2)],
                    "conformal_interval_95": [round(pred_val - q_95, 2), round(pred_val + q_95, 2)],
                    "margin_error_90": q_90,
                    "margin_error_95": q_95,
                }

            fuel_saved_pct = max(0.0, preds.get("fuel_saved_pct", 0.0))
            co2_saved_pct = preds.get("net_co2_saved_pct_wtw", 0.0)
            batt_mass_kg = max(0.0, preds.get("battery_weight_kg", 0.0))
            mtow_hybrid_kg = max(13500.0, preds.get("mtow_hybrid_kg", 23000.0))
            passengers_carried = float(np.clip(preds.get("passengers_carried", 70.0), 0.0, 70.0))

            # Base fuel consumption estimate for kg conversion
            base_fuel = 140.0 + 1.15 * dist + 0.00035 * (dist**1.8)
            fuel_saved_kg = max(0.0, (fuel_saved_pct / 100.0) * base_fuel)

            # Feasibility definition: MTOW constraint <= 23000 kg and passengers >= 70
            is_feasible = (mtow_hybrid_kg <= 23000.0) and (passengers_carried >= 69.5)
            feasibility_prob = 1.0 / (1.0 + np.exp((mtow_hybrid_kg - 23000.0) / 250.0))
            if passengers_carried < 69.5:
                feasibility_prob = min(feasibility_prob, 0.40)

            fuel_q90 = self.conformal_quantiles.get("fuel_saved_pct", {}).get("q_90", 0.5)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "model_type": "HistGradientBoostingRegressor",
                "is_fallback": False,
                "targets": target_details,
                "predicted_fuel_saved_pct": round(fuel_saved_pct, 2),
                "predicted_fuel_saved_kg": round(fuel_saved_kg, 1),
                "predicted_co2_saved_pct_wtw": round(co2_saved_pct, 2),
                "uncertainty_range_pct": [
                    round(max(0.0, fuel_saved_pct - fuel_q90), 2),
                    round(fuel_saved_pct + fuel_q90, 2),
                ],
                "feasibility_probability": round(float(feasibility_prob), 3),
                "is_feasible": bool(is_feasible),
                "estimated_battery_mass_kg": round(batt_mass_kg, 1),
                "estimated_tow_kg": round(mtow_hybrid_kg, 1),
                "passengers_carried": round(passengers_carried, 1),
                "inference_time_ms": round(latency_ms, 3),
            }

        # Analytical fallback if model file is not available
        base_fuel = 140.0 + 1.15 * dist + 0.00035 * (dist**1.8)
        batt_kwh = (hp * 4100.0 * (10.0 / 60.0)) / (0.96 * 0.985 * 0.80)
        batt_mass_kg = (batt_kwh * 1000.0) / wh
        mass_penalty_factor = 1.0 + (batt_mass_kg / 1000.0) * 0.034
        elec_shaft_kwh = batt_kwh * 0.80 * 0.96 * 0.985
        fuel_displaced_raw_kg = elec_shaft_kwh * 0.285
        fuel_hybrid_predicted = (base_fuel - fuel_displaced_raw_kg) * mass_penalty_factor
        fuel_saved_kg = max(0.0, base_fuel - fuel_hybrid_predicted)
        fuel_saved_pct = (fuel_saved_kg / base_fuel) * 100.0 if base_fuel > 0 else 0.0
        total_tow = 13500.0 + batt_mass_kg + (base_fuel + 550.0) + (70 * 95.0)
        is_feasible = total_tow <= 23000.0
        feasibility_prob = 1.0 / (1.0 + np.exp((total_tow - 23000.0) / 300.0))
        uncertainty_band_pct = 0.85 + 0.15 * (hp / 0.3) + 0.10 * (abs(dt) / 20.0)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "model_type": "Analytical_Fallback",
            "is_fallback": True,
            "targets": {},
            "predicted_fuel_saved_pct": round(float(fuel_saved_pct), 2),
            "predicted_fuel_saved_kg": round(float(fuel_saved_kg), 1),
            "predicted_co2_saved_pct_wtw": round(float(fuel_saved_pct * 0.7), 2),
            "uncertainty_range_pct": [
                round(float(max(0.0, fuel_saved_pct - uncertainty_band_pct)), 2),
                round(float(fuel_saved_pct + uncertainty_band_pct), 2),
            ],
            "feasibility_probability": round(float(feasibility_prob), 3),
            "is_feasible": bool(is_feasible),
            "estimated_battery_mass_kg": round(float(batt_mass_kg), 1),
            "estimated_tow_kg": round(float(total_tow), 1),
            "passengers_carried": 70.0,
            "inference_time_ms": round(latency_ms, 3),
        }


SURROGATE = SurrogateModel()

