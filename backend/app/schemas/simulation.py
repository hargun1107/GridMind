"""Pydantic Schemas for GridMind What-If Simulation API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator


class SimulationRequest(BaseModel):
    """Configurable scenario parameter overrides for deterministic what-if simulation."""

    total_students: Optional[int] = Field(
        None,
        gt=0,
        description="Resident student population (must be > 0)",
        examples=[600],
    )
    transformer_capacity_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Transformer physical rating in kW (must be > 0)",
        examples=[500.0],
    )
    operating_ceiling_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Safe operating ceiling in kW (must be <= transformer capacity)",
        examples=[450.0],
    )
    baseline_power_kw: Optional[float] = Field(
        None,
        ge=0.0,
        description="Constant unshiftable baseline power in kW (must be < operating ceiling)",
        examples=[30.0],
    )
    min_baseline_kw: Optional[float] = Field(
        None,
        ge=0.0,
        description="Minimum scaled baseline power during dormant hours in kW",
        examples=[25.0],
    )
    max_baseline_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Maximum scaled baseline power during peak hours in kW",
        examples=[130.0],
    )
    geyser_quantity: Optional[int] = Field(
        None,
        gt=0,
        description="Total water heater / geyser unit count (must be > 0)",
        examples=[150],
    )
    geyser_power_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Power rating per geyser in kW",
        examples=[2.0],
    )
    geyser_max_simultaneous: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum simultaneous geyser units permitted",
        examples=[75],
    )
    washing_machine_quantity: Optional[int] = Field(
        None,
        gt=0,
        description="Total washing machine count (must be > 0)",
        examples=[30],
    )
    washing_machine_power_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Power rating per washing machine in kW",
        examples=[0.7],
    )
    washing_machine_max_simultaneous: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum simultaneous washing machines permitted",
        examples=[15],
    )
    device_charging_quantity: Optional[int] = Field(
        None,
        gt=0,
        description="Total device charging stations (must be > 0)",
        examples=[350],
    )
    device_charging_power_kw: Optional[float] = Field(
        None,
        gt=0.0,
        description="Power rating per charging station in kW",
        examples=[0.1],
    )
    device_charging_max_simultaneous: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum simultaneous charging stations permitted",
        examples=[175],
    )
    start_time: Optional[str] = Field(
        None,
        description="Optional starting timestamp for forecast context (ISO 'YYYY-MM-DD HH:MM:SS')",
        examples=["2018-08-02 00:00:00"],
    )
    time_limit_seconds: float = Field(
        10.0,
        ge=0.5,
        le=60.0,
        description="Maximum solver runtime limit in seconds",
        examples=[10.0],
    )

    @model_validator(mode="after")
    def validate_simulation_inputs(self) -> "SimulationRequest":
        """Validate inter-field consistency rules."""
        if self.operating_ceiling_kw is not None and self.transformer_capacity_kw is not None:
            if self.operating_ceiling_kw > self.transformer_capacity_kw:
                raise ValueError(
                    f"Operating ceiling ({self.operating_ceiling_kw} kW) cannot exceed "
                    f"transformer capacity ({self.transformer_capacity_kw} kW)."
                )
        if self.baseline_power_kw is not None and self.operating_ceiling_kw is not None:
            if self.baseline_power_kw >= self.operating_ceiling_kw:
                raise ValueError(
                    f"Baseline power ({self.baseline_power_kw} kW) must be strictly below "
                    f"operating ceiling ({self.operating_ceiling_kw} kW)."
                )
        if self.min_baseline_kw is not None and self.max_baseline_kw is not None:
            if self.min_baseline_kw >= self.max_baseline_kw:
                raise ValueError(
                    f"min_baseline_kw ({self.min_baseline_kw} kW) must be strictly less than "
                    f"max_baseline_kw ({self.max_baseline_kw} kW)."
                )
        if self.geyser_max_simultaneous is not None and self.geyser_quantity is not None:
            if self.geyser_max_simultaneous > self.geyser_quantity:
                raise ValueError("geyser_max_simultaneous cannot exceed geyser_quantity.")
        if self.washing_machine_max_simultaneous is not None and self.washing_machine_quantity is not None:
            if self.washing_machine_max_simultaneous > self.washing_machine_quantity:
                raise ValueError("washing_machine_max_simultaneous cannot exceed washing_machine_quantity.")
        if self.device_charging_max_simultaneous is not None and self.device_charging_quantity is not None:
            if self.device_charging_max_simultaneous > self.device_charging_quantity:
                raise ValueError("device_charging_max_simultaneous cannot exceed device_charging_quantity.")
        return self


class ScenarioMetrics(BaseModel):
    """Aggregate electrical demand and consumption metrics for a specific scenario."""

    unoptimized_peak_kw: float = Field(..., description="Peak load before optimization (kW)")
    optimized_peak_kw: float = Field(..., description="Peak load after CP-SAT optimization (kW)")
    peak_reduction_kw: float = Field(..., description="Absolute peak load reduction achieved (kW)")
    peak_reduction_percent: float = Field(..., description="Percentage peak reduction achieved (%)")
    total_energy_kwh: float = Field(..., description="Total daily electrical energy consumed (kWh)")


class ScenarioComparison(BaseModel):
    """Contrast between the default reference benchmark and the simulated scenario."""

    baseline_peak_kw: float = Field(..., description="Peak load of default benchmark (kW)")
    simulated_peak_kw: float = Field(..., description="Peak load of simulated scenario (kW)")
    peak_difference_kw: float = Field(..., description="Absolute difference in peak load (simulated - baseline) in kW")
    peak_difference_percent: float = Field(..., description="Percentage difference in peak load (%)")
    baseline_energy_kwh: float = Field(..., description="Total energy of default benchmark (kWh)")
    simulated_energy_kwh: float = Field(..., description="Total energy of simulated scenario (kWh)")
    energy_difference_kwh: float = Field(..., description="Energy difference (simulated - baseline) in kWh")
    is_feasible: bool = Field(..., description="Whether the simulated scenario is physically and operationally feasible")
    solver_status: str = Field(..., description="CP-SAT solver termination status ('OPTIMAL', 'FEASIBLE', 'INFEASIBLE')")


class SimulationResponse(BaseModel):
    """Structured response contract for what-if scenario simulations."""

    status: str = Field(..., description="Solver status ('OPTIMAL', 'FEASIBLE', 'INFEASIBLE')")
    is_feasible: bool = Field(..., description="True if scenario can be satisfied within all limits")

    # High-level scenario contrast
    baseline_scenario: ScenarioMetrics = Field(..., description="Default 500-student hostel metrics")
    simulated_scenario: ScenarioMetrics = Field(..., description="Simulated scenario metrics")
    comparison: ScenarioComparison = Field(..., description="Direct comparative delta metrics")

    # Disaggregated load series
    forecasted_demand_mw: List[float] = Field(..., description="24-hour utility grid load forecast in MW")
    hourly_baseline_load_kw: List[float] = Field(..., description="Simulated 24-hour non-shiftable base load in kW")
    hourly_load_before_kw: List[float] = Field(..., description="Simulated 24-hour hostel demand before optimization in kW")
    hourly_load_after_kw: List[float] = Field(..., description="Simulated 24-hour hostel demand after optimization in kW")
    slot_load_before_kw: Optional[List[float]] = Field(None, description="48 half-hour slot demand before optimization in kW")
    slot_load_after_kw: Optional[List[float]] = Field(None, description="48 half-hour slot demand after optimization in kW")
    appliance_schedule: Dict[str, List[int]] = Field(
        ...,
        description="Optimized schedule mapping appliance category to active units per 30-min slot",
    )

    # Physical thresholds & headroom
    transformer_capacity_kw: float = Field(..., description="Simulated transformer capacity in kW")
    operating_ceiling_kw: float = Field(..., description="Simulated operating ceiling in kW")
    maximum_headroom_kw: float = Field(..., description="Maximum available headroom beneath transformer capacity (kW)")
    minimum_headroom_kw: float = Field(..., description="Minimum headroom remaining at peak hour (kW)")

    # Execution telemetry
    solver_runtime_seconds: float = Field(..., description="CP-SAT solver computation time in seconds")
    scenario_parameters_applied: Dict[str, Any] = Field(..., description="Summary of applied scenario parameter overrides")
    details: Optional[str] = Field(None, description="Diagnostic commentary or explanation")
