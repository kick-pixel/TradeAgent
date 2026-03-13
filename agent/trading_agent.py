"""
Solana Meme Trading Agent - Deep Agents Orchestration

This module coordinates 4 specialized skills (risk-scorer, wallet-manager, meme-scanner, trade-executor)
using the Deep Agents framework for autonomous meme coin trading with human-in-the-loop safeguards.

Workflow: 先风控、再报价、后执行 (Risk First, Then Quote, Then Execute)
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from langchain.tools import tool
from deepagents import create_deep_agent


# =============================================================================
# Configuration
# =============================================================================

SKILLS_BASE = Path(__file__).parent.parent / "skills"

# Model configuration from environment variables
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", None)

SKILL_PATHS = {
    "risk-scorer": SKILLS_BASE / "risk-scorer-skill" / "scripts" / "risk_scorer.py",
    "meme-scanner": SKILLS_BASE / "meme-scanner-skill" / "scripts" / "meme_scanner.py",
    "wallet-manager": SKILLS_BASE
    / "wallet-manager-skill"
    / "scripts"
    / "wallet_manager.py",
    "trade-executor": SKILLS_BASE
    / "trade-executor-skill"
    / "scripts"
    / "trade_executor.py",
}


# =============================================================================
# Tool Wrappers - Subprocess calls to skill scripts
# =============================================================================


@tool
def risk_score(chain: str, contract: str) -> dict:
    """
    Calculate risk score for a token contract.

    Args:
        chain: Blockchain network ('solana', 'ethereum', 'bsc', etc.)
        contract: Token contract address

    Returns:
        dict with keys:
            - score: int (0-100, higher is safer)
            - level: str ('SAFE', 'CAUTION', 'AVOID')
            - factors: list of risk factors found
            - warnings: list of specific warnings
            - recommendation: str (trade recommendation)
    """
    try:
        result = subprocess.run(
            [
                "python",
                str(SKILL_PATHS["risk-scorer"]),
                "--chain",
                chain,
                "--contract",
                contract,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return {
                "error": f"Risk scorer failed: {result.stderr}",
                "score": 0,
                "level": "ERROR",
                "recommendation": "AVOID - Unable to analyze",
            }

        output = result.stdout.strip()
        # Handle potential multiple JSON objects or extra output
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Try to extract JSON from output
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(output[json_start:json_end])
            return {
                "error": "Invalid JSON output from risk scorer",
                "raw_output": output[:500],
                "score": 0,
                "level": "ERROR",
            }

    except subprocess.TimeoutExpired:
        return {
            "error": "Risk analysis timeout",
            "score": 0,
            "level": "TIMEOUT",
            "recommendation": "AVOID - Analysis timeout",
        }
    except Exception as e:
        return {
            "error": str(e),
            "score": 0,
            "level": "ERROR",
            "recommendation": "AVOID - Analysis failed",
        }


@tool
def scan_memes(
    min_liquidity: int = 10000,
    min_score: int = 50,
    limit: int = 10,
    chain: str = "solana",
) -> list:
    """
    Scan for trending meme coins with automatic risk filtering.

    Args:
        min_liquidity: Minimum liquidity in USD (default: $10,000)
        min_score: Minimum risk score to include (default: 50)
        limit: Maximum number of results (default: 10)
        chain: Blockchain to scan (default: 'solana')

    Returns:
        list of dicts, each containing:
            - name: str (token name)
            - symbol: str (token symbol)
            - contract: str (contract address)
            - liquidity: float (USD liquidity)
            - holders: int (number of holders)
            - age_hours: float (token age in hours)
            - risk_score: int (0-100)
            - risk_level: str ('SAFE', 'CAUTION', 'AVOID')
            - volume_24h: float (24h trading volume)
            - price_change_24h: float (percentage)
    """
    try:
        cmd = [
            "python",
            str(SKILL_PATHS["meme-scanner"]),
            "--min-liquidity",
            str(min_liquidity),
            "--min-score",
            str(min_score),
            "--limit",
            str(limit),
            "--chain",
            chain,
            "--json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return [{"error": f"Scanner failed: {result.stderr}", "count": 0}]

        output = result.stdout.strip()

        try:
            data = json.loads(output)
            # Handle both list and dict with 'results' key
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            elif isinstance(data, list):
                return data
            else:
                return [data]
        except json.JSONDecodeError:
            return [{"error": "Invalid JSON from scanner", "raw_output": output[:500]}]

    except subprocess.TimeoutExpired:
        return [{"error": "Scan timeout - market data unavailable", "count": 0}]
    except Exception as e:
        return [{"error": f"Scan failed: {str(e)}", "count": 0}]


@tool
def get_wallet_addresses() -> dict:
    """
    Get configured wallet addresses for trading.

    Returns:
        dict with keys:
            - solana: dict (Solana wallet info)
                - address: str (public key)
                - network: str (mainnet-beta, devnet, etc.)
            - evm: dict (EVM-compatible wallets)
                - ethereum: str (ETH address)
                - bsc: str (BSC address)
                - base: str (Base address, optional)
            - status: str ('configured', 'partial', 'missing')
    """
    try:
        result = subprocess.run(
            ["python", str(SKILL_PATHS["wallet-manager"]), "addresses", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {
                "error": f"Wallet manager failed: {result.stderr}",
                "status": "error",
            }

        output = result.stdout.strip()

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from wallet manager", "status": "error"}

    except subprocess.TimeoutExpired:
        return {"error": "Wallet manager timeout", "status": "timeout"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@tool
def execute_trade(
    from_token: str,
    to_token: str,
    amount: float,
    chain: str = "solana",
    slippage: float = 1.0,
    priority_fee: Optional[float] = None,
    gasless: bool = True,
) -> dict:
    """
    Execute a token swap trade.

    CRITICAL: This tool requires explicit user confirmation before execution.
    The agent must interrupt and get "YES" confirmation from the user.

    Args:
        from_token: Source token symbol or contract address (e.g., 'SOL', 'USDC')
        to_token: Target token symbol or contract address
        amount: Amount of from_token to swap
        chain: Blockchain network (default: 'solana')
        slippage: Maximum slippage tolerance in % (default: 1.0)
        priority_fee: Priority fee in lamports (optional, for Solana)
        gasless: Use gasless mode when available (default: True)

    Returns:
        dict with keys:
            - success: bool
            - tx_hash: str (transaction hash if successful)
            - from_amount: float
            - to_amount: float (expected output)
            - price_impact: float (percentage)
            - fees: dict (breakdown of fees)
            - error: str (if failed)
    """
    try:
        cmd = [
            "python",
            str(SKILL_PATHS["trade-executor"]),
            "swap",
            "--from",
            from_token,
            "--to",
            to_token,
            "--amount",
            str(amount),
            "--chain",
            chain,
            "--slippage",
            str(slippage),
            "--gasless" if gasless else "--no-gasless",
            "--json",
        ]

        if priority_fee is not None:
            cmd.extend(["--priority-fee", str(priority_fee)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Trade execution failed: {result.stderr}",
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
            }

        output = result.stdout.strip()

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON from trade executor",
                "raw_output": output[:500],
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Trade execution timeout - transaction may be pending",
            "from_token": from_token,
            "to_token": to_token,
            "amount": amount,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Trade failed: {str(e)}",
            "from_token": from_token,
            "to_token": to_token,
            "amount": amount,
        }


@tool
def check_portfolio() -> dict:
    """
    Get current portfolio balances and positions.

    Returns:
        dict with keys:
            - total_value_usd: float
            - positions: list of dicts (token, amount, value_usd, pnl_percent)
            - available_balance: dict (available tokens for trading)
            - risk_exposure: float (current portfolio risk level)
    """
    try:
        result = subprocess.run(
            ["python", str(SKILL_PATHS["wallet-manager"]), "portfolio", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return {"error": f"Portfolio fetch failed: {result.stderr}"}

        output = result.stdout.strip()

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON from wallet manager",
                "raw_output": output[:500],
            }

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Subagent Definitions
# =============================================================================

RISK_ANALYST = {
    "name": "risk-analyst",
    "description": "Analyzes token security and provides risk scores. Specializes in identifying honeypots, mint authority risks, and token tax anomalies.",
    "system_prompt": """You are a risk analysis specialist for meme coin trading.

