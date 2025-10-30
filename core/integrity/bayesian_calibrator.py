"""
Bayesian Calibrator - Dynamic Confidence Calibration
Part of the PIE (Predictive Integrity Engine)

Adjusts agent weights and confidence scores using Bayesian inference
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CalibrationMetrics:
    """Metrics for calibration tracking"""
    agent_name: str
    prior_weight: float
    posterior_weight: float
    accuracy: float
    confidence_error: float
    adjustment: float


class BayesianCalibrator:
    """
    Dynamically calibrates agent weights and confidences
    Uses Bayesian inference to adjust based on performance
    """
    
    def __init__(self, initial_weights: Dict[str, float] = None):
        self.weights = initial_weights or {
            'EchoQuant': 0.33,
            'Contramind': 0.33,
            'MythFleck': 0.34
        }
        self.performance_history = {agent: [] for agent in self.weights.keys()}
        self.calibration_alpha = 0.1  # Learning rate
        
    async def calibrate_weights(
        self, 
        agent_predictions: List,
        actual_outcome: float
    ) -> Dict[str, float]:
        """
        Calibrate agent weights based on prediction accuracy
        
        Args:
            agent_predictions: List of AgentPrediction objects
            actual_outcome: The actual market outcome
            
        Returns:
            Updated weights dictionary
        """
        metrics = []
        
        for pred in agent_predictions:
            # Calculate prediction error
            error = abs(pred.value - actual_outcome)
            accuracy = 1.0 - min(error, 1.0)
            
            # Update performance history
            self.performance_history[pred.agent_name].append(accuracy)
            
            # Keep only recent history (last 100 predictions)
            if len(self.performance_history[pred.agent_name]) > 100:
                self.performance_history[pred.agent_name].pop(0)
            
            # Calculate mean accuracy
            mean_accuracy = np.mean(self.performance_history[pred.agent_name])
            
            # Bayesian update
            prior_weight = self.weights[pred.agent_name]
            likelihood = mean_accuracy
            posterior_weight = self._bayesian_update(prior_weight, likelihood)
            
            # Store metrics
            metrics.append(CalibrationMetrics(
                agent_name=pred.agent_name,
                prior_weight=prior_weight,
                posterior_weight=posterior_weight,
                accuracy=accuracy,
                confidence_error=abs(pred.confidence - accuracy),
                adjustment=posterior_weight - prior_weight
            ))
        
        # Normalize weights to sum to 1.0
        self._normalize_weights(metrics)
        
        # Log calibration
        for metric in metrics:
            logger.debug(
                f"📊 {metric.agent_name}: "
                f"{metric.prior_weight:.3f} → {metric.posterior_weight:.3f} "
                f"(acc: {metric.accuracy:.2f})"
            )
        
        return self.weights
    
    def _bayesian_update(self, prior: float, likelihood: float) -> float:
        """
        Perform Bayesian weight update
        
        Uses exponential smoothing for gradual adaptation
        """
        # Exponential moving average
        posterior = (1 - self.calibration_alpha) * prior + self.calibration_alpha * likelihood
        
        # Ensure bounds [0.1, 0.6] to prevent extreme weights
        return np.clip(posterior, 0.1, 0.6)
    
    def _normalize_weights(self, metrics: List[CalibrationMetrics]):
        """Normalize weights to sum to 1.0"""
        total = sum(m.posterior_weight for m in metrics)
        
        for metric in metrics:
            self.weights[metric.agent_name] = metric.posterior_weight / total
    
    async def calibrate_confidence(
        self,
        predicted_confidence: float,
        actual_accuracy: float
    ) -> float:
        """
        Calibrate confidence score based on historical accuracy
        
        Args:
            predicted_confidence: Agent's confidence score
            actual_accuracy: Actual prediction accuracy
            
        Returns:
            Calibrated confidence score
        """
        # Calculate calibration error
        error = abs(predicted_confidence - actual_accuracy)
        
        # Adjust confidence using sigmoid calibration
        calibrated = self._sigmoid_calibration(predicted_confidence, error)
        
        return calibrated
    
    def _sigmoid_calibration(self, confidence: float, error: float) -> float:
        """Apply sigmoid calibration curve"""
        # If error is high, reduce confidence
        adjustment = 1.0 - (error * 0.5)
        calibrated = confidence * adjustment
        
        # Ensure bounds [0.3, 0.95]
        return np.clip(calibrated, 0.3, 0.95)
    
    def get_ensemble_confidence(
        self,
        agent_confidences: List[float],
        agent_names: List[str]
    ) -> float:
        """
        Calculate ensemble confidence using weighted average
        
        Args:
            agent_confidences: List of agent confidence scores
            agent_names: List of agent names
            
        Returns:
            Weighted ensemble confidence
        """
        weighted_conf = sum(
            conf * self.weights[name]
            for conf, name in zip(agent_confidences, agent_names)
        )
        
        return weighted_conf
    
    def get_calibration_stats(self) -> Dict:
        """Get calibration statistics"""
        stats = {}
        
        for agent, history in self.performance_history.items():
            if history:
                stats[agent] = {
                    'weight': self.weights[agent],
                    'mean_accuracy': np.mean(history),
                    'std_accuracy': np.std(history),
                    'predictions': len(history)
                }
        
        return stats
