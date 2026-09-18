"""End-to-End Baseline Training and Evaluation Pipeline.

Loads data, engineers features, performs chronological train-test split,
fits baseline models, evaluates test metrics (MAE, RMSE, MAPE), and saves artifacts.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

from ml.preprocessing.cleaner import clean_and_merge_energy_weather
from ml.preprocessing.features import generate_feature_matrix
from ml.evaluation.metrics import evaluate_forecast, format_metrics_report
from ml.forecasting.baseline import (
    Naive24hPersistence,
    HistoricalWeeklyMean,
    RidgeRegressionBaseline,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
SAVED_MODELS_DIR = BASE_DIR / "ml" / "saved_models"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def run_pipeline(train_ratio: float = 0.80) -> dict:
    """Execute full baseline model training and evaluation pipeline."""
    print("=" * 60)
    print("GRIDMIND ML PIPELINE: BASELINE FORECASTING")
    print("=" * 60)

    elec_path = DATA_RAW_DIR / "electricity_real_hourly.csv"
    weather_path = DATA_RAW_DIR / "weather_hourly.csv"

    if not elec_path.exists() or not weather_path.exists():
        print("[Pipeline] Raw data missing. Running ingestion first...")
        from data.download_data import run_data_ingestion
        run_data_ingestion()

    print("[Pipeline] Loading raw datasets...")
    elec_df = pd.read_csv(elec_path)
    weather_df = pd.read_csv(weather_path)

    print("[Pipeline] Cleaning, regularizing, and merging datasets...")
    merged_df = clean_and_merge_energy_weather(elec_df, weather_df)
    print(f"[Pipeline] Synchronized dataset contains {len(merged_df)} hourly records.")

    target_col = "grid_load_mw"
    print(f"[Pipeline] Engineering time-series features for target: '{target_col}'...")
    feat_df, feature_cols = generate_feature_matrix(merged_df, target_col=target_col, drop_na=True)
    print(f"[Pipeline] Feature matrix ready: {feat_df.shape[0]} samples, {len(feature_cols)} features.")

    # Chronological split (no future leakage)
    split_idx = int(len(feat_df) * train_ratio)
    train_df = feat_df.iloc[:split_idx].copy()
    test_df = feat_df.iloc[split_idx:].copy()

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    print(f"[Pipeline] Train set: {len(train_df)} rows ({train_df['Datetime'].min()} to {train_df['Datetime'].max()})")
    print(f"[Pipeline] Test set:  {len(test_df)} rows ({test_df['Datetime'].min()} to {test_df['Datetime'].max()})")

    # Initialize Baselines
    models = {
        "naive_24h": Naive24hPersistence(lag_24_col="lag_24h"),
        "historical_mean": HistoricalWeeklyMean(),
        "ridge_regression": RidgeRegressionBaseline(alpha=10.0, feature_cols=feature_cols),
    }

    results = {}
    print("\n" + "-" * 60)
    print(f"{'Model Name':<28} | {'MAE':<10} | {'RMSE':<10} | {'MAPE (%)':<10}")
    print("-" * 60)

    for model_key, model in models.items():
        # Fit
        model.fit(X_train, y_train)
        # Predict on out-of-sample test set
        preds = model.predict(X_test)
        metrics = evaluate_forecast(y_test.values, preds)
        results[model_key] = {
            "name": model.name,
            "metrics": metrics,
        }
        print(f"{model.name:<28} | {metrics['mae']:<10.2f} | {metrics['rmse']:<10.2f} | {metrics['mape_pct']:<10.2f}%")

    print("-" * 60)

    # Save Ridge Model Artifact
    ridge_model_path = SAVED_MODELS_DIR / "baseline_ridge.joblib"
    models["ridge_regression"].save(str(ridge_model_path))
    print(f"\n[Pipeline] Serialized baseline Ridge model saved to: {ridge_model_path}")

    # Export Primary Model Evaluation Metrics for API (/api/model/metrics)
    ridge_metrics = results["ridge_regression"]["metrics"]
    api_metrics = {
        "model": "Ridge Linear Regression",
        "mae_mw": round(ridge_metrics["mae"], 2),
        "rmse_mw": round(ridge_metrics["rmse"], 2),
        "mape_percent": round(ridge_metrics["mape_pct"], 2),
        "test_samples": len(test_df),
    }
    api_metrics_path = SAVED_MODELS_DIR / "model_metrics.json"
    with open(api_metrics_path, "w") as f:
        json.dump(api_metrics, f, indent=2)
    print(f"[Pipeline] API metrics saved to: {api_metrics_path}")

    # Export Comprehensive Model Metadata for API (/api/model/info)
    metadata = {
        "model_name": "GridMind Ridge Baseline",
        "model_type": "Ridge Linear Regression",
        "feature_count": len(feature_cols),
        "feature_names": feature_cols,
        "training_period": {
            "start": str(train_df["Datetime"].min()),
            "end": str(train_df["Datetime"].max()),
        },
        "test_period": {
            "start": str(test_df["Datetime"].min()),
            "end": str(test_df["Datetime"].max()),
        },
        "training_sample_count": len(train_df),
        "test_sample_count": len(test_df),
        "data_source": "PJM Interconnection (PJME Zone) real hourly grid electricity consumption",
        "weather_data_provenance": "Synthetic / deterministic development meteorological series (not physical weather station measurements)",
    }
    metadata_path = SAVED_MODELS_DIR / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Pipeline] Model metadata exported to: {metadata_path}")

    # Export Comprehensive Baseline Comparison Report
    metrics_path = DATA_PROCESSED_DIR / "baseline_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[Pipeline] Baseline evaluation report exported to: {metrics_path}")

    # Save processed test slice for reproducible API demo
    sample_export = test_df[["Datetime", target_col] + feature_cols].iloc[-168:].copy()
    sample_export.to_csv(DATA_PROCESSED_DIR / "sample_forecast_eval.csv", index=False)
    print(f"[Pipeline] Sample 168-hour evaluation slice saved to data/processed/sample_forecast_eval.csv")

    return results


if __name__ == "__main__":
    run_pipeline()
