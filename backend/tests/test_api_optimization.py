"""Integration and Unit Tests for GridMind Milestone 5 Optimization and Simulation APIs."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. OpenAPI Specification & Swagger Endpoint Coverage
# -----------------------------------------------------------------------------

def test_openapi_schema_contains_all_six_endpoints():
    """Verify Swagger / OpenAPI schema includes all required Milestone 1-5 endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    # Check all 6 required routes are exposed
    assert "/api/health" in paths
    assert "get" in paths["/api/health"]

    assert "/api/forecast" in paths
    assert "get" in paths["/api/forecast"]

    assert "/api/model/metrics" in paths
    assert "get" in paths["/api/model/metrics"]

    assert "/api/model/info" in paths
    assert "get" in paths["/api/model/info"]

    assert "/api/optimize" in paths
    assert "post" in paths["/api/optimize"]

    assert "/api/simulate" in paths
    assert "post" in paths["/api/simulate"]


# -----------------------------------------------------------------------------
# 2. Optimization API (POST /api/optimize)
# -----------------------------------------------------------------------------

def test_post_optimize_endpoint_succeeds():
    """Verify POST /api/optimize runs CP-SAT optimization and returns structured response."""
    response = client.post("/api/optimize", json={})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["horizon_hours"] == 24
    assert data["time_step_minutes"] == 30
    assert data["baseline_peak_kw"] > 0.0
    assert data["optimized_peak_kw"] > 0.0
    assert data["peak_reduction_kw"] >= 0.0
    assert data["peak_reduction_percent"] >= 0.0
    assert data["baseline_total_energy_kwh"] > 0.0
    assert data["optimized_total_energy_kwh"] > 0.0

    # Verify curves and schedule presence
    assert len(data["hourly_load_before_kw"]) == 24
    assert len(data["hourly_load_after_kw"]) == 24
    assert len(data["slot_load_before_kw"]) == 48
    assert len(data["slot_load_after_kw"]) == 48
    assert "geyser" in data["appliance_schedule"]
    assert "washing_machine" in data["appliance_schedule"]
    assert "device_charging" in data["appliance_schedule"]

    assert data["transformer_capacity_kw"] == 500.0
    assert data["operating_ceiling_kw"] == 450.0
    assert data["solver_runtime_seconds"] > 0.0


def test_optimize_respects_ceiling_and_transformer_limits():
    """Verify optimized loads strictly respect the 450 kW operating ceiling and 500 kW transformer."""
    response = client.post("/api/optimize", json={"enforce_operating_ceiling": True})
    assert response.status_code == 200
    data = response.json()

    ceiling = data["operating_ceiling_kw"]
    transformer = data["transformer_capacity_kw"]

    for kw in data["slot_load_after_kw"]:
        assert kw <= ceiling + 1e-3
        assert kw <= transformer + 1e-3

    for kw in data["hourly_load_after_kw"]:
        assert kw <= ceiling + 1e-3
        assert kw <= transformer + 1e-3

    assert data["minimum_headroom_kw"] >= transformer - ceiling


def test_optimize_energy_is_physically_conserved():
    """Verify total daily electrical energy is conserved between before and after schedules."""
    response = client.post("/api/optimize", json={})
    assert response.status_code == 200
    data = response.json()

    # Total energy must match within 0.1 kWh precision
    assert pytest.approx(data["baseline_total_energy_kwh"], abs=0.1) == data["optimized_total_energy_kwh"]


def test_optimize_invalid_start_time_returns_400():
    """Verify invalid start_time format returns HTTP 400 Bad Request."""
    response = client.post("/api/optimize", json={"start_time": "not-a-valid-date"})
    assert response.status_code == 400
    assert "Invalid start_time format" in response.json()["detail"]


# -----------------------------------------------------------------------------
# 3. What-If Simulation API (POST /api/simulate)
# -----------------------------------------------------------------------------

def test_post_simulate_endpoint_succeeds_default():
    """Verify POST /api/simulate returns comparative scenario analytics for default parameters."""
    response = client.post("/api/simulate", json={})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["is_feasible"] is True

    # Contrast sections
    assert "baseline_scenario" in data
    assert "simulated_scenario" in data
    assert "comparison" in data

    # Disaggregated curves
    assert len(data["forecasted_demand_mw"]) == 24
    assert len(data["hourly_baseline_load_kw"]) == 24
    assert len(data["hourly_load_before_kw"]) == 24
    assert len(data["hourly_load_after_kw"]) == 24
    assert len(data["slot_load_before_kw"]) == 48
    assert len(data["slot_load_after_kw"]) == 48

    # When no overrides are applied, comparison deltas should be zero
    assert pytest.approx(data["comparison"]["peak_difference_kw"], abs=0.01) == 0.0
    assert pytest.approx(data["comparison"]["energy_difference_kwh"], abs=0.1) == 0.0


