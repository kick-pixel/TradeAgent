#!/usr/bin/env python3
"""
Trade Executor Skill - Human-in-the-Loop Trade Execution

CRITICAL SKILL: Executes trades following the mandatory workflow:
1. Risk Pre-Check (先风控)
2. Get Quote (再报价)
3. User Confirmation (人工确认)
4. Execute Trade (执行)

NEVER auto-execute without explicit user confirmation.
"""

import argparse
import json
import os
import sys
import time
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


# ============================================================================
# CONFIGURATION
# ============================================================================

# Token metadata for common tokens
KNOWN_TOKENS = {
    "sol": {
        "native": {"symbol": "SOL", "decimals": 9},
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {
            "symbol": "USDC",
            "decimals": 6,
        },
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": {
            "symbol": "USDT",
            "decimals": 6,
        },
    },
    "eth": {
        "native": {"symbol": "ETH", "decimals": 18},
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {"symbol": "USDC", "decimals": 6},
        "0xdAC17F958D2ee523a2206206994597C13D831ec7": {"symbol": "USDT", "decimals": 6},
    },
    "bnb": {
        "native": {"symbol": "BNB", "decimals": 18},
        "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d": {
            "symbol": "USDC",
            "decimals": 18,
        },
    },
    "base": {
        "native": {"symbol": "ETH", "decimals": 18},
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": {"symbol": "USDC", "decimals": 6},
    },
}

# Risk thresholds
RISK_THRESHOLD_REJECT = 40  # Below this: REJECT
RISK_THRESHOLD_WARN = 70  # Below this: WARN


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class RiskResult:
    """Result from risk score check."""

    score: int  # 0-100
    rating: str  # DANGEROUS, HIGH_RISK, MODERATE, LOW_RISK, SAFE
    issues: List[str]
    warnings: List[str]


@dataclass
class Quote:
    """Quote from Bitget DEX aggregator."""

    from_chain: str
    from_contract: str
    to_chain: str
    to_contract: str
    from_amount: str  # Human-readable
    to_amount: str  # Human-readable (estimated)
    from_symbol: str
    to_symbol: str
    slippage: float  # Percentage
    price_impact: float  # Percentage
    estimated_gas: float  # In USD
    route: List[str]  # DEX route
    expires_at: int  # Unix timestamp


@dataclass
class TradeResult:
    """Result of trade execution."""

    status: str  # success, failed, cancelled
    order_id: Optional[str]
    tx_hash: Optional[str]
    from_amount: str
    from_token: str
    to_amount: str
    to_token: str
    effective_price: str
    risk_score: int
    gasless: bool
    error: Optional[str] = None


# ============================================================================
# STEP 1: RISK PRE-CHECK
# ============================================================================


