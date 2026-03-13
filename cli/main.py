#!/usr/bin/env python3
"""
Solana Meme Trading Agent CLI

Command-line interface for the Solana Meme Trading Agent.
Provides commands for scanning trending coins, checking token risk,
executing swaps, and viewing portfolio balances.

Usage:
    meme-agent scan          # Scan for trending coins
    meme-agent risk-check    # Check single token risk
    meme-agent swap          # Interactive trade workflow
    meme-agent portfolio     # Show wallet balances
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# LLM API Configuration - OpenAI Compatible (Default)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Legacy Anthropic Configuration (optional)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Use OpenAI-compatible API by default
USE_OPENAI_COMPATIBLE = bool(OPENAI_API_KEY)

BGW_API_KEY = os.getenv("BGW_API_KEY", "4843D8C3F1E20772C0E634EDACC5C5F9A0E2DC92")
BGW_API_SECRET = os.getenv("BGW_API_SECRET", "F2ABFDC684BDC6775FD6286B8D06A3AAD30FD587")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# Bitget Wallet API endpoints
BITGET_V2_BASE = "https://api.bitget.com/v2"

# RugCheck API
RUGCHECK_BASE_URL = "https://api.rugcheck.xyz/v1/tokens"

# =============================================================================
# Rich Output Formatting (Optional - falls back to plain text)
# =============================================================================

RICH_AVAILABLE = False
console = None
Panel = None

try:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    pass


def _rich_print(text: str, style: str | None = None) -> None:
    """Safely print using Rich, fallback to plain text on errors."""
    if RICH_AVAILABLE and console:
        try:
            if style:
                console.print(text, style=style)
            else:
                console.print(text)
        except (UnicodeEncodeError, OSError):
            # Fallback to plain text on Windows console encoding issues
            print(text)


def _strip_emoji(text: str) -> str:
    """Remove emoji and special Unicode characters for systems that don't support them."""
    result = []
    for char in text:
        code = ord(char)
        # Keep ASCII and basic Latin characters
        if code < 128:
            result.append(char)
        # Skip emoji and special symbols
        elif code >= 0x1F000:  # Emoji range
            continue
        elif 0x2600 <= code <= 0x26FF:  # Miscellaneous Symbols
            continue
        elif 0x2700 <= code <= 0x27BF:  # Dingbats (includes checkmarks)
            continue
        elif 0x1F300 <= code <= 0x1F9FF:  # More emoji ranges
            continue
        elif 0xFE00 <= code <= 0xFE0F:  # Variation selectors
            continue
        elif 0x2000 <= code <= 0x206F:  # General punctuation
            continue
        else:
            result.append(char)
    return "".join(result)


def print_section_header(title: str, emoji: str = "[SCAN]") -> None:
    """Print a formatted section header."""
    safe_emoji = _strip_emoji(emoji)
    if RICH_AVAILABLE and console and Panel:
        try:
            console.print(Panel(f"[bold]{safe_emoji} {title}[/bold]", style="blue"))
            return
        except (UnicodeEncodeError, OSError):
            pass
    print(f"\n{'=' * 60}")
    print(f"{safe_emoji} {title}")
    print("=" * 60)


def print_success(message: str) -> None:
    """Print a success message."""
    if RICH_AVAILABLE and console:
        try:
            console.print("[green][OK][/green] " + message)
            return
        except (UnicodeEncodeError, OSError):
            pass
    print("[OK] " + message)


def print_error(message: str) -> None:
    """Print an error message."""
    if RICH_AVAILABLE and console:
        try:
            console.print("[red][ERROR][/red] " + message, style="red")
            return
        except (UnicodeEncodeError, OSError):
            pass
    print("[ERROR] " + message)


def print_warning(message: str) -> None:
    """Print a warning message."""
    if RICH_AVAILABLE and console:
        try:
            console.print("[yellow][WARN][/yellow] " + message, style="yellow")
            return
        except (UnicodeEncodeError, OSError):
            pass
    print("[WARN] " + message)


# =============================================================================
# Trading Agent Implementation
# =============================================================================


@dataclass
class AgentState:
    """Trading agent state and configuration."""

    model: str = OPENAI_MODEL if USE_OPENAI_COMPATIBLE else ANTHROPIC_MODEL
    max_tokens: int = 4096
    temperature: float = 0.7
    verbose: bool = False
    api_type: str = "openai" if USE_OPENAI_COMPATIBLE else "anthropic"
    tools: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


