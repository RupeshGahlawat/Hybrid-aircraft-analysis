"""Generate offline cached scenarios for frontend fallback and instant demonstration."""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sim_core.mission_sim import MissionSimulator
from sim_core.aircraft_specs import AircraftBaseline
from sim_core.indian_routes import get_route_by_id
from ml_service.surrogate import SurrogateService
from ml_service.analyst import FlightFeasibilityAnalyst

def main():
    specs = AircraftBaseline()
    sim = MissionSimulator(specs=specs, physics_mode="phase2")
    analyst = FlightFeasibilityAnalyst()
    surrogate = SurrogateService()

    route_ids = ["BLR-IXG", "BOM-PNQ", "DEL-DED", "MAA-TIR"]
    cached = {}

    for rid in route_ids:
        route = get_route_by_id(rid)
        res = sim.run_mission(
            route=route,
            hp_fraction=0.30,
            battery_wh_per_kg=400.0,
            ambient_delta_c=0.0,
        )
        dist = route.stage_distance_km
        surr_res = surrogate.predict(dist, 0.30, 400.0, 0.0)

        analysis = analyst.generate_flight_analysis(
            route_name=f"{route.origin.name} to {route.destination.name}",
            stage_distance_km=route.stage_distance_km,
            hp_fraction=0.30,
            battery_wh_per_kg=400.0,
            ambient_delta_c=0.0,
            fuel_saved_pct=res["summary"]["fuel_saved_pct"],
            battery_weight_kg=res["summary"]["battery_weight_kg"],
            is_feasible=res["summary"]["is_feasible"],
            passengers_carried=res["summary"]["passengers_carried"],
            takeoff_reduction_pct=res["summary"]["takeoff_roll_reduction_pct"],
            net_co2_saved_pct=res["summary"]["net_co2_saved_pct"],
        )
        res["ai_analyst"] = analysis
        res["surrogate"] = surr_res
        cached[rid] = res

    target_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "cachedScenarios.js")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("// Precomputed offline scenario cache for demonstration & offline fallback\n")
        f.write("export const CACHED_SCENARIOS = ")
        json.dump(cached, f, indent=2)
        f.write(";\n")

    print(f"Generated {target_path} successfully ({os.path.getsize(target_path)} bytes)")

if __name__ == "__main__":
    main()