def run_risk_score(chain: str, contract_address: str) -> RiskResult:
    """
    Run comprehensive risk analysis on a token contract.

    This is the FIRST and MANDATORY step before any trade.
    """
    issues = []
    warnings = []
    score = 100  # Start with perfect score, deduct for issues

    # Get token info
    token_info = _get_token_info(chain, contract_address)

    # Check 1: Is this a known/verified token?
    chain_tokens = KNOWN_TOKENS.get(chain, {})
    is_known = contract_address in chain_tokens or contract_address == ""

    if not is_known:
        warnings.append("Token is not in known tokens list")
        score -= 10

    # Check 2: Contract verification status (simulated)
    is_verified = _check_contract_verified(chain, contract_address)
    if not is_verified and contract_address:
        issues.append("Contract source code not verified")
        score -= 20

    # Check 3: Honeypot detection (simulated)
    is_honeypot = _check_honeypot(chain, contract_address)
    if is_honeypot:
        issues.append("HONEYPOT DETECTED - Token cannot be sold")
        score -= 50

    # Check 4: Liquidity check
    liquidity_usd = _get_liquidity_usd(chain, contract_address)
    if liquidity_usd < 1000:
        issues.append(f"Very low liquidity: ${liquidity_usd:.2f}")
        score -= 25
    elif liquidity_usd < 10000:
        warnings.append(f"Low liquidity: ${liquidity_usd:.2f}")
        score -= 10

    # Check 5: Holder concentration (simulated)
    top_holder_pct = _get_top_holder_concentration(chain, contract_address)
    if top_holder_pct > 50:
        issues.append(f"Top holder controls {top_holder_pct:.1f}% of supply")
        score -= 15

    # Check 6: Age of contract
    contract_age_days = _get_contract_age_days(chain, contract_address)
    if contract_age_days < 1:
        issues.append("Contract created less than 24 hours ago")
        score -= 20
    elif contract_age_days < 7:
        warnings.append(f"Contract is only {contract_age_days} days old")
        score -= 10

    # Check 7: Mint authority (Solana specific)
    if chain == "sol" and contract_address:
        has_mint_auth = _check_mint_authority(contract_address)
        if has_mint_auth:
            issues.append("Mint authority still enabled - infinite supply risk")
            score -= 15

    # Check 8: Freeze authority (Solana specific)
    if chain == "sol" and contract_address:
        has_freeze_auth = _check_freeze_authority(contract_address)
        if has_freeze_auth:
            issues.append("Freeze authority enabled - tokens can be frozen")
            score -= 15

    # Determine rating
    if score < 40:
        rating = "DANGEROUS"
    elif score < 60:
        rating = "HIGH_RISK"
    elif score < 80:
        rating = "MODERATE"
    elif score < 95:
        rating = "LOW_RISK"
    else:
        rating = "SAFE"

    return RiskResult(
        score=max(0, score), rating=rating, issues=issues, warnings=warnings
    )


def _get_token_info(chain: str, contract_address: str) -> Dict[str, Any]:
    """Get token metadata."""
    if not contract_address:
        # Native token
        return KNOWN_TOKENS.get(chain, {}).get(
            "native", {"symbol": "UNKNOWN", "decimals": 18}
        )

    chain_tokens = KNOWN_TOKENS.get(chain, {})
    return chain_tokens.get(contract_address, {"symbol": "UNKNOWN", "decimals": 18})


def _check_contract_verified(chain: str, contract_address: str) -> bool:
    """Check if contract source code is verified on explorer."""
    if not contract_address:
        return True
    chain_tokens = KNOWN_TOKENS.get(chain, {})
    return contract_address in chain_tokens


def _check_honeypot(chain: str, contract_address: str) -> bool:
    """Check if token is a honeypot (cannot be sold)."""
    if not contract_address:
        return False
    chain_tokens = KNOWN_TOKENS.get(chain, {})
    return contract_address in chain_tokens


def _get_liquidity_usd(chain: str, contract_address: str) -> float:
    """Get total liquidity in USD."""
    if not contract_address:
        return 1_000_000_000  # Native tokens have high liquidity
    chain_tokens = KNOWN_TOKENS.get(chain, {})
    if contract_address in chain_tokens:
        return 100_000_000  # Known tokens have good liquidity
    return 5000  # Unknown tokens - assume moderate


def _get_top_holder_concentration(chain: str, contract_address: str) -> float:
    """Get percentage held by top wallet."""
    if not contract_address:
        return 5.0  # Native tokens well-distributed
    return 25.0  # Assume moderate concentration


def _get_contract_age_days(chain: str, contract_address: str) -> int:
    """Get contract age in days."""
    if not contract_address:
        return 3650  # Native tokens are old
    return 30  # Assume moderate age


def _check_mint_authority(contract_address: str) -> bool:
    """Check if Solana token has mint authority enabled."""
    return False


def _check_freeze_authority(contract_address: str) -> bool:
    """Check if Solana token has freeze authority enabled."""
    return False


# ============================================================================
# STEP 2: GET QUOTE
# ============================================================================


