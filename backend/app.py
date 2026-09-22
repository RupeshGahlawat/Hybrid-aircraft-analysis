"""
FastAPI Server for Hybrid Aircraft Simulation Platform.
Exposes REST and WebSocket endpoints for physics simulation, ML surrogates,
Gemma 3 270M analyst explanations, and Indian UDAN regional routes.
"""

import asyncio
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from backend.ml_service.analyst import ANALYST  # noqa: E402
    from backend.ml_service.surrogate import SURROGATE  # noqa: E402
    from backend.sim_core.mission_sim import MissionSimulator  # noqa: E402
    from backend.sim_core.routes import UDAN_ROUTES, get_route_by_id  # noqa: E402
except ImportError:
    from ml_service.analyst import ANALYST  # type: ignore[no-redef] # noqa: E402
    from ml_service.surrogate import SURROGATE  # type: ignore[no-redef] # noqa: E402
    from sim_core.mission_sim import MissionSimulator  # type: ignore[no-redef] # noqa: E402
    from sim_core.routes import UDAN_ROUTES, get_route_by_id  # type: ignore[no-redef] # noqa: E402

app = FastAPI(
    title="Hybrid Electric Aircraft Feasibility Platform API",
    description="Physics-based digital twin and ML feasibility analysis for ATR-72 regional aircraft.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    route_id: str = "BLR-IXG"
    hp_fraction: float = 0.30
    battery_wh_per_kg: float = 400.0
    ambient_delta_c: float = 0.0


@app.get("/api/health")
def health_check():
    return {"status": "online", "model": "ATR-72-600 Parallel Hybrid"}


@app.get("/api/routes")
def list_routes():
    """Returns available Indian UDAN regional routes with airport metrics."""
    return [
        {
            "route_id": r.route_id,
            "name": r.name,
            "origin": {
                "iata": r.origin.iata,
                "name": r.origin.name,
                "city": r.origin.city,
                "elevation_ft": r.origin.elevation_ft,
                "runway_m": r.origin.runway_length_m,
                "oat_c": r.origin.avg_summer_oat_c,
            },
            "destination": {
                "iata": r.destination.iata,
                "name": r.destination.name,
                "city": r.destination.city,
                "elevation_ft": r.destination.elevation_ft,
                "runway_m": r.destination.runway_length_m,
            },
            "stage_distance_km": r.stage_distance_km,
            "nominal_cruise_alt_ft": r.nominal_cruise_alt_ft,
            "description": r.description,
            "regional_grid_co2_kg_per_kwh": r.regional_grid_co2_kg_per_kwh,
        }
        for r in UDAN_ROUTES
    ]


@app.post("/api/simulate")
def run_simulation(req: SimulationRequest):
    """Runs full physics flight mission integration."""
    route = get_route_by_id(req.route_id)
    sim = MissionSimulator(
        route=route,
        hp_fraction=req.hp_fraction,
        battery_wh_per_kg=req.battery_wh_per_kg,
        ambient_delta_c=req.ambient_delta_c,
    )
    result = sim.run_simulation()
    # Attach Gemma 3 270M verified technical analysis
    analysis = ANALYST.analyze_simulation(result)
    result["ai_analyst"] = analysis
    return result


class AnalystQueryRequest(BaseModel):
    query: str


@app.post("/api/analyst/query")
def query_analyst(req: AnalystQueryRequest):
    """
    Translates natural-language aviation query to validated simulator inputs,
    runs full physics mission integration, and returns technical flight report
    gated by Numerical Consistency Checks.
    """
    from fastapi import HTTPException

    try:
        from backend.ml_service.analyst import InputValidationError
        from backend.ml_service.eval_harness import parse_query_to_simulator_json
    except ImportError:
        from ml_service.analyst import InputValidationError  # type: ignore[no-redef]
        from ml_service.eval_harness import parse_query_to_simulator_json  # type: ignore[no-redef]

    try:
        parsed_inputs = parse_query_to_simulator_json(req.query)
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail={"error": "REFUSAL", "reason": str(e)}) from e

    route = get_route_by_id(parsed_inputs["route_id"])
    sim = MissionSimulator(
        route=route,
        hp_fraction=parsed_inputs["hp_fraction"],
        battery_wh_per_kg=parsed_inputs["battery_wh_per_kg"],
        ambient_delta_c=parsed_inputs["ambient_delta_c"],
    )
    result = sim.run_simulation()
    result["parsed_inputs"] = parsed_inputs
    result["ai_analyst"] = ANALYST.analyze_simulation(result)
    return result


@app.get("/api/analyst/eval-benchmarks")
def get_analyst_eval_benchmarks():
    """Returns official evaluation harness benchmark metrics for Gemma 3 270M analyst."""
    import json
    import os

    metrics_path = "data/models/gemma_eval_metrics.json"
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Analyst benchmark metrics not found"}


class SurrogateRequest(BaseModel):
    distance_km: float = 462.0
    hp_fraction: float = 0.30
    battery_wh_per_kg: float = 400.0
    ambient_delta_c: float = 0.0


