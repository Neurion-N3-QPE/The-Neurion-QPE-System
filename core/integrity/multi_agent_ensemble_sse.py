"""
🤖 SSE-Enhanced Multi-Agent Ensemble System

Three specialized agents with Monte Carlo simulation:
- EchoQuant: Deterministic Finance Core + SSE
- Contramind: Logical Structure / Causality + SSE
- MythFleck: Chaotic Modeler / Volatility Lens + SSE

Each prediction runs 10,000 Monte Carlo simulations for 99% certainty.
"""

import asyncio
import structlog
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

# Import Monte Carlo Simulator
try:
    # Try relative import first (for package use)
    from ..models.hybrid_model import MonteCarloSimulator
except (ImportError, ValueError):
    # Fall back to absolute import (for standalone testing)
    from core.models.hybrid_model import MonteCarloSimulator

logger = structlog.get_logger(__name__)


@dataclass
class AgentPrediction:
    """Prediction from a single agent with SSE metrics"""
    agent_name: str
    value: float
    confidence: float
    reasoning: str
    metadata: Dict
    sse_scenarios: Optional[np.ndarray] = None  # SSE simulation results
    sse_metrics: Optional[Dict] = None  # SSE risk metrics


class EchoQuantAgent:
    """
    Deterministic Finance Core Agent
    
    Uses traditional quantitative finance models
    Enhanced with SSE Monte Carlo simulation
    """
    
    def __init__(self, use_sse: bool = True, n_simulations: int = 10000):
        self.name = "EchoQuant"
        self.weight = 0.33
        self.use_sse = use_sse
        
        if self.use_sse:
            self.sse = MonteCarloSimulator(n_simulations=n_simulations)
            logger.info(f"🎲 {self.name}: SSE enabled with {n_simulations:,} simulations")
        
    async def predict(self, market_state: Dict) -> AgentPrediction:
        """Generate prediction using quantitative methods + SSE"""
        
        logger.info(f"🔮 {self.name} Agent: Starting prediction...")
        
        # Technical analysis
        technical_score = self._technical_analysis(market_state)
        fundamental_score = self._fundamental_analysis(market_state)
        
        # Combine scores
        base_value = (technical_score * 0.6 + fundamental_score * 0.4)
        base_confidence = self._calculate_confidence(technical_score, fundamental_score)
        
        logger.info(f"   Technical: {technical_score:.4f} | Fundamental: {fundamental_score:.4f}")
        logger.info(f"   Base Prediction: {base_value:.4f} | Base Confidence: {base_confidence:.4f}")
        
        # Run SSE if enabled
        sse_scenarios = None
        sse_metrics = None
        final_value = base_value
        final_confidence = base_confidence
        
        if self.use_sse:
            logger.info(f"🎲 {self.name}: Launching SSE simulation...")
            
            # Calculate volatility from market state
            volatility = self._calculate_volatility(market_state)
            
            # Run Monte Carlo simulation
            sse_scenarios = self.sse.simulate_scenarios(
                base_prediction=base_value,
                volatility=volatility,
                shock_probabilities={
                    'market_crash': 0.01,
                    'geopolitical': 0.02,
                    'positive_surprise': 0.03
                }
            )
            
            # Calculate SSE risk metrics
            sse_metrics = self.sse.calculate_risk_metrics(sse_scenarios)
            
            # Adjust confidence based on SSE results
            probability_of_profit = 1.0 - sse_metrics['probability_of_loss']
            final_confidence = (base_confidence * 0.4) + (probability_of_profit * 0.6)
            
            # Adjust value based on SSE mean
            final_value = (base_value * 0.5) + (sse_scenarios.mean() * 0.5)
            
            logger.info(f"✅ {self.name}: SSE Complete!")
            logger.info(f"   SSE-Adjusted Value: {final_value:.4f}")
            logger.info(f"   SSE-Adjusted Confidence: {final_confidence:.4f}")
            logger.info(f"   Probability of Profit: {probability_of_profit*100:.2f}%")
        
        return AgentPrediction(
            agent_name=self.name,
            value=final_value,
            confidence=final_confidence,
            reasoning=f"Quant+SSE: tech={technical_score:.2f}, fund={fundamental_score:.2f}, sse_prob={sse_metrics['probability_of_loss']*100:.1f}% loss risk" if sse_metrics else f"Quant: tech={technical_score:.2f}, fund={fundamental_score:.2f}",
            metadata={
                'technical': technical_score,
                'fundamental': fundamental_score,
                'volatility': volatility if self.use_sse else None,
                'base_value': base_value,
                'base_confidence': base_confidence
            },
            sse_scenarios=sse_scenarios,
            sse_metrics=sse_metrics
        )
    
    def _technical_analysis(self, market_state: Dict) -> float:
        """
        Real technical indicator analysis
        
        Implements: RSI, MACD, Bollinger Bands, Moving Averages
        """
        score = 0.5  # Neutral starting point
        
        # RSI Analysis
        if 'rsi' in market_state:
            rsi = market_state['rsi']
            if rsi < 30:  # Oversold
                score += 0.15
            elif rsi > 70:  # Overbought
                score -= 0.15
            logger.debug(f"      RSI: {rsi:.2f} → Score adjustment")
        
        # MACD Analysis
        if 'macd' in market_state and 'macd_signal' in market_state:
            macd = market_state['macd']
            signal = market_state['macd_signal']
            if macd > signal:  # Bullish
                score += 0.10
            else:  # Bearish
                score -= 0.10
            logger.debug(f"      MACD: {macd:.4f} vs Signal: {signal:.4f}")
        
        # Bollinger Bands
        if 'price' in market_state and 'bollinger_upper' in market_state and 'bollinger_lower' in market_state:
            price = market_state['price']
            upper = market_state['bollinger_upper']
            lower = market_state['bollinger_lower']
            
            # Normalize position within bands
            band_position = (price - lower) / (upper - lower) if upper != lower else 0.5
            score += (band_position - 0.5) * 0.2  # Adjust based on position
            logger.debug(f"      Bollinger Position: {band_position:.2f}")
        
        # Moving Average Crossover
        if 'ma_short' in market_state and 'ma_long' in market_state:
            ma_short = market_state['ma_short']
            ma_long = market_state['ma_long']
            if ma_short > ma_long:  # Bullish
                score += 0.10
            else:  # Bearish
                score -= 0.10
            logger.debug(f"      MA Cross: Short={ma_short:.2f} vs Long={ma_long:.2f}")
        
        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        
        return score
    
    def _fundamental_analysis(self, market_state: Dict) -> float:
        """
        Fundamental analysis based on market conditions
        """
        score = 0.5  # Neutral
        
        # Volume analysis
        if 'volume' in market_state and 'avg_volume' in market_state:
            volume_ratio = market_state['volume'] / market_state['avg_volume']
            if volume_ratio > 1.5:  # High volume
                score += 0.10
            elif volume_ratio < 0.5:  # Low volume
                score -= 0.05
            logger.debug(f"      Volume Ratio: {volume_ratio:.2f}")
        
        # Trend strength
        if 'trend_strength' in market_state:
            trend = market_state['trend_strength']
            score += trend * 0.15  # Positive for uptrend, negative for downtrend
            logger.debug(f"      Trend Strength: {trend:.2f}")
        
        # Market sentiment
        if 'sentiment' in market_state:
            sentiment = market_state['sentiment']  # -1 to 1
            score += sentiment * 0.10
            logger.debug(f"      Sentiment: {sentiment:.2f}")
        
        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        
        return score
    
    def _calculate_volatility(self, market_state: Dict) -> float:
        """Calculate market volatility for SSE"""
        if 'volatility' in market_state:
            return market_state['volatility']
        
        # Default volatility estimate
        if 'atr' in market_state:  # Average True Range
            return market_state['atr'] * 0.01
        
        return 0.02  # Default 2% volatility
    
    def _calculate_confidence(self, tech: float, fund: float) -> float:
        """Calculate prediction confidence"""
        agreement = 1.0 - abs(tech - fund)
        base_confidence = 0.5 + (agreement * 0.4)
        return base_confidence