RESPONSIBILITIES:
1. Calculate risk scores using the risk_score tool
2. Identify red flags: honeypot indicators, mint authority, high tax, liquidity locks
3. Provide clear recommendation: SAFE (≥70), CAUTION (40-69), AVOID (<40)

OUTPUT FORMAT:
- Token: [name/symbol]
- Contract: [address]
- Risk Score: [0-100]
- Risk Level: [SAFE/CAUTION/AVOID]
- Key Factors:
  * [Factor 1]: [impact]
  * [Factor 2]: [impact]
- Recommendation: [clear yes/no/maybe with reasoning]

Always explain your reasoning with specific risk factors. Never recommend trading tokens with score < 40.""",
}

MEME_FINDER = {
    "name": "meme-finder",
    "description": "Discovers trending meme coins with automatic risk filtering. Scans multiple sources for new opportunities.",
    "system_prompt": """You discover trending meme coins with strong potential.

WORKFLOW:
1. Use scan_memes to find candidate tokens
2. Apply filters: liquidity > $10K, holders > 100, age > 1h, risk_score ≥ 50
3. Present top 5 opportunities sorted by risk-adjusted score

OUTPUT FORMAT:
- Rank | Symbol | Liquidity | Holders | Age | Risk Score | 24h Change
- [Emoji indicator]: 🔥 Hot, ⚠️ Risky, ✅ Safe
- Brief thesis for each pick

FILTERING RULES:
- NEVER include tokens with risk_score < 50
- Flag tokens < 24h old as high risk
- Prefer tokens with growing holder count
- Avoid tokens with > 5% holder concentration""",
}

TRADE_EXECUTOR_AGENT = {
    "name": "trade-executor",
    "description": "Executes trades with mandatory risk pre-checks and user confirmation.",
    "system_prompt": """CRITICAL: Follow this exact workflow:

