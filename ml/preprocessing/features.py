"""Feature Engineering Module for Time-Series Electricity Forecasting.

Computes:
- Calendar temporal variables & indicator flags
- Trigonometric cyclical encodings for periodic continuity (hour, day, month)
- Autoregressive lag features (1h, 2h, 24h, 168h)
- Rolling statistical aggregates (means, std, min, max)
- Thermodynamic degree days and heat index interaction terms
"""

import pandas as pd
import numpy as np
from typing import List, Tuple


def build_calendar_features(df: pd.DataFrame, time_col: str = "Datetime") -> pd.DataFrame:
    """Extract calendar and cyclical trigonometric features from timestamps."""
    out = df.copy()
    ts = pd.to_datetime(out[time_col])

    # Calendar primitives
    out["hour"] = ts.dt.hour
    out["dayofweek"] = ts.dt.dayofweek
    out["dayofyear"] = ts.dt.dayofyear
    out["month"] = ts.dt.month
    out["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)

    # Cyclical encodings preserving circular boundary continuity
    # e.g., 23:00 is temporally adjacent to 00:00
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24.0)

    out["day_sin"] = np.sin(2 * np.pi * out["dayofweek"] / 7.0)
    out["day_cos"] = np.cos(2 * np.pi * out["dayofweek"] / 7.0)

    out["month_sin"] = np.sin(2 * np.pi * (out["month"] - 1) / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * (out["month"] - 1) / 12.0)

    return out


def build_lag_features(
    df: pd.DataFrame,
    target_col: str = "grid_load_mw",
    lags: List[int] = [1, 2, 3, 24, 48, 168],
) -> pd.DataFrame:
    """Generate autoregressive lag features for previous hours, days, and weeks."""
    out = df.copy()
    for lag in lags:
        out[f"lag_{lag}h"] = out[target_col].shift(lag)
    return out


def build_rolling_features(
    df: pd.DataFrame,
    target_col: str = "grid_load_mw",
    windows: List[int] = [6, 24],
) -> pd.DataFrame:
    """Generate rolling window statistics based only on historical observations (shift 1)."""
    out = df.copy()
    shifted = out[target_col].shift(1)  # Strictly avoid look-ahead bias

    for w in windows:
        out[f"rolling_mean_{w}h"] = shifted.rolling(window=w, min_periods=1).mean()
        out[f"rolling_std_{w}h"] = shifted.rolling(window=w, min_periods=1).std().fillna(0.0)

    out["rolling_min_24h"] = shifted.rolling(window=24, min_periods=1).min()
    out["rolling_max_24h"] = shifted.rolling(window=24, min_periods=1).max()
    return out


def build_weather_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute cooling/heating degree days and heat index interaction terms."""
    out = df.copy()
    if "temperature_c" in out.columns:
        temp = out["temperature_c"]
        if "cooling_degree_days" not in out.columns:
            out["cooling_degree_days"] = np.maximum(0.0, temp - 18.0)
        if "heating_degree_days" not in out.columns:
            out["heating_degree_days"] = np.maximum(0.0, 18.0 - temp)

        if "relative_humidity_pct" in out.columns:
            rh = out["relative_humidity_pct"]
            # Temperature-Humidity Discomfort / Heat Index approximation
            out["thi_discomfort_index"] = temp - (0.55 - 0.0055 * rh) * (temp - 14.5)
    return out


def generate_feature_matrix(
    df: pd.DataFrame,
    time_col: str = "Datetime",
    target_col: str = "grid_load_mw",
    drop_na: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """Build complete feature matrix and return feature column names."""
    df_feat = build_calendar_features(df, time_col=time_col)
    df_feat = build_lag_features(df_feat, target_col=target_col)
    df_feat = build_rolling_features(df_feat, target_col=target_col)
    df_feat = build_weather_interaction_features(df_feat)

    if drop_na:
        # Max lag is 168h (1 week), drop initial rows that have NaN lags
        df_feat = df_feat.dropna().reset_index(drop=True)

    feature_cols = [
        # Calendar & cyclical
        "hour",
        "dayofweek",
        "is_weekend",
        "month",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
        "month_sin",
        "month_cos",
        # Lags
        "lag_1h",
        "lag_2h",
        "lag_3h",
        "lag_24h",
        "lag_48h",
        "lag_168h",
        # Rolling
        "rolling_mean_6h",
        "rolling_std_6h",
        "rolling_mean_24h",
        "rolling_std_24h",
        "rolling_min_24h",
        "rolling_max_24h",
    ]

    # Include weather if available
    for w_col in ["temperature_c", "relative_humidity_pct", "cooling_degree_days", "heating_degree_days", "thi_discomfort_index"]:
        if w_col in df_feat.columns and w_col not in feature_cols:
            feature_cols.append(w_col)

    return df_feat, feature_cols