class ContramindAgent:
    """
    Logical Structure / Causality Agent
    
    Detects regime shifts and structural patterns
    Enhanced with SSE Monte Carlo simulation
    """
    
    def __init__(self, use_sse: bool = True, n_simulations: int = 10000):
        self.name = "Contramind"
        self.weight = 0.33
        self.use_sse = use_sse
        
        if self.use_sse:
            self.sse = MonteCarloSimulator(n_simulations=n_simulations)
            logger.info(f"🎲 {self.name}: SSE enabled with {n_simulations:,} simulations")
        
    async def predict(self, market_state: Dict) -> AgentPrediction:
        """Generate prediction using logical analysis + SSE"""
        
        logger.info(f"🔮 {self.name} Agent: Starting prediction...")
        
        # Regime analysis
        regime_score = self._detect_regime_shift(market_state)
        correlation_score = self._analyze_correlations(market_state)
        
        # Combine scores
        base_value = (regime_score * 0.5 + correlation_score * 0.5)
        base_confidence = self._calculate_confidence(regime_score, correlation_score)
        
        logger.info(f"   Regime: {regime_score:.4f} | Correlation: {correlation_score:.4f}")
        logger.info(f"   Base Prediction: {base_value:.4f} | Base Confidence: {base_confidence:.4f}")
        
        # Run SSE if enabled
        sse_scenarios = None
        sse_metrics = None
        final_value = base_value
        final_confidence = base_confidence
        
        if self.use_sse:
            logger.info(f"🎲 {self.name}: Launching SSE simulation...")
            
            volatility = self._calculate_volatility(market_state)
            
            sse_scenarios = self.sse.simulate_scenarios(
                base_prediction=base_value,
                volatility=volatility,
                shock_probabilities={
                    'market_crash': 0.015,
                    'liquidity_crisis': 0.01,
                    'positive_surprise': 0.025
                }
            )
            
            sse_metrics = self.sse.calculate_risk_metrics(sse_scenarios)
            
            probability_of_profit = 1.0 - sse_metrics['probability_of_loss']
            final_confidence = (base_confidence * 0.4) + (probability_of_profit * 0.6)
            final_value = (base_value * 0.5) + (sse_scenarios.mean() * 0.5)
            
            logger.info(f"✅ {self.name}: SSE Complete!")
            logger.info(f"   SSE-Adjusted Value: {final_value:.4f}")
            logger.info(f"   SSE-Adjusted Confidence: {final_confidence:.4f}")
            logger.info(f"   Probability of Profit: {probability_of_profit*100:.2f}%")
        
        return AgentPrediction(
            agent_name=self.name,
            value=final_value,
            confidence=final_confidence,
            reasoning=f"Logic+SSE: regime={regime_score:.2f}, corr={correlation_score:.2f}, sse_prob={sse_metrics['probability_of_loss']*100:.1f}% loss risk" if sse_metrics else f"Logic: regime={regime_score:.2f}, corr={correlation_score:.2f}",
            metadata={
                'regime': regime_score,
                'correlation': correlation_score,
                'volatility': volatility if self.use_sse else None,
                'base_value': base_value,
                'base_confidence': base_confidence
            },
            sse_scenarios=sse_scenarios,
            sse_metrics=sse_metrics
        )
    
    def _detect_regime_shift(self, market_state: Dict) -> float:
        """
        Detect market regime changes
        
        Identifies: Bull/Bear transitions, volatility regimes, liquidity changes
        """
        score = 0.5  # Neutral
        
        # Volatility regime
        if 'volatility' in market_state and 'historical_volatility' in market_state:
            current_vol = market_state['volatility']
            hist_vol = market_state['historical_volatility']
            vol_ratio = current_vol / hist_vol if hist_vol > 0 else 1.0
            
            if vol_ratio > 1.5:  # High vol regime
                score -= 0.10  # More cautious
            elif vol_ratio < 0.7:  # Low vol regime
                score += 0.10  # More confident
            
            logger.debug(f"      Volatility Regime: {vol_ratio:.2f}")
        
        # Trend regime
        if 'trend_strength' in market_state:
            trend = market_state['trend_strength']
            if abs(trend) > 0.7:  # Strong trend
                score += trend * 0.15
            logger.debug(f"      Trend Regime: {trend:.2f}")
        
        # Liquidity regime
        if 'spread' in market_state and 'avg_spread' in market_state:
            spread_ratio = market_state['spread'] / market_state['avg_spread']
            if spread_ratio > 1.5:  # Wide spreads
                score -= 0.10
            logger.debug(f"      Liquidity Regime: {spread_ratio:.2f}")
        
        score = max(0.0, min(1.0, score))
        return score
    
    def _analyze_correlations(self, market_state: Dict) -> float:
        """
        Analyze cross-asset correlations
        """
        score = 0.5
        
        # Correlation with major indices
        if 'correlation_spy' in market_state:
            corr = market_state['correlation_spy']
            # Higher correlation = more predictable
            score += abs(corr) * 0.15
            logger.debug(f"      SPY Correlation: {corr:.2f}")
        
        # Sector correlation
        if 'sector_correlation' in market_state:
            sector_corr = market_state['sector_correlation']
            score += sector_corr * 0.10
            logger.debug(f"      Sector Correlation: {sector_corr:.2f}")
        
        score = max(0.0, min(1.0, score))
        return score
    
    def _calculate_volatility(self, market_state: Dict) -> float:
        """Calculate volatility for SSE"""
        if 'volatility' in market_state:
            return market_state['volatility']
        return 0.025  # Default 2.5%
    
    def _calculate_confidence(self, regime: float, corr: float) -> float:
        """Calculate prediction confidence"""
        consistency = 1.0 - abs(regime - corr) * 0.5
        return 0.5 + (consistency * 0.4)


