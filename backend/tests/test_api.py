"""Unit and Integration Tests for GridMind FastAPI Endpoints."""

import pytest
from fastapi.testclient import TestClient
import pandas as pd
from unittest.mock import patch
from pathlib import Path

from backend.app.main import app
from backend.app.services.forecast_service import ForecastService, ModelNotTrainedError


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Health Endpoint Tests
# -----------------------------------------------------------------------------

def test_health_endpoint(client):
    """Verify health endpoint returns 200, valid schema, and model_loaded status."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("online", "degraded")
    assert "service" in data
    assert "version" in data
    assert isinstance(data["model_loaded"], bool)
    assert data["model_loaded"] is True


# -----------------------------------------------------------------------------
# 2. Forecast Endpoint Tests
# -----------------------------------------------------------------------------

def test_forecast_endpoint_default_24_points(client):
    """Verify default forecast returns exactly 24 ordered, non-negative hourly predictions."""
    response = client.get("/api/forecast")
    assert response.status_code == 200

    data = response.json()
    assert data["horizon_hours"] == 24
    assert data["unit"] == "MW"
    assert data["model"] == "ridge_baseline"
    assert "forecast" in data

    forecast = data["forecast"]
    assert len(forecast) == 24

    for pt in forecast:
        assert "timestamp" in pt
        assert "predicted_load_mw" in pt
        assert isinstance(pt["predicted_load_mw"], (int, float))
        assert pt["predicted_load_mw"] > 0.0


def test_forecast_timestamps_are_hourly_and_ordered(client):
    """Verify forecast timestamps are strictly continuous hourly steps."""
    response = client.get("/api/forecast")
    assert response.status_code == 200

    forecast = response.json()["forecast"]
    parsed_timestamps = [pd.to_datetime(pt["timestamp"]) for pt in forecast]

    # Verify chronological sequence and exact 1-hour deltas
    for i in range(1, len(parsed_timestamps)):
        delta = parsed_timestamps[i] - parsed_timestamps[i - 1]
        assert delta == pd.Timedelta(hours=1)


def test_forecast_values_are_dynamic_not_hardcoded(client):
    """Verify predictions exhibit realistic variance and are not static/hardcoded."""
    response = client.get("/api/forecast")
    assert response.status_code == 200

    loads = [pt["predicted_load_mw"] for pt in response.json()["forecast"]]

    # Standard deviation must be > 0 (varying across diurnal cycle)
    assert pd.Series(loads).std() > 50.0

    # Test requesting a different historical start time yields distinct predictions
    resp_custom = client.get("/api/forecast?start_time=2018-08-01 00:00:00")
    assert resp_custom.status_code == 200
    custom_loads = [pt["predicted_load_mw"] for pt in resp_custom.json()["forecast"]]

    # The predictions from 2018-08-01 should differ from default cutoff
    assert loads != custom_loads


def test_forecast_custom_valid_start_time(client):
    """Verify custom start_time returns 24 hours starting immediately after cutoff."""
    start_time = "2018-07-25 12:00:00"
    response = client.get(f"/api/forecast?start_time={start_time}")
    assert response.status_code == 200

    data = response.json()
    assert len(data["forecast"]) == 24
    assert data["forecast"][0]["timestamp"] == "2018-07-25 12:00:00"


def test_forecast_invalid_start_time_format(client):
    """Verify malformed start_time returns HTTP 400."""
    response = client.get("/api/forecast?start_time=not-a-valid-date")
    assert response.status_code == 400
    assert "Invalid start_time" in response.json()["detail"]


def test_forecast_insufficient_history_error(client):
    """Verify requesting start_time with < 168 hours of preceding history returns HTTP 422."""
    # The dataset starts at 2014-08-05 13:00:00; 24h later is insufficient for 168h lags
    response = client.get("/api/forecast?start_time=2014-08-06 13:00:00")
    assert response.status_code == 422
    assert "Insufficient historical observations" in response.json()["detail"] or "preceding" in response.json()["detail"]


# -----------------------------------------------------------------------------
# 3. Model Metrics Endpoint Tests
# -----------------------------------------------------------------------------

def test_model_metrics_endpoint(client):
    """Verify /api/model/metrics returns true out-of-sample test metrics."""
    response = client.get("/api/model/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["model"] == "Ridge Linear Regression"
    assert isinstance(data["mae_mw"], (int, float))
    assert isinstance(data["rmse_mw"], (int, float))
    assert isinstance(data["mape_percent"], (int, float))
    assert isinstance(data["test_samples"], int)

    # Validate reasonable values matching Milestone 1 verification
    assert 200.0 < data["mae_mw"] < 600.0
    assert 300.0 < data["rmse_mw"] < 800.0
    assert 0.5 < data["mape_percent"] < 5.0
    assert data["test_samples"] > 5000


# -----------------------------------------------------------------------------
# 4. Model Info & Provenance Endpoint Tests
# -----------------------------------------------------------------------------

def test_model_info_endpoint(client):
    """Verify /api/model/info returns model specs and transparent provenance disclosures."""
    response = client.get("/api/model/info")
    assert response.status_code == 200

    data = response.json()
    assert data["model_name"] == "GridMind Ridge Baseline"
    assert data["model_type"] == "Ridge Linear Regression"
    assert data["feature_count"] == 27
    assert len(data["feature_names"]) == 27
    assert "lag_168h" in data["feature_names"]
    assert "thi_discomfort_index" in data["feature_names"]

    # Check temporal periods
    assert "start" in data["training_period"]
    assert "end" in data["training_period"]
    assert "start" in data["test_period"]
    assert "end" in data["test_period"]

    assert data["training_sample_count"] > 20000
    assert data["test_sample_count"] > 5000

    # Verify provenance disclosures
    assert "PJM" in data["data_source"]
    assert "Synthetic" in data["weather_data_provenance"] or "synthetic" in data["weather_data_provenance"]


# -----------------------------------------------------------------------------
# 5. Missing Artifact Error Handling Tests
# -----------------------------------------------------------------------------

def test_missing_model_artifact_error(client):
    """Verify that a missing model artifact produces an informative HTTP 503 error."""
    with patch.object(ForecastService, "load_model", side_effect=ModelNotTrainedError("Trained model artifact not found")):
        response = client.get("/api/forecast")
        assert response.status_code == 503
        assert "Trained model artifact not found" in response.json()["detail"]


def test_missing_metrics_artifact_error(client):
    """Verify that missing metrics artifact produces an informative HTTP 503 error."""
    with patch.object(ForecastService, "get_metrics", side_effect=ModelNotTrainedError("Model evaluation metrics not found")):
        response = client.get("/api/model/metrics")
        assert response.status_code == 503
        assert "evaluation metrics not found" in response.json()["detail"]
