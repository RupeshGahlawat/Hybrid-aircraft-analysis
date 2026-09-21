# Quickstart & Reproduction Guide
## AeroHybrid Platform Setup and Verification

**Document Identifier**: QS-AEROHYBRID-2026-V1  
**Estimated Setup Time**: 3 minutes  

---

## 1. System Requirements

* **Operating System**: Windows 10/11, macOS, or Linux (Ubuntu 22.04+).
* **Python Runtime**: Python 3.10, 3.11, 3.12, 3.13, or 3.14.
* **Node Runtime**: Node.js v18.0.0+ and npm v9.0.0+.
* **Hardware**: Standard dual-core CPU with WebGL 2.0 compatible browser (Chrome, Edge, Firefox, Safari).

---

## 2. Step-by-Step Installation

### Step 2.1: Clone the Repository
```bash
git clone https://github.com/Jatinkumar2503/Hybrid-aircraft-analysis.git
cd Hybrid-aircraft-analysis
```

### Step 2.2: Python Backend Environment Setup
```bash
# Install required Python dependencies
python -m pip install -r requirements.txt
```

### Step 2.3: Frontend Web App Setup
```bash
# Navigate to frontend and install npm packages
cd frontend
npm install
cd ..
```

---

## 3. Running the Verification Test Suite

Before launching services, verify that all core physics and sizing tests pass:

```bash
python -m pytest tests/test_core.py -v
```
*Expected Output*: `11 passed in ~0.15s`

---

## 4. Starting the Platform

### Terminal 1: Launch FastAPI Backend Server
```bash
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
*Verification*: Open [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) in your browser.  
*Expected Output*: `{"status":"online","model":"ATR-72-600 Parallel Hybrid"}`

### Terminal 2: Launch Vite React 3D Dashboard
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
*Access Web App*: Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) in your web browser.

---

## 5. Interactive Demo Walkthrough

1. **Observe 3D Takeoff**: Notice the ATR-72 turboprop rolling down the runway, spinning its 6-blade propellers with electric cyan blur disks, rotating at $V_R = 108\text{ KIAS}$, and smoothly climbing out.
2. **Switch Cameras**: In the bottom control deck, click **`Cam: Tower`** to watch the aircraft fly past the runway threshold, or **`Cam: Orbit (Drag)`** to click and rotate 360° around the airframe.
3. **Inspect the Dual Ghost Mode**: Notice the baseline conventional ATR-72 flying in parallel to observe the takeoff roll reduction.
4. **Test Short-Haul Dominance**: Change the route dropdown to **`Mumbai (BOM) ➔ Pune (PNQ)`** (122 km) and observe block fuel savings jump to **`22.1%`**.
5. **Adjust Battery Sensitivity**: Drag the **Battery Specific Energy** slider from `400 Wh/kg` down to `250 Wh/kg` (today's Li-ion pack tech) and observe how the MTOW margin tightens.

---

## 6. Troubleshooting

* **Port Conflict (`Address already in use`)**:
  * If port 8000 or 5173 is occupied, specify alternative ports:
    `python -m uvicorn app:app --app-dir backend --port 8080`
    `npm run dev -- --port 3000`
* **Three.js WebGL Black/Blank Screen**:
  * Ensure hardware acceleration is enabled in your browser settings (`chrome://settings/system` $\to$ *Use hardware acceleration when available*).
* **Cross-Origin Errors (CORS)**:
  * By default, the FastAPI backend allows all origins (`allow_origins=["*"]`). If restricted, check your browser's proxy or security extension settings.