@app.get("/api/surrogate")
def evaluate_surrogate(
    distance_km: float = Query(462.0),
    hp_fraction: float = Query(0.30),
    battery_wh_per_kg: float = Query(400.0),
    ambient_delta_c: float = Query(0.0),
):
    """Instantaneous ML surrogate evaluation with conformal prediction intervals."""
    return SURROGATE.predict(
        stage_distance_km=distance_km,
        hp_fraction=hp_fraction,
        battery_wh_per_kg=battery_wh_per_kg,
        ambient_delta_c=ambient_delta_c,
    )


@app.post("/api/surrogate/predict")
def predict_surrogate(req: SurrogateRequest):
    """Structured POST endpoint for instantaneous ML surrogate evaluation."""
    return SURROGATE.predict(
        stage_distance_km=req.distance_km,
        hp_fraction=req.hp_fraction,
        battery_wh_per_kg=req.battery_wh_per_kg,
        ambient_delta_c=req.ambient_delta_c,
    )


@app.get("/api/surrogate/benchmarks")
def get_surrogate_benchmarks():
    """Returns comparative model benchmark metrics across GBDT, MLP, and Polynomial Ridge with conformal coverage."""
    import json

    metrics_path = "data/models/surrogate_metrics.json"
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Benchmark metrics not found"}


@app.get("/api/validation/fcom-benchmarks")
def get_fcom_benchmarks():
    """Returns official ATR 72-600 FCOM performance benchmarks and parameter calibration results."""
    from sim_core.calibration import FCOMCalibrator

    calibrator = FCOMCalibrator()
    res = calibrator.run_calibration()
    return {
        "cd0_initial": res.cd0_initial,
        "cd0_calibrated": res.cd0_calibrated,
        "bsfc_initial": res.bsfc_initial,
        "bsfc_calibrated": res.bsfc_calibrated,
        "uncalibrated_rmse_kg": res.uncalibrated_rmse_kg,
        "calibrated_rmse_kg": res.calibrated_rmse_kg,
        "uncalibrated_max_error_pct": res.uncalibrated_max_error_pct,
        "calibrated_max_error_pct": res.calibrated_max_error_pct,
        "r_squared": res.r_squared,
        "point_comparisons": res.point_comparisons,
    }


@app.get("/api/validation/recorded-flight/{route_id}")
def get_recorded_flight(route_id: str):
    """Returns actual commercial recorded ADS-B flight trajectory for an Indian regional sector."""
    from sim_core.opensky_client import OpenSkyClient

    try:
        data = OpenSkyClient.get_reference_route_trajectory(route_id)
        return data
    except FileNotFoundError as e:
        return {"error": str(e), "route_id": route_id}


@app.get("/api/validation/live-states")
def get_live_states():
    """Queries OpenSky Network for live states over India airspace with local caching and offline fallback."""
    from sim_core.opensky_client import OpenSkyClient

    client = OpenSkyClient()
    return client.fetch_live_states()


class MonteCarloRequest(BaseModel):
    route_id: str = "BLR-IXG"
    hp_fraction: float = 0.30
    n_samples: int = 1000
    seed: int = 42


@app.post("/api/uncertainty/monte-carlo")
def run_monte_carlo(req: MonteCarloRequest):
    """Executes Sobol quasi-random Monte Carlo feasibility analysis (N=1000 default)."""
    from sim_core.uncertainty import run_monte_carlo_feasibility

    route = get_route_by_id(req.route_id)
    return run_monte_carlo_feasibility(route, req.hp_fraction, req.n_samples, req.seed)


@app.get("/api/uncertainty/tornado")
def get_tornado(
    route_id: str = Query("BLR-IXG"),
    hp_fraction: float = Query(0.30),
    battery_wh_per_kg: float = Query(400.0),
):
    """Computes One-at-a-Time (OAT) parameter sensitivities."""
    from sim_core.uncertainty import run_tornado_sensitivity

    route = get_route_by_id(route_id)
    return run_tornado_sensitivity(route, hp_fraction, battery_wh_per_kg)


@app.get("/api/uncertainty/battery-sweep")
def get_battery_sweep(
    route_id: str = Query("BLR-IXG"),
    hp_fraction: float = Query(0.30),
    grid_co2_kg_per_kwh: float | None = Query(None),
):
    """Sweeps battery specific energy from 250 to 600 Wh/kg."""
    from sim_core.uncertainty import run_battery_density_sweep

    route = get_route_by_id(route_id)
    return run_battery_density_sweep(route, hp_fraction, grid_co2_kg_per_kwh=grid_co2_kg_per_kwh)


@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    """
    Streams 1Hz time-synchronized telemetry for live 3D animation and avionics playback.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        route_id = data.get("route_id", "BLR-IXG")
        hp_fraction = float(data.get("hp_fraction", 0.30))
        battery_wh = float(data.get("battery_wh_per_kg", 400.0))
        ambient_delta = float(data.get("ambient_delta_c", 0.0))
        speed_multiplier = float(data.get("speed_multiplier", 4.0))  # 4x playback

        route = get_route_by_id(route_id)
        sim = MissionSimulator(route, hp_fraction, battery_wh, ambient_delta)
        result = sim.run_simulation()

        telemetry = result["telemetry_hybrid"]

        for frame in telemetry:
            await websocket.send_json({"type": "TELEMETRY_FRAME", "frame": frame, "summary": result["summary"]})
            await asyncio.sleep(0.05 / speed_multiplier)

        await websocket.send_json({"type": "MISSION_COMPLETE"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "ERROR", "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