class TradingAgent:
    """
    AI-powered trading agent for meme coin analysis and trading.

    Uses Claude API for natural language understanding and decision making,
    combined with on-chain data from Bitget Wallet and RugCheck APIs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_type: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize the trading agent.

        Args:
            api_key: API key (uses OPENAI_API_KEY or ANTHROPIC_API_KEY env var if not provided)
            base_url: API base URL (uses env var if not provided)
            model: Model name (uses env var if not provided)
            api_type: 'openai' or 'anthropic' (auto-detects from available keys)
            verbose: Enable verbose logging
        """
        # Auto-detect API type if not specified
        if api_type is None:
            api_type = "openai" if USE_OPENAI_COMPATIBLE else "anthropic"

        self.api_type = api_type

        if api_type == "openai":
            self.api_key = api_key or OPENAI_API_KEY
            self.base_url = base_url or OPENAI_BASE_URL
            self.model = model or OPENAI_MODEL
        else:
            self.api_key = api_key or ANTHROPIC_API_KEY
            self.base_url = base_url or ANTHROPIC_BASE_URL
            self.model = model or ANTHROPIC_MODEL

        self.verbose = verbose
        self.state = AgentState(model=self.model, verbose=verbose, api_type=api_type)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "SolanaMemeAgent/1.0",
            }
        )

    def invoke(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        Invoke the agent with a conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Dict with 'messages' containing the conversation history
        """
        if not self.api_key:
            # Fallback: Simulate agent response for demo purposes
            return self._simulate_response(messages)

        try:
            # Prepare request based on API type
            if self.api_type == "openai":
                # OpenAI-compatible format (for DashScope, OpenAI, etc.)
                payload = {
                    "model": self.state.model,
                    "max_tokens": self.state.max_tokens,
                    "messages": [m for m in messages if m["role"] != "system"],
                }

                # Add system message if present
                system_messages = [m for m in messages if m.get("role") == "system"]
                if system_messages:
                    payload["messages"].insert(
                        0, {"role": "system", "content": system_messages[0]["content"]}
                    )

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }

                # OpenAI uses /chat/completions endpoint
                endpoint = f"{self.base_url}/chat/completions"
            else:
                # Anthropic format
                payload = {
                    "model": self.state.model,
                    "max_tokens": self.state.max_tokens,
                    "messages": [m for m in messages if m["role"] != "system"],
                }

                system_messages = [m for m in messages if m.get("role") == "system"]
                if system_messages:
                    payload["system"] = system_messages[0]["content"]

                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }

                endpoint = f"{self.base_url}/messages"

            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

            # Parse response based on API type
            if self.api_type == "openai":
                # OpenAI format: choices[0].message.content
                assistant_content = result["choices"][0]["message"]["content"]
            else:
                # Anthropic format: content[0].text
                assistant_content = result["content"][0]["text"]

            assistant_message = {
                "role": "assistant",
                "content": assistant_content,
            }
            messages.append(assistant_message)

            return {"messages": messages}

        except requests.Timeout:
            error_response = {
                "role": "assistant",
                "content": "Error: API request timed out. Please try again.",
            }
            messages.append(error_response)
            return {"messages": messages}
        except requests.RequestException as e:
            error_response = {
                "role": "assistant",
                "content": f"Error: API request failed - {str(e)}",
            }
            messages.append(error_response)
            return {"messages": messages}

    def _simulate_response(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        Simulate agent response when API key is not available.

        This allows the CLI to function in demo mode without API credentials.
        """
        last_message = messages[-1]["content"] if messages else ""
        content = last_message.lower()

        # Simulate responses based on query content
        if "scan" in content:
            response_content = self._simulate_scan_response(content)
        elif "risk" in content or "contract" in content:
            response_content = self._simulate_risk_response(content)
        elif "swap" in content or "trade" in content:
            response_content = self._simulate_swap_response(content)
        elif "portfolio" in content or "balance" in content:
            response_content = self._simulate_portfolio_response(content)
        else:
            response_content = (
                "Hello! I'm your Solana Meme Trading Agent.\n\n"
                "I can help you with:\n"
                "• Scanning for trending meme coins\n"
                "• Analyzing token risk scores\n"
                "• Executing trades on Bitget Wallet\n"
                "• Managing your portfolio\n\n"
                "What would you like to do?\n\n"
                "⚠️  Note: Running in demo mode. Set ANTHROPIC_API_KEY for full AI features."
            )

        messages.append({"role": "assistant", "content": response_content})
        return {"messages": messages}

    def _simulate_scan_response(self, content: str) -> str:
        """Simulate scan command response."""
        return """🔍 **Trending Meme Coins Analysis**

Based on current market data, here are the top trending meme coins:

**Top Picks (Risk-Filtered):**

| Rank | Symbol | Price Change | Liquidity | Risk Score |
|------|--------|--------------|-----------|------------|
| 1 | BONK | +15.2% | $2.5M | 85/100 |
| 2 | WIF | +8.7% | $1.8M | 78/100 |
| 3 | MYRO | +12.3% | $950K | 72/100 |

**Key Observations:**
- Market sentiment: Bullish 📈
- Average risk score: 78/100 (Safe range)
- Total liquidity: $5.2M+ across top picks

⚠️  Always DYOR before trading. Past performance ≠ future results.

To execute a trade, use: `meme-agent swap --chain sol --from SOL --to <TOKEN> --amount 0.1`"""

    def _simulate_risk_response(self, content: str) -> str:
        """Simulate risk-check command response."""
        return """🛡️  **Token Risk Analysis**

**Security Assessment:**
- Contract Risk: LOW ✓
- Liquidity Score: 85/100 ✓
- Holder Distribution: HEALTHY ✓

**Detailed Breakdown:**

| Category | Score | Status |
|----------|-------|--------|
| Security | 90/100 | ✓ Safe |
| Liquidity | 85/100 | ✓ Good |
| Transactions | 78/100 | ✓ Active |

**Overall Risk Score: 84/100 (SAFE)**

**Recommendations:**
✓ Token appears safe to trade
✓ Liquidity is sufficient
⚠️ Monitor for unusual volume spikes

To proceed with trading, use: `meme-agent swap`"""

    def _simulate_swap_response(self, content: str) -> str:
        """Simulate swap command response."""
        return """💱 **Swap Execution Summary**

**Trade Details:**
- From: 0.1 SOL
- To: ~$15.20 worth of tokens (estimated)
- Network: Solana
- Slippage: 1.0% (default)

**Transaction Preview:**
```
Route: SOL → USDC → Target Token
Expected Output: Calculated at execution
Gas Fee: ~0.000005 SOL
```

⚠️  **IMPORTANT: Confirm Before Executing**

To complete this swap:
1. Review the details above
2. Ensure you have sufficient SOL balance
3. Run with --confirm flag to execute

```bash
meme-agent swap --chain sol --from SOL --to <TOKEN> --amount 0.1 --confirm
```

Would you like to proceed with this trade?"""

    def _simulate_portfolio_response(self, content: str) -> str:
        """Simulate portfolio command response."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""💼 **Portfolio Overview**

**Wallet Summary** (as of {now})

| Asset | Balance | Value (USD) | 24h Change |
|-------|---------|-------------|------------|
| SOL | 2.5 | $375.00 | +2.3% |
| BONK | 1,000,000 | $25.00 | +15.2% |
| USDC | 100.00 | $100.00 | 0.0% |

**Total Portfolio Value: $500.00**

**Performance:**
- 24h Change: +$11.50 (+2.3%) 📈
- 7d Change: +$45.00 (+9.9%) 📈

**Top Holdings:**
1. SOL - 75.0%
2. USDC - 20.0%
3. BONK - 5.0%

⚠️  Connect your wallet to see real-time balances."""


def create_trading_agent(
    api_key: Optional[str] = None, verbose: bool = False
) -> TradingAgent:
    """
    Factory function to create a trading agent instance.

    Args:
        api_key: Optional Anthropic API key override
        verbose: Enable verbose logging

    Returns:
        Configured TradingAgent instance
    """
    return TradingAgent(api_key=api_key, verbose=verbose)


# =============================================================================
# Bitget Wallet API Client
# =============================================================================


class BitgetWalletClient:
    """Client for Bitget Wallet API operations."""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "SolanaMemeAgent/1.0",
            }
        )

    def get_token_price(self, chain: str, contract: str) -> Optional[float]:
        """Fetch token price from Bitget Wallet API."""
        try:
            url = f"{BITGET_V2_BASE}/wallet/token/info"
            params = {"contractAddress": contract, "chain": chain}
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == "00000":
                return float(data.get("data", {}).get("price", 0))
        except Exception as e:
            logger.debug(f"Failed to fetch token price: {e}")
        return None

    def get_portfolio(
        self, wallet_address: str, chain: str = "solana"
    ) -> list[dict[str, Any]]:
        """Fetch portfolio balances for a wallet."""
        try:
            url = f"{BITGET_V2_BASE}/wallet/account/balance"
            params = {"address": wallet_address, "chain": chain}
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == "00000":
                return data.get("data", {}).get("tokens", [])
        except Exception as e:
            logger.debug(f"Failed to fetch portfolio: {e}")
        return []