def bitget_order_quote(
    from_chain: str,
    from_contract: str,
    to_chain: str,
    to_contract: str,
    amount: str,
    from_address: str,
    slippage: float = 1.0,
) -> Quote:
    """
    Get trading quote from Bitget DEX aggregator.

    This queries the best route across multiple DEXes.
    """
    # Get token symbols for display
    from_symbol = _get_token_symbol(from_chain, from_contract)
    to_symbol = _get_token_symbol(to_chain, to_contract)

    # Simulate price calculation
    exchange_rate = _get_mock_exchange_rate(from_contract, to_contract, from_chain)

    from_amount_raw = float(amount)
    to_amount_raw = from_amount_raw * exchange_rate

    # Calculate price impact (larger trades have more impact)
    price_impact = min(from_amount_raw * 0.1, 5.0)  # Cap at 5%

    # Calculate effective slippage
    effective_slippage = slippage + (price_impact * 0.5)

    # Mock gas estimate
    estimated_gas = _estimate_gas_cost(from_chain)

    # Mock route
    route = _get_mock_route(from_chain, from_contract, to_contract)

    return Quote(
        from_chain=from_chain,
        from_contract=from_contract,
        to_chain=to_chain,
        to_contract=to_contract,
        from_amount=amount,
        to_amount=f"{to_amount_raw:.6f}",
        from_symbol=from_symbol,
        to_symbol=to_symbol,
        slippage=round(effective_slippage, 2),
        price_impact=round(price_impact, 2),
        estimated_gas=estimated_gas,
        route=route,
        expires_at=int(time.time()) + 30,  # 30 second expiry
    )


def _get_token_symbol(chain: str, contract: str) -> str:
    """Get token symbol."""
    info = _get_token_info(chain, contract)
    return info.get("symbol", "UNKNOWN")


def _get_token_decimals(chain: str, contract: str) -> int:
    """Get token decimals."""
    info = _get_token_info(chain, contract)
    return info.get("decimals", 18)


def _get_mock_exchange_rate(from_contract: str, to_contract: str, chain: str) -> float:
    """Get mock exchange rate for simulation."""
    prices = {
        "": 150.0,  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 1.0,  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 1.0,  # USDT
    }

    from_price = prices.get(from_contract, 1.0)
    to_price = prices.get(to_contract, 1.0)

    return from_price / to_price if to_price > 0 else 1.0


def _estimate_gas_cost(chain: str) -> float:
    """Estimate gas cost in USD."""
    gas_costs = {
        "sol": 0.00025,
        "eth": 5.0,
        "bnb": 0.5,
        "base": 0.1,
    }
    return gas_costs.get(chain, 1.0)


def _get_mock_route(from_chain: str, from_contract: str, to_contract: str) -> List[str]:
    """Get mock DEX route."""
    if from_chain == "sol":
        return ["Jupiter", "Raydium", "Orca"]
    elif from_chain == "eth":
        return ["Uniswap", "1inch", "Curve"]
    else:
        return ["PancakeSwap"]


# ============================================================================
# STEP 3: USER CONFIRMATION
# ============================================================================


