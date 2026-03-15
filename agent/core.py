"""
Solana Meme Trading Agent Core

Uses LangGraph + LangChain for intelligent trading decisions.
Skills provide tools, LLM makes decisions.
"""

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import SecretStr
from rich.console import Console

from agent.capabilities import build_capability_help
from agent.config import config
from agent.intent import Intent, IntentType
from agent.prompts import build_solana_meme_system_prompt
from agent.state import AgentState, Position, Trade, TradeAction, get_state, save_state
from agent.wallet import get_wallet_manager, get_solana_address

console = Console()

# Add skills to path for importing scripts
SKILLS_PATH = Path(__file__).parent.parent / "skills"


@dataclass
class AgentRunResult:
    """Structured result from a LangGraph agent run."""

    text: str
    final_ai_text: str = ""
    last_tool_output: str = ""
    tool_outputs: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[BaseMessage] = field(default_factory=list)


def _looks_incomplete_response(text: str) -> bool:
    """Detect clearly incomplete conversational prefixes."""
    normalized = text.strip().lower()
    if not normalized:
        return True
    incomplete_prefixes = {
        "i'll",
        "i will",
        "let",
        "let me",
        "sure,",
        "okay,",
        "ok,",
    }
    return normalized in incomplete_prefixes


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a model response."""
    stripped = text.strip()
    if not stripped:
        return {}

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


class MemeTradingAgent:
    """
    AI Trading Agent that uses LLM to make trading decisions.

    Skills provide tools and knowledge, but the LLM decides:
    - Which tokens to analyze
    - Whether to trade
    - Position sizing
    - Entry/exit timing
    """

    def __init__(self):
        self.state = get_state()
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance"""
        llm_config = config.llm

        if not llm_config.api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Please configure your .env file.\n"
                "For DashScope (Qwen), use:\n"
                "  OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1\n"
                "  OPENAI_API_KEY=sk-your-key\n"
                "  OPENAI_MODEL=qwen-plus"
            )

        llm_kwargs = {
            "base_url": llm_config.base_url,
            "api_key": SecretStr(llm_config.api_key),
            "model": llm_config.model,
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
        }
        return ChatOpenAI(**llm_kwargs)

    @staticmethod
    def _stringify_message_content(content: Any) -> str:
        """Convert LangChain/LangGraph message content to plain text."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(str(text))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part).strip()
        if isinstance(content, dict):
            return str(content.get("text") or content.get("content") or content)
        return str(content)

    def _extract_run_result(self, result: Dict[str, Any]) -> AgentRunResult:
        """Extract stable text and tool outputs from LangGraph invoke result."""
        messages = result.get("messages") or []
        tool_outputs: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        final_ai_text = ""

        for message in messages:
            calls = getattr(message, "tool_calls", None) or []
            for call in calls:
                if isinstance(call, dict):
                    tool_calls.append(call)
            if isinstance(message, ToolMessage):
                text = self._stringify_message_content(message.content)
                if text:
                    tool_outputs.append(text)
            elif isinstance(message, AIMessage):
                text = self._stringify_message_content(message.content)
                if text:
                    final_ai_text = text

        text = ""
        if final_ai_text and len(final_ai_text.strip()) >= 8:
            text = final_ai_text
        elif tool_outputs:
            text = tool_outputs[-1]
        elif final_ai_text:
            text = final_ai_text
        elif messages:
            text = self._stringify_message_content(messages[-1].content)
        else:
            text = "No response generated"

        return AgentRunResult(
            text=text,
            final_ai_text=final_ai_text,
            last_tool_output=tool_outputs[-1] if tool_outputs else "",
            tool_outputs=tool_outputs,
            tool_calls=tool_calls,
            messages=messages,
        )

    def _create_tools(self) -> List:
        """
        Create tools from skills. Each skill exposes capabilities as tools.
        The LLM decides when and how to use them.
        """
        tools = []

        @tool
        def get_token_price(chain: str, contract: str) -> str:
            """Get current price and info for a token.

            Args:
                chain: Chain code (e.g., 'sol', 'eth', 'bnb')
                contract: Token contract address (empty string for native token like SOL)

            Returns:
                Formatted text with token price and info
            """
            try:
                result = self._run_bitget_api("token-price", f"chain={chain},contract={contract}")
                data = json.loads(result)

                # 格式化为易读的文本
                symbol = data.get("symbol", "UNKNOWN")
                name = data.get("name", "")
                price = data.get("price", 0)
                change_24h = data.get("change24h", 0)

                return (
                    f"Token: {symbol} ({name})\n"
                    f"Price: ${price:.8f}\n"
                    f"24h Change: {change_24h:+.2f}%\n"
                    f"Chain: {chain}\n"
                    f"Contract: {contract}"
                )
            except json.JSONDecodeError:
                return f"Error: Invalid response from API"
            except Exception as e:
                return f"Error getting price: {str(e)}"

        @tool
        def get_token_security(chain: str, contract: str) -> str:
            """Get security audit for a token (honeypot check, taxes, risks).

            Args:
                chain: Chain code (e.g., 'sol')
                contract: Token contract address

            Returns:
                JSON string with security audit results
            """
            return self._run_bitget_api("security", f"chain={chain},contract={contract}")

        @tool
        def get_trending_tokens(name: str) -> str:
            """Get trending/hot tokens from rankings.

            Args:
                name: Ranking name - 'Hotpicks', 'topGainers', or 'topLosers'

            Returns:
                JSON string with ranked token list
            """
            return self._run_bitget_api("rankings", f"name={name}")

        @tool
        def get_token_liquidity(chain: str, contract: str) -> str:
            """Get liquidity pool info for a token.

            Args:
                chain: Chain code (e.g., 'sol')
                contract: Token contract address

            Returns:
                Formatted text with liquidity pool information
            """
            try:
                result = self._run_bitget_api("liquidity", f"chain={chain},contract={contract}")
                data = json.loads(result)

                if "data" in data:
                    liq_data = data["data"]
                    total_liq = liq_data.get("totalLpValue", 0)
                    locked_liq = liq_data.get("lockedLpValue", 0)
                    locked_pct = liq_data.get("lockedLpPercent", 0)

                    return (
                        f"Total Liquidity: ${total_liq:,.2f}\n"
                        f"Locked Liquidity: ${locked_liq:,.2f}\n"
                        f"Locked Percentage: {locked_pct:.1f}%\n"
                        f"Chain: {chain}\n"
                        f"Contract: {contract}"
                    )
                return "No liquidity data available"
            except Exception as e:
                return f"Error getting liquidity: {str(e)}"
            return self._run_bitget_api("liquidity", f"chain={chain},contract={contract}")

        @tool
        def get_token_tx_info(chain: str, contract: str) -> str:
            """Get recent transaction stats for a token (buy/sell volume, trader count).

            Args:
                chain: Chain code (e.g., 'sol')
                contract: Token contract address

            Returns:
                JSON string with transaction statistics
            """
            return self._run_bitget_api("tx-info", f"chain={chain},contract={contract}")

        @tool
        def get_wallet_balance(chain: str, address: str, contracts: str = "") -> str:
            """Get wallet balance for tokens.

            Args:
                chain: Chain code (e.g., 'sol')
                address: Wallet address
                contracts: Comma-separated token contract addresses (empty for native token only)

            Returns:
                JSON string with wallet balances
            """
            args = f"chain={chain},address={address}"
            if contracts:
                args += f",contract={contracts}"
            return self._run_bitget_api("get-processed-balance", args)

        @tool
        def get_swap_quote(
            from_chain: str,
            from_contract: str,
            from_symbol: str,
            from_amount: str,
            to_chain: str,
            to_contract: str,
            to_symbol: str,
            from_address: str,
        ) -> str:
            """Get swap quote for token exchange.

            Args:
                from_chain: Source chain code
                from_contract: Source token contract (empty for native)
                from_symbol: Source token symbol
                from_amount: Amount to swap (human-readable, e.g., "0.1")
                to_chain: Target chain code
                to_contract: Target token contract (empty for native)
                to_symbol: Target token symbol
                from_address: Wallet address

            Returns:
                Formatted text with quote details
            """
            try:
                args = (
                    f"from-chain={from_chain},from-contract={from_contract},from-symbol={from_symbol},"
                    f"from-amount={from_amount},to-chain={to_chain},to-contract={to_contract},"
                    f"to-symbol={to_symbol},from-address={from_address}"
                )
                result = self._run_bitget_api("quote", args)
                data = json.loads(result)

                if data.get("error_code", 0) != 0:
                    return f"Quote Error: {data.get('msg', 'Unknown error')}"

                quote_results = data.get("data", {}).get("quoteResults", [])
                if not quote_results:
                    return "No quote available - No price data from liquidity pools"

                # 格式化第一个市场的报价
                best_quote = quote_results[0]
                market = best_quote.get("market", {})
                out_amount = best_quote.get("outAmount", "0")
                min_amount = best_quote.get("minAmount", "0")
                gas_fees = best_quote.get("gasFees", {})
                slippage_info = best_quote.get("slippageInfo", {})

                return (
                    f"Swap Quote:\n"
                    f"  From: {from_amount} {from_symbol}\n"
                    f"  To: ~{float(out_amount):.6f} {to_symbol}\n"
                    f"  Min Receive: {float(min_amount):.6f} {to_symbol}\n"
                    f"  Market: {market.get('label', market.get('id', 'Unknown'))}\n"
                    f"  Protocol: {market.get('protocol', 'Unknown')}\n"
                    f"  Market ID: {market.get('id', '')}\n"
                    f"  Gas Fee: {gas_fees.get('gasTotalAmount', '0')} SOL\n"
                    f"  Recommended Slippage: {slippage_info.get('recommendSlippage', 1.0)}%\n"
                    f"  Price Impact: {slippage_info.get('priceImpact', 0):.2f}%"
                )
            except json.JSONDecodeError:
                return "Quote Error: Invalid response from API"
            except Exception as e:
                return f"Quote Error: {str(e)}"

        @tool
        def get_portfolio_state() -> str:
            """Get current portfolio state including balances, positions, and PnL.

            Returns:
                JSON string with complete portfolio state
            """
            state_data = {
                "wallet_address": self.state.wallet_address,
                "native_balance": float(self.state.native_balance),
                "token_balances": [
                    {
                        "symbol": b.symbol,
                        "contract": b.contract,
                        "balance": float(b.balance),
                        "balance_usd": float(b.balance_usd) if b.balance_usd else None,
                    }
                    for b in self.state.token_balances
                ],
                "open_positions": [
                    {
                        "id": p.id,
                        "token_symbol": p.token_symbol,
                        "token_contract": p.token_contract,
                        "entry_price": float(p.entry_price),
                        "entry_amount": float(p.entry_amount),
                        "entry_value_usd": float(p.entry_value_usd),
                        "entry_time": p.entry_time.isoformat(),
                        "hold_duration_hours": p.hold_duration_hours,
                    }
                    for p in self.state.open_positions
                ],
                "total_pnl_usd": float(self.state.total_pnl_usd),
                "total_trades": self.state.total_trades,
                "win_rate": self.state.win_rate,
                "daily_trade_count": self.state.daily_trade_count,
                "can_trade_today": self.state.can_trade_today(config.trading.max_daily_trades),
            }
            return json.dumps(state_data, indent=2)

        @tool
        def record_position(
            token_symbol: str,
            token_contract: str,
            entry_price: float,
            entry_amount: float,
            entry_value_usd: float,
            entry_tx_id: str = "",
        ) -> str:
            """Record a new position after successful buy.

            Args:
                token_symbol: Token symbol (e.g., 'PEPE')
                token_contract: Token contract address
                entry_price: Entry price per token
                entry_amount: Number of tokens purchased
                entry_value_usd: Total USD value at entry
                entry_tx_id: Transaction ID (optional)

            Returns:
                Confirmation message with position ID
            """
            try:
                position = Position(
                    token_symbol=token_symbol,
                    token_contract=token_contract,
                    entry_price=Decimal(str(entry_price)),
                    entry_amount=Decimal(str(entry_amount)),
                    entry_value_usd=Decimal(str(entry_value_usd)),
                    entry_tx_id=entry_tx_id if entry_tx_id else None,
                )

                self.state.positions.append(position)
                save_state(self.state)

                return f"Position recorded: {position.id} - {position.token_symbol}"
            except Exception as e:
                return f"Error recording position: {str(e)}"

        @tool
        def close_position(
            position_id: str,
            exit_price: float,
            exit_value_usd: float,
            exit_tx_id: str = "",
        ) -> str:
            """Close a position after successful sell.

            Args:
                position_id: The position ID to close
                exit_price: Exit price per token
                exit_value_usd: Total USD value at exit
                exit_tx_id: Transaction ID (optional)

            Returns:
                Confirmation message with PnL
            """
            try:
                position = self.state.close_position(
                    position_id=position_id,
                    exit_price=Decimal(str(exit_price)),
                    exit_value_usd=Decimal(str(exit_value_usd)),
                    exit_tx_id=exit_tx_id or "",
                )
                save_state(self.state)

                return f"Position closed: {position.id} - PnL: ${position.pnl_usd} ({position.pnl_pct}%)"
            except Exception as e:
                return f"Error closing position: {str(e)}"

        @tool
        def check_risk_rules(token_contract: str, trade_value_usd: float) -> str:
            """Check if a trade passes risk management rules.

            Args:
                token_contract: Token contract address
                trade_value_usd: USD value of the proposed trade

            Returns:
                Risk check results with pass/fail status
            """
            trading_config = config.trading

            checks = []
            passed = True

            # Check daily trade limit
            if not self.state.can_trade_today(trading_config.max_daily_trades):
                checks.append(f"Daily trade limit reached ({trading_config.max_daily_trades})")
                passed = False
            else:
                checks.append(
                    f"Daily trades: {self.state.daily_trade_count}/{trading_config.max_daily_trades}"
                )

            # Check max holdings
            if len(self.state.open_positions) >= trading_config.max_holdings:
                checks.append(f"Max holdings reached ({trading_config.max_holdings})")
                passed = False
            else:
                checks.append(
                    f"Open positions: {len(self.state.open_positions)}/{trading_config.max_holdings}"
                )

            # Check position size
            total_value = self.state.total_value_usd
            if total_value > 0:
                position_pct = (Decimal(str(trade_value_usd)) / total_value) * 100
                if position_pct > Decimal(str(trading_config.max_position_pct)):
                    checks.append(
                        f"Position too large: {float(position_pct):.1f}% > {trading_config.max_position_pct}%"
                    )
                    passed = False
                else:
                    checks.append(f"Position size: {float(position_pct):.1f}% of portfolio")

            # Check if token is blacklisted
            if token_contract in self.state.memory.token_blacklist:
                checks.append("Token is blacklisted")
                passed = False

            result = "Risk Check Results:\n" + "\n".join(f"  - {c}" for c in checks)
            result += f"\n\nStatus: {'PASSED' if passed else 'FAILED'}"

            return result

        @tool
        def execute_buy(
            token_contract: str,
            token_symbol: str,
            amount_sol: float,
            slippage: float = 1.0,
        ) -> str:
            """Execute a BUY trade (SOL -> Token).

            This tool performs the complete swap flow:
            1. Get wallet address from mnemonic
            2. Get swap quote
            3. Confirm the quote
            4. Sign and send transaction
            5. Record the position

            IMPORTANT: This requires user confirmation before execution.

            Args:
                token_contract: Token contract address to buy (e.g., "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN")
                token_symbol: Token symbol (MUST be the actual symbol like "TRUMP", not "UNKNOWN")
                amount_sol: Amount of SOL to spend (e.g., 0.01)
                slippage: Slippage tolerance in percent (default 1.0 = 1%)

            Returns:
                Transaction result or confirmation prompt
            """
            result = self.prepare_buy_transaction(
                token_contract, token_symbol, amount_sol, slippage
            )
            return result["message"]

        @tool
        def confirm_buy(
            token_contract: str,
            token_symbol: str,
            amount_sol: float,
            market: str,
            protocol: str,
            slippage: float = 1.0,
        ) -> str:
            """Confirm and execute a BUY trade after user approval.

            This should ONLY be called after explicit user confirmation.

            Args:
                token_contract: Token contract address to buy
                token_symbol: Token symbol
                amount_sol: Amount of SOL to spend
                market: Selected market ID from quote
                protocol: Selected protocol from quote
                slippage: Slippage tolerance

            Returns:
                Transaction result with tx_id
            """
            result = self.execute_buy_transaction(
                token_contract=token_contract,
                token_symbol=token_symbol,
                amount_sol=amount_sol,
                market=market,
                protocol=protocol,
                slippage=slippage,
            )
            return result["message"]

        @tool
        def execute_sell(
            position_id: str,
            slippage: float = 1.0,
        ) -> str:
            """Execute a SELL trade to close a position.

            Args:
                position_id: Position ID to close
                slippage: Slippage tolerance (default 1.0%)

            Returns:
                Transaction result
            """
            result = self.prepare_sell_transaction(position_id, slippage)
            return result["message"]

        @tool
        def analyze_investment_opportunities(
            budget_usd: float,
            max_positions: int = 3,
            min_score: int = 70,
        ) -> str:
            """Analyze trending tokens and find investment opportunities within budget.

            This tool performs a complete analysis pipeline:
            1. Scans trending tokens
            2. Runs security audits
            3. Checks liquidity and activity
            4. Scores each opportunity
            5. Recommends allocation

            Args:
                budget_usd: Total budget in USD
                max_positions: Maximum number of positions to open
                min_score: Minimum risk score threshold (0-100)

            Returns:
                Detailed analysis with ranked opportunities and recommendations
            """
            import json

            results = []

            # Get trending tokens - filter for Solana only
            rankings_result = self._run_bitget_api("rankings", "name=Hotpicks")
            try:
                rankings_data = json.loads(rankings_result)
                all_tokens = rankings_data.get("data", {}).get("list", [])
                # Filter for Solana tokens only
                tokens = [t for t in all_tokens if t.get("chain") == "sol"][:10]
            except Exception as e:
                return f"Error fetching trending tokens: {str(e)}"

            analyzed_count = 0
            for token in tokens:
                symbol = token.get("symbol", "")
                contract = token.get("contract", "")

                if not contract:
                    continue

                analyzed_count += 1

                # Security check
                security_result = self._run_bitget_api("security", f"chain=sol,contract={contract}")
                try:
                    security_data = json.loads(security_result)
                    # Handle list response format
                    if (
                        isinstance(security_data.get("data"), list)
                        and len(security_data.get("data", [])) > 0
                    ):
                        security = security_data["data"][0]
                    else:
                        security = {}
                except Exception as e:
                    continue

                # Skip high risk
                if security.get("highRisk", False):
                    continue

                # Liquidity check
                liquidity_result = self._run_bitget_api(
                    "liquidity", f"chain=sol,contract={contract}"
                )
                try:
                    liquidity_data = json.loads(liquidity_result)
                    # Handle dict format with totalLpValue
                    if isinstance(liquidity_data.get("data"), dict):
                        liquidity_usd = float(liquidity_data["data"].get("totalLpValue", 0))
                    else:
                        liquidity_usd = 0
                except:
                    liquidity_usd = 0

                # Skip low liquidity
                if liquidity_usd < 10000:
                    continue

                # Activity check
                tx_result = self._run_bitget_api("tx-info", f"chain=sol,contract={contract}")
                try:
                    tx_data = json.loads(tx_result)
                    tx_info = tx_data.get("data", {})
                    if isinstance(tx_info, list):
                        tx_info = tx_info[0] if tx_info else {}
                except:
                    tx_info = {}

                # Calculate score
                score = 0
                score_breakdown = []

                # Security score (40 points max)
                if not security.get("isHoneypot"):
                    score += 20
                    score_breakdown.append("No honeypot: +20")

                buy_tax = float(security.get("buyTax", 0) or 0)
                sell_tax = float(security.get("sellTax", 0) or 0)
                if buy_tax <= 5 and sell_tax <= 5:
                    score += 20
                    score_breakdown.append("Low taxes: +20")
                elif buy_tax <= 10 and sell_tax <= 10:
                    score += 10
                    score_breakdown.append("Medium taxes: +10")

                # Liquidity score (30 points max)
                if liquidity_usd >= 100000:
                    score += 30
                    score_breakdown.append(f"High liquidity (${liquidity_usd / 1e6:.1f}M): +30")
                elif liquidity_usd >= 50000:
                    score += 20
                    score_breakdown.append(f"Good liquidity (${liquidity_usd / 1e3:.0f}K): +20")
                elif liquidity_usd >= 10000:
                    score += 10
                    score_breakdown.append(f"Adequate liquidity (${liquidity_usd / 1e3:.0f}K): +10")

                # Activity score (30 points max)
                volume_24h = float(tx_info.get("volume24h", 0) or 0)
                if volume_24h >= 1000000:
                    score += 20
                    score_breakdown.append(f"High volume (${volume_24h / 1e6:.1f}M): +20")
                elif volume_24h >= 100000:
                    score += 10
                    score_breakdown.append(f"Good volume (${volume_24h / 1e3:.0f}K): +10")

                # Check buy/sell ratio
                buy_ratio = tx_info.get("buyRatio24h", 0.5)
                if isinstance(buy_ratio, str):
                    try:
                        buy_ratio = float(buy_ratio)
                    except:
                        buy_ratio = 0.5
                if buy_ratio > 0.6:
                    score += 10
                    score_breakdown.append(f"Bullish ratio ({buy_ratio:.0%}): +10")
                elif buy_ratio > 0.5:
                    score += 5
                    score_breakdown.append(f"Neutral ratio ({buy_ratio:.0%}): +5")

                if score >= min_score:
                    results.append(
                        {
                            "symbol": symbol,
                            "contract": contract,
                            "score": score,
                            "score_breakdown": score_breakdown,
                            "liquidity_usd": liquidity_usd,
                            "volume_24h": volume_24h,
                            "buy_ratio": buy_ratio,
                            "price": token.get("price", 0),
                            "change_24h": token.get("change24h", 0),
                        }
                    )

            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)

            # Build report
            report = f"""[INVESTMENT OPPORTUNITY ANALYSIS]

