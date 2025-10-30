"""
Migrated from: qpe_core\api\main.py
Migration Date: 2025-10-30 08:12:27.968696
N3 QPE v2.0 - Neurion Quantum Predictive Engine
Target Performance: 99.8% Win Rate | Sharpe 26.74
"""

"""
N³ QPE FastAPI Application
=========================

REST/WebSocket API endpoints for live data delivery with authentication,
rate limiting, and real-time forecast streaming.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..data_ingestion.ingestion import DataPoint, ingestion_manager
from ..feature_extraction.extractors import VectorType, feature_manager
from ..forecast_synthesizer.synthesizer import (
    ForecastType,
    PredictionHorizon,
    synthesizer,
)
from ..model_core.hybrid_model import prediction_model
from ..telemetry.logger import QPEMetrics, get_logger, start_metrics_server
from .pie_init import initialize_pie_system

logger = get_logger(__name__)
security = HTTPBearer()


# Pydantic Models for API
class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = settings.APP_VERSION
    uptime_seconds: float


class DataFeedStatus(BaseModel):
    name: str
    type: str
    status: str
    last_update: Optional[datetime]
    error_count: int


class SystemStatus(BaseModel):
    api_status: str
    data_feeds: List[DataFeedStatus]
    model_status: str
    forecast_status: str
    active_connections: int


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


class WebSocketMessage(BaseModel):
    type: str  # "forecast", "data_update", "system_alert"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]


# Global state
app_start_time = datetime.utcnow()
websocket_connections: List[WebSocket] = []


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting N³ QPE API server...")

    # Initialize components
    await synthesizer.initialize()

    # Start metrics server
    if settings.PROMETHEUS_ENABLED:
        start_metrics_server(settings.PROMETHEUS_PORT)

    # Start data ingestion
    await ingestion_manager.start()

    # Register data processing callbacks
    ingestion_manager.register_callback(process_new_data)
    feature_manager.register_callback(process_new_features)

    # Initialize PIE system
    initialize_pie_system(app)

    logger.info("N³ QPE API server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down N³ QPE API server...")
    await ingestion_manager.stop()
    logger.info("N³ QPE API server shut down")


# Create FastAPI app
app = FastAPI(
    title="N³ Quantitative Prediction Engine",
    description="Neural Net Worth Quantitative Prediction Engine API",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token (simplified for demo)"""
    # In production, validate JWT properly
    if credentials.credentials == "demo-token":
        return {"user_id": "demo", "permissions": ["read", "forecast"]}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Rate limiting (simplified)
request_counts: Dict[str, List[datetime]] = {}


async def rate_limit(user: dict = Depends(get_current_user)):
    """Simple rate limiting"""
    user_id = user["user_id"]
    now = datetime.utcnow()

    if user_id not in request_counts:
        request_counts[user_id] = []

    # Remove old requests (older than 1 minute)
    request_counts[user_id] = [
        req_time for req_time in request_counts[user_id] if now - req_time < timedelta(minutes=1)
    ]

    # Check limit
    if len(request_counts[user_id]) >= settings.MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    request_counts[user_id].append(now)
    return user


