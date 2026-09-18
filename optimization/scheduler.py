"""Google OR-Tools CP-SAT Appliance Scheduling Optimization Engine for GridMind.

Formulates and solves the discrete-interval constrained appliance scheduling problem:
- Horizon: 24 hours discretized into 30-minute intervals (48 slots).
- Decision Variables: Number of appliance units initiated at each time slot.
- Constraints: Fleet completion, concurrency limits, operating windows, transformer capacity.
- Primary Objective: Minimize maximum instantaneous peak load (kW).
- Secondary Objective: Minimize user schedule deviation / convenience penalty.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from ortools.sat.python import cp_model

from backend.app.models.hostel import HostelConfig, FlexibleApplianceProfile
from backend.app.services.digital_twin_service import HostelDigitalTwin
from optimization.models import (
    OptimizationResult,
    OptimizationStatus,
    InfeasibleScheduleError,
)
from optimization.objective import (
    PEAK_MINIMIZATION_WEIGHT,
    CONVENIENCE_PENALTY_WEIGHT,
)


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sample" / "hostel_config_default.json"
)


class ApplianceScheduler:
    """Discrete-time appliance scheduler powered by OR-Tools CP-SAT."""

    def __init__(
        self,
        hostel_config: Optional[HostelConfig] = None,
        time_step_minutes: int = 30,
        scaling_factor: int = 100,  # 100 -> 0.01 kW (10 Watts) precision in integer solver
    ):
        if hostel_config is not None:
            self.config = hostel_config
        elif DEFAULT_CONFIG_PATH.exists():
            self.config = HostelConfig.load_from_file(DEFAULT_CONFIG_PATH)
        else:
            self.config = HostelConfig.create_default_500_student_hostel()

        self.time_step_minutes = time_step_minutes
        self.dt_hours = time_step_minutes / 60.0
        self.num_slots = int(24.0 / self.dt_hours)  # 48 slots for 30-min intervals
        self.scaling_factor = scaling_factor
        self.twin = HostelDigitalTwin(config=self.config)

    def _discretize_baseline(self, grid_forecast_mw: Optional[List[float]] = None) -> List[float]:
        """Expand 24-hour baseline load into 30-minute discrete slots."""
        hourly_base = self.twin.calculate_hourly_baseline(grid_forecast_mw=grid_forecast_mw)
        slot_base: List[float] = []
        slots_per_hour = int(60 / self.time_step_minutes)

        for val in hourly_base:
            for _ in range(slots_per_hour):
                slot_base.append(val)

        return slot_base

    def generate_baseline_unoptimized_schedule(self) -> Dict[str, List[int]]:
        """Construct the deterministic unoptimized baseline schedule in 30-min resolution.

        In the unoptimized baseline, appliances start at their preferred hour in sequential
        batches respecting concurrency limits.

        Returns
        -------
        Dict[str, List[int]]
            Active units per slot per appliance category across the 48 half-hour slots.
        """
        slot_schedule: Dict[str, List[int]] = {
            app_type: [0] * self.num_slots
            for app_type in self.config.flexible_appliances.keys()
        }

        for app_type, app in self.config.flexible_appliances.items():
            start_hour = app.preferred_start_hour if app.preferred_start_hour is not None else app.earliest_start_hour
            start_slot = int(start_hour / self.dt_hours)
            finish_slot = int(app.latest_finish_hour / self.dt_hours)
            duration_slots = max(1, int(round(app.runtime_hours / self.dt_hours)))

            remaining = app.quantity
            current_slot = start_slot

            while remaining > 0 and current_slot < finish_slot:
                batch = min(remaining, app.maximum_simultaneous_units)
                for d in range(duration_slots):
                    if current_slot + d < self.num_slots:
                        slot_schedule[app_type][current_slot + d] = min(
                            app.maximum_simultaneous_units,
                            slot_schedule[app_type][current_slot + d] + batch,
                        )
                remaining -= batch
                current_slot += duration_slots

        return slot_schedule

    def optimize(
        self,
        grid_forecast_mw: Optional[List[float]] = None,
        time_limit_seconds: float = 10.0,
        enforce_operating_ceiling: bool = True,
        strict_feasibility: bool = False,
    ) -> OptimizationResult:
        """Run CP-SAT optimization to minimize peak hostel electrical demand.

        Parameters
        ----------
        grid_forecast_mw : Optional[List[float]]
            24-hour utility grid load forecast in MW.
        time_limit_seconds : float
            Maximum solver search execution time.
        enforce_operating_ceiling : bool
            Whether to enforce total load <= facility.operating_ceiling_kw (450 kW).
        strict_feasibility : bool
            If True, raises InfeasibleScheduleError on infeasibility rather than
            returning a structured result.

        Returns
        -------
        OptimizationResult
            Detailed optimization results including before vs after metrics and schedules.
        """
        start_exec_time = time.perf_counter()

        # 1. Prepare discretized baseload
        base_slot_kw = self._discretize_baseline(grid_forecast_mw=grid_forecast_mw)
        facility = self.config.facility
        ceiling_kw = facility.operating_ceiling_kw
        transformer_kw = facility.transformer_capacity_kw

        # 2. Calculate Unoptimized Baseline Schedule (BEFORE)
        baseline_slot_schedule = self.generate_baseline_unoptimized_schedule()
        slot_load_before = list(base_slot_kw)

        for app_type, units_list in baseline_slot_schedule.items():
            power = self.config.flexible_appliances[app_type].power_kw
            for t in range(self.num_slots):
                slot_load_before[t] += units_list[t] * power

        slot_load_before = [round(v, 2) for v in slot_load_before]
        baseline_peak_kw = round(float(max(slot_load_before)), 2)
        baseline_total_energy_kwh = round(float(sum(slot_load_before) * self.dt_hours), 2)

        # 3. Construct CP-SAT Constraint Programming Model
        model = cp_model.CpModel()

        # Decision Variables: starts[app_type, t] = count of units starting at slot t
        starts_vars: Dict[str, Dict[int, cp_model.IntVar]] = {}
        active_vars: Dict[str, Dict[int, Any]] = {}

        for app_type, app in self.config.flexible_appliances.items():
            starts_vars[app_type] = {}
            active_vars[app_type] = {}

            duration_slots = max(1, int(round(app.runtime_hours / self.dt_hours)))
            earliest_slot = int(app.earliest_start_hour / self.dt_hours)
            latest_finish_slot = int(app.latest_finish_hour / self.dt_hours)
            latest_start_slot = latest_finish_slot - duration_slots

            # Create start variables only within allowed operating window
            valid_start_slots = []
            for t in range(self.num_slots):
                if earliest_slot <= t <= latest_start_slot:
                    var = model.NewIntVar(
                        0,
                        min(app.quantity, app.maximum_simultaneous_units),
                        f"start_{app_type}_{t}",
                    )
                    starts_vars[app_type][t] = var
                    valid_start_slots.append(var)
                else:
                    starts_vars[app_type][t] = None

            # Constraint 1: Fleet Energy / Total Quantity Requirement
            # Sum of starts over all permitted slots MUST equal the total quantity
            model.Add(sum(valid_start_slots) == app.quantity)

            # Expression for active units at slot t
            for t in range(self.num_slots):
                active_contributors = []
                for tau in range(max(0, t - duration_slots + 1), t + 1):
                    if starts_vars[app_type][tau] is not None:
                        active_contributors.append(starts_vars[app_type][tau])

                if active_contributors:
                    active_expr = sum(active_contributors)
                    active_vars[app_type][t] = active_expr

                    # Constraint 2: Simultaneous Units Cap
                    model.Add(active_expr <= app.maximum_simultaneous_units)
                else:
                    active_vars[app_type][t] = 0

        # Integer scaled physical parameters
        F = self.scaling_factor
        ceiling_scaled = int(round(ceiling_kw * F))
        transformer_scaled = int(round(transformer_kw * F))

        # Peak load variable
        peak_var_scaled = model.NewIntVar(0, transformer_scaled, "peak_load_scaled")

        total_slot_load_exprs = []
        for t in range(self.num_slots):
            base_scaled = int(round(base_slot_kw[t] * F))

            # Sum of active loads across all appliances
            flex_draws = []
            for app_type, app in self.config.flexible_appliances.items():
                app_power_scaled = int(round(app.power_kw * F))
                act = active_vars[app_type][t]
                if not isinstance(act, int):
                    flex_draws.append(act * app_power_scaled)

            slot_total_expr = base_scaled + sum(flex_draws)
            total_slot_load_exprs.append(slot_total_expr)

            # Constraint 3: Operating Ceiling / Transformer Limit
            if enforce_operating_ceiling:
                model.Add(slot_total_expr <= ceiling_scaled)
            else:
                model.Add(slot_total_expr <= transformer_scaled)

            # Constraint 4: Peak Load Tracking
            model.Add(peak_var_scaled >= slot_total_expr)

        # 4. Multi-Objective Function
        # Objective = PEAK_WEIGHT * peak_load_scaled + CONVENIENCE_WEIGHT * penalty_sum
        convenience_penalties = []
        for app_type, app in self.config.flexible_appliances.items():
            pref_h = app.preferred_start_hour if app.preferred_start_hour is not None else app.earliest_start_hour
            pref_slot = int(pref_h / self.dt_hours)

            for t, start_var in starts_vars[app_type].items():
                if start_var is not None:
                    # Inconvenience penalty proportional to distance from preferred hour
                    hours_diff = abs(t - pref_slot) * self.dt_hours
                    penalty_rate = app.shift_penalty_per_hour
                    # Penalty scaled by factor of 10
                    penalty_coef = int(round(hours_diff * penalty_rate * 10))
                    if penalty_coef > 0:
                        convenience_penalties.append(start_var * penalty_coef)

        objective_expr = (
            PEAK_MINIMIZATION_WEIGHT * peak_var_scaled
            + CONVENIENCE_PENALTY_WEIGHT * sum(convenience_penalties)
        )
        model.Minimize(objective_expr)

        # 5. Solve CP-SAT Model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 1  # Guaranteed deterministic solution
        solver.parameters.random_seed = 42

        solve_status = solver.Solve(model)
        elapsed_seconds = round(time.perf_counter() - start_exec_time, 4)

        status_str = solver.StatusName(solve_status)

        if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if strict_feasibility:
                raise InfeasibleScheduleError(
                    f"CP-SAT solver returned {status_str}. Configured appliances cannot fit "
                    f"within operating ceiling of {ceiling_kw} kW and operational windows."
                )

            return OptimizationResult(
                status=status_str,
                horizon_hours=24,
                time_step_minutes=self.time_step_minutes,
                baseline_peak_kw=baseline_peak_kw,
                optimized_peak_kw=baseline_peak_kw,
                peak_reduction_kw=0.0,
                peak_reduction_percent=0.0,
                baseline_total_energy_kwh=baseline_total_energy_kwh,
                optimized_total_energy_kwh=baseline_total_energy_kwh,
                appliance_schedule={},
                hourly_load_before_kw=[],
                hourly_load_after_kw=[],
                slot_load_before_kw=[],
                slot_load_after_kw=[],
                transformer_capacity_kw=transformer_kw,
                operating_ceiling_kw=ceiling_kw,
                maximum_headroom_kw=0.0,
                minimum_headroom_kw=0.0,
                solver_runtime_seconds=elapsed_seconds,
                details=f"Infeasible model: constraints cannot be satisfied ({status_str}).",
            )

        # 6. Extract Solution
        optimized_schedule: Dict[str, List[int]] = {}
        slot_load_after: List[float] = list(base_slot_kw)

        for app_type, app in self.config.flexible_appliances.items():
            active_counts = []
            for t in range(self.num_slots):
                act = active_vars[app_type][t]
                count = int(solver.Value(act)) if not isinstance(act, int) else 0
                active_counts.append(count)
                slot_load_after[t] += count * app.power_kw
            optimized_schedule[app_type] = active_counts

        slot_load_after = [round(v, 2) for v in slot_load_after]
        optimized_peak_kw = round(float(max(slot_load_after)), 2)
        optimized_total_energy_kwh = round(float(sum(slot_load_after) * self.dt_hours), 2)

        peak_reduction_kw = round(baseline_peak_kw - optimized_peak_kw, 2)
        peak_reduction_percent = round((peak_reduction_kw / baseline_peak_kw) * 100.0, 2)

        # Aggregate 48 half-hour slots to 24 hourly averages
        slots_per_hour = int(60 / self.time_step_minutes)
        hourly_before = [
            round(float(np.mean(slot_load_before[h * slots_per_hour : (h + 1) * slots_per_hour])), 2)
            for h in range(24)
        ]
        hourly_after = [
            round(float(np.mean(slot_load_after[h * slots_per_hour : (h + 1) * slots_per_hour])), 2)
            for h in range(24)
        ]

        headrooms = [round(transformer_kw - load, 2) for load in slot_load_after]
        max_headroom = round(float(max(headrooms)), 2)
        min_headroom = round(float(min(headrooms)), 2)

        return OptimizationResult(
            status=status_str,
            horizon_hours=24,
            time_step_minutes=self.time_step_minutes,
            baseline_peak_kw=baseline_peak_kw,
            optimized_peak_kw=optimized_peak_kw,
            peak_reduction_kw=peak_reduction_kw,
            peak_reduction_percent=peak_reduction_percent,
            baseline_total_energy_kwh=baseline_total_energy_kwh,
            optimized_total_energy_kwh=optimized_total_energy_kwh,
            appliance_schedule=optimized_schedule,
            hourly_load_before_kw=hourly_before,
            hourly_load_after_kw=hourly_after,
            slot_load_before_kw=slot_load_before,
            slot_load_after_kw=slot_load_after,
            transformer_capacity_kw=transformer_kw,
            operating_ceiling_kw=ceiling_kw,
            maximum_headroom_kw=max_headroom,
            minimum_headroom_kw=min_headroom,
            solver_runtime_seconds=elapsed_seconds,
            details=f"CP-SAT {status_str}: Peak reduced from {baseline_peak_kw} kW to {optimized_peak_kw} kW (-{peak_reduction_percent}%).",
        )
