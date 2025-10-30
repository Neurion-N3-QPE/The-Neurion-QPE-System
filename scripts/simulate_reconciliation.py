import sys
import os
import logging
from datetime import datetime
from core.risk_management.position_reconciler import PositionReconciler, PositionRecord, PositionState
from core.models.data_structures import BrokerPosition

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize PositionReconciler
reconciler = PositionReconciler()

# Mock internal positions
reconciler.internal_positions = {
    "DEAL1": PositionRecord(
        deal_id="DEAL1",
        epic="EPIC1",
        direction="BUY",
        size=1.0,
        entry_price=100.0,
        entry_time=datetime.now(),
        state=PositionState.OPEN,
        broker_confirmed=True
    ),
    "DEAL2": PositionRecord(
        deal_id="DEAL2",
        epic="EPIC2",
        direction="SELL",
        size=2.0,
        entry_price=200.0,
        entry_time=datetime.now(),
        state=PositionState.OPEN,
        broker_confirmed=True
    )
}

# Mock broker positions
broker_positions = [
    BrokerPosition(
        deal_id="DEAL1",
        epic="EPIC1",
        direction="BUY",
        size=1.0,
        level=100.0,
        current_price=105.0
    ),
    BrokerPosition(
        deal_id="DEAL3",
        epic="EPIC3",
        direction="BUY",
        size=1.5,
        level=150.0,
        current_price=155.0
    )
]

# Perform reconciliation
result = reconciler.reconcile_positions(broker_positions)

# Print reconciliation result
print("\nReconciliation Result:")
print(f"Total Internal Positions: {result.total_internal}")
print(f"Total Broker Positions: {result.total_broker}")
print(f"Matched Positions: {result.matched_positions}")
print(f"Missing from Internal: {result.missing_from_internal}")
print(f"Missing from Broker: {result.missing_from_broker}")
print(f"State Mismatches: {result.state_mismatches}")
print(f"Actions Taken: {result.actions_taken}")
print(f"Is Synchronized: {result.is_synchronized}")