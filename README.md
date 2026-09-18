# GridMind ⚡
### AI-Powered Hostel Energy Optimization & Peak Load Management

> **Core Product Statement:**  
> GridMind predicts a hostel's near-future electricity demand and automatically schedules flexible appliances to reduce peak load and estimated energy cost without violating user deadlines and physical capacity constraints.

---

## 🏛️ System Architecture

GridMind is built with a deterministic, mathematically grounded optimization engine powered by machine learning demand forecasting:

```
REAL PJM ENERGY DATA + SYNTHETIC DEV WEATHER DATA
                 ↓
      DATA CLEANING & VALIDATION
                 ↓
     FEATURE ENGINEERING & LAGS
                 ↓
    DEMAND FORECASTING (ML Engine)
                 ↓
      HOSTEL DIGITAL TWIN LAYER
                 ↓
  APPLIANCE LOAD & FLEXIBILITY MODEL
                 ↓
CONSTRAINT OPTIMIZATION (OR-Tools CP-SAT)
                 ↓
        OPTIMIZED SCHEDULE
                 ↓
     BEFORE vs AFTER METRICS
                 ↓
      INTERACTIVE DASHBOARD
```

---

## 📁 Repository Structure

- `backend/`: FastAPI application, API routes, schemas, services, and unit test suites.
- `frontend/`: React + Vite + Tailwind CSS + Recharts interactive dashboard.
- `data/`:
  - `raw/`: Real historical electricity load (PJM utility grid) and synthetic aligned weather time series for development.
  - `processed/`: Validated, imputed, feature-engineered datasets.
  - `sample/`: Synthetic, configurable hostel configurations (500 residents, appliance catalogs, time windows).
- `ml/`:
  - `preprocessing/`: Time-series cleaners, lag/rolling feature generators, and exploratory data analysis (EDA).
  - `forecasting/`: Baseline models (Naive 24h persistence, Historical Weekly Mean, Ridge Regression) and model pipelines.
  - `evaluation/`: Metrics calculation (MAE, RMSE, MAPE).
  - `saved_models/`: Serialized model checkpoints.
- `optimization/`: Constraint programming scheduler, constraints definitions, and objective functions.
- `docs/`: Technical documentation, data dictionaries, and EDA reports.
- `DATA_PROVENANCE.md`: Full specification of data sources, limitations, and synthetic data governance.

---

## 📊 Data Provenance & Synthetic Data Policy

For the hackathon evaluation and production roadmap, GridMind strictly enforces transparent data governance. Full details are in [`DATA_PROVENANCE.md`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/DATA_PROVENANCE.md).

- **Real External Data:** Electricity demand is real historical hourly load from the **PJM Interconnection (PJME Zone)**, covering 35,000 hourly observations from 2014 to 2018.
- **Synthetic Development Weather Data:** Current ambient weather data (temperature, humidity, CDD, HDD) is **synthetically generated** using deterministic seasonal and diurnal equations aligned with the PJM timestamps. It was created to develop and test weather-feature couplings without external API dependencies.
- **Synthetic Configurable Hostel Model:** The hostel facility and appliance flexibility catalogs ([`data/sample/hostel_config_default.json`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/sample/hostel_config_default.json)) represent a **synthetic engineering digital twin** modeled for a 500-student hostel facility.
- **Governance Mandate:** Synthetic data **must never be presented or claimed as real physical sensor measurements**. All data structures are schema-standardized to allow drop-in replacement with real IoT smart meters and weather APIs in production.

---

## 🏢 Hostel Digital Twin Layer (Milestone 3)

The **Hostel Digital Twin** ([`backend/app/models/hostel.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/backend/app/models/hostel.py), [`backend/app/services/digital_twin_service.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/backend/app/services/digital_twin_service.py)) bridges utility-scale grid dynamics down to a student residential facility's physical electrical boundaries.

