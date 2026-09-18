"""Forecasting Service Module for GridMind.

Handles:
- Loading and caching the serialized Ridge regression baseline model
- Historical dataset loading, validation, and feature preparation
- Recursive multi-step autoregressive 24-hour load forecasting
- Retrieving held-out test evaluation metrics and model provenance metadata
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from ml.forecasting.baseline import RidgeRegressionBaseline
from ml.preprocessing.cleaner import clean_and_merge_energy_weather

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SAVED_MODELS_DIR = BASE_DIR / "ml" / "saved_models"
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

ELECTRICITY_RAW_PATH = DATA_RAW_DIR / "electricity_real_hourly.csv"
WEATHER_RAW_PATH = DATA_RAW_DIR / "weather_hourly.csv"
MODEL_PATH = SAVED_MODELS_DIR / "baseline_ridge.joblib"
METRICS_PATH = SAVED_MODELS_DIR / "model_metrics.json"
METADATA_PATH = SAVED_MODELS_DIR / "model_metadata.json"


class ModelNotTrainedError(Exception):
    """Raised when model or evaluation artifacts are missing from disk."""
    pass


class InsufficientDataError(Exception):
    """Raised when fewer than 168 historical hours are available for lag generation."""
    pass


class InvalidTimestampError(Exception):
    """Raised when requested start timestamp is malformed or out of valid range."""
    pass


class ForecastService:
    """Production service for demand forecasting and model inspection."""

    _instance: Optional["ForecastService"] = None

    def __init__(self):
        self.model: Optional[RidgeRegressionBaseline] = None
        self._cached_merged_data: Optional[pd.DataFrame] = None

    @classmethod
    def get_instance(cls) -> "ForecastService":
        """Singleton accessor ensuring the model is loaded once."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self, force_reload: bool = False) -> RidgeRegressionBaseline:
        """Load fitted model artifact from disk, caching the instance."""
        if self.model is not None and not force_reload:
            return self.model

        if not MODEL_PATH.exists():
            raise ModelNotTrainedError(
                f"Trained model artifact not found at: {MODEL_PATH}. "
                "Please train the model first by running: python -m ml.forecasting.pipeline"
            )

        self.model = RidgeRegressionBaseline.load(str(MODEL_PATH))
        return self.model

    def is_model_loaded(self) -> bool:
        """Check if model artifact exists and is ready."""
        try:
            self.load_model()
            return True
        except Exception:
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Load held-out test evaluation metrics from disk."""
        if not METRICS_PATH.exists():
            raise ModelNotTrainedError(
                f"Model evaluation metrics not found at: {METRICS_PATH}. "
                "Please train the model first by running: python -m ml.forecasting.pipeline"
            )
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_model_info(self) -> Dict[str, Any]:
        """Load model metadata and data provenance disclosures from disk."""
        if not METADATA_PATH.exists():
            raise ModelNotTrainedError(
                f"Model metadata not found at: {METADATA_PATH}. "
                "Please train the model first by running: python -m ml.forecasting.pipeline"
            )
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_cleaned_history(self) -> pd.DataFrame:
        """Load and cache cleaned and merged historical data."""
        if self._cached_merged_data is not None:
            return self._cached_merged_data

        if not ELECTRICITY_RAW_PATH.exists() or not WEATHER_RAW_PATH.exists():
            raise FileNotFoundError(
                "Historical raw electricity or weather dataset not found in data/raw/. "
                "Please ingest data first by running: python -m data.download_data"
            )

        elec_df = pd.read_csv(ELECTRICITY_RAW_PATH)
        weather_df = pd.read_csv(WEATHER_RAW_PATH)
        merged = clean_and_merge_energy_weather(elec_df, weather_df)
        self._cached_merged_data = merged
        return self._cached_merged_data

    @staticmethod
    def _compute_weather_for_timestamp(ts: pd.Timestamp) -> Dict[str, float]:
        """Compute realistic synthetic weather variables for an arbitrary future timestamp."""
        dayofyear = ts.dayofyear
        hour = ts.hour

        # Deterministic meteorological equations matching data/download_data.py
        annual_temp = 16.0 + 12.0 * np.sin(2 * np.pi * (dayofyear - 105) / 365.25)
        daily_temp = 5.5 * np.sin(2 * np.pi * (hour - 9) / 24)
        temp = round(float(annual_temp + daily_temp), 2)

        humidity_base = 70.0 - 0.9 * daily_temp
        humidity = float(np.clip(np.round(humidity_base, 1), 20.0, 98.0))

        cdd = max(0.0, round(temp - 18.0, 2))
        hdd = max(0.0, round(18.0 - temp, 2))
        thi = round(temp - (0.55 - 0.0055 * humidity) * (temp - 14.5), 2)

        return {
            "temperature_c": temp,
            "relative_humidity_pct": humidity,
            "cooling_degree_days": cdd,
            "heating_degree_days": hdd,
            "thi_discomfort_index": thi,
        }

    def generate_forecast(
        self,
        horizon_hours: int = 24,
        start_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate dynamic 24-hour demand predictions using recursive autoregression.

        Parameters
        ----------
        horizon_hours : int
            Number of hours to forecast ahead (defaults to 24).
        start_time : Optional[str]
            Starting point for the forecast window. If None, forecasts the 24 hours
            immediately following the latest recorded historical observation.

        Returns
        -------
        List[Dict[str, Any]]
            Ordered list of dicts with 'timestamp' and 'predicted_load_mw'.
        """
        model = self.load_model()
        history = self._get_cleaned_history()

        if len(history) < 168:
            raise InsufficientDataError(
                f"Insufficient historical data ({len(history)} records). "
                "A minimum of 168 hours (1 week) is required for autoregressive feature extraction."
            )

        # Determine cutoff timestamp
        if start_time is not None:
            try:
                target_start = pd.to_datetime(start_time)
            except Exception as exc:
                raise InvalidTimestampError(f"Invalid start_time format: '{start_time}'. Use ISO 'YYYY-MM-DD HH:MM:SS'.") from exc

            # Ensure start_time exists or has enough preceding history
            sub_history = history[history["Datetime"] < target_start]
            if len(sub_history) < 168:
                raise InsufficientDataError(
                    f"Requested start_time '{start_time}' has only {len(sub_history)} preceding hourly observations. "
                    "At least 168 hours of historical observations prior to start_time are required."
                )
            base_timestamp = sub_history["Datetime"].max()
            available_history = sub_history.copy()
        else:
            # Default to the end of the historical dataset
            base_timestamp = history["Datetime"].max()
            available_history = history.copy()

        # We need a series of timestamps and load values to compute lags and rolling stats
        # Keep only the last 200 hours to ensure lean, fast memory operations
        recent_history = available_history.tail(200).copy()
        timestamps = list(recent_history["Datetime"])
        loads = list(recent_history["grid_load_mw"])

        # Weather lookup dictionary for fast access
        weather_lookup: Dict[pd.Timestamp, Dict[str, float]] = {}
        for _, row in history.tail(300).iterrows():
            ts = row["Datetime"]
            weather_lookup[ts] = {
                "temperature_c": float(row["temperature_c"]),
                "relative_humidity_pct": float(row["relative_humidity_pct"]),
                "cooling_degree_days": float(row["cooling_degree_days"]),
                "heating_degree_days": float(row["heating_degree_days"]),
                "thi_discomfort_index": float(
                    row.get(
                        "thi_discomfort_index",
                        row["temperature_c"] - (0.55 - 0.0055 * row["relative_humidity_pct"]) * (row["temperature_c"] - 14.5),
                    )
                ),
            }

        forecast_results: List[Dict[str, Any]] = []

        # Autoregressive multi-step recursion
        current_time = base_timestamp
        for _ in range(horizon_hours):
            current_time = current_time + pd.Timedelta(hours=1)
            hour = current_time.hour
            dayofweek = current_time.dayofweek
            month = current_time.month
            is_weekend = int(dayofweek >= 5)

            # Calendar cyclical encodings
            hour_sin = np.sin(2 * np.pi * hour / 24.0)
            hour_cos = np.cos(2 * np.pi * hour / 24.0)
            day_sin = np.sin(2 * np.pi * dayofweek / 7.0)
            day_cos = np.cos(2 * np.pi * dayofweek / 7.0)
            month_sin = np.sin(2 * np.pi * (month - 1) / 12.0)
            month_cos = np.cos(2 * np.pi * (month - 1) / 12.0)

            # Autoregressive lags from recent observations (1h, 2h, 3h, 24h, 48h, 168h)
            lag_1h = loads[-1]
            lag_2h = loads[-2]
            lag_3h = loads[-3]
            lag_24h = loads[-24]
            lag_48h = loads[-48]
            lag_168h = loads[-168]

            # Rolling statistics (using shift(1) equivalent: strictly prior observations)
            arr_6 = np.array(loads[-6:], dtype=float)
            arr_24 = np.array(loads[-24:], dtype=float)

            rolling_mean_6h = float(np.mean(arr_6))
            rolling_std_6h = float(np.std(arr_6, ddof=1)) if len(arr_6) > 1 else 0.0
            rolling_mean_24h = float(np.mean(arr_24))
            rolling_std_24h = float(np.std(arr_24, ddof=1)) if len(arr_24) > 1 else 0.0
            rolling_min_24h = float(np.min(arr_24))
            rolling_max_24h = float(np.max(arr_24))

            # Weather features
            if current_time in weather_lookup:
                w = weather_lookup[current_time]
            else:
                w = self._compute_weather_for_timestamp(current_time)

            feature_dict = {
                "hour": hour,
                "dayofweek": dayofweek,
                "is_weekend": is_weekend,
                "month": month,
                "hour_sin": hour_sin,
                "hour_cos": hour_cos,
                "day_sin": day_sin,
                "day_cos": day_cos,
                "month_sin": month_sin,
                "month_cos": month_cos,
                "lag_1h": lag_1h,
                "lag_2h": lag_2h,
                "lag_3h": lag_3h,
                "lag_24h": lag_24h,
                "lag_48h": lag_48h,
                "lag_168h": lag_168h,
                "rolling_mean_6h": rolling_mean_6h,
                "rolling_std_6h": rolling_std_6h,
                "rolling_mean_24h": rolling_mean_24h,
                "rolling_std_24h": rolling_std_24h,
                "rolling_min_24h": rolling_min_24h,
                "rolling_max_24h": rolling_max_24h,
                "temperature_c": w["temperature_c"],
                "relative_humidity_pct": w["relative_humidity_pct"],
                "cooling_degree_days": w["cooling_degree_days"],
                "heating_degree_days": w["heating_degree_days"],
                "thi_discomfort_index": w["thi_discomfort_index"],
            }

            # Align strictly with model feature columns
            row_df = pd.DataFrame([feature_dict])[model.feature_cols]

            # Model prediction
            predicted_mw = float(model.predict(row_df)[0])
            predicted_mw = max(0.0, round(predicted_mw, 2))

            # Append to dynamic series for subsequent recursive lags
            timestamps.append(current_time)
            loads.append(predicted_mw)

            forecast_results.append({
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "predicted_load_mw": predicted_mw,
            })

        return forecast_results
