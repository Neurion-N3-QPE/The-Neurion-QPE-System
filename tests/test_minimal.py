import numpy as np
import pytest


class SimpleMonteCarloSimulator:
    def __init__(self, n_simulations: int = 10000):
        self.n_simulations = n_simulations
        self.random_state = np.random.RandomState(42)

    def simulate_scenarios(self, base_prediction: float, volatility: float):
        scenarios = [
            base_prediction + self.random_state.normal(0, volatility)
            for _ in range(self.n_simulations)
        ]
        return np.array(scenarios)


def test_basic_simulation():
    """Test basic Monte Carlo simulation"""
    sse = SimpleMonteCarloSimulator(n_simulations=1000)
    scenarios = sse.simulate_scenarios(base_prediction=0.75, volatility=0.02)

    assert len(scenarios) == 1000, "Expected 1000 scenarios"
    assert 0.7 < scenarios.mean() < 0.8, "Mean should be close to base prediction"


def test_minimal():
    """A minimal test to verify pytest functionality"""
    assert 1 + 1 == 2


@pytest.mark.parametrize("n_simulations, base_prediction, volatility", [
    (1000, 0.75, 0.02),
    (10000, 0.75, 0.02),
])
def test_simulation(n_simulations, base_prediction, volatility):
    """Test Monte Carlo simulation with different configurations"""
    sse = SimpleMonteCarloSimulator(n_simulations=n_simulations)
    scenarios = sse.simulate_scenarios(base_prediction=base_prediction, volatility=volatility)

    assert len(scenarios) == n_simulations, f"Expected {n_simulations} scenarios, got {len(scenarios)}"
    assert base_prediction - 0.05 < scenarios.mean() < base_prediction + 0.05, "Mean should be close to base prediction"