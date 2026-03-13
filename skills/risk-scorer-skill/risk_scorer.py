"""
Token Risk Scorer Module

Evaluates token contracts for rug-pull risks by analyzing security factors,
liquidity metrics, and transaction patterns.

Scoring Formula:
- Security weight: 50%
- Liquidity weight: 30%
- Transaction weight: 20%

Rating thresholds:
- score >= 70: "safe"
- 40 <= score < 70: "caution"
- score < 40: "dangerous"
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RiskRating(Enum):
    """Token risk rating levels."""

    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


@dataclass
class RiskFactor:
    """Individual risk factor with score and details."""

    name: str
    score: int
    weight: float
    details: str = ""


@dataclass
class TokenRiskResult:
    """Complete risk assessment result for a token."""

    contract_address: str
    score: int
    rating: str
    security_score: int = 0
    liquidity_score: int = 0
    transaction_score: int = 0
    risks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContractValidationError(Exception):
    """Raised when contract address validation fails."""

    pass


class APITimeoutError(Exception):
    """Raised when API request times out."""

    pass


class TokenRiskScorer:
    """
    Token risk scoring engine.

    Analyzes token contracts using multiple data sources:
    - RugCheck API for security analysis
    - Bitget API for liquidity data
    - On-chain transaction patterns
    """

    # Scoring weights
    SECURITY_WEIGHT = 0.50
    LIQUIDITY_WEIGHT = 0.30
    TRANSACTION_WEIGHT = 0.20

    # Rating thresholds
    SAFE_THRESHOLD = 70
    CAUTION_THRESHOLD = 40

    def __init__(self, rugcheck_client=None, bitget_client=None, timeout: int = 30):
        """
        Initialize the risk scorer.

        Args:
            rugcheck_client: Client for RugCheck API
            bitget_client: Client for Bitget API
            timeout: API request timeout in seconds
        """
        self.rugcheck_client = rugcheck_client
        self.bitget_client = bitget_client
        self.timeout = timeout

    def validate_contract_address(self, address: str) -> bool:
        """
        Validate Solana contract address format.

        Args:
            address: Contract address to validate

        Returns:
            True if valid

        Raises:
            ContractValidationError: If address is invalid
        """
        if not address or not isinstance(address, str):
            raise ContractValidationError("Contract address must be a non-empty string")

        # Solana addresses are base58 encoded, 32-44 characters
        pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
        if not re.match(pattern, address):
            raise ContractValidationError(
                f"Invalid contract address format: {address}. "
                "Solana addresses must be 32-44 base58 characters"
            )

        return True

    def _calculate_weighted_score(
        self, security_score: int, liquidity_score: int, transaction_score: int
    ) -> int:
        """
        Calculate weighted average score.

        Formula: (security * 0.50) + (liquidity * 0.30) + (transaction * 0.20)

        Args:
            security_score: 0-100 security rating
            liquidity_score: 0-100 liquidity rating
            transaction_score: 0-100 transaction pattern rating

        Returns:
            Weighted average score (0-100)
        """
        weighted = (
            security_score * self.SECURITY_WEIGHT
            + liquidity_score * self.LIQUIDITY_WEIGHT
            + transaction_score * self.TRANSACTION_WEIGHT
        )
        return round(weighted)

    def _get_rating(self, score: int) -> str:
        """
        Convert numeric score to risk rating.

        Args:
            score: Numeric score 0-100

        Returns:
            Risk rating string
        """
        if score >= self.SAFE_THRESHOLD:
            return RiskRating.SAFE.value
        elif score >= self.CAUTION_THRESHOLD:
            return RiskRating.CAUTION.value
        else:
            return RiskRating.DANGEROUS.value

    def _fetch_rugcheck_data(self, contract: str) -> Dict[str, Any]:
        """
        Fetch security data from RugCheck API.

        Args:
            contract: Token contract address

        Returns:
            RugCheck analysis data

        Raises:
            APITimeoutError: If request times out
        """
        if self.rugcheck_client is None:
            # Return default safe data for testing without client
            return {"score": 50, "risks": [], "security_factors": {}}

        try:
            return self.rugcheck_client.analyze(contract, timeout=self.timeout)
        except TimeoutError:
            raise APITimeoutError(f"RugCheck API timeout after {self.timeout}s")

    def _fetch_bitget_data(self, contract: str) -> Dict[str, Any]:
        """
        Fetch liquidity data from Bitget API.

        Args:
            contract: Token contract address

        Returns:
            Bitget liquidity data

        Raises:
            APITimeoutError: If request times out
        """
        if self.bitget_client is None:
            # Return default data for testing without client
            return {"liquidity_usd": 100000, "volume_24h": 50000, "price_impact": 0.05}

        try:
            return self.bitget_client.get_liquidity(contract, timeout=self.timeout)
        except TimeoutError:
            raise APITimeoutError(f"Bitget API timeout after {self.timeout}s")

    def _calculate_security_score(self, rugcheck_data: Dict[str, Any]) -> int:
        """
        Calculate security score from RugCheck data.

        Args:
            rugcheck_data: Raw data from RugCheck API

        Returns:
            Security score 0-100
        """
        # Use direct score if available
        if "score" in rugcheck_data:
            return min(100, max(0, rugcheck_data["score"]))

        # Calculate from risk factors
        risks = rugcheck_data.get("risks", [])
        risk_penalty = 0

        for risk in risks:
            severity = risk.get("severity", "low")
            if severity == "critical":
                risk_penalty += 40
            elif severity == "high":
                risk_penalty += 25
            elif severity == "medium":
                risk_penalty += 10
            else:
                risk_penalty += 5

        return max(0, 100 - risk_penalty)

    def _calculate_liquidity_score(self, bitget_data: Dict[str, Any]) -> int:
        """
        Calculate liquidity score from Bitget data.

        Args:
            bitget_data: Raw data from Bitget API

        Returns:
            Liquidity score 0-100
        """
        liquidity_usd = bitget_data.get("liquidity_usd", 0)

        if liquidity_usd >= 1000000:  # >= $1M
            return 100
        elif liquidity_usd >= 500000:  # >= $500k
            return 85
        elif liquidity_usd >= 100000:  # >= $100k
            return 70
        elif liquidity_usd >= 50000:  # >= $50k
            return 50
        elif liquidity_usd >= 10000:  # >= $10k
            return 30
        else:
            return 10

    def _calculate_transaction_score(self, token_data: Dict[str, Any]) -> int:
        """
        Calculate transaction pattern score.

        Args:
            token_data: Token metadata and transaction data

        Returns:
            Transaction score 0-100
        """
        # Check for suspicious patterns
        score = 100

        # High holder concentration penalty
        top_10_percent = token_data.get("top_10_holders_percent", 0)
        if top_10_percent > 80:
            score -= 40
        elif top_10_percent > 60:
            score -= 25
        elif top_10_percent > 40:
            score -= 10

        # Low transaction count penalty
        tx_count = token_data.get("transaction_count_24h", 0)
        if tx_count < 10:
            score -= 30
        elif tx_count < 50:
            score -= 15

        return max(0, score)

    def score_token(
        self, contract: str, token_metadata: Optional[Dict[str, Any]] = None
    ) -> TokenRiskResult:
        """
        Calculate comprehensive risk score for a token.

        Args:
            contract: Token contract address
            token_metadata: Optional additional token data

        Returns:
            TokenRiskResult with score, rating, and risk factors

        Raises:
            ContractValidationError: If contract address is invalid
            APITimeoutError: If API requests timeout
        """
        # Validate contract address
        self.validate_contract_address(contract)

        # Fetch data from sources
        rugcheck_data = self._fetch_rugcheck_data(contract)
        bitget_data = self._fetch_bitget_data(contract)

        # Calculate individual scores
        security_score = self._calculate_security_score(rugcheck_data)
        liquidity_score = self._calculate_liquidity_score(bitget_data)
        transaction_score = self._calculate_transaction_score(token_metadata or {})

        # Calculate weighted final score
        final_score = self._calculate_weighted_score(
            security_score, liquidity_score, transaction_score
        )

        # Get rating
        rating = self._get_rating(final_score)

        # Collect risks
        risks = rugcheck_data.get("risks", [])

        return TokenRiskResult(
            contract_address=contract,
            score=final_score,
            rating=rating,
            security_score=security_score,
            liquidity_score=liquidity_score,
            transaction_score=transaction_score,
            risks=risks,
            metadata={
                "rugcheck_score": rugcheck_data.get("score"),
                "liquidity_usd": bitget_data.get("liquidity_usd"),
            },
        )

    def to_dict(self, result: TokenRiskResult) -> Dict[str, Any]:
        """
        Convert result to dictionary format.

        Args:
            result: TokenRiskResult object

        Returns:
            Dictionary with all result fields
        """
        return {
            "contract_address": result.contract_address,
            "score": result.score,
            "rating": result.rating,
            "security_score": result.security_score,
            "liquidity_score": result.liquidity_score,
            "transaction_score": result.transaction_score,
            "risks": result.risks,
            "metadata": result.metadata,
        }

    def to_json(self, result: TokenRiskResult) -> str:
        """
        Convert result to JSON string.

        Args:
            result: TokenRiskResult object

        Returns:
            JSON string representation
        """
        import json

        return json.dumps(self.to_dict(result), indent=2)


# Convenience function for quick scoring
def quick_score_token(contract: str) -> Dict[str, Any]:
    """
    Quick token risk assessment.

    Args:
        contract: Token contract address

    Returns:
        Dictionary with score and rating
    """
    scorer = TokenRiskScorer()
    result = scorer.score_token(contract)
    return {"contract": contract, "score": result.score, "rating": result.rating}
