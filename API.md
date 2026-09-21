# API Specification
## AeroHybrid REST & WebSocket Interface Definition

**Document Identifier**: API-AEROHYBRID-2026-V1  
**Base URL**: `http://127.0.0.1:8000`  
**Protocol**: HTTP/1.1 and WSS (WebSocket)  
**Authentication**: None (Localhost / Internal Network Mode)  

---

## 1. Endpoints Overview

| Method | Endpoint | Description | Expected Latency |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/health` | Service liveness and active airframe model check | $< 5\text{ ms}$ |
| `GET` | `/api/routes` | Lists supported Indian regional UDAN routes and airport parameters | $< 10\text{ ms}$ |
| `POST` | `/api/simulate` | Executes full 4-phase physics flight mission trajectory integration | $< 100\text{ ms}$ |
| `GET` | `/api/surrogate` | Executes instantaneous analytical surrogate evaluation | $< 1\text{ ms}$ |
| `WS` | `/ws/telemetry` | Time-synchronized live telemetry stream for external dashboards | Streaming |

---

## 2. Endpoint Details

### 2.1 Health Check
* **Path**: `/api/health`
* **Method**: `GET`
* **Response (200 OK)**:
```json
{
  "status": "online",
  "model": "ATR-72-600 Parallel Hybrid"
}
```

---

### 2.2 List UDAN Routes
* **Path**: `/api/routes`
* **Method**: `GET`
* **Response (200 OK)**:
```json
[
  {
    "route_id": "BLR-IXG",
    "name": "Bengaluru (BLR) ➔ Belagavi (IXG)",
    "origin": {
      "iata": "BLR",
      "name": "Kempegowda Int'l",
      "city": "Bengaluru",
      "elevation_ft": 3000.0,
      "runway_m": 4000.0,
      "oat_c": 34.0
    },
    "destination": {
      "iata": "IXG",
      "name": "Belagavi Airport",
      "city": "Belagavi",
      "elevation_ft": 2488.0,
      "runway_m": 2300.0
    },
    "stage_distance_km": 462.0,
    "nominal_cruise_alt_ft": 20000.0,
    "description": "High-traffic Karnataka regional route...",
    "regional_grid_co2_kg_per_kwh": 0.68
  }
]
```

---

### 2.3 Run Mission Simulation
* **Path**: `/api/simulate`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
```json
{
  "route_id": "BOM-PNQ",
  "hp_fraction": 0.30,
  "battery_wh_per_kg": 400.0,
  "ambient_delta_c": 0.0
}
```
* **Validation Rules**:
  * `route_id`: Must match an active route key.
  * `hp_fraction`: Clamped between `0.0` and `0.60`.
  * `battery_wh_per_kg`: Clamped between `150.0` and `800.0`.
  * `ambient_delta_c`: Clamped between `-20.0` and `40.0`.
* **Response (200 OK)**:
```json
{
  "route": { ... },
  "parameters": {
    "hp_fraction": 0.3,
    "battery_wh_per_kg": 400.0,
    "ambient_delta_c": 0.0
  },
  "summary": {
    "conventional_fuel_kg": 182.4,
    "hybrid_fuel_kg": 142.1,
    "fuel_saved_kg": 40.3,
    "fuel_saved_pct": 22.1,
    "takeoff_roll_conv_m": 520.0,
    "takeoff_roll_hybrid_m": 464.0,
    "takeoff_roll_reduction_pct": 10.8,
    "battery_weight_kg": 677.5,
    "battery_capacity_kwh": 271.0,
    "mtow_hybrid_kg": 21820.0,
    "mtow_conv_kg": 21100.0,
    "passengers_carried": 70,
    "payload_penalty_pax": 0,
    "is_feasible": true
  },
  "telemetry_hybrid": [
    {
      "time_s": 0.0,
      "phase": "takeoff",
      "distance_km": 0.0,
      "altitude_ft": 39.0,
      "airspeed_kt": 0.0,
      "pitch_deg": 1.5,
      "turboshaft_power_kw": 2870.0,
      "electric_power_kw": 1230.0,
      "fuel_flow_kg_hr": 789.2,
      "fuel_burned_kg": 0.0,
      "battery_soc_pct": 100.0,
      "gear_extended": true
    }
  ],
  "ai_analyst": {
    "model_metadata": {
      "architecture": "Gemma 3 270M (Fine-Tuned Feasibility Analyst)",
      "verification_status": "PASSED (100% Programmatically Grounded)"
    },
    "summary_bullet_points": [ ... ]
  }
}
```

---

### 2.4 Evaluate ML Surrogate
* **Path**: `/api/surrogate`
* **Method**: `GET`
* **Query Parameters**:
  * `distance_km`: Float (default `462.0`)
  * `hp_fraction`: Float (default `0.30`)
  * `battery_wh_per_kg`: Float (default `400.0`)
  * `ambient_delta_c`: Float (default `0.0`)
* **Response (200 OK)**:
```json
{
  "predicted_fuel_saved_pct": 7.12,
  "predicted_fuel_saved_kg": 42.0,
  "uncertainty_range_pct": [6.15, 8.09],
  "feasibility_probability": 0.998,
  "is_feasible": true,
  "estimated_battery_mass_kg": 677.5,
  "estimated_tow_kg": 22277.1,
  "inference_time_ms": 0.08
}
```

---

### 2.5 Live Telemetry WebSocket
* **Path**: `/ws/telemetry`
* **Protocol**: `WSS / WS`
* **Initial Client Handshake Message**:
```json
{
  "route_id": "BLR-IXG",
  "hp_fraction": 0.30,
  "battery_wh_per_kg": 400.0,
  "speed_multiplier": 2.0
}
```
* **Server Stream Messages**: Emits `TELEMETRY_FRAME` JSON messages at variable rates until `MISSION_COMPLETE`.
