# GridMind

GridMind forecasts electricity demand for hostel environments and models how that demand affects a configurable facility. It uses constraint-based optimization to schedule flexible appliances and reduce peak load while preserving the required appliance work.

## What It Does

- **Demand forecasting:** Trains a model to produce a 24-hour electricity demand forecast.
- **Hostel digital twin:** Scales the forecast into a configurable hostel load model with facility and appliance parameters.
- **CP-SAT appliance scheduling:** Schedules flexible appliances around operating and capacity constraints to reduce peak demand.
- **What-if simulation:** Tests changes to the hostel population, appliance fleet, and electrical capacity.

## How It Works

```text
Historical electricity data
        -> Demand forecasting
        -> Hostel digital twin
        -> CP-SAT optimization
        -> Optimized appliance schedule
        -> What-if simulation
```

The forecasting model provides the demand signal, the digital twin converts it into hostel-scale load, and the scheduler shifts flexible appliance demand within the configured limits. The simulation service runs the same process for user-defined scenarios.

## Machine Learning

GridMind uses a Ridge Regression forecasting model trained on historical PJM hourly electricity consumption data. The feature pipeline includes temporal and lag-based features, and the data is split chronologically into training and held-out test sets.

Held-out test metrics:

- MAE: 386.48 MW
- RMSE: 515.46 MW
- MAPE: 1.22%

## Optimization

GridMind uses Google OR-Tools CP-SAT for constraint-based appliance scheduling. Optimization runs at 30-minute resolution over a 24-hour horizon.

The scheduler accounts for:

- appliance quantities
- operating windows
- runtime requirements
- maximum simultaneous usage
- transformer capacity
- safe operating ceiling

The main objective is to reduce peak load by shifting flexible demand in time, rather than simply switching appliances off.

## Tech Stack

**Backend:** Python, FastAPI, Pydantic, Scikit-learn, Pandas, NumPy, OR-Tools, Joblib

**Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React

**Data:** PJM Interconnection PJME hourly electricity consumption dataset, configurable hostel parameters, and synthetic development weather data.

## Running Locally

Backend:

```powershell
.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The FastAPI API runs at `http://127.0.0.1:8000`.

## Project Structure

```text
GridMind/
├── backend/       FastAPI application, schemas, services, and tests
├── frontend/      React dashboard and API client
├── ml/            Data preprocessing, forecasting, and evaluation
├── optimization/ Constraint models, objectives, and scheduler
├── data/          Raw, processed, and sample data
├── notebooks/     Exploratory analysis notebooks
└── docs/          Supporting project documentation
```

## Results

The demonstrated default scenario produces:

- Unoptimized peak: approximately 192.53 kW
- Optimized peak: approximately 183.37 kW
- Peak reduction: 9.16 kW (4.76%)
- Total daily energy: 3,204.27 kWh before and after optimization

This demonstrates peak-load shifting while preserving total daily energy.
