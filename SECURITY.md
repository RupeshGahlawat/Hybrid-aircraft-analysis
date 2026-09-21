# Security Policy & Threat Model
## AeroHybrid Platform Security Specification

**Document Identifier**: SEC-AEROHYBRID-2026-V1  
**Status**: ACTIVE SECURITY SPECIFICATION  

---

## 1. Security Posture Overview

AeroHybrid is an engineering research and simulation digital twin platform. It currently operates within an internal or developer-hosted network boundary without public multi-tenant user accounts. Consequently, security mechanisms prioritize **input sanitization**, **denial-of-service prevention through input clamping**, **dependency integrity**, and **prevention of ungrounded language model generation**.

> [!WARNING]
> This system does NOT currently enforce user authentication or multi-tenant authorization. It should only be deployed on trusted internal intranets or behind an authenticated reverse proxy (e.g., NGINX with mTLS/OAuth2) if exposed outside localhost.

---

## 2. Threat Model (STRIDE-Aligned)

| Threat | Attack Surface | Impact | Likelihood | Mitigation Implemented |
| :--- | :--- | :--- | :---: | :--- |
| **Numerical DoS (Infinite Loop)** | `POST /api/simulate` | Backend CPU hangs in infinite climb loop if thrust < drag. | Medium | Mandatory climb rate floor clamp ($1.0\text{ m/s}$), absolute step timeout, and ceiling exit conditions. |
| **Out-of-Bounds Parameter Injection** | `GET /api/surrogate`, `/api/simulate` | Floating point overflow / `NaN` propagation across physics engine. | High | Pydantic validation + explicit `np.clip` bounds on all input parameters ($H_P \le 0.60$, $e_{\text{batt}} \in [150, 800]$). |
| **WebSocket Memory Exhaustion** | `/ws/telemetry` | Client opens hundreds of unclosed WebSocket connections. | Medium | Client disconnect cleanup handlers (`except WebSocketDisconnect`), one active stream per socket. |
| **Cross-Origin Resource Abuse** | HTTP Endpoints | Malicious external websites triggering simulation requests. | Low | Strict CORS header configuration (`allow_origins` configurable via environment variables). |
| **Prompt Injection / Hallucinated Guidance** | Language Analyst Service | Fabricated performance figures misleading safety-critical evaluations. | Medium | Programmatic assertion audit: all numerical values in text are verified against simulation output dictionary before rendering. |
| **Dependency Vulnerability** | `npm` and `pip` packages | Remote code execution via compromised supply-chain dependency. | Low | Regular automated auditing (`npm audit`, `pip-audit`), lockfiles committed (`package-lock.json`). |

---

## 3. Input Validation Architecture

All incoming API requests are parsed through strict Pydantic models:

```python
class SimulationRequest(BaseModel):
    route_id: str = Field(..., description="Must match an approved UDAN route identifier")
    hp_fraction: float = Field(0.30, ge=0.0, le=0.60, description="Clamped to 0.0 to 0.60")
    battery_wh_per_kg: float = Field(400.0, ge=150.0, le=800.0, description="Clamped to physical envelope")
    ambient_delta_c: float = Field(0.0, ge=-20.0, le=40.0, description="Clamped to realistic ISA delta")
```

Any malformed payload or type mismatch triggers an immediate HTTP `422 Unprocessable Entity` response before reaching the physics numerical integrator.

---

## 4. Operational Secrets & Data Privacy

* **Secrets Management**: The platform requires **zero cloud API keys, secrets, or database credentials** in its baseline implementation. No `.env` secrets are packaged or required for local simulation.
* **Telemetry Data Privacy**: Flight simulations run strictly in-memory. No client IP addresses, route queries, or corporate sizing models are transmitted to third-party tracking services or external cloud providers.

---

## 5. Vulnerability Reporting

If you discover a security vulnerability within AeroHybrid, please report it directly via GitHub Security Advisories or by emailing `jatinbaberwal230@gmail.com`. Do not disclose public vulnerabilities until a remediation patch is released.
