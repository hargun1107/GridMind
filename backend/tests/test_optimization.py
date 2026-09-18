"""Unit and Integration Tests for GridMind OR-Tools CP-SAT Appliance Scheduling Engine."""

import pytest
import numpy as np
from optimization.scheduler import ApplianceScheduler
from optimization.models import OptimizationStatus, InfeasibleScheduleError
from backend.app.models.hostel import (
    HostelConfig,
    FacilityConfig,
    FlexibleApplianceProfile,
    GridScalingConfig,
)


# -----------------------------------------------------------------------------
# 1. Feasibility and Limit Enforcement Tests
# -----------------------------------------------------------------------------

def test_optimizer_returns_feasible_schedule():
    """Verify solver achieves OPTIMAL or FEASIBLE status on default 500-student hostel."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.optimized_peak_kw > 0.0
    assert result.peak_reduction_kw >= 0.0
    assert result.peak_reduction_percent >= 0.0
    assert len(result.hourly_load_after_kw) == 24
    assert len(result.slot_load_after_kw) == 48


def test_optimized_load_respects_operating_ceiling_and_transformer():
    """Verify optimized load never exceeds operating ceiling (450 kW) or transformer (500 kW)."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    ceiling = scheduler.config.facility.operating_ceiling_kw
    transformer = scheduler.config.facility.transformer_capacity_kw

    for kw in result.slot_load_after_kw:
        assert kw <= ceiling + 1e-3
        assert kw <= transformer + 1e-3

    for kw in result.hourly_load_after_kw:
        assert kw <= ceiling + 1e-3
        assert kw <= transformer + 1e-3

    assert result.minimum_headroom_kw >= transformer - ceiling


# -----------------------------------------------------------------------------
# 2. Fleet Quantity, Concurrency, and Operating Window Tests
# -----------------------------------------------------------------------------

def test_fleet_quantities_and_energy_fully_satisfied():
    """Verify every appliance fleet receives exactly its required operating duration/energy."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    for app_type, app in scheduler.config.flexible_appliances.items():
        schedule = result.appliance_schedule[app_type]
        duration_slots = max(1, int(round(app.runtime_hours / scheduler.dt_hours)))

        # Sum of active slots across the day must equal quantity * duration_slots
        total_active_slots = sum(schedule)
        expected_active_slots = app.quantity * duration_slots
        assert total_active_slots == expected_active_slots


def test_simultaneous_unit_limits_never_exceeded():
    """Verify active units at any half-hour slot never exceed maximum_simultaneous_units."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    for app_type, app in scheduler.config.flexible_appliances.items():
        schedule = result.appliance_schedule[app_type]
        for slot, active_count in enumerate(schedule):
            assert active_count <= app.maximum_simultaneous_units, (
                f"Appliance '{app_type}' at slot {slot} has {active_count} active units, "
                f"exceeding simultaneous limit of {app.maximum_simultaneous_units}."
            )


