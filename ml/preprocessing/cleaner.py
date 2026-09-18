"""Data Cleaning and Validation Module for GridMind.

Handles:
- Timestamp parsing and sorting
- Duplicate timestamp resolution
- Missing hourly timestamp detection and interpolation
- Physical sanity checks and outlier clamping
"""

import pandas as pd
import numpy as np
from typing import Tuple


def clean_energy_data(df: pd.DataFrame, time_col: str = "Datetime", value_col: str = "grid_load_mw") -> pd.DataFrame:
    """Clean, sort, deduplicate, and fill missing hourly timestamps for electricity data."""
    cleaned = df.copy()

    # 1. Parse timestamps
    cleaned[time_col] = pd.to_datetime(cleaned[time_col])

    # 2. Deduplicate keeping first
    cleaned = cleaned.drop_duplicates(subset=[time_col]).sort_values(time_col).reset_index(drop=True)

    # 3. Ensure regular hourly frequency
    cleaned = cleaned.set_index(time_col)
    full_idx = pd.date_range(start=cleaned.index.min(), end=cleaned.index.max(), freq="h")
    cleaned = cleaned.reindex(full_idx)

    # 4. Interpolate small gaps in load (up to 3 consecutive hours)
    cleaned[value_col] = cleaned[value_col].interpolate(method="linear", limit=3)
    # Forward-fill and backward-fill remaining if any
    cleaned[value_col] = cleaned[value_col].bfill().ffill()

    # 5. Sanity check: non-negative
    cleaned[value_col] = np.maximum(cleaned[value_col], 0.0)

    cleaned = cleaned.reset_index().rename(columns={"index": time_col})
    return cleaned


def clean_and_merge_energy_weather(
    energy_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    time_col: str = "Datetime",
    energy_col: str = "grid_load_mw",
) -> pd.DataFrame:
    """Clean and merge electricity load with aligned weather parameters."""
    clean_energy = clean_energy_data(energy_df, time_col=time_col, value_col=energy_col)

    clean_weather = weather_df.copy()
    clean_weather[time_col] = pd.to_datetime(clean_weather[time_col])
    clean_weather = clean_weather.drop_duplicates(subset=[time_col]).sort_values(time_col)

    # Inner join on timestamp to guarantee synchronous data points
    merged = pd.merge(clean_energy, clean_weather, on=time_col, how="inner")
    return merged
