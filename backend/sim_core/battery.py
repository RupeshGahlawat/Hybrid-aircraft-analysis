"""
Aviation Battery Pack Sizing, C-Rate & Degradation Model.
Sizes battery mass based on the dual constraint:
1. Energy-constrained mass: m_energy = E_usable / (DoD * EOL * e_pack)
2. Power-constrained mass: m_power = P_max / (C_max * e_pack)
Includes:
- Pack structural & BMS overhead factor (+18% over bare cells)
- End-of-Life (EOL) 80% capacity retention sizing buffer
- Discharge C-rate limits (continuous 3.5C, peak 5.0C)
- Ambient temperature derating above 40°C
- Clear separation between Cell-Level vs. Pack-Level specific energy.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class BatteryConfig:
    specific_energy_pack_wh_kg: float = 280.0    # Pack-level usable density (baseline ~250-280 Wh/kg; future 400-600)
    is_pack_level: bool = True                   # Flag confirming pack-level density
    cell_to_pack_mass_fraction: float = 0.82    # 82% cell mass, 18% structure, cooling plates, BMS, busbars
    usable_dod: float = 0.80                    # 80% usable depth of discharge (10% lower & 10% upper reserve)
    eol_capacity_fraction: float = 0.80         # Sized to achieve mission at 80% End-of-Life retention
    max_c_rate_continuous: float = 3.5          # Max continuous discharge rate
    max_c_rate_peak: float = 5.0                # Max 30-sec transient discharge rate
    temp_derate_threshold_c: float = 40.0       # Derate capacity buffer above 40°C

    @property
    def specific_energy_cell_wh_kg(self) -> float:
        """Equivalent bare cell specific energy."""
        if self.is_pack_level:
            return self.specific_energy_pack_wh_kg / self.cell_to_pack_mass_fraction
        return self.specific_energy_pack_wh_kg

def size_battery_pack(
    energy_demanded_usable_kwh: float,
    peak_power_demanded_kw: float,
    config: BatteryConfig = BatteryConfig(),
    ambient_temp_c: float = 25.0
) -> dict[str, Any]:
    """
    Sizes the battery pack mass as the MAX of energy-governed mass and power-governed mass,
    incorporating EOL degradation buffer and pack structural overhead.
    """
    e_pack = config.specific_energy_pack_wh_kg

    # Temperature derating factor for high ambient heat (e.g. North Indian summer > 40°C)
    temp_penalty = 1.0
    if ambient_temp_c > config.temp_derate_threshold_c:
        # 1.5% extra mass buffer per °C above 40°C for thermal margin / active coolant flow
        temp_penalty = 1.0 + 0.015 * (ambient_temp_c - config.temp_derate_threshold_c)

    # 1. Energy-governed mass:
    # Sized so that at End of Life (EOL SOH = 80%), with 80% usable DoD, it still delivers the full required mission kWh
    nameplate_capacity_kwh = energy_demanded_usable_kwh / (config.usable_dod * config.eol_capacity_fraction)
    m_energy_kg = (nameplate_capacity_kwh * 1000.0) / e_pack * temp_penalty

    # 2. Power-governed mass:
    # Power limit: P_max = m_batt * e_pack * C_peak / 1000
    # => m_power = P_max * 1000 / (C_peak * e_pack)
    c_peak = config.max_c_rate_peak
    m_power_kg = (peak_power_demanded_kw * 1000.0) / (c_peak * e_pack)

    # 3. Structural sizing: larger of the two constraints
    if m_energy_kg >= m_power_kg:
        sizing_driver = "ENERGY"
        final_mass_kg = m_energy_kg
    else:
        sizing_driver = "POWER"
        final_mass_kg = m_power_kg
        # If power-driven, the installed capacity is correspondingly larger
        nameplate_capacity_kwh = (final_mass_kg * e_pack) / 1000.0

    # Actual continuous C-rate at peak power
    actual_peak_c_rate = peak_power_demanded_kw / nameplate_capacity_kwh if nameplate_capacity_kwh > 0 else 0.0

    return {
        "battery_mass_kg": final_mass_kg,
        "nameplate_capacity_kwh": nameplate_capacity_kwh,
        "usable_capacity_kwh": nameplate_capacity_kwh * config.usable_dod,
        "m_energy_kg": m_energy_kg,
        "m_power_kg": m_power_kg,
        "sizing_driver": sizing_driver,
        "actual_peak_c_rate": actual_peak_c_rate,
        "is_c_rate_compliant": actual_peak_c_rate <= config.max_c_rate_peak,
        "specific_energy_pack_wh_kg": e_pack,
        "specific_energy_cell_wh_kg": config.specific_energy_cell_wh_kg
    }
