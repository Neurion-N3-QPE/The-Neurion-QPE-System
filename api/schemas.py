"""
Migrated from: qpe_core\api\schemas.py
Migration Date: 2025-10-30 08:12:27.982666
N3 QPE v2.0 - Neurion Quantum Predictive Engine
Target Performance: 99.8% Win Rate | Sharpe 26.74
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from qpe_core.forecast_synthesizer.synthesizer import (
    ForecastType,
    MarketRegime,
    PredictionHorizon,
)
from qpe_core.model_core.hybrid_model import ModelPrediction


# --- User and Auth Schemas ---
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    hashed_password: str


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# --- Data Ingestion Schemas ---
class FeedConfigCreate(BaseModel):
    name: str
    feed_type: str
    url: str
    update_interval: int = 60
    timeout: int = 30
    max_retries: int = 3
    parser: str = "json"
    auth_headers: Optional[Dict[str, str]] = None
    enabled: bool = True


class FeedConfigUpdate(BaseModel):
    name: Optional[str] = None
    feed_type: Optional[str] = None
    url: Optional[str] = None
    update_interval: Optional[int] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    parser: Optional[str] = None
    auth_headers: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None


class FeedStatus(BaseModel):
    name: str
    type: str
    status: str
    last_update: Optional[datetime]
    error_count: int


class DataPointResponse(BaseModel):
    timestamp: datetime
    source: str
    feed_type: str
    signal_name: str
    value: float
    confidence: float
    metadata: Dict[str, Any]
    hash: str


# --- Feature Extraction Schemas ---
class FeatureVectorResponse(BaseModel):
    vector_type: str
    timestamp: datetime
    values: List[float]
    confidence: float
    source_signals: List[str]
    metadata: Dict[str, Any]


# --- Model Prediction Schemas ---
class ModelPredictionResponse(BaseModel):
    model_id: str
    model_version: str
    timestamp: datetime
    horizon: PredictionHorizon
    mean_prediction: float
    confidence_intervals: Dict[str, List[float]]
    probability_distribution: List[float]
    scenarios: List[Dict[str, Any]]
    uncertainty: float
    feature_importance: Dict[str, float]


# --- Forecast Synthesizer Schemas ---
class ForecastRequest(BaseModel):
    asset_name: str = Field(..., description="Asset to forecast")
    forecast_type: ForecastType = ForecastType.ENSEMBLE
    horizon: PredictionHorizon = PredictionHorizon.MEDIUM_TERM
    include_explanation: bool = True


class ForecastResponse(BaseModel):
    forecast_id: str
    asset_name: str
    timestamp: datetime
    point_forecast: float
    confidence_intervals: Dict[str, tuple]
    uncertainty_score: float
    market_regime: str
    forecast_quality: float
    scenarios: List[Dict[str, Any]]
    explanation: Optional[Dict[str, Any]] = None


# --- System Status Schemas ---
class SystemStatus(BaseModel):
    api_status: str
    data_feeds: List[FeedStatus]
    model_status: str
    forecast_status: str
    active_connections: int


# --- Prediction Outcome Update ---
class PredictionOutcomeUpdate(BaseModel):
    prediction_id: str
    actual_outcome: float
    asset_name: str
    timestamp: datetime


class PredictionOutcomeResponse(BaseModel):
    message: str
    prediction_id: str
    status: str