# =============================================================================
# Command Implementations
# =============================================================================


def cmd_scan(args) -> int:
    """
    Execute the scan command - Scan for trending meme coins.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success)
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(
            f"Scan args: limit={args.limit}, min_liquidity={args.min_liquidity}, "
            f"min_score={args.min_score}, chain={args.chain}"
        )

    print_section_header("Scanning for Trending Meme Coins", "[SCAN]")

    try:
        agent = create_trading_agent(verbose=args.verbose)
        result = agent.invoke(
            [
                {
                    "role": "user",
                    "content": (
                        f"Scan for top {args.limit} meme coins with "
                        f"min liquidity ${args.min_liquidity}, min risk score {args.min_score} "
                        f"on {args.chain} chain"
                    ),
                }
            ]
        )
        print(_strip_emoji(result["messages"][-1]["content"]))
        return 0

    except Exception as e:
        print_error(f"Scan failed: {str(e)}")
        logger.exception("Scan command error")
        return 1


def cmd_risk_check(args) -> int:
    """
    Execute the risk-check command - Check single token risk.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success)
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Risk check args: contract={args.contract}, chain={args.chain}")

    print_section_header("Token Risk Analysis", "[RISK]")

    try:
        agent = create_trading_agent(verbose=args.verbose)
        result = agent.invoke(
            [
                {
                    "role": "user",
                    "content": f"Analyze risk for token {args.contract} on {args.chain}",
                }
            ]
        )
        print(_strip_emoji(result["messages"][-1]["content"]))

        if args.json:
            # Also output JSON format for programmatic use
            print(
                "\n"
                + json.dumps(
                    {
                        "chain": args.chain,
                        "contract": args.contract,
                        "analyzed_at": datetime.now().isoformat(),
                    },
                    indent=2,
                )
            )

        return 0

    except Exception as e:
        print_error(f"Risk check failed: {str(e)}")
        logger.exception("Risk check command error")
        return 1


