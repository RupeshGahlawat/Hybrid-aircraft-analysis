"""
Turboshaft Engine Performance & Off-Design BSFC Map.
Reference: Pratt & Whitney Canada PW127M Turboshaft.
Models:
1. Thermodynamic flat-rating up to 30°C (ISA + 15°C) and hot-day temperature lapse.
2. Density altitude lapse on available shaft power.
3. Part-load Brake Specific Fuel Consumption (BSFC) penalty curve reflecting
   compressor off-design operation and reduced cycle pressure ratio during hybrid throttling.
"""
from dataclasses import dataclass

from .atmosphere import get_atmosphere


@dataclass(frozen=True)
class TurboshaftEngineMap:
    engine_model: str = "PW127M"
    num_engines: int = 2
    rated_takeoff_power_kw: float = 1845.6   # 2,475 SHP normal takeoff rating per engine
    apr_takeoff_power_kw: float = 2050.7     # 2,750 SHP Automatic Power Reserve (APR / OEI rating)
    flat_rating_temp_c: float = 30.0         # Flat-rated up to 30°C (ISA + 15°C at sea level)
    hot_day_derate_rate_per_c: float = 0.009 # 0.9% shaft power reduction per °C above flat rating

    # BSFC baseline ratings (kg Jet-A1 per kWh shaft work)
    bsfc_takeoff_rated_kg_kwh: float = 0.275 # High power / high pressure ratio setting
    bsfc_cruise_nominal_kg_kwh: float = 0.295 # Nominal cruise (~60-70% power setting)
    bsfc_idle_kg_kwh: float = 0.480          # Ground/flight idle low-efficiency setting

    def compute_available_power_kw(
        self,
        altitude_m: float = 0.0,
        ambient_delta_c: float = 0.0,
        use_apr: bool = False
    ) -> float:
        """
        Computes maximum available shaft power per engine (kW) taking into account
        altitude density ratio and ambient hot-day flat-rating.
        """
        atm = get_atmosphere(altitude_m, ambient_delta_c)
        oat_c = atm["temperature_c"]
        p = atm["pressure_pa"]

        base_power = self.apr_takeoff_power_kw if use_apr else self.rated_takeoff_power_kw

        # Temperature derating applies only above the flat-rating limit (30°C)
        if oat_c > self.flat_rating_temp_c:
            temp_derate_factor = max(0.65, 1.0 - self.hot_day_derate_rate_per_c * (oat_c - self.flat_rating_temp_c))
        else:
            temp_derate_factor = 1.0

        # Altitude lapse: thermodynamic shaft power scales with ambient atmospheric pressure ratio
        # Flat-rated engines maintain full rated torque at sea level
        p_ratio_alt = (p / 101325.0) ** 0.85

        return float(base_power * temp_derate_factor * p_ratio_alt)

    def compute_bsfc_kg_per_kwh(
        self,
        shaft_power_demanded_kw: float,
        altitude_m: float = 0.0,
        ambient_delta_c: float = 0.0
    ) -> float:
        """
        Computes the effective Brake Specific Fuel Consumption (kg/kWh) as a function of
        the instantaneous power fraction (P_demanded / P_max_available).
        Captures the part-load thermal efficiency penalty when the gas turbine is throttled back.
        """
        p_avail = self.compute_available_power_kw(altitude_m, ambient_delta_c, use_apr=False)
        if p_avail <= 0.0:
            return self.bsfc_idle_kg_kwh

        # Normalize demanded power per engine if total aircraft power is supplied
        p_demanded_eng = shaft_power_demanded_kw / self.num_engines if shaft_power_demanded_kw > p_avail * 1.2 else shaft_power_demanded_kw
        load_fraction = max(0.10, min(1.0, p_demanded_eng / p_avail))

        # High power regime (load >= 0.85): Peak thermal efficiency, BSFC ~ 0.275 kg/kWh
        if load_fraction >= 0.85:
            ratio = (1.0 - load_fraction) / 0.15
            return float(self.bsfc_takeoff_rated_kg_kwh + ratio * (self.bsfc_cruise_nominal_kg_kwh - self.bsfc_takeoff_rated_kg_kwh))
        elif load_fraction >= 0.50:
            # Nominal cruise / moderate part-load: BSFC ~ 0.295 to 0.315 kg/kWh
            # Polynomial curve fit matching typical turboshaft part-load curves (Mattingly / Walsh & Fletcher)
            excess_drop = 0.85 - load_fraction
            return float(self.bsfc_cruise_nominal_kg_kwh + 0.08 * (excess_drop ** 1.3))
        else:
            # Deep part-load (hybrid high-electric boost): cycle pressure ratio drops significantly
            deep_drop = 0.50 - load_fraction
            part_load_bsfc = self.bsfc_cruise_nominal_kg_kwh + 0.035 + 0.35 * (deep_drop ** 1.5)
            return float(min(self.bsfc_idle_kg_kwh, part_load_bsfc))

    def compute_fuel_flow_kg_s(
        self,
        shaft_power_kw: float,
        altitude_m: float = 0.0,
        ambient_delta_c: float = 0.0
    ) -> float:
        """
        Instantaneous fuel flow rate (kg/s) for a given power demand.
        """
        bsfc = self.compute_bsfc_kg_per_kwh(shaft_power_kw, altitude_m, ambient_delta_c)
        return (shaft_power_kw * bsfc) / 3600.0

ENGINE_MAP_PW127M = TurboshaftEngineMap()