# API Routes


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic info"""
    return """
    <html>
        <head>
            <title>N³ QPE - Quantitative Prediction Engine</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                       background: #0A1429; color: #F8F5EC; padding: 2rem; }
                .header { color: #D4AF37; font-size: 2.5rem; font-weight: 700; margin-bottom: 1rem; }
                .subtitle { color: #D4AF37; font-size: 1.2rem; margin-bottom: 2rem; }
                .link { color: #D4AF37; text-decoration: none; margin-right: 2rem; }
                .link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="header">🧠 N³ Quantitative Prediction Engine</div>
            <div class="subtitle">Neural Net Worth Ltd - Transforming Data Into Foresight</div>
            <p>
                <a href="/api/docs" class="link">📖 API Documentation</a>
                <a href="/api/health" class="link">❤️ Health Check</a>
                <a href="/api/status" class="link">📊 System Status</a>
                <a href="/console" class="link">🖥️ QPE Console</a>
            </p>
            <p>Status: <span style="color: #90EE90;">Online</span></p>
        </body>
    </html>
    """


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = (datetime.utcnow() - app_start_time).total_seconds()

    return HealthResponse(uptime_seconds=uptime)


@app.get("/api/status", response_model=SystemStatus)
async def system_status():
    """Comprehensive system status"""
    # Get data feed status
    feed_status = ingestion_manager.get_feed_status()
    data_feeds = [
        DataFeedStatus(
            name=name,
            type=info["type"],
            status=info["status"],
            last_update=(
                datetime.fromisoformat(info["last_update"]) if info["last_update"] else None
            ),
            error_count=info["error_count"],
        )
        for name, info in feed_status.items()
    ]

    return SystemStatus(
        api_status="healthy",
        data_feeds=data_feeds,
        model_status="ready" if prediction_model.is_fitted else "not_ready",
        forecast_status="ready",
        active_connections=len(websocket_connections),
    )


@app.post("/api/forecast", response_model=ForecastResponse)
async def generate_forecast(request: ForecastRequest, user: dict = Depends(rate_limit)):
    """Generate a forecast for the specified asset"""
    start_time = time.time()

    try:
        # Get current feature vectors
        feature_vectors = list(feature_manager.get_latest_vectors().values())
        feature_vectors = [fv for fv in feature_vectors if fv is not None]

        if len(feature_vectors) == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No feature data available for forecasting",
            )

        # Generate forecast
        forecast = await synthesizer.synthesize_forecast(
            asset_name=request.asset_name,
            feature_vectors=feature_vectors,
            forecast_type=request.forecast_type,
            horizon=request.horizon,
        )

        # Prepare response
        response = ForecastResponse(
            forecast_id=forecast.forecast_id,
            asset_name=forecast.asset_name,
            timestamp=forecast.timestamp,
            point_forecast=forecast.point_forecast,
            confidence_intervals=forecast.confidence_intervals,
            uncertainty_score=forecast.uncertainty_score,
            market_regime=forecast.market_regime.value,
            forecast_quality=forecast.forecast_quality,
            scenarios=[
                {
                    "name": s.name,
                    "description": s.description,
                    "probability": s.probability,
                    "outcome_value": s.outcome_value,
                    "confidence": s.confidence,
                }
                for s in forecast.scenarios
            ],
            explanation=forecast.explanation.__dict__ if request.include_explanation else None,
        )

        # Record metrics
        duration = time.time() - start_time
        QPEMetrics.record_request("POST", "/api/forecast", duration)

        logger.info(f"Generated forecast for {request.asset_name} in {duration:.3f}s")

        # Broadcast to WebSocket clients
        await broadcast_forecast_update(forecast)

        return response

    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Add new N³ Intelligence Report endpoint
class N3ReportRequest(BaseModel):
    asset_list: List[str] = Field(
        default=["EURUSD", "BTCUSD", "SPY", "GOLD"], description="List of assets for N³ analysis"
    )
    forecast_type: ForecastType = ForecastType.ENSEMBLE
    horizon: PredictionHorizon = PredictionHorizon.MEDIUM_TERM
    format: str = Field(default="text", description="Output format: 'text' or 'json'")


@app.post("/api/n3-intelligence-report")
async def generate_n3_intelligence_report(
    request: N3ReportRequest, user: dict = Depends(rate_limit)
):
    """
    Generate N³ Sovereign-Grade Intelligence Report

    Returns structured market intelligence in the N³ format with:
    - Signal identification and classification
    - Fundamental analysis reasoning
    - N³ intelligence insights
    - Entry/exit zones with risk metrics
    - Probability confidence scores
    """
    start_time = time.time()

    try:
        logger.info(f"Generating N³ intelligence report for assets: {request.asset_list}")

        # Generate N³ formatted report
        n3_report = await synthesizer.generate_n3_report(
            asset_list=request.asset_list,
            forecast_type=request.forecast_type,
            horizon=request.horizon,
        )

        duration = time.time() - start_time
        QPEMetrics.record_request("POST", "/api/n3-intelligence-report", duration)

        logger.info(f"Generated N³ intelligence report in {duration:.3f}s")

        if request.format == "json":
            # Return structured JSON format
            return {
                "report_type": "N³ Sovereign-Grade Intelligence Report",
                "timestamp": datetime.utcnow().isoformat(),
                "assets_analyzed": request.asset_list,
                "report_content": n3_report,
                "generation_time_ms": int(duration * 1000),
            }
        else:
            # Return plain text format for display
            return Response(
                content=n3_report,
                media_type="text/plain; charset=utf-8",
                headers={
                    "Content-Disposition": f"inline; filename=n3-intelligence-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
                },
            )

    except Exception as e:
        logger.error(f"Error generating N³ intelligence report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate N³ intelligence report: {str(e)}",
        )


@app.get("/api/features")
async def get_feature_vectors(user: dict = Depends(get_current_user)):
    """Get current feature vector states"""
    vectors = feature_manager.get_latest_vectors()

    result = {}
    for vector_type, vector in vectors.items():
        if vector:
            result[vector_type.value] = {
                "timestamp": vector.timestamp.isoformat(),
                "values": vector.values.tolist(),
                "confidence": vector.confidence,
                "metadata": vector.metadata,
            }
        else:
            result[vector_type.value] = None

    return result


@app.get("/api/feeds")
async def get_data_feeds(user: dict = Depends(get_current_user)):
    """Get data feed status and recent data"""
    return ingestion_manager.get_feed_status()


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    QPEMetrics.set_active_connections(len(websocket_connections))

    try:
        logger.info(f"New WebSocket connection. Total: {len(websocket_connections)}")

        # Send initial system status
        await websocket.send_json(
            {
                "type": "connection_established",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"message": "Connected to N³ QPE live feed"},
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Echo back for ping/pong
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json(
                    {"type": "keepalive", "timestamp": datetime.utcnow().isoformat(), "data": {}}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        QPEMetrics.set_active_connections(len(websocket_connections))


# Background data processing callbacks


def process_new_data(data_points: List[DataPoint]) -> None:
    """Process new data points from ingestion layer"""
    logger.debug(f"Processing {len(data_points)} new data points")

    # Send data to feature extraction
    feature_results = feature_manager.process_data(data_points)

    # Broadcast data updates if there are WebSocket connections
    if websocket_connections and data_points:
        asyncio.create_task(broadcast_data_update(data_points))


def process_new_features(feature_vector) -> None:
    """Process new feature vectors"""
    logger.debug(f"New feature vector: {feature_vector.vector_type}")

    # Broadcast feature updates
    if websocket_connections:
        asyncio.create_task(broadcast_feature_update(feature_vector))


async def broadcast_data_update(data_points: List[DataPoint]) -> None:
    """Broadcast data updates to WebSocket clients"""
    if not websocket_connections:
        return

    message = {
        "type": "data_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "count": len(data_points),
            "latest_signals": [
                {
                    "source": dp.source,
                    "signal": dp.signal_name,
                    "value": dp.value,
                    "timestamp": dp.timestamp.isoformat(),
                }
                for dp in data_points[-5:]  # Last 5 data points
            ],
        },
    }

    await broadcast_message(message)


async def broadcast_feature_update(feature_vector) -> None:
    """Broadcast feature vector updates to WebSocket clients"""
    message = {
        "type": "feature_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "vector_type": feature_vector.vector_type.value,
            "confidence": feature_vector.confidence,
            "magnitude": float(np.linalg.norm(feature_vector.values)),
        },
    }

    await broadcast_message(message)


async def broadcast_forecast_update(forecast) -> None:
    """Broadcast new forecast to WebSocket clients"""
    message = {
        "type": "forecast_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "forecast_id": forecast.forecast_id,
            "asset_name": forecast.asset_name,
            "point_forecast": forecast.point_forecast,
            "uncertainty": forecast.uncertainty_score,
            "regime": forecast.market_regime.value,
            "quality": forecast.forecast_quality,
        },
    }

    await broadcast_message(message)


async def broadcast_message(message: dict) -> None:
    """Broadcast message to all WebSocket clients"""
    if not websocket_connections:
        return

    # Send to all connected clients
    disconnected = []
    for websocket in websocket_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            disconnected.append(websocket)

    # Remove disconnected clients
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)

    QPEMetrics.set_active_connections(len(websocket_connections))


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest

    return Response(generate_latest(), media_type="text/plain")


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "qpe_core.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
