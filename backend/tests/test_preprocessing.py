"""Unit tests for data preprocessing and cleaning modules."""

import pytest
import pandas as pd
import numpy as np
from ml.preprocessing.cleaner import clean_energy_data, clean_and_merge_energy_weather


def test_clean_energy_data_ordering_and_duplicates():
    """Test that unordered timestamps are sorted and duplicates removed."""
    raw_data = pd.DataFrame({
        "Datetime": [
            "2023-01-01 02:00:00",
            "2023-01-01 00:00:00",
            "2023-01-01 01:00:00",
            "2023-01-01 01:00:00",  # Duplicate
        ],
        "grid_load_mw": [32000.0, 30000.0, 31000.0, 31500.0],
    })

    cleaned = clean_energy_data(raw_data)

    assert len(cleaned) == 3
    assert list(cleaned["Datetime"].dt.hour) == [0, 1, 2]
    assert cleaned["grid_load_mw"].iloc[1] == 31000.0  # First duplicate preserved


def test_clean_energy_data_missing_hour_interpolation():
    """Test that missing hourly gaps are detected and linearly interpolated."""
    raw_data = pd.DataFrame({
        "Datetime": [
            "2023-01-01 10:00:00",
            # 11:00 is missing
            "2023-01-01 12:00:00",
        ],
        "grid_load_mw": [100.0, 200.0],
    })

    cleaned = clean_energy_data(raw_data)

    assert len(cleaned) == 3
    assert cleaned["Datetime"].iloc[1] == pd.Timestamp("2023-01-01 11:00:00")
    # Linear interpolation between 100 and 200
    assert pytest.approx(cleaned["grid_load_mw"].iloc[1], rel=1e-3) == 150.0


def test_clean_energy_data_non_negativity():
    """Test that invalid negative power values are clamped to zero."""
    raw_data = pd.DataFrame({
        "Datetime": ["2023-01-01 00:00:00", "2023-01-01 01:00:00"],
        "grid_load_mw": [-50.0, 120.0],
    })

    cleaned = clean_energy_data(raw_data)
    assert cleaned["grid_load_mw"].iloc[0] == 0.0
    assert cleaned["grid_load_mw"].iloc[1] == 120.0


def test_clean_and_merge_energy_weather():
    """Test inner merge between electricity and weather data."""
    energy_df = pd.DataFrame({
        "Datetime": ["2023-01-01 00:00:00", "2023-01-01 01:00:00", "2023-01-01 02:00:00"],
        "grid_load_mw": [100.0, 110.0, 120.0],
    })
    weather_df = pd.DataFrame({
        "Datetime": ["2023-01-01 01:00:00", "2023-01-01 02:00:00", "2023-01-01 03:00:00"],
        "temperature_c": [15.0, 14.5, 14.0],
        "relative_humidity_pct": [60.0, 65.0, 70.0],
    })

    merged = clean_and_merge_energy_weather(energy_df, weather_df)

    # Only hours 01:00 and 02:00 overlap
    assert len(merged) == 2
    assert "grid_load_mw" in merged.columns
    assert "temperature_c" in merged.columns
