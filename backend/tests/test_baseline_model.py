"""Unit tests for baseline forecasting models and model persistence."""

import pytest
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from ml.forecasting.baseline import (
    Naive24hPersistence,
    HistoricalWeeklyMean,
    RidgeRegressionBaseline,
)


@pytest.fixture
def synthetic_dataset():
    """Create small deterministic dataset for model testing."""
    np.random.seed(42)
    n = 200
    times = pd.date_range("2023-01-01", periods=n, freq="h")
    y = 50.0 + 10.0 * np.sin(2 * np.pi * times.hour / 24) + np.random.normal(0, 1, n)

    X = pd.DataFrame({
        "Datetime": times,
        "hour": times.hour,
        "dayofweek": times.dayofweek,
        "lag_24h": np.roll(y, 24),
        "hour_sin": np.sin(2 * np.pi * times.hour / 24),
        "hour_cos": np.cos(2 * np.pi * times.hour / 24),
        "temp": np.random.uniform(15, 30, n),
    })
    return X, pd.Series(y)


def test_naive_persistence_predict(synthetic_dataset):
    """Test naive 24h persistence extracts the exact lag_24h series."""
    X, y = synthetic_dataset
    model = Naive24hPersistence(lag_24_col="lag_24h")
    model.fit(X, y)

    preds = model.predict(X)
    assert len(preds) == len(X)
    assert np.allclose(preds, X["lag_24h"].values)


def test_naive_persistence_missing_col():
    """Test naive persistence raises ValueError if lag column is missing."""
    model = Naive24hPersistence(lag_24_col="non_existent")
    with pytest.raises(ValueError):
        model.predict(pd.DataFrame({"a": [1, 2, 3]}))


def test_historical_weekly_mean(synthetic_dataset):
    """Test historical weekly mean correctly computes slot averages."""
    X, y = synthetic_dataset
    model = HistoricalWeeklyMean()
    model.fit(X, y)

    preds = model.predict(X)
    assert len(preds) == len(X)
    assert np.isfinite(preds).all()

    # Slot average for day 0, hour 10 should match manual calculation
    mask = (X["dayofweek"] == 0) & (X["hour"] == 10)
    expected_slot_mean = y[mask].mean()
    idx = np.where(mask)[0][0]
    assert pytest.approx(preds[idx], rel=1e-3) == expected_slot_mean


def test_ridge_regression_fit_predict_save_load(synthetic_dataset):
    """Test Ridge baseline fit, predict, save, and load cycle."""
    X, y = synthetic_dataset
    feature_cols = ["hour_sin", "hour_cos", "lag_24h", "temp"]

    model = RidgeRegressionBaseline(alpha=1.0, feature_cols=feature_cols)
    model.fit(X, y)

    preds = model.predict(X)
    assert len(preds) == len(X)
    assert np.isfinite(preds).all()

    # Test saving and loading
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_ridge.joblib"
        model.save(str(model_path))
        assert model_path.exists()

        loaded_model = RidgeRegressionBaseline.load(str(model_path))
        loaded_preds = loaded_model.predict(X)

        assert np.allclose(preds, loaded_preds)
