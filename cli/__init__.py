"""
Solana Meme Trading Agent CLI Package

Command-line interface for the Solana Meme Trading Agent.
"""

__version__ = "0.1.0"

from .main import (
    main,
    create_trading_agent,
    TradingAgent,
    cmd_scan,
    cmd_risk_check,
    cmd_swap,
    cmd_portfolio,
)

__all__ = [
    "main",
    "create_trading_agent",
    "TradingAgent",
    "cmd_scan",
    "cmd_risk_check",
    "cmd_swap",
    "cmd_portfolio",
]
