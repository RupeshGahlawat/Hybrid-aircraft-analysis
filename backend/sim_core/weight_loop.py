"""
Mass Convergence & Multi-Constraint Sizing Loop (CS-25 / FAR Part 25 / 121 Sizing).
Calculates aircraft Take-Off Weight (TOW), Zero Fuel Weight (ZFW), and Landing Weight (LW).
Enforces:
1. Maximum Takeoff Weight (MTOW = 22,800 kg basic / 23,000 kg option)
2. Maximum Zero Fuel Weight (MZFW = 20,800 kg basic / 21,000 kg option)
3. Maximum Landing Weight (MLW = 22,350 kg)
4. Maximum Structural Payload (7,500 kg)
5. Mass-scaled ICAO/DGCA mandatory kerosene reserves (45 min hold + 100 km alternate)
6. Fixed-point iteration with convergence tolerance and seat-shedding inside the loop.
"""

import math
from dataclasses import dataclass

from .aircraft_specs import AircraftBaseline, get_aircraft_specs
from .battery import BatteryConfig, size_battery_pack
from .propulsion import HybridPhaseSchedule, HybridPowertrain, HybridTechParams
from .thermal import compute_instantaneous_heat_load_kw, size_tms_mass


class ConvergenceError(RuntimeError):
    """Raised when the fixed-point sizing iteration fails to converge within max iterations."""

    pass


@dataclass
class SizingResult:
    oew_base_kg: float
    powertrain_delta_kg: float
    battery_mass_kg: float
    battery_capacity_kwh: float
    payload_mass_kg: float
    passengers_carried: int
    mission_fuel_kg: float
    reserve_fuel_kg: float
    taxi_fuel_kg: float
    total_fuel_kg: float
    mtow_calculated_kg: float
    mtow_limit_kg: float
    mzfw_calculated_kg: float
    mzfw_limit_kg: float
    mlw_calculated_kg: float
    mlw_limit_kg: float
    is_structurally_feasible: bool
    payload_penalty_pax: int
    fuel_capacity_margin_kg: float
    limiting_constraint: str  # "MTOW", "MZFW", "MLW", "PAYLOAD_CAPACITY", or "NONE"
    iterations_to_converge: int
    battery_sizing_driver: str = "ENERGY"


def compute_mass_scaled_reserve_fuel(tow_kg: float) -> float:
    """
    Computes required kerosene reserve fuel (kg) scaled to aircraft takeoff mass.
    Components:
    1. 45-minute holding reserve at 1,500 ft: ATR-72 holding fuel flow is ~450 kg/h baseline + 5 kg/h per 1,000 kg above 15,000 kg.
    2. 100 km diversion to alternate airport at nominal cruise burn rate (~1.7 kg/km scaled with mass).
    """
    mass_diff = max(0.0, tow_kg - 15000.0)
    holding_fuel_flow_kg_h = 450.0 + 0.005 * mass_diff
    holding_reserve_kg = 0.75 * holding_fuel_flow_kg_h  # 45 minutes = 0.75 hours

    diversion_rate_kg_km = 1.7 * (tow_kg / 20000.0)
    diversion_reserve_kg = 100.0 * diversion_rate_kg_km

    return holding_reserve_kg + diversion_reserve_kg


