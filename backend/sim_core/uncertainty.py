"""
Uncertainty Quantification, Monte Carlo Feasibility & Sensitivity Engine.
Includes:
1. Technology Horizon Sweeps: Battery pack specific energy (250 - 600 Wh/kg) and crossover thresholds.
2. Quasi-Random Monte Carlo Feasibility: Sobol sequence space-filling sampling (N=1000) for structural feasibility probability.
3. Tornado Sensitivity Analysis: One-at-a-time (OAT) parameter swings to rank key uncertainty drivers.
"""
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import norm, qmc

from backend.sim_core.aircraft_specs import ATR72_BASELINE, AircraftBaseline
from backend.sim_core.mission_sim import MissionSimulator
from backend.sim_core.routes import Route
from backend.sim_core.weight_loop import size_aircraft_mass


@dataclass
class TechnologyThresholds:
    zero_seat_shed_density_wh_kg: float | None
    co2_breakeven_density_wh_kg: float | None
    economic_breakeven_density_wh_kg: float | None


def run_battery_density_sweep(
    route: Route,
    hp_fraction: float = 0.30,
    densities: list[float] | None = None,
    ambient_delta_c: float = 0.0,
    grid_co2_kg_per_kwh: float | None = None,
    physics_mode: str = "phase2"
) -> dict[str, Any]:
    """
    Sweeps battery specific energy from current technology (250 Wh/kg) to advanced future horizons (600 Wh/kg).
    Calculates zero-seat-shed and net CO2 break-even technology thresholds.
    """
    if densities is None:
        densities = [250.0, 280.0, 320.0, 360.0, 400.0, 450.0, 500.0, 550.0, 600.0]

    sweep_points = []
    zero_seat_shed_thresh: float | None = None
    co2_breakeven_thresh: float | None = None
    doc_breakeven_thresh: float | None = None

    for d in densities:
        sim = MissionSimulator(
            route=route,
            hp_fraction=hp_fraction,
            battery_wh_per_kg=d,
            ambient_delta_c=ambient_delta_c,
            grid_co2_kg_per_kwh=grid_co2_kg_per_kwh,
            physics_mode=physics_mode
        )
        res = sim.run_simulation()
        s = res["summary"]

        pax = s["passengers_carried"]
        fuel_save_pct = s["fuel_saved_pct"]
        net_co2_pct = s["net_co2_saved_pct_wtw"]
        doc = s.get("operating_costs", {})
        doc_delta = doc.get("net_cost_savings_usd", 0.0)

        # Threshold detection
        if pax == 70 and zero_seat_shed_thresh is None:
            zero_seat_shed_thresh = d
        if net_co2_pct > 0.0 and co2_breakeven_thresh is None:
            co2_breakeven_thresh = d
        if doc_delta > 0.0 and doc_breakeven_thresh is None:
            doc_breakeven_thresh = d

        sweep_points.append({
            "specific_energy_wh_kg": d,
            "battery_weight_kg": s["battery_weight_kg"],
            "passengers_carried": pax,
            "payload_penalty_pax": s["payload_penalty_pax"],
            "limiting_constraint": s["limiting_constraint"],
            "fuel_saved_kg": s["fuel_saved_kg"],
            "fuel_saved_pct": fuel_save_pct,
            "net_co2_saved_pct_wtw": net_co2_pct,
            "hybrid_block_fuel_kg": s["block_fuel_hybrid_kg"],
            "conv_block_fuel_kg": s["block_fuel_conv_kg"],
            "doc_savings_usd": doc_delta,
            "is_feasible": s["is_feasible"]
        })

    return {
        "route_id": route.route_id,
        "hp_fraction": hp_fraction,
        "ambient_delta_c": ambient_delta_c,
        "points": sweep_points,
        "thresholds": {
            "zero_seat_shed_density_wh_kg": zero_seat_shed_thresh,
            "co2_breakeven_density_wh_kg": co2_breakeven_thresh,
            "economic_breakeven_density_wh_kg": doc_breakeven_thresh
        }
    }


