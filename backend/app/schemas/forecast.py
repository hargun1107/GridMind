"""Pydantic Schemas for GridMind Forecasting API."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall system operational status")
    service: str = Field(..., description="Name of the backend service")
    version: str = Field(..., description="API Version identifier")
    model_loaded: bool = Field(..., description="Whether the ML model is successfully loaded and ready")


class ForecastPoint(BaseModel):
    """Individual hourly demand forecast point."""

    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    predicted_load_mw: float = Field(..., description="Predicted electricity load in Megawatts (MW)")


class ForecastResponse(BaseModel):
    """24-Hour forecasting response schema."""

    horizon_hours: int = Field(24, description="Forecast horizon length in hours")
    unit: str = Field("MW", description="Energy demand unit of measurement")
    model: str = Field(..., description="Forecasting model identifier")
    forecast: List[ForecastPoint] = Field(..., description="List of 24 hourly load predictions")


class ModelMetricsResponse(BaseModel):
    """Model evaluation metrics on held-out test dataset."""

    model: str = Field(..., description="Model display name")
    mae_mw: float = Field(..., description="Mean Absolute Error in Megawatts")
    rmse_mw: float = Field(..., description="Root Mean Squared Error in Megawatts")
    mape_percent: float = Field(..., description="Mean Absolute Percentage Error (0-100%)")
    test_samples: int = Field(..., description="Number of out-of-sample test evaluation hours")


class PeriodInfo(BaseModel):
    """Temporal period boundary."""

    start: str = Field(..., description="Period start timestamp")
    end: str = Field(..., description="Period end timestamp")


class ModelInfoResponse(BaseModel):
    """Forecasting model architecture, features, and provenance metadata."""

    model_name: str = Field(..., description="Model identifier name")
    model_type: str = Field(..., description="Algorithm/model family")
    feature_count: int = Field(..., description="Total number of input features")
    feature_names: List[str] = Field(..., description="Ordered list of feature column names")
    training_period: PeriodInfo = Field(..., description="Temporal coverage of training partition")
    test_period: PeriodInfo = Field(..., description="Temporal coverage of test partition")
    training_sample_count: int = Field(..., description="Number of training observation hours")
    test_sample_count: int = Field(..., description="Number of held-out test evaluation hours")
    data_source: str = Field(..., description="Electricity dataset source and origin")
    weather_data_provenance: str = Field(..., description="Provenance and limitations of the weather dataset")