def size_aircraft_mass(
    hp_fraction: float | HybridPhaseSchedule = 0.30,
    battery_wh_per_kg: float = 400.0,
    stage_distance_km: float = 400.0,
    nominal_pax: int = 70,
    climb_boost_duration_min: float = 8.0,
    estimated_mission_fuel_kg: float = 800.0,
    specs: AircraftBaseline | None = None,
    weight_option: str = "basic",
    tolerance_kg: float = 0.1,
    max_iterations: int = 30,
    physics_mode: str = "phase2",
    taxi_fuel_kg: float = 80.0,
    ambient_temp_c: float = 25.0,
) -> SizingResult:
    """
    Fixed-point mass convergence sizing loop evaluating MTOW, MZFW, and MLW boundaries.
    Seat-shedding is handled INSIDE the convergence loop so fuel requirements and mass
    re-converge consistently.
    Supports physics_mode='phase2' (advanced dual-sized battery, TMS heat model, taxi fuel)
    and physics_mode='phase1' (backward compatible baseline).
    """
    if specs is None:
        specs = get_aircraft_specs("option" if weight_option == "option" else "basic")

    tech = HybridTechParams(battery_specific_energy_wh_per_kg=battery_wh_per_kg)
    powertrain = HybridPowertrain(hp_schedule=hp_fraction, tech=tech)

    # 1. Powertrain dry mass increment
    pt_weights = powertrain.weights
    powertrain_delta_kg = pt_weights["powertrain_dry_delta_kg"]

    # 2. Battery pack sizing
    max_hp = max(powertrain.schedule.takeoff, powertrain.schedule.climb)
    battery_sizing_driver = "ENERGY"

    if max_hp > 0.0:
        total_elec_kw = powertrain.electric_power_per_engine_kw * specs.num_engines
        boost_hours = (climb_boost_duration_min + 2.0) / 60.0
        e_shaft_kwh = total_elec_kw * boost_hours
        e_battery_usable_kwh = e_shaft_kwh / (tech.motor_efficiency * tech.inverter_efficiency)

        if physics_mode == "phase2":
            # Advanced dual-sized battery model (battery.py)
            b_cfg = BatteryConfig(specific_energy_pack_wh_kg=battery_wh_per_kg)
            b_res = size_battery_pack(
                energy_demanded_usable_kwh=e_battery_usable_kwh,
                peak_power_demanded_kw=total_elec_kw / (tech.motor_efficiency * tech.inverter_efficiency),
                config=b_cfg,
                ambient_temp_c=ambient_temp_c
            )
            battery_mass_kg = b_res["battery_mass_kg"]
            total_battery_capacity_kwh = b_res["nameplate_capacity_kwh"]
            battery_sizing_driver = b_res["sizing_driver"]

            # Physics-driven TMS sizing from peak heat load (thermal.py)
            heat = compute_instantaneous_heat_load_kw(
                shaft_power_electric_kw=total_elec_kw,
                battery_draw_power_kw=total_elec_kw / (tech.motor_efficiency * tech.inverter_efficiency),
                motor_efficiency=tech.motor_efficiency,
                inverter_efficiency=tech.inverter_efficiency,
                battery_efficiency=tech.battery_roundtrip_efficiency
            )
            tms_mass = size_tms_mass(heat["total_heat_load_kw"])
            powertrain_delta_kg = (pt_weights["motors_kg"] + pt_weights["inverters_kg"] + pt_weights["cabling_kg"] + tms_mass)
        else:
            # Phase 1 baseline sizing
            usable_fraction = 1.0 - tech.battery_usable_soc_min
            total_battery_capacity_kwh = e_battery_usable_kwh / usable_fraction
            battery_mass_kg = (total_battery_capacity_kwh * 1000.0) / battery_wh_per_kg
    else:
        total_battery_capacity_kwh = 0.0
        battery_mass_kg = 0.0

    pax_unit_weight = specs.pax_unit_weight_kg  # 95.0 kg (80 kg pax + 15 kg bag)
    effective_taxi_fuel_kg = taxi_fuel_kg if physics_mode == "phase2" else 0.0

    # 3. Fixed-point iteration loop
    pax_count = nominal_pax
    current_mission_fuel = estimated_mission_fuel_kg
    current_tow = (
        specs.oew_kg
        + powertrain_delta_kg
        + battery_mass_kg
        + (pax_count * pax_unit_weight)
        + current_mission_fuel
        + 550.0
        + effective_taxi_fuel_kg
    )

    converged = False
    iteration = 0
    limiting_constraint = "NONE"

    while iteration < max_iterations and not converged:
        iteration += 1

        # Current payload
        payload_kg = pax_count * pax_unit_weight

        # Zero Fuel Weight
        zfw = specs.oew_kg + powertrain_delta_kg + battery_mass_kg + payload_kg

        # Mass-scaled reserve fuel
        reserve_fuel = compute_mass_scaled_reserve_fuel(current_tow)
        total_fuel = current_mission_fuel + reserve_fuel

        # Takeoff weight and Landing weight
        tow = zfw + total_fuel
        lw = (
            tow - current_mission_fuel
        )  # Since battery remains aboard, landing weight includes all dry hybrid mass + battery

        # Constraint evaluation
        excess_mtow = max(0.0, tow - specs.mtow_kg)
        excess_mzfw = max(0.0, zfw - specs.mzfw_kg)
        excess_mlw = max(0.0, lw - specs.mlw_kg)
        excess_payload = max(0.0, payload_kg - specs.max_payload_kg)

        # Determine the most restrictive excess mass
        max_excess = max(excess_mtow, excess_mzfw, excess_mlw, excess_payload)

        if max_excess > 0.0:
            if max_excess == excess_mtow:
                limiting_constraint = "MTOW"
            elif max_excess == excess_mzfw:
                limiting_constraint = "MZFW"
            elif max_excess == excess_mlw:
                limiting_constraint = "MLW"
            else:
                limiting_constraint = "PAYLOAD_CAPACITY"

            # Shed passenger seats to relieve constraint
            seats_to_shed = int(math.ceil(max_excess / pax_unit_weight))
            new_pax = max(0, pax_count - seats_to_shed)

            if new_pax != pax_count:
                pax_count = new_pax
                # Re-estimate mission fuel for reduced mass
                current_mission_fuel = max(100.0, estimated_mission_fuel_kg * (1.0 - 0.003 * seats_to_shed))
                current_tow = tow - (seats_to_shed * pax_unit_weight)
                continue

        # Check convergence on TOW
        if abs(tow - current_tow) < tolerance_kg:
            converged = True
            current_tow = tow
            break

        current_tow = 0.5 * (current_tow + tow)  # Relaxation update

    if not converged:
        raise ConvergenceError(
            f"Weight loop did not converge after {max_iterations} iterations (current_tow={current_tow:.1f}, tow={tow:.1f})."
        )

    actual_payload_kg = pax_count * pax_unit_weight
    final_zfw = specs.oew_kg + powertrain_delta_kg + battery_mass_kg + actual_payload_kg
    final_reserve = compute_mass_scaled_reserve_fuel(current_tow)
    final_total_fuel = current_mission_fuel + final_reserve
    final_tow = final_zfw + final_total_fuel
    final_lw = final_tow - current_mission_fuel

    payload_penalty_pax = nominal_pax - pax_count
    # Feasible if pax carried >= 50 and all structural limits satisfied
    is_feasible = (
        (pax_count >= 50)
        and (final_tow <= specs.mtow_kg + 0.1)
        and (final_zfw <= specs.mzfw_kg + 0.1)
        and (final_lw <= specs.mlw_kg + 0.1)
    )
    fuel_capacity_margin = specs.max_fuel_capacity_kg - final_total_fuel

    return SizingResult(
        oew_base_kg=specs.oew_kg,
        powertrain_delta_kg=powertrain_delta_kg,
        battery_mass_kg=battery_mass_kg,
        battery_capacity_kwh=total_battery_capacity_kwh,
        payload_mass_kg=actual_payload_kg,
        passengers_carried=pax_count,
        mission_fuel_kg=current_mission_fuel,
        reserve_fuel_kg=final_reserve,
        taxi_fuel_kg=effective_taxi_fuel_kg,
        total_fuel_kg=final_total_fuel + effective_taxi_fuel_kg,
        mtow_calculated_kg=final_tow + effective_taxi_fuel_kg,
        mtow_limit_kg=specs.mtow_kg,
        mzfw_calculated_kg=final_zfw,
        mzfw_limit_kg=specs.mzfw_kg,
        mlw_calculated_kg=final_lw,
        mlw_limit_kg=specs.mlw_kg,
        is_structurally_feasible=is_feasible,
        payload_penalty_pax=payload_penalty_pax,
        fuel_capacity_margin_kg=fuel_capacity_margin,
        limiting_constraint=limiting_constraint,
        iterations_to_converge=iteration,
        battery_sizing_driver=battery_sizing_driver,
    )
