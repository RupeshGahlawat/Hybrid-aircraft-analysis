"""
Propeller Aerodynamic & Takeoff Ground Roll Model.
Reference: Hamilton Sundstrand 568F 6-Blade Propeller (Diameter D = 3.93 m).
Models thrust and efficiency as a function of advance ratio (J = V / (n * D)),
calibrated to certified ATR 72-600 static takeoff thrust (~44 kN total / 22 kN per engine)
and takeoff distance to 35 ft screen height (~1,279 m published FCOM).
"""
import math
from dataclasses import dataclass

from .aircraft_specs import ATR72_BASELINE, AircraftBaseline
from .atmosphere import G0, get_atmosphere


@dataclass(frozen=True)
class PropellerModel:
    diameter_m: float = 3.93                 # Hamilton Sundstrand 568F diameter
    rpm_takeoff: float = 1200.0              # Nominal propeller rotation speed (RPM)
    num_blades: int = 6                      # Advanced composite blades
    static_thrust_per_engine_n: float = 22000.0  # Certified static thrust per PW127M at sea level ISA (44 kN total)
    max_efficiency_cruise: float = 0.85      # Peak propeller efficiency in cruise

    @property
    def rps_takeoff(self) -> float:
        """Propeller revolutions per second (n = RPM / 60)."""
        return self.rpm_takeoff / 60.0       # 20.0 rev/s

    def compute_advance_ratio(self, true_airspeed_mps: float) -> float:
        """
        Computes propeller advance ratio J = V / (n * D).
        """
        n = self.rps_takeoff
        return max(0.0, true_airspeed_mps / (n * self.diameter_m))

    def compute_efficiency(self, advance_ratio_j: float) -> float:
        """
        Propeller efficiency as a function of advance ratio J.
        Calibrated against typical variable-pitch turboprop J-curves:
        - J = 0.0: eta ~ 0.0 (static)
        - J = 0.4 (climb): eta ~ 0.78 - 0.81
        - J = 0.8 - 1.0 (cruise): eta ~ 0.84 - 0.85
        """
        j = advance_ratio_j
        if j <= 0.0:
            return 0.0
        # Smooth asymptotic fit representing governor-controlled variable pitch blade
        # Peak at J ~ 0.85
        eta = self.max_efficiency_cruise * (1.0 - math.exp(-2.8 * j)) * (1.0 - 0.05 * max(0.0, j - 0.9)**2)
        return max(0.0, min(self.max_efficiency_cruise, eta))

    def compute_thrust_n(
        self,
        shaft_power_kw_per_engine: float,
        true_airspeed_mps: float,
        air_density_kg_m3: float = 1.225
    ) -> float:
        """
        Computes thrust per engine (Newtons) across the entire flight envelope,
        smoothly blending static thrust at low speed into P * eta / V at high speed.
        """
        v = max(0.0, true_airspeed_mps)
        rho_ratio = air_density_kg_m3 / 1.225

        # Static thrust component (scales with density and shaft power fraction)
        p_ref_kw = 1845.6  # PW127M normal takeoff rating
        p_ratio = max(0.0, shaft_power_kw_per_engine / p_ref_kw)

        # Blade element static thrust correlation: T_static ~ (P * rho * D^2)^(2/3)
        t_static = self.static_thrust_per_engine_n * (p_ratio ** 0.75) * (rho_ratio ** 0.5)

        j = self.compute_advance_ratio(v)
        eta = self.compute_efficiency(j)

        # High speed aerodynamic thrust: T = P_shaft * eta / V
        if v >= 15.0:
            t_dynamic = (shaft_power_kw_per_engine * 1000.0 * eta) / v
            # Smooth blend between 15 m/s and 30 m/s
            if v >= 30.0:
                return t_dynamic
            weight = (v - 15.0) / 15.0
            return float((1.0 - weight) * t_static * (1.0 - 0.4 * j) + weight * t_dynamic)
        else:
            # Low speed / static regime: thrust decreases slightly with forward speed
            return float(t_static * max(0.2, 1.0 - 0.45 * j - 0.20 * (j ** 2)))