### 1. Default Facility Benchmark (500-Student Hostel)
* **Resident Population:** 500 students across 250 rooms.
* **Transformer Capacity:** **500.0 kW** (hard physical safety boundary).
* **Safe Operating Ceiling:** **450.0 kW** (90% threshold to avoid thermal degradation and peak demand surcharges).
* **Constant Baseload:** **25.0 kW** (uninterruptible circulation pumps, IT routers, emergency lighting).

### 2. Electrical Demand Categorization
* **Inflexible Loads:** Critical non-shiftable loads required for safety, education, and ventilation:
  - *Corridor & Security Lighting:* 20.0 kW (active 17:00–01:00).
  - *Study Rooms & Ventilation:* 15.0 kW (active 09:00–23:00).
* **Flexible Appliance Profiles:**
  - *Water Heaters / Geysers (120 units):* 2.0 kW per unit, 30-min runtime, operable 05:00–22:00, max 60 simultaneous units, shift penalty: 2.0/h, preferred start: 06:00.
  - *Common Laundry Machines (20 units):* 0.7 kW per unit, 60-min runtime, operable 08:00–23:00, max 10 simultaneous units, shift penalty: 1.0/h, preferred start: 10:00.
  - *Personal Device / EV Charging (300 units):* 0.1 kW per unit, 120-min runtime, operable 00:00–24:00, max 150 simultaneous units, shift penalty: 0.5/h, preferred start: 20:00.

### 3. Grid-to-Hostel Baseload Scaling
Utility forecasts are measured in Megawatts ($\sim 35,000\text{ MW}$), while the hostel operates at Kilowatt scale ($\le 500\text{ kW}$). Rather than using arbitrary percentages, GridMind employs mathematically grounded scaling ([`backend/app/services/scaling_service.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/backend/app/services/scaling_service.py)):
$$\text{hostel\_baseline\_kw}(t) = \text{min\_kw} + \frac{P_{\text{grid}}(t) - \min(P_{\text{grid}})}{\max(P_{\text{grid}}) - \min(P_{\text{grid}})} \times (\text{max\_kw} - \text{min\_kw})$$
* **Physical Basis:** Preserves the true diurnal waking, temperature, and activity momentum of the regional grid while strictly bounding non-shiftable hostel demand within $[25\text{ kW}, 125\text{ kW}]$.

### 4. Continuous Headroom & Capacity Verification
The digital twin calculates hourly headroom against transformer constraints:
$$\text{headroom}(t) = P_{\text{transformer}} - (P_{\text{baseline}}(t) + P_{\text{flexible}}(t))$$
Flags operating ceiling breaches ($> 450\text{ kW}$) and transformer overloads ($> 500\text{ kW}$), establishing the exact cost and constraint functions for Milestone 4 (OR-Tools CP-SAT optimization).

---

## ⚙️ OR-Tools CP-SAT Appliance Scheduling Engine (Milestone 4)

GridMind's optimization engine ([`optimization/scheduler.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/optimization/scheduler.py), [`optimization/models.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/optimization/models.py), [`optimization/objective.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/optimization/objective.py)) formulates flexible load shifting as a discrete-time integer constraint satisfaction and optimization problem (CP-SAT) powered by **Google OR-Tools**.

### 1. Mathematical Formulation & Architecture

#### Time Resolution (30-Minute Discretization)
- **Granularity:** The 24-hour horizon is discretized into $T = 48$ half-hour intervals ($\Delta t = 0.5\text{ h}$).
- **Physical Rationale:** Water heaters (geysers) possess a standard 30-minute runtime ($0.5\text{ h}$). A 1-hour resolution would either distort required energy (rounding up to 1.0h doubles daily energy) or split units artificially. A 30-minute resolution natively models geysers ($1\text{ slot}$), washing machines ($2\text{ slots}$), and device chargers ($4\text{ slots}$) with zero rounding error.
- **Grid Forecast Coupling:** The 24-hour hourly grid forecast $P_{\text{grid}}(h)$ is mapped into two consecutive 30-minute slots ($t = 2h, 2h+1$), preserving baseline diurnal variation.

