"""
Pytest fixtures for Token Risk Scorer tests.

Provides mock API clients, sample test data, and reusable fixtures.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List


class MockRugCheckClient:
    """Mock client for RugCheck API."""

    def __init__(self, default_score: int = 50, risks: List[Dict] = None):
        self.default_score = default_score
        self.risks = risks or []
        self.call_count = 0
        self.called_with = []

    def analyze(self, contract: str, timeout: int = 30) -> Dict[str, Any]:
        """Mock analyze method."""
        self.call_count += 1
        self.called_with.append((contract, timeout))

        return {
            "score": self.default_score,
            "risks": self.risks,
            "security_factors": {
                "mint_authority": False,
                "freeze_authority": False,
                "lp_locked": True,
            },
        }

    def reset(self):
        """Reset mock state."""
        self.call_count = 0
        self.called_with = []


class MockBitgetClient:
    """Mock client for Bitget API."""

    def __init__(self, liquidity_usd: float = 100000, volume_24h: float = 50000):
        self.liquidity_usd = liquidity_usd
        self.volume_24h = volume_24h
        self.call_count = 0

    def get_liquidity(self, contract: str, timeout: int = 30) -> Dict[str, Any]:
        """Mock get_liquidity method."""
        self.call_count += 1

        return {
            "liquidity_usd": self.liquidity_usd,
            "volume_24h": self.volume_24h,
            "price_impact": 0.05 if self.liquidity_usd > 100000 else 0.2,
        }

    def reset(self):
        """Reset mock state."""
        self.call_count = 0


@pytest.fixture
def mock_rugcheck_api():
    """
    Fixture providing a mock RugCheck API client.

    Default returns score of 50 with no risks.
    Customize by passing parameters to the fixture request.

    Usage:
        def test_something(mock_rugcheck_api):
            mock_rugcheck_api.default_score = 92  # Set custom score
            mock_rugcheck_api.risks = [...]       # Set custom risks
    """
    return MockRugCheckClient()


@pytest.fixture
def mock_bitget_api():
    """
    Fixture providing a mock Bitget API client.

    Default returns $100k liquidity and $50k volume.
    Customize by passing parameters to the fixture request.

    Usage:
        def test_something(mock_bitget_api):
            mock_bitget_api.liquidity_usd = 1000000  # Set custom liquidity
            mock_bitget_api.volume_24h = 500000      # Set custom volume
    """
    return MockBitgetClient()


@pytest.fixture
def sample_tokens() -> Dict[str, Dict[str, Any]]:
    """
    Fixture providing sample token test data.

    Returns dictionary with different token scenarios:
    - safe_token: High score, good liquidity
    - dangerous_token: Low score, multiple risks
    - medium_token: Medium score, some concerns
    - new_token: Brand new token with limited data
    """
    return {
        "safe_token": {
            "contract": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            "metadata": {
                "name": "SafeToken",
                "symbol": "SAFE",
                "top_10_holders_percent": 25,
                "transaction_count_24h": 500,
                "age_days": 365,
            },
        },
        "dangerous_token": {
            "contract": "9xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgASD",
            "metadata": {
                "name": "RugToken",
                "symbol": "RUG",
                "top_10_holders_percent": 85,
                "transaction_count_24h": 5,
                "age_days": 1,
            },
        },
        "medium_token": {
            "contract": "5xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgMED",
            "metadata": {
                "name": "CautionToken",
                "symbol": "CAUT",
                "top_10_holders_percent": 50,
                "transaction_count_24h": 50,
                "age_days": 30,
            },
        },
        "new_token": {
            "contract": "3xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgNEW",
            "metadata": {
                "name": "NewToken",
                "symbol": "NEW",
                "top_10_holders_percent": 40,
                "transaction_count_24h": 20,
                "age_days": 2,
            },
        },
    }


@pytest.fixture
def valid_solana_address() -> str:
    """Fixture providing a valid Solana address."""
    return "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"


@pytest.fixture
def invalid_addresses() -> List[str]:
    """Fixture providing invalid address formats."""
    return [
        "",  # Empty string
        "invalid!@#$",  # Invalid characters
        "abc",  # Too short
        "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU1234567890extra",  # Too long
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  # Ethereum format
    ]


@pytest.fixture
def dangerous_risks() -> List[Dict[str, Any]]:
    """Fixture providing dangerous risk factors."""
    return [
        {
            "name": "mint_authority_enabled",
            "severity": "critical",
            "description": "Mint authority is still enabled",
        },
        {
            "name": "freeze_authority_enabled",
            "severity": "critical",
            "description": "Freeze authority is still enabled",
        },
        {
            "name": "lp_unlocked",
            "severity": "high",
            "description": "Liquidity pool is not locked",
        },
        {
            "name": "top_holders_concentration",
            "severity": "high",
            "description": "Top 10 holders control 85% of supply",
        },
    ]


@pytest.fixture
def medium_risks() -> List[Dict[str, Any]]:
    """Fixture providing medium risk factors."""
    return [
        {
            "name": "holder_concentration",
            "severity": "medium",
            "description": "Top 10 holders control 50% of supply",
        },
        {
            "name": "low_liquidity",
            "severity": "medium",
            "description": "Liquidity below recommended threshold",
        },
    ]


@pytest.fixture
def risk_scorer(mock_rugcheck_api, mock_bitget_api):
    """
    Fixture providing a TokenRiskScorer instance with mock clients.

    Usage:
        def test_something(risk_scorer):
            result = risk_scorer.score_token(contract_address)
            assert result.score > 0
    """
    from risk_scorer import TokenRiskScorer

    return TokenRiskScorer(
        rugcheck_client=mock_rugcheck_api, bitget_client=mock_bitget_api, timeout=30
    )
