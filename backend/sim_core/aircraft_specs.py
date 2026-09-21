"""
ATR 72-600 Class Regional Turboprop Baseline Specifications.
Values calibrated against published ATR 72-600 Manufacturer Factsheet,
EASA Type Certificate Data Sheet (TCDS A.084, Issue 08),
and Pratt & Whitney Canada PW127M Turboshaft Engine Data.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AircraftBaseline:
    name: str = "ATR 72-600 Regional Turboprop"
    category: str = "CS-25 / FAR Part 25 Commuter/Regional"

    # Structural Mass Limits (kg) - Sources: ATR 72-600 Factsheet & EASA TCDS A.084
    # Basic / Standard vs High Gross Weight (Option)
    mtow_basic_kg: float = 22800.0  # Maximum Take-Off Weight (Basic)
    mtow_option_kg: float = 23000.0  # Maximum Take-Off Weight (Optional high-gross-weight)
    mtow_kg: float = 22800.0  # Active MTOW limit (defaults to basic)

    mlw_kg: float = 22350.0  # Maximum Landing Weight (structural limit)

    mzfw_basic_kg: float = 20800.0  # Maximum Zero Fuel Weight (Basic)
    mzfw_option_kg: float = 21000.0  # Maximum Zero Fuel Weight (Option)
    mzfw_kg: float = 20800.0  # Active MZFW limit (defaults to basic)

    oew_tech_spec_kg: float = 13010.0  # Operating Empty Weight (manufacturer bare spec)
    oew_in_service_kg: float = 13450.0  # Typical airline in-service OEW (crew, pantry, seats)
    oew_kg: float = 13450.0  # Active baseline OEW

    max_payload_kg: float = 7500.0  # Maximum structural payload capacity
    max_fuel_capacity_kg: float = 5000.0  # Standard twin-wing tank kerosene capacity (6,250 L)

    # Passenger configuration
    nominal_pax: int = 70
    max_pax: int = 72
    pax_unit_weight_kg: float = 95.0  # Passenger + checked/carry-on luggage (standard ICAO 80+15 kg)

    # Geometric and Aerodynamic specifications
    wing_area_m2: float = 61.0  # Wing reference area
    wingspan_m: float = 27.05  # Wing span
    aspect_ratio: float = 12.0  # High aspect ratio (b^2 / S = 27.05^2 / 61.0 = 12.00)
    oswald_efficiency: float = 0.84  # Oswald span efficiency factor (clean configuration)

    # Drag polar coefficients (Clean cruise configuration)
    # CD = CD0 + K * CL^2, where K = 1 / (pi * AR * e)
    cd0_clean: float = 0.0242
    cd0_takeoff_flaps: float = 0.0385  # Flaps 15 + landing gear down
    cd0_landing_flaps: float = 0.0550  # Flaps 30 + landing gear down
    cl_max_clean: float = 1.65
    cl_max_takeoff: float = 2.20
    cl_max_landing: float = 2.60

    # Conventional Propulsion (2x Pratt & Whitney Canada PW127M)
    engine_model: str = "PW127M"
    num_engines: int = 2
    takeoff_power_shp_per_engine: float = 2475.0  # Normal Takeoff SHP per engine (P&WC / ATR Factsheet)
    takeoff_power_kw_per_engine: float = 1845.6  # 2,475 SHP * 0.7457 kW/SHP
    apr_power_shp_per_engine: float = 2750.0  # Automatic Power Reserve (APR / OEI 10-min reserve)
    apr_power_kw_per_engine: float = 2050.7  # 2,750 SHP * 0.7457 kW/SHP
    max_continuous_power_kw: float = 1635.0  # Nominal climb / continuous shaft power (~2,192 shp)
    propeller_diameter_m: float = 3.93  # Hamilton Sundstrand 568F 6-blade propeller
    propeller_efficiency_takeoff: float = 0.72  # Low speed static/takeoff efficiency
    propeller_efficiency_climb: float = 0.81
    propeller_efficiency_cruise: float = 0.85

    # Engine Specific Fuel Consumption (SFC)
    # Brake Specific Fuel Consumption (BSFC) in kg of Jet-A1 per kWh
    bsfc_takeoff_kg_per_kwh: float = 0.275  # Takeoff rating
    bsfc_cruise_kg_per_kwh: float = 0.295  # Nominal cruise rating (~762 kg/h at FL200)

    # Operational limits
    max_cruise_alt_ft: float = 25000.0  # Certified service ceiling
    nominal_cruise_alt_ft: float = 20000.0  # FL200
    nominal_cruise_tas_kt: float = 275.0  # ~510 km/h or ~141.5 m/s True Airspeed
    takeoff_vr_kias: float = 108.0  # Nominal rotation speed
    approach_vapp_kias: float = 112.0  # Nominal approach speed


def get_aircraft_specs(weight_option: Literal["basic", "option"] = "basic") -> AircraftBaseline:
    """
    Returns aircraft baseline with either basic certified weight limits
    (MTOW 22,800 kg, MZFW 20,800 kg) or optional high-gross-weight package
    (MTOW 23,000 kg, MZFW 21,000 kg).
    """
    if weight_option == "option":
        return AircraftBaseline(mtow_kg=23000.0, mzfw_kg=21000.0, oew_kg=13500.0)
    return AircraftBaseline(mtow_kg=22800.0, mzfw_kg=20800.0, oew_kg=13450.0)


ATR72_BASELINE = get_aircraft_specs("basic")
