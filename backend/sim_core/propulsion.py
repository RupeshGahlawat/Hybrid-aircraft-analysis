"""
Parallel Hybrid-Electric Propulsion (HEP) Model.
Models the mechanical coupling of turboshaft and electric motor driving the reduction gearbox,
accounting for motor power density, inverter efficiency, battery mass, discharge C-rate,
and Thermal Management System (TMS) heat rejection.
Reference engine: Pratt & Whitney Canada PW127M (2x 2,475 SHP / 1,845.6 kW normal takeoff rating).
"""

from dataclasses import dataclass

from .aircraft_specs import ATR72_BASELINE


@dataclass(frozen=True)
class HybridPhaseSchedule:
    """Per-phase degree of hybridization of shaft power H_P."""

    takeoff: float = 0.30
    climb: float = 0.30
    cruise: float = 0.00
    descent: float = 0.00


@dataclass
class HybridTechParams:
    battery_specific_energy_wh_per_kg: float = (
        400.0  # Pack level (Wh/kg): 250-300 (baseline) to 600 (future solid state)
    )
    battery_usable_soc_min: float = 0.20  # Minimum Reserve SOC (20%)
    battery_max_c_rate: float = 4.0  # Max continuous discharge rate (4C)
    battery_roundtrip_efficiency: float = 0.95  # Electrochemical discharge efficiency

    motor_power_density_kw_per_kg: float = 6.0  # Electric motor power-to-weight ratio (kW/kg)
    motor_efficiency: float = 0.96  # Electric to shaft mechanical efficiency

    inverter_power_density_kw_per_kg: float = 14.0  # Silicon Carbide (SiC) inverter power density (kW/kg)
    inverter_efficiency: float = 0.985  # Inverter electrical efficiency

    cabling_and_protection_factor: float = 0.12  # 12% extra mass for HV wiring, contactors, fusing
    tms_specific_mass_kg_per_kw_th: float = 0.15  # Thermal Management System mass per kW waste heat rejected
    enable_engine_downsizing: bool = False  # True for clean-sheet, False for airframe retrofit


