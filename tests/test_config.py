"""
Test configuration and state management
"""

import pytest
from decimal import Decimal
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.config import Config, TradingConfig, LLMConfig
from agent.state import AgentState, Position, Trade, TradeAction, PositionStatus


class TestConfig:
    """Test configuration loading"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = Config()
        
        assert config.trading.default_slippage == 1.0
        assert config.trading.min_liquidity_usd == 10000
        assert config.trading.min_risk_score == 50
        assert config.trading.max_position_pct == 5.0
        assert config.trading.max_daily_trades == 5
        assert config.trading.max_holdings == 3
    
    def test_trading_config(self):
        """Test trading configuration"""
        tc = TradingConfig(
            default_slippage=2.0,
            min_risk_score=60,
        )
        
        assert tc.default_slippage == 2.0
        assert tc.min_risk_score == 60


class TestState:
    """Test state management"""
    
    def test_empty_state(self):
        """Test initial empty state"""
        state = AgentState()
        
        assert state.wallet_address is None
        assert state.native_balance == Decimal("0")
        assert len(state.positions) == 0
        assert len(state.trades) == 0
        assert state.total_pnl_usd == Decimal("0")
    
    def test_position_creation(self):
        """Test position creation and properties"""
        position = Position(
            token_symbol="TEST",
            token_contract="TestContract123",
            entry_price=Decimal("0.001"),
            entry_amount=Decimal("1000"),
            entry_value_usd=Decimal("1"),
        )
        
        assert position.is_open
        assert position.status == PositionStatus.OPEN
        assert position.pnl_usd is None
        assert position.hold_duration_hours > 0
    
    def test_position_close(self):
        """Test position closing and PnL calculation"""
        position = Position(
            token_symbol="TEST",
            token_contract="TestContract123",
            entry_price=Decimal("0.001"),
            entry_amount=Decimal("1000"),
            entry_value_usd=Decimal("100"),
        )
        
        # Close position with profit
        state = AgentState()
        state.positions.append(position)
        
        closed = state.close_position(
            position_id=position.id,
            exit_price=Decimal("0.002"),
            exit_value_usd=Decimal("150"),
            exit_tx_id="tx123",
        )
        
        assert closed.status == PositionStatus.CLOSED
        assert closed.pnl_usd == Decimal("50")
        assert closed.pnl_pct == Decimal("50")
        assert state.total_pnl_usd == Decimal("50")
        assert state.win_count == 1
    
    def test_trade_recording(self):
        """Test trade recording"""
        state = AgentState()
        
        trade = Trade(
            action=TradeAction.BUY,
            token_symbol="TEST",
            token_contract="TestContract123",
            amount=Decimal("100"),
            price=Decimal("0.01"),
            value_usd=Decimal("1"),
        )
        
        state.record_trade(trade)
        
        assert len(state.trades) == 1
        assert state.total_trades == 1
        assert state.daily_trade_count == 1
    
    def test_daily_trade_limit(self):
        """Test daily trade limit checking"""
        state = AgentState()
        
        # Should be able to trade
        assert state.can_trade_today(5)
        
        # Record 5 trades
        for _ in range(5):
            state.record_trade(Trade(
                action=TradeAction.BUY,
                token_symbol="TEST",
                token_contract="test",
                amount=Decimal("1"),
                price=Decimal("1"),
                value_usd=Decimal("1"),
            ))
        
        # Should not be able to trade more
        assert not state.can_trade_today(5)
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        state = AgentState()
        
        # No trades
        assert state.win_rate == 0.0
        
        # Add wins and losses
        state.win_count = 3
        state.loss_count = 2
        
        assert state.win_rate == 0.6  # 3/5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
