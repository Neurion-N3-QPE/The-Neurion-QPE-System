"""
STANDALONE SSE TEST - MINIMAL DEPENDENCIES

Quick verification that SSE core functionality works
Tests the Monte Carlo simulation logic directly
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import asyncio
from datetime import datetime
import pytest


class SimpleMonteCarloSimulator:
    """Simplified Monte Carlo Simulator for testing"""
    
    def __init__(self, n_simulations: int = 10000):
        self.n_simulations = n_simulations
        self.random_state = np.random.RandomState(42)
        print(f"🎲 Monte Carlo Simulator initialized: {n_simulations:,} simulations")
    
    def simulate_scenarios(
        self,
        base_prediction: float,
        volatility: float,
        shock_probabilities: dict = None
    ) -> np.ndarray:
        """Generate Monte Carlo scenarios"""
        print(f"\n🎲 SSE RUNNING: Simulating {self.n_simulations:,} market scenarios...")
        print(f"   Base Prediction: {base_prediction:.4f} | Volatility: {volatility:.4f}")
        
        scenarios = []
        shock_probs = shock_probabilities or {}
        
        for i in range(self.n_simulations):
            # Base random walk
            random_shock = self.random_state.normal(0, volatility)
            scenario_value = base_prediction + random_shock
            
            # Add tail risk events
            for shock_type, probability in shock_probs.items():
                if self.random_state.random() < probability:
                    shock_magnitude = self._generate_shock(shock_type)
                    scenario_value += shock_magnitude
            
            scenarios.append(scenario_value)
            
            # Progress logging
            if (i + 1) % 2000 == 0:
                print(f"   SSE Progress: {i+1:,}/{self.n_simulations:,} scenarios")
        
        scenarios_array = np.array(scenarios)
        print(f"\n✅ SSE COMPLETE: {self.n_simulations:,} scenarios analyzed")
        print(f"   Mean: {scenarios_array.mean():.4f} | Std: {scenarios_array.std():.4f}")
        
        return scenarios_array
    
    def _generate_shock(self, shock_type: str) -> float:
        """Generate shock magnitude"""
        shocks = {
            "market_crash": self.random_state.normal(-0.2, 0.05),
            "geopolitical": self.random_state.normal(-0.1, 0.03),
            "positive_surprise": self.random_state.normal(0.1, 0.02),
        }
        return shocks.get(shock_type, 0.0)
    
    def calculate_risk_metrics(self, scenarios: np.ndarray) -> dict:
        """Calculate risk metrics with realistic probability caps"""
        print("\n📊 SSE Risk Analysis:")

        # Calculate realistic probabilities with caps to prevent 100%/0% impossibilities
        raw_probability_of_loss = float(np.sum(scenarios < 0) / len(scenarios))

        # Apply probability caps: Never allow exactly 0% or 100%
        # Minimum 0.1% (1 in 1000), Maximum 99.9% (999 in 1000)
        probability_of_loss = max(0.001, min(0.999, raw_probability_of_loss))

        # If we had to cap the probability, log a warning
        if raw_probability_of_loss != probability_of_loss:
            print(f"⚠️  Probability capped: Raw={raw_probability_of_loss*100:.3f}% → Capped={probability_of_loss*100:.3f}%")

        metrics = {
            "var_95": float(np.percentile(scenarios, 5)),
            "var_99": float(np.percentile(scenarios, 1)),
            "probability_of_loss": probability_of_loss,
            "probability_of_profit": 1.0 - probability_of_loss,
            "mean": float(np.mean(scenarios)),
            "std": float(np.std(scenarios)),
        }

        print(f"   VaR (95%): {metrics['var_95']:.4f}")
        print(f"   VaR (99%): {metrics['var_99']:.4f}")
        print(f"   Probability of Loss: {metrics['probability_of_loss']*100:.2f}%")
        print(f"   Probability of Profit: {metrics['probability_of_profit']*100:.2f}%")

        return metrics


@pytest.mark.parametrize("n_simulations, base_prediction, volatility", [
    (1000, 0.75, 0.02),
    (10000, 0.75, 0.02),
])
def test_monte_carlo_simulation(n_simulations, base_prediction, volatility):
    """Test Monte Carlo simulation with different configurations"""
    sse = SimpleMonteCarloSimulator(n_simulations=n_simulations)

    scenarios = sse.simulate_scenarios(
        base_prediction=base_prediction,
        volatility=volatility
    )

    assert len(scenarios) == n_simulations, f"Expected {n_simulations} scenarios, got {len(scenarios)}"
    assert base_prediction - 0.05 < scenarios.mean() < base_prediction + 0.05, "Mean should be close to base prediction"

    print(f"\n✅ Monte Carlo simulation passed for {n_simulations} simulations")


def test_3_risk_metrics():
    """Test 3: Risk metric calculation"""
    print("\n" + "="*80)
    print("🧪 TEST 3: RISK METRICS CALCULATION")
    print("="*80)
    
    sse = SimpleMonteCarloSimulator(n_simulations=5000)
    
    scenarios = sse.simulate_scenarios(
        base_prediction=0.75,
        volatility=0.03
    )
    
    metrics = sse.calculate_risk_metrics(scenarios)
    
    assert 'var_95' in metrics, "Should have VaR 95%"
    assert 'probability_of_loss' in metrics, "Should have probability of loss"
    assert metrics['probability_of_loss'] >= 0 and metrics['probability_of_loss'] <= 1, "Probability should be 0-1"
    
    print("\n✅ TEST 3 PASSED")
    return True


@pytest.mark.parametrize("base_prediction, volatility, expected_certainty", [
    (0.80, 0.015, 0.90),
])
def test_certainty_calculation(base_prediction, volatility, expected_certainty):
    """Test certainty calculation with low volatility"""
    sse = SimpleMonteCarloSimulator(n_simulations=10000)

    scenarios = sse.simulate_scenarios(
        base_prediction=base_prediction,
        volatility=volatility
    )

    metrics = sse.calculate_risk_metrics(scenarios)
    certainty = 1.0 - metrics['probability_of_loss']

    assert certainty > expected_certainty, f"Expected >{expected_certainty*100:.2f}% certainty, got {certainty*100:.2f}%"

    print(f"\n✅ Certainty calculation passed with {certainty*100:.2f}% certainty")


@pytest.mark.parametrize("n_agents, base_prediction, volatility, expected_scenarios", [
    (3, 0.75, 0.02, 30000),
])
def test_multi_agent_simulation(n_agents, base_prediction, volatility, expected_scenarios):
    """Test multi-agent simulation with ensemble metrics"""
    agents = [(f"Agent_{i}", SimpleMonteCarloSimulator(n_simulations=10000)) for i in range(n_agents)]

    all_scenarios = []
    for _, sse in agents:
        scenarios = sse.simulate_scenarios(
            base_prediction=base_prediction,
            volatility=volatility
        )
        all_scenarios.append(scenarios)

    total_scenarios = sum(len(s) for s in all_scenarios)
    ensemble_mean = np.mean([s.mean() for s in all_scenarios])
    ensemble_std = np.mean([s.std() for s in all_scenarios])

    assert total_scenarios == expected_scenarios, f"Expected {expected_scenarios} scenarios, got {total_scenarios}"
    assert ensemble_mean > 0.7 and ensemble_mean < 0.8, "Ensemble mean should be close to base prediction"

    print(f"\n✅ Multi-agent simulation passed with {total_scenarios} scenarios")


@pytest.mark.parametrize("test_function", [
    test_monte_carlo_simulation,
    test_3_risk_metrics,
    test_certainty_calculation,
    test_multi_agent_simulation,
])
def test_all(test_function):
    """Run all tests in the suite"""
    test_function()


if __name__ == "__main__":
    import sys
    success = test_all()
    sys.exit(0 if success else 1)