#### Decision Variables
For each flexible appliance type $a \in \mathcal{A}$ and time slot $t \in [0, 47]$:
- $\text{starts}[a, t] \in [0, \min(Q_a, M_a)]$: Number of appliance units initiated at interval $t$.
- $\text{active}[a, t] = \sum_{\tau = \max(0, t - d_a + 1)}^{t} \text{starts}[a, \tau]$: Number of units actively drawing power at slot $t$ (where $d_a = \lceil\text{runtime}_a / \Delta t\rceil$).
- $P_{\text{peak}} \in [0, P_{\text{transformer}}]$: Auxiliary variable capturing maximum total instantaneous load across the 24-hour horizon.

#### Constraints
1. **Fleet Quantity & Energy Completion:**
   $$\sum_{t = t_{\text{earliest}}}^{t_{\text{latest}} - d_a} \text{starts}[a, t] = Q_a, \quad \forall a \in \mathcal{A}$$
   Every appliance unit in the fleet is guaranteed to start and complete its full duty cycle within its permitted operational window.
2. **Maximum Concurrency Limit:**
   $$\text{active}[a, t] \le M_a, \quad \forall a \in \mathcal{A}, \forall t \in [0, 47]$$
   Physical circuit limitations (e.g. at most 60 geysers or 10 laundry machines concurrently) are strictly enforced.
3. **Operational Window Bounds:**
   $$\text{starts}[a, t] = 0, \quad \forall t \notin [t_{\text{earliest}}, t_{\text{latest}} - d_a]$$
   No appliance can run outside its configured operational boundaries.
4. **Facility Operating Ceiling & Transformer Protection:**
   $$P_{\text{total}}(t) = P_{\text{baseline}}(t) + \sum_{a \in \mathcal{A}} \text{active}[a, t] \cdot P_a \le P_{\text{ceiling}} \le P_{\text{transformer}}, \quad \forall t \in [0, 47]$$
   Guarantees load never breaches the $450.0\text{ kW}$ operating ceiling or the $500.0\text{ kW}$ transformer capacity.
5. **Peak Load Tracking:**
   $$P_{\text{peak}} \ge P_{\text{total}}(t), \quad \forall t \in [0, 47]$$

#### Multi-Objective Function
$$\min \left[ W_{\text{peak}} \cdot P_{\text{peak}} + W_{\text{conv}} \sum_{a \in \mathcal{A}} \sum_{t} \text{starts}[a, t] \cdot |t - t_{\text{pref}}| \cdot \Delta t \cdot \text{penalty}_a \right]$$
- **Strict Prioritization:** $W_{\text{peak}} = 10,000$ and $W_{\text{conv}} = 1$. Peak load shaving strictly dominates the objective; user convenience acts only as a tie-breaker so appliances prefer starting near user-preferred hours when peak load is unaffected.

#### Integer Scaling Precision
OR-Tools CP-SAT operates natively on integer domains. Power ratings and loads are scaled by factor $F = 100$ ($0.01\text{ kW} = 10\text{ Watts}$ precision). Solutions are extracted and divided by $F$.

---

### 2. Deterministic Baseline Schedule (BEFORE vs AFTER)

To measure true optimization impact, GridMind builds an explicit, deterministic unoptimized baseline schedule:
- **Baseline Logic:** Appliances start at their `preferred_start_hour` in sequential batches respecting concurrency limits until all units complete.
- **No Fabricated Savings:** Energy is strictly conserved ($\text{Energy}_{\text{baseline}} \equiv \text{Energy}_{\text{optimized}}$). GridMind shifts load in time rather than claiming phantom energy reductions.

---

### 3. Example Optimization Results

#### Scenario A: Coupled with 24-Hour ML Demand Forecast
```
Status:                    OPTIMAL
Baseline Peak Load:        192.53 kW (coincident geyser + baseline peak)
Optimized Peak Load:       183.37 kW (flattened to non-shiftable baseline peak)
Peak Reduction:            9.16 kW (-4.76%)
Total Energy:              3,204.27 kWh (100% conserved)
Transformer Headroom:      316.63 kW remaining at peak (Transformer: 500 kW, Ceiling: 450 kW)
Solver Runtime:            0.124 seconds
```

