"""Baseline Forecasting Models for Electricity Demand.

Implements:
1. Naive24hPersistence: Predicts tomorrow's load as today's observed load at the same hour.
2. HistoricalWeeklyMean: Predicts load as the average historical load for that specific day-of-week and hour.
3. RidgeRegressionBaseline: Regularized linear model utilizing temporal lags, rolling statistics, and weather factors.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib


class Naive24hPersistence:
    """Predicts load at time t using actual load at time t - 24 hours."""

    def __init__(self, lag_24_col: str = "lag_24h"):
        self.lag_24_col = lag_24_col
        self.name = "Naive 24h Persistence"

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        """Persistence requires no parameter fitting."""
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Extract t-24 values as predictions."""
        if self.lag_24_col in X.columns:
            return X[self.lag_24_col].to_numpy(dtype=float)
        raise ValueError(f"Required lag column '{self.lag_24_col}' not found in input features.")


class HistoricalWeeklyMean:
    """Predicts load using historical group-by mean of (dayofweek, hour)."""

    def __init__(self):
        self.name = "Historical Weekly Mean"
        self.slot_means_: Dict[tuple, float] = {}
        self.global_mean_: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Learn mean load for each (dayofweek, hour) slot."""
        df = X[["dayofweek", "hour"]].copy()
        df["target"] = y.values
        grouped = df.groupby(["dayofweek", "hour"])["target"].mean()
        self.slot_means_ = grouped.to_dict()
        self.global_mean_ = float(y.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict slot mean for each row."""
        preds = []
        for _, row in X[["dayofweek", "hour"]].iterrows():
            key = (int(row["dayofweek"]), int(row["hour"]))
            preds.append(self.slot_means_.get(key, self.global_mean_))
        return np.array(preds, dtype=float)


class RidgeRegressionBaseline:
    """Regularized linear model on engineered time-series and weather features."""

    def __init__(self, alpha: float = 1.0, feature_cols: Optional[List[str]] = None):
        self.name = "Ridge Linear Regression"
        self.alpha = alpha
        self.feature_cols = feature_cols
        self.pipeline_ = Pipeline([
            ("scaler", StandardScaler()),
            ("regressor", Ridge(alpha=self.alpha, random_state=42)),
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Fit scaler and ridge regressor."""
        cols = self.feature_cols if self.feature_cols else X.columns
        X_mat = X[cols].values
        self.pipeline_.fit(X_mat, y.values)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate forecasts from feature matrix."""
        cols = self.feature_cols if self.feature_cols else X.columns
        X_mat = X[cols].values
        return self.pipeline_.predict(X_mat)

    def save(self, filepath: str):
        """Save fitted model pipeline to disk."""
        joblib.dump({"pipeline": self.pipeline_, "feature_cols": self.feature_cols}, filepath)

    @classmethod
    def load(cls, filepath: str) -> "RidgeRegressionBaseline":
        """Load fitted model pipeline from disk."""
        data = joblib.load(filepath)
        instance = cls(feature_cols=data["feature_cols"])
        instance.pipeline_ = data["pipeline"]
        return instance
