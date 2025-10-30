"""
📊 Confidence Scorer

Calculates prediction confidence based on multiple factors:
- Historical accuracy
- Market volatility
- Agent consensus
- Bayesian uncertainty
"""

import numpy as np
import structlog
from typing import Dict, Optional
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceMetrics:
    """Confidence calculation metrics"""
    accuracy_score: float = 0.0
    volatility_score: float = 0.0
    consensus_score: float = 0.0
    uncertainty_score: float = 0.0
    final_confidence: float = 0.0


class ConfidenceScorer:
    """
    Multi-factor confidence scoring system
    
    Combines multiple signals to produce reliable confidence scores
    """
    
    def __init__(self):
        self.min_confidence = 0.65
        self.max_confidence = 0.99
        self.initialized = False
        
    async def initialize(self):
        """Initialize the scorer"""
        logger.info("📊 Initializing Confidence Scorer...")
        self.initialized = True
        logger.info("✅ Confidence Scorer initialized")
    
    async def score(self, prediction: Dict, market_state) -> float:
        """
        Calculate confidence score for prediction
        
        Args:
            prediction: Calibrated prediction
            market_state: Current market conditions
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        
        metrics = ConfidenceMetrics()
        
        # 1. Accuracy score (from Bayesian state)
        metrics.accuracy_score = self._calculate_accuracy_score(prediction)
        
        # 2. Volatility score (market stability)
        metrics.volatility_score = self._calculate_volatility_score(market_state)
        
        # 3. Consensus score (agent agreement)
        metrics.consensus_score = self._calculate_consensus_score(prediction)
        
        # 4. Uncertainty score (Bayesian uncertainty)
        metrics.uncertainty_score = self._calculate_uncertainty_score(prediction)
        
        # Combine scores (weighted average)
        weights = [0.3, 0.2, 0.3, 0.2]  # Accuracy, Volatility, Consensus, Uncertainty
        scores = [
            metrics.accuracy_score,
            metrics.volatility_score,
            metrics.consensus_score,
            metrics.uncertainty_score
        ]
        
        final_confidence = sum(w * s for w, s in zip(weights, scores))
        final_confidence = np.clip(final_confidence, self.min_confidence, self.max_confidence)
        
        metrics.final_confidence = final_confidence
        
        logger.debug(f"Confidence: {final_confidence:.3f} (acc={metrics.accuracy_score:.2f}, vol={metrics.volatility_score:.2f})")
        
        return final_confidence
    
    def _calculate_accuracy_score(self, prediction: Dict) -> float:
        """Score based on historical accuracy"""
        if 'posterior_mean' in prediction:
            return prediction['posterior_mean']
        return 0.8
    
    def _calculate_volatility_score(self, market_state) -> float:
        """Score based on market volatility (stable = higher confidence)"""
        if hasattr(market_state, 'volatility'):
            # Lower volatility = higher confidence
            return max(0.0, 1.0 - market_state.volatility)
        return 0.7
    
    def _calculate_consensus_score(self, prediction: Dict) -> float:
        """Score based on agent consensus"""
        if 'confidence' in prediction:
            return prediction['confidence']
        return 0.75
    
    def _calculate_uncertainty_score(self, prediction: Dict) -> float:
        """Score based on Bayesian uncertainty"""
        if 'alpha' in prediction and 'beta' in prediction:
            a, b = prediction['alpha'], prediction['beta']
            variance = (a * b) / ((a + b)**2 * (a + b + 1))
            return 1.0 - min(variance * 10, 0.5)
        return 0.7
