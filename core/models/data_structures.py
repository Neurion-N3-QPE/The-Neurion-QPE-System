"""
N3 QPE Core Data Structures
Model predictions, forecasts, and trading signals
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import uuid


class MarketRegime(str, Enum):
    """Market regime classifications"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOL = "high_volatility"
    LOW_VOL = "low_volatility"
    CRISIS = "crisis"


class SignalDirection(str, Enum):
    """Trading signal directions"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class ProbabilityDistribution:
    """Probability distribution for predictions"""
    mean: float
    std: float
    quantiles: Dict[float, float] = field(default_factory=dict)  # e.g., {0.05: -10, 0.5: 0, 0.95: 10}
    probabilities: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    
    def get_confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Get confidence interval bounds"""
        alpha = (1 - confidence) / 2
        lower_q = alpha
        upper_q = 1 - alpha
        return (self.quantiles.get(lower_q, self.mean - 2*self.std),
                self.quantiles.get(upper_q, self.mean + 2*self.std))


@dataclass
class Scenario:
    """Market scenario projection"""
    name: str  # Bear, Pessimistic, Base, Optimistic, Bull
    probability: float
    return_forecast: float
    confidence: float
    timeframe: str  # 1h, 24h, 7d, 30d
    drivers: List[str] = field(default_factory=list)


@dataclass
class ModelPrediction:
    """Single model prediction output"""
    model_id: str
    model_version: str
    timestamp: datetime
    asset: str
    horizon: str  # 1h, 4h, 24h, 7d
    
    # Core prediction
    mean_prediction: float
    confidence: float
    distribution: Optional[ProbabilityDistribution] = None
    
    # Uncertainty & risk
    uncertainty_score: float = 0.0
    tail_risk_score: float = 0.0
    
    # Feature importance
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Scenarios
    scenarios: List[Scenario] = field(default_factory=list)


@dataclass
class EnsemblePrediction:
    """Combined prediction from multiple agents"""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    asset: str = ""
    horizon: str = "24h"
    
    # Ensemble result
    final_prediction: float = 0.0
    ensemble_confidence: float = 0.0
    ensemble_uncertainty: float = 0.0
    
    # Individual agent predictions
    agent_predictions: Dict[str, ModelPrediction] = field(default_factory=dict)
    agent_weights: Dict[str, float] = field(default_factory=dict)
    
    # Market context
    market_regime: MarketRegime = MarketRegime.SIDEWAYS
    volatility_regime: str = "normal"
    
    # Scenarios
    scenarios: List[Scenario] = field(default_factory=list)
    
    # Explainability
    causal_drivers: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class TradingSignal:
    """Actionable trading signal"""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Asset & direction
    asset: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    
    # Confidence & sizing
    confidence: float = 0.0
    recommended_size: float = 0.0  # In lots or stake per point
    max_risk_pct: float = 0.02
    
    # Entry & exits
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Risk/reward
    risk_reward_ratio: float = 0.0
    expected_return: float = 0.0
    expected_loss: float = 0.0
    
    # Timeframe
    holding_period: str = "24h"
    expiry: Optional[datetime] = None
    
    # Supporting data
    ensemble_prediction: Optional[EnsemblePrediction] = None
    market_regime: MarketRegime = MarketRegime.SIDEWAYS
    
    # Filters passed
    filters_passed: Dict[str, bool] = field(default_factory=dict)
    
    # Reason
    reasoning: str = ""
    
    def is_valid(self) -> bool:
        """Check if signal is valid and actionable"""
        return (
            self.confidence >= 0.85 and
            self.direction != SignalDirection.NEUTRAL and
            self.entry_price is not None and
            self.stop_loss is not None and
            self.take_profit is not None and
            self.risk_reward_ratio >= 2.0
        )


@dataclass
class Position:
    """Active trading position"""
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str = ""
    
    # Asset & direction
    asset: str = ""
    direction: SignalDirection = SignalDirection.NEUTRAL
    
    # Entry
    entry_time: datetime = field(default_factory=datetime.utcnow)
    entry_price: float = 0.0
    position_size: float = 0.0
    
    # Exits
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # Current state
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Exit
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    
    # Status
    is_open: bool = True
    exit_reason: str = ""
    
    def update_pnl(self, current_price: float):
        """Update P&L based on current price"""
        self.current_price = current_price
        
        if self.direction == SignalDirection.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.position_size
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.position_size
        
        self.unrealized_pnl_pct = self.unrealized_pnl / (self.entry_price * self.position_size)
