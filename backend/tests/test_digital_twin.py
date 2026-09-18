"""Unit Tests for GridMind Hostel Digital Twin Domain Layer."""

import pytest
import numpy as np
from pathlib import Path
from pydantic import ValidationError

from backend.app.models.hostel import (
    FacilityConfig,
    TariffConfig,
    InflexibleLoadProfile,
    FlexibleApplianceProfile,
    GridScalingConfig,
    HostelConfig,
)
from backend.app.services.scaling_service import (
    scale_grid_forecast_to_hostel_baseline,
    ScalingValidationError,
)
from backend.app.services.digital_twin_service import (
    HostelDigitalTwin,
    SimultaneousUnitExceededError,
    InvalidScheduleError,
    DigitalTwinSimulationResult,
)

SAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "hostel_config_default.json"


# -----------------------------------------------------------------------------
# 1. Configuration Loading Tests
# -----------------------------------------------------------------------------

def test_load_default_hostel_config_from_file():
    """Verify loading and parsing the default 500-student hostel configuration."""
    assert SAMPLE_CONFIG_PATH.exists()
    config = HostelConfig.load_from_file(SAMPLE_CONFIG_PATH)

    assert config.facility.total_students == 500
    assert config.facility.total_rooms == 250
    assert config.facility.transformer_capacity_kw == 500.0
    assert config.facility.operating_ceiling_kw == 450.0
    assert config.facility.baseline_power_kw == 25.0

    # Flexible appliances check
    assert "geyser" in config.flexible_appliances
    assert "washing_machine" in config.flexible_appliances
    assert "device_charging" in config.flexible_appliances

    geyser = config.flexible_appliances["geyser"]
    assert geyser.quantity == 120
    assert geyser.power_kw == 2.0
    assert geyser.runtime_hours == 0.5
    assert geyser.maximum_simultaneous_units == 60
    assert geyser.earliest_start_hour == 5
    assert geyser.latest_finish_hour == 22

    # Inflexible loads check
    assert "corridor_lighting" in config.inflexible_loads
    assert config.inflexible_loads["corridor_lighting"].power_kw == 20.0


def test_factory_default_matches_schema():
    """Verify programmatic factory produces valid configuration."""
    config = HostelConfig.create_default_500_student_hostel()
    assert config.facility.total_students == 500
    assert len(config.flexible_appliances) == 3
    assert len(config.inflexible_loads) == 2


# -----------------------------------------------------------------------------
# 2. Validation Rule Tests
# -----------------------------------------------------------------------------

def test_validation_no_negative_or_zero_power():
    """Verify non-positive power ratings are strictly rejected."""
    with pytest.raises(ValidationError):
        FlexibleApplianceProfile(
            appliance_type="bad_app",
            display_name="Bad App",
            quantity=10,
            power_kw=-1.5,  # Invalid negative
            runtime_hours=1.0,
            maximum_simultaneous_units=5,
        )

    with pytest.raises(ValidationError):
        FacilityConfig(
            total_students=500,
            transformer_capacity_kw=0.0,  # Invalid zero
        )


def test_validation_positive_quantities():
    """Verify appliance quantities and student counts must be positive integers."""
    with pytest.raises(ValidationError):
        FacilityConfig(total_students=0)

    with pytest.raises(ValidationError):
        FlexibleApplianceProfile(
            appliance_type="geyser",
            display_name="Geyser",
            quantity=0,  # Invalid
            power_kw=2.0,
            runtime_hours=1.0,
            maximum_simultaneous_units=5,
        )


def test_validation_operating_ceiling_bounds():
    """Verify operating ceiling cannot exceed physical transformer capacity."""
    with pytest.raises(ValidationError):
        FacilityConfig(
            transformer_capacity_kw=500.0,
            operating_ceiling_kw=550.0,  # Exceeds transformer
        )

    with pytest.raises(ValidationError):
        FacilityConfig(
            transformer_capacity_kw=500.0,
            operating_ceiling_kw=450.0,
            baseline_power_kw=460.0,  # Baseload exceeds ceiling
        )


