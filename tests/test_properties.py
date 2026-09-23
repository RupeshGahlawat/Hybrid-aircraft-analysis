"""
Property-Based Tests for AeroHybrid Physics Models using Hypothesis.
Enforces physical invariants across continuous ranges of inputs.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.sim_core.atmosphere import get_atmosphere
from backend.sim_core.propulsion import HybridPhaseSchedule, HybridPowertrain
from backend.sim_core.weight_loop import size_aircraft_mass


# 1. Atmospheric Invariants
@given(
    alt1=st.floats(min_value=0.0, max_value=10000.0),
    delta_h=st.floats(min_value=100.0, max_value=1000.0),
    delta_t=st.floats(min_value=-20.0, max_value=35.0),
)
@settings(max_examples=50)
def test_atmosphere_monotonic_density_lapse(alt1: float, delta_h: float, delta_t: float):
    """Air density must strictly decrease with increasing altitude."""
    alt2 = min(11000.0, alt1 + delta_h)
    atm1 = get_atmosphere(alt1, delta_t_c=delta_t)
    atm2 = get_atmosphere(alt2, delta_t_c=delta_t)
    assert atm2["density_kg_m3"] < atm1["density_kg_m3"]
    assert atm2["pressure_pa"] < atm1["pressure_pa"]


# 2. Conservation of Power Invariant
@given(
    power_req_kw=st.floats(min_value=500.0, max_value=3500.0),
    hp_takeoff=st.floats(min_value=0.0, max_value=0.50),
    soc=st.floats(min_value=0.25, max_value=1.0),
)
@settings(max_examples=50)
def test_power_split_conservation(power_req_kw: float, hp_takeoff: float, soc: float):
    """The sum of shaft turboshaft power and shaft electric power must equal power required."""
    sched = HybridPhaseSchedule(takeoff=hp_takeoff, climb=hp_takeoff, cruise=0.0, descent=0.0)
    pt = HybridPowertrain(hp_schedule=sched)
    split = pt.compute_instantaneous_power_split(power_req_kw, "takeoff", battery_soc=soc)

    total_shaft = split["p_shaft_turboshaft_kw"] + split["p_shaft_electric_kw"]
    assert pytest.approx(total_shaft, rel=1e-5) == power_req_kw


# 3. Structural Limits Invariant
@given(
    hp_val=st.floats(min_value=0.0, max_value=0.40),
    batt_wh_kg=st.floats(min_value=250.0, max_value=500.0),
    distance_km=st.floats(min_value=100.0, max_value=600.0),
)
@settings(max_examples=40)
def test_sizing_structural_invariants(hp_val: float, batt_wh_kg: float, distance_km: float):
    """The sizing loop must always satisfy MTOW, MZFW, and MLW boundaries."""
    res = size_aircraft_mass(
        hp_fraction=hp_val, battery_wh_per_kg=batt_wh_kg, stage_distance_km=distance_km, nominal_pax=70
    )
    # Check all three limits with 0.5 kg numerical slack
    assert res.mtow_calculated_kg <= res.mtow_limit_kg + 0.5
    assert res.mzfw_calculated_kg <= res.mzfw_limit_kg + 0.5
    assert res.mlw_calculated_kg <= res.mlw_limit_kg + 0.5
    assert res.passengers_carried <= 70
