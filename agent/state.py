"""
Agent State Management

Tracks portfolio, positions, trade history, and agent memory.
All state is persisted to allow recovery and analysis.
"""

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Position(BaseModel):
    """A trading position"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    token_symbol: str
    token_contract: str
    chain: str = "sol"

    # Entry info
    entry_price: Decimal
    entry_amount: Decimal  # Token amount
    entry_value_usd: Decimal  # USD value at entry
    entry_tx_id: Optional[str] = None
    entry_time: datetime = Field(default_factory=datetime.utcnow)

    # Exit info (if closed)
    exit_price: Optional[Decimal] = None
    exit_amount: Optional[Decimal] = None
    exit_value_usd: Optional[Decimal] = None
    exit_tx_id: Optional[str] = None
    exit_time: Optional[datetime] = None

    status: PositionStatus = PositionStatus.OPEN

    # Risk management
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None

    @property
    def is_open(self) -> bool:
        return self.status == PositionStatus.OPEN

    @property
    def pnl_usd(self) -> Optional[Decimal]:
        if self.exit_value_usd and self.entry_value_usd:
            return self.exit_value_usd - self.entry_value_usd
        return None

    @property
    def pnl_pct(self) -> Optional[Decimal]:
        if self.exit_value_usd and self.entry_value_usd and self.entry_value_usd > 0:
            return ((self.exit_value_usd - self.entry_value_usd) / self.entry_value_usd) * 100
        return None

    @property
    def hold_duration_hours(self) -> float:
        end_time = self.exit_time or datetime.utcnow()
        return (end_time - self.entry_time).total_seconds() / 3600


class Trade(BaseModel):
    """A trade record"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    action: TradeAction
    token_symbol: str
    token_contract: str
    chain: str = "sol"

    amount: Decimal
    price: Decimal
    value_usd: Decimal

    tx_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Related position
    position_id: Optional[str] = None

    # Metadata
    strategy: Optional[str] = None
    notes: Optional[str] = None


class TokenBalance(BaseModel):
    """Token balance info"""

    symbol: str
    contract: str
    chain: str
    balance: Decimal
    balance_usd: Optional[Decimal] = None
    price: Optional[Decimal] = None


class AgentMemory(BaseModel):
    """Agent memory for learning from past trades"""

    successful_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    failed_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    token_blacklist: List[str] = Field(default_factory=list)  # Contracts to avoid
    token_whitelist: List[str] = Field(default_factory=list)  # Trusted tokens
    insights: List[str] = Field(default_factory=list)  # Learned insights


class AgentState(BaseModel):
    """Complete agent state"""

    # Identity
    agent_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Portfolio
    wallet_address: Optional[str] = None
    native_balance: Decimal = Decimal("0")  # SOL balance
    token_balances: List[TokenBalance] = Field(default_factory=list)

    # Positions
    positions: List[Position] = Field(default_factory=list)

    # Trade history
    trades: List[Trade] = Field(default_factory=list)

    # Daily limits
    daily_trade_count: int = 0
    daily_trade_date: Optional[str] = None  # YYYY-MM-DD

    # Memory
    memory: AgentMemory = Field(default_factory=AgentMemory)

    # Stats
    total_pnl_usd: Decimal = Decimal("0")
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0

    @property
    def open_positions(self) -> List[Position]:
        return [p for p in self.positions if p.is_open]

    @property
    def total_value_usd(self) -> Decimal:
        native_usd = self.native_balance * Decimal("150")  # Rough SOL price
        tokens_usd = sum(b.balance_usd or Decimal("0") for b in self.token_balances)
        positions_usd = sum(p.entry_value_usd for p in self.open_positions)
        return native_usd + tokens_usd + positions_usd

    @property
    def win_rate(self) -> float:
        total = self.win_count + self.loss_count
        return self.win_count / total if total > 0 else 0.0

    def get_position_by_token(self, contract: str) -> Optional[Position]:
        for p in self.open_positions:
            if p.token_contract == contract:
                return p
        return None

    def can_trade_today(self, max_daily: int) -> bool:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.daily_trade_date != today:
            self.daily_trade_count = 0
            self.daily_trade_date = today
        return self.daily_trade_count < max_daily

    def record_trade(self, trade: Trade) -> None:
        self.trades.append(trade)
        self.total_trades += 1
        self.daily_trade_count += 1
        self.updated_at = datetime.utcnow()

    def close_position(
        self, position_id: str, exit_price: Decimal, exit_value_usd: Decimal, exit_tx_id: str
    ) -> Position:
        for p in self.positions:
            if p.id == position_id:
                p.status = PositionStatus.CLOSED
                p.exit_price = exit_price
                p.exit_value_usd = exit_value_usd
                p.exit_tx_id = exit_tx_id
                p.exit_time = datetime.utcnow()

                # Update stats
                pnl = p.pnl_usd
                if pnl:
                    self.total_pnl_usd += pnl
                    if pnl > 0:
                        self.win_count += 1
                    else:
                        self.loss_count += 1

                self.updated_at = datetime.utcnow()
                return p
        raise ValueError(f"Position {position_id} not found")

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "AgentState":
        with open(path, "r") as f:
            return cls.model_validate_json(f.read())


# State file location - use .agent directory for better organization
STATE_FILE = Path(".agent/state.json")


def get_state() -> AgentState:
    """Load or create agent state"""
    if STATE_FILE.exists():
        return AgentState.load(STATE_FILE)
    return AgentState()


def save_state(state: AgentState) -> None:
    """Save agent state"""
    state.save(STATE_FILE)
