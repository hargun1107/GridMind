"""Unit tests for evaluation metrics (MAE, RMSE, MAPE)."""

import pytest
import numpy as np
from ml.evaluation.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    mean_absolute_percentage_error,
    evaluate_forecast,
)


def test_mean_absolute_error():
    """Verify MAE matches manual math."""
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 300.0])
    # Absolute errors: [10, 10, 0] -> mean = 20 / 3 = 6.6666...
    assert pytest.approx(mean_absolute_error(y_true, y_pred), rel=1e-3) == 20.0 / 3.0


def test_root_mean_squared_error():
    """Verify RMSE matches manual math."""
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([13.0, 16.0])
    # Squared errors: [9, 16] -> mean = 12.5 -> sqrt = 3.5355...
    assert pytest.approx(root_mean_squared_error(y_true, y_pred), rel=1e-3) == np.sqrt(12.5)


def test_mean_absolute_percentage_error():
    """Verify MAPE calculates correct percentage."""
    y_true = np.array([100.0, 200.0])
    y_pred = np.array([110.0, 180.0])
    # Percentage errors: [10/100, 20/200] = [0.10, 0.10] -> mean = 10%
    assert pytest.approx(mean_absolute_percentage_error(y_true, y_pred), rel=1e-3) == 10.0


def test_mape_zero_division_protection():
    """Verify MAPE does not crash when true values contain zeros."""
    y_true = np.array([0.0, 100.0])
    y_pred = np.array([5.0, 105.0])
    mape = mean_absolute_percentage_error(y_true, y_pred)
    assert np.isfinite(mape)


def test_evaluate_forecast_dictionary():
    """Verify evaluate_forecast returns expected keys and rounded floats."""
    y_true = np.array([50.0, 100.0, 150.0])
    y_pred = np.array([52.0, 98.0, 149.0])
    metrics = evaluate_forecast(y_true, y_pred)

    assert "mae" in metrics
    assert "rmse" in metrics
    assert "mape_pct" in metrics
    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert metrics["mape_pct"] > 0
