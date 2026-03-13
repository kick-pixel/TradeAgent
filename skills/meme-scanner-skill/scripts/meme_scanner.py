#!/usr/bin/env python3
"""
Meme Scanner - Discover trending meme coins with automatic risk filtering.

Fetches trending tokens from Bitget Wallet API, applies risk filters,
and ranks by risk-adjusted scores to identify safe high-potential meme coins.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests


# =============================================================================
# Configuration
# =============================================================================

BITGET_API_BASE = "https://openapi.bitget.com"
BITGET_V2_BASE = "https://api.bitget.com/v2"

CHAIN_MAPPING = {
    "sol": "solana",
    "eth": "ethereum",
    "bsc": "bsc",
    "base": "base",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TokenInfo:
    """Token information from API."""

    symbol: str
    name: str
    address: str
    chain: str
    price_usd: float
    price_change_24h: float
    liquidity_usd: float
    holders: int
    age_hours: float
    volume_24h: float = 0.0
    market_cap: float = 0.0
    risk_score: int = 0
    adjusted_score: float = 0.0
    security_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "address": self.address,
            "chain": self.chain,
            "price_usd": self.price_usd,
            "price_change_24h": self.price_change_24h,
            "liquidity_usd": self.liquidity_usd,
            "holders": self.holders,
            "age_hours": self.age_hours,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "risk_score": self.risk_score,
            "adjusted_score": round(self.adjusted_score, 2),
            "security_flags": self.security_flags,
        }


@dataclass
class ScanResult:
    """Results from a meme coin scan."""

    tokens: list[TokenInfo]
    total_scanned: int
    passed_filters: int
    filtered_out: int
    scan_time_seconds: float
    filters_applied: dict[str, Any]


# =============================================================================
# API Client
# =============================================================================


class BitgetWalletAPI:
    """Client for Bitget Wallet API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "MemeScanner/1.0",
            }
        )

    def fetch_rankings(
        self, ranking_name: str = "topGainers", chain: str = "solana", limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Fetch token rankings from Bitget Wallet.

        Args:
            ranking_name: 'topGainers' or 'Hotpicks'
            chain: Chain identifier
            limit: Max number of results

        Returns:
            List of token data dictionaries
        """
        try:
            # Try the rankings endpoint
            url = f"{BITGET_V2_BASE}/wallet/token/rankings"
            params = {
                "name": ranking_name,
                "chain": chain,
                "limit": limit,
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "00000" and "data" in data:
                return data["data"].get("tokens", [])

            # Fallback: Try alternative endpoint structure
            if "data" in data and isinstance(data["data"], list):
                return data["data"][:limit]

            return []

        except requests.exceptions.RequestException as e:
            print(f"⚠️  API request failed for {ranking_name}: {e}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse API response: {e}", file=sys.stderr)
            return []

    def fetch_token_info(
        self, token_address: str, chain: str = "solana"
    ) -> Optional[dict[str, Any]]:
        """Fetch detailed token information."""
        try:
            url = f"{BITGET_V2_BASE}/wallet/token/info"
            params = {
                "contractAddress": token_address,
                "chain": chain,
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "00000":
                return data.get("data", {})
            return None

        except requests.exceptions.RequestException:
            return None
        except json.JSONDecodeError:
            return None

    def fetch_security_check(
        self, token_address: str, chain: str = "solana"
    ) -> dict[str, Any]:
        """Fetch security analysis for a token."""
        try:
            url = f"{BITGET_V2_BASE}/wallet/token/security"
            params = {
                "contractAddress": token_address,
                "chain": chain,
            }

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "00000":
                return data.get("data", {})
            return {"risk_level": "unknown", "flags": []}

        except requests.exceptions.RequestException:
            return {"risk_level": "unknown", "flags": ["api_error"]}
        except json.JSONDecodeError:
            return {"risk_level": "unknown", "flags": ["parse_error"]}


# =============================================================================
# Risk Scorer Integration
# =============================================================================


def calculate_risk_score(
    token_data: dict[str, Any], security_info: dict[str, Any]
) -> tuple[int, list[str]]:
    """
    Calculate risk score for a token (0-100, higher is safer).

    Uses multiple risk factors:
    - Security flags from API
    - Liquidity level
    - Holder count
    - Token age
    - Price volatility

    Returns:
        Tuple of (risk_score, list_of_flags)
    """
    score = 100
    flags = []

    # Security analysis flags (major deductions)
    security_risk = security_info.get("risk_level", "unknown")
    if security_risk == "high":
        score -= 50
        flags.append("high_risk_security")
    elif security_risk == "medium":
        score -= 25
        flags.append("medium_risk_security")

    # Check specific security issues
    if security_info.get("is_honeypot"):
        score -= 40
        flags.append("honeypot_detected")
    if security_info.get("mint_function"):
        score -= 20
        flags.append("mint_function")
    if security_info.get("proxy_contract"):
        score -= 10
        flags.append("proxy_contract")
    if not security_info.get("liquidity_locked", True):
        score -= 30
        flags.append("unlocked_liquidity")
    if security_info.get("owner_can_trade", False) is False:
        score -= 15
        flags.append("trading_restricted")

    # Liquidity risk
    liquidity = token_data.get("liquidity_usd", 0)
    if liquidity < 5000:
        score -= 20
        flags.append("very_low_liquidity")
    elif liquidity < 10000:
        score -= 10
        flags.append("low_liquidity")

    # Holder concentration risk
    holders = token_data.get("holders", 0)
    if holders < 50:
        score -= 15
        flags.append("few_holders")
    elif holders < 100:
        score -= 5
        flags.append("low_holders")

    # Age risk (newer = riskier)
    age_hours = token_data.get("age_hours", 0)
    if age_hours < 1:
        score -= 25
        flags.append("very_new_token")
    elif age_hours < 6:
        score -= 10
        flags.append("new_token")
    elif age_hours < 24:
        score -= 5
        flags.append("recent_token")

    # Volatility risk (extreme gains can indicate pumps)
    price_change = abs(token_data.get("price_change_24h", 0))
    if price_change > 500:
        score -= 15
        flags.append("extreme_volatility")
    elif price_change > 200:
        score -= 10
        flags.append("high_volatility")

    # Ensure score is in valid range
    score = max(0, min(100, score))

    return score, flags


# =============================================================================
# Filtering and Scoring
# =============================================================================


def parse_token_data(
    raw_data: dict[str, Any], chain: str, security_info: dict[str, Any]
) -> Optional[TokenInfo]:
    """Parse raw API data into TokenInfo object."""
    try:
        # Extract common fields with fallbacks
        symbol = raw_data.get("symbol", "UNKNOWN")
        name = raw_data.get("name", "Unknown Token")
        address = raw_data.get("contractAddress", raw_data.get("address", ""))

        # Price data
        price_usd = float(raw_data.get("price", 0) or 0)
        price_change = float(raw_data.get("priceChange24h", 0) or 0)

        # Liquidity and holders
        liquidity = float(raw_data.get("liquidity", 0) or 0)
        holders = int(raw_data.get("holders", 0) or 0)

        # Volume and market cap
        volume_24h = float(raw_data.get("volume24h", 0) or 0)
        market_cap = float(raw_data.get("marketCap", 0) or 0)

        # Age calculation (if timestamp provided)
        created_at = raw_data.get("createdAt", raw_data.get("timestamp"))
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_hours = (
                    datetime.now(created_time.tzinfo) - created_time
                ).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0.0
        else:
            age_hours = raw_data.get("ageHours", 0.0)

        # Calculate risk score
        token_temp = {
            "liquidity_usd": liquidity,
            "holders": holders,
            "age_hours": age_hours,
            "price_change_24h": price_change,
        }
        risk_score, flags = calculate_risk_score(token_temp, security_info)

        return TokenInfo(
            symbol=symbol,
            name=name,
            address=address,
            chain=chain,
            price_usd=price_usd,
            price_change_24h=price_change,
            liquidity_usd=liquidity,
            holders=holders,
            age_hours=age_hours,
            volume_24h=volume_24h,
            market_cap=market_cap,
            risk_score=risk_score,
            security_flags=flags,
        )
    except (ValueError, KeyError, TypeError) as e:
        print(f"⚠️  Failed to parse token data: {e}", file=sys.stderr)
        return None


def filter_tokens(
    tokens: list[TokenInfo],
    min_liquidity: float,
    min_holders: int,
    min_age_hours: float,
) -> list[TokenInfo]:
    """Apply basic filters to token list."""
    filtered = []
    for token in tokens:
        if token.liquidity_usd >= min_liquidity:
            if token.holders >= min_holders:
                if token.age_hours >= min_age_hours:
                    filtered.append(token)
    return filtered


def calculate_adjusted_scores(tokens: list[TokenInfo]) -> list[TokenInfo]:
    """
    Calculate risk-adjusted scores for tokens.

    Formula: adjusted_score = (price_change_24h * risk_score) / 100

    This balances gains against safety - a 100% gain with 90 score
    beats a 200% gain with 30 score.
    """
    for token in tokens:
        # Use positive price change only for scoring
        gain = max(0, token.price_change_24h)
        token.adjusted_score = (gain * token.risk_score) / 100
    return tokens


# =============================================================================
# Output Formatting
# =============================================================================


def format_table(tokens: list[TokenInfo]) -> str:
    """Format tokens as ASCII table."""
    if not tokens:
        return "No tokens matched the criteria."

    lines = []
    lines.append("=== Trending Meme Coins (Risk-Filtered) ===")
    lines.append("")

    # Header
    header = (
        "Rank | Symbol | Price Change | Liquidity  | Holders | Risk Score | Adjusted"
    )
    separator = (
        "-----+--------+--------------+------------+---------+------------+----------"
    )
    lines.append(header)
    lines.append(separator)

    # Rows
    for i, token in enumerate(tokens, 1):
        symbol = token.symbol[:6] if len(token.symbol) > 6 else token.symbol

        # Format price change with color indicators
        change = token.price_change_24h
        if change >= 0:
            change_str = f"+{change:.1f}%"
        else:
            change_str = f"{change:.1f}%"

        # Format liquidity
        if token.liquidity_usd >= 1_000_000:
            liq_str = f"${token.liquidity_usd / 1_000_000:.1f}M"
        elif token.liquidity_usd >= 1_000:
            liq_str = f"${token.liquidity_usd / 1_000:.0f}K"
        else:
            liq_str = f"${token.liquidity_usd:.0f}"

        row = (
            f"{i:>4} | {symbol:<6} | {change_str:>12} | {liq_str:>10} | "
            f"{token.holders:>7} | {token.risk_score:>10} | {token.adjusted_score:>8.1f}"
        )
        lines.append(row)

    return "\n".join(lines)


def format_statistics(result: ScanResult) -> str:
    """Format scan statistics."""
    lines = []
    lines.append("")
    lines.append(
        f"🔍 Scanned: {result.total_scanned} coins | "
        f"🟢 Passed: {result.passed_filters} | "
        f"🔴 Filtered: {result.filtered_out}"
    )
    lines.append(
        f"⏱️  Scan time: {result.scan_time_seconds:.2f}s | "
        f"⛓️  Chain: {result.filters_applied.get('chain', 'unknown')}"
    )
    lines.append("")
    lines.append("Filter criteria:")
    lines.append(
        f"  • Min liquidity: ${result.filters_applied.get('min_liquidity', 0):,.0f}"
    )
    lines.append(f"  • Min holders: {result.filters_applied.get('min_holders', 0)}")
    lines.append(f"  • Min age: {result.filters_applied.get('min_age_hours', 0):.1f}h")
    lines.append(f"  • Min risk score: {result.filters_applied.get('min_score', 0)}")
    return "\n".join(lines)


def format_json_output(result: ScanResult) -> str:
    """Format results as JSON."""
    output = {
        "scan_time": datetime.now().isoformat(),
        "statistics": {
            "total_scanned": result.total_scanned,
            "passed_filters": result.passed_filters,
            "filtered_out": result.filtered_out,
            "scan_duration_seconds": round(result.scan_time_seconds, 2),
        },
        "filters_applied": result.filters_applied,
        "tokens": [token.to_dict() for token in result.tokens],
    }
    return json.dumps(output, indent=2)


# =============================================================================
# Main Scanner
# =============================================================================


class MemeScanner:
    """Main scanner class orchestrating the meme coin discovery."""

    def __init__(
        self,
        min_liquidity: float,
        min_score: int,
        min_holders: int,
        min_age_hours: float,
        limit: int,
        chain: str,
        api_key: Optional[str] = None,
    ):
        self.min_liquidity = min_liquidity
        self.min_score = min_score
        self.min_holders = min_holders
        self.min_age_hours = min_age_hours
        self.limit = limit
        self.chain = chain
        self.api = BitgetWalletAPI(api_key)

    def scan(self) -> ScanResult:
        """Execute the full scanning pipeline."""
        start_time = time.time()

        # Map chain name
        chain_id = CHAIN_MAPPING.get(self.chain, self.chain)

        # Step 1: Fetch candidates from multiple ranking sources
        all_candidates = []

        # Fetch top gainers
        top_gainers = self.api.fetch_rankings("topGainers", chain_id, limit=50)
        all_candidates.extend(top_gainers)

        # Fetch hot picks
        hot_picks = self.api.fetch_rankings("Hotpicks", chain_id, limit=50)
        all_candidates.extend(hot_picks)

        # Remove duplicates by address
        seen_addresses = set()
        unique_candidates = []
        for candidate in all_candidates:
            address = candidate.get("contractAddress", candidate.get("address", ""))
            if address and address not in seen_addresses:
                seen_addresses.add(address)
                unique_candidates.append(candidate)

        total_scanned = len(unique_candidates)

        # Step 2: Parse and get security info for each candidate
        parsed_tokens = []
        for candidate in unique_candidates:
            address = candidate.get("contractAddress", candidate.get("address", ""))
            security_info = self.api.fetch_security_check(address, chain_id)

            token = parse_token_data(candidate, self.chain, security_info)
            if token:
                parsed_tokens.append(token)

        # Step 3: Apply filters
        filtered_tokens = filter_tokens(
            parsed_tokens,
            self.min_liquidity,
            self.min_holders,
            self.min_age_hours,
        )

        # Step 4: Filter by minimum risk score
        safe_tokens = [t for t in filtered_tokens if t.risk_score >= self.min_score]

        # Step 5: Calculate risk-adjusted scores
        scored_tokens = calculate_adjusted_scores(safe_tokens)

        # Step 6: Sort by adjusted score (descending)
        sorted_tokens = sorted(
            scored_tokens, key=lambda t: t.adjusted_score, reverse=True
        )

        # Step 7: Limit results
        final_tokens = sorted_tokens[: self.limit]

        scan_time = time.time() - start_time

        return ScanResult(
            tokens=final_tokens,
            total_scanned=total_scanned,
            passed_filters=len(final_tokens),
            filtered_out=total_scanned - len(final_tokens),
            scan_time_seconds=scan_time,
            filters_applied={
                "chain": self.chain,
                "min_liquidity": self.min_liquidity,
                "min_holders": self.min_holders,
                "min_age_hours": self.min_age_hours,
                "min_score": self.min_score,
                "limit": self.limit,
            },
        )


# =============================================================================
# CLI Interface
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="meme_scanner",
        description="Discover trending meme coins with automatic risk filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --min-liquidity 50000 --min-score 70
  %(prog)s --chain eth --limit 20
  %(prog)s --min-age-hours 24 --min-holders 500
  %(prog)s --json --min-liquidity 10000
        """,
    )

    parser.add_argument(
        "--min-liquidity",
        type=float,
        default=10000,
        help="Minimum liquidity in USD (default: 10000)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum risk score 0-100 (default: 50, higher is safer)",
    )
    parser.add_argument(
        "--min-holders",
        type=int,
        default=100,
        help="Minimum holder count (default: 100)",
    )
    parser.add_argument(
        "--min-age-hours",
        type=float,
        default=1,
        help="Minimum token age in hours (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    parser.add_argument(
        "--chain",
        type=str,
        default="sol",
        choices=["sol", "eth", "bsc", "base"],
        help="Blockchain to scan (default: sol)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of table",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Bitget API key (optional, for higher rate limits)",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments
    if args.min_score < 0 or args.min_score > 100:
        print("❌ Error: --min-score must be between 0 and 100", file=sys.stderr)
        return 1

    if args.min_liquidity < 0:
        print("❌ Error: --min-liquidity must be non-negative", file=sys.stderr)
        return 1

    if args.min_holders < 0:
        print("❌ Error: --min-holders must be non-negative", file=sys.stderr)
        return 1

    if args.min_age_hours < 0:
        print("❌ Error: --min-age-hours must be non-negative", file=sys.stderr)
        return 1

    if args.limit < 1 or args.limit > 100:
        print("❌ Error: --limit must be between 1 and 100", file=sys.stderr)
        return 1

    # Create scanner and run
    scanner = MemeScanner(
        min_liquidity=args.min_liquidity,
        min_score=args.min_score,
        min_holders=args.min_holders,
        min_age_hours=args.min_age_hours,
        limit=args.limit,
        chain=args.chain,
        api_key=args.api_key,
    )

    print(f"🔍 Scanning {args.chain} for trending meme coins...", file=sys.stderr)
    print(
        f"   Filters: liquidity≥${args.min_liquidity:,.0f}, "
        f"holders≥{args.min_holders}, "
        f"age≥{args.min_age_hours}h, "
        f"score≥{args.min_score}",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    result = scanner.scan()

    # Output results
    if args.json:
        print(format_json_output(result))
    else:
        print(format_table(result.tokens))
        print(format_statistics(result))

    # Return exit code based on results
    return 0 if result.passed_filters > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