def run_monte_carlo_feasibility(
    route: Route,
    hp_fraction: float = 0.30,
    n_samples: int = 1000,
    seed: int = 42
) -> dict[str, Any]:
    """
    Executes Sobol quasi-random sequence Monte Carlo simulation (N=1000 default)
    across multi-dimensional input uncertainty distributions:
    1. Battery pack density: U(280, 450) Wh/kg
    2. Summer ambient temperature delta: U(0, 25) °C
    3. Grid emission factor: U(0.55, 0.85) kg/kWh
    4. Airframe parasite drag uncertainty: N(0.02803, 0.0015)
    5. Motor power density: N(5.0, 0.5) kW/kg
    6. Takeoff taxi fuel allowance: U(60, 100) kg
    """
    # Sobol low-discrepancy sampler in 6 dimensions
    sampler = qmc.Sobol(d=6, seed=seed)
    # Sobol requires power of 2 for optimal space filling, clip to n_samples
    m_power = int(np.ceil(np.log2(n_samples)))
    raw_samples = sampler.random_base2(m=m_power)[:n_samples]

    # Map uniform unit hypercube to physical distributions
    batt_densities = 280.0 + raw_samples[:, 0] * (450.0 - 280.0)
    ambient_deltas = 0.0 + raw_samples[:, 1] * 25.0
    grid_factors = 0.55 + raw_samples[:, 2] * (0.85 - 0.55)
    cd0_values = norm.ppf(np.clip(raw_samples[:, 3], 1e-4, 1.0 - 1e-4), loc=0.02803, scale=0.0015)
    cd0_values = np.clip(cd0_values, 0.023, 0.035)
    motor_p_densities = norm.ppf(np.clip(raw_samples[:, 4], 1e-4, 1.0 - 1e-4), loc=5.0, scale=0.5)
    motor_p_densities = np.clip(motor_p_densities, 3.5, 6.5)
    taxi_fuels = 60.0 + raw_samples[:, 5] * 40.0

    feasible_count = 0
    pax_carried_list = []
    fuel_saved_pct_list = []
    net_co2_pct_list = []
    limiting_constraints = {"MTOW": 0, "MZFW": 0, "MLW": 0, "NONE": 0}

    # Execute simulation iterations
    # Pre-calculate conventional baseline
    est_fuel = 1.8 * route.stage_distance_km
    for i in range(n_samples):
        b_wh = float(batt_densities[i])
        amb_d = float(ambient_deltas[i])
        g_co2 = float(grid_factors[i])
        c_d0 = float(cd0_values[i])
        t_fuel = float(taxi_fuels[i])

        custom_specs = AircraftBaseline(
            cd0_clean=c_d0,
            bsfc_cruise_kg_per_kwh=0.3299
        )

        sizing = size_aircraft_mass(
            hp_fraction=hp_fraction,
            battery_wh_per_kg=b_wh,
            stage_distance_km=route.stage_distance_km,
            estimated_mission_fuel_kg=est_fuel,
            specs=custom_specs,
            taxi_fuel_kg=t_fuel,
            ambient_temp_c=15.0 + amb_d
        )

        pax = sizing.passengers_carried
        pax_carried_list.append(pax)
        limit = sizing.limiting_constraint
        limiting_constraints[limit] = limiting_constraints.get(limit, 0) + 1

        # Feasibility criterion: meets all structural boundaries with >= 60 passengers carried (<= 10 shed)
        is_feas = sizing.is_structurally_feasible and pax >= 60
        if is_feas:
            feasible_count += 1

        # Approximate fuel and CO2 delta for distribution
        # Energy balance approximation scaled from verified baseline
        fuel_savings_pct = max(0.0, hp_fraction * 0.70 - (sizing.battery_mass_kg / ATR72_BASELINE.mtow_kg) * 20.0)
        fuel_saved_pct_list.append(round(fuel_savings_pct, 2))

        # Well-to-wake CO2 accounting
        tailpipe_co2_save = fuel_savings_pct * 3.84
        grid_co2_penalty = (hp_fraction * 0.85) * (g_co2 / 0.74) * 2.8
        net_co2 = tailpipe_co2_save - grid_co2_penalty
        net_co2_pct_list.append(round(net_co2, 2))

    feasibility_prob = float(feasible_count / n_samples)

    return {
        "route_id": route.route_id,
        "hp_fraction": hp_fraction,
        "n_samples": n_samples,
        "feasibility_probability": round(feasibility_prob, 4),
        "confidence_interval_95": [
            round(max(0.0, feasibility_prob - 1.96 * np.sqrt(feasibility_prob * (1.0 - feasibility_prob) / n_samples)), 4),
            round(min(1.0, feasibility_prob + 1.96 * np.sqrt(feasibility_prob * (1.0 - feasibility_prob) / n_samples)), 4)
        ],
        "limiting_constraint_distribution": {
            k: round(v / n_samples * 100.0, 1) for k, v in limiting_constraints.items()
        },
        "passengers_carried_stats": {
            "mean": round(float(np.mean(pax_carried_list)), 1),
            "median": int(np.median(pax_carried_list)),
            "p05": int(np.percentile(pax_carried_list, 5)),
            "p95": int(np.percentile(pax_carried_list, 95))
        },
        "fuel_saved_pct_stats": {
            "mean": round(float(np.mean(fuel_saved_pct_list)), 2),
            "median": round(float(np.median(fuel_saved_pct_list)), 2),
            "p05": round(float(np.percentile(fuel_saved_pct_list, 5)), 2),
            "p95": round(float(np.percentile(fuel_saved_pct_list, 95)), 2)
        },
        "net_co2_saved_pct_stats": {
            "mean": round(float(np.mean(net_co2_pct_list)), 2),
            "median": round(float(np.median(net_co2_pct_list)), 2),
            "p05": round(float(np.percentile(net_co2_pct_list, 5)), 2),
            "p95": round(float(np.percentile(net_co2_pct_list, 95)), 2)
        }
    }