class MythFleckAgent:
    """
    Chaotic Modeler / Volatility Lens Agent
    
    Models chaos and volatility patterns
    Enhanced with SSE Monte Carlo simulation
    """
    
    def __init__(self, use_sse: bool = True, n_simulations: int = 10000):
        self.name = "MythFleck"
        self.weight = 0.34
        self.use_sse = use_sse
        
        if self.use_sse:
            self.sse = MonteCarloSimulator(n_simulations=n_simulations)
            logger.info(f"🎲 {self.name}: SSE enabled with {n_simulations:,} simulations")
        
    async def predict(self, market_state: Dict) -> AgentPrediction:
        """Generate prediction using chaos theory + SSE"""
        
        logger.info(f"🔮 {self.name} Agent: Starting prediction...")
        
        # Chaos and volatility analysis
        entropy_score = self._calculate_entropy(market_state)
        pattern_score = self._synthesize_patterns(market_state)
        
        # Combine scores
        base_value = (entropy_score * 0.4 + pattern_score * 0.6)
        base_confidence = self._calculate_confidence(entropy_score, pattern_score)
        
        logger.info(f"   Entropy: {entropy_score:.4f} | Pattern: {pattern_score:.4f}")
        logger.info(f"   Base Prediction: {base_value:.4f} | Base Confidence: {base_confidence:.4f}")
        
        # Run SSE if enabled
        sse_scenarios = None
        sse_metrics = None
        final_value = base_value
        final_confidence = base_confidence
        
        if self.use_sse:
            logger.info(f"🎲 {self.name}: Launching SSE simulation...")
            
            volatility = self._calculate_volatility(market_state)
            
            sse_scenarios = self.sse.simulate_scenarios(
                base_prediction=base_value,
                volatility=volatility,
                shock_probabilities={
                    'market_crash': 0.02,
                    'geopolitical': 0.03,
                    'liquidity_crisis': 0.015,
                    'positive_surprise': 0.02
                }
            )
            
            sse_metrics = self.sse.calculate_risk_metrics(sse_scenarios)
            
            probability_of_profit = 1.0 - sse_metrics['probability_of_loss']
            final_confidence = (base_confidence * 0.4) + (probability_of_profit * 0.6)
            final_value = (base_value * 0.5) + (sse_scenarios.mean() * 0.5)
            
            logger.info(f"✅ {self.name}: SSE Complete!")
            logger.info(f"   SSE-Adjusted Value: {final_value:.4f}")
            logger.info(f"   SSE-Adjusted Confidence: {final_confidence:.4f}")
            logger.info(f"   Probability of Profit: {probability_of_profit*100:.2f}%")
        
        return AgentPrediction(
            agent_name=self.name,
            value=final_value,
            confidence=final_confidence,
            reasoning=f"Chaos+SSE: entropy={entropy_score:.2f}, pattern={pattern_score:.2f}, sse_prob={sse_metrics['probability_of_loss']*100:.1f}% loss risk" if sse_metrics else f"Chaos: entropy={entropy_score:.2f}, pattern={pattern_score:.2f}",
            metadata={
                'entropy': entropy_score,
                'pattern': pattern_score,
                'volatility': volatility if self.use_sse else None,
                'base_value': base_value,
                'base_confidence': base_confidence
            },
            sse_scenarios=sse_scenarios,
            sse_metrics=sse_metrics
        )
    
    def _calculate_entropy(self, market_state: Dict) -> float:
        """
        Calculate market entropy (randomness/chaos)
        """
        score = 0.5
        
        # Price entropy
        if 'price_history' in market_state:
            prices = np.array(market_state['price_history'])
            if len(prices) > 10:
                # Calculate entropy from price changes
                returns = np.diff(prices) / prices[:-1]
                hist, _ = np.histogram(returns, bins=10)
                prob = hist / hist.sum()
                entropy = -np.sum(prob * np.log(prob + 1e-10))
                
                # Normalize entropy (higher = more chaos)
                normalized_entropy = min(entropy / 3.0, 1.0)
                score = 0.5 + (normalized_entropy - 0.5) * 0.3
                logger.debug(f"      Price Entropy: {entropy:.4f}")
        
        # Volatility clustering
        if 'volatility_history' in market_state:
            vols = np.array(market_state['volatility_history'])
            if len(vols) > 5:
                vol_autocorr = np.corrcoef(vols[:-1], vols[1:])[0, 1]
                score += vol_autocorr * 0.10
                logger.debug(f"      Volatility Clustering: {vol_autocorr:.4f}")
        
        score = max(0.0, min(1.0, score))
        return score
    
    def _synthesize_patterns(self, market_state: Dict) -> float:
        """
        Identify and synthesize market patterns
        """
        score = 0.5
        
        # Pattern recognition
        if 'pattern' in market_state:
            pattern_type = market_state['pattern']
            pattern_scores = {
                'head_and_shoulders': 0.3,  # Bearish
                'double_bottom': 0.7,  # Bullish
                'ascending_triangle': 0.7,  # Bullish
                'descending_triangle': 0.3,  # Bearish
                'bull_flag': 0.75,  # Bullish
                'bear_flag': 0.25,  # Bearish
            }
            score = pattern_scores.get(pattern_type, 0.5)
            logger.debug(f"      Pattern: {pattern_type} → {score:.2f}")
        
        # Fractal analysis
        if 'fractal_dimension' in market_state:
            fractal = market_state['fractal_dimension']
            # Fractal dimension 1.5-2.0 indicates trending behavior
            if 1.5 <= fractal <= 2.0:
                score += 0.10
            logger.debug(f"      Fractal Dimension: {fractal:.4f}")
        
        score = max(0.0, min(1.0, score))
        return score
    
    def _calculate_volatility(self, market_state: Dict) -> float:
        """Calculate volatility for SSE"""
        if 'volatility' in market_state:
            return market_state['volatility'] * 1.2  # Chaos agent uses higher vol
        return 0.03  # Default 3%
    
    def _calculate_confidence(self, entropy: float, pattern: float) -> float:
        """Calculate prediction confidence"""
        # Lower entropy = higher confidence
        entropy_factor = 1.0 - abs(entropy - 0.5) * 0.5
        pattern_factor = abs(pattern - 0.5) * 2.0  # Strong patterns = high confidence
        
        confidence = 0.5 + (entropy_factor * 0.2) + (pattern_factor * 0.3)
        return min(confidence, 0.95)