class HybridPowertrain:
    def __init__(
        self,
        hp_schedule: float | HybridPhaseSchedule = 0.30,
        tech: HybridTechParams | None = None,
        hp_fraction: float | None = None,
    ):
        """
        hp_schedule: Either a single float H_P (applied during takeoff and climb)
                     or a HybridPhaseSchedule specifying H_P per flight phase.
        hp_fraction: Backward compatibility alias for hp_schedule.
        """
        if hp_fraction is not None:
            hp_schedule = hp_fraction

        if isinstance(hp_schedule, (int, float)):
            hp_val = max(0.0, min(0.60, float(hp_schedule)))
            self.schedule = HybridPhaseSchedule(takeoff=hp_val, climb=hp_val, cruise=0.0, descent=0.0)
            self.hp_fraction = hp_val
        else:
            self.schedule = hp_schedule
            self.hp_fraction = max(hp_schedule.takeoff, hp_schedule.climb)

        self.tech = tech if tech is not None else HybridTechParams()

        # Max total installed takeoff shaft power for both PW127M engines (2 x 1,845.6 kW = 3,691.2 kW)
        self.total_installed_power_kw = ATR72_BASELINE.num_engines * ATR72_BASELINE.takeoff_power_kw_per_engine

        # Sizing electric motor to satisfy peak scheduled H_P (typically takeoff or climb)
        max_hp = max(self.schedule.takeoff, self.schedule.climb, self.schedule.cruise)
        self.electric_power_per_engine_kw = (self.total_installed_power_kw * max_hp) / ATR72_BASELINE.num_engines
        self.turboshaft_power_per_engine_kw = (
            ATR72_BASELINE.takeoff_power_kw_per_engine - self.electric_power_per_engine_kw
        )

        # Sizing powertrain component weights
        self.weights = self._calculate_powertrain_weights()

    def _calculate_powertrain_weights(self) -> dict[str, float]:
        total_elec_kw = self.electric_power_per_engine_kw * ATR72_BASELINE.num_engines

        if total_elec_kw <= 0.0:
            return {
                "motors_kg": 0.0,
                "inverters_kg": 0.0,
                "cabling_kg": 0.0,
                "tms_kg": 0.0,
                "turboshaft_saving_kg": 0.0,
                "powertrain_dry_delta_kg": 0.0,
            }

        # Motor mass (two motors, one per nacelle)
        motors_mass = total_elec_kw / self.tech.motor_power_density_kw_per_kg

        # Inverter mass (two dual-inverter units)
        inverters_mass = total_elec_kw / self.tech.inverter_power_density_kw_per_kg

        # Cabling, HV disconnects, contactors, pre-charge resistors
        cabling_mass = (motors_mass + inverters_mass) * self.tech.cabling_and_protection_factor

        # Maximum waste heat generated during peak electric draw:
        eta_combined = self.tech.motor_efficiency * self.tech.inverter_efficiency
        waste_heat_kw = total_elec_kw * (1.0 - eta_combined) / eta_combined
        tms_mass = waste_heat_kw * self.tech.tms_specific_mass_kg_per_kw_th

        # Turboshaft downsizing mass credit:
        # In a retrofit, existing PW127M cores are retained (saving = 0).
        # In a clean-sheet engine design, downsizing credit is allowed if enabled.
        turboshaft_saving_kg = 0.0
        if self.tech.enable_engine_downsizing:
            turboshaft_saving_kg = total_elec_kw * 0.22

        powertrain_dry_delta = (motors_mass + inverters_mass + cabling_mass + tms_mass) - turboshaft_saving_kg

        return {
            "motors_kg": motors_mass,
            "inverters_kg": inverters_mass,
            "cabling_kg": cabling_mass,
            "tms_kg": tms_mass,
            "turboshaft_saving_kg": turboshaft_saving_kg,
            "powertrain_dry_delta_kg": max(0.0, powertrain_dry_delta),
        }

    def compute_instantaneous_power_split(
        self, power_required_kw: float, phase: str, battery_soc: float
    ) -> dict[str, float]:
        """
        Splits instantaneous mechanical shaft power required between turboshaft and electric motor
        based on the per-phase HybridPhaseSchedule.
        """
        min_soc = self.tech.battery_usable_soc_min
        can_boost = battery_soc > min_soc

        if phase == "takeoff":
            target_hp = self.schedule.takeoff
        elif phase == "climb":
            target_hp = self.schedule.climb
        elif phase == "cruise":
            target_hp = self.schedule.cruise
        elif phase == "descent":
            target_hp = self.schedule.descent
        else:
            target_hp = 0.0

        hp_applied = target_hp if can_boost else 0.0

        p_shaft_electric = power_required_kw * hp_applied
        p_shaft_turboshaft = power_required_kw - p_shaft_electric

        # Electrical draw from battery pack accounting for motor and inverter efficiencies
        if p_shaft_electric > 0.0:
            p_battery_draw_kw = p_shaft_electric / (self.tech.motor_efficiency * self.tech.inverter_efficiency)
        else:
            p_battery_draw_kw = 0.0

        # Specific Fuel Consumption (BSFC)
        bsfc = (
            ATR72_BASELINE.bsfc_takeoff_kg_per_kwh
            if phase in ["takeoff", "climb"]
            else ATR72_BASELINE.bsfc_cruise_kg_per_kwh
        )

        # Instantaneous fuel flow rate (kg/s)
        fuel_flow_kg_s = (p_shaft_turboshaft * bsfc) / 3600.0

        # Instantaneous heat generated (kW thermal)
        waste_heat_kw = p_battery_draw_kw - p_shaft_electric

        return {
            "p_shaft_turboshaft_kw": p_shaft_turboshaft,
            "p_shaft_electric_kw": p_shaft_electric,
            "p_battery_draw_kw": p_battery_draw_kw,
            "actual_hp": hp_applied,
            "fuel_flow_kg_s": fuel_flow_kg_s,
            "fuel_flow_kg_hr": fuel_flow_kg_s * 3600.0,
            "waste_heat_kw": waste_heat_kw,
        }
