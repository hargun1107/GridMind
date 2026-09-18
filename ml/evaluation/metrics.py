"""Evaluation Metrics Module for Forecasting Models.

Computes:
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Mean Absolute Percentage Error (MAPE, with division-by-zero protection)
"""

import numpy as np
from typing import Dict, Union


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Error (MAE)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_t - y_p)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Root Mean Squared Error (RMSE)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_t - y_p) ** 2)))


def mean_absolute_percentage_error(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    epsilon: float = 1e-5,
) -> float:
    """Calculate Mean Absolute Percentage Error (MAPE) in percentage (0-100%)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    # Avoid zero division
    denom = np.maximum(np.abs(y_t), epsilon)
    return float(np.mean(np.abs((y_t - y_p) / denom)) * 100.0)


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard forecasting evaluation metrics dictionary."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "mape_pct": round(mape, 3),
    }


def format_metrics_report(model_name: str, metrics: Dict[str, float]) -> str:
    """Format metrics into a concise human-readable string."""
    return (
        f"[{model_name}] "
        f"MAE: {metrics['mae']:.2f} | "
        f"RMSE: {metrics['rmse']:.2f} | "
        f"MAPE: {metrics['mape_pct']:.2f}%"
    )