def test_simulate_scenario_overrides_actually_change_model():
    """Verify scenario overrides genuinely alter the model and produce dynamic, non-hardcoded results."""
    # Scenario: Increase geysers from 120 to 180 (increasing daily energy by 60 * 2kW * 0.5h = 60 kWh)
    response = client.post("/api/simulate", json={"geyser_quantity": 180, "geyser_max_simultaneous": 70})
    assert response.status_code == 200
    data = response.json()

    assert data["is_feasible"] is True
    # Energy must increase
    assert data["simulated_scenario"]["total_energy_kwh"] > data["baseline_scenario"]["total_energy_kwh"]
    assert pytest.approx(data["comparison"]["energy_difference_kwh"], abs=0.1) == 60.0

    # Total active slots for geysers must be 180 units * 1 slot = 180
    assert sum(data["appliance_schedule"]["geyser"]) == 180

    # Applied params tracked
    assert data["scenario_parameters_applied"]["geyser_quantity"] == 180
    assert data["scenario_parameters_applied"]["geyser_max_simultaneous"] == 70


def test_different_valid_scenarios_produce_different_results():
    """Verify small vs large hostel scenarios yield distinctly different load profiles."""
    # Scenario A: Small Hostel (200 students, 50 geysers, 5 washers, 100 chargers)
    res_a = client.post(
        "/api/simulate",
        json={
            "total_students": 200,
            "geyser_quantity": 50,
            "geyser_max_simultaneous": 25,
            "washing_machine_quantity": 5,
            "device_charging_quantity": 100,
        },
    )
    assert res_a.status_code == 200
    data_a = res_a.json()

    # Scenario B: Large Hostel (800 students, 200 geysers, 30 washers, 400 chargers)
    res_b = client.post(
        "/api/simulate",
        json={
            "total_students": 800,
            "geyser_quantity": 200,
            "geyser_max_simultaneous": 75,
            "washing_machine_quantity": 30,
            "device_charging_quantity": 400,
        },
    )
    assert res_b.status_code == 200
    data_b = res_b.json()

    # Large hostel consumes more energy, has higher unoptimized peak, and achieves larger peak reduction
    assert data_b["simulated_scenario"]["total_energy_kwh"] > data_a["simulated_scenario"]["total_energy_kwh"]
    assert data_b["simulated_scenario"]["unoptimized_peak_kw"] > data_a["simulated_scenario"]["unoptimized_peak_kw"]
    assert data_b["comparison"]["energy_difference_kwh"] > data_a["comparison"]["energy_difference_kwh"]
    assert data_b["simulated_scenario"]["peak_reduction_kw"] > data_a["simulated_scenario"]["peak_reduction_kw"]


# -----------------------------------------------------------------------------
# 4. Scenario Validation & Error Rejections (HTTP 400 / 422)
# -----------------------------------------------------------------------------

def test_simulate_negative_student_count_rejected():
    """Verify negative or zero student count is rejected with HTTP 422."""
    res = client.post("/api/simulate", json={"total_students": -50})
    assert res.status_code == 422


def test_simulate_zero_appliance_quantity_rejected():
    """Verify zero appliance quantity is rejected with HTTP 422."""
    res = client.post("/api/simulate", json={"geyser_quantity": 0})
    assert res.status_code == 422


def test_simulate_operating_ceiling_greater_than_transformer_rejected():
    """Verify operating ceiling exceeding transformer capacity is rejected with HTTP 422."""
    res = client.post(
        "/api/simulate",
        json={"operating_ceiling_kw": 550.0, "transformer_capacity_kw": 500.0},
    )
    assert res.status_code == 422
    assert "cannot exceed transformer capacity" in res.text


def test_simulate_baseline_greater_than_operating_ceiling_rejected():
    """Verify baseline power exceeding operating ceiling is rejected with HTTP 422."""
    res = client.post(
        "/api/simulate",
        json={"baseline_power_kw": 460.0, "operating_ceiling_kw": 450.0},
    )
    assert res.status_code == 422
    assert "must be strictly below operating ceiling" in res.text


def test_simulate_simultaneous_greater_than_quantity_rejected():
    """Verify simultaneous limit exceeding total quantity is rejected with HTTP 400/422."""
    res = client.post(
        "/api/simulate",
        json={"geyser_quantity": 40, "geyser_max_simultaneous": 80},
    )
    assert res.status_code in (400, 422)


def test_simulate_infeasible_scenario_handled_gracefully():
    """Verify mathematically infeasible scenarios return INFEASIBLE status without crashing."""
    # Set ceiling very low (e.g. 50 kW) while baseload already requires 25-125 kW, making it impossible
    res = client.post(
        "/api/simulate",
        json={
            "operating_ceiling_kw": 60.0,
            "transformer_capacity_kw": 60.0,
            "min_baseline_kw": 10.0,
            "max_baseline_kw": 50.0,
            "baseline_power_kw": 5.0,
            "geyser_quantity": 100,  # 100 geysers = 200 kW total load cannot fit under 60 kW!
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INFEASIBLE"
    assert data["is_feasible"] is False
    assert data["comparison"]["is_feasible"] is False
    assert "Infeasible model" in data["details"]
