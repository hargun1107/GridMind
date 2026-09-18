"""What-If Simulation Service Module for GridMind.

Orchestrates:
- Deep copying and modifying HostelConfig parameters from scenario requests
- Validating scenario feasibility and physical constraint consistency
- Simulating unoptimized and CP-SAT optimized demand curves
- Generating comparative before vs after analytics contrasting the default benchmark against the scenario
"""

import copy
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import ValidationError

from backend.app.models.hostel import (
    HostelConfig,
    FacilityConfig,
    FlexibleApplianceProfile,
)
from backend.app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
    ScenarioMetrics,
    ScenarioComparison,
)
from backend.app.services.forecast_service import ForecastService
from optimization.scheduler import ApplianceScheduler

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "sample"
    / "hostel_config_default.json"
)


class ScenarioValidationError(Exception):
    """Raised when a simulation scenario contains physically or operationally invalid parameters."""
    pass


class SimulationService:
    """Production service for deterministic what-if scenario simulations."""

    _instance: Optional["SimulationService"] = None

    @classmethod
    def get_instance(cls) -> "SimulationService":
        """Singleton accessor for the simulation service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_default_config(self) -> HostelConfig:
        """Load the pristine default 500-student hostel configuration."""
        if DEFAULT_CONFIG_PATH.exists():
            return HostelConfig.load_from_file(DEFAULT_CONFIG_PATH)
        return HostelConfig.create_default_500_student_hostel()

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        """Execute a deterministic what-if simulation comparing baseline vs scenario.

        Parameters
        ----------
        request : SimulationRequest
            Requested scenario overrides (e.g. students, ceiling, appliance counts/ratings).

        Returns
        -------
        SimulationResponse
            Comparative analytics contrasting default benchmark against the simulated scenario.
        """
        # 1. Start from default configuration
        default_config = self._get_default_config()
        sim_config = copy.deepcopy(default_config)

        # 2. Apply Facility Overrides
        if request.total_students is not None:
            sim_config.facility.total_students = request.total_students
        if request.transformer_capacity_kw is not None:
            sim_config.facility.transformer_capacity_kw = request.transformer_capacity_kw
        if request.operating_ceiling_kw is not None:
            sim_config.facility.operating_ceiling_kw = request.operating_ceiling_kw
        if request.baseline_power_kw is not None:
            sim_config.facility.baseline_power_kw = request.baseline_power_kw

        # 3. Apply Grid Scaling Overrides
        if request.min_baseline_kw is not None:
            sim_config.scaling.min_baseline_kw = request.min_baseline_kw
        if request.max_baseline_kw is not None:
            sim_config.scaling.max_baseline_kw = request.max_baseline_kw

        # 4. Apply Flexible Appliance Overrides
        # a. Geysers
        if "geyser" in sim_config.flexible_appliances:
            g = sim_config.flexible_appliances["geyser"]
            if request.geyser_quantity is not None:
                g.quantity = request.geyser_quantity
                if request.geyser_max_simultaneous is None and g.maximum_simultaneous_units > g.quantity:
                    g.maximum_simultaneous_units = g.quantity
            if request.geyser_power_kw is not None:
                g.power_kw = request.geyser_power_kw
            if request.geyser_max_simultaneous is not None:
                if request.geyser_max_simultaneous > g.quantity:
                    raise ScenarioValidationError(
                        f"geyser_max_simultaneous ({request.geyser_max_simultaneous}) "
                        f"cannot exceed geyser_quantity ({g.quantity})."
                    )
                g.maximum_simultaneous_units = request.geyser_max_simultaneous

        # b. Washing Machines
        if "washing_machine" in sim_config.flexible_appliances:
            w = sim_config.flexible_appliances["washing_machine"]
            if request.washing_machine_quantity is not None:
                w.quantity = request.washing_machine_quantity
                if request.washing_machine_max_simultaneous is None and w.maximum_simultaneous_units > w.quantity:
                    w.maximum_simultaneous_units = w.quantity
            if request.washing_machine_power_kw is not None:
                w.power_kw = request.washing_machine_power_kw
            if request.washing_machine_max_simultaneous is not None:
                if request.washing_machine_max_simultaneous > w.quantity:
                    raise ScenarioValidationError(
                        f"washing_machine_max_simultaneous ({request.washing_machine_max_simultaneous}) "
                        f"cannot exceed washing_machine_quantity ({w.quantity})."
                    )
                w.maximum_simultaneous_units = request.washing_machine_max_simultaneous

        # c. Device Charging
        if "device_charging" in sim_config.flexible_appliances:
            c = sim_config.flexible_appliances["device_charging"]
            if request.device_charging_quantity is not None:
                c.quantity = request.device_charging_quantity
                if request.device_charging_max_simultaneous is None and c.maximum_simultaneous_units > c.quantity:
                    c.maximum_simultaneous_units = c.quantity
            if request.device_charging_power_kw is not None:
                c.power_kw = request.device_charging_power_kw
            if request.device_charging_max_simultaneous is not None:
                if request.device_charging_max_simultaneous > c.quantity:
                    raise ScenarioValidationError(
                        f"device_charging_max_simultaneous ({request.device_charging_max_simultaneous}) "
                        f"cannot exceed device_charging_quantity ({c.quantity})."
                    )
                c.maximum_simultaneous_units = request.device_charging_max_simultaneous

        # 5. Validate the resulting modified configuration against all domain rules
        try:
            # Re-validate facility, appliances, and overall configuration
            FacilityConfig.model_validate(sim_config.facility.model_dump())
            for app_type, app in sim_config.flexible_appliances.items():
                FlexibleApplianceProfile.model_validate(app.model_dump())
            HostelConfig.model_validate(sim_config.model_dump())
        except (ValidationError, ValueError) as exc:
            raise ScenarioValidationError(f"Invalid scenario configuration: {exc}") from exc

        # 6. Retrieve dynamic 24-hour demand forecast
        forecast_svc = ForecastService.get_instance()
        forecast_points = forecast_svc.generate_forecast(
            horizon_hours=24,
            start_time=request.start_time,
        )
        grid_forecast_mw: List[float] = [
            pt["predicted_load_mw"] for pt in forecast_points
        ]

        # 7. Run Reference Baseline Optimization (default 500-student hostel)
        base_scheduler = ApplianceScheduler(hostel_config=default_config)
        base_res = base_scheduler.optimize(
            grid_forecast_mw=grid_forecast_mw,
            time_limit_seconds=request.time_limit_seconds,
            enforce_operating_ceiling=True,
            strict_feasibility=False,
        )

        # 8. Run Simulated Scenario Optimization
        sim_scheduler = ApplianceScheduler(hostel_config=sim_config)
        sim_res = sim_scheduler.optimize(
            grid_forecast_mw=grid_forecast_mw,
            time_limit_seconds=request.time_limit_seconds,
            enforce_operating_ceiling=True,
            strict_feasibility=False,
        )

        is_feasible = sim_res.status in ("OPTIMAL", "FEASIBLE")

        # 9. Calculate Scenario Contrast Metrics
        base_metrics = ScenarioMetrics(
            unoptimized_peak_kw=base_res.baseline_peak_kw,
            optimized_peak_kw=base_res.optimized_peak_kw,
            peak_reduction_kw=base_res.peak_reduction_kw,
            peak_reduction_percent=base_res.peak_reduction_percent,
            total_energy_kwh=base_res.optimized_total_energy_kwh,
        )

        sim_metrics = ScenarioMetrics(
            unoptimized_peak_kw=sim_res.baseline_peak_kw,
            optimized_peak_kw=sim_res.optimized_peak_kw,
            peak_reduction_kw=sim_res.peak_reduction_kw,
            peak_reduction_percent=sim_res.peak_reduction_percent,
            total_energy_kwh=sim_res.optimized_total_energy_kwh,
        )

        peak_diff = round(sim_res.optimized_peak_kw - base_res.optimized_peak_kw, 2)
        peak_diff_pct = (
            round((peak_diff / base_res.optimized_peak_kw) * 100.0, 2)
            if base_res.optimized_peak_kw > 0.0
            else 0.0
        )
        energy_diff = round(sim_res.optimized_total_energy_kwh - base_res.optimized_total_energy_kwh, 2)

        comparison = ScenarioComparison(
            baseline_peak_kw=base_res.optimized_peak_kw,
            simulated_peak_kw=sim_res.optimized_peak_kw,
            peak_difference_kw=peak_diff,
            peak_difference_percent=peak_diff_pct,
            baseline_energy_kwh=base_res.optimized_total_energy_kwh,
            simulated_energy_kwh=sim_res.optimized_total_energy_kwh,
            energy_difference_kwh=energy_diff,
            is_feasible=is_feasible,
            solver_status=sim_res.status,
        )

        # 10. Extract Disaggregated Load Curves
        sim_baseline_kw = sim_scheduler.twin.calculate_hourly_baseline(
            grid_forecast_mw=grid_forecast_mw
        )

        # Collect applied parameter overrides for auditing
        applied_params = {
            k: v
            for k, v in request.model_dump().items()
            if v is not None and k not in ("time_limit_seconds", "start_time")
        }

        return SimulationResponse(
            status=sim_res.status,
            is_feasible=is_feasible,
            baseline_scenario=base_metrics,
            simulated_scenario=sim_metrics,
            comparison=comparison,
            forecasted_demand_mw=grid_forecast_mw,
            hourly_baseline_load_kw=sim_baseline_kw,
            hourly_load_before_kw=sim_res.hourly_load_before_kw,
            hourly_load_after_kw=sim_res.hourly_load_after_kw,
            slot_load_before_kw=sim_res.slot_load_before_kw,
            slot_load_after_kw=sim_res.slot_load_after_kw,
            appliance_schedule=sim_res.appliance_schedule,
            transformer_capacity_kw=sim_config.facility.transformer_capacity_kw,
            operating_ceiling_kw=sim_config.facility.operating_ceiling_kw,
            maximum_headroom_kw=sim_res.maximum_headroom_kw,
            minimum_headroom_kw=sim_res.minimum_headroom_kw,
            solver_runtime_seconds=sim_res.solver_runtime_seconds,
            scenario_parameters_applied=applied_params,
            details=sim_res.details,
        )