def integrate_takeoff_distance(
    mass_kg: float,
    total_shaft_power_kw: float,
    specs: AircraftBaseline = ATR72_BASELINE,
    altitude_m: float = 0.0,
    ambient_delta_c: float = 0.0,
    runway_friction_mu: float = 0.025,
    prop_model: PropellerModel = PropellerModel()
) -> dict[str, float]:
    """
    Integrates the full takeoff distance to 35 ft (10.7 m) screen height:
    1. Ground roll: 0 m/s to Rotation speed V_R = 1.05 * V_stall
    2. Rotation & transition: V_R to V_LOF (Liftoff speed)
    3. Airborne climb segment: V_LOF to 35 ft screen height at obstacle climb gradient
    """
    atm = get_atmosphere(altitude_m, ambient_delta_c)
    rho = atm["density_kg_m3"]

    # Stall speed in takeoff configuration (Flaps 15, CL_max = 2.20)
    cl_max_to = specs.cl_max_takeoff
    v_stall = math.sqrt((2.0 * mass_kg * G0) / (rho * specs.wing_area_m2 * cl_max_to))

    # CS-25 regulation takeoff speeds
    v_r = 1.05 * v_stall      # Rotation speed (~55.0 m/s or ~107 KIAS at basic MTOW)
    v_lof = 1.10 * v_stall    # Liftoff speed
    v2 = 1.20 * v_stall       # Takeoff safety speed at 35 ft

    dt = 0.5                  # Integration time step (s)
    v = 0.0
    s_ground = 0.0
    t_ground = 0.0
    p_per_engine = total_shaft_power_kw / specs.num_engines

    # Phase 1: Ground run to V_R
    cl_ground = 0.55          # Ground roll lift coefficient with Flaps 15
    cd_ground = specs.cd0_takeoff_flaps + (cl_ground ** 2) / (math.pi * specs.aspect_ratio * specs.oswald_efficiency)

    while v < v_r:
        q = 0.5 * rho * (v ** 2)
        lift_n = q * specs.wing_area_m2 * cl_ground
        drag_n = q * specs.wing_area_m2 * cd_ground

        thrust_per_eng = prop_model.compute_thrust_n(p_per_engine, v, rho)
        thrust_total_n = thrust_per_eng * specs.num_engines

        normal_force = max(0.0, mass_kg * G0 - lift_n)
        rolling_res_n = runway_friction_mu * normal_force

        a = (thrust_total_n - drag_n - rolling_res_n) / mass_kg
        v += a * dt
        s_ground += v * dt
        t_ground += dt

    # Phase 2: Rotation & transition to V_LOF (~3 seconds)
    t_rotation = 2.5
    s_rotation = v_r * t_rotation + 0.5 * 1.5 * (t_rotation ** 2)
    s_liftoff = s_ground + s_rotation

    # Phase 3: Airborne distance to 35 ft (10.668 m) screen height
    h_screen_m = 10.668
    # Average all-engine climb gradient at V2: gamma = (T - D) / W
    q_v2 = 0.5 * rho * (v2 ** 2)
    cl_v2 = (mass_kg * G0) / (q_v2 * specs.wing_area_m2)
    cd_v2 = specs.cd0_clean + 0.015 + (cl_v2 ** 2) / (math.pi * specs.aspect_ratio * specs.oswald_efficiency)
    drag_v2 = q_v2 * specs.wing_area_m2 * cd_v2
    thrust_v2 = prop_model.compute_thrust_n(p_per_engine, v2, rho) * specs.num_engines

    gamma_to = max(0.035, (thrust_v2 - drag_v2) / (mass_kg * G0))
    s_airborne_all_engine = h_screen_m / gamma_to
    tod_all_engine_unfactored = s_liftoff + s_airborne_all_engine
    tod_all_engine_factored = tod_all_engine_unfactored * 1.15

    # Phase 4: CS-25 / FAR Part 25 Certified Balanced Field Length (OEI at V1):
    # Under CS-25.113, published Takeoff Distance is governed by an engine failure at V1
    # with the remaining engine operating at APR (2,050.7 kW) and propeller feathered.
    # Second-segment climb gradient with OEI:
    thrust_v2_oei = prop_model.compute_thrust_n(specs.apr_power_kw_per_engine, v2, rho)
    drag_v2_oei = q_v2 * specs.wing_area_m2 * (cd_v2 + 0.0025)
    gamma_oei = max(0.024, (thrust_v2_oei - drag_v2_oei) / (mass_kg * G0))
    s_airborne_oei = h_screen_m / gamma_oei

    # Ground acceleration penalty from V1 to VR with single engine: ~110 m extra ground roll
    tod_oei_continued = s_ground + 110.0 + s_rotation + s_airborne_oei

    # Certified Takeoff Distance per CS-25 is max(1.15 * TOD_AEO, TOD_OEI)
    certified_tod_m = max(tod_all_engine_factored, tod_oei_continued)

    return {
        "v_stall_mps": v_stall,
        "v_stall_kias": v_stall * 1.94384,
        "v_r_mps": v_r,
        "v_r_kias": v_r * 1.94384,
        "v_lof_mps": v_lof,
        "v2_mps": v2,
        "v2_kias": v2 * 1.94384,
        "ground_roll_m": s_ground,
        "liftoff_distance_m": s_liftoff,
        "airborne_distance_to_35ft_m": s_airborne_all_engine,
        "all_engine_takeoff_distance_m": tod_all_engine_unfactored,
        "factored_all_engine_distance_m": tod_all_engine_factored,
        "oei_takeoff_distance_m": tod_oei_continued,
        "total_takeoff_distance_m": certified_tod_m,
        "climb_gradient_pct": gamma_to * 100.0,
        "oei_climb_gradient_pct": gamma_oei * 100.0,
        "t_ground_s": t_ground
    }