#### Scenario B: Uncoupled Hostel Baseline
```
Status:                    OPTIMAL
Baseline Peak Load:        145.00 kW
Optimized Peak Load:       60.00 kW
Peak Reduction:            85.00 kW (-58.62%)
Total Energy:              1,179.00 kWh (100% conserved)
Transformer Headroom:      440.00 kW remaining at peak
Solver Runtime:            0.122 seconds
```

---

### 4. Feasibility & Error Handling

- **Deterministic Solving:** Configured with `num_search_workers = 1` and `random_seed = 42` for 100% reproducible schedules.
- **Infeasibility Detection:** If an appliance fleet cannot physically fit within operating windows and concurrency caps under the operating ceiling, the solver immediately returns `status = INFEASIBLE` with diagnostic details (or raises `InfeasibleScheduleError` in strict mode), never emitting an invalid schedule.

---

## 🌐 Optimization & What-If Simulation API (Milestone 5)

Milestone 5 exposes the optimization engine and hostel digital twin as production REST APIs with interactive Swagger documentation (`/docs`), accompanied by a deterministic what-if scenario simulation service.

### Architecture Layering

GridMind strictly separates presentation, domain services, and constraint solving:

```
FastAPI Routes (backend/app/api/routes.py)
                   ↓
Domain Services (backend/app/services/)
   ├── OptimizationService (optimization_service.py)
   ├── SimulationService (simulation_service.py)
   └── ForecastService (forecast_service.py)
                   ↓
Core Engine & Digital Twin
   ├── ApplianceScheduler (optimization/scheduler.py - OR-Tools CP-SAT)
   ├── HostelDigitalTwin (backend/app/services/digital_twin_service.py)
   └── HostelConfig (backend/app/models/hostel.py)
```

---

### Endpoints Specification

#### 1. `POST /api/optimize`
Runs CP-SAT discrete-interval optimization on the default 500-student hostel facility using the live 24-hour ML demand forecast.

* **Request Body (Optional):**
  ```json
  {
    "start_time": null,
    "enforce_operating_ceiling": true,
    "time_limit_seconds": 10.0
  }
  ```
* **Response Body (200 OK):**
  ```json
  {
    "status": "OPTIMAL",
    "horizon_hours": 24,
    "time_step_minutes": 30,
    "baseline_peak_kw": 192.53,
    "optimized_peak_kw": 183.37,
    "peak_reduction_kw": 9.16,
    "peak_reduction_percent": 4.76,
    "baseline_total_energy_kwh": 3204.27,
    "optimized_total_energy_kwh": 3204.27,
    "hourly_load_before_kw": [ ... ],
    "hourly_load_after_kw": [ ... ],
    "slot_load_before_kw": [ ... ],
    "slot_load_after_kw": [ ... ],
    "appliance_schedule": {
      "geyser": [0, 0, ..., 60, 55, 5, 0, ...],
      "washing_machine": [0, 0, ..., 10, 10, ...],
      "device_charging": [0, 0, ..., 150, 150, ...]
    },
    "transformer_capacity_kw": 500.0,
    "operating_ceiling_kw": 450.0,
    "maximum_headroom_kw": 450.0,
    "minimum_headroom_kw": 316.63,
    "solver_runtime_seconds": 0.0282,
    "details": "CP-SAT OPTIMAL: Peak reduced from 192.53 kW to 183.37 kW (-4.76%)."
  }
  ```

#### 2. `POST /api/simulate`
Executes a deterministic what-if scenario simulation modifying resident population, transformer ratings, or appliance fleets. Contrasts the simulated scenario against the pristine 500-student baseline benchmark.

* **Example Request Body:**
  ```json
  {
    "total_students": 600,
    "operating_ceiling_kw": 450.0,
    "transformer_capacity_kw": 500.0,
    "geyser_quantity": 200,
    "geyser_max_simultaneous": 75,
    "washing_machine_quantity": 25,
    "washing_machine_max_simultaneous": 12,
    "device_charging_quantity": 350
  }
  ```
