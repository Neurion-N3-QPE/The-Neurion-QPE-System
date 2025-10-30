"""
N3 QPE System - Configuration Settings
Neurion Quantum Predictive Engine v2.0

Target Performance:
- Win Rate: 99.8%
- Sharpe Ratio: 26.74
- Max Drawdown: 0.1%
"""

from pydantic import BaseSettings, Field
from typing import Optional, List
from pathlib import Path
import os


class Settings(BaseSettings):
    """Main configuration for N3 QPE System"""
    
    # === SYSTEM METADATA ===
    APP_NAME: str = "Neurion QPE v2.0"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="production", env="QPE_ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="QPE_DEBUG")
    
    # === API CONFIGURATION ===
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_PREFIX: str = "/api/v1"
    
    # === IG MARKETS (LIVE TRADING) ===
    IG_API_KEY: str = Field(default="", env="IG_API_KEY")
    IG_USERNAME: str = Field(default="", env="IG_USERNAME")
    IG_PASSWORD: str = Field(default="", env="IG_PASSWORD")
    IG_ACCOUNT_ID: str = Field(default="", env="IG_ACCOUNT_ID")
    IG_DEMO_MODE: bool = Field(default=False, env="IG_DEMO_MODE")
    IG_BASE_URL: str = "https://api.ig.com/gateway/deal"
    
    # === IC MARKETS (MT5) ===
    IC_LOGIN: int = Field(default=0, env="IC_LOGIN")
    IC_PASSWORD: str = Field(default="", env="IC_PASSWORD")
    IC_SERVER: str = Field(default="", env="IC_SERVER")
    
    # === MODEL CONFIGURATION ===
    MODEL_UPDATE_INTERVAL: int = 60  # minutes
    MONTE_CARLO_ITERATIONS: int = 10000
    CONFIDENCE_THRESHOLD: float = 0.85  # 85% minimum confidence
    TARGET_WIN_RATE: float = 0.998  # 99.8% target
    TARGET_SHARPE_RATIO: float = 26.74
    
    # === PIE SYSTEM (Predictive Integrity Expansion) ===
    PIE_ENABLED: bool = True
    PIE_TARGET_ACCURACY: float = 0.92
    PIE_STRETCH_ACCURACY: float = 0.97
    PIE_ABSOLUTE_LIMIT: float = 0.99
    PIE_RETRAINING_THRESHOLD: float = 0.03  # Retrain if accuracy drops 3%
    
    # === RISK MANAGEMENT ===
    MAX_RISK_PER_TRADE: float = 0.02  # 2%
    MAX_DAILY_LOSS: float = 0.05  # 5%
    MAX_POSITIONS: int = 5
    MAX_CORRELATION: float = 0.7
    
    # === TRADING PROFILES ===
    TRADING_PROFILE: str = Field(default="aggressive", env="TRADING_PROFILE")
    
    # Aggressive Profile (99.8% win rate target)
    AGGRESSIVE_MIN_CONFIDENCE: float = 0.92
    AGGRESSIVE_STAKE_PER_POINT: float = 0.50  # £0.50
    AGGRESSIVE_MAX_POSITIONS: int = 5
    AGGRESSIVE_STOP_LOSS_PCT: float = 0.015  # 1.5%
    AGGRESSIVE_TAKE_PROFIT_PCT: float = 0.10  # 10%
    AGGRESSIVE_DAILY_ROI_TARGET: float = 0.10  # 10%
    
    # Moderate Profile
    MODERATE_MIN_CONFIDENCE: float = 0.75
    MODERATE_STAKE_PER_POINT: float = 0.30
    MODERATE_MAX_POSITIONS: int = 4
    MODERATE_STOP_LOSS_PCT: float = 0.02
    MODERATE_TAKE_PROFIT_PCT: float = 0.05
    MODERATE_DAILY_ROI_TARGET: float = 0.05
    
    # Conservative Profile
    CONSERVATIVE_MIN_CONFIDENCE: float = 0.65
    CONSERVATIVE_STAKE_PER_POINT: float = 0.20
    CONSERVATIVE_MAX_POSITIONS: int = 3
    CONSERVATIVE_STOP_LOSS_PCT: float = 0.02
    CONSERVATIVE_TAKE_PROFIT_PCT: float = 0.03
    CONSERVATIVE_DAILY_ROI_TARGET: float = 0.025
    
    # === DATABASE ===
    DATABASE_URL: str = Field(
        default="sqlite:///data/n3qpe.db",
        env="DATABASE_URL"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # === LOGGING ===
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = "data/logs/n3qpe.log"
    AUDIT_LOG_FILE: str = "data/logs/audit.log"
    
    # === DATA FEEDS ===
    ECONOMIC_CALENDAR_ENABLED: bool = True
    NEWS_SENTIMENT_ENABLED: bool = True
    SOCIAL_SENTIMENT_ENABLED: bool = False
    
    # === MONITORING ===
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    METRICS_UPDATE_INTERVAL: int = 60  # seconds
    
    # === SSE (State Space Exploration) ===
    SSE_ENABLED: bool = True
    SSE_EPISODES: int = 10000
    SSE_CHECKPOINT_DIR: str = "data/checkpoints"
    SSE_MODEL_PATH: str = "data/models/sse_trained_model.pkl"
    
    # === SECURITY ===
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION",
        env="SECRET_KEY"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()


def get_trading_profile_config():
    """Get current trading profile configuration"""
    profile = settings.TRADING_PROFILE.lower()
    
    if profile == "aggressive":
        return {
            "min_confidence": settings.AGGRESSIVE_MIN_CONFIDENCE,
            "stake_per_point": settings.AGGRESSIVE_STAKE_PER_POINT,
            "max_positions": settings.AGGRESSIVE_MAX_POSITIONS,
            "stop_loss_pct": settings.AGGRESSIVE_STOP_LOSS_PCT,
            "take_profit_pct": settings.AGGRESSIVE_TAKE_PROFIT_PCT,
            "daily_roi_target": settings.AGGRESSIVE_DAILY_ROI_TARGET,
        }
    elif profile == "moderate":
        return {
            "min_confidence": settings.MODERATE_MIN_CONFIDENCE,
            "stake_per_point": settings.MODERATE_STAKE_PER_POINT,
            "max_positions": settings.MODERATE_MAX_POSITIONS,
            "stop_loss_pct": settings.MODERATE_STOP_LOSS_PCT,
            "take_profit_pct": settings.MODERATE_TAKE_PROFIT_PCT,
            "daily_roi_target": settings.MODERATE_DAILY_ROI_TARGET,
        }
    else:  # conservative
        return {
            "min_confidence": settings.CONSERVATIVE_MIN_CONFIDENCE,
            "stake_per_point": settings.CONSERVATIVE_STAKE_PER_POINT,
            "max_positions": settings.CONSERVATIVE_MAX_POSITIONS,
            "stop_loss_pct": settings.CONSERVATIVE_STOP_LOSS_PCT,
            "take_profit_pct": settings.CONSERVATIVE_TAKE_PROFIT_PCT,
            "daily_roi_target": settings.CONSERVATIVE_DAILY_ROI_TARGET,
        }


# Display startup banner
def display_banner():
    """Display system startup banner"""
    banner = f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           N³ QUANTUM PREDICTIVE ENGINE v2.0                   ║
    ║           Neurion QPE - Ultimate Trading System               ║
    ║                                                               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  🎯 TARGET PERFORMANCE METRICS                                ║
    ║     • Win Rate: 99.8%                                         ║
    ║     • Sharpe Ratio: 26.74                                     ║
    ║     • Max Drawdown: 0.1%                                      ║
    ║     • Daily ROI: 10%+                                         ║
    ║                                                               ║
    ║  🔧 CONFIGURATION                                             ║
    ║     • Environment: {settings.ENVIRONMENT:<40}║
    ║     • Trading Profile: {settings.TRADING_PROFILE:<35}║
    ║     • PIE System: {'ENABLED' if settings.PIE_ENABLED else 'DISABLED':<39}║
    ║     • SSE Pre-Training: {'ENABLED' if settings.SSE_ENABLED else 'DISABLED':<34}║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)
