"""
Margin Safety Module

Implements proper margin safety calculations with trade blocking when insufficient funds.
Fixes the issue where £0.05 margin-safe sizing with £3/unit margin results in 0 units.
"""

import logging
from typing import Tuple, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarginCalculation:
    """Result of margin safety calculation"""
    safe_units: float
    required_margin: float
    available_margin: float
    safety_factor: float
    is_blocked: bool
    block_reason: str
    calculation_details: Dict


def calculate_safe_units(
    available_margin: float, 
    margin_per_unit: float, 
    safety_factor: float = 1.2,
    min_units: float = 0.1,
    max_units: Optional[float] = None
) -> MarginCalculation:
    """
    Calculate safe position size with margin constraints.
    
    Returns 0 and blocks trade if insufficient margin.
    Never allows trades that would exceed margin requirements.
    
    Args:
        available_margin: Available margin in account currency
        margin_per_unit: Margin requirement per unit of position
        safety_factor: Safety multiplier (default 1.2 = 20% buffer)
        min_units: Minimum viable position size
        max_units: Maximum allowed position size (optional)
    
    Returns:
        MarginCalculation with safe units and blocking logic
    """
    logger.debug(f"🔍 Margin Safety Calculation:")
    logger.debug(f"   Available Margin: £{available_margin:.2f}")
    logger.debug(f"   Margin Per Unit: £{margin_per_unit:.2f}")
    logger.debug(f"   Safety Factor: {safety_factor:.2f}")
    
    # Calculate theoretical maximum units without safety factor
    if margin_per_unit <= 0:
        return MarginCalculation(
            safe_units=0.0,
            required_margin=0.0,
            available_margin=available_margin,
            safety_factor=safety_factor,
            is_blocked=True,
            block_reason="Invalid margin per unit (≤0)",
            calculation_details={"error": "margin_per_unit_invalid"}
        )
    
    theoretical_max_units = available_margin / margin_per_unit
    
    # Apply safety factor
    safe_max_units = theoretical_max_units / safety_factor
    
    # Check if we can meet minimum position size
    min_required_margin = min_units * margin_per_unit * safety_factor
    
    if available_margin < min_required_margin:
        return MarginCalculation(
            safe_units=0.0,
            required_margin=min_required_margin,
            available_margin=available_margin,
            safety_factor=safety_factor,
            is_blocked=True,
            block_reason=f"Insufficient margin for minimum position. Need £{min_required_margin:.2f}, have £{available_margin:.2f}",
            calculation_details={
                "theoretical_max_units": theoretical_max_units,
                "safe_max_units": safe_max_units,
                "min_required_margin": min_required_margin,
                "shortfall": min_required_margin - available_margin
            }
        )
    
    # Determine safe units
    if safe_max_units < min_units:
        # Can afford minimum but not safely - block trade
        return MarginCalculation(
            safe_units=0.0,
            required_margin=min_units * margin_per_unit,
            available_margin=available_margin,
            safety_factor=safety_factor,
            is_blocked=True,
            block_reason=f"Safe units ({safe_max_units:.3f}) below minimum ({min_units})",
            calculation_details={
                "theoretical_max_units": theoretical_max_units,
                "safe_max_units": safe_max_units,
                "min_units": min_units
            }
        )
    
    # Calculate final safe units
    safe_units = safe_max_units
    
    # Apply maximum limit if specified
    if max_units and safe_units > max_units:
        safe_units = max_units
        logger.debug(f"   Units capped at maximum: {max_units}")
    
    # Round to appropriate precision (0.1 for most brokers)
    safe_units = round(safe_units, 1)
    
    # Final validation - ensure we don't exceed available margin
    required_margin = safe_units * margin_per_unit * safety_factor
    
    if required_margin > available_margin:
        # Recalculate to fit exactly
        safe_units = available_margin / (margin_per_unit * safety_factor)
        safe_units = round(safe_units, 1)
        required_margin = safe_units * margin_per_unit * safety_factor
    
    calculation_details = {
        "theoretical_max_units": theoretical_max_units,
        "safe_max_units": safe_max_units,
        "final_safe_units": safe_units,
        "required_margin": required_margin,
        "margin_utilization": (required_margin / available_margin) * 100
    }
    
    logger.info(f"✅ Margin Safety Result:")
    logger.info(f"   Safe Units: {safe_units}")
    logger.info(f"   Required Margin: £{required_margin:.2f}")
    logger.info(f"   Margin Utilization: {calculation_details['margin_utilization']:.1f}%")
    
    return MarginCalculation(
        safe_units=safe_units,
        required_margin=required_margin,
        available_margin=available_margin,
        safety_factor=safety_factor,
        is_blocked=False,
        block_reason="",
        calculation_details=calculation_details
    )


