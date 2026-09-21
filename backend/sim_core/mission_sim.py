"""
Point-Mass Flight Mission Trajectory Integrator.
Simulates commercial mission segments (Takeoff Roll, Climb, Cruise, Descent, Landing),
generating 3D spatial coordinates and instantaneous telemetry vectors for both
Conventional and Hybrid-Electric ATR-72 configurations.
"""

import math
from typing import Any

from .aircraft_specs import AircraftBaseline, get_aircraft_specs
from .atmosphere import G0, get_atmosphere
from .costs import compute_direct_operating_costs
from .engine_map import TurboshaftEngineMap
from .propeller import PropellerModel, integrate_takeoff_distance
from .propulsion import HybridPhaseSchedule, HybridPowertrain, HybridTechParams
from .routes import Route
from .safety import evaluate_safety_envelope
from .weight_loop import SizingResult, size_aircraft_mass


class MissionSimulator:
    def __init__(
        self,
        route: Route,
        hp_fraction: float | HybridPhaseSchedule = 0.30,
        battery_wh_per_kg: float = 400.0,
        ambient_delta_c: float = 0.0,
        grid_co2_kg_per_kwh: float | None = None,
        include_well_to_tank: bool = False,
        weight_option: str = "basic",
        physics_mode: str = "phase2",
        specs: AircraftBaseline | None = None,
    ):
        self.route = route
        self.battery_wh_per_kg = battery_wh_per_kg
        self.ambient_delta_c = ambient_delta_c
        self.include_well_to_tank = include_well_to_tank
        self.weight_option = weight_option
        self.physics_mode = physics_mode

        # Grid carbon intensity (defaults to CEA v19.0 database value for route if not overridden)
        self.grid_co2_kg_per_kwh = (
            grid_co2_kg_per_kwh if grid_co2_kg_per_kwh is not None else route.regional_grid_co2_kg_per_kwh
        )

        # Resolve schedule
        if isinstance(hp_fraction, (int, float)):
            val = max(0.0, min(0.60, float(hp_fraction)))
            self.schedule = HybridPhaseSchedule(takeoff=val, climb=val, cruise=0.0, descent=0.0)
            self.hp_fraction = val
        else:
            self.schedule = hp_fraction
            self.hp_fraction = max(hp_fraction.takeoff, hp_fraction.climb)

        self.tech = HybridTechParams(battery_specific_energy_wh_per_kg=battery_wh_per_kg)
        self.powertrain = HybridPowertrain(hp_schedule=self.schedule, tech=self.tech)
        self.baseline_powertrain = HybridPowertrain(hp_schedule=0.0)
        self.specs = specs if specs is not None else get_aircraft_specs("option" if weight_option == "option" else "basic")
        self.engine_map = TurboshaftEngineMap(bsfc_cruise_nominal_kg_kwh=self.specs.bsfc_cruise_kg_per_kwh)

    def run_simulation(self) -> dict[str, Any]:
        """
        Runs full flight mission for both Hybrid and Conventional baseline,
        returning side-by-side time-series telemetry and summary metrics.
        """
        # Step 1: Pre-sizing baseline mission fuel
        est_fuel = 1.8 * self.route.stage_distance_km  # ~1.8 kg fuel per km for ATR 72

        # Sizing mass for both configurations
        sizing_hybrid = size_aircraft_mass(
            hp_fraction=self.schedule,
            battery_wh_per_kg=self.battery_wh_per_kg,
            stage_distance_km=self.route.stage_distance_km,
            estimated_mission_fuel_kg=est_fuel,
            specs=self.specs,
            weight_option=self.weight_option,
            physics_mode=self.physics_mode,
            ambient_temp_c=15.0 + self.ambient_delta_c,
        )
        sizing_conv = size_aircraft_mass(
            hp_fraction=0.0,
            battery_wh_per_kg=self.battery_wh_per_kg,
            stage_distance_km=self.route.stage_distance_km,
            estimated_mission_fuel_kg=est_fuel,
            specs=self.specs,
            weight_option=self.weight_option,
            physics_mode=self.physics_mode,
            ambient_temp_c=15.0 + self.ambient_delta_c,
        )

        # Step 2: Simulate flight trajectory for both
        hybrid_telemetry = self._integrate_trajectory(sizing_hybrid, is_hybrid=True)
        conv_telemetry = self._integrate_trajectory(sizing_conv, is_hybrid=False)

        # Step 3: Comparative metrics calculation
        fuel_conv = conv_telemetry["total_fuel_burned_kg"]
        fuel_hybrid = hybrid_telemetry["total_fuel_burned_kg"]
        fuel_saved_kg = max(0.0, fuel_conv - fuel_hybrid)
        fuel_saved_pct = (fuel_saved_kg / fuel_conv * 100.0) if fuel_conv > 0 else 0.0

        # Emission factors
        # Direct Tank-to-Wake: 3.16 kg CO2 per kg Jet-A1 (ICAO standard)
        # Upstream Well-to-Tank: +0.68 kg CO2 per kg Jet-A1 (ICAO CORSIA / JEC standard)
        ef_ttw = 3.16
        ef_wtw = 3.16 + (0.68 if self.include_well_to_tank else 0.0)

        co2_conv_ttw_kg = fuel_conv * ef_ttw
        co2_conv_wtw_kg = fuel_conv * ef_wtw
        co2_hybrid_tailpipe_kg = fuel_hybrid * ef_ttw
        co2_hybrid_combustion_wtw_kg = fuel_hybrid * ef_wtw

        # Recharge energy required from grid (accounting for 90% ground charger efficiency)
        charger_efficiency = 0.90
        battery_energy_recharge_kwh = hybrid_telemetry["battery_energy_consumed_kwh"] / charger_efficiency
        grid_co2_kg = battery_energy_recharge_kwh * self.grid_co2_kg_per_kwh

        net_hybrid_co2_ttw_kg = co2_hybrid_tailpipe_kg + grid_co2_kg
        net_hybrid_co2_wtw_kg = co2_hybrid_combustion_wtw_kg + grid_co2_kg

        net_co2_saved_pct_ttw = (
            ((co2_conv_ttw_kg - net_hybrid_co2_ttw_kg) / co2_conv_ttw_kg * 100.0) if co2_conv_ttw_kg > 0 else 0.0
        )
        net_co2_saved_pct_wtw = (
            ((co2_conv_wtw_kg - net_hybrid_co2_wtw_kg) / co2_conv_wtw_kg * 100.0) if co2_conv_wtw_kg > 0 else 0.0
        )

        # Step 4: Phase 2 Physics Evaluations (Takeoff distance to 35 ft, Safety, Operating Costs)
        origin_alt_m = self.route.origin.elevation_ft * 0.3048
        prop_model = PropellerModel()
        p_to_conv_kw = self.specs.num_engines * self.specs.takeoff_power_kw_per_engine
        atm_to = get_atmosphere(origin_alt_m, self.ambient_delta_c)
        elec_to_kw = p_to_conv_kw * self.schedule.takeoff
        turboshaft_to_kw = (p_to_conv_kw - elec_to_kw) * atm_to["sigma"]
        p_to_hybrid_kw = elec_to_kw + turboshaft_to_kw

        tod_conv = integrate_takeoff_distance(
            mass_kg=sizing_conv.mtow_calculated_kg,
            total_shaft_power_kw=p_to_conv_kw,
            specs=self.specs,
            altitude_m=origin_alt_m,
            ambient_delta_c=self.ambient_delta_c,
            prop_model=prop_model
        )
        tod_hybrid = integrate_takeoff_distance(
            mass_kg=sizing_hybrid.mtow_calculated_kg,
            total_shaft_power_kw=p_to_hybrid_kw,
            specs=self.specs,
            altitude_m=origin_alt_m,
            ambient_delta_c=self.ambient_delta_c,
            prop_model=prop_model
        )

        # Compare against published ATR 72-600 FCOM takeoff distance: 1,279 m at basic MTOW (22,800 kg), sea level, ISA
        tod_published_fcom_m = 1279.0
        is_sea_level_isa = (origin_alt_m < 50.0 and abs(self.ambient_delta_c) < 1.0)
        tod_conv_error_pct = (
            round(((tod_conv["total_takeoff_distance_m"] - tod_published_fcom_m) / tod_published_fcom_m) * 100.0, 2)
            if is_sea_level_isa else None
        )

        # Safety envelope checks
        safety_eval = evaluate_safety_envelope(
            takeoff_mass_kg=sizing_hybrid.mtow_calculated_kg,
            altitude_m=origin_alt_m,
            ambient_delta_c=self.ambient_delta_c,
            specs=self.specs,
            prop_model=prop_model
        )

        # Direct Operating Costs
        flight_duration_hours = hybrid_telemetry["flight_duration_min"] / 60.0
        doc_eval = compute_direct_operating_costs(
            fuel_burned_conv_kg=fuel_conv + sizing_conv.taxi_fuel_kg,
            fuel_burned_hybrid_kg=fuel_hybrid + sizing_hybrid.taxi_fuel_kg,
            battery_recharge_kwh=battery_energy_recharge_kwh,
            battery_capacity_kwh=sizing_hybrid.battery_capacity_kwh,
            flight_duration_hours=flight_duration_hours,
            seats_shed=sizing_hybrid.payload_penalty_pax
        )

        return {
            "route": {
                "route_id": self.route.route_id,
                "name": self.route.name,
                "origin": self.route.origin.iata,
                "origin_elev_ft": self.route.origin.elevation_ft,
                "destination": self.route.destination.iata,
                "dest_elev_ft": self.route.destination.elevation_ft,
                "stage_distance_km": self.route.stage_distance_km,
                "nominal_cruise_alt_ft": self.route.nominal_cruise_alt_ft,
                "is_return_leg": self.route.is_return_leg,
            },
            "parameters": {
                "hp_fraction": self.hp_fraction,
                "hp_schedule": {
                    "takeoff": self.schedule.takeoff,
                    "climb": self.schedule.climb,
                    "cruise": self.schedule.cruise,
                    "descent": self.schedule.descent,
                },
                "battery_wh_per_kg": self.battery_wh_per_kg,
                "ambient_delta_c": self.ambient_delta_c,
                "ambient_oat_c_sea_level": 15.0 + self.ambient_delta_c,
                "grid_co2_kg_per_kwh": self.grid_co2_kg_per_kwh,
                "include_well_to_tank": self.include_well_to_tank,
                "weight_option": self.weight_option,
            },
            "summary": {
                "conventional_fuel_kg": round(fuel_conv, 1),
                "hybrid_fuel_kg": round(fuel_hybrid, 1),
                "fuel_saved_kg": round(fuel_saved_kg, 1),
                "fuel_saved_pct": round(fuel_saved_pct, 1),
                "conventional_co2_kg": round(co2_conv_ttw_kg, 1),
                "conventional_co2_wtw_kg": round(co2_conv_wtw_kg, 1),
                "hybrid_tailpipe_co2_kg": round(co2_hybrid_tailpipe_kg, 1),
                "grid_recharge_co2_kg": round(grid_co2_kg, 1),
                "net_co2_saved_pct": round(net_co2_saved_pct_ttw, 1),
                "net_co2_saved_pct_wtw": round(net_co2_saved_pct_wtw, 1),
                "battery_energy_consumed_kwh": round(hybrid_telemetry["battery_energy_consumed_kwh"], 1),
                "battery_recharge_energy_kwh": round(battery_energy_recharge_kwh, 1),
                "energy_kwh_by_phase": hybrid_telemetry["energy_kwh_by_phase"],
                "takeoff_roll_conv_m": round(conv_telemetry["takeoff_roll_m"], 0),
                "takeoff_roll_hybrid_m": round(hybrid_telemetry["takeoff_roll_m"], 0),
                "takeoff_roll_reduction_pct": round(
                    (1.0 - hybrid_telemetry["takeoff_roll_m"] / conv_telemetry["takeoff_roll_m"]) * 100.0, 1
                ),
                "battery_weight_kg": round(sizing_hybrid.battery_mass_kg, 1),
                "battery_capacity_kwh": round(sizing_hybrid.battery_capacity_kwh, 1),
                "mtow_hybrid_kg": round(sizing_hybrid.mtow_calculated_kg, 1),
                "mtow_conv_kg": round(sizing_conv.mtow_calculated_kg, 1),
                "mzfw_hybrid_kg": round(sizing_hybrid.mzfw_calculated_kg, 1),
                "mlw_hybrid_kg": round(sizing_hybrid.mlw_calculated_kg, 1),
                "passengers_carried": sizing_hybrid.passengers_carried,
                "payload_penalty_pax": sizing_hybrid.payload_penalty_pax,
                "limiting_constraint": sizing_hybrid.limiting_constraint,
                "battery_sizing_driver": sizing_hybrid.battery_sizing_driver,
                "is_feasible": sizing_hybrid.is_structurally_feasible,
                "takeoff_distance_35ft_conv_m": round(tod_conv["total_takeoff_distance_m"], 1),
                "takeoff_distance_35ft_hybrid_m": round(tod_hybrid["total_takeoff_distance_m"], 1),
                "takeoff_distance_published_fcom_m": tod_published_fcom_m,
                "takeoff_distance_error_vs_fcom_pct": tod_conv_error_pct,
                "safety_oei_climb_gradient_pct": safety_eval.oei_climb_gradient_pct,
                "safety_oei_check_passed": safety_eval.oei_check_passed,
                "safety_elec_failure_gradient_pct": safety_eval.elec_failure_climb_gradient_pct,
                "safety_elec_failure_check_passed": safety_eval.elec_failure_check_passed,
                "taxi_fuel_kg": sizing_hybrid.taxi_fuel_kg,
                "block_fuel_conv_kg": round(fuel_conv + sizing_conv.taxi_fuel_kg, 1),
                "block_fuel_hybrid_kg": round(fuel_hybrid + sizing_hybrid.taxi_fuel_kg, 1),
                "operating_costs": doc_eval,
            },
            "telemetry_hybrid": hybrid_telemetry["profile"],
            "telemetry_conv": conv_telemetry["profile"],
        }

    def _integrate_trajectory(self, sizing: SizingResult, is_hybrid: bool) -> dict[str, Any]:
        """
        Integrates flight segments: Takeoff ground roll, Climb, Cruise, Descent.
        """
        pt = self.powertrain if is_hybrid else self.baseline_powertrain

        # Flight parameters
        current_mass = sizing.mtow_calculated_kg
        battery_soc = 1.0 if is_hybrid else 0.0
        total_battery_kwh = sizing.battery_capacity_kwh
        battery_energy_used_kwh = 0.0
        total_fuel_burned = 0.0

        energy_by_phase = {"takeoff": 0.0, "climb": 0.0, "cruise": 0.0, "descent": 0.0}

        profile = []
        t = 0.0
        distance_m = 0.0
        origin_alt_m = self.route.origin.elevation_ft * 0.3048
        dest_alt_m = self.route.destination.elevation_ft * 0.3048
        altitude_m = origin_alt_m
        target_cruise_alt_m = max(dest_alt_m + 1500.0, self.route.nominal_cruise_alt_ft * 0.3048)

        # 1. Takeoff Ground Roll
        # Accelerated run from 0 to V_R (55.5 m/s)
        v = 0.0
        v_vr = self.specs.takeoff_vr_kias * 0.514444  # m/s (~55.5 m/s)
        dt = 1.0  # 1-second time step for ground roll

        while v < v_vr:
            atm = get_atmosphere(altitude_m, self.ambient_delta_c)
            rho = atm["density_kg_m3"]

            # Thrust available (PW127M baseline = 2 x 1845.6 kW = 3691.2 kW)
            p_avail_kw = self.specs.num_engines * self.specs.takeoff_power_kw_per_engine

            # Electric motor does not suffer atmospheric density lapse, but turboshaft does
            if is_hybrid:
                elec_kw = p_avail_kw * pt.schedule.takeoff
                turboshaft_kw = (p_avail_kw - elec_kw) * atm["sigma"]
                p_total_shaft_kw = elec_kw + turboshaft_kw
            else:
                p_total_shaft_kw = p_avail_kw * atm["sigma"]

            eta_prop = self.specs.propeller_efficiency_takeoff
            v_eff = max(v, 8.0)
            thrust_n = (p_total_shaft_kw * 1000.0 * eta_prop) / v_eff

            # Aerodynamic drag and rolling friction
            q = 0.5 * rho * (v**2)
            cl = 0.6  # Ground roll angle CL
            cd = self.specs.cd0_takeoff_flaps + (cl**2) / (
                math.pi * self.specs.aspect_ratio * self.specs.oswald_efficiency
            )
            drag_n = q * self.specs.wing_area_m2 * cd
            lift_n = q * self.specs.wing_area_m2 * cl
            normal_force = max(0.0, current_mass * G0 - lift_n)
            friction_n = 0.025 * normal_force  # Rubber on asphalt mu ~ 0.025

            # Net forward acceleration
            a = (thrust_n - drag_n - friction_n) / current_mass
            v += a * dt
            distance_m += v * dt
            t += dt

            # Power split & fuel
            split = pt.compute_instantaneous_power_split(p_total_shaft_kw, "takeoff", battery_soc)
            fuel_burned_step = split["fuel_flow_kg_s"] * dt
            total_fuel_burned += fuel_burned_step
            current_mass -= fuel_burned_step

            if is_hybrid and total_battery_kwh > 0:
                e_step_kwh = (split["p_battery_draw_kw"] * dt) / 3600.0
                battery_energy_used_kwh += e_step_kwh
                energy_by_phase["takeoff"] += e_step_kwh
                battery_soc = max(0.0, 1.0 - (battery_energy_used_kwh / total_battery_kwh))

            if int(t) % 4 == 0 or v >= v_vr:
                v_tas_kt = v * 1.94384
                v_ias_kt = v_tas_kt * math.sqrt(atm["sigma"])
                profile.append(
                    {
                        "time_s": round(t, 1),
                        "phase": "takeoff",
                        "distance_km": round(distance_m / 1000.0, 3),
                        "altitude_ft": round(altitude_m * 3.28084, 0),
                        "altitude_agl_ft": round((altitude_m - origin_alt_m) * 3.28084, 0),
                        "airspeed_kt": round(v_ias_kt, 1),
                        "airspeed_ias_kt": round(v_ias_kt, 1),
                        "airspeed_tas_kt": round(v_tas_kt, 1),
                        "airspeed_mps": round(v, 1),
                        "pitch_deg": 1.5 if v < v_vr * 0.9 else 8.0,
                        "roll_deg": 0.0,
                        "climb_rate_fpm": 0.0,
                        "turboshaft_power_kw": round(split["p_shaft_turboshaft_kw"], 0),
                        "electric_power_kw": round(split["p_shaft_electric_kw"], 0),
                        "fuel_flow_kg_hr": round(split["fuel_flow_kg_hr"], 1),
                        "fuel_burned_kg": round(total_fuel_burned, 1),
                        "battery_soc_pct": round(battery_soc * 100.0, 1),
                        "waste_heat_kw": round(split["waste_heat_kw"], 1),
                        "gear_extended": True,
                    }
                )

        takeoff_roll_m = distance_m

        # 2. Climb Segment
        v_climb_mps = 85.0  # ~165 KIAS
        climb_rate_mps = 6.5  # ~1,280 ft/min
        dt_climb = 15.0

        while altitude_m < target_cruise_alt_m:
            atm = get_atmosphere(altitude_m, self.ambient_delta_c)
            rho = atm["density_kg_m3"]

            # Thrust required and aerodynamic drag
            q = 0.5 * rho * (v_climb_mps**2)
            cl = (current_mass * G0) / (q * self.specs.wing_area_m2)
            cd = self.specs.cd0_clean + (cl**2) / (math.pi * self.specs.aspect_ratio * self.specs.oswald_efficiency)
            drag_n = q * self.specs.wing_area_m2 * cd

            # Climb angle gamma = arcsin(climb_rate / V)
            sin_gamma = max(0.01, min(0.20, climb_rate_mps / v_climb_mps))
            gamma = math.asin(sin_gamma)

            thrust_req_n = drag_n + current_mass * G0 * sin_gamma
            p_shaft_req_kw = (thrust_req_n * v_climb_mps) / (self.specs.propeller_efficiency_climb * 1000.0)

            split = pt.compute_instantaneous_power_split(p_shaft_req_kw, "climb", battery_soc)
            if self.physics_mode == "phase2":
                fuel_flow_s = self.engine_map.compute_fuel_flow_kg_s(
                    shaft_power_kw=split["p_shaft_turboshaft_kw"],
                    altitude_m=altitude_m,
                    ambient_delta_c=self.ambient_delta_c,
                )
            else:
                fuel_flow_s = split["fuel_flow_kg_s"]
            fuel_step = fuel_flow_s * dt_climb
            total_fuel_burned += fuel_step
            current_mass -= fuel_step

            if is_hybrid and total_battery_kwh > 0:
                e_step_kwh = (split["p_battery_draw_kw"] * dt_climb) / 3600.0
                battery_energy_used_kwh += e_step_kwh
                energy_by_phase["climb"] += e_step_kwh
                battery_soc = max(0.0, 1.0 - (battery_energy_used_kwh / total_battery_kwh))

            altitude_m += climb_rate_mps * dt_climb
            distance_m += v_climb_mps * math.cos(gamma) * dt_climb
            t += dt_climb

            v_tas_kt = v_climb_mps * 1.94384
            v_ias_kt = v_tas_kt * math.sqrt(atm["sigma"])

            profile.append(
                {
                    "time_s": round(t, 1),
                    "phase": "climb",
                    "distance_km": round(distance_m / 1000.0, 3),
                    "altitude_ft": round(altitude_m * 3.28084, 0),
                    "altitude_agl_ft": round((altitude_m - origin_alt_m) * 3.28084, 0),
                    "airspeed_kt": round(v_ias_kt, 1),
                    "airspeed_ias_kt": round(v_ias_kt, 1),
                    "airspeed_tas_kt": round(v_tas_kt, 1),
                    "airspeed_mps": round(v_climb_mps, 1),
                    "pitch_deg": round(math.degrees(gamma) + 3.0, 1),
                    "roll_deg": 0.0,
                    "climb_rate_fpm": round(climb_rate_mps * 196.85, 0),
                    "turboshaft_power_kw": round(split["p_shaft_turboshaft_kw"], 0),
                    "electric_power_kw": round(split["p_shaft_electric_kw"], 0),
                    "fuel_flow_kg_hr": round(fuel_flow_s * 3600.0, 1),
                    "fuel_burned_kg": round(total_fuel_burned, 1),
                    "battery_soc_pct": round(battery_soc * 100.0, 1),
                    "waste_heat_kw": round(split["waste_heat_kw"], 1),
                    "gear_extended": False,
                }
            )

        # 3. Cruise Segment
        total_dist_m = self.route.stage_distance_km * 1000.0
        # Descent distance based on elevation difference
        alt_to_descend_m = max(500.0, target_cruise_alt_m - dest_alt_m)
        descent_dist_m = alt_to_descend_m * 3.0 * 6.076  # 3nm per 1000ft rule
        cruise_dist_target_m = max(distance_m + 10000.0, total_dist_m - descent_dist_m)

        v_cruise_mps = self.specs.nominal_cruise_tas_kt * 0.514444  # ~141.5 m/s
        dt_cruise = 30.0

        while distance_m < cruise_dist_target_m:
            atm = get_atmosphere(target_cruise_alt_m, self.ambient_delta_c)
            rho = atm["density_kg_m3"]

            q = 0.5 * rho * (v_cruise_mps**2)
            cl = (current_mass * G0) / (q * self.specs.wing_area_m2)
            cd = self.specs.cd0_clean + (cl**2) / (math.pi * self.specs.aspect_ratio * self.specs.oswald_efficiency)
            drag_n = q * self.specs.wing_area_m2 * cd

            thrust_req_n = drag_n
            p_shaft_req_kw = (thrust_req_n * v_cruise_mps) / (self.specs.propeller_efficiency_cruise * 1000.0)

            split = pt.compute_instantaneous_power_split(p_shaft_req_kw, "cruise", battery_soc)
            if self.physics_mode == "phase2":
                fuel_flow_s = self.engine_map.compute_fuel_flow_kg_s(
                    shaft_power_kw=split["p_shaft_turboshaft_kw"],
                    altitude_m=target_cruise_alt_m,
                    ambient_delta_c=self.ambient_delta_c,
                )
            else:
                fuel_flow_s = split["fuel_flow_kg_s"]
            fuel_step = fuel_flow_s * dt_cruise
            total_fuel_burned += fuel_step
            current_mass -= fuel_step

            if is_hybrid and total_battery_kwh > 0:
                e_step_kwh = (split["p_battery_draw_kw"] * dt_cruise) / 3600.0
                battery_energy_used_kwh += e_step_kwh
                energy_by_phase["cruise"] += e_step_kwh
                battery_soc = max(0.0, 1.0 - (battery_energy_used_kwh / total_battery_kwh))

            distance_m += v_cruise_mps * dt_cruise
            t += dt_cruise

            v_tas_kt = v_cruise_mps * 1.94384
            v_ias_kt = v_tas_kt * math.sqrt(atm["sigma"])

            profile.append(
                {
                    "time_s": round(t, 1),
                    "phase": "cruise",
                    "distance_km": round(distance_m / 1000.0, 3),
                    "altitude_ft": round(target_cruise_alt_m * 3.28084, 0),
                    "altitude_agl_ft": round((target_cruise_alt_m - ((origin_alt_m + dest_alt_m) / 2.0)) * 3.28084, 0),
                    "airspeed_kt": round(v_ias_kt, 1),
                    "airspeed_ias_kt": round(v_ias_kt, 1),
                    "airspeed_tas_kt": round(v_tas_kt, 1),
                    "airspeed_mps": round(v_cruise_mps, 1),
                    "pitch_deg": 2.2,
                    "roll_deg": 0.0,
                    "climb_rate_fpm": 0.0,
                    "turboshaft_power_kw": round(split["p_shaft_turboshaft_kw"], 0),
                    "electric_power_kw": round(split["p_shaft_electric_kw"], 0),
                    "fuel_flow_kg_hr": round(fuel_flow_s * 3600.0, 1),
                    "fuel_burned_kg": round(total_fuel_burned, 1),
                    "battery_soc_pct": round(battery_soc * 100.0, 1),
                    "waste_heat_kw": round(split["waste_heat_kw"], 1),
                    "gear_extended": False,
                }
            )

        # 4. Descent & Landing Segment (descending to destination airport elevation)
        v_descent_mps = 100.0  # ~195 KIAS
        descent_rate_mps = 7.0  # ~1,400 ft/min
        dt_descent = 20.0

        while altitude_m > dest_alt_m + 15.0:
            altitude_m = max(dest_alt_m, altitude_m - descent_rate_mps * dt_descent)
            distance_m += v_descent_mps * dt_descent
            t += dt_descent

            p_idle_kw = 450.0
            split = pt.compute_instantaneous_power_split(p_idle_kw, "descent", battery_soc)
            if self.physics_mode == "phase2":
                fuel_flow_s = self.engine_map.compute_fuel_flow_kg_s(
                    shaft_power_kw=split["p_shaft_turboshaft_kw"],
                    altitude_m=altitude_m,
                    ambient_delta_c=self.ambient_delta_c,
                )
            else:
                fuel_flow_s = split["fuel_flow_kg_s"]
            fuel_step = fuel_flow_s * dt_descent
            total_fuel_burned += fuel_step
            current_mass -= fuel_step

            atm_desc = get_atmosphere(altitude_m, self.ambient_delta_c)
            v_tas_kt = v_descent_mps * 1.94384
            v_ias_kt = v_tas_kt * math.sqrt(atm_desc["sigma"])

            profile.append(
                {
                    "time_s": round(t, 1),
                    "phase": "descent" if altitude_m > dest_alt_m + 300.0 else "landing",
                    "distance_km": round(distance_m / 1000.0, 3),
                    "altitude_ft": round(altitude_m * 3.28084, 0),
                    "altitude_agl_ft": round((altitude_m - dest_alt_m) * 3.28084, 0),
                    "airspeed_kt": round(v_ias_kt, 1),
                    "airspeed_ias_kt": round(v_ias_kt, 1),
                    "airspeed_tas_kt": round(v_tas_kt, 1),
                    "airspeed_mps": round(v_descent_mps, 1),
                    "pitch_deg": -1.8 if altitude_m > dest_alt_m + 300.0 else 3.5,
                    "roll_deg": 0.0,
                    "climb_rate_fpm": -round(descent_rate_mps * 196.85, 0),
                    "turboshaft_power_kw": round(split["p_shaft_turboshaft_kw"], 0),
                    "electric_power_kw": 0.0,
                    "fuel_flow_kg_hr": round(split["fuel_flow_kg_hr"], 1),
                    "fuel_burned_kg": round(total_fuel_burned, 1),
                    "battery_soc_pct": round(battery_soc * 100.0, 1),
                    "waste_heat_kw": 0.0,
                    "gear_extended": True if altitude_m < dest_alt_m + 500.0 else False,
                }
            )

        return {
            "total_fuel_burned_kg": total_fuel_burned,
            "battery_energy_consumed_kwh": battery_energy_used_kwh,
            "energy_kwh_by_phase": {k: round(v, 1) for k, v in energy_by_phase.items()},
            "takeoff_roll_m": takeoff_roll_m,
            "flight_duration_min": t / 60.0,
            "profile": profile,
        }