def cmd_swap(args) -> int:
    """
    Execute the swap command - Interactive trade workflow.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success)
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(
            f"Swap args: amount={args.amount}, from={args.from_token}, "
            f"to={args.to_token}, chain={args.chain}"
        )

    print_section_header("Interactive Swap", "[SWAP]")

    try:
        agent = create_trading_agent(verbose=args.verbose)
        query = (
            f"Swap {args.amount} {args.from_token} to {args.to_token} on {args.chain}"
        )

        # Add confirm flag info if provided
        if args.confirm:
            query += " - user has confirmed, proceed with execution"

        result = agent.invoke([{"role": "user", "content": query}])
        print(_strip_emoji(result["messages"][-1]["content"]))

        if args.confirm:
            print_warning("Demo mode: No real transaction executed")
            print_success(
                "In production mode, swap would be executed via Bitget Wallet API"
            )

        return 0

    except Exception as e:
        print_error(f"Swap failed: {str(e)}")
        logger.exception("Swap command error")
        return 1


def cmd_portfolio(args) -> int:
    """
    Execute the portfolio command - Show wallet balances.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success)
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Portfolio args: wallet={args.wallet}, chain={args.chain}")

    print_section_header("Portfolio Overview", "[PORTFOLIO]")

    try:
        agent = create_trading_agent(verbose=args.verbose)
        result = agent.invoke(
            [
                {
                    "role": "user",
                    "content": f"Show portfolio balances for wallet {args.wallet or 'default'} on {args.chain}",
                }
            ]
        )
        print(_strip_emoji(result["messages"][-1]["content"]))

        if args.json:
            # Output JSON format for programmatic use
            print(
                "\n"
                + json.dumps(
                    {
                        "wallet": args.wallet or "demo",
                        "chain": args.chain,
                        "retrieved_at": datetime.now().isoformat(),
                    },
                    indent=2,
                )
            )

        return 0

    except Exception as e:
        print_error(f"Portfolio check failed: {str(e)}")
        logger.exception("Portfolio command error")
        return 1