STEP 1: RISK CHECK
- Run risk_score on target token contract
- If score < 40: REJECT trade immediately, explain why
- If score 40-69: Warn user STRONGLY about risks

STEP 2: USER CONFIRMATION
- Present trade details: from→to, amount, expected output, slippage
- List all identified risks
- GET EXPLICIT user confirmation: "Type YES to confirm this trade"
- DO NOT proceed without exact "YES" response

STEP 3: EXECUTION
- Call execute_trade with confirmed parameters
- Report transaction hash and results
- Monitor for failures

STEP 4: POST-TRADE
- Confirm new position in portfolio
- Set alert for price monitoring

NEVER execute without confirmation. NEVER trade tokens with score < 40.""",
}


# =============================================================================
# Main Coordinator Agent
# =============================================================================

TRADING_AGENT_SYSTEM_PROMPT = """You are a Solana meme coin trading coordinator powered by Deep Agents.

CRITICAL WORKFLOW (先风控、再报价、后执行):
1. DELEGATE to risk-analyst: Check token safety FIRST before any action
2. DELEGATE to meme-finder: When scanning for new opportunities
3. DELEGATE to trade-executor: Only if risk check passes AND user confirms

NON-NEGOTIABLE RULES:
- Never trade tokens with risk score < 40
- Always require explicit user confirmation ("YES") before execution
- Max 2% of portfolio value per single trade
- Prefer gasless mode when available to reduce costs
- Always check portfolio before suggesting trades

COMMUNICATION STYLE:
- Be concise and direct
- Use bullet points for clarity
- Include confidence scores (0-100%) with recommendations
- Flag risks prominently with ⚠️ emoji
- Use ✅ for safe actions, ❌ for rejected actions

AVAILABLE TOOLS:
- risk_score: Analyze token safety
- scan_memes: Find trending opportunities
- get_wallet_addresses: Check configured wallets
- execute_trade: Execute swaps (requires confirmation)
- check_portfolio: View current positions

RESPONSE FORMAT:
- Start with clear recommendation or status
- Provide supporting details as bullet points
- End with next steps or required actions

Example:
"✅ RECOMMENDATION: Safe to proceed with CAUTIOUS optimism

Analysis:
- Risk Score: 65/100 (CAUTION level)
- Liquidity: $50K (adequate)
- Holders: 500 (growing)
- ⚠️ Warning: Token is only 12 hours old

Next Steps:
1. Confirm trade size (suggest ≤1% portfolio)
2. Type 'YES' to execute"
"""


def create_trading_agent(
    model: Optional[str] = None, interrupt_on_execute: bool = True
) -> Any:
    """
    Create and configure the trading agent with all tools, subagents, and skills.

    Args:
        model: Model identifier for Deep Agents (uses ANTHROPIC_MODEL env var if not provided)
        interrupt_on_execute: Whether to interrupt on trade execution for user confirmation

    Returns:
        Configured Deep Agent instance
    """
    # Use environment variable or default
    if model is None:
        model = f"anthropic:{ANTHROPIC_MODEL}"

    # Define all tools
    tools = [
        risk_score,
        scan_memes,
        get_wallet_addresses,
        execute_trade,
        check_portfolio,
    ]

    # Define subagents
    subagents = [
        RISK_ANALYST,
        MEME_FINDER,
        TRADE_EXECUTOR_AGENT,
    ]

    # Configure skills (progressive disclosure)
    skills = [
        str(SKILLS_BASE / "risk-scorer-skill"),
        str(SKILLS_BASE / "wallet-manager-skill"),
        str(SKILLS_BASE / "meme-scanner-skill"),
        str(SKILLS_BASE / "trade-executor-skill"),
    ]

    # Configure interrupt rules
    interrupt_config = {"execute_trade": True} if interrupt_on_execute else {}

    # Create the agent
    agent = create_deep_agent(
        model=model,
        tools=tools,
        subagents=subagents,
        skills=skills,
        interrupt_on=interrupt_config,
        system_prompt=TRADING_AGENT_SYSTEM_PROMPT,
    )

    return agent


# =============================================================================
# Entry Points
# =============================================================================


def run_agent_interactive():
    """Run the trading agent in interactive mode."""
    agent = create_trading_agent()

    print("=" * 60)
    print("SOLANA MEME TRADING AGENT - Deep Agents Orchestration")
    print("=" * 60)
    print("\nCommands:")
    print("  analyze <contract>  - Analyze token risk")
    print("  scan                - Scan for trending memes")
    print("  portfolio           - Check current portfolio")
    print("  trade <from> <to> <amount> - Execute trade")
    print("  quit/exit           - Exit the agent\n")

    while True:
        try:
            user_input = input("\n🤖 > ").strip()

            if user_input.lower() in ("quit", "exit", "q"):
                print("Exiting trading agent. Stay safe! 🫡")
                break

            if not user_input:
                continue

            # Process the input
            response = agent.run(user_input)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit or continue.")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def run_agent_single_query(query: str):
    """Run the trading agent with a single query and return response."""
    agent = create_trading_agent()
    return agent.run(query)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        response = run_agent_single_query(query)
        print(response)
    else:
        # Interactive mode
        run_agent_interactive()
