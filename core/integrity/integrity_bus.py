"""
Integrity Bus - Central Coordination Hub
Part of the PIE (Predictive Integrity Engine)

Coordinates all PIE components and manages prediction flow
"""

import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from .multi_agent_ensemble import MultiAgentEnsemble, AgentPrediction
from .bayesian_calibrator import BayesianCalibrator
from .confidence_scorer import ConfidenceScorer, ConfidenceFactors

logger = logging.getLogger(__name__)


@dataclass
class IntegrityPrediction:
    """Final prediction from PIE system"""
    timestamp: datetime
    prediction_value: float
    confidence: float
    confidence_level: str
    confidence_factors: ConfidenceFactors
    agent_predictions: List[AgentPrediction]
    ensemble_weights: Dict[str, float]
    is_tradeable: bool
    position_size_multiplier: float
    reasoning: str
    metadata: Dict


class IntegrityBus:
    """
    Central coordination hub for the PIE system
    
    Manages the flow:
    1. Multi-Agent Ensemble generates predictions
    2. Bayesian Calibrator adjusts weights
    3. Confidence Scorer assesses confidence
    4. Final prediction is generated
    """
    
    def __init__(self):
        self.ensemble = MultiAgentEnsemble()
        self.calibrator = BayesianCalibrator()
        self.scorer = ConfidenceScorer()
        self.initialized = False
        self.prediction_history = []
        
    async def initialize(self):
        """Initialize all PIE components"""
        logger.info("🚀 Initializing Integrity Bus...")
        
        # Initialize ensemble
        await self.ensemble.initialize()
        
        logger.info("  ✓ Bayesian Calibrator ready")
        logger.info("  ✓ Confidence Scorer ready")
        
        self.initialized = True
        logger.info("✅ Integrity Bus initialized")
    
    async def predict(
        self,
        market_state: Dict,
        historical_accuracy: float = 0.80
    ) -> IntegrityPrediction:
        """
        Generate integrity-checked prediction
        
        Args:
            market_state: Current market state
            historical_accuracy: Recent prediction accuracy
            
        Returns:
            IntegrityPrediction with full confidence assessment
        """
        if not self.initialized:
            await self.initialize()
        
        timestamp = datetime.now()
        
        # Step 1: Get predictions from all agents
        agent_predictions = await self.ensemble.predict(market_state)
        
        # Step 2: Calculate weighted ensemble prediction
        ensemble_value = self._calculate_ensemble_value(agent_predictions)
        
        # Step 3: Score confidence
        confidence, confidence_factors = await self.scorer.score_prediction(
            agent_predictions=agent_predictions,
            market_state=market_state,
            historical_accuracy=historical_accuracy
        )
        
        # Step 4: Determine if tradeable
        is_tradeable = self.scorer.is_tradeable(confidence)
        position_multiplier = self.scorer.get_position_size_multiplier(confidence)
        confidence_level = self.scorer.get_confidence_level(confidence)
        
        # Step 5: Generate reasoning
        reasoning = self._generate_reasoning(
            agent_predictions,
            ensemble_value,
            confidence,
            is_tradeable
        )
        
        # Create final prediction
        prediction = IntegrityPrediction(
            timestamp=timestamp,
            prediction_value=ensemble_value,
            confidence=confidence,
            confidence_level=confidence_level,
            confidence_factors=confidence_factors,
            agent_predictions=agent_predictions,
            ensemble_weights=self.calibrator.weights.copy(),
            is_tradeable=is_tradeable,
            position_size_multiplier=position_multiplier,
            reasoning=reasoning,
            metadata={
                'market_state_summary': self._summarize_market_state(market_state),
                'historical_accuracy': historical_accuracy
            }
        )
        
        # Store in history
        self.prediction_history.append(prediction)
        
        # Log prediction
        self._log_prediction(prediction)
        
        return prediction
    
    def _calculate_ensemble_value(self, predictions: List[AgentPrediction]) -> float:
        """Calculate weighted ensemble prediction"""
        weighted_sum = sum(
            pred.value * self.calibrator.weights[pred.agent_name]
            for pred in predictions
        )
        return weighted_sum
    
    def _generate_reasoning(
        self,
        agent_predictions: List[AgentPrediction],
        ensemble_value: float,
        confidence: float,
        is_tradeable: bool
    ) -> str:
        """Generate human-readable reasoning"""
        # Agent contributions
        agent_summary = " | ".join([
            f"{p.agent_name}: {p.value:.2f} (w={self.calibrator.weights[p.agent_name]:.2f})"
            for p in agent_predictions
        ])
        
        # Confidence assessment
        conf_text = "HIGH" if confidence >= 0.80 else "MODERATE" if confidence >= 0.70 else "LOW"
        
        # Trading decision
        action = "✅ TRADEABLE" if is_tradeable else "❌ NOT TRADEABLE"
        
        reasoning = (
            f"Ensemble: {ensemble_value:.3f} | "
            f"Confidence: {confidence:.2f} ({conf_text}) | "
            f"{action}\n"
            f"Agents: {agent_summary}"
        )
        
        return reasoning
    
    def _summarize_market_state(self, market_state: Dict) -> str:
        """Create market state summary"""
        # TODO: Implement proper market state summary
        return "Normal trading conditions"
    
    def _log_prediction(self, prediction: IntegrityPrediction):
        """Log prediction details"""
        logger.info(
            f"🎯 PREDICTION: {prediction.prediction_value:.3f} | "
            f"Confidence: {prediction.confidence:.2f} ({prediction.confidence_level}) | "
            f"{'✅ TRADEABLE' if prediction.is_tradeable else '❌ HOLD'}"
        )
        
        for pred in prediction.agent_predictions:
            logger.debug(
                f"  • {pred.agent_name}: {pred.value:.3f} "
                f"(conf: {pred.confidence:.2f}, w: {prediction.ensemble_weights[pred.agent_name]:.2f})"
            )
    
    async def update_with_outcome(
        self,
        prediction: IntegrityPrediction,
        actual_outcome: float
    ):
        """
        Update system with actual outcome for calibration
        
        Args:
            prediction: The prediction that was made
            actual_outcome: The actual market outcome
        """
        # Calibrate agent weights
        new_weights = await self.calibrator.calibrate_weights(
            agent_predictions=prediction.agent_predictions,
            actual_outcome=actual_outcome
        )
        
        # Log calibration
        logger.info(f"🔄 Weights updated: {new_weights}")
        
        # Calculate accuracy
        error = abs(prediction.prediction_value - actual_outcome)
        accuracy = 1.0 - min(error, 1.0)
        
        logger.info(f"📊 Prediction accuracy: {accuracy:.2%}")
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        if not self.prediction_history:
            return {
                'total_predictions': 0,
                'message': 'No predictions yet'
            }
        
        recent = self.prediction_history[-100:]  # Last 100 predictions
        
        stats = {
            'total_predictions': len(self.prediction_history),
            'recent_predictions': len(recent),
            'avg_confidence': sum(p.confidence for p in recent) / len(recent),
            'tradeable_rate': sum(p.is_tradeable for p in recent) / len(recent),
            'agent_weights': self.calibrator.weights.copy(),
            'calibration_stats': self.calibrator.get_calibration_stats()
        }
        
        return stats
    
    async def shutdown(self):
        """Shutdown the Integrity Bus"""
        logger.info("🛑 Shutting down Integrity Bus...")
        
        await self.ensemble.shutdown()
        
        logger.info("✅ Integrity Bus shut down")
