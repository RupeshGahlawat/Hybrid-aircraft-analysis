"""
Direct Operating Cost (DOC) & Turnaround Charging Infrastructure Model.
Evaluates the economic feasibility of parallel hybrid retrofits accounting for:
1. Jet-A1 fuel consumption cost ($/kg).
2. Ground grid recharge electricity cost ($/kWh).
3. Battery pack cycle-life amortization ($/flight cycle).
4. Revenue lost due to passenger seat shedding ($/shed seat).
5. Turboshaft engine maintenance savings due to reduced peak temperature stress.
6. Ground charger turnaround power requirements (kW) as a function of turnaround time (TAT).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CostParameters:
    fuel_price_usd_per_kg: float = 0.85       # ~2.80 USD/gallon Jet-A1
    electricity_tariff_usd_per_kwh: float = 0.11 # Industrial regional electricity rate
    battery_pack_cost_usd_per_kwh: float = 220.0 # Installed aviation pack cost ($/kWh)
    battery_cycle_life: int = 1500           # Full flight cycles to 80% EOL capacity
    seat_revenue_loss_usd_per_pax: float = 65.0 # Average lost regional passenger ticket fare per flight
    engine_maint_saving_usd_per_fh: float = 45.0 # Maintenance saving from reduced hot-section thermal cycles ($/flight hour)
    turnaround_time_minutes: float = 30.0    # Scheduled ground turn time (30 min)
    charger_efficiency: float = 0.90         # Ground charger electrical efficiency

def compute_direct_operating_costs(
    fuel_burned_conv_kg: float,
    fuel_burned_hybrid_kg: float,
    battery_recharge_kwh: float,
    battery_capacity_kwh: float,
    flight_duration_hours: float,
    seats_shed: int = 0,
    cost_params: CostParameters = CostParameters()
) -> dict[str, float]:
    """
    Computes comparative flight sector direct operating costs (DOC) in USD.
    """
    # 1. Fuel cost
    fuel_cost_conv = fuel_burned_conv_kg * cost_params.fuel_price_usd_per_kg
    fuel_cost_hybrid = fuel_burned_hybrid_kg * cost_params.fuel_price_usd_per_kg
    fuel_cost_saving = fuel_cost_conv - fuel_cost_hybrid

    # 2. Electricity cost
    electricity_cost = battery_recharge_kwh * cost_params.electricity_tariff_usd_per_kwh

    # 3. Battery amortization per flight: Cost = (Pack Capacity * $/kWh) / Cycle Life
    battery_amortization_per_flight = (battery_capacity_kwh * cost_params.battery_pack_cost_usd_per_kwh) / cost_params.battery_cycle_life

    # 4. Revenue penalty from shed passenger seats
    lost_passenger_revenue = seats_shed * cost_params.seat_revenue_loss_usd_per_pax

    # 5. Turboshaft maintenance credit
    engine_maint_credit = flight_duration_hours * cost_params.engine_maint_saving_usd_per_fh if fuel_burned_hybrid_kg < fuel_burned_conv_kg else 0.0

    # Total net trip cost comparison
    trip_cost_conv = fuel_cost_conv
    trip_cost_hybrid = fuel_cost_hybrid + electricity_cost + battery_amortization_per_flight + lost_passenger_revenue - engine_maint_credit
    net_cost_delta_usd = trip_cost_conv - trip_cost_hybrid

    # 6. Turnaround charging power constraint
    # Charger power = E_recharge / (TAT_hours * eta_charger)
    tat_hours = cost_params.turnaround_time_minutes / 60.0
    required_charger_power_kw = battery_recharge_kwh / (tat_hours * cost_params.charger_efficiency) if tat_hours > 0 else 0.0

    return {
        "fuel_cost_conv_usd": round(fuel_cost_conv, 2),
        "fuel_cost_hybrid_usd": round(fuel_cost_hybrid, 2),
        "fuel_saving_usd": round(fuel_cost_saving, 2),
        "electricity_cost_usd": round(electricity_cost, 2),
        "battery_amortization_usd": round(battery_amortization_per_flight, 2),
        "lost_seat_revenue_usd": round(lost_passenger_revenue, 2),
        "engine_maint_credit_usd": round(engine_maint_credit, 2),
        "trip_cost_conv_usd": round(trip_cost_conv, 2),
        "trip_cost_hybrid_usd": round(trip_cost_hybrid, 2),
        "net_cost_saving_usd": round(net_cost_delta_usd, 2),
        "required_charger_power_kw": round(required_charger_power_kw, 1),
        "turnaround_time_minutes": cost_params.turnaround_time_minutes
    }
