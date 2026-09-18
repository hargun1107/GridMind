"""Optimization Objective Formulations for GridMind.

Formulates:
1. Primary Objective: Min-Max Peak Demand Minimization (kW)
2. Secondary Objective: Schedule Inconvenience / Shift Penalty Minimization
3. Economic Energy Cost Evaluation under Time-of-Use Tariffs
"""

from typing import Dict, List, Any
import numpy as np

# Multi-objective prioritization weights
# Peak minimization strictly dominates so user convenience never compromises peak reduction.
PEAK_MINIMIZATION_WEIGHT = 10000
CONVENIENCE_PENALTY_WEIGHT = 1


def calculate_schedule_cost(
    schedule_kw: List[float],
    tariff_per_kwh: List[float],
    dt_hours: float = 0.5,
) -> float:
    """Calculate total energy cost for a power profile under Time-of-Use rates.

    Parameters
    ----------
    schedule_kw : List[float]
        Power demand at each time interval in kW.
    tariff_per_kwh : List[float]
        Applicable electricity tariff rate for each interval (e.g. INR/kWh).
    dt_hours : float
        Interval duration in hours (0.5 for 30 minutes).

    Returns
    -------
    float
        Total estimated energy expenditure in currency units.
    """
    if len(schedule_kw) != len(tariff_per_kwh):
        raise ValueError("Schedule length must match tariff rate schedule length.")
    return round(float(sum(p * r * dt_hours for p, r in zip(schedule_kw, tariff_per_kwh))), 2)


def calculate_inconvenience_penalty(
    appliance_starts: Dict[str, List[int]],
    appliance_profiles: Dict[str, Any],
    time_step_minutes: int = 30,
) -> float:
    """Calculate aggregate user convenience penalty from schedule shift.

    Penalty is assessed as:
        units_started * hours_deviated * shift_penalty_per_hour
    """
    total_penalty = 0.0
    dt_hours = time_step_minutes / 60.0

    for app_type, starts_list in appliance_starts.items():
        if app_type in appliance_profiles:
            app = appliance_profiles[app_type]
            pref_start_slot = (
                int(app.preferred_start_hour / dt_hours)
                if app.preferred_start_hour is not None
                else int(app.earliest_start_hour / dt_hours)
            )
            penalty_rate = app.shift_penalty_per_hour

            for slot, count in enumerate(starts_list):
                if count > 0:
                    slot_diff = abs(slot - pref_start_slot)
                    hours_diff = slot_diff * dt_hours
                    total_penalty += count * hours_diff * penalty_rate

    return round(float(total_penalty), 2)
