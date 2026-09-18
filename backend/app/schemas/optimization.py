"""Pydantic Schemas for GridMind Optimization API."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    """Request payload for running appliance scheduling optimization."""

    start_time: Optional[str] = Field(
        None,
        description="Optional starting timestamp for forecast series (ISO 'YYYY-MM-DD HH:MM:SS'). Defaults to latest dataset observation.",
        examples=["2018-08-02 00:00:00"],
    )
    enforce_operating_ceiling: bool = Field(
        True,
        description="Whether total hostel load must strictly remain <= facility operating ceiling (450 kW)",
    )
    time_limit_seconds: float = Field(
        10.0,
        ge=0.5,
        le=60.0,
        description="Maximum solver search execution time in seconds",
        examples=[10.0],
    )


class OptimizationResponse(BaseModel):
    """Structured output response for GridMind appliance scheduling optimization."""

    status: str = Field(..., description="CP-SAT solver termination status ('OPTIMAL', 'FEASIBLE', 'INFEASIBLE')")
    horizon_hours: int = Field(24, description="Optimization time horizon in hours")
    time_step_minutes: int = Field(30, description="Discrete interval granularity in minutes")

    # Peak demand metrics
    baseline_peak_kw: float = Field(..., description="Peak load BEFORE optimization in kW")
    optimized_peak_kw: float = Field(..., description="Peak load AFTER optimization in kW")
    peak_reduction_kw: float = Field(..., description="Absolute peak load reduction achieved (kW)")
    peak_reduction_percent: float = Field(..., description="Percentage peak reduction achieved (%)")

    # Energy metrics
    baseline_total_energy_kwh: float = Field(..., description="Total daily electrical energy consumption before optimization (kWh)")
    optimized_total_energy_kwh: float = Field(..., description="Total daily electrical energy consumption after optimization (kWh)")

    # Schedules & curves
    hourly_load_before_kw: List[float] = Field(
        ...,
        description="24-hour aggregate hostel demand curve before optimization (kW)",
    )
    hourly_load_after_kw: List[float] = Field(
        ...,
        description="24-hour aggregate hostel demand curve after optimization (kW)",
    )
    slot_load_before_kw: Optional[List[float]] = Field(
        None,
        description="48 half-hour slot demand curve before optimization (kW)",
    )
    slot_load_after_kw: Optional[List[float]] = Field(
        None,
        description="48 half-hour slot demand curve after optimization (kW)",
    )
    appliance_schedule: Dict[str, List[int]] = Field(
        ...,
        description="Optimized schedule mapping appliance category to active unit counts per 30-min slot",
    )

    # Physical capacity & headroom
    transformer_capacity_kw: float = Field(500.0, description="Max physical transformer rating (kW)")
    operating_ceiling_kw: float = Field(450.0, description="Safe operating ceiling (kW)")
    maximum_headroom_kw: float = Field(..., description="Maximum available headroom beneath transformer capacity (kW)")
    minimum_headroom_kw: float = Field(..., description="Minimum headroom remaining at peak hour (kW)")

    # Telemetry
    solver_runtime_seconds: float = Field(..., description="CP-SAT solver computation time in seconds")
    details: Optional[str] = Field(None, description="Diagnostic commentary or solver summary")
