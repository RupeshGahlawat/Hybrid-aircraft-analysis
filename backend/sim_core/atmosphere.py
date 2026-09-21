"""
International Standard Atmosphere (ISA) Model with Hot & High Adjustments.
Calculates atmospheric temperature, pressure, density, and speed of sound up to 36,000 ft (troposphere).
Includes temperature offsets (e.g. +15°C to +30°C for Indian summer conditions).
"""

import math

# Sea level standard conditions
T0_ISA = 288.15  # Kelvin (15°C)
P0_ISA = 101325.0  # Pascals
RHO0_ISA = 1.225  # kg/m^3
G0 = 9.80665  # m/s^2
R_AIR = 287.05287  # J/(kg·K)
LAPSE_RATE = 0.0065  # K/m (Troposphere temperature lapse)
GAMMA = 1.4  # Heat capacity ratio for air


def get_atmosphere(altitude_m: float, delta_t_c: float = 0.0) -> dict:
    """
    Computes ambient atmospheric properties at given altitude (meters) with optional
    ambient temperature offset delta_t_c (Celsius/Kelvin above standard ISA).
    """
    altitude_m = max(0.0, min(altitude_m, 11000.0))  # Troposphere clamp

    # ISA standard temperature at altitude
    t_isa = T0_ISA - LAPSE_RATE * altitude_m

    # Pressure (independent of temperature offset at same geopotential altitude)
    p = P0_ISA * (1.0 - (LAPSE_RATE * altitude_m) / T0_ISA) ** (G0 / (R_AIR * LAPSE_RATE))

    # Actual temperature with hot-day offset
    t_actual = t_isa + delta_t_c

    # Actual air density
    rho = p / (R_AIR * t_actual)

    # Speed of sound
    speed_of_sound = math.sqrt(GAMMA * R_AIR * t_actual)

    # Density ratio (sigma)
    sigma = rho / RHO0_ISA

    return {
        "altitude_m": altitude_m,
        "altitude_ft": altitude_m * 3.28084,
        "temperature_k": t_actual,
        "temperature_c": t_actual - 273.15,
        "pressure_pa": p,
        "density_kg_m3": rho,
        "speed_of_sound_mps": speed_of_sound,
        "sigma": sigma,
    }


if __name__ == "__main__":
    sea_level = get_atmosphere(0.0)
    print("Sea Level Standard:", sea_level)
    fl200 = get_atmosphere(6096.0)  # ~20,000 ft
    print("FL200 Standard:", fl200)
    summer_delhi = get_atmosphere(200.0, delta_t_c=25.0)  # 40°C
    print("Delhi Hot Day:", summer_delhi)