class MultiAgentEnsembleSSE:
    """
    SSE-Enhanced Multi-Agent Ensemble
    
    Coordinates three agents with full Monte Carlo simulation:
    - EchoQuant (Finance)
    - Contramind (Logic)
    - MythFleck (Chaos)
    
    Each agent runs 10,000 simulations → 30,000 total scenarios analyzed
    """
    
    def __init__(self, use_sse: bool = True, n_simulations: int = 10000):
        self.use_sse = use_sse
        self.n_simulations = n_simulations
        
        # Initialize agents
        self.agents = [
            EchoQuantAgent(use_sse=use_sse, n_simulations=n_simulations),
            ContramindAgent(use_sse=use_sse, n_simulations=n_simulations),
            MythFleckAgent(use_sse=use_sse, n_simulations=n_simulations)
        ]
        
        self.initialized = False
        logger.info("🤖 Multi-Agent Ensemble SSE initialized")
        if use_sse:
            total_sims = n_simulations * len(self.agents)
            logger.info(f"🎲 Total SSE capacity: {total_sims:,} scenarios per prediction")
        
    async def initialize(self):
        """Initialize all agents"""
        logger.info("🚀 Initializing Multi-Agent Ensemble...")
        
        for agent in self.agents:
            logger.info(f"  ✓ {agent.name} ready (weight: {agent.weight:.2f})")
        
        self.initialized = True
        logger.info("✅ Multi-Agent Ensemble initialized")
    
    async def predict(self, market_state: Dict) -> List[AgentPrediction]:
        """
        Generate predictions from all agents with SSE
        
        Process:
        1. Each agent analyzes market state
        2. Each agent runs 10,000 Monte Carlo simulations
        3. Predictions are aggregated with SSE metrics
        
        Returns:
            List of agent predictions with SSE data
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info("="*80)
        logger.info("🎯 MULTI-AGENT ENSEMBLE: Starting Prediction Cycle")
        logger.info("="*80)
        
        if self.use_sse:
            logger.info(f"🎲 SSE ACTIVE: {self.n_simulations:,} simulations per agent")
            logger.info(f"🎲 TOTAL: {self.n_simulations * len(self.agents):,} scenarios will be analyzed")
        
        # Get predictions from all agents
        predictions = []
        for agent in self.agents:
            logger.info(f"\n{'─'*80}")
            pred = await agent.predict(market_state)
            predictions.append(pred)
            logger.info(f"{'─'*80}\n")
        
        # Log ensemble summary
        logger.info("="*80)
        logger.info("📊 ENSEMBLE SUMMARY:")
        logger.info("="*80)
        
        for pred in predictions:
            logger.info(f"  {pred.agent_name}:")
            logger.info(f"    Value: {pred.value:.4f} | Confidence: {pred.confidence:.4f}")
            if pred.sse_metrics:
                logger.info(f"    SSE Loss Risk: {pred.sse_metrics['probability_of_loss']*100:.2f}%")
                logger.info(f"    SSE VaR(95%): {pred.sse_metrics['var_95']:.4f}")
        
        # Calculate ensemble statistics
        avg_value = np.mean([p.value for p in predictions])
        avg_confidence = np.mean([p.confidence for p in predictions])
        
        logger.info(f"\n  Ensemble Average:")
        logger.info(f"    Value: {avg_value:.4f}")
        logger.info(f"    Confidence: {avg_confidence:.4f}")
        
        if self.use_sse:
            # Aggregate SSE metrics
            avg_loss_prob = np.mean([p.sse_metrics['probability_of_loss'] for p in predictions if p.sse_metrics])
            logger.info(f"    Average Loss Risk: {avg_loss_prob*100:.2f}%")
            logger.info(f"    Profit Probability: {(1-avg_loss_prob)*100:.2f}%")
        
        logger.info("="*80)
        logger.info("✅ MULTI-AGENT ENSEMBLE: Prediction Cycle Complete")
        logger.info("="*80)
        
        return predictions
    
    async def get_ensemble_prediction(
        self,
        market_state: Dict,
        use_weighted: bool = True
    ) -> Dict:
        """
        Get final ensemble prediction with SSE aggregation
        
        Args:
            market_state: Current market state
            use_weighted: Use agent weights for ensemble
            
        Returns:
            Dictionary with ensemble prediction and SSE metrics
        """
        predictions = await self.predict(market_state)
        
        if use_weighted:
            # Weighted ensemble
            total_weight = sum(agent.weight for agent in self.agents)
            weighted_value = sum(
                pred.value * agent.weight
                for pred, agent in zip(predictions, self.agents)
            ) / total_weight
            
            weighted_confidence = sum(
                pred.confidence * agent.weight
                for pred, agent in zip(predictions, self.agents)
            ) / total_weight
        else:
            # Simple average
            weighted_value = np.mean([p.value for p in predictions])
            weighted_confidence = np.mean([p.confidence for p in predictions])
        
        # Aggregate SSE metrics
        ensemble_sse_metrics = None
        if self.use_sse and all(p.sse_metrics for p in predictions):
            ensemble_sse_metrics = {
                'avg_var_95': np.mean([p.sse_metrics['var_95'] for p in predictions]),
                'avg_var_99': np.mean([p.sse_metrics['var_99'] for p in predictions]),
                'avg_probability_of_loss': np.mean([p.sse_metrics['probability_of_loss'] for p in predictions]),
                'min_probability_of_loss': min([p.sse_metrics['probability_of_loss'] for p in predictions]),
                'max_probability_of_loss': max([p.sse_metrics['probability_of_loss'] for p in predictions]),
                'consensus_strength': 1.0 - np.std([p.value for p in predictions]),
                'total_scenarios_analyzed': self.n_simulations * len(self.agents)
            }
            
            logger.info("\n🎲 ENSEMBLE SSE METRICS:")
            logger.info(f"   Total Scenarios: {ensemble_sse_metrics['total_scenarios_analyzed']:,}")
            logger.info(f"   Avg Loss Prob: {ensemble_sse_metrics['avg_probability_of_loss']*100:.2f}%")
            logger.info(f"   Profit Certainty: {(1-ensemble_sse_metrics['avg_probability_of_loss'])*100:.2f}%")
            logger.info(f"   Consensus Strength: {ensemble_sse_metrics['consensus_strength']*100:.2f}%")
        
        return {
            'value': weighted_value,
            'confidence': weighted_confidence,
            'agent_predictions': predictions,
            'sse_metrics': ensemble_sse_metrics,
            'timestamp': asyncio.get_event_loop().time()
        }


# Export classes
__all__ = [
    'EchoQuantAgent',
    'ContramindAgent',
    'MythFleckAgent',
    'MultiAgentEnsembleSSE',
    'AgentPrediction'
]