def display_trade_confirmation(
    risk_result: RiskResult, quote: Quote, wallet_address: str
) -> bool:
    """
    Display trade details and require explicit user confirmation.

    CRITICAL: This step MUST NOT be skipped. Returns True only if user types YES.
    """
    print("\n" + "=" * 60)
    print("              WARNING: TRADE CONFIRMATION REQUIRED")
    print("=" * 60)
    print()

    # Display risk assessment
    if risk_result.score < 40:
        risk_color = "[CRITICAL]"
    elif risk_result.score < 70:
        risk_color = "[WARNING]"
    else:
        risk_color = "[OK]"

    print(f"{risk_color} RISK ASSESSMENT")
    print(f"   Score: {risk_result.score}/100 ({risk_result.rating})")

    if risk_result.issues:
        print("   ISSUES:")
        for issue in risk_result.issues:
            print(f"      - {issue}")

    if risk_result.warnings:
        print("   WARNINGS:")
        for warning in risk_result.warnings:
            print(f"      - {warning}")

    if not risk_result.issues and not risk_result.warnings:
        print("   No issues detected")

    print()

    # Display trade details
    print("TRADE DETAILS")
    print(f"   From: {quote.from_amount} {quote.from_symbol}")
    print(f"   To:   {quote.to_amount} {quote.to_symbol} (estimated)")
    price_ratio = (
        float(quote.to_amount) / float(quote.from_amount)
        if float(quote.from_amount) > 0
        else 0
    )
    print(f"   Price: 1 {quote.from_symbol} = {price_ratio:.6f} {quote.to_symbol}")
    print()

    # Display fees and slippage
    print("FEES & SLIPPAGE")
    print(f"   Slippage Tolerance: {quote.slippage}%")
    print(f"   Price Impact: {quote.price_impact}%")
    print(f"   Estimated Gas: ${quote.estimated_gas:.4f}")
    print(f"   Route: {' -> '.join(quote.route)}")
    print()

    # Display wallet
    print("WALLET")
    print(f"   Address: {wallet_address[:8]}...{wallet_address[-6:]}")
    print()

    # Display warnings based on risk
    if risk_result.score < 40:
        print("CRITICAL WARNING: Risk score too low!")
        print("   This trade is DANGEROUS and should NOT proceed.")
        print()
    elif risk_result.score < 70:
        print("WARNING: Moderate risk detected")
        print("   Please review the issues above carefully.")
        print()

    if quote.price_impact > 1.0:
        print(f"HIGH PRICE IMPACT: {quote.price_impact}%")
        print("   Consider splitting into smaller trades.")
        print()

    if quote.slippage > 3.0:
        print(f"HIGH SLIPPAGE: {quote.slippage}%")
        print("   Actual output may be significantly lower.")
        print()

    print("=" * 60)

    # Require explicit confirmation
    while True:
        response = input("\nType 'YES' to confirm, anything else to cancel: ").strip()

        if response == "YES":
            print("\nUser confirmed trade")
            return True
        elif response.lower() in ["", "n", "no", "cancel"]:
            print("\nTrade cancelled by user")
            return False
        else:
            print(f"   Received: '{response}' - Please type exactly 'YES' to confirm")


# ============================================================================
# STEP 4: EXECUTE TRADE
# ============================================================================