def test_appliances_never_operate_outside_allowed_windows():
    """Verify zero units are active outside the configured earliest/latest boundaries."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    for app_type, app in scheduler.config.flexible_appliances.items():
        schedule = result.appliance_schedule[app_type]
        earliest_slot = int(app.earliest_start_hour / scheduler.dt_hours)
        latest_finish_slot = int(app.latest_finish_hour / scheduler.dt_hours)

        for slot in range(scheduler.num_slots):
            if slot < earliest_slot or slot >= latest_finish_slot:
                assert schedule[slot] == 0, (
                    f"Appliance '{app_type}' is running at slot {slot} "
                    f"(outside allowed window [{earliest_slot}, {latest_finish_slot}))."
                )


# -----------------------------------------------------------------------------
# 3. Peak Reduction and Metric Verification Tests
# -----------------------------------------------------------------------------

def test_peak_load_and_reduction_calculated_correctly():
    """Verify peak load, reduction in kW, and percentage match array maxima."""
    scheduler = ApplianceScheduler()
    result = scheduler.optimize()

    expected_baseline_peak = max(result.slot_load_before_kw)
    expected_optimized_peak = max(result.slot_load_after_kw)

    assert pytest.approx(result.baseline_peak_kw, abs=0.01) == expected_baseline_peak
    assert pytest.approx(result.optimized_peak_kw, abs=0.01) == expected_optimized_peak
    assert pytest.approx(result.peak_reduction_kw, abs=0.01) == expected_baseline_peak - expected_optimized_peak

    expected_pct = ((expected_baseline_peak - expected_optimized_peak) / expected_baseline_peak) * 100.0
    assert pytest.approx(result.peak_reduction_percent, abs=0.01) == expected_pct
    assert result.peak_reduction_percent > 30.0  # Demonstrates significant load shifting


# -----------------------------------------------------------------------------
# 4. Determinism Tests
# -----------------------------------------------------------------------------

def test_baseline_and_optimized_schedules_deterministic():
    """Verify repeated optimization runs produce 100% identical schedules and loads."""
    scheduler = ApplianceScheduler()
    res1 = scheduler.optimize()
    res2 = scheduler.optimize()

    assert res1.baseline_peak_kw == res2.baseline_peak_kw
    assert res1.optimized_peak_kw == res2.optimized_peak_kw
    assert res1.peak_reduction_kw == res2.peak_reduction_kw
    assert res1.slot_load_after_kw == res2.slot_load_after_kw
    assert res1.appliance_schedule == res2.appliance_schedule


# -----------------------------------------------------------------------------
# 5. Feasibility and Infeasible Model Detection
# -----------------------------------------------------------------------------

def test_intentionally_impossible_configuration_returns_infeasible():
    """Verify an impossible configuration returns INFEASIBLE status cleanly."""
    # Create configuration where operating ceiling is lower than unshiftable base load
    impossible_config = HostelConfig.create_default_500_student_hostel()

    # Add a huge appliance fleet that cannot physically fit into the allowed window:
    # 100 geysers that must run in a 1-slot window but max_simultaneous is only 10
    impossible_config.flexible_appliances["geyser"] = FlexibleApplianceProfile(
        appliance_type="geyser",
        display_name="Overloaded Geysers",
        quantity=100,
        power_kw=2.0,
        runtime_hours=0.5,
        earliest_start_hour=6,
        latest_finish_hour=7,  # Only 2 half-hour slots available!
        maximum_simultaneous_units=10,  # Max 10 * 2 slots = 20 units possible, but 100 required!
        shift_penalty_per_hour=1.0,
    )

    scheduler = ApplianceScheduler(hostel_config=impossible_config)
    result = scheduler.optimize(strict_feasibility=False)

    assert result.status == "INFEASIBLE"
    assert result.peak_reduction_kw == 0.0

    # Also test strict_feasibility=True raises InfeasibleScheduleError
    with pytest.raises(InfeasibleScheduleError):
        scheduler.optimize(strict_feasibility=True)


# -----------------------------------------------------------------------------
# 6. Custom Small Test Configuration
# -----------------------------------------------------------------------------

def test_custom_small_configuration():
    """Verify solver generalizes to custom small test configurations."""
    custom_facility = FacilityConfig(
        total_students=50,
        total_rooms=25,
        transformer_capacity_kw=100.0,
        operating_ceiling_kw=80.0,
        baseline_power_kw=10.0,
    )

    custom_config = HostelConfig(
        facility=custom_facility,
        scaling=GridScalingConfig(min_baseline_kw=10.0, max_baseline_kw=30.0),
        flexible_appliances={
            "mini_geyser": FlexibleApplianceProfile(
                appliance_type="mini_geyser",
                display_name="Mini Geyser",
                quantity=10,
                power_kw=1.5,
                runtime_hours=0.5,
                earliest_start_hour=6,
                latest_finish_hour=10,
                maximum_simultaneous_units=5,
                preferred_start_hour=6,
            )
        },
    )

    scheduler = ApplianceScheduler(hostel_config=custom_config)
    result = scheduler.optimize()

    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.optimized_peak_kw <= 80.0
    assert len(result.appliance_schedule["mini_geyser"]) == 48
    # 10 units * 1 slot = 10 active slots total
    assert sum(result.appliance_schedule["mini_geyser"]) == 10
