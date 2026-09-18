"""GridMind FastAPI Application Entrypoint.

Provides:
- Production-ready Demand Forecasting API (Milestone 2)
- Endpoints for health, 24-hour demand forecasts, evaluation metrics, and model provenance
- Swagger / OpenAPI automatic interactive documentation at /docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router

app = FastAPI(
    title="GridMind API",
    description=(
        "AI-Powered Hostel Energy Optimization & Peak Load Management API.\n\n"
        "**Core Capabilities:**\n"
        "- **Milestone 2:** Real PJM utility grid load forecasting with Ridge regularized regression\n"
        "- **Milestone 3:** Digital Twin simulation of 500-student university hostel baseload and flexible appliances\n"
        "- **Milestone 4:** Google OR-Tools CP-SAT discrete-interval appliance scheduling optimization\n"
        "- **Milestone 5:** Production API endpoints (`POST /api/optimize`) and deterministic what-if scenario simulations (`POST /api/simulate`)"
    ),
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for future frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
