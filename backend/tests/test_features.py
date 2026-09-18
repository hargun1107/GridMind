"""Unit tests for feature engineering and transformation functions."""

import pytest
import pandas as pd
import numpy as np
from ml.preprocessing.features import (
    build_calendar_features,
    build_lag_features,
    build_rolling_features,
    build_weather_interaction_features,
    generate_feature_matrix,
)


@pytest.fixture
def sample_timeseries():
    """Create 200 hours of continuous synthetic time series."""
    times = pd.date_range(start="2023-01-01 00:00:00", periods=200, freq="h")
    # Linear trend with hourly variation
    load = 50.0 + 10.0 * np.sin(2 * np.pi * times.hour / 24)
    temp = 20.0 + 5.0 * np.cos(2 * np.pi * times.hour / 24)
    return pd.DataFrame({
        "Datetime": times,
        "grid_load_mw": load,
        "temperature_c": temp,
        "relative_humidity_pct": np.full(len(times), 60.0),
    })


def test_build_calendar_features_bounds(sample_timeseries):
    """Verify sine and cosine cyclical encodings remain bounded in [-1, 1]."""
    df = build_calendar_features(sample_timeseries)

    for col in ["hour_sin", "hour_cos", "day_sin", "day_cos", "month_sin", "month_cos"]:
        assert df[col].min() >= -1.0 - 1e-6
        assert df[col].max() <= 1.0 + 1e-6

    # Verify weekend flag (Jan 1 2023 was Sunday -> dayofweek=6 -> is_weekend=1)
    assert df["is_weekend"].iloc[0] == 1
    # Jan 2 2023 was Monday -> dayofweek=0 -> is_weekend=0
    assert df["is_weekend"].iloc[24] == 0


def test_build_lag_features_shift_alignment(sample_timeseries):
    """Verify lag features are correctly shifted in time."""
    df = build_lag_features(sample_timeseries, target_col="grid_load_mw", lags=[1, 24])

    assert pd.isna(df["lag_1h"].iloc[0])
    assert pd.isna(df["lag_24h"].iloc[23])

    # lag_1h at index 10 should equal grid_load_mw at index 9
    assert df["lag_1h"].iloc[10] == sample_timeseries["grid_load_mw"].iloc[9]
    # lag_24h at index 25 should equal grid_load_mw at index 1
    assert df["lag_24h"].iloc[25] == sample_timeseries["grid_load_mw"].iloc[1]


def test_build_rolling_features_no_lookahead(sample_timeseries):
    """Verify rolling mean uses shift(1) to avoid current observation leakage."""
    df = build_rolling_features(sample_timeseries, target_col="grid_load_mw", windows=[6])

    # First row shifted value is NaN, rolling mean min_periods=1 returns NaN at index 0
    assert pd.isna(df["rolling_mean_6h"].iloc[0])

    # At index 2, rolling mean should average indices 0 and 1
    expected_mean = sample_timeseries["grid_load_mw"].iloc[0:2].mean()
    assert pytest.approx(df["rolling_mean_6h"].iloc[2], rel=1e-3) == expected_mean


def test_weather_interactions(sample_timeseries):
    """Verify degree day calculations."""
    df = build_weather_interaction_features(sample_timeseries)
    assert "cooling_degree_days" in df.columns
    assert "heating_degree_days" in df.columns
    assert (df["cooling_degree_days"] >= 0.0).all()
    assert (df["heating_degree_days"] >= 0.0).all()


def test_generate_feature_matrix(sample_timeseries):
    """Verify complete feature matrix output and dropna behavior."""
    feat_df, cols = generate_feature_matrix(sample_timeseries, target_col="grid_load_mw", drop_na=True)

    assert not feat_df.empty
    assert feat_df[cols].isna().sum().sum() == 0
    assert "lag_168h" in cols
    # Since max lag is 168, 200 - 168 = 32 rows remain
    assert len(feat_df) == 32
