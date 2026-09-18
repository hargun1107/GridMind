"""Optimization Domain Models and Result Schemas for GridMind."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OptimizationStatus(str, Enum):
    """Solver termination status classifications."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    MODEL_INVALID = "MODEL_INVALID"
    UNKNOWN = "UNKNOWN"


class InfeasibleScheduleError(Exception):
    """Raised when an appliance configuration is mathematically impossible under configured constraints."""
    pass


class OptimizationResult(BaseModel):
    """Structured output contract of the CP-SAT appliance scheduling engine."""

    status: str = Field(..., description="Solver status ('OPTIMAL', 'FEASIBLE', 'INFEASIBLE')")
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
    appliance_schedule: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Optimized schedule mapping appliance category to active unit counts per time slot",
    )
    hourly_load_before_kw: List[float] = Field(
        default_factory=list,
        description="24-hour aggregate hostel demand curve before optimization (kW)",
    )
    hourly_load_after_kw: List[float] = Field(
        default_factory=list,
        description="24-hour aggregate hostel demand curve after optimization (kW)",
    )
    slot_load_before_kw: Optional[List[float]] = Field(
        default=None,
        description="48 half-hour slot demand curve before optimization (kW)",
    )
    slot_load_after_kw: Optional[List[float]] = Field(
        default=None,
        description="48 half-hour slot demand curve after optimization (kW)",
    )

    # Physical limits & headroom
    transformer_capacity_kw: float = Field(500.0, description="Max physical transformer rating (kW)")
    operating_ceiling_kw: float = Field(450.0, description="Safe operating ceiling (kW)")
    maximum_headroom_kw: float = Field(..., description="Maximum available headroom beneath transformer capacity (kW)")
    minimum_headroom_kw: float = Field(..., description="Minimum headroom remaining at peak hour (kW)")

    # Execution telemetry
    solver_runtime_seconds: float = Field(..., description="CP-SAT solver computation time in seconds")
    details: Optional[str] = Field(None, description="Diagnostic commentary or infeasibility cause")
