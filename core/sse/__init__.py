"""
🎯 SSE (Simulated Scenario Engine) - Core Module

The SSE is the primary risk firewall that runs 10,000 Monte Carlo simulations
before EVERY live trade to ensure 99%+ certainty on trade outcomes.

Components:
- SSERiskEngine: Pre-trade Monte Carlo validation
- TradeProposal: Trade proposal data structure
- SSEValidationResult: Validation result data structure

This module prevents ANY trade from executing unless it passes rigorous
statistical validation through 10,000 simulated scenarios.
"""

from .sse_risk_engine import (
    SSERiskEngine,
    SSEValidationResult,
    TradeProposal
)

__all__ = [
    'SSERiskEngine',
    'SSEValidationResult', 
    'TradeProposal'
]