def validate_margin_before_trade(
    position_size: float,
    margin_per_unit: float,
    available_margin: float,
    safety_factor: float = 1.2
) -> Tuple[bool, str]:
    """
    Validate margin requirements before executing a trade.
    
    Args:
        position_size: Proposed position size
        margin_per_unit: Margin requirement per unit
        available_margin: Available margin in account
        safety_factor: Safety buffer multiplier
    
    Returns:
        Tuple of (is_valid, reason)
    """
    required_margin = position_size * margin_per_unit * safety_factor
    
    if required_margin > available_margin:
        shortfall = required_margin - available_margin
        return False, f"Insufficient margin: need £{required_margin:.2f}, have £{available_margin:.2f} (shortfall: £{shortfall:.2f})"
    
    utilization = (required_margin / available_margin) * 100
    
    if utilization > 80:  # Warn if using >80% of available margin
        logger.warning(f"⚠️  High margin utilization: {utilization:.1f}%")
    
    return True, f"Margin OK: £{required_margin:.2f} required, {utilization:.1f}% utilization"


def calculate_position_size_from_risk(
    risk_amount: float,
    stop_distance_points: float,
    point_value: float = 1.0
) -> float:
    """
    Calculate position size based on risk amount and stop distance.
    
    Args:
        risk_amount: Maximum amount willing to risk (in account currency)
        stop_distance_points: Distance to stop loss in points
        point_value: Value per point (default 1.0 for most instruments)
    
    Returns:
        Position size in units
    """
    if stop_distance_points <= 0:
        logger.error("❌ Invalid stop distance: must be > 0")
        return 0.0
    
    position_size = risk_amount / (stop_distance_points * point_value)
    return round(position_size, 1)


class MarginSafetyEngine:
    """
    Comprehensive margin safety engine for position sizing.
    
    Integrates risk-based sizing with margin constraints.
    """
    
    def __init__(self, default_safety_factor: float = 1.2):
        self.default_safety_factor = default_safety_factor
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_optimal_position_size(
        self,
        risk_amount: float,
        stop_distance_points: float,
        available_margin: float,
        margin_per_unit: float,
        point_value: float = 1.0,
        min_units: float = 0.1
    ) -> MarginCalculation:
        """
        Calculate optimal position size considering both risk and margin constraints.
        
        Returns the smaller of risk-based size and margin-safe size.
        """
        # Calculate risk-based position size
        risk_based_size = calculate_position_size_from_risk(
            risk_amount, stop_distance_points, point_value
        )
        
        # Calculate margin-safe position size
        margin_calc = calculate_safe_units(
            available_margin, margin_per_unit, self.default_safety_factor, min_units
        )
        
        if margin_calc.is_blocked:
            return margin_calc
        
        # Use the smaller of the two
        optimal_size = min(risk_based_size, margin_calc.safe_units)
        
        # Recalculate with optimal size
        return calculate_safe_units(
            available_margin, margin_per_unit, self.default_safety_factor, 
            min_units, max_units=optimal_size
        )
