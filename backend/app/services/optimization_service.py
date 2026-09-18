"""Optimization Service Module for GridMind.

Orchestrates:
- Retrieving 24-hour demand forecasts from ForecastService
- Loading and configuring HostelDigitalTwin
- Executing CP-SAT appliance scheduling optimization via ApplianceScheduler
- Constructing structured OptimizationResponse objects
"""

from typing import Optional, List
from backend.app.schemas.optimization import OptimizationRequest, OptimizationResponse
from backend.app.services.forecast_service import ForecastService
from optimization.scheduler import ApplianceScheduler


class OptimizationService:
    """Production service for managing appliance scheduling optimization."""

    _instance: Optional["OptimizationService"] = None

    @classmethod
    def get_instance(cls) -> "OptimizationService":
        """Singleton accessor for the optimization service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def optimize(
        self,
        request: Optional[OptimizationRequest] = None,
    ) -> OptimizationResponse:
        """Execute CP-SAT appliance scheduling using the live 24-hour ML demand forecast.

        Parameters
        ----------
        request : Optional[OptimizationRequest]
            Parameters for start timestamp, operating ceiling enforcement, and solver timeout.

        Returns
        -------
        OptimizationResponse
            Detailed before vs after metrics, schedules, and capacity telemetry.
        """
        req = request or OptimizationRequest()

        # 1. Retrieve 24-hour demand forecast
        forecast_svc = ForecastService.get_instance()
        forecast_points = forecast_svc.generate_forecast(
            horizon_hours=24,
            start_time=req.start_time,
        )
        grid_forecast_mw: List[float] = [
            pt["predicted_load_mw"] for pt in forecast_points
        ]

        # 2. Run CP-SAT optimization on default hostel configuration
        scheduler = ApplianceScheduler()
        result = scheduler.optimize(
            grid_forecast_mw=grid_forecast_mw,
            time_limit_seconds=req.time_limit_seconds,
            enforce_operating_ceiling=req.enforce_operating_ceiling,
            strict_feasibility=False,
        )

        # 3. Format structured response
        return OptimizationResponse(
            status=result.status,
            horizon_hours=result.horizon_hours,
            time_step_minutes=result.time_step_minutes,
            baseline_peak_kw=result.baseline_peak_kw,
            optimized_peak_kw=result.optimized_peak_kw,
            peak_reduction_kw=result.peak_reduction_kw,
            peak_reduction_percent=result.peak_reduction_percent,
            baseline_total_energy_kwh=result.baseline_total_energy_kwh,
            optimized_total_energy_kwh=result.optimized_total_energy_kwh,
            hourly_load_before_kw=result.hourly_load_before_kw,
            hourly_load_after_kw=result.hourly_load_after_kw,
            slot_load_before_kw=result.slot_load_before_kw,
            slot_load_after_kw=result.slot_load_after_kw,
            appliance_schedule=result.appliance_schedule,
            transformer_capacity_kw=result.transformer_capacity_kw,
            operating_ceiling_kw=result.operating_ceiling_kw,
            maximum_headroom_kw=result.maximum_headroom_kw,
            minimum_headroom_kw=result.minimum_headroom_kw,
            solver_runtime_seconds=result.solver_runtime_seconds,
            details=result.details,
        )
