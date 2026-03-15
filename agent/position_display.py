"""Helpers for rendering strategy-aware position text."""

from agent.state import Position


def describe_position_exit_strategy(position: Position) -> str:
    """Return a concise strategy summary for an open position."""
    parts: list[str] = []

    if position.stop_loss_price is not None:
        parts.append(f"initial SL ${float(position.stop_loss_price):.6f}")

    if position.take_profit_price is not None and not position.partial_take_profit_taken:
        parts.append(f"partial TP ${float(position.take_profit_price):.6f} (50%)")

    if position.partial_take_profit_taken:
        parts.append("breakeven armed")
        if position.trailing_stop_price is not None:
            parts.append(f"trailing ${float(position.trailing_stop_price):.6f}")

    if position.exit_pending:
        parts.append("exit pending")

    return " | ".join(parts) if parts else "strategy unavailable"


def describe_exit_reason(reason: str | None) -> str:
    """Render a compact human-friendly exit reason."""
    labels = {
        "partial_take_profit": "partial take profit",
        "trailing_stop": "trailing stop",
        "stop_loss": "stop loss",
        "time_stop": "time stop",
    }
    return labels.get(reason or "", reason or "-")
