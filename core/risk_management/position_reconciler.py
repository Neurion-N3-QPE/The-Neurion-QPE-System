"""
Position Reconciliation System

Reconciles internal position state with broker positions using dealId-based state machine.
Fixes the issue where internal state shows 0 positions but broker shows 2 positions.
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PositionState(Enum):
    """Position state enumeration"""
    PENDING = "PENDING"      # Order submitted, awaiting confirmation
    OPEN = "OPEN"           # Position confirmed open
    CLOSING = "CLOSING"     # Close order submitted
    CLOSED = "CLOSED"       # Position confirmed closed
    REJECTED = "REJECTED"   # Order rejected
    UNKNOWN = "UNKNOWN"     # State unclear, needs investigation


@dataclass
class PositionRecord:
    """Internal position record with state tracking"""
    deal_id: str
    epic: str
    direction: str  # 'BUY' or 'SELL'
    size: float
    entry_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    state: PositionState = PositionState.PENDING
    deal_reference: Optional[str] = None  # Original deal reference
    last_updated: datetime = field(default_factory=datetime.now)
    broker_confirmed: bool = False
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    pnl: Optional[float] = None
    
    def update_state(self, new_state: PositionState, reason: str = ""):
        """Update position state with logging"""
        old_state = self.state
        self.state = new_state
        self.last_updated = datetime.now()
        
        logger.info(f"🔄 Position {self.deal_id}: {old_state.value} → {new_state.value}")
        if reason:
            logger.info(f"   Reason: {reason}")


@dataclass
class BrokerPosition:
    """Position data from broker"""
    deal_id: str
    epic: str
    direction: str
    size: float
    level: float  # Entry price
    current_price: Optional[float] = None
    pnl: Optional[float] = None


@dataclass
class ReconciliationResult:
    """Result of position reconciliation"""
    total_internal: int
    total_broker: int
    matched_positions: int
    missing_from_internal: List[str]  # Deal IDs in broker but not internal
    missing_from_broker: List[str]    # Deal IDs in internal but not broker
    state_mismatches: List[Tuple[str, PositionState, str]]  # Deal ID, internal state, broker state
    actions_taken: List[str]
    is_synchronized: bool


class PositionReconciler:
    """
    Position reconciliation system with dealId-based state machine.
    
    Maintains strict synchronization between internal position tracking
    and broker position state.
    """
    
    def __init__(self):
        self.internal_positions: Dict[str, PositionRecord] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.reconciliation_history: List[ReconciliationResult] = []
    
    def add_pending_position(
        self, 
        deal_reference: str, 
        epic: str, 
        direction: str, 
        size: float
    ) -> str:
        """
        Add a pending position (order submitted but not confirmed).
        
        Returns a temporary internal ID until deal_id is confirmed.
        """
        temp_id = f"PENDING_{deal_reference}"
        
        position = PositionRecord(
            deal_id=temp_id,
            epic=epic,
            direction=direction,
            size=size,
            state=PositionState.PENDING,
            deal_reference=deal_reference
        )
        
        self.internal_positions[temp_id] = position
        
        self.logger.info(f"➕ Added pending position: {temp_id} ({epic} {direction} {size})")
        return temp_id
    
    def confirm_position_opened(
        self, 
        deal_reference: str, 
        deal_id: str, 
        entry_price: float,
        entry_time: Optional[datetime] = None
    ) -> bool:
        """
        Confirm that a pending position has been opened with actual deal_id.
        """
        # Find pending position by deal reference
        pending_id = f"PENDING_{deal_reference}"
        
        if pending_id not in self.internal_positions:
            self.logger.error(f"❌ Cannot confirm position: no pending position for {deal_reference}")
            return False
        
        # Move from pending to confirmed
        pending_position = self.internal_positions.pop(pending_id)
        
        # Create confirmed position record
        confirmed_position = PositionRecord(
            deal_id=deal_id,
            epic=pending_position.epic,
            direction=pending_position.direction,
            size=pending_position.size,
            entry_price=entry_price,
            entry_time=entry_time or datetime.now(),
            state=PositionState.OPEN,
            deal_reference=deal_reference,
            broker_confirmed=True
        )
        
        self.internal_positions[deal_id] = confirmed_position
        
        self.logger.info(f"✅ Position confirmed: {pending_id} → {deal_id} @ {entry_price}")
        return True
    
    def mark_position_closing(self, deal_id: str) -> bool:
        """Mark position as closing (close order submitted)"""
        if deal_id not in self.internal_positions:
            self.logger.error(f"❌ Cannot mark closing: position {deal_id} not found")
            return False
        
        position = self.internal_positions[deal_id]
        position.update_state(PositionState.CLOSING, "Close order submitted")
        return True
    
    def confirm_position_closed(
        self, 
        deal_id: str, 
        close_price: float, 
        pnl: float,
        close_time: Optional[datetime] = None
    ) -> bool:
        """Confirm position has been closed"""
        if deal_id not in self.internal_positions:
            self.logger.error(f"❌ Cannot confirm close: position {deal_id} not found")
            return False
        
        position = self.internal_positions[deal_id]
        position.close_price = close_price
        position.close_time = close_time or datetime.now()
        position.pnl = pnl
        position.update_state(PositionState.CLOSED, f"Closed @ {close_price}, P&L: £{pnl:.2f}")
        
        return True
    
    def reconcile_positions(self, broker_positions: List[BrokerPosition]) -> ReconciliationResult:
        """
        Reconcile internal position state with broker positions.
        
        Key reconciliation logic:
        1. Match positions by dealId
        2. Identify missing positions in either system
        3. Detect state mismatches
        4. Take corrective actions
        """
        self.logger.info(f"🔄 Starting position reconciliation...")
        self.logger.info(f"   Internal positions: {len(self.internal_positions)}")
        self.logger.info(f"   Broker positions: {len(broker_positions)}")
        
        # Build broker position lookup
        broker_positions_dict = {pos.deal_id: pos for pos in broker_positions}
        broker_deal_ids = set(broker_positions_dict.keys())
        
        # Get internal position deal IDs (exclude pending positions)
        internal_deal_ids = {
            deal_id for deal_id, pos in self.internal_positions.items() 
            if not deal_id.startswith("PENDING_") and pos.state in [PositionState.OPEN, PositionState.CLOSING]
        }
        
        # Find discrepancies
        missing_from_internal = list(broker_deal_ids - internal_deal_ids)
        missing_from_broker = list(internal_deal_ids - broker_deal_ids)
        matched_positions = list(broker_deal_ids & internal_deal_ids)
        
        actions_taken = []
        state_mismatches = []
        
        # Handle positions missing from internal tracking
        for deal_id in missing_from_internal:
            broker_pos = broker_positions_dict[deal_id]
            
            # Add missing position to internal tracking
            missing_position = PositionRecord(
                deal_id=deal_id,
                epic=broker_pos.epic,
                direction=broker_pos.direction,
                size=broker_pos.size,
                entry_price=broker_pos.level,
                entry_time=datetime.now(),  # Approximate
                state=PositionState.OPEN,
                broker_confirmed=True
            )
            
            self.internal_positions[deal_id] = missing_position
            actions_taken.append(f"Added missing position {deal_id} from broker")
            
            self.logger.warning(f"⚠️  Added missing position: {deal_id} ({broker_pos.epic})")
        
        # Handle positions missing from broker
        for deal_id in missing_from_broker:
            internal_pos = self.internal_positions[deal_id]
            
            if internal_pos.state == PositionState.OPEN:
                # Position should be open but not found on broker - mark as closed
                internal_pos.update_state(
                    PositionState.CLOSED, 
                    "Position not found on broker, assuming closed"
                )
                actions_taken.append(f"Marked {deal_id} as closed (not found on broker)")
                
                self.logger.warning(f"⚠️  Position {deal_id} not found on broker, marked as closed")
        
        # Check state consistency for matched positions
        for deal_id in matched_positions:
            internal_pos = self.internal_positions[deal_id]
            broker_pos = broker_positions_dict[deal_id]
            
            # Update current price and P&L from broker
            if broker_pos.current_price:
                # Calculate unrealized P&L if we have entry price
                if internal_pos.entry_price:
                    if internal_pos.direction == 'BUY':
                        unrealized_pnl = (broker_pos.current_price - internal_pos.entry_price) * internal_pos.size
                    else:  # SELL
                        unrealized_pnl = (internal_pos.entry_price - broker_pos.current_price) * internal_pos.size
                    
                    # Update internal position with current data
                    internal_pos.pnl = unrealized_pnl
            
            # Verify position details match
            if (internal_pos.size != broker_pos.size or 
                internal_pos.direction != broker_pos.direction or
                internal_pos.epic != broker_pos.epic):
                
                state_mismatches.append((
                    deal_id, 
                    internal_pos.state, 
                    f"Size/Direction/Epic mismatch"
                ))
                
                self.logger.warning(f"⚠️  Position details mismatch for {deal_id}")
        
        # Create reconciliation result
        result = ReconciliationResult(
            total_internal=len([p for p in self.internal_positions.values() 
                              if not p.deal_id.startswith("PENDING_") and p.state != PositionState.CLOSED]),
            total_broker=len(broker_positions),
            matched_positions=len(matched_positions),
            missing_from_internal=missing_from_internal,
            missing_from_broker=missing_from_broker,
            state_mismatches=state_mismatches,
            actions_taken=actions_taken,
            is_synchronized=len(missing_from_internal) == 0 and len(missing_from_broker) == 0 and len(state_mismatches) == 0
        )
        
        # Store reconciliation history
        self.reconciliation_history.append(result)
        
        # Log reconciliation summary
        if result.is_synchronized:
            self.logger.info("✅ Positions synchronized successfully")
        else:
            self.logger.warning(f"⚠️  Reconciliation issues found:")
            self.logger.warning(f"   Missing from internal: {len(missing_from_internal)}")
            self.logger.warning(f"   Missing from broker: {len(missing_from_broker)}")
            self.logger.warning(f"   State mismatches: {len(state_mismatches)}")
        
        return result
    
    def get_open_positions(self) -> Dict[str, PositionRecord]:
        """Get all open positions"""
        return {
            deal_id: pos for deal_id, pos in self.internal_positions.items()
            if pos.state == PositionState.OPEN
        }
    
    def get_position_summary(self) -> Dict:
        """Get summary of position states"""
        summary = {}
        for state in PositionState:
            count = len([p for p in self.internal_positions.values() if p.state == state])
            summary[state.value] = count
        
        return summary