* **Response Body (200 OK):**
  ```json
  {
    "status": "OPTIMAL",
    "is_feasible": true,
    "baseline_scenario": {
      "unoptimized_peak_kw": 192.53,
      "optimized_peak_kw": 183.37,
      "peak_reduction_kw": 9.16,
      "peak_reduction_percent": 4.76,
      "total_energy_kwh": 3204.27
    },
    "simulated_scenario": {
      "unoptimized_peak_kw": 222.53,
      "optimized_peak_kw": 183.37,
      "peak_reduction_kw": 39.16,
      "peak_reduction_percent": 17.6,
      "total_energy_kwh": 3284.27
    },
    "comparison": {
      "baseline_peak_kw": 183.37,
      "simulated_peak_kw": 183.37,
      "peak_difference_kw": 0.0,
      "peak_difference_percent": 0.0,
      "baseline_energy_kwh": 3204.27,
      "simulated_energy_kwh": 3284.27,
      "energy_difference_kwh": 80.0,
      "is_feasible": true,
      "solver_status": "OPTIMAL"
    },
    "forecasted_demand_mw": [ ... ],
    "hourly_baseline_load_kw": [ ... ],
    "hourly_load_before_kw": [ ... ],
    "hourly_load_after_kw": [ ... ],
    "appliance_schedule": { ... },
    "transformer_capacity_kw": 500.0,
    "operating_ceiling_kw": 450.0,
    "maximum_headroom_kw": 450.0,
    "minimum_headroom_kw": 316.63,
    "solver_runtime_seconds": 0.0259,
    "scenario_parameters_applied": {
      "total_students": 600,
      "geyser_quantity": 200,
      "geyser_max_simultaneous": 75,
      "washing_machine_quantity": 25,
      "washing_machine_max_simultaneous": 12,
      "device_charging_quantity": 350
    }
  }
  ```

---

### Validation & Error Handling

- **Pydantic Model Validations (HTTP 422):** Invalid inputs (e.g. `total_students <= 0`, `geyser_quantity = 0`, or `operating_ceiling_kw > transformer_capacity_kw`) are strictly rejected with comprehensive field error messages. Inputs are never silently clamped.
- **Operational Constraint Validations (HTTP 400):** Impossible combinations (e.g. `geyser_max_simultaneous > geyser_quantity` or invalid operational windows) raise `ScenarioValidationError` returned as HTTP 400.
- **Infeasible Problem Handling:** When a scenario demands loads that cannot mathematically fit beneath the operating ceiling, the solver returns `status = "INFEASIBLE"` with `is_feasible = false` and explanatory diagnostics without crashing.

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Virtual environment (`.venv`)

### 2. Environment Setup
```powershell
# Create and activate virtual environment
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r backend/requirements.txt
```

### 3. Ingest Data & Train Baseline ML Pipeline
```powershell
# Download real electricity consumption data and pair with weather data
.venv\Scripts\python -m data.download_data

# Run Exploratory Data Analysis
.venv\Scripts\python -m ml.preprocessing.eda

# Run baseline feature pipeline and model training
.venv\Scripts\python -m ml.forecasting.pipeline
```

### 4. Run Automated Tests
```powershell
# Run complete test suite (68 tests across all milestones)
.venv\Scripts\pytest backend/tests/ -v
```

### 5. Launch FastAPI Backend Server
```powershell
.venv\Scripts\uvicorn backend.app.main:app --reload --port 8000
```
Interactive Swagger API documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- `GET /api/health`: Service health check and model status
- `GET /api/forecast`: 24-hour ahead dynamic electricity demand forecast
- `GET /api/model/metrics`: Model evaluation metrics (MAE, RMSE, MAPE) on held-out test data
- `GET /api/model/info`: Model metadata, feature list, and data provenance disclosures
- `POST /api/optimize`: Run CP-SAT appliance scheduling optimization
- `POST /api/simulate`: Run deterministic what-if scenario simulations with comparative analytics