def test_validation_operating_windows_and_runtime():
    """Verify earliest start, latest finish, and runtime feasibility."""
    # Earliest start >= latest finish
    with pytest.raises(ValidationError):
        FlexibleApplianceProfile(
            appliance_type="test",
            display_name="Test",
            quantity=10,
            power_kw=1.0,
            runtime_hours=2.0,
            earliest_start_hour=15,
            latest_finish_hour=10,  # Inverted window
            maximum_simultaneous_units=5,
        )

    # Runtime exceeds window width
    with pytest.raises(ValidationError):
        FlexibleApplianceProfile(
            appliance_type="test",
            display_name="Test",
            quantity=10,
            power_kw=1.0,
            runtime_hours=5.0,  # 5h runtime in a 3h window
            earliest_start_hour=10,
            latest_finish_hour=13,
            maximum_simultaneous_units=5,
        )

    # Simultaneous units exceed quantity
    with pytest.raises(ValidationError):
        FlexibleApplianceProfile(
            appliance_type="test",
            display_name="Test",
            quantity=10,
            power_kw=1.0,
            runtime_hours=1.0,
            earliest_start_hour=5,
            latest_finish_hour=12,
            maximum_simultaneous_units=20,  # 20 > 10
        )


# -----------------------------------------------------------------------------
# 3. Grid Scaling Layer Tests
# -----------------------------------------------------------------------------

def test_grid_scaling_min_max_normalized():
    """Verify min-max normalized scaling maps grid forecast to hostel baseline bounds."""
    # Synthetic diurnal curve with peak and trough
    grid_forecast = [30000.0, 32000.0, 35000.0, 40000.0, 45000.0]
    config = GridScalingConfig(
        method="min_max_normalized",
        min_baseline_kw=30.0,
        max_baseline_kw=120.0,
    )

    scaled = scale_grid_forecast_to_hostel_baseline(grid_forecast, config)
    assert len(scaled) == len(grid_forecast)

    # Min grid (30000) should map to min baseline (30.0)
    assert pytest.approx(scaled[0], abs=0.1) == 30.0
    # Max grid (45000) should map to max baseline (120.0)
    assert pytest.approx(scaled[-1], abs=0.1) == 120.0
    # Monotonicity preserved
    assert all(scaled[i] <= scaled[i + 1] for i in range(len(scaled) - 1))


def test_grid_scaling_flat_forecast_edge_case():
    """Verify scaling handles uniform/flat forecasts without divide-by-zero."""
    flat_forecast = [35000.0] * 24
    config = GridScalingConfig(
        method="min_max_normalized",
        min_baseline_kw=20.0,
        max_baseline_kw=100.0,
    )
    scaled = scale_grid_forecast_to_hostel_baseline(flat_forecast, config)
    assert len(scaled) == 24
    # Should center around median (60.0 kW)
    assert pytest.approx(scaled[0], abs=0.1) == 60.0


def test_grid_scaling_per_capita():
    """Verify per-capita scaling scales proportionally with student population."""
    grid_forecast = [30000.0, 40000.0]
    config = GridScalingConfig(
        method="per_capita",
        per_capita_base_kw=0.20,
    )
    facility = FacilityConfig(total_students=500)

    scaled = scale_grid_forecast_to_hostel_baseline(grid_forecast, config, facility_config=facility)
    assert len(scaled) == 2
    # Mean of [30000, 40000] is 35000; base is 500 * 0.20 = 100 kW
    # At 35000 MW, load is 100 kW
    assert scaled[0] < 100.0 < scaled[1]


def test_grid_scaling_validation_errors():
    """Verify bad inputs trigger ScalingValidationError."""
    config = GridScalingConfig()
    with pytest.raises(ScalingValidationError):
        scale_grid_forecast_to_hostel_baseline([], config)

    with pytest.raises(ScalingValidationError):
        scale_grid_forecast_to_hostel_baseline([-50.0, 100.0], config)


# -----------------------------------------------------------------------------
# 4. Digital Twin Load Calculation Tests
# -----------------------------------------------------------------------------

