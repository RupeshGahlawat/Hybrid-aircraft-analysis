"""
Aerodynamic & Thermodynamic Calibration Engine.
Calibrates zero-lift parasite drag coefficient (Cd0) and cruise BSFC against
official ATR 72-600 Flight Crew Operating Manual (FCOM) trip fuel performance tables.
"""
import json
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import minimize

from backend.sim_core.aircraft_specs import AircraftBaseline
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.routes import Airport, Route


@dataclass
class CalibrationBenchmarkPoint:
    stage_length_nm: float
    distance_km: float
    cruise_altitude_fl: int
    fcom_trip_fuel_kg: float
    fcom_flight_time_min: float


@dataclass
class CalibrationResult:
    cd0_initial: float
    cd0_calibrated: float
    bsfc_initial: float
    bsfc_calibrated: float
    uncalibrated_rmse_kg: float
    calibrated_rmse_kg: float
    uncalibrated_max_error_pct: float
    calibrated_max_error_pct: float
    r_squared: float
    point_comparisons: list[dict[str, Any]]


class FCOMCalibrator:
    """
    Calibrates baseline conventional aircraft parameters against certified FCOM trip fuel benchmarks.
    """

    def __init__(self, fcom_data_path: str = "data/validation/atr72_fcom_data.json"):
        if not os.path.isabs(fcom_data_path):
            # Resolve relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            fcom_data_path = os.path.join(base_dir, fcom_data_path)

        with open(fcom_data_path, encoding="utf-8") as f:
            self.data = json.load(f)

        self.benchmarks: list[CalibrationBenchmarkPoint] = [
            CalibrationBenchmarkPoint(
                stage_length_nm=pt["stage_length_nm"],
                distance_km=pt["distance_km"],
                cruise_altitude_fl=pt["cruise_altitude_fl"],
                fcom_trip_fuel_kg=pt["fcom_trip_fuel_kg"],
                fcom_flight_time_min=pt["fcom_flight_time_min"],
            )
            for pt in self.data["mission_benchmarks"]
        ]

    def _simulate_point(
        self,
        pt: CalibrationBenchmarkPoint,
        cd0: float,
        bsfc: float
    ) -> float:
        """
        Simulates trip fuel for a single FCOM benchmark point with custom Cd0 and BSFC.
        """
        origin_apt = Airport(
            icao="ZZZZ",
            iata="ZZZ",
            name="Validation Origin",
            city="Origin City",
            elevation_ft=0.0,
            runway_length_m=3000.0,
            avg_summer_oat_c=15.0
        )
        dest_apt = Airport(
            icao="ZZZY",
            iata="ZZY",
            name="Validation Dest",
            city="Dest City",
            elevation_ft=0.0,
            runway_length_m=3000.0,
            avg_summer_oat_c=15.0
        )
        route = Route(
            route_id=f"FCOM-{int(pt.stage_length_nm)}NM",
            name=f"FCOM {int(pt.stage_length_nm)} NM Benchmark",
            origin=origin_apt,
            destination=dest_apt,
            stage_distance_km=pt.distance_km,
            nominal_cruise_alt_ft=float(pt.cruise_altitude_fl * 100),
            description="FCOM Validation Sector",
            regional_grid_co2_kg_per_kwh=0.74
        )

        custom_specs = AircraftBaseline(
            cd0_clean=cd0,
            bsfc_cruise_kg_per_kwh=bsfc
        )

        sim = MissionSimulator(
            route=route,
            hp_fraction=0.0, # Pure conventional baseline
            specs=custom_specs,
            physics_mode="phase2"
        )
        res = sim.run_simulation()
        # conventional_fuel_kg is flight trip fuel (taxi fuel is tracked separately in block_fuel_conv_kg)
        trip_fuel_kg = res["summary"]["conventional_fuel_kg"]
        return float(trip_fuel_kg)

    def run_calibration(
        self,
        initial_cd0: float = 0.0260,
        initial_bsfc: float = 0.295
    ) -> CalibrationResult:
        """
        Executes Nelder-Mead / L-BFGS-B parameter calibration against FCOM trip fuel benchmarks.
        """
        fcom_targets = np.array([pt.fcom_trip_fuel_kg for pt in self.benchmarks])

        # Initial baseline predictions
        initial_preds = np.array([
            self._simulate_point(pt, initial_cd0, initial_bsfc)
            for pt in self.benchmarks
        ])
        uncal_residuals = initial_preds - fcom_targets
        uncal_rmse = float(np.sqrt(np.mean(uncal_residuals ** 2)))
        uncal_max_err_pct = float(np.max(np.abs(uncal_residuals / fcom_targets) * 100.0))

        def loss_function(params: list[float]) -> float:
            c_d0 = params[0] / 1000.0
            b_sfc = params[1] / 1000.0
            # Bound penalty
            if not (0.020 <= c_d0 <= 0.035 and 0.260 <= b_sfc <= 0.330):
                return 1e8
            preds = [self._simulate_point(pt, c_d0, b_sfc) for pt in self.benchmarks]
            resids = np.array(preds) - fcom_targets
            # Weighted loss prioritizing standard regional sectors (150-250 NM)
            weights = np.array([1.0, 1.2, 1.2, 1.2, 1.0])
            return float(np.sum(weights * (resids ** 2)))

        opt_res = minimize(
            loss_function,
            x0=[initial_cd0 * 1000.0, initial_bsfc * 1000.0],
            method="Powell",
            options={"maxiter": 30, "ftol": 1e-3}
        )

        cal_cd0 = float(opt_res.x[0] / 1000.0)
        cal_bsfc = float(opt_res.x[1] / 1000.0)

        # Calibrated predictions
        cal_preds = np.array([
            self._simulate_point(pt, cal_cd0, cal_bsfc)
            for pt in self.benchmarks
        ])
        cal_residuals = cal_preds - fcom_targets
        cal_rmse = float(np.sqrt(np.mean(cal_residuals ** 2)))
        cal_max_err_pct = float(np.max(np.abs(cal_residuals / fcom_targets) * 100.0))

        ss_res = np.sum(cal_residuals ** 2)
        ss_tot = np.sum((fcom_targets - np.mean(fcom_targets)) ** 2)
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0

        comparisons = []
        for i, pt in enumerate(self.benchmarks):
            comparisons.append({
                "stage_length_nm": pt.stage_length_nm,
                "distance_km": pt.distance_km,
                "fcom_trip_fuel_kg": pt.fcom_trip_fuel_kg,
                "uncalibrated_sim_fuel_kg": round(float(initial_preds[i]), 1),
                "calibrated_sim_fuel_kg": round(float(cal_preds[i]), 1),
                "uncalibrated_error_pct": round(float((initial_preds[i] - pt.fcom_trip_fuel_kg) / pt.fcom_trip_fuel_kg * 100.0), 2),
                "calibrated_error_pct": round(float((cal_preds[i] - pt.fcom_trip_fuel_kg) / pt.fcom_trip_fuel_kg * 100.0), 2)
            })

        return CalibrationResult(
            cd0_initial=initial_cd0,
            cd0_calibrated=round(cal_cd0, 5),
            bsfc_initial=initial_bsfc,
            bsfc_calibrated=round(cal_bsfc, 4),
            uncalibrated_rmse_kg=round(uncal_rmse, 2),
            calibrated_rmse_kg=round(cal_rmse, 2),
            uncalibrated_max_error_pct=round(uncal_max_err_pct, 2),
            calibrated_max_error_pct=round(cal_max_err_pct, 2),
            r_squared=round(r_squared, 4),
            point_comparisons=comparisons
        )
