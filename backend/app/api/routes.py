"""FastAPI Route Definitions for GridMind API."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.forecast import (
    HealthResponse,
    ForecastResponse,
    ModelMetricsResponse,
    ModelInfoResponse,
)
from backend.app.schemas.optimization import (
    OptimizationRequest,
    OptimizationResponse,
)
from backend.app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
)
from backend.app.services.forecast_service import (
    ForecastService,
    ModelNotTrainedError,
    InsufficientDataError,
    InvalidTimestampError,
)
from backend.app.services.optimization_service import OptimizationService
from backend.app.services.simulation_service import (
    SimulationService,
    ScenarioValidationError,
)

router = APIRouter(prefix="/api", tags=["GridMind API"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational health of the GridMind API and confirms whether the ML model is loaded.",
)
def health_check():
    service = ForecastService.get_instance()
    is_loaded = service.is_model_loaded()
    return HealthResponse(
        status="online" if is_loaded else "degraded",
        service="GridMind Demand Forecasting Service",
        version="0.2.0",
        model_loaded=is_loaded,
    )


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Generate Electricity Demand Forecast",
    description="Generates dynamic hourly electricity demand predictions for the specified horizon (default: 24 hours) using the trained Ridge regression baseline.",
    responses={
        200: {"description": "Forecast successfully generated with exactly 24 hourly predictions."},
        400: {"description": "Invalid timestamp format."},
        422: {"description": "Insufficient historical observations to construct features."},
        503: {"description": "Model artifact or required dataset not available."},
    },
)
def get_forecast(
    start_time: Optional[str] = Query(
        None,
        description="Optional starting timestamp (ISO format 'YYYY-MM-DD HH:MM:SS'). Defaults to the 24 hours following the latest recorded observation.",
        examples=["2018-08-02 00:00:00"],
    ),
    horizon_hours: int = Query(
        24,
        description="Forecast horizon length in hours (default: 24).",
        ge=1,
        le=168,
        examples=[24],
    ),
):
    service = ForecastService.get_instance()

    try:
        forecast_points = service.generate_forecast(
            horizon_hours=horizon_hours,
            start_time=start_time,
        )
        return ForecastResponse(
            horizon_hours=horizon_hours,
            unit="MW",
            model="ridge_baseline",
            forecast=forecast_points,
        )
    except ModelNotTrainedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidTimestampError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting generation failed: {exc}",
        ) from exc


@router.get(
    "/model/metrics",
    response_model=ModelMetricsResponse,
    summary="Held-Out Model Evaluation Metrics",
    description="Returns the actual held-out test evaluation metrics (MAE, RMSE, MAPE, test sample count) loaded from the trained model evaluation artifact.",
    responses={
        200: {"description": "Evaluation metrics loaded successfully."},
        503: {"description": "Evaluation metrics artifact not found."},
    },
)
def get_model_metrics():
    service = ForecastService.get_instance()
    try:
        metrics_data = service.get_metrics()
        return ModelMetricsResponse(**metrics_data)
    except ModelNotTrainedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model metrics: {exc}",
        ) from exc


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Model Metadata & Provenance Disclosure",
    description="Returns model specification, feature names, train/test periods, observation counts, and transparent data provenance disclosures (explicitly noting synthetic weather development data).",
    responses={
        200: {"description": "Model metadata and provenance returned successfully."},
        503: {"description": "Model metadata artifact not found."},
    },
)
def get_model_info():
    service = ForecastService.get_instance()
    try:
        info_data = service.get_model_info()
        return ModelInfoResponse(**info_data)
    except ModelNotTrainedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model info: {exc}",
        ) from exc


@router.post(
    "/optimize",
    response_model=OptimizationResponse,
    summary="Run Appliance Scheduling Optimization",
    description="Executes Google OR-Tools CP-SAT discrete-interval optimization to minimize peak hostel electrical demand using the live 24-hour ML forecast.",
    responses={
        200: {"description": "Appliance schedule optimized successfully."},
        400: {"description": "Invalid input or timestamp format."},
        422: {"description": "Insufficient historical data or validation failure."},
        503: {"description": "Forecasting model or dataset unavailable."},
    },
)
def run_optimization(request: Optional[OptimizationRequest] = None):
    service = OptimizationService.get_instance()
    try:
        return service.optimize(request=request)
    except (ModelNotTrainedError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidTimestampError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {exc}",
        ) from exc


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Run What-If Scenario Simulation",
    description="Executes a deterministic what-if scenario simulation modifying hostel capacity, student population, and appliance fleets, contrasting results against the baseline benchmark.",
    responses={
        200: {"description": "Scenario simulated and optimized successfully."},
        400: {"description": "Invalid scenario configuration parameters."},
        422: {"description": "Pydantic validation error or unprocessable scenario."},
        503: {"description": "Forecasting model or dataset unavailable."},
    },
)
def run_simulation(request: SimulationRequest):
    service = SimulationService.get_instance()
    try:
        return service.simulate(request=request)
    except ScenarioValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (ModelNotTrainedError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InsufficientDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidTimestampError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {exc}",
        ) from exc