def run_tornado_sensitivity(
    route: Route,
    hp_fraction: float = 0.30,
    baseline_battery_wh_kg: float = 400.0
) -> dict[str, Any]:
    """
    Computes One-at-a-Time (OAT) parameter sensitivities relative to baseline nominal conditions.
    Ranks uncertainty drivers by the swing magnitude in Net CO2 % and Fuel Savings %.
    """
    # Nominal reference run
    baseline_sim = MissionSimulator(
        route=route,
        hp_fraction=hp_fraction,
        battery_wh_per_kg=baseline_battery_wh_kg,
        ambient_delta_c=0.0,
        physics_mode="phase2"
    )
    base_res = baseline_sim.run_simulation()["summary"]
    base_fuel_pct = base_res["fuel_saved_pct"]
    base_co2_pct = base_res["net_co2_saved_pct_wtw"]

    # Parameter variations (variable, low_val, high_val, label)
    parameters_to_test = [
        ("battery_wh_per_kg", 320.0, 480.0, "Battery Pack Density (±20%)"),
        ("ambient_delta_c", -10.0, 25.0, "Ambient Temperature (-10°C to +25°C)"),
        ("grid_co2_kg_per_kwh", 0.40, 0.85, "Grid Carbon Intensity (0.40 to 0.85 kg/kWh)"),
        ("cd0", 0.0240, 0.0320, "Parasite Drag Cd0 (±15%)"),
    ]

    tornado_items = []

    for param, val_low, val_high, label in parameters_to_test:
        # Evaluate Low
        if param == "battery_wh_per_kg":
            s_low = MissionSimulator(route, hp_fraction, battery_wh_per_kg=val_low, physics_mode="phase2").run_simulation()["summary"]
            s_high = MissionSimulator(route, hp_fraction, battery_wh_per_kg=val_high, physics_mode="phase2").run_simulation()["summary"]
        elif param == "ambient_delta_c":
            s_low = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, ambient_delta_c=val_low, physics_mode="phase2").run_simulation()["summary"]
            s_high = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, ambient_delta_c=val_high, physics_mode="phase2").run_simulation()["summary"]
        elif param == "grid_co2_kg_per_kwh":
            s_low = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, grid_co2_kg_per_kwh=val_low, physics_mode="phase2").run_simulation()["summary"]
            s_high = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, grid_co2_kg_per_kwh=val_high, physics_mode="phase2").run_simulation()["summary"]
        elif param == "cd0":
            sp_low = AircraftBaseline(cd0_clean=val_low)
            sp_high = AircraftBaseline(cd0_clean=val_high)
            s_low = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, specs=sp_low, physics_mode="phase2").run_simulation()["summary"]
            s_high = MissionSimulator(route, hp_fraction, battery_wh_per_kg=baseline_battery_wh_kg, specs=sp_high, physics_mode="phase2").run_simulation()["summary"]

        low_co2 = s_low["net_co2_saved_pct_wtw"]
        high_co2 = s_high["net_co2_saved_pct_wtw"]
        swing_co2 = abs(high_co2 - low_co2)

        low_fuel = s_low["fuel_saved_pct"]
        high_fuel = s_high["fuel_saved_pct"]
        swing_fuel = abs(high_fuel - low_fuel)

        tornado_items.append({
            "parameter": param,
            "label": label,
            "val_low": val_low,
            "val_high": val_high,
            "fuel_saved_low": low_fuel,
            "fuel_saved_high": high_fuel,
            "fuel_swing_pct": round(swing_fuel, 2),
            "co2_saved_low": low_co2,
            "co2_saved_high": high_co2,
            "co2_swing_pct": round(swing_co2, 2)
        })

    # Sort descending by CO2 swing magnitude
    tornado_items.sort(key=lambda x: x["co2_swing_pct"], reverse=True)

    return {
        "route_id": route.route_id,
        "baseline_fuel_saved_pct": base_fuel_pct,
        "baseline_co2_saved_pct": base_co2_pct,
        "rankings": tornado_items
    }
