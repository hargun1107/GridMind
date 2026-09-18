"""GridMind Optimization Package.

Powered by Google OR-Tools CP-SAT discrete-interval constraint solver.
"""

from optimization.models import (
    OptimizationResult,
    OptimizationStatus,
    InfeasibleScheduleError,
)
from optimization.scheduler import ApplianceScheduler
from optimization.objective import (
    calculate_schedule_cost,
    calculate_inconvenience_penalty,
    PEAK_MINIMIZATION_WEIGHT,
    CONVENIENCE_PENALTY_WEIGHT,
)

__all__ = [
    "ApplianceScheduler",
    "OptimizationResult",
    "OptimizationStatus",
    "InfeasibleScheduleError",
    "calculate_schedule_cost",
    "calculate_inconvenience_penalty",
    "PEAK_MINIMIZATION_WEIGHT",
    "CONVENIENCE_PENALTY_WEIGHT",
]