def test_hourly_baseline_calculation():
    """Verify base load accurately adds constant baseline and active inflexible profiles."""
    twin = HostelDigitalTwin()
    baseline_curve = twin.calculate_hourly_baseline(grid_forecast_mw=None)

    assert len(baseline_curve) == 24

    # Hour 3: Corridor lights (17-00) inactive, study rooms (9-23) inactive
    # Only facility.baseline_power_kw (25 kW)
    assert baseline_curve[3] == 25.0

    # Hour 20 (8 PM): Corridor lights (20 kW) + Study rooms (15 kW) active
    # Expected: 25 + 20 + 15 = 60 kW
    assert baseline_curve[20] == 60.0


def test_custom_appliance_load_calculation():
    """Verify flexible appliance power matches active count times unit rating."""
    twin = HostelDigitalTwin()

    # Schedule 30 geysers active at hour 6 (30 * 2.0 kW = 60 kW)
    custom_schedule = {
        "geyser": [0] * 24,
        "washing_machine": [0] * 24,
        "device_charging": [0] * 24,
    }
    custom_schedule["geyser"][6] = 30

    result = twin.simulate_24h(appliance_schedule=custom_schedule)
    hour_6 = result.hourly_loads[6]

    assert hour_6.appliance_loads_kw["geyser"] == 60.0
    assert hour_6.total_flexible_load_kw == 60.0
    assert hour_6.total_hostel_load_kw == hour_6.baseline_load_kw + 60.0


def test_simultaneous_unit_limits_enforced():
    """Verify exceeding simultaneous unit limit raises SimultaneousUnitExceededError."""
    twin = HostelDigitalTwin()

    # Geyser max simultaneous is 60; attempt to schedule 61
    invalid_schedule = {
        "geyser": [0] * 24,
        "washing_machine": [0] * 24,
        "device_charging": [0] * 24,
    }
    invalid_schedule["geyser"][6] = 61

    with pytest.raises(SimultaneousUnitExceededError):
        twin.simulate_24h(appliance_schedule=invalid_schedule)


def test_schedule_operating_window_enforced():
    """Verify scheduling appliances outside allowed window raises InvalidScheduleError."""
    twin = HostelDigitalTwin()

    # Geyser allowed window is [5, 22); attempt to run at 02:00
    invalid_schedule = {
        "geyser": [0] * 24,
        "washing_machine": [0] * 24,
        "device_charging": [0] * 24,
    }
    invalid_schedule["geyser"][2] = 10

    with pytest.raises(InvalidScheduleError):
        twin.simulate_24h(appliance_schedule=invalid_schedule)


def test_transformer_capacity_headroom_and_breach_detection():
    """Verify headroom calculation and overage flag detection."""
    twin = HostelDigitalTwin()

    # Schedule heavy load: 60 geysers (120 kW) + 10 washers (7 kW) + 150 chargers (15 kW) at hour 20
    # Baseline at hour 20 is 60 kW -> Total = 60 + 120 + 7 + 15 = 202 kW (safe)
    safe_schedule = {
        "geyser": [0] * 24,
        "washing_machine": [0] * 24,
        "device_charging": [0] * 24,
    }
    safe_schedule["geyser"][20] = 60
    safe_schedule["washing_machine"][20] = 10
    safe_schedule["device_charging"][20] = 150

    result = twin.simulate_24h(appliance_schedule=safe_schedule)
    h20 = result.hourly_loads[20]

    assert h20.total_hostel_load_kw == 202.0
    assert h20.capacity_headroom_kw == 500.0 - 202.0  # 298 kW headroom
    assert h20.ceiling_headroom_kw == 450.0 - 202.0   # 248 kW headroom
    assert not h20.is_over_ceiling
    assert not h20.is_over_transformer


def test_simulation_deterministic_output():
    """Verify twin produces 100% identical outputs for repeated runs."""
    twin = HostelDigitalTwin()
    grid_forecast = [35000.0 + i * 200 for i in range(24)]

    res1 = twin.simulate_24h(grid_forecast_mw=grid_forecast)
    res2 = twin.simulate_24h(grid_forecast_mw=grid_forecast)

    assert res1.peak_load_kw == res2.peak_load_kw
    assert res1.total_energy_kwh == res2.total_energy_kwh
    for h in range(24):
        assert res1.hourly_loads[h].total_hostel_load_kw == res2.hourly_loads[h].total_hostel_load_kw