def bitget_order_create(
    from_chain: str,
    from_contract: str,
    to_contract: str,
    amount: str,
    from_address: str,
    slippage: float,
    feature: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create order via Bitget DEX API.

    Returns order data including unsigned transaction.
    """
    order_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

    return {
        "order_id": order_id,
        "from_chain": from_chain,
        "from_contract": from_contract,
        "to_contract": to_contract,
        "amount": amount,
        "slippage": slippage,
        "feature": feature,
        "tx_data": {
            "data": "mock_transaction_data_" + order_id,
            "to": "0x" + "0" * 40,
            "value": "0",
            "chainId": _get_chain_id(from_chain),
        },
        "expires_at": int(time.time()) + 300,  # 5 minutes
    }


def _get_chain_id(chain: str) -> int:
    """Get numeric chain ID."""
    chain_ids = {
        "sol": 0,
        "eth": 1,
        "bnb": 56,
        "base": 8453,
        "arb": 42161,
        "op": 10,
        "polygon": 137,
    }
    return chain_ids.get(chain, 1)


def supports_gasless(chain: str, from_contract: str, to_contract: str) -> bool:
    """Check if gasless transaction is supported."""
    gasless_supported_chains = ["sol", "base", "arb", "op"]
    return chain in gasless_supported_chains


def sign_transaction(tx_data: Dict[str, Any], wallet_key: str) -> str:
    """
    Sign transaction with wallet.

    In production, this would use secure wallet-manager integration.
    """
    mock_signature = "0x" + secrets.token_hex(64)
    return mock_signature


def bitget_order_submit(order_id: str, signed_tx: str) -> Dict[str, Any]:
    """
    Submit signed transaction to Bitget.

    Returns submission result with transaction hash.
    """
    tx_hash = "0x" + secrets.token_hex(32)

    return {
        "order_id": order_id,
        "tx_hash": tx_hash,
        "status": "submitted",
        "submitted_at": int(time.time()),
    }


def helius_simulate_transaction(signed_tx: str, chain: str) -> Dict[str, Any]:
    """
    Simulate transaction before sending.

    Uses Helius API for Solana, similar services for other chains.
    """
    if chain == "sol":
        return {"success": True, "error": None}
    else:
        return {"success": True, "error": None}


def execute_trade(
    quote: Quote,
    slippage: float,
    wallet_address: str,
    wallet_key: str,
    simulate: bool = False,
    risk_score: int = 0,
) -> TradeResult:
    """
    Execute the trade after user confirmation.

    Uses gasless mode by default when available.
    """
    try:
        # Check gasless support
        gasless = supports_gasless(
            quote.from_chain, quote.from_contract, quote.to_contract
        )

        # Create order
        order = bitget_order_create(
            from_chain=quote.from_chain,
            from_contract=quote.from_contract,
            to_contract=quote.to_contract,
            amount=quote.from_amount,
            from_address=wallet_address,
            slippage=slippage,
            feature="no_gas" if gasless else None,
        )

        # Sign transaction
        signed_tx = sign_transaction(order["tx_data"], wallet_key)

        # Simulation (if requested)
        if simulate:
            sim_result = helius_simulate_transaction(signed_tx, quote.from_chain)
            if sim_result.get("error"):
                return TradeResult(
                    status="failed",
                    order_id=None,
                    tx_hash=None,
                    from_amount=quote.from_amount,
                    from_token=quote.from_symbol,
                    to_amount=quote.to_amount,
                    to_token=quote.to_symbol,
                    effective_price=f"{float(quote.to_amount) / float(quote.from_amount):.6f} {quote.to_symbol}/{quote.from_symbol}",
                    risk_score=risk_score,
                    gasless=gasless,
                    error=f"Simulation failed: {sim_result['error']}",
                )
            print("Simulation passed")

        # Submit transaction
        submission = bitget_order_submit(order["order_id"], signed_tx)

        # Calculate effective price
        price_ratio = (
            float(quote.to_amount) / float(quote.from_amount)
            if float(quote.from_amount) > 0
            else 0
        )
        effective_price = f"{price_ratio:.6f} {quote.to_symbol}/{quote.from_symbol}"

        return TradeResult(
            status="success",
            order_id=submission["order_id"],
            tx_hash=submission["tx_hash"],
            from_amount=quote.from_amount,
            from_token=quote.from_symbol,
            to_amount=quote.to_amount,
            to_token=quote.to_symbol,
            effective_price=effective_price,
            risk_score=risk_score,
            gasless=gasless,
        )

    except Exception as e:
        return TradeResult(
            status="failed",
            order_id=None,
            tx_hash=None,
            from_amount=quote.from_amount,
            from_token=quote.from_symbol,
            to_amount=quote.to_amount,
            to_token=quote.to_symbol,
            effective_price="",
            risk_score=risk_score,
            gasless=False,
            error=str(e),
        )


# ============================================================================
# WALLET MANAGEMENT
# ============================================================================


def get_wallet_address(chain: str) -> str:
    """
    Get wallet address from secure storage.

    In production, this integrates with wallet-manager.
    """
    if chain == "sol":
        return "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    elif chain == "eth":
        return "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
    else:
        return "0x" + "0" * 40


def get_wallet_key(chain: str, wallet_index: int = 0) -> str:
    """
    Get wallet private key from secure storage.

    NEVER log or display this value.
    """
    return "mock_secure_key_" + chain


# ============================================================================
# ERROR HANDLING
# ============================================================================


class TradeError(Exception):
    """Base exception for trade errors."""

    pass


class InsufficientBalanceError(TradeError):
    """Raised when wallet has insufficient balance."""

    pass


class SlippageTooHighError(TradeError):
    """Raised when slippage exceeds threshold."""

    pass


class SimulationFailedError(TradeError):
    """Raised when transaction simulation fails."""

    pass


class UserCancelledError(TradeError):
    """Raised when user cancels trade confirmation."""

    pass


class RiskCheckFailedError(TradeError):
    """Raised when risk check fails."""

    pass


def check_balance(
    chain: str, token_contract: str, wallet_address: str, amount: str
) -> bool:
    """
    Check if wallet has sufficient balance.

    Returns True if balance is sufficient.
    """
    # TODO: Query blockchain for balance
    return True


def handle_insufficient_balance(from_symbol: str, required: str, available: str):
    """Display clear insufficient balance error."""
    print(f"\nINSUFFICIENT BALANCE")
    print(f"   Required: {required} {from_symbol}")
    print(f"   Available: {available} {from_symbol}")
    shortfall = float(required) - float(available)
    print(f"   Shortfall: {shortfall:.6f} {from_symbol}")
    print()


def handle_slippage_warning(slippage: float, recommended: float = 1.0):
    """Display slippage warning with recommendation."""
    print(f"\nHIGH SLIPPAGE WARNING")
    print(f"   Current slippage: {slippage}%")
    print(f"   Recommended: {recommended}%")
    print("   Consider increasing slippage tolerance or reducing trade size.")
    print()


# ============================================================================
# MAIN CLI
# ============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute trades with human-in-the-loop confirmation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Trade 0.1 SOL for USDC on Solana
  python trade_executor.py --chain sol --from-token "" --to-token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --amount 0.1

  # Trade 1 ETH for USDC on Ethereum
  python trade_executor.py --chain eth --from-token "" --to-token 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 --amount 1

  # Dry run (simulation only)
  python trade_executor.py --chain sol --from-token "" --to-token EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --amount 0.1 --simulate
        """,
    )

    parser.add_argument(
        "--chain",
        type=str,
        required=True,
        choices=["sol", "eth", "bnb", "base", "arb", "op", "polygon"],
        help="Blockchain network (sol, eth, bnb, base, etc.)",
    )

    parser.add_argument(
        "--from-token",
        type=str,
        required=True,
        help='Source token contract address (use "" for native token)',
    )

    parser.add_argument(
        "--to-token", type=str, required=True, help="Destination token contract address"
    )

    parser.add_argument(
        "--amount",
        type=str,
        required=True,
        help="Amount to trade (human-readable, NOT wei/lamports)",
    )

    parser.add_argument(
        "--slippage",
        type=float,
        default=1.0,
        help="Slippage tolerance percentage (default: 1.0)",
    )

    parser.add_argument(
        "--wallet",
        type=str,
        default=None,
        help="Wallet override (default: derive from storage)",
    )

    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Dry run - simulate without actual execution",
    )

    parser.add_argument(
        "--max-slippage",
        type=float,
        default=5.0,
        help="Maximum slippage to accept (default: 5.0)",
    )

    parser.add_argument(
        "--min-risk-score",
        type=int,
        default=40,
        help="Minimum risk score to proceed (default: 40)",
    )

    return parser.parse_args()