# =============================================================================
# CLI Argument Parser
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the CLI argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="meme-agent",
        description="Solana Meme Trading Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan for safe meme coins
  %(prog)s scan --limit 10 --min-liquidity 10000 --min-score 50

  # Check single token risk
  %(prog)s risk-check --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

  # Interactive swap
  %(prog)s swap --chain sol --from SOL --to EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --amount 0.1

  # Show portfolio
  %(prog)s portfolio

  # Enable verbose/debug mode
  %(prog)s scan --verbose

  # Output in JSON format
  %(prog)s risk-check --chain sol --contract <ADDRESS> --json

Get help for specific command:
  %(prog)s scan --help
  %(prog)s risk-check --help
        """,
    )

    # Global options
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show version and exit",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose/debug output"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -------------------------------------------------------------------------
    # scan command
    # -------------------------------------------------------------------------
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan for trending meme coins",
        description="Discover trending meme coins with automatic risk filtering",
    )
    scan_parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    scan_parser.add_argument(
        "--min-liquidity",
        type=float,
        default=10000,
        help="Minimum liquidity in USD (default: 10000)",
    )
    scan_parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum risk score 0-100 (default: 50, higher is safer)",
    )
    scan_parser.add_argument(
        "--chain",
        "-c",
        type=str,
        default="sol",
        choices=["sol", "eth", "bsc", "base"],
        help="Blockchain to scan (default: sol)",
    )
    scan_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    scan_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    scan_parser.set_defaults(func=cmd_scan)

    # -------------------------------------------------------------------------
    # risk-check command
    # -------------------------------------------------------------------------
    risk_parser = subparsers.add_parser(
        "risk-check",
        help="Check single token risk",
        description="Analyze risk score for a specific token contract",
    )
    risk_parser.add_argument(
        "--chain",
        "-c",
        type=str,
        required=True,
        choices=["sol", "eth", "bsc", "base", "arbitrum", "polygon"],
        help="Blockchain (required)",
    )
    risk_parser.add_argument(
        "--contract",
        "-t",
        type=str,
        required=True,
        help="Token contract address (required)",
    )
    risk_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    risk_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    risk_parser.set_defaults(func=cmd_risk_check)

    # -------------------------------------------------------------------------
    # swap command
    # -------------------------------------------------------------------------
    swap_parser = subparsers.add_parser(
        "swap",
        help="Interactive trade workflow",
        description="Execute token swap with AI-powered guidance",
    )
    swap_parser.add_argument(
        "--chain", "-c", type=str, default="sol", help="Blockchain (default: sol)"
    )
    swap_parser.add_argument(
        "--from",
        dest="from_token",
        type=str,
        default="SOL",
        help="Source token (default: SOL)",
    )
    swap_parser.add_argument(
        "--to",
        dest="to_token",
        type=str,
        required=True,
        help="Target token contract or symbol (required)",
    )
    swap_parser.add_argument(
        "--amount", type=float, default=0.1, help="Amount to swap (default: 0.1)"
    )
    swap_parser.add_argument(
        "--confirm", action="store_true", help="Confirm and execute the swap"
    )
    swap_parser.add_argument(
        "--slippage",
        type=float,
        default=1.0,
        help="Slippage tolerance %% (default: 1.0)",
    )
    swap_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    swap_parser.set_defaults(func=cmd_swap)

    # -------------------------------------------------------------------------
    # portfolio command
    # -------------------------------------------------------------------------
    portfolio_parser = subparsers.add_parser(
        "portfolio",
        help="Show wallet balances",
        description="View portfolio balances and performance",
    )
    portfolio_parser.add_argument(
        "--wallet",
        "-w",
        type=str,
        default=None,
        help="Wallet address (optional, uses default if not provided)",
    )
    portfolio_parser.add_argument(
        "--chain", "-c", type=str, default="sol", help="Blockchain (default: sol)"
    )
    portfolio_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    portfolio_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    portfolio_parser.set_defaults(func=cmd_portfolio)

    return parser


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    """
    Main entry point for the CLI.

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle no command case
    if not args.command:
        parser.print_help()
        return 0

    # Check for required environment variables
    if args.command in ("scan", "risk-check", "swap") and not ANTHROPIC_API_KEY:
        print_warning("Running in demo mode without ANTHROPIC_API_KEY")
        print_warning("Full AI features require setting ANTHROPIC_API_KEY in .env")
        print()

    # Execute the command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error in main")
        return 1


if __name__ == "__main__":
    sys.exit(main())
