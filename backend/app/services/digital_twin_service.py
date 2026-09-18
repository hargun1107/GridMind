"""Hostel Digital Twin Load Calculation Service.

Calculates deterministic hourly electrical demand profiles for university hostels,
combining inflexible baseloads, scaled grid momentum, and flexible shiftable appliance
fleets while continuously monitoring transformer capacity limits.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import numpy as np

from backend.app.models.hostel import (
    HostelConfig,
    FlexibleApplianceProfile,
    InflexibleLoadProfile,
)
from backend.app.services.scaling_service import scale_grid_forecast_to_hostel_baseline


class SimultaneousUnitExceededError(Exception):
    """Raised when an appliance schedule exceeds the physical simultaneous unit limit."""
    pass


class InvalidScheduleError(Exception):
    """Raised when an appliance schedule violates operating windows or array lengths."""
    pass


class HourlyLoadPoint(BaseModel):
    """Calculated power demand and capacity status for a single hour."""

    hour: int = Field(..., ge=0, le=23, description="Hour of the day (0-23)")
    baseline_load_kw: float = Field(..., ge=0.0, description="Inflexible + scaled background demand in kW")
    appliance_loads_kw: Dict[str, float] = Field(default_factory=dict, description="Active power draw per appliance category in kW")
    total_flexible_load_kw: float = Field(..., ge=0.0, description="Aggregate flexible appliance power in kW")
    total_hostel_load_kw: float = Field(..., ge=0.0, description="Total instantaneous demand (base + appliances) in kW")
    operating_ceiling_kw: float = Field(..., gt=0.0, description="Safe operating threshold limit in kW")
    transformer_capacity_kw: float = Field(..., gt=0.0, description="Max physical transformer rating in kW")
    capacity_headroom_kw: float = Field(..., description="Available headroom beneath transformer capacity in kW")
    ceiling_headroom_kw: float = Field(..., description="Available headroom beneath operating ceiling in kW")
    is_over_ceiling: bool = Field(False, description="True if total load exceeds safe operating threshold")
    is_over_transformer: bool = Field(False, description="True if total load exceeds physical transformer capacity")


class DigitalTwinSimulationResult(BaseModel):
    """Complete 24-hour simulation output and aggregate performance statistics."""

    hourly_loads: List[HourlyLoadPoint] = Field(..., description="24 hourly load calculations")
    peak_load_kw: float = Field(..., description="Maximum instantaneous load across the 24-hour horizon in kW")
    peak_hour: int = Field(..., description="Hour at which peak load occurred")
    min_load_kw: float = Field(..., description="Minimum load across the horizon in kW")
    total_energy_kwh: float = Field(..., description="Total daily electrical energy consumption in kWh")
    ceiling_breach_count: int = Field(..., description="Number of hours exceeding operating ceiling")
    transformer_breach_count: int = Field(..., description="Number of hours exceeding transformer capacity")


class HostelDigitalTwin:
    """Deterministic Digital Twin service for load simulation and constraint evaluation."""

    def __init__(self, config: Optional[HostelConfig] = None):
        if config is None:
            self.config = HostelConfig.create_default_500_student_hostel()
        else:
            self.config = config

    def calculate_hourly_baseline(
        self,
        grid_forecast_mw: Optional[List[float]] = None,
    ) -> List[float]:
        """Calculate the 24-hour non-shiftable baseline load.

        Combines:
        1. Constant baseline power (facility.baseline_power_kw)
        2. Scaled grid forecast profile (if provided)
        3. Scheduled inflexible facility loads (corridor lights, study rooms, etc.)

        Returns
        -------
        List[float]
            24 values representing baseline demand in kW.
        """
        facility = self.config.facility
        scaled_grid = (
            scale_grid_forecast_to_hostel_baseline(
                grid_forecast_mw,
                self.config.scaling,
                facility_config=facility,
            )
            if grid_forecast_mw
            else [0.0] * 24
        )

        baseline_curve = []
        for h in range(24):
            # Constant base + scaled grid activity
            load = facility.baseline_power_kw + scaled_grid[h]

            # Add scheduled inflexible loads active at hour h
            for _, infl_load in self.config.inflexible_loads.items():
                if h in infl_load.active_hours:
                    load += infl_load.power_kw

            baseline_curve.append(round(float(load), 2))

        return baseline_curve

    def generate_unoptimized_appliance_schedule(self) -> Dict[str, List[int]]:
        """Generate the default unshifted appliance schedule reflecting typical human habits.

        Appliances run starting at their `preferred_start_hour` in batches respecting
        `maximum_simultaneous_units` until all units complete their required runtime.
        """
        schedule: Dict[str, List[int]] = {
            app_type: [0] * 24 for app_type in self.config.flexible_appliances.keys()
        }

        for app_type, app in self.config.flexible_appliances.items():
            start_hour = app.preferred_start_hour if app.preferred_start_hour is not None else app.earliest_start_hour
            runtime_int = max(1, int(np.ceil(app.runtime_hours)))
            remaining_units = app.quantity
            current_h = start_hour

            while remaining_units > 0 and current_h < app.latest_finish_hour:
                batch = min(remaining_units, app.maximum_simultaneous_units)
                for r in range(runtime_int):
                    if current_h + r < 24:
                        schedule[app_type][current_h + r] = min(
                            app.maximum_simultaneous_units,
                            schedule[app_type][current_h + r] + batch,
                        )
                remaining_units -= batch
                current_h += runtime_int

        return schedule

    def simulate_24h(
        self,
        appliance_schedule: Optional[Dict[str, List[int]]] = None,
        grid_forecast_mw: Optional[List[float]] = None,
    ) -> DigitalTwinSimulationResult:
        """Simulate 24-hour electrical demand for the hostel.

        Parameters
        ----------
        appliance_schedule : Optional[Dict[str, List[int]]]
            Matrix mapping appliance_type to a list of 24 integers representing active units.
            If None, the default unoptimized schedule is used.
        grid_forecast_mw : Optional[List[float]]
            Optional 24-hour utility grid forecast (MW) to dynamically scale baseline activity.

        Returns
        -------
        DigitalTwinSimulationResult
            Detailed breakdown of hourly loads, headroom, and overage flags.
        """
        if appliance_schedule is None:
            active_schedule = self.generate_unoptimized_appliance_schedule()
        else:
            active_schedule = appliance_schedule

        # Validate schedule dimensions and simultaneous unit constraints
        for app_type, hourly_units in active_schedule.items():
            if len(hourly_units) != 24:
                raise InvalidScheduleError(
                    f"Schedule for '{app_type}' must contain exactly 24 hourly steps; got {len(hourly_units)}."
                )

            if app_type in self.config.flexible_appliances:
                app = self.config.flexible_appliances[app_type]
                for h, units in enumerate(hourly_units):
                    if units < 0:
                        raise InvalidScheduleError(f"Negative unit count ({units}) at hour {h} for '{app_type}'.")
                    if units > app.maximum_simultaneous_units:
                        raise SimultaneousUnitExceededError(
                            f"Hour {h}: {units} active units for '{app_type}' exceeds "
                            f"simultaneous limit of {app.maximum_simultaneous_units}."
                        )
                    # Check operational window
                    if units > 0 and (h < app.earliest_start_hour or h >= app.latest_finish_hour):
                        raise InvalidScheduleError(
                            f"Hour {h}: active units ({units}) scheduled outside permitted window "
                            f"[{app.earliest_start_hour}:00, {app.latest_finish_hour}:00) for '{app_type}'."
                        )

        # 1. Calculate baseload curve
        baseline_loads = self.calculate_hourly_baseline(grid_forecast_mw=grid_forecast_mw)

        # 2. Calculate hourly appliance power and totals
        facility = self.config.facility
        hourly_results: List[HourlyLoadPoint] = []
        total_energy_kwh = 0.0
        ceiling_breaches = 0
        transformer_breaches = 0

        for h in range(24):
            base_kw = baseline_loads[h]
            app_draws: Dict[str, float] = {}
            flex_total_kw = 0.0

            for app_type, units_list in active_schedule.items():
                if app_type in self.config.flexible_appliances:
                    app = self.config.flexible_appliances[app_type]
                    active_count = units_list[h]
                    draw_kw = round(active_count * app.power_kw, 2)
                    app_draws[app_type] = draw_kw
                    flex_total_kw += draw_kw

            flex_total_kw = round(flex_total_kw, 2)
            total_kw = round(base_kw + flex_total_kw, 2)
            total_energy_kwh += total_kw  # 1 hour steps -> kWh == kW * 1h

            cap_headroom = round(facility.transformer_capacity_kw - total_kw, 2)
            ceil_headroom = round(facility.operating_ceiling_kw - total_kw, 2)

            is_over_ceil = total_kw > facility.operating_ceiling_kw
            is_over_trans = total_kw > facility.transformer_capacity_kw

            if is_over_ceil:
                ceiling_breaches += 1
            if is_over_trans:
                transformer_breaches += 1

            hourly_results.append(
                HourlyLoadPoint(
                    hour=h,
                    baseline_load_kw=base_kw,
                    appliance_loads_kw=app_draws,
                    total_flexible_load_kw=flex_total_kw,
                    total_hostel_load_kw=total_kw,
                    operating_ceiling_kw=facility.operating_ceiling_kw,
                    transformer_capacity_kw=facility.transformer_capacity_kw,
                    capacity_headroom_kw=cap_headroom,
                    ceiling_headroom_kw=ceil_headroom,
                    is_over_ceiling=is_over_ceil,
                    is_over_transformer=is_over_trans,
                )
            )

        loads_arr = np.array([pt.total_hostel_load_kw for pt in hourly_results])
        peak_idx = int(np.argmax(loads_arr))

        return DigitalTwinSimulationResult(
            hourly_loads=hourly_results,
            peak_load_kw=float(loads_arr[peak_idx]),
            peak_hour=peak_idx,
            min_load_kw=float(np.min(loads_arr)),
            total_energy_kwh=round(total_energy_kwh, 2),
            ceiling_breach_count=ceiling_breaches,
            transformer_breach_count=transformer_breaches,
        )
