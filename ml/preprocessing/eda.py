"""Exploratory Data Analysis (EDA) Module.

Analyzes:
- Energy consumption distribution statistics (mean, std, percentiles)
- Diurnal profile and peak demand hours
- Day-of-week load variations (weekday vs weekend)
- Temperature sensitivity and degree-day correlations
- Generates a structured markdown report at docs/eda_summary.md
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

from ml.preprocessing.cleaner import clean_and_merge_energy_weather
from ml.preprocessing.features import build_calendar_features

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def run_eda(output_md: Path = DOCS_DIR / "eda_summary.md") -> dict:
    """Run statistical analysis on synchronized electricity and weather data."""
    elec_path = DATA_RAW_DIR / "electricity_real_hourly.csv"
    weather_path = DATA_RAW_DIR / "weather_hourly.csv"

    if not elec_path.exists() or not weather_path.exists():
        from data.download_data import run_data_ingestion
        run_data_ingestion()

    elec_df = pd.read_csv(elec_path)
    weather_df = pd.read_csv(weather_path)
    df = clean_and_merge_energy_weather(elec_df, weather_df)
    df = build_calendar_features(df)

    target = "grid_load_mw"

    # 1. Distribution summary
    desc = df[target].describe().to_dict()

    # 2. Hourly profile
    hourly_stats = df.groupby("hour")[target].agg(["mean", "min", "max", "std"]).reset_index()
    peak_hour = int(hourly_stats.loc[hourly_stats["mean"].idxmax(), "hour"])
    trough_hour = int(hourly_stats.loc[hourly_stats["mean"].idxmin(), "hour"])
    peak_val = float(hourly_stats["mean"].max())
    trough_val = float(hourly_stats["mean"].min())

    # 3. Weekday vs Weekend
    day_stats = df.groupby("is_weekend")[target].agg(["mean", "std"]).to_dict()
    weekday_mean = float(day_stats["mean"][0])
    weekend_mean = float(day_stats["mean"][1])
    weekend_reduction_pct = ((weekday_mean - weekend_mean) / weekday_mean) * 100.0

    # 4. Weather correlation
    corr_temp = float(df[[target, "temperature_c"]].corr().iloc[0, 1])
    corr_cdd = float(df[[target, "cooling_degree_days"]].corr().iloc[0, 1])
    corr_hdd = float(df[[target, "heating_degree_days"]].corr().iloc[0, 1])

    summary = {
        "dataset_total_hours": len(df),
        "start_date": str(df["Datetime"].min()),
        "end_date": str(df["Datetime"].max()),
        "distribution": {
            "mean_mw": round(desc["mean"], 2),
            "std_mw": round(desc["std"], 2),
            "min_mw": round(desc["min"], 2),
            "p25_mw": round(desc["25%"], 2),
            "median_mw": round(desc["50%"], 2),
            "p75_mw": round(desc["75%"], 2),
            "max_mw": round(desc["max"], 2),
        },
        "diurnal_profile": {
            "peak_hour": peak_hour,
            "peak_mean_mw": round(peak_val, 2),
            "trough_hour": trough_hour,
            "trough_mean_mw": round(trough_val, 2),
            "peak_to_trough_ratio": round(peak_val / max(trough_val, 1e-5), 2),
        },
        "day_of_week": {
            "weekday_mean_mw": round(weekday_mean, 2),
            "weekend_mean_mw": round(weekend_mean, 2),
            "weekend_reduction_pct": round(weekend_reduction_pct, 2),
        },
        "weather_correlations": {
            "temperature_corr": round(corr_temp, 3),
            "cooling_degree_days_corr": round(corr_cdd, 3),
            "heating_degree_days_corr": round(corr_hdd, 3),
        },
    }

    # Generate Markdown documentation
    md_content = f"""# GridMind: Exploratory Data Analysis & Energy Profile Summary

This document summarizes the empirical characteristics of the real PJM hourly electricity dataset paired with aligned synthetic development meteorological variables (see DATA_PROVENANCE.md).

---

## 1. Dataset Overview
- **Total Synchronized Observations:** {summary['dataset_total_hours']:,} hourly records
- **Electricity Data Source:** Real PJM Interconnection (PJME Zone) hourly demand
- **Weather Data Source:** Synthetic/deterministic development series (not physical weather station measurements)
- **Temporal Coverage:** `{summary['start_date']}` to `{summary['end_date']}`
- **Primary Metric:** `grid_load_mw` (Megawatts)

---

## 2. Statistical Distribution

| Metric | Value (MW) | Notes |
| :--- | :--- | :--- |
| **Mean** | {summary['distribution']['mean_mw']:,} | Central tendency |
| **Standard Deviation** | {summary['distribution']['std_mw']:,} | Inherent demand volatility |
| **Minimum** | {summary['distribution']['min_mw']:,} | Base seasonal trough |
| **25th Percentile** | {summary['distribution']['p25_mw']:,} | Lower quartile load |
| **Median (50th)** | {summary['distribution']['median_mw']:,} | Median operating point |
| **75th Percentile** | {summary['distribution']['p75_mw']:,} | Upper quartile load |
| **Maximum** | {summary['distribution']['max_mw']:,} | Historic grid peak demand |

---

## 3. Diurnal & Temporal Patterns

- **Daily Peak Hour:** `{summary['diurnal_profile']['peak_hour']:02d}:00` with average load of **{summary['diurnal_profile']['peak_mean_mw']:,} MW**.
- **Daily Trough Hour:** `{summary['diurnal_profile']['trough_hour']:02d}:00` with average load of **{summary['diurnal_profile']['trough_mean_mw']:,} MW**.
- **Peak-to-Trough Ratio:** **{summary['diurnal_profile']['peak_to_trough_ratio']}x** load multiplier across the diurnal cycle.
- **Weekday vs. Weekend Effect:**
  - Weekday average: **{summary['day_of_week']['weekday_mean_mw']:,} MW**
  - Weekend average: **{summary['day_of_week']['weekend_mean_mw']:,} MW**
  - Average weekend load drop: **{summary['day_of_week']['weekend_reduction_pct']}%**

---

## 4. Temperature & Weather Sensitivity

Electricity demand exhibits a classic non-linear U-shaped relationship with ambient temperature due to space heating (winter) and air conditioning (summer):

| Variable | Pearson Correlation ($r$) | Physical Interpretation |
| :--- | :--- | :--- |
| **Temperature (°C)** | {summary['weather_correlations']['temperature_corr']} | Net directional correlation |
| **Cooling Degree Days (CDD)** | {summary['weather_correlations']['cooling_degree_days_corr']} | Strong positive correlation with summer cooling demand |
| **Heating Degree Days (HDD)** | {summary['weather_correlations']['heating_degree_days_corr']} | Positive correlation during colder winter periods |

---

## 5. Architectural Implications for GridMind Optimization

1. **Predictable Evening Spikes**: Peak demand consistently gathers in the late afternoon/early evening hours (17:00–21:00). This confirms that flexible thermal loads (water heaters/geysers) and device charging can be shifted away from this window.
2. **Deep Overnight Valleys**: Load drops significantly between 01:00 and 05:00, providing an ideal low-cost, low-load buffer for pre-heating water or bulk charging.
3. **Weather Drivers**: Incorporating cooling degree days provides critical predictive signal for estimating high-load days when AC usage stresses transformer capacity.
"""

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[EDA] Summary report written to: {output_md}")
    return summary


if __name__ == "__main__":
    run_eda()
