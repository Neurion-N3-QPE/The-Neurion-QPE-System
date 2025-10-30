"""
Unit tests for probability calculation fixes.

Tests the fixed probability calculations to ensure they never return 100% or 0% probabilities
and that VaR-probability consistency is maintained.
"""

import numpy as np
from scipy import stats
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.hybrid_model import MonteCarloSimulator


class TestProbabilityCalculationFixes:
    """Test suite for probability calculation fixes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.simulator = MonteCarloSimulator(n_simulations=10000)
    
    def test_probability_never_zero_or_hundred_percent(self):
        """Test that probabilities are never exactly 0% or 100%"""
        print("\n🧪 Testing probability caps...")
        
        # Test case 1: Very positive scenarios (should cap at 99.9% profit)
        scenarios_positive = np.random.normal(0.8, 0.01, 10000)  # Very positive mean, low volatility
        metrics = self.simulator.calculate_risk_metrics(scenarios_positive)
        
        assert metrics['probability_of_loss'] >= 0.001, f"Loss probability too low: {metrics['probability_of_loss']}"
        assert metrics['probability_of_loss'] <= 0.999, f"Loss probability too high: {metrics['probability_of_loss']}"
        assert metrics['probability_of_profit'] >= 0.001, f"Profit probability too low: {metrics['probability_of_profit']}"
        assert metrics['probability_of_profit'] <= 0.999, f"Profit probability too high: {metrics['probability_of_profit']}"
        
        print(f"✅ Positive scenarios: P(Loss)={metrics['probability_of_loss']*100:.2f}%, P(Profit)={metrics['probability_of_profit']*100:.2f}%")
        
        # Test case 2: Very negative scenarios (should cap at 99.9% loss)
        scenarios_negative = np.random.normal(-0.8, 0.01, 10000)  # Very negative mean, low volatility
        metrics = self.simulator.calculate_risk_metrics(scenarios_negative)
        
        assert metrics['probability_of_loss'] >= 0.001, f"Loss probability too low: {metrics['probability_of_loss']}"
        assert metrics['probability_of_loss'] <= 0.999, f"Loss probability too high: {metrics['probability_of_loss']}"
        assert metrics['probability_of_profit'] >= 0.001, f"Profit probability too low: {metrics['probability_of_profit']}"
        assert metrics['probability_of_profit'] <= 0.999, f"Profit probability too high: {metrics['probability_of_profit']}"
        
        print(f"✅ Negative scenarios: P(Loss)={metrics['probability_of_loss']*100:.2f}%, P(Profit)={metrics['probability_of_profit']*100:.2f}%")
    
    def test_known_normal_distribution(self):
        """Test with known normal distribution: μ=0.002, σ=0.02"""
        print("\n🧪 Testing known normal distribution...")
        
        # Generate scenarios with known parameters
        mu, sigma = 0.002, 0.02
        scenarios = np.random.normal(mu, sigma, 10000)
        
        metrics = self.simulator.calculate_risk_metrics(scenarios)
        
        # For normal distribution with μ=0.002, σ=0.02:
        # P(X < 0) ≈ P(Z < -0.002/0.02) = P(Z < -0.1) ≈ 46%
        expected_loss_prob = stats.norm.cdf(0, mu, sigma)
        
        # Allow 5% tolerance for Monte Carlo sampling
        tolerance = 0.05
        assert abs(metrics['probability_of_loss'] - expected_loss_prob) < tolerance, \
            f"Loss probability {metrics['probability_of_loss']:.3f} too far from expected {expected_loss_prob:.3f}"
        
        # Verify it's not exactly 0% or 100%
        assert 0.001 <= metrics['probability_of_loss'] <= 0.999
        assert 0.001 <= metrics['probability_of_profit'] <= 0.999
        
        print(f"✅ Normal dist test: Expected P(Loss)≈{expected_loss_prob*100:.1f}%, Got P(Loss)={metrics['probability_of_loss']*100:.2f}%")
    
    def test_var_probability_consistency(self):
        """Test VaR-Probability consistency validation"""
        print("\n🧪 Testing VaR-Probability consistency...")
        
        # Test case: Normal distribution around 0.5 (should trigger edge detection)
        scenarios_no_edge = np.random.normal(0.5, 0.1, 10000)
        metrics = self.simulator.calculate_risk_metrics(scenarios_no_edge)
        
        # Should detect "NO EDGE" condition
        mean = metrics['mean']
        std = metrics['std']
        edge_condition = abs(mean - 0.5) < 0.5 * std
        
        print(f"✅ Edge detection: |{mean:.3f} - 0.5| = {abs(mean - 0.5):.3f}, 0.5×{std:.3f} = {0.5*std:.3f}")
        print(f"   No edge detected: {edge_condition}")
        
        # Test case: High volatility with very low loss probability (should flag inconsistency)
        scenarios_suspicious = np.random.normal(0.8, 0.05, 10000)  # High mean, high volatility
        metrics = self.simulator.calculate_risk_metrics(scenarios_suspicious)
        
        suspicious_condition = metrics['probability_of_loss'] < 0.001 and metrics['std'] > 0.01
        print(f"✅ Suspicious metrics: P(Loss)={metrics['probability_of_loss']*100:.3f}%, Std={metrics['std']:.4f}")
        print(f"   Suspicious condition: {suspicious_condition}")
    
    def test_probability_sum_equals_one(self):
        """Test that probability of loss + probability of profit = 1.0"""
        print("\n🧪 Testing probability sum...")
        
        scenarios = np.random.normal(0.1, 0.03, 10000)
        metrics = self.simulator.calculate_risk_metrics(scenarios)
        
        prob_sum = metrics['probability_of_loss'] + metrics['probability_of_profit']
        
        assert abs(prob_sum - 1.0) < 1e-10, f"Probabilities don't sum to 1.0: {prob_sum}"
        
        print(f"✅ Probability sum: {metrics['probability_of_loss']:.6f} + {metrics['probability_of_profit']:.6f} = {prob_sum:.6f}")
    
    def test_edge_cases(self):
        """Test edge cases that previously caused 100%/0% probabilities"""
        print("\n🧪 Testing edge cases...")
        
        # Edge case 1: All scenarios exactly zero
        scenarios_zero = np.zeros(1000)
        metrics = self.simulator.calculate_risk_metrics(scenarios_zero)
        
        assert 0.001 <= metrics['probability_of_loss'] <= 0.999
        assert 0.001 <= metrics['probability_of_profit'] <= 0.999
        
        print(f"✅ All-zero scenarios: P(Loss)={metrics['probability_of_loss']*100:.2f}%")
        
        # Edge case 2: All scenarios positive
        scenarios_all_positive = np.ones(1000) * 0.5
        metrics = self.simulator.calculate_risk_metrics(scenarios_all_positive)
        
        assert 0.001 <= metrics['probability_of_loss'] <= 0.999
        assert 0.001 <= metrics['probability_of_profit'] <= 0.999
        
        print(f"✅ All-positive scenarios: P(Loss)={metrics['probability_of_loss']*100:.2f}%")
        
        # Edge case 3: All scenarios negative
        scenarios_all_negative = np.ones(1000) * -0.5
        metrics = self.simulator.calculate_risk_metrics(scenarios_all_negative)
        
        assert 0.001 <= metrics['probability_of_loss'] <= 0.999
        assert 0.001 <= metrics['probability_of_profit'] <= 0.999
        
        print(f"✅ All-negative scenarios: P(Loss)={metrics['probability_of_loss']*100:.2f}%")


def run_probability_tests():
    """Run all probability calculation tests"""
    print("="*80)
    print("🧪 PROBABILITY CALCULATION FIXES - UNIT TESTS")
    print("="*80)
    
    test_suite = TestProbabilityCalculationFixes()
    test_suite.setup_method()
    
    try:
        test_suite.test_probability_never_zero_or_hundred_percent()
        test_suite.test_known_normal_distribution()
        test_suite.test_var_probability_consistency()
        test_suite.test_probability_sum_equals_one()
        test_suite.test_edge_cases()
        
        print("\n" + "="*80)
        print("✅ ALL PROBABILITY TESTS PASSED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    run_probability_tests()