Budget: {budget_usd} USDT
Max Positions: {max_positions}
Min Score: {min_score}
Tokens Analyzed: {analyzed_count}
Qualified Opportunities: {len(results)}

"""

            if not results:
                report += "No tokens met the investment criteria.\n"
                return report

            # Top opportunities
            report += "TOP OPPORTUNITIES:\n" + "=" * 50 + "\n\n"

            for i, opp in enumerate(results[:max_positions], 1):
                position_size = min(
                    budget_usd / max_positions, budget_usd * 0.05
                )  # Max 5% per trade

                report += f"{i}. {opp['symbol']} (Score: {opp['score']}/100)\n"
                report += f"   Contract: {opp['contract']}\n"
                report += f"   Price: ${opp['price']}\n"
                report += f"   24h Change: {opp['change_24h']}%\n"
                report += f"   Liquidity: ${opp['liquidity_usd'] / 1e3:.0f}K\n"
                report += f"   Volume 24h: ${opp['volume_24h'] / 1e3:.0f}K\n"
                report += f"   Buy Ratio: {opp['buy_ratio']:.0%}\n"
                report += f"   Suggested Position: {position_size:.2f} USDT\n"
                report += f"   Score Breakdown:\n"
                for item in opp["score_breakdown"]:
                    report += f"      - {item}\n"
                report += "\n"

            # Investment plan
            report += "\nRECOMMENDED INVESTMENT PLAN:\n" + "=" * 50 + "\n\n"

            total_allocated = 0
            for i, opp in enumerate(results[:max_positions], 1):
                position_size = min(budget_usd / max_positions, budget_usd * 0.05)
                total_allocated += position_size

                report += f"{i}. Buy {opp['symbol']}\n"
                report += f"   Amount: {position_size:.2f} USDT (~{position_size / 150:.3f} SOL)\n"
                report += f"   Contract: {opp['contract']}\n"
                report += f"   Stop Loss: -15% | Take Profit: +30%\n\n"

            report += f"Total Allocated: {total_allocated:.2f} USDT\n"
            report += f"Remaining: {budget_usd - total_allocated:.2f} USDT\n"

            return report

        @tool
        def confirm_sell(
            position_id: str,
            market: str,
            protocol: str,
            slippage: float = 1.0,
        ) -> str:
            """Confirm and execute a SELL trade.

            Args:
                position_id: Position ID to close
                market: Selected market ID
                protocol: Selected protocol
                slippage: Slippage tolerance

            Returns:
                Transaction result
            """
            result = self.execute_sell_transaction(position_id, market, protocol, slippage)
            return result["message"]

        tools = [
            get_token_price,
            get_token_security,
            get_trending_tokens,
            get_token_liquidity,
            get_token_tx_info,
            get_wallet_balance,
            get_swap_quote,
            get_portfolio_state,
            record_position,
            close_position,
            check_risk_rules,
            execute_buy,
            confirm_buy,
            execute_sell,
            confirm_sell,
            analyze_investment_opportunities,
        ]

        return tools

    def _run_bitget_api(self, command: str, args: str) -> str:
        """Run bitget_agent_api.py script"""
        script_path = SKILLS_PATH / "bitget-wallet-skill" / "scripts" / "bitget_agent_api.py"

        # Parse args (expecting comma-separated key=value)
        cmd_args = []
        if args:
            for part in args.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    cmd_args.extend([f"--{key.strip()}", value.strip()])
                else:
                    cmd_args.append(part.strip())

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), command] + cmd_args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            return result.stdout
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    def _create_agent(self):
        """Create the LangGraph react agent with trading personality"""
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=build_solana_meme_system_prompt(self.state),
        )

    def classify_intent_with_llm(
        self, user_input: str, chat_history: Optional[List[tuple[str, str]]] = None
    ) -> Intent:
        """Classify a free-form user request into a supported trading intent."""
        messages: List[BaseMessage] = [
            SystemMessage(
                content=(
                    "Map the user's request to one supported intent. "
                    "Valid intents: buy, sell, scan, analyze, status, positions, history, auto_invest, help, unknown. "
                    "Return JSON only with keys intent, confidence, params. "
                    "Use params keys token, amount_sol, position_id, limit, budget_usd when relevant. "
                    "If unsupported, choose unknown.\n\n"
                    f"{build_capability_help()}"
                )
            )
        ]
        if chat_history:
            for role, content in chat_history[-8:]:
                if role == "human":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user_input))

        response = self.llm.invoke(messages)
        parsed = _extract_json_object(
            self._stringify_message_content(getattr(response, "content", ""))
        )

        intent_name = str(parsed.get("intent", "unknown")).lower()
        params = parsed.get("params") if isinstance(parsed.get("params"), dict) else {}
        confidence = parsed.get("confidence", 0.0)

        intent_map = {
            "buy": IntentType.BUY,
            "sell": IntentType.SELL,
            "scan": IntentType.SCAN,
            "analyze": IntentType.ANALYZE,
            "status": IntentType.STATUS,
            "positions": IntentType.POSITIONS,
            "history": IntentType.HISTORY,
            "auto_invest": IntentType.AUTO_INVEST,
            "help": IntentType.HELP,
            "unknown": IntentType.UNKNOWN,
        }
        intent_type = intent_map.get(intent_name, IntentType.UNKNOWN)

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0

        return Intent(
            type=intent_type,
            params=params,
            confidence=confidence_value,
            raw_input=user_input,
        )

    def resolve_token_symbol(self, token_contract: str, preferred_symbol: str = "") -> str:
        """Resolve a token symbol with API fallback."""
        if preferred_symbol and preferred_symbol.upper() != "UNKNOWN":
            return preferred_symbol
        try:
            result = self._run_bitget_api("token-price", f"chain=sol,contract={token_contract}")
            data = json.loads(result)
            symbol = data.get("symbol") or preferred_symbol
            return symbol if symbol else "UNKNOWN"
        except Exception:
            return preferred_symbol or "UNKNOWN"

    def prepare_buy_transaction(
        self,
        token_contract: str,
        token_symbol: str,
        amount_sol: float,
        slippage: float = 1.0,
    ) -> Dict[str, Any]:
        """Prepare a buy transaction and return structured quote details."""
        wm = get_wallet_manager()
        if not wm.has_mnemonic:
            return {
                "ok": False,
                "message": "Error: No mnemonic configured. Set MNEMONIC_PHRASE in .env file",
            }

        try:
            address = wm.get_solana_address()
        except Exception as exc:
            return {"ok": False, "message": f"Error deriving wallet: {str(exc)}"}

        resolved_symbol = self.resolve_token_symbol(token_contract, token_symbol)
        if not resolved_symbol or resolved_symbol.upper() == "UNKNOWN":
            return {"ok": False, "message": "Unable to resolve token symbol for quote request"}

        quote_result = self._run_bitget_api(
            "quote",
            f"from-chain=sol,from-contract=,from-symbol=SOL,from-amount={amount_sol},"
            f"to-chain=sol,to-contract={token_contract},to-symbol={resolved_symbol},"
            f"from-address={address}",
        )

        try:
            quote_data = json.loads(quote_result)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "message": f"Error parsing quote: {quote_result}",
                "raw": quote_result,
            }

        if quote_data.get("error_code", 0) != 0:
            return {
                "ok": False,
                "message": f"Quote error: {quote_data.get('msg', 'Unknown error')}",
                "raw": quote_data,
                "token_symbol": resolved_symbol,
            }

        quote_results = quote_data.get("data", {}).get("quoteResults", [])
        if not quote_results:
            return {
                "ok": False,
                "message": "No quotes available - Token may have insufficient liquidity or price data unavailable",
                "raw": quote_data,
                "token_symbol": resolved_symbol,
            }

        best_quote = quote_results[0]
        market = best_quote.get("market", {}).get("id", "")
        protocol = best_quote.get("market", {}).get("protocol", "")
        out_amount = best_quote.get("outAmount", "0")
        if not market or not protocol:
            return {
                "ok": False,
                "message": "Invalid quote - Missing market/protocol information",
                "raw": quote_data,
            }

        return {
            "ok": True,
            "message": (
                f"[BUY PREPARATION - REQUIRES CONFIRMATION]\n\n"
                f"Action: Buy {resolved_symbol}\n"
                f"Spend: {amount_sol} SOL\n"
                f"Receive: ~{out_amount} {resolved_symbol}\n"
                f"Market: {market}\n"
                f"Protocol: {protocol}\n"
                f"Slippage: {slippage}%\n"
                f"Wallet: {address}"
            ),
            "token_symbol": resolved_symbol,
            "market": market,
            "protocol": protocol,
            "out_amount": out_amount,
            "address": address,
            "quote_data": quote_data,
        }

    def execute_buy_transaction(
        self,
        token_contract: str,
        token_symbol: str,
        amount_sol: float,
        market: str,
        protocol: str,
        slippage: float = 1.0,
    ) -> Dict[str, Any]:
        """Execute buy transaction directly and return structured result."""
        wm = get_wallet_manager()
        address = wm.get_solana_address()
        resolved_symbol = self.resolve_token_symbol(token_contract, token_symbol)
        slippage_decimal = slippage / 100.0

        confirm_args = (
            f"from-chain=sol,from-contract=,from-symbol=SOL,from-amount={amount_sol},"
            f"from-address={address},"
            f"to-chain=sol,to-contract={token_contract},to-symbol={resolved_symbol},"
            f"to-address={address},"
            f"market={market},protocol={protocol},slippage={slippage_decimal},"
            f"features=user_gas"
        )
        confirm_result = self._run_bitget_api("confirm", confirm_args)

        try:
            confirm_data = json.loads(confirm_result)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "message": f"Error confirming quote: {confirm_result}",
                "raw": confirm_result,
            }

        if confirm_data.get("error_code", 0) != 0:
            return {
                "ok": False,
                "message": f"Confirm error: {confirm_data.get('msg', 'Unknown error')}",
                "raw": confirm_data,
            }

        order_id = confirm_data.get("data", {}).get("orderId")
        if not order_id:
            return {"ok": False, "message": "No order ID in confirm response", "raw": confirm_data}

        result = wm.sign_and_send_swap(
            order_id=order_id,
            from_chain="sol",
            from_contract="",
            from_symbol="SOL",
            from_amount=str(amount_sol),
            to_chain="sol",
            to_contract=token_contract,
            to_symbol=resolved_symbol,
            from_address=address,
            to_address=address,
            market=market,
            protocol=protocol,
            slippage=str(slippage_decimal),
        )

        if "error" in result:
            return {"ok": False, "message": f"Transaction failed: {result['error']}", "raw": result}

        tx_id = result.get("data", {}).get("details", {}).get("fromTxId", "")
        quote_data = confirm_data.get("data", {}).get("quoteResult", {})
        out_amount = quote_data.get("outAmount", "0")
        entry_price = (
            Decimal(str(amount_sol)) / Decimal(str(out_amount)) if out_amount else Decimal("0")
        )
        entry_value_usd = Decimal(str(amount_sol)) * Decimal("150")
        stop_loss_price = entry_price * Decimal(str(1 - config.trading.stop_loss_pct / 100))
        take_profit_price = entry_price * Decimal(str(1 + config.trading.take_profit_pct / 100))

        position = Position(
            token_symbol=resolved_symbol,
            token_contract=token_contract,
            entry_price=entry_price,
            entry_amount=Decimal(str(out_amount)),
            remaining_amount=Decimal(str(out_amount)),
            entry_value_usd=entry_value_usd,
            entry_tx_id=tx_id,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            highest_price=entry_price,
        )
        self.state.positions.append(position)
        self.state.record_trade(
            Trade(
                action=TradeAction.BUY,
                token_symbol=resolved_symbol,
                token_contract=token_contract,
                amount=Decimal(str(out_amount)),
                price=entry_price,
                value_usd=entry_value_usd,
                tx_id=tx_id,
                position_id=position.id,
            )
        )
        save_state(self.state)

        message = (
            f"[BUY EXECUTED SUCCESSFULLY]\n\n"
            f"Token: {resolved_symbol}\n"
            f"Amount: {out_amount}\n"
            f"SOL Spent: {amount_sol}\n"
            f"Entry Price: ${float(entry_price):.8f}\n"
            f"Stop Loss: ${float(stop_loss_price):.8f} (-{config.trading.stop_loss_pct}%)\n"
            f"Take Profit: ${float(take_profit_price):.8f} (+{config.trading.take_profit_pct}%)\n"
            f"Transaction: {tx_id}\n"
            f"Position ID: {position.id}"
        )
        return {
            "ok": True,
            "message": message,
            "tx_id": tx_id,
            "position_id": position.id,
            "token_symbol": resolved_symbol,
        }

    def prepare_sell_transaction(
        self,
        position_id: str,
        slippage: float = 1.0,
    ) -> Dict[str, Any]:
        """Prepare a sell transaction and return structured quote details."""
        position = next(
            (p for p in self.state.positions if p.id == position_id and p.is_open), None
        )
        if not position:
            return {"ok": False, "message": f"Position {position_id} not found or already closed"}

        wm = get_wallet_manager()
        address = wm.get_solana_address()

        quote_result = self._run_bitget_api(
            "quote",
            f"from-chain=sol,from-contract={position.token_contract},from-symbol={position.token_symbol},"
            f"from-amount={position.entry_amount},to-chain=sol,to-contract=,to-symbol=SOL,"
            f"from-address={address}",
        )

        try:
            quote_data = json.loads(quote_result)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "message": f"Error parsing quote: {quote_result}",
                "raw": quote_result,
            }

        if quote_data.get("error_code", 0) != 0:
            return {
                "ok": False,
                "message": f"Quote error: {quote_data.get('msg', 'Unknown error')}",
                "raw": quote_data,
            }

        quote_results = quote_data.get("data", {}).get("quoteResults", [])
        if not quote_results:
            return {"ok": False, "message": "No quotes available", "raw": quote_data}

        best_quote = quote_results[0]
        out_amount = best_quote.get("outAmount", "0")
        market = best_quote.get("market", {}).get("id", "")
        protocol = best_quote.get("market", {}).get("protocol", "")

        if not market or not protocol:
            return {
                "ok": False,
                "message": "Invalid quote - Missing market/protocol information",
                "raw": quote_data,
            }

        return {
            "ok": True,
            "message": (
                f"[SELL PREPARATION - REQUIRES CONFIRMATION]\n\n"
                f"Action: Sell {position.token_symbol}\n"
                f"Position ID: {position_id}\n"
                f"Amount: {position.entry_amount}\n"
                f"Expected SOL: ~{out_amount}\n"
                f"Market: {market}\n"
                f"Protocol: {protocol}\n"
                f"Slippage: {slippage}%"
            ),
            "position": position,
            "market": market,
            "protocol": protocol,
            "out_amount": out_amount,
            "quote_data": quote_data,
        }

    def execute_sell_transaction(
        self,
        position_id: str,
        market: str,
        protocol: str,
        slippage: float = 1.0,
    ) -> Dict[str, Any]:
        """Execute sell transaction directly and return structured result."""
        position = next(
            (p for p in self.state.positions if p.id == position_id and p.is_open), None
        )
        if not position:
            return {"ok": False, "message": f"Position {position_id} not found or already closed"}

        wm = get_wallet_manager()
        address = wm.get_solana_address()
        slippage_decimal = slippage / 100.0

        confirm_args = (
            f"from-chain=sol,from-contract={position.token_contract},from-symbol={position.token_symbol},"
            f"from-amount={position.entry_amount},from-address={address},"
            f"to-chain=sol,to-contract=,to-symbol=SOL,to-address={address},"
            f"market={market},protocol={protocol},slippage={slippage_decimal},features=user_gas"
        )
        confirm_result = self._run_bitget_api("confirm", confirm_args)

        try:
            confirm_data = json.loads(confirm_result)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "message": f"Error confirming quote: {confirm_result}",
                "raw": confirm_result,
            }

        if confirm_data.get("error_code", 0) != 0:
            return {
                "ok": False,
                "message": f"Confirm error: {confirm_data.get('msg', 'Unknown error')}",
                "raw": confirm_data,
            }

        order_id = confirm_data.get("data", {}).get("orderId")
        if not order_id:
            return {"ok": False, "message": "No order ID in confirm response", "raw": confirm_data}

        result = wm.sign_and_send_swap(
            order_id=order_id,
            from_chain="sol",
            from_contract=position.token_contract,
            from_symbol=position.token_symbol,
            from_amount=str(position.entry_amount),
            to_chain="sol",
            to_contract="",
            to_symbol="SOL",
            from_address=address,
            to_address=address,
            market=market,
            protocol=protocol,
            slippage=str(slippage_decimal),
        )

        if "error" in result:
            return {"ok": False, "message": f"Transaction failed: {result['error']}", "raw": result}

        tx_id = result.get("data", {}).get("details", {}).get("fromTxId", "")
        quote_data = confirm_data.get("data", {}).get("quoteResult", {})
        sol_received = quote_data.get("outAmount", "0")
        exit_value = Decimal(str(sol_received)) * Decimal("150")
        exit_price = (
            Decimal(str(sol_received)) / position.entry_amount
            if position.entry_amount
            else Decimal("0")
        )

        closed_position = self.state.close_position(
            position_id=position_id,
            exit_price=exit_price,
            exit_value_usd=exit_value,
            exit_tx_id=tx_id or "",
        )
        self.state.record_trade(
            Trade(
                action=TradeAction.SELL,
                token_symbol=position.token_symbol,
                token_contract=position.token_contract,
                amount=position.entry_amount,
                price=exit_price,
                value_usd=exit_value,
                tx_id=tx_id,
                position_id=position_id,
            )
        )
        save_state(self.state)

        return {
            "ok": True,
            "message": (
                f"[SELL EXECUTED SUCCESSFULLY]\n\n"
                f"Token: {position.token_symbol}\n"
                f"SOL Received: {sol_received}\n"
                f"PnL: ${closed_position.pnl_usd} ({closed_position.pnl_pct}%)\n"
                f"Transaction: {tx_id}"
            ),
            "tx_id": tx_id,
            "position_id": position_id,
        }

    def run(self, user_input: str, chat_history: Optional[List[tuple[str, str]]] = None) -> str:
        """Run the agent with user input"""
        result = self.run_detailed(user_input, chat_history)
        return result.text

    def chat_reply(
        self, user_input: str, chat_history: Optional[List[tuple[str, str]]] = None
    ) -> str:
        """Return a stable plain-text reply for free-form chat inputs."""
        result = self.run_detailed(user_input, chat_history)
        text = self._stringify_message_content(result.text).strip()
        if text and not _looks_incomplete_response(text):
            return text

        fallback_messages: List[BaseMessage] = []
        if chat_history:
            for role, content in chat_history:
                if role == "human":
                    fallback_messages.append(HumanMessage(content=content))
                else:
                    fallback_messages.append(AIMessage(content=content))

        fallback_messages.append(
            SystemMessage(
                content=(
                    "Reply in English only using plain ASCII characters. "
                    "Do not mention tools. Do not start with filler like 'I'll' or 'Let me'. "
                    "If the request is unclear, ask one short clarifying question."
                )
            )
        )
        fallback_messages.append(HumanMessage(content=user_input))
        fallback = self.llm.invoke(fallback_messages)
        fallback_text = self._stringify_message_content(getattr(fallback, "content", "")).strip()
        return (
            fallback_text
            or "I don't understand. Try: scan, buy <token>, sell <position>, status, positions, or help."
        )

    def run_detailed(
        self, user_input: str, chat_history: Optional[List[tuple[str, str]]] = None
    ) -> AgentRunResult:
        """Run the agent and return structured LangGraph output."""
        # Refresh state
        self.state = get_state()
        self.agent = self._create_agent()

        # Build messages
        messages = []

        # Add chat history
        if chat_history:
            for role, content in chat_history:
                if role == "human":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

        # Add current input
        messages.append(HumanMessage(content=user_input))

        # Run agent
        result = self.agent.invoke({"messages": messages})

        # Save any state changes
        save_state(self.state)

        return self._extract_run_result(result)

    async def run_async(
        self, user_input: str, chat_history: Optional[List[tuple[str, str]]] = None
    ) -> str:
        """Async run"""
        return await asyncio.to_thread(self.run, user_input, chat_history)


def create_agent() -> MemeTradingAgent:
    """Factory function to create agent"""
    return MemeTradingAgent()
