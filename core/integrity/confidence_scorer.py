"""
Confidence Scorer - Prediction Confidence Assessment
Part of the PIE (Predictive Integrity Engine)

Scores prediction confidence using multiple factors
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Individual factors contributing to confidence"""
    agent_agreement: float
    historical_accuracy: float
    market_clarity: float
    volatility_factor: float
    data_quality: float
    
    def overall_score(self) -> float:
        """Calculate overall confidence score"""
        weights = {
            'agent_agreement': 0.30,
            'historical_accuracy': 0.25,
            'market_clarity': 0.20,
            'volatility_factor': 0.15,
            'data_quality': 0.10
        }
        
        return (
            self.agent_agreement * weights['agent_agreement'] +
            self.historical_accuracy * weights['historical_accuracy'] +
            self.market_clarity * weights['market_clarity'] +
            self.volatility_factor * weights['volatility_factor'] +
            self.data_quality * weights['data_quality']
        )


class ConfidenceScorer:
    """
    Assesses prediction confidence using multiple factors
    
    Factors:
    1. Agent agreement (how much agents agree)
    2. Historical accuracy (recent performance)
    3. Market clarity (how clear signals are)
    4. Volatility factor (market conditions)
    5. Data quality (input data reliability)
    """
    
    def __init__(self):
        self.min_confidence = 0.3
        self.max_confidence = 0.95
        self.confidence_threshold = 0.70  # Minimum for trading
        
    async def score_prediction(
        self,
        agent_predictions: List,
        market_state: Dict,
        historical_accuracy: float = 0.80
    ) -> Tuple[float, ConfidenceFactors]:
        """
        Score prediction confidence
        
        Args:
            agent_predictions: List of AgentPrediction objects
            market_state: Current market state
            historical_accuracy: Recent accuracy rate
            
        Returns:
            (confidence_score, ConfidenceFactors)
        """
        # Calculate individual factors
        agent_agreement = self._calculate_agent_agreement(agent_predictions)
        market_clarity = self._assess_market_clarity(market_state)
        volatility_factor = self._calculate_volatility_factor(market_state)
        data_quality = self._assess_data_quality(market_state)
        
        # Create factors object
        factors = ConfidenceFactors(
            agent_agreement=agent_agreement,
            historical_accuracy=historical_accuracy,
            market_clarity=market_clarity,
            volatility_factor=volatility_factor,
            data_quality=data_quality
        )
        
        # Calculate overall score
        confidence = factors.overall_score()
        
        # Apply bounds
        confidence = np.clip(confidence, self.min_confidence, self.max_confidence)
        
        logger.debug(
            f"📊 Confidence: {confidence:.2f} "
            f"[agree={agent_agreement:.2f}, clarity={market_clarity:.2f}, "
            f"vol={volatility_factor:.2f}]"
        )
        
        return confidence, factors
    
    def _calculate_agent_agreement(self, predictions: List) -> float:
        """
        Calculate how much agents agree
        
        High agreement = high confidence
        """
        if len(predictions) < 2:
            return 0.5
        
        # Extract prediction values
        values = [p.value for p in predictions]
        
        # Calculate variance (lower = more agreement)
        variance = np.var(values)
        
        # Convert to agreement score (0-1)
        # Low variance = high agreement
        agreement = 1.0 - min(variance * 2, 1.0)
        
        # Also consider confidence agreement
        confidences = [p.confidence for p in predictions]
        conf_variance = np.var(confidences)
        conf_agreement = 1.0 - min(conf_variance * 2, 1.0)
        
        # Weighted average
        return agreement * 0.7 + conf_agreement * 0.3
    
    def _assess_market_clarity(self, market_state: Dict) -> float:
        """
        Assess how clear market signals are
        
        Clear signals = high confidence
        """
        # TODO: Implement actual market clarity assessment
        # Factors: trend strength, support/resistance levels, pattern clarity
        
        # Placeholder: return moderate clarity
        return 0.75
    
    def _calculate_volatility_factor(self, market_state: Dict) -> float:
        """
        Calculate volatility factor
        
        Lower volatility = higher confidence
        """
        # TODO: Implement actual volatility calculation
        # Use ATR, historical volatility, VIX, etc.
        
        # Placeholder: return moderate volatility
        volatility = 0.20  # 20% volatility
        
        # Convert to confidence factor (lower vol = higher confidence)
        factor = 1.0 - min(volatility, 0.5)
        
        return factor
    
    def _assess_data_quality(self, market_state: Dict) -> float:
        """
        Assess input data quality
        
        High quality data = high confidence
        """
        # TODO: Implement data quality checks
        # Check for: missing values, outliers, data freshness, source reliability
        
        # Placeholder: return high quality
        return 0.85
    
    def is_tradeable(self, confidence: float) -> bool:
        """Check if confidence meets trading threshold"""
        return confidence >= self.confidence_threshold
    
    def get_position_size_multiplier(self, confidence: float) -> float:
        """
        Calculate position size multiplier based on confidence
        
        Higher confidence = larger position (up to 100% of max)
        """
        if not self.is_tradeable(confidence):
            return 0.0
        
        # Linear scaling from threshold to max
        range_size = self.max_confidence - self.confidence_threshold
        confidence_above_threshold = confidence - self.confidence_threshold
        
        multiplier = confidence_above_threshold / range_size
        
        # Ensure bounds [0.3, 1.0]
        return np.clip(multiplier, 0.3, 1.0)
    
    def get_confidence_level(self, confidence: float) -> str:
        """Get human-readable confidence level"""
        if confidence >= 0.90:
            return "VERY HIGH"
        elif confidence >= 0.80:
            return "HIGH"
        elif confidence >= 0.70:
            return "MODERATE"
        elif confidence >= 0.60:
            return "LOW"
        else:
            return "VERY LOW"
