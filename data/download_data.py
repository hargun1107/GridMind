"""Data Ingestion Module for GridMind.

Prepares:
1. Real external historical electricity demand data (PJM Eastern region hourly load).
2. Aligned synthetic development weather data (temperature, humidity, cooling/heating degree days).
3. Fallback deterministic generator if offline, maintaining reproducible real-world statistical properties.
"""

import os
import sys
import urllib.request
import numpy as np
import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

ELECTRICITY_RAW_PATH = RAW_DATA_DIR / "electricity_real_hourly.csv"
WEATHER_RAW_PATH = RAW_DATA_DIR / "weather_hourly.csv"

# Real public dataset URL
PJM_DATASET_URL = (
    "https://raw.githubusercontent.com/archd3sai/Hourly-Energy-Consumption-Prediction/master/PJME_hourly.csv"
)


def download_pjm_electricity_data(output_path: Path, max_rows: int = 35000) -> pd.DataFrame:
    """Download real PJM hourly electricity consumption dataset or load cached."""
    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"[Ingest] Found existing electricity dataset at: {output_path}")
        df = pd.read_csv(output_path)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        return df

    print(f"[Ingest] Downloading real public electricity dataset from: {PJM_DATASET_URL} ...")
    try:
        req = urllib.request.Request(PJM_DATASET_URL, headers={"User-Agent": "GridMind/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            df = pd.read_csv(resp)

        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values("Datetime").drop_duplicates(subset=["Datetime"])
        df = df.rename(columns={"PJME_MW": "grid_load_mw"})

        # Retain recent slice if large to keep development fast & lean
        if len(df) > max_rows:
            df = df.iloc[-max_rows:].copy()

        df.to_csv(output_path, index=False)
        print(f"[Ingest] Successfully saved {len(df)} hourly records to {output_path}")
        return df

    except Exception as exc:
        print(f"[Ingest] Warning: Remote download failed ({exc}). Generating reproducible deterministic dataset...")
        return generate_reproducible_benchmark_dataset(output_path, num_hours=8760 * 2)


def generate_reproducible_benchmark_dataset(output_path: Path, num_hours: int = 17520) -> pd.DataFrame:
    """Deterministic fallback generator mirroring real utility grid dynamics (seed=42)."""
    np.random.seed(42)
    start_time = pd.Timestamp("2023-01-01 00:00:00")
    timestamps = pd.date_range(start=start_time, periods=num_hours, freq="h")

    # Time components
    hour = timestamps.hour.values
    dayofweek = timestamps.dayofweek.values
    dayofyear = timestamps.dayofyear.values

    # Base seasonal & diurnal patterns
    annual_cycle = 30000 + 4000 * np.sin(2 * np.pi * (dayofyear - 30) / 365.25)
    diurnal_cycle = 4500 * np.sin(2 * np.pi * (hour - 6) / 24)
    evening_peak = 3500 * np.exp(-0.5 * ((hour - 19) / 2.5) ** 2)
    morning_peak = 1500 * np.exp(-0.5 * ((hour - 8) / 2.0) ** 2)
    weekend_reduction = np.where(dayofweek >= 5, -2500, 0)
    noise = np.random.normal(0, 500, size=num_hours)

    grid_load_mw = annual_cycle + diurnal_cycle + evening_peak + morning_peak + weekend_reduction + noise
    df = pd.DataFrame({"Datetime": timestamps, "grid_load_mw": np.round(grid_load_mw, 2)})
    df.to_csv(output_path, index=False)
    print(f"[Ingest] Created benchmark electricity dataset ({len(df)} rows) at {output_path}")
    return df


def generate_aligned_weather_data(electricity_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """Generate synthetic development weather series aligned to timestamps (temperature, humidity, CDD, HDD).
    
    NOTE: This is synthetic/deterministic development data, not physical weather station measurements.
    """
    timestamps = pd.to_datetime(electricity_df["Datetime"])
    np.random.seed(42)

    dayofyear = timestamps.dt.dayofyear.values
    hour = timestamps.dt.hour.values

    # Realistic temperature model (°C) with seasonal and diurnal oscillation
    annual_temp = 16.0 + 12.0 * np.sin(2 * np.pi * (dayofyear - 105) / 365.25)
    daily_temp = 5.5 * np.sin(2 * np.pi * (hour - 9) / 24)
    weather_noise = np.random.normal(0, 1.8, size=len(timestamps))
    temperature = np.round(annual_temp + daily_temp + weather_noise, 2)

    # Relative humidity (%) inversely correlated with temperature
    humidity_base = 70.0 - 0.9 * daily_temp + np.random.normal(0, 4.0, size=len(timestamps))
    humidity = np.clip(np.round(humidity_base, 1), 20.0, 98.0)

    # Degree days
    cooling_degree_days = np.maximum(0.0, temperature - 18.0)
    heating_degree_days = np.maximum(0.0, 18.0 - temperature)

    weather_df = pd.DataFrame(
        {
            "Datetime": timestamps,
            "temperature_c": temperature,
            "relative_humidity_pct": humidity,
            "cooling_degree_days": np.round(cooling_degree_days, 2),
            "heating_degree_days": np.round(heating_degree_days, 2),
        }
    )
    weather_df.to_csv(output_path, index=False)
    print(f"[Ingest] Saved aligned weather data ({len(weather_df)} rows) to {output_path}")
    return weather_df


def run_data_ingestion():
    """Run end-to-end data ingestion pipeline."""
    print("=== GridMind Data Ingestion Pipeline ===")
    elec_df = download_pjm_electricity_data(ELECTRICITY_RAW_PATH)
    weather_df = generate_aligned_weather_data(elec_df, WEATHER_RAW_PATH)
    print("=== Data Ingestion Complete ===")
    return elec_df, weather_df


if __name__ == "__main__":
    run_data_ingestion()
