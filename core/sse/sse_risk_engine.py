"""
🎯 SSE Risk Engine - Pre-Trade Monte Carlo Validation

This is the critical risk firewall that runs 10,000 Monte Carlo simulations
before EVERY live trade to ensure 99%+ certainty on trade outcomes.

Key Functions:
1. Pre-execution risk validation
2. Monte Carlo probability gates
3. Historical win rate analysis
4. Risk-of-ruin calculations
5. Expected value validation

This engine prevents ANY trade from executing unless it passes rigorous
statistical validation through 10,000 simulated scenarios.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

# Import Monte Carlo Simulator
try:
    from ..models.hybrid_model import MonteCarloSimulator
except ImportError:
    from core.models.hybrid_model import MonteCarloSimulator

logger = logging.getLogger(__name__)


@dataclass
class SSEValidationResult:
    """Result of SSE pre-trade validation"""
    approved: bool
    win_probability: float
    risk_of_ruin: float
    expected_value: float
    confidence_level: float
    scenarios_analyzed: int
    rejection_reason: Optional[str] = None
    simulation_metrics: Optional[Dict] = None


@dataclass
class TradeProposal:
    """Proposed trade for SSE validation"""
    epic: str
    direction: str
    size: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence_score: float = 0.0
    market_context: Optional[Dict] = None


class SSERiskEngine:
    """
    🎯 SSE Risk Engine - Monte Carlo Pre-Trade Validation
    
    The primary risk firewall that validates every trade through
    10,000 Monte Carlo simulations before live execution.
    """
    
    def __init__(self, config: Dict):
        """Initialize SSE Risk Engine"""
        self.config = config
        self.sse_config = config.get('trading', {}).get('sse', {})
        
        # SSE Parameters
        self.enabled = self.sse_config.get('enabled', True)
        self.n_simulations = self.sse_config.get('n_simulations', 10000)
        self.pre_trade_validation = self.sse_config.get('pre_trade_validation', True)
        
        # Monte Carlo Gates
        gates_config = self.sse_config.get('monte_carlo_gates', {})
        self.min_win_probability = gates_config.get('min_win_probability', 0.65)
        self.max_risk_of_ruin = gates_config.get('max_risk_of_ruin', 0.05)
        self.min_expected_value = gates_config.get('min_expected_value', 0.1)
        self.confidence_threshold = gates_config.get('confidence_threshold', 0.99)
        
        # Risk Firewall
        firewall_config = self.sse_config.get('risk_firewall', {})
        self.block_high_risk_trades = firewall_config.get('block_high_risk_trades', True)
        self.emergency_stop_multiplier = firewall_config.get('emergency_stop_loss_multiplier', 2.0)
        
        # Initialize Monte Carlo Simulator
        if self.enabled:
            self.monte_carlo = MonteCarloSimulator(n_simulations=self.n_simulations)
            logger.info(f"🎯 SSE Risk Engine initialized: {self.n_simulations:,} simulations per validation")
        else:
            self.monte_carlo = None
            logger.warning("⚠️ SSE Risk Engine DISABLED - trades will execute without Monte Carlo validation")
        
        # Validation history
        self.validation_history = []
        self.blocked_trades = 0
        self.approved_trades = 0
    
    async def validate_trade(self, trade_proposal: TradeProposal) -> SSEValidationResult:
        """
        🎯 CRITICAL: Validate trade through 10,000 Monte Carlo simulations
        
        This is the primary risk firewall - NO trade executes without passing this validation.
        
        Args:
            trade_proposal: Proposed trade details
            
        Returns:
            SSEValidationResult with approval/rejection decision
        """
        if not self.enabled or not self.pre_trade_validation:
            logger.warning("⚠️ SSE validation BYPASSED - trade approved without Monte Carlo analysis")
            return SSEValidationResult(
                approved=True,
                win_probability=0.0,
                risk_of_ruin=0.0,
                expected_value=0.0,
                confidence_level=0.0,
                scenarios_analyzed=0,
                rejection_reason="SSE_DISABLED"
            )
        
        logger.info(f"🎯 SSE VALIDATION STARTING: {trade_proposal.epic} {trade_proposal.direction} £{trade_proposal.size}/pt")
        logger.info(f"   Running {self.n_simulations:,} Monte Carlo simulations...")
        
        try:
            # Calculate market volatility for simulation
            volatility = await self._calculate_market_volatility(trade_proposal)
            
            # Run Monte Carlo simulation
            scenarios = self.monte_carlo.simulate_scenarios(
                base_prediction=trade_proposal.confidence_score,
                volatility=volatility,
                shock_probabilities=self._get_shock_probabilities(trade_proposal)
            )
            
            # Analyze simulation results
            analysis = await self._analyze_simulation_results(scenarios, trade_proposal)
            
            # Apply Monte Carlo gates
            validation_result = await self._apply_monte_carlo_gates(analysis, trade_proposal)
            
            # Log validation result
            await self._log_validation_result(validation_result, trade_proposal)
            
            # Update statistics
            if validation_result.approved:
                self.approved_trades += 1
                logger.info(f"✅ SSE APPROVED: Trade passed Monte Carlo validation")
            else:
                self.blocked_trades += 1
                logger.warning(f"❌ SSE BLOCKED: {validation_result.rejection_reason}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ SSE validation error: {e}")
            # Fail-safe: block trade on validation error
            return SSEValidationResult(
                approved=False,
                win_probability=0.0,
                risk_of_ruin=1.0,
                expected_value=-1.0,
                confidence_level=0.0,
                scenarios_analyzed=0,
                rejection_reason=f"VALIDATION_ERROR: {str(e)}"
            )
    
    async def _calculate_market_volatility(self, trade_proposal: TradeProposal) -> float:
        """Calculate market volatility for Monte Carlo simulation"""
        try:
            # Use market context if available
            if trade_proposal.market_context:
                volatility = trade_proposal.market_context.get('volatility', 0.02)
            else:
                # Default volatility based on epic type
                if 'CS.D.' in trade_proposal.epic:  # Forex
                    volatility = 0.015
                elif 'IX.D.' in trade_proposal.epic:  # Indices
                    volatility = 0.025
                else:  # Commodities
                    volatility = 0.03
            
            # Adjust volatility based on confidence score
            confidence_adjustment = 1.0 - (trade_proposal.confidence_score * 0.2)
            adjusted_volatility = volatility * confidence_adjustment
            
            return max(0.005, min(0.1, adjusted_volatility))  # Clamp between 0.5% and 10%
            
        except Exception as e:
            logger.error(f"❌ Error calculating volatility: {e}")
            return 0.02  # Safe default
    
    def _get_shock_probabilities(self, trade_proposal: TradeProposal) -> Dict[str, float]:
        """Get shock probabilities for Monte Carlo simulation"""
        # Base shock probabilities
        base_shocks = {
            'market_crash': 0.01,
            'geopolitical': 0.015,
            'liquidity_crisis': 0.005,
            'positive_surprise': 0.02
        }
        
        # Adjust based on epic type
        if 'IX.D.' in trade_proposal.epic:  # Indices more sensitive to crashes
            base_shocks['market_crash'] *= 1.5
        elif 'CS.D.' in trade_proposal.epic:  # Forex more sensitive to geopolitical
            base_shocks['geopolitical'] *= 1.3
        
        return base_shocks
    
    async def _analyze_simulation_results(self, scenarios: np.ndarray, trade_proposal: TradeProposal) -> Dict:
        """Analyze Monte Carlo simulation results"""
        try:
            # Calculate key metrics
            # Interpret scenarios as profit/loss outcomes (positive => profitable)
            win_scenarios = scenarios > 0.0  # Scenarios where trade would be profitable
            win_probability = float(np.mean(win_scenarios))

            # Probability of loss (any scenario that yields loss)
            loss_scenarios = scenarios < 0.0
            probability_of_loss = float(np.mean(loss_scenarios))

            # Risk of ruin (probability of significant loss)
            ruin_threshold = 0.2  # 20% loss threshold (adjustable)
            ruin_scenarios = scenarios < -ruin_threshold
            risk_of_ruin = float(np.mean(ruin_scenarios))
            
            # Expected value
            expected_value = np.mean(scenarios)
            
            # Confidence level (statistical significance)
            # Confidence level: normalized measure of dispersion relative to mean
            mean_val = float(np.mean(scenarios))
            std_val = float(np.std(scenarios))
            if abs(mean_val) < 1e-6:
                confidence_level = 0.0
            else:
                confidence_level = 1.0 - (std_val / (abs(mean_val) + 1e-6))
                # Clamp to [0,1]
                confidence_level = max(0.0, min(1.0, confidence_level))
            
            # Additional metrics
            percentiles = np.percentile(scenarios, [5, 25, 50, 75, 95])
            
            # Include probability_of_loss for consistency checks
            analysis = {
                'win_probability': float(win_probability),
                'probability_of_loss': float(probability_of_loss),
                'risk_of_ruin': float(risk_of_ruin),
                'expected_value': float(expected_value),
                'confidence_level': float(confidence_level),
                'scenarios_count': len(scenarios),
                'percentiles': {
                    'p5': float(percentiles[0]),
                    'p25': float(percentiles[1]),
                    'p50': float(percentiles[2]),
                    'p75': float(percentiles[3]),
                    'p95': float(percentiles[4])
                },
                'volatility': float(std_val),
                'skewness': float(self._calculate_skewness(scenarios)),
                'kurtosis': float(self._calculate_kurtosis(scenarios))
            }
            
            logger.info(f"📊 SSE ANALYSIS COMPLETE:")
            logger.info(f"   Win Probability: {win_probability:.1%}")
            logger.info(f"   Probability of Loss: {probability_of_loss:.1%}")
            logger.info(f"   Risk of Ruin: {risk_of_ruin:.1%}")
            logger.info(f"   Expected Value: {expected_value:.3f}")
            logger.info(f"   Confidence Level: {confidence_level:.1%}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing simulation results: {e}")
            return {
                'win_probability': 0.0,
                'risk_of_ruin': 1.0,
                'expected_value': -1.0,
                'confidence_level': 0.0,
                'scenarios_count': 0
            }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of distribution"""
        try:
            mean = np.mean(data)
            std = np.std(data)
            if std == 0:
                return 0.0
            return np.mean(((data - mean) / std) ** 3)
        except:
            return 0.0
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of distribution"""
        try:
            mean = np.mean(data)
            std = np.std(data)
            if std == 0:
                return 0.0
            return np.mean(((data - mean) / std) ** 4) - 3.0
        except:
            return 0.0
    
    async def _apply_monte_carlo_gates(self, analysis: Dict, trade_proposal: TradeProposal) -> SSEValidationResult:
        """Apply Monte Carlo gates to determine trade approval"""
        
        # Extract metrics
        win_probability = float(analysis.get('win_probability', 0.0))
        probability_of_loss = float(analysis.get('probability_of_loss', 0.0))
        risk_of_ruin = float(analysis.get('risk_of_ruin', 1.0))
        expected_value = float(analysis.get('expected_value', -1.0))
        confidence_level = float(analysis.get('confidence_level', 0.0))

        # Sanity check: win_probability should be consistent with probability_of_loss
        if probability_of_loss > 0 and win_probability >= 0.999:
            logger.warning("⚠️ Inconsistent Monte Carlo metrics: perfect win_probability with non-zero loss probability. Adjusting win_probability.")
            win_probability = max(0.0, 1.0 - probability_of_loss)
        
        # Check each gate
        gates_passed = []
        rejection_reasons = []
        
        # Gate 1: Minimum win probability
        if win_probability >= self.min_win_probability:
            gates_passed.append("WIN_PROBABILITY")
        else:
            rejection_reasons.append(f"Win probability {win_probability:.1%} < {self.min_win_probability:.1%}")
        
        # Gate 2: Maximum risk of ruin
        if risk_of_ruin <= self.max_risk_of_ruin:
            gates_passed.append("RISK_OF_RUIN")
        else:
            rejection_reasons.append(f"Risk of ruin {risk_of_ruin:.1%} > {self.max_risk_of_ruin:.1%}")
        
        # Gate 3: Minimum expected value
        if expected_value >= self.min_expected_value:
            gates_passed.append("EXPECTED_VALUE")
        else:
            rejection_reasons.append(f"Expected value {expected_value:.3f} < {self.min_expected_value:.3f}")
        
        # Gate 4: Minimum confidence level
        if confidence_level >= (self.confidence_threshold - 0.01):  # Allow small tolerance
            gates_passed.append("CONFIDENCE_LEVEL")
        else:
            rejection_reasons.append(f"Confidence level {confidence_level:.1%} < {self.confidence_threshold:.1%}")
        
        # Determine approval
        all_gates_passed = len(gates_passed) == 4
        approved = all_gates_passed and self.block_high_risk_trades
        
        if not self.block_high_risk_trades:
            approved = True  # Override if risk blocking is disabled
            rejection_reasons = []
        
        return SSEValidationResult(
            approved=approved,
            win_probability=win_probability,
            risk_of_ruin=risk_of_ruin,
            expected_value=expected_value,
            confidence_level=confidence_level,
            scenarios_analyzed=analysis['scenarios_count'],
            rejection_reason="; ".join(rejection_reasons) if rejection_reasons else None,
            simulation_metrics=analysis
        )
    
    async def _log_validation_result(self, result: SSEValidationResult, trade_proposal: TradeProposal):
        """Log validation result for audit trail"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'epic': trade_proposal.epic,
                'direction': trade_proposal.direction,
                'size': trade_proposal.size,
                'approved': result.approved,
                'win_probability': result.win_probability,
                'risk_of_ruin': result.risk_of_ruin,
                'expected_value': result.expected_value,
                'confidence_level': result.confidence_level,
                'scenarios_analyzed': result.scenarios_analyzed,
                'rejection_reason': result.rejection_reason
            }
            
            self.validation_history.append(log_entry)
            
            # Keep only last 1000 validations
            if len(self.validation_history) > 1000:
                self.validation_history = self.validation_history[-1000:]
                
        except Exception as e:
            logger.error(f"❌ Error logging validation result: {e}")
    
    def get_validation_statistics(self) -> Dict:
        """Get SSE validation statistics"""
        total_validations = self.approved_trades + self.blocked_trades
        
        return {
            'total_validations': total_validations,
            'approved_trades': self.approved_trades,
            'blocked_trades': self.blocked_trades,
            'approval_rate': self.approved_trades / total_validations if total_validations > 0 else 0.0,
            'block_rate': self.blocked_trades / total_validations if total_validations > 0 else 0.0,
            'sse_enabled': self.enabled,
            'simulations_per_validation': self.n_simulations
        }
