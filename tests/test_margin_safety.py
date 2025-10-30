"""
Unit tests for margin safety calculations.

Tests the fixed margin calculations to ensure proper trade blocking
when insufficient funds and realistic position sizing.
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.risk_management.margin_safety import (
    calculate_safe_units, 
    validate_margin_before_trade,
    calculate_position_size_from_risk,
    MarginSafetyEngine
)


class TestMarginSafety:
    """Test suite for margin safety calculations"""
    
    def test_insufficient_margin_blocks_trade(self):
        """Test that insufficient margin properly blocks trades"""
        print("\n🧪 Testing margin blocking...")
        
        # Test case from the issue: £0.05 available, £3/unit margin
        result = calculate_safe_units(
            available_margin=0.05,
            margin_per_unit=3.0,
            safety_factor=1.2,
            min_units=0.1
        )
        
        assert result.is_blocked, "Trade should be blocked with insufficient margin"
        assert result.safe_units == 0.0, "Safe units should be 0 when blocked"
        assert "Insufficient margin" in result.block_reason
        
        print(f"✅ Blocked trade: {result.block_reason}")
        print(f"   Required: £{result.calculation_details.get('min_required_margin', 0):.2f}")
        print(f"   Available: £{result.available_margin:.2f}")
    
    def test_minimum_viable_position(self):
        """Test minimum viable position calculations"""
        print("\n🧪 Testing minimum viable positions...")
        
        # Test case: Just enough margin for minimum position
        min_units = 0.1
        margin_per_unit = 3.0
        safety_factor = 1.2
        required_margin = min_units * margin_per_unit * safety_factor  # £0.36
        
        # Provide exactly enough margin
        result = calculate_safe_units(
            available_margin=required_margin,
            margin_per_unit=margin_per_unit,
            safety_factor=safety_factor,
            min_units=min_units
        )
        
        assert not result.is_blocked, "Trade should not be blocked with sufficient margin"
        assert result.safe_units >= min_units, f"Safe units {result.safe_units} should be >= {min_units}"
        
        print(f"✅ Minimum position allowed: {result.safe_units} units")
        print(f"   Required margin: £{result.required_margin:.2f}")
        
        # Test case: Slightly less than required - should block
        result_insufficient = calculate_safe_units(
            available_margin=required_margin - 0.01,
            margin_per_unit=margin_per_unit,
            safety_factor=safety_factor,
            min_units=min_units
        )
        
        assert result_insufficient.is_blocked, "Trade should be blocked when just under minimum"
        print(f"✅ Blocked when insufficient: {result_insufficient.block_reason}")
    
    def test_safety_factor_application(self):
        """Test that safety factor is properly applied"""
        print("\n🧪 Testing safety factor application...")
        
        available_margin = 100.0
        margin_per_unit = 10.0
        safety_factor = 1.5  # 50% buffer
        
        result = calculate_safe_units(
            available_margin=available_margin,
            margin_per_unit=margin_per_unit,
            safety_factor=safety_factor
        )
        
        # Without safety factor: 100/10 = 10 units
        # With 1.5x safety factor: 100/(10*1.5) = 6.67 units
        expected_max = available_margin / (margin_per_unit * safety_factor)
        
        assert not result.is_blocked
        assert abs(result.safe_units - round(expected_max, 1)) < 0.1
        
        print(f"✅ Safety factor applied: {result.safe_units} units (expected ~{expected_max:.1f})")
        print(f"   Margin utilization: {result.calculation_details['margin_utilization']:.1f}%")
    
    def test_margin_validation_before_trade(self):
        """Test pre-trade margin validation"""
        print("\n🧪 Testing pre-trade validation...")
        
        # Valid trade
        is_valid, reason = validate_margin_before_trade(
            position_size=2.0,
            margin_per_unit=10.0,
            available_margin=100.0,
            safety_factor=1.2
        )
        
        assert is_valid, "Valid trade should pass validation"
        assert "Margin OK" in reason
        print(f"✅ Valid trade: {reason}")
        
        # Invalid trade
        is_valid, reason = validate_margin_before_trade(
            position_size=10.0,
            margin_per_unit=10.0,
            available_margin=50.0,
            safety_factor=1.2
        )
        
        assert not is_valid, "Invalid trade should fail validation"
        assert "Insufficient margin" in reason
        print(f"✅ Invalid trade blocked: {reason}")
    
    def test_risk_based_position_sizing(self):
        """Test position sizing based on risk amount"""
        print("\n🧪 Testing risk-based sizing...")
        
        risk_amount = 20.0  # £20 risk
        stop_distance = 50.0  # 50 points
        point_value = 1.0
        
        position_size = calculate_position_size_from_risk(
            risk_amount, stop_distance, point_value
        )
        
        expected_size = risk_amount / (stop_distance * point_value)  # 20/50 = 0.4
        
        assert abs(position_size - expected_size) < 0.1
        print(f"✅ Risk-based sizing: {position_size} units for £{risk_amount} risk over {stop_distance} points")
    
    def test_margin_safety_engine_integration(self):
        """Test the integrated margin safety engine"""
        print("\n🧪 Testing margin safety engine...")
        
        engine = MarginSafetyEngine(default_safety_factor=1.2)
        
        result = engine.calculate_optimal_position_size(
            risk_amount=30.0,      # £30 risk
            stop_distance_points=60.0,  # 60 points stop
            available_margin=200.0,     # £200 available
            margin_per_unit=15.0,       # £15 per unit
            point_value=1.0,
            min_units=0.1
        )
        
        # Risk-based size: 30/60 = 0.5 units
        # Margin-safe size: 200/(15*1.2) = 11.1 units
        # Should choose the smaller: 0.5 units
        
        assert not result.is_blocked
        assert result.safe_units <= 0.5  # Should be limited by risk, not margin
        
        print(f"✅ Optimal sizing: {result.safe_units} units")
        print(f"   Limited by: {'risk' if result.safe_units <= 0.5 else 'margin'}")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        print("\n🧪 Testing edge cases...")
        
        # Zero margin per unit
        result = calculate_safe_units(
            available_margin=100.0,
            margin_per_unit=0.0,
            safety_factor=1.2
        )
        
        assert result.is_blocked
        assert "Invalid margin per unit" in result.block_reason
        print(f"✅ Zero margin per unit blocked: {result.block_reason}")
        
        # Negative margin per unit
        result = calculate_safe_units(
            available_margin=100.0,
            margin_per_unit=-5.0,
            safety_factor=1.2
        )
        
        assert result.is_blocked
        assert "Invalid margin per unit" in result.block_reason
        print(f"✅ Negative margin per unit blocked: {result.block_reason}")
        
        # Zero available margin
        result = calculate_safe_units(
            available_margin=0.0,
            margin_per_unit=10.0,
            safety_factor=1.2,
            min_units=0.1
        )
        
        assert result.is_blocked
        assert "Insufficient margin" in result.block_reason
        print(f"✅ Zero available margin blocked: {result.block_reason}")
    
    def test_realistic_forex_scenario(self):
        """Test realistic forex trading scenario"""
        print("\n🧪 Testing realistic forex scenario...")
        
        # Realistic GBP/USD scenario
        # Account: £264.63, Margin: £3.33/unit, Min size: 0.5
        
        result = calculate_safe_units(
            available_margin=264.63,
            margin_per_unit=3.33,
            safety_factor=1.2,
            min_units=0.5
        )
        
        assert not result.is_blocked
        
        # Expected: 264.63 / (3.33 * 1.2) = ~66.2 units
        expected_units = 264.63 / (3.33 * 1.2)
        
        assert abs(result.safe_units - round(expected_units, 1)) < 1.0
        
        print(f"✅ Forex scenario: {result.safe_units} units from £{264.63:.2f}")
        print(f"   Margin utilization: {result.calculation_details['margin_utilization']:.1f}%")


def run_margin_safety_tests():
    """Run all margin safety tests"""
    print("="*80)
    print("🧪 MARGIN SAFETY FIXES - UNIT TESTS")
    print("="*80)
    
    test_suite = TestMarginSafety()
    
    try:
        test_suite.test_insufficient_margin_blocks_trade()
        test_suite.test_minimum_viable_position()
        test_suite.test_safety_factor_application()
        test_suite.test_margin_validation_before_trade()
        test_suite.test_risk_based_position_sizing()
        test_suite.test_margin_safety_engine_integration()
        test_suite.test_edge_cases()
        test_suite.test_realistic_forex_scenario()
        
        print("\n" + "="*80)
        print("✅ ALL MARGIN SAFETY TESTS PASSED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


def run_position_reconciliation_tests():
    """Run position reconciliation tests"""
    print("="*80)
    print("🧪 POSITION RECONCILIATION FIXES - UNIT TESTS")
    print("="*80)

    from core.risk_management.position_reconciler import (
        PositionReconciler, BrokerPosition, PositionState
    )
    from datetime import datetime

    reconciler = PositionReconciler()

    try:
        print("\n🧪 Testing position reconciliation...")

        # Test 1: Add pending position
        temp_id = reconciler.add_pending_position("REF123", "CS.D.GBPUSD.TODAY.IP", "BUY", 1.0)
        assert temp_id.startswith("PENDING_")
        print(f"✅ Added pending position: {temp_id}")

        # Test 2: Confirm position opened
        deal_id = "DEAL456"
        success = reconciler.confirm_position_opened("REF123", deal_id, 1.2500)
        assert success
        assert deal_id in reconciler.internal_positions
        assert reconciler.internal_positions[deal_id].state == PositionState.OPEN
        print(f"✅ Confirmed position opened: {deal_id}")

        # Test 3: Reconcile with broker positions
        broker_positions = [
            BrokerPosition("DEAL456", "CS.D.GBPUSD.TODAY.IP", "BUY", 1.0, 1.2500),
            BrokerPosition("DEAL789", "CS.D.EURUSD.TODAY.IP", "SELL", 0.5, 1.1000)  # Missing from internal
        ]

        result = reconciler.reconcile_positions(broker_positions)

        assert result.total_broker == 2
        assert len(result.missing_from_internal) == 1
        assert "DEAL789" in result.missing_from_internal
        assert not result.is_synchronized  # Should detect the missing position

        print(f"✅ Reconciliation detected missing position: {result.missing_from_internal}")

        # Test 4: After reconciliation, missing position should be added
        assert "DEAL789" in reconciler.internal_positions
        print(f"✅ Missing position added to internal tracking")

        # Test 5: Test position closing
        success = reconciler.mark_position_closing("DEAL456")
        assert success
        assert reconciler.internal_positions["DEAL456"].state == PositionState.CLOSING
        print(f"✅ Position marked as closing")

        success = reconciler.confirm_position_closed("DEAL456", 1.2550, 5.0)
        assert success
        assert reconciler.internal_positions["DEAL456"].state == PositionState.CLOSED
        assert reconciler.internal_positions["DEAL456"].pnl == 5.0
        print(f"✅ Position confirmed closed with P&L: £5.00")

        print("\n" + "="*80)
        print("✅ ALL POSITION RECONCILIATION TESTS PASSED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ RECONCILIATION TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    run_margin_safety_tests()
    run_position_reconciliation_tests()
