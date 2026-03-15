"""Tests for upgraded monitor exit strategy behavior."""

from decimal import Decimal

from agent.monitor import SimplePositionMonitor, build_monitor_strategy_summary
from agent.position_display import describe_exit_reason, describe_position_exit_strategy
from agent.state import Position


def build_position() -> Position:
    return Position(
        token_symbol="BONK",
        token_contract="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        entry_price=Decimal("1.00"),
        entry_amount=Decimal("100"),
        entry_value_usd=Decimal("100"),
        remaining_amount=Decimal("100"),
        stop_loss_price=Decimal("0.85"),
        take_profit_price=Decimal("1.30"),
        highest_price=Decimal("1.00"),
    )


class TestMonitorStrategy:
    """Test partial exit and dynamic stop behavior."""

    def test_take_profit_triggers_partial_exit_first(self):
        monitor = SimplePositionMonitor()
        position = build_position()

        action = monitor._determine_exit_action(position, current_price=1.31)

        assert action is not None
        assert action.action == "partial_take_profit"
        assert action.sell_amount == Decimal("50")

    def test_partial_exit_promotes_breakeven_and_trailing(self):
        monitor = SimplePositionMonitor()
        position = build_position()

        monitor._apply_partial_take_profit(position, current_price=1.31)

        assert position.partial_take_profit_taken is True
        assert position.remaining_amount == Decimal("50")
        assert position.stop_loss_price == Decimal("1.00")
        assert position.trailing_stop_price == Decimal("1.179")

    def test_trailing_stop_updates_from_new_high(self):
        monitor = SimplePositionMonitor()
        position = build_position()
        monitor._apply_partial_take_profit(position, current_price=1.31)

        monitor._update_dynamic_stops(position, current_price=1.50)

        assert position.highest_price == Decimal("1.50")
        assert position.trailing_stop_price == Decimal("1.35")

    def test_trailing_stop_exits_remaining_position(self):
        monitor = SimplePositionMonitor()
        position = build_position()
        monitor._apply_partial_take_profit(position, current_price=1.31)
        monitor._update_dynamic_stops(position, current_price=1.50)

        action = monitor._determine_exit_action(position, current_price=1.34)

        assert action is not None
        assert action.action == "trailing_stop"
        assert action.sell_amount == Decimal("50")

    def test_exit_pending_blocks_new_exit_action(self):
        monitor = SimplePositionMonitor()
        position = build_position()
        position.exit_pending = True

        action = monitor._determine_exit_action(position, current_price=1.31)

        assert action is None

    def test_reconciliation_prefers_actual_order_details(self):
        monitor = SimplePositionMonitor()

        reconciled = monitor._reconcile_execution_result(
            fallback_out_amount="0.20",
            fallback_tx_id="fallback-tx",
            order_details={
                "data": {
                    "toAmount": "0.25",
                    "details": {
                        "status": "success",
                        "fromTxId": "actual-tx",
                    },
                }
            },
        )

        assert reconciled["out_amount"] == Decimal("0.25")
        assert reconciled["tx_id"] == "actual-tx"

    def test_recover_pending_position_from_successful_order_details(self):
        monitor = SimplePositionMonitor()
        position = build_position()
        position.exit_pending = True
        position.monitor_state = "exit_pending"
        position.pending_order_id = "order-123"
        position.pending_exit_action = "stop_loss"
        position.pending_sell_amount = Decimal("100")

        recovered = monitor._recover_position_from_order_details(
            position,
            {
                "data": {
                    "toAmount": "0.21",
                    "details": {
                        "status": "success",
                        "fromTxId": "tx-123",
                    },
                }
            },
        )

        assert recovered is True
        assert position.exit_pending is False
        assert position.monitor_state == "closed"


class TestMonitorStrategyText:
    def test_strategy_summary_matches_dynamic_exit_logic(self):
        summary = build_monitor_strategy_summary()

        assert "Initial stop loss: -15.0%" in summary
        assert "Partial take profit: +15.0% (sell 50%)" in summary
        assert "Breakeven promotion: enabled after partial TP" in summary
        assert "Trailing stop: 10.0% on remainder" in summary
        assert "Max hold: 24h" in summary

    def test_position_strategy_description_shows_partial_take_profit_before_trigger(self):
        position = build_position()

        description = describe_position_exit_strategy(position)

        assert "initial SL $0.850000" in description
        assert "partial TP $1.300000 (50%)" in description

    def test_position_strategy_description_shows_breakeven_and_trailing_after_trigger(self):
        position = build_position()
        position.partial_take_profit_taken = True
        position.trailing_stop_price = Decimal("1.35")

        description = describe_position_exit_strategy(position)

        assert "breakeven armed" in description
        assert "trailing $1.350000" in description

    def test_exit_reason_description_maps_internal_code(self):
        assert describe_exit_reason("trailing_stop") == "trailing stop"
