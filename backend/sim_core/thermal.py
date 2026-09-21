"""
Thermal Management System (TMS) Model.
Calculates real-time waste heat generation across electric motors, silicon carbide inverters,
and battery electrochemical internal losses (I^2*R).
Sizes cooling system mass (radiators, heat exchangers, pumps, coolant fluid)
proportional to peak heat load rejection requirements.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ThermalConfig:
    cooling_specific_mass_kg_per_kw_th: float = 0.15  # Mass per kW thermal rejected (active liquid cooling loop)
    ram_air_heat_exchanger_fraction: float = 0.40     # Fraction of radiator surface area embedded in nacelle ram ducts
    coolant_operating_temp_max_c: float = 75.0        # Max allowable loop temperature (for motor/inverter cooling)

def compute_instantaneous_heat_load_kw(
    shaft_power_electric_kw: float,
    battery_draw_power_kw: float,
    motor_efficiency: float = 0.96,
    inverter_efficiency: float = 0.985,
    battery_efficiency: float = 0.95
) -> dict[str, float]:
    """
    Computes instantaneous thermal dissipation (kW thermal) across powertrain components.
    """
    if shaft_power_electric_kw <= 0.0:
        return {
            "motor_heat_kw": 0.0,
            "inverter_heat_kw": 0.0,
            "battery_heat_kw": 0.0,
            "total_heat_load_kw": 0.0
        }

    # Motor loss: heat generated in stator windings and rotor magnets
    motor_heat_kw = shaft_power_electric_kw * (1.0 - motor_efficiency) / motor_efficiency

    # Inverter loss: heat generated in SiC MOSFET switches
    ac_power_kw = shaft_power_electric_kw / motor_efficiency
    dc_power_kw = ac_power_kw / inverter_efficiency
    inverter_heat_kw = dc_power_kw - ac_power_kw

    # Battery internal electrochemical dissipation (I^2 * R)
    battery_heat_kw = battery_draw_power_kw * (1.0 - battery_efficiency)

    total_heat_kw = motor_heat_kw + inverter_heat_kw + battery_heat_kw

    return {
        "motor_heat_kw": motor_heat_kw,
        "inverter_heat_kw": inverter_heat_kw,
        "battery_heat_kw": battery_heat_kw,
        "total_heat_load_kw": total_heat_kw
    }

def size_tms_mass(
    peak_heat_load_kw: float,
    config: ThermalConfig = ThermalConfig()
) -> float:
    """
    Sizes the total dry mass of the thermal management system (kg) based on peak heat load.
    """
    return max(0.0, peak_heat_load_kw * config.cooling_specific_mass_kg_per_kw_th)
