#!/usr/bin/env python3
"""
Risk Scorer for Solana Meme Coin Trading Agent.

Calculates composite risk scores (0-100) by combining multiple data sources:
- RugCheck API: Security audit and risk factors
- Bitget Wallet API: Liquidity info, transaction stats, security audits

Scoring Formula:
    total = (security_score × 0.5) + (liquidity_score × 0.3) + (tx_score × 0.2)

Risk Thresholds:
    - SAFE: score ≥ 70
    - CAUTION: 40 ≤ score < 70
    - DANGEROUS: score < 40

Usage:
    python risk_scorer.py --chain sol --contract <TOKEN_MINT> --format json

Example:
    python risk_scorer.py --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configure logging - debug level for detailed troubleshooting
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# API Configuration
# ============================================================================

# RugCheck API endpoint for Solana token risk reports
RUGCHECK_BASE_URL = "https://api.rugcheck.xyz/v1/tokens"

# Bitget Wallet API - imports from existing module
# Uses built-in demo credentials or env var override
BGW_BASE_URL = "https://bopenapi.bgwapi.io"
DEFAULT_BGW_API_KEY = "4843D8C3F1E20772C0E634EDACC5C5F9A0E2DC92"
DEFAULT_BGW_API_SECRET = "F2ABFDC684BDC6775FD6286B8D06A3AAD30FD587"

# Request timeouts (seconds)
API_TIMEOUT = 30
RUGCHECK_TIMEOUT = 15
BGW_TIMEOUT = 30

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class RiskBreakdown:
    """Individual risk component scores."""

    security: float = 0.0
    liquidity: float = 0.0
    tx: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            "security": round(self.security, 2),
            "liquidity": round(self.liquidity, 2),
            "tx": round(self.tx, 2),
        }


@dataclass
class RiskReport:
    """Complete risk assessment report."""

    score: int = 0
    rating: str = "unknown"
    breakdown: RiskBreakdown = field(default_factory=RiskBreakdown)
    risks: List[str] = field(default_factory=list)
    recommendation: str = "UNKNOWN"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "rating": self.rating,
            "breakdown": self.breakdown.to_dict(),
            "risks": self.risks,
            "recommendation": self.recommendation,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ============================================================================
# Input Validation
# ============================================================================


def validate_contract_address(contract: str, chain: str) -> Tuple[bool, str]:
    """
    Validate contract address format based on blockchain.

    Args:
        contract: Contract address to validate
        chain: Blockchain name (sol, eth, bnb, etc.)

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_contract_address("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "sol")
        (True, "")
        >>> validate_contract_address("invalid", "sol")
        (False, "Invalid Solana address format")
    """
    if not contract or not contract.strip():
        return False, "Contract address cannot be empty"

    contract = contract.strip()
    chain = chain.lower()

    if chain == "sol":
        # Solana addresses are base58 encoded, 32-44 characters
        # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
        base58_pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
        if not re.match(base58_pattern, contract):
            return False, "Invalid Solana address format (expected base58, 32-44 chars)"

    elif chain in ("eth", "bnb", "base", "arbitrum", "polygon", "optimism"):
        # EVM addresses are 0x-prefixed, 40 hex characters
        if not re.match(r"^0x[a-fA-F0-9]{40}$", contract):
            return False, "Invalid EVM address format (expected 0x + 40 hex chars)"

    # For other chains, accept non-empty strings
    if len(contract) < 10:
        return False, "Contract address too short"

    return True, ""


def validate_chain(chain: str) -> Tuple[bool, str]:
    """
    Validate chain parameter.

    Args:
        chain: Blockchain name

    Returns:
        Tuple of (is_valid, error_message)
    """
    supported_chains = [
        "sol",
        "eth",
        "bnb",
        "base",
        "arbitrum",
        "polygon",
        "optimism",
        "avalanche",
        "fantom",
        "tron",
        "sui",
    ]

    if chain.lower() not in supported_chains:
        return (
            False,
            f"Unsupported chain '{chain}'. Supported: {', '.join(supported_chains)}",
        )

    return True, ""


# ============================================================================
# RugCheck API Integration
# ============================================================================


def fetch_rugcheck_report(
    mint_address: str, timeout: int = RUGCHECK_TIMEOUT
) -> Dict[str, Any]:
    """
    Fetch token risk report from RugCheck API.

    RugCheck provides comprehensive security analysis for Solana tokens including:
    - Mint authority status
    - Freeze authority status
    - LP lock status
    - Holder distribution
    - Known risk patterns

    Args:
        mint_address: Solana token mint address
        timeout: Request timeout in seconds

    Returns:
        Dict containing RugCheck report data

    Raises:
        requests.RequestException: On network errors
        KeyError: On malformed API response

    Example:
        >>> report = fetch_rugcheck_report("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        >>> print(report.get("score"))  # Risk score 0-100
    """
    url = f"{RUGCHECK_BASE_URL}/{mint_address}/report"

    logger.debug(f"Fetching RugCheck report from: {url}")

    response = requests.get(
        url,
        timeout=timeout,
        headers={"Accept": "application/json", "User-Agent": "RiskScorer/1.0"},
    )

    response.raise_for_status()
    return response.json()


def compute_security_score(rugcheck_data: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Compute security score from RugCheck report.

    The security score is derived from:
    - Direct risk score from RugCheck (if available)
    - Computed from individual risk factors

    Args:
        rugcheck_data: Raw RugCheck API response

    Returns:
        Tuple of (security_score 0-100, list of identified risks)

    Example:
        >>> score, risks = compute_security_score({"score": 85, "risks": [...]})
        >>> print(score)  # 85.0
    """
    risks = []
    score = 0.0

    # Try to get direct score from RugCheck
    rugcheck_score = rugcheck_data.get("score")

    if rugcheck_score is not None:
        # RugCheck score is already 0-100 (higher = safer)
        score = float(rugcheck_score)
    else:
        # Compute score from risk factors
        score = 100.0  # Start with perfect score, deduct for risks

        # Check mint authority (high risk if enabled)
        mint_auth = rugcheck_data.get("mintAuthority")
        if mint_auth is not None and mint_auth is True:
            score -= 40
            risks.append("mint_authority_enabled")
            logger.warning("Mint authority still enabled - high risk!")

        # Check freeze authority (high risk if enabled)
        freeze_auth = rugcheck_data.get("freezeAuthority")
        if freeze_auth is not None and freeze_auth is True:
            score -= 30
            risks.append("freeze_authority_enabled")
            logger.warning("Freeze authority still enabled - high risk!")

        # Check LP lock status
        lp_status = rugcheck_data.get("lpLocked")
        if lp_status is False:
            score -= 35
            risks.append("lp_unlocked")
            logger.warning("Liquidity pool is unlocked - rug pull risk!")

        # Check for top holder concentration
        top_holders = rugcheck_data.get("topHoldersPercent", 0)
        if top_holders > 50:
            score -= 25
            risks.append("high_concentration")
            logger.warning(f"High holder concentration: {top_holders}%")
        elif top_holders > 30:
            score -= 15
            risks.append("medium_concentration")

        # Check token age (newer = riskier)
        token_age_hours = rugcheck_data.get("ageHours", 999)
        if token_age_hours < 24:
            score -= 20
            risks.append("very_new_token")
        elif token_age_hours < 72:
            score -= 10
            risks.append("new_token")

        # Ensure score stays in valid range
        score = max(0.0, min(100.0, score))

    return score, risks


# ============================================================================
# Bitget Wallet API Integration
# ============================================================================


def get_bgw_credentials() -> Tuple[str, str]:
    """
    Get Bitget Wallet API credentials.

    Priority:
    1. Environment variables (BGW_API_KEY, BGW_API_SECRET)
    2. Built-in demo credentials

    Returns:
        Tuple of (api_key, api_secret)
    """
    api_key = os.environ.get("BGW_API_KEY", DEFAULT_BGW_API_KEY)
    api_secret = os.environ.get("BGW_API_SECRET", DEFAULT_BGW_API_SECRET)
    return api_key, api_secret


def bgw_request(
    path: str, body: Dict[str, Any], timeout: int = BGW_TIMEOUT
) -> Dict[str, Any]:
    """
    Make authenticated request to Bitget Wallet API.

    Uses HMAC-SHA256 signature per Bitget Wallet documentation.

    Args:
        path: API endpoint path (e.g., "/bgw-pro/market/v3/coin/security/audits")
        body: Request body dictionary
        timeout: Request timeout in seconds

    Returns:
        Dict containing API response

    Raises:
        requests.RequestException: On network errors
    """
    import base64
    import hashlib
    import hmac
    import time

    api_key, api_secret = get_bgw_credentials()
    timestamp = str(int(time.time() * 1000))
    body_str = json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""

    # Generate signature
    content = {
        "apiPath": path,
        "body": body_str,
        "x-api-key": api_key,
        "x-api-timestamp": timestamp,
    }
    sorted_content = dict(sorted(content.items()))
    payload = json.dumps(sorted_content, separators=(",", ":"))
    signature = base64.b64encode(
        hmac.new(api_secret.encode(), payload.encode(), hashlib.sha256).digest()
    ).decode()

    # Make request
    url = f"{BGW_BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "x-api-timestamp": timestamp,
        "x-api-signature": signature,
    }

    logger.debug(f"Making BGW API request to: {url}")

    response = requests.post(
        url, data=body_str if body_str else None, headers=headers, timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def fetch_bitget_security(chain: str, contract: str) -> Dict[str, Any]:
    """
    Fetch security audit data from Bitget Wallet API.

    Args:
        chain: Blockchain name
        contract: Token contract address

    Returns:
        Dict containing security audit results
    """
    body = {"list": [{"chain": chain, "contract": contract}], "source": "bg"}

    try:
        result = bgw_request("/bgw-pro/market/v3/coin/security/audits", body)
        return result
    except Exception as e:
        logger.error(f"Bitget security API error: {e}")
        return {"error": str(e)}


def fetch_bitget_tx_info(chain: str, contract: str) -> Dict[str, Any]:
    """
    Fetch transaction statistics from Bitget Wallet API.

    Returns 24h volume, buyer/seller counts, holder info.

    Args:
        chain: Blockchain name
        contract: Token contract address

    Returns:
        Dict containing transaction statistics
    """
    body = {"chain": chain, "contract": contract}

    try:
        result = bgw_request("/bgw-pro/market/v3/coin/getTxInfo", body)
        return result
    except Exception as e:
        logger.error(f"Bitget tx info API error: {e}")
        return {"error": str(e)}


def fetch_bitget_liquidity(chain: str, contract: str) -> Dict[str, Any]:
    """
    Fetch liquidity pool information from Bitget Wallet API.

    Args:
        chain: Blockchain name
        contract: Token contract address

    Returns:
        Dict containing liquidity pool data
    """
    body = {"chain": chain, "contract": contract}

    try:
        result = bgw_request("/bgw-pro/market/v3/poolList", body)
        return result
    except Exception as e:
        logger.error(f"Bitget liquidity API error: {e}")
        return {"error": str(e)}


def compute_liquidity_score(
    liquidity_data: Dict[str, Any], tx_data: Dict[str, Any]
) -> Tuple[float, List[str]]:
    """
    Compute liquidity score from Bitget data.

    Factors:
    - LP locked percentage
    - Pool size (total liquidity)
    - Holder count
    - 24h volume

    Args:
        liquidity_data: Liquidity pool data from Bitget
        tx_data: Transaction statistics from Bitget

    Returns:
        Tuple of (liquidity_score 0-100, list of warnings)
    """
    score = 0.0
    warnings = []

    # Extract pool data
    pools = liquidity_data.get("data", {}).get("list", [])

    if not pools:
        warnings.append("no_liquidity_pools_found")
        return 0.0, warnings

    # Calculate total liquidity
    total_liquidity_usd = sum(pool.get("liquidityUsd", 0) for pool in pools)

    # Liquidity score based on pool size
    # $1M+ = 100, $100K+ = 70, $10K+ = 40, <$10K = 20
    if total_liquidity_usd >= 1_000_000:
        score += 40
    elif total_liquidity_usd >= 100_000:
        score += 30
    elif total_liquidity_usd >= 10_000:
        score += 20
    else:
        score += 10
        warnings.append("low_liquidity")

    # Holder count score (max 30 points)
    holder_count = tx_data.get("data", {}).get("holders", 0)
    if holder_count >= 10000:
        score += 30
    elif holder_count >= 1000:
        score += 25
    elif holder_count >= 100:
        score += 20
    elif holder_count >= 10:
        score += 10
    else:
        score += 5
        warnings.append("low_holders")

    # LP lock percentage (max 30 points)
    # Check if pools are locked
    locked_ratio = 0.0
    for pool in pools:
        lock_info = pool.get("lockInfo", {})
        if lock_info.get("locked", False):
            locked_ratio += 1.0

    if pools:
        locked_ratio /= len(pools)

    score += locked_ratio * 30

    if locked_ratio < 0.5:
        warnings.append("partial_lp_unlock")
    if locked_ratio == 0:
        warnings.append("no_lp_locked")

    return min(100.0, score), warnings


def compute_tx_score(tx_data: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Compute transaction score from Bitget data.

    Factors:
    - 24h trading volume
    - Buyer/seller ratio (healthy = balanced)
    - Transaction count

    Args:
        tx_data: Transaction statistics from Bitget

    Returns:
        Tuple of (tx_score 0-100, list of warnings)
    """
    score = 0.0
    warnings = []

    data = tx_data.get("data", {})

    # 24h volume score (max 40 points)
    volume_24h = data.get("volume24h", 0)
    if volume_24h >= 1_000_000:
        score += 40
    elif volume_24h >= 100_000:
        score += 35
    elif volume_24h >= 10_000:
        score += 25
    elif volume_24h >= 1_000:
        score += 15
    else:
        score += 5
        warnings.append("low_volume")

    # Buyer/seller ratio (max 30 points)
    # Healthy ratio: 0.7-1.3 (balanced)
    buyers = data.get("buyCount24h", 0)
    sellers = data.get("sellCount24h", 0)

    if buyers == 0 and sellers == 0:
        score += 0
        warnings.append("no_transactions")
    elif buyers == 0 or sellers == 0:
        score += 5
        warnings.append("one_sided_trading")
    else:
        ratio = buyers / sellers
        if 0.7 <= ratio <= 1.3:
            score += 30  # Healthy balance
        elif 0.5 <= ratio < 0.7 or 1.3 < ratio <= 1.5:
            score += 20  # Slight imbalance
        else:
            score += 10  # Significant imbalance
            warnings.append("unusual_buy_sell_ratio")

    # Transaction count consistency (max 30 points)
    tx_count = data.get("txCount24h", 0)
    if tx_count >= 1000:
        score += 30
    elif tx_count >= 100:
        score += 25
    elif tx_count >= 10:
        score += 15
    elif tx_count > 0:
        score += 5
    else:
        warnings.append("no_recent_transactions")

    return min(100.0, score), warnings


# ============================================================================
# Risk Calculation and Rating
# ============================================================================


def calculate_composite_score(breakdown: RiskBreakdown) -> int:
    """
    Calculate composite risk score using weighted formula.

    Formula:
        total = (security × 0.5) + (liquidity × 0.3) + (tx × 0.2)

    Args:
        breakdown: Individual risk component scores

    Returns:
        Composite score (0-100)

    Example:
        >>> b = RiskBreakdown(security=90, liquidity=75, tx=80)
        >>> calculate_composite_score(b)
        83
    """
    score = breakdown.security * 0.5 + breakdown.liquidity * 0.3 + breakdown.tx * 0.2
    return round(score)


def get_rating(score: int) -> str:
    """
    Get risk rating label from score.

    Args:
        score: Composite risk score (0-100)

    Returns:
        Rating string: "safe", "caution", or "dangerous"

    Thresholds:
        - SAFE: score ≥ 70
        - CAUTION: 40 ≤ score < 70
        - DANGEROUS: score < 40
    """
    if score >= 70:
        return "safe"
    elif score >= 40:
        return "caution"
    else:
        return "dangerous"


def get_recommendation(rating: str, risks: List[str]) -> str:
    """
    Get trading recommendation based on rating and risks.

    Args:
        rating: Risk rating ("safe", "caution", "dangerous")
        risks: List of identified risk factors

    Returns:
        Recommendation string
    """
    if rating == "safe":
        if not risks or len(risks) < 2:
            return "SAFE_TO_TRADE"
        else:
            return "SAFE_WITH_CAUTION"
    elif rating == "caution":
        return "REDUCE_POSITION_SIZE"
    else:  # dangerous
        return "AVOID_HIGH_RISK"


# ============================================================================
# Main Risk Scoring Function
# ============================================================================


def calculate_risk_score(
    chain: str, contract: str, use_fallback: bool = True
) -> RiskReport:
    """
    Calculate comprehensive risk score for a token.

    Combines data from multiple sources:
    1. RugCheck API (security audit)
    2. Bitget Wallet API (liquidity, transaction stats)

    Args:
        chain: Blockchain name (sol, eth, bnb, etc.)
        contract: Token contract address
        use_fallback: If True, continue with partial data if API fails

    Returns:
        RiskReport with composite score and breakdown

    Example:
        >>> report = calculate_risk_score("sol", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        >>> print(report.score)  # 0-100
        >>> print(report.rating)  # "safe", "caution", or "dangerous"
    """
    report = RiskReport()
    breakdown = RiskBreakdown()
    all_risks = []
    all_warnings = []

    # Validate inputs
    valid, error = validate_chain(chain)
    if not valid:
        report.errors.append(error)
        return report

    valid, error = validate_contract_address(contract, chain)
    if not valid:
        report.errors.append(error)
        return report

    # ========================================================================
    # 1. Security Score (50% weight) - RugCheck API
    # ========================================================================
    logger.info(f"Fetching security data for {chain}:{contract}")

    try:
        if chain == "sol":
            rugcheck_data = fetch_rugcheck_report(contract)
            security_score, sec_risks = compute_security_score(rugcheck_data)
            breakdown.security = security_score
            all_risks.extend(sec_risks)
            logger.info(f"Security score: {security_score:.2f}")
        else:
            # For non-Solana chains, use Bitget security audit
            bgw_security = fetch_bitget_security(chain, contract)
            if "error" not in bgw_security:
                # Extract score from Bitget security audit
                # Response format varies: sometimes data is a list directly
                data = bgw_security.get("data", {})
                if isinstance(data, list):
                    audit_list = data
                else:
                    audit_list = data.get("list", [])

                if audit_list:
                    audit = audit_list[0]
                    if isinstance(audit, dict):
                        # Bitget returns risk level: safe, warning, danger
                        risk_level = audit.get("riskLevel", "unknown")
                        if risk_level == "safe":
                            breakdown.security = 90
                        elif risk_level == "warning":
                            breakdown.security = 50
                            all_risks.append("bitget_warning")
                        else:
                            breakdown.security = 20
                            all_risks.append("bitget_danger")
            else:
                report.warnings.append("Security API unavailable")
                if use_fallback:
                    breakdown.security = 50.0  # Neutral score
    except requests.Timeout:
        error_msg = "RugCheck API timeout"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.security = 50.0
            all_warnings.append("security_api_timeout")
    except requests.RequestException as e:
        error_msg = f"RugCheck API error: {e}"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.security = 50.0
            all_warnings.append("security_api_error")

    # ========================================================================
    # 2. Liquidity Score (30% weight) - Bitget Wallet API
    # ========================================================================
    logger.info(f"Fetching liquidity data for {chain}:{contract}")

    liq_score = 50.0
    liq_warnings: List[str] = []
    tx_score = 50.0
    tx_warnings: List[str] = []
    liquidity_data: Dict[str, Any] = {}
    tx_data: Dict[str, Any] = {}

    try:
        liquidity_data = fetch_bitget_liquidity(chain, contract)
        tx_data = fetch_bitget_tx_info(chain, contract)

        liq_score, liq_warnings = compute_liquidity_score(liquidity_data, tx_data)
        breakdown.liquidity = liq_score
        all_warnings.extend(liq_warnings)
        logger.info(f"Liquidity score: {liq_score:.2f}")

    except requests.Timeout:
        error_msg = "Bitget liquidity API timeout"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.liquidity = 50.0
            all_warnings.append("liquidity_api_timeout")
    except requests.RequestException as e:
        error_msg = f"Bitget liquidity API error: {e}"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.liquidity = 50.0
            all_warnings.append("liquidity_api_error")

    # ========================================================================
    # 3. Transaction Score (20% weight) - Bitget Wallet API
    # ========================================================================
    logger.info(f"Fetching transaction data for {chain}:{contract}")

    try:
        # Use tx_data if already fetched, otherwise fetch it
        if not tx_data:
            tx_data = fetch_bitget_tx_info(chain, contract)

        tx_score, tx_warnings = compute_tx_score(tx_data)
        breakdown.tx = tx_score
        all_warnings.extend(tx_warnings)
        logger.info(f"Transaction score: {tx_score:.2f}")

    except requests.Timeout:
        error_msg = "Bitget transaction API timeout"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.tx = 50.0
            all_warnings.append("tx_api_timeout")
    except requests.RequestException as e:
        error_msg = f"Bitget transaction API error: {e}"
        logger.error(error_msg)
        report.errors.append(error_msg)
        if use_fallback:
            breakdown.tx = 50.0
            all_warnings.append("tx_api_error")

    # ========================================================================
    # Calculate Composite Score
    # ========================================================================
    report.breakdown = breakdown
    report.score = calculate_composite_score(breakdown)
    report.rating = get_rating(report.score)
    report.risks = all_risks
    report.warnings = all_warnings
    report.recommendation = get_recommendation(report.rating, all_risks)

    logger.info(f"Final score: {report.score} ({report.rating})")

    return report


# ============================================================================
# CLI Interface
# ============================================================================


def format_output_json(report: RiskReport) -> str:
    """Format report as JSON string."""
    return json.dumps(report.to_dict(), indent=2)


def format_output_text(report: RiskReport, chain: str, contract: str) -> str:
    """
    Format report as human-readable text.

    Example output:
        Risk Score: 85/100 (SAFE)
        Chain: sol
        Contract: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

        Breakdown:
          Security:  90/100
          Liquidity: 75/100
          Tx Score:  80/100

        Risks: high_concentration, mint_authority
        Recommendation: SAFE_TO_TRADE
    """
    lines = [
        f"Risk Score: {report.score}/100 ({report.rating.upper()})",
        f"Chain: {chain}",
        f"Contract: {contract}",
        "",
        "Breakdown:",
        f"  Security:  {report.breakdown.security:5.1f}/100",
        f"  Liquidity: {report.breakdown.liquidity:5.1f}/100",
        f"  Tx Score:  {report.breakdown.tx:5.1f}/100",
        "",
    ]

    if report.risks:
        lines.append(f"Risks: {', '.join(report.risks)}")
    else:
        lines.append("Risks: None identified")

    if report.warnings:
        lines.append(f"Warnings: {', '.join(report.warnings)}")

    lines.extend(
        [
            "",
            f"Recommendation: {report.recommendation}",
        ]
    )

    if report.errors:
        lines.extend(
            [
                "",
                "Errors:",
            ]
        )
        for error in report.errors:
            lines.append(f"  - {error}")

    return "\n".join(lines)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Risk Scorer for Solana Meme Coin Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
  %(prog)s --chain eth --contract 0x1234567890abcdef1234567890abcdef12345678 --format text
  %(prog)s -c sol -t EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v -f json

Risk Thresholds:
  SAFE:      score ≥ 70
  CAUTION:   40 ≤ score < 70
  DANGEROUS: score < 40

Scoring Formula:
  total = (security × 0.5) + (liquidity × 0.3) + (tx × 0.2)
        """,
    )

    parser.add_argument(
        "--chain",
        "-c",
        required=True,
        type=str,
        help="Blockchain name (required): sol, eth, bnb, base, etc.",
    )

    parser.add_argument(
        "--contract",
        "-t",
        required=True,
        type=str,
        help="Token contract address (required)",
    )

    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail immediately on API errors (default: use fallback scores)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging to stderr"
    )

    return parser


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    logger.info(f"Starting risk assessment for {args.chain}:{args.contract}")

    try:
        # Calculate risk score
        report = calculate_risk_score(
            chain=args.chain, contract=args.contract, use_fallback=not args.no_fallback
        )

        # Format and output result
        if args.format == "json":
            print(format_output_json(report))
        else:
            print(format_output_text(report, args.chain, args.contract))

        # Return appropriate exit code
        if report.errors and not report.score:
            return 1
        return 0

    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