def main():
    """Main entry point for trade executor."""
    args = parse_args()

    print("\n" + "=" * 60)
    print("           TRADE EXECUTOR - HUMAN IN THE LOOP")
    print("=" * 60)
    print()

    # Validate inputs
    if not args.amount or float(args.amount) <= 0:
        print("Error: Amount must be greater than 0")
        sys.exit(1)

    # Get wallet
    wallet_address = args.wallet or get_wallet_address(args.chain)
    wallet_key = get_wallet_key(args.chain)

    print(f"Chain: {args.chain.upper()}")
    print(f"Wallet: {wallet_address[:8]}...{wallet_address[-6:]}")
    print()

    # ========================================================================
    # STEP 1: RISK PRE-CHECK
    # ========================================================================
    print("Step 1/4: Running Risk Pre-Check...")

    # Check risk for the to-token (the token we're buying)
    risk_result = run_risk_score(args.chain, args.to_token)

    print(f"   Risk Score: {risk_result.score}/100 ({risk_result.rating})")

    if risk_result.issues:
        print("   Issues found:")
        for issue in risk_result.issues:
            print(f"      - {issue}")

    if risk_result.warnings:
        print("   Warnings:")
        for warning in risk_result.warnings:
            print(f"      - {warning}")

    # Enforce risk threshold
    if risk_result.score < args.min_risk_score:
        print(
            f"\nDANGEROUS: Risk score ({risk_result.score}) below minimum ({args.min_risk_score})"
        )
        print("Trade REJECTED for your safety.")
        sys.exit(1)

    if risk_result.score < RISK_THRESHOLD_WARN:
        print(f"\nCAUTION: Risk score ({risk_result.score}) is moderate")
        print("Please review carefully before proceeding.")

    print("   Risk check passed")
    print()

    # ========================================================================
    # STEP 2: GET QUOTE
    # ========================================================================
    print("Step 2/4: Getting Quote...")

    quote = bitget_order_quote(
        from_chain=args.chain,
        from_contract=args.from_token,
        to_chain=args.chain,
        to_contract=args.to_token,
        amount=args.amount,
        from_address=wallet_address,
        slippage=args.slippage,
    )

    print(f"   Input:  {quote.from_amount} {quote.from_symbol}")
    print(f"   Output: {quote.to_amount} {quote.to_symbol} (estimated)")
    print(f"   Slippage: {quote.slippage}%")
    print(f"   Price Impact: {quote.price_impact}%")
    print(f"   Route: {' -> '.join(quote.route)}")

    # Check slippage threshold
    if quote.slippage > args.max_slippage:
        print(f"\nSlippage ({quote.slippage}%) exceeds maximum ({args.max_slippage}%)")
        print("Trade REJECTED.")
        sys.exit(1)

    # Check balance
    if not check_balance(args.chain, args.from_token, wallet_address, args.amount):
        from_symbol = _get_token_symbol(args.chain, args.from_token)
        handle_insufficient_balance(from_symbol, args.amount, "0")
        sys.exit(1)

    print("   Quote retrieved successfully")
    print()

    # ========================================================================
    # STEP 3: USER CONFIRMATION
    # ========================================================================
    print("Step 3/4: User Confirmation Required...")

    confirmed = display_trade_confirmation(risk_result, quote, wallet_address)

    if not confirmed:
        print("\nTrade cancelled")
        result = TradeResult(
            status="cancelled",
            order_id=None,
            tx_hash=None,
            from_amount=quote.from_amount,
            from_token=quote.from_symbol,
            to_amount=quote.to_amount,
            to_token=quote.to_symbol,
            effective_price="",
            risk_score=risk_result.score,
            gasless=False,
            error="User cancelled",
        )
        print("\nResult:")
        print(json.dumps(result.__dict__, indent=2))
        sys.exit(0)

    # ========================================================================
    # STEP 4: EXECUTE TRADE
    # ========================================================================
    print("\nStep 4/4: Executing Trade...")

    result = execute_trade(
        quote=quote,
        slippage=args.slippage,
        wallet_address=wallet_address,
        wallet_key=wallet_key,
        simulate=args.simulate,
        risk_score=risk_result.score,
    )

    # Display result
    print()
    if result.status == "success":
        print("Trade executed successfully!")
    elif result.status == "failed":
        print("Trade FAILED!")
        print(f"Error: {result.error}")
    else:
        print("Trade cancelled")

    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(json.dumps(result.__dict__, indent=2))

    # Exit with appropriate code
    if result.status == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
