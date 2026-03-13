"""Pytest fixtures for Solana trading agent tests.

Provides reusable fixtures for mocking APIs, creating test wallets,
and providing test data for Solana trading agent testing.
"""

from collections.abc import Generator
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import pytest
import shutil

from solders.keypair import Keypair


# =============================================================================
# Bitget Wallet API Mocks
# =============================================================================


@pytest.fixture
def mock_bitget_api(mocker: Any) -> Any:
    """Mock Bitget Wallet API responses.

    Provides methods to configure mock responses for:
    - token_info: Sample token metadata
    - security_audit: Safe/risky token scenarios
    - swap_quote: Sample swap quotes

    Usage:
        def test_token_swap(mock_bitget_api):
            mock_bitget_api.mock_token_info.return_value = {...}
    """
    api_mock = mocker.MagicMock()

    def mock_token_info() -> dict[str, Any]:
        """Return sample token data."""
        return {
            "symbol": "SOL",
            "name": "Wrapped Solana",
            "address": "So11111111111111111111111111111111111111112",
            "decimals": 9,
            "logo_uri": "https://example.com/sol.png",
            "coingecko_id": "solana",
            "verified": True,
        }

    def mock_security_audit(
        token_address: str | None = None, is_safe: bool = True
    ) -> dict[str, Any]:
        """Return security audit results.

        Args:
            token_address: Token address to audit
            is_safe: If True, return safe audit; if False, return risky

        Returns:
            Audit results with risk indicators
        """
        if is_safe:
            return {
                "token_address": token_address or "SafeToken1111111111111111111111111",
                "audit_status": "passed",
                "risk_level": "low",
                "is_verified": True,
                "holder_concentration": 0.15,
                "liquidity_locked": True,
                "mint_authority_revoked": True,
                "freeze_authority_revoked": True,
                "top_10_holders_percent": 25.5,
            }
        else:
            return {
                "token_address": token_address or "RiskyToken1111111111111111111111111",
                "audit_status": "failed",
                "risk_level": "high",
                "is_verified": False,
                "holder_concentration": 0.85,
                "liquidity_locked": False,
                "mint_authority_revoked": False,
                "freeze_authority_revoked": False,
                "top_10_holders_percent": 92.3,
                "red_flags": [
                    "High holder concentration",
                    "Liquidity not locked",
                    "Mint authority still active",
                ],
            }

    def mock_swap_quote(
        input_mint: str,
        output_mint: str,
        amount: int = 1000000000,
        slippage_bps: int = 50,
    ) -> dict[str, Any]:
        """Return sample swap quote.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in lamports/smallest unit
            slippage_bps: Slippage tolerance in basis points

        Returns:
            Swap quote with rate and estimated output
        """
        return {
            "input_mint": input_mint,
            "output_mint": output_mint,
            "input_amount": amount,
            "output_amount": int(amount * 0.95),  # Simulated exchange rate
            "price_impact": 0.02,
            "slippage_bps": slippage_bps,
            "route": [
                "Route111111111111111111111111111111111",
                "Route222222222222222222222222222222222",
            ],
            "min_output": int(amount * 0.95 * (1 - slippage_bps / 10000)),
            "estimated_time_ms": 400,
        }

    # Attach mock methods to the API mock
    api_mock.token_info = mocker.MagicMock(side_effect=mock_token_info)
    api_mock.security_audit = mocker.MagicMock(side_effect=mock_security_audit)
    api_mock.swap_quote = mocker.MagicMock(side_effect=mock_swap_quote)

    return api_mock


# =============================================================================
# RugCheck API Mocks
# =============================================================================


@pytest.fixture
def mock_rugcheck_api(mocker: Any) -> Any:
    """Mock RugCheck API responses.

    Provides methods to return risk reports with varying danger levels.

    Usage:
        def test_risk_assessment(mock_rugcheck_api):
            safe_report = mock_rugcheck_api.mock_risk_report_safe()
            dangerous_report = mock_rugcheck_api.mock_risk_report_dangerous()
    """
    api_mock = mocker.MagicMock()

    def mock_risk_report_safe(token_address: str | None = None) -> dict[str, Any]:
        """Return safe token risk report (score 85+).

        Args:
            token_address: Token address to check

        Returns:
            Risk report with high score and minimal risks
        """
        return {
            "token_address": token_address or "SafeToken1111111111111111111111111",
            "score": 92,
            "level": "Low Risk",
            "audit_status": "passed",
            "risks": [],
            "checks": {
                "liquidity": {
                    "status": "pass",
                    "details": "Liquidity locked for 2+ years",
                },
                "mint_authority": {
                    "status": "pass",
                    "details": "Mint authority revoked",
                },
                "freeze_authority": {
                    "status": "pass",
                    "details": "Freeze authority revoked",
                },
                "holder_distribution": {
                    "status": "pass",
                    "details": "Well distributed",
                },
                "metadata": {"status": "pass", "details": "Verified metadata"},
            },
            "warnings": [],
            "metadata": {
                "symbol": "SAFE",
                "name": "Safe Token",
                "decimals": 9,
            },
        }

    def mock_risk_report_dangerous(token_address: str | None = None) -> dict[str, Any]:
        """Return dangerous token risk report (score <40).

        Args:
            token_address: Token address to check

        Returns:
            Risk report with low score and multiple red flags
        """
        return {
            "token_address": token_address or "DangerToken111111111111111111111111",
            "score": 25,
            "level": "Danger",
            "audit_status": "failed",
            "risks": [
                {
                    "name": "High Holder Concentration",
                    "score_impact": -30,
                    "severity": "high",
                    "description": "Top 10 holders own >90% of supply",
                },
                {
                    "name": "Mint Authority Enabled",
                    "score_impact": -25,
                    "severity": "critical",
                    "description": "Mint authority can create unlimited tokens",
                },
                {
                    "name": "Unlocked Liquidity",
                    "score_impact": -20,
                    "severity": "high",
                    "description": "Liquidity can be removed at any time",
                },
                {
                    "name": "Freeze Authority Enabled",
                    "score_impact": -15,
                    "severity": "medium",
                    "description": "Freeze authority can block transfers",
                },
            ],
            "checks": {
                "liquidity": {"status": "fail", "details": "Liquidity not locked"},
                "mint_authority": {
                    "status": "fail",
                    "details": "Mint authority active",
                },
                "freeze_authority": {
                    "status": "fail",
                    "details": "Freeze authority active",
                },
                "holder_distribution": {
                    "status": "fail",
                    "details": "Highly concentrated",
                },
                "metadata": {"status": "warning", "details": "Unverified metadata"},
            },
            "warnings": [
                "High risk of rug pull",
                "Do not invest more than you can afford to lose",
                "Consider avoiding this token",
            ],
            "metadata": {
                "symbol": "DANGR",
                "name": "Danger Token",
                "decimals": 9,
            },
        }

    # Attach mock methods to the API mock
    api_mock.get_risk_report = mocker.MagicMock(
        side_effect=lambda addr, **kwargs: mock_risk_report_safe(addr)
        if "safe" in str(addr).lower()
        else mock_risk_report_dangerous(addr)
    )
    api_mock.mock_risk_report_safe = mocker.MagicMock(side_effect=mock_risk_report_safe)
    api_mock.mock_risk_report_dangerous = mocker.MagicMock(
        side_effect=mock_risk_report_dangerous
    )

    return api_mock


# =============================================================================
# Solana Keypair Fixtures
# =============================================================================


@pytest.fixture
def test_keypair() -> Keypair:
    """Generate deterministic test Solana keypair.

    Uses a known test mnemonic for reproducible addresses across test runs.

    Returns:
        Keypair object with deterministic key generation

    Note:
        This keypair is for testing only. Never use in production.
        Private key is derived from: "test test test test test test test test test test test junk"
    """
    # Deterministic seed for reproducible tests
    # This is the standard Solana test mnemonic
    test_seed = bytes(
        [
            0xC7,
            0x17,
            0x3A,
            0xD2,
            0x7B,
            0x58,
            0x3E,
            0x85,
            0x49,
            0x0A,
            0x2C,
            0xB2,
            0x4C,
            0x7A,
            0x6E,
            0x0E,
            0x8F,
            0x3E,
            0x5A,
            0x7B,
            0xD9,
            0x2C,
            0x8F,
            0xC1,
            0x3E,
            0x9A,
            0x4B,
            0x5D,
            0x6F,
            0x1E,
            0x2C,
            0x3D,
        ]
    )

    keypair = Keypair.from_seed(test_seed)
    return keypair


@pytest.fixture
def test_addresses(test_keypair: Keypair) -> dict[str, str | bytes]:
    """Extract addresses from test keypair.

    Args:
        test_keypair: The test keypair fixture

    Returns:
        Dictionary with pubkey strings for easy use in tests
    """
    return {
        "pubkey": str(test_keypair.pubkey()),
        "pubkey_bytes": bytes(test_keypair.pubkey()),
    }


# =============================================================================
# Sample Token Data
# =============================================================================


@pytest.fixture
def sample_tokens() -> dict[str, dict[str, Any]]:
    """Provide sample token test data.

    Returns:
        Dictionary containing:
        - safe_token: High score (92), good liquidity, verified
        - risky_token: Low score (25), multiple red flags
        - edge_token: Medium score (58), mixed indicators
    """
    return {
        "safe_token": {
            "address": "SafeToken1111111111111111111111111111111111",
            "symbol": "SAFE",
            "name": "Safe Token",
            "decimals": 9,
            "risk_score": 92,
            "risk_level": "Low Risk",
            "liquidity_usd": 1500000,
            "volume_24h_usd": 250000,
            "holder_count": 5420,
            "verified": True,
            "mint_authority_revoked": True,
            "freeze_authority_revoked": True,
            "liquidity_locked": True,
            "top_10_holders_percent": 18.5,
        },
        "risky_token": {
            "address": "DangerToken111111111111111111111111111111111",
            "symbol": "DANGR",
            "name": "Danger Token",
            "decimals": 9,
            "risk_score": 25,
            "risk_level": "Danger",
            "liquidity_usd": 5000,
            "volume_24h_usd": 1200,
            "holder_count": 87,
            "verified": False,
            "mint_authority_revoked": False,
            "freeze_authority_revoked": False,
            "liquidity_locked": False,
            "top_10_holders_percent": 94.2,
            "red_flags": [
                "Mint authority enabled",
                "Liquidity unlocked",
                "High holder concentration",
            ],
        },
        "edge_token": {
            "address": "EdgeToken1111111111111111111111111111111111",
            "symbol": "EDGE",
            "name": "Edge Case Token",
            "decimals": 6,
            "risk_score": 58,
            "risk_level": "Medium Risk",
            "liquidity_usd": 75000,
            "volume_24h_usd": 12000,
            "holder_count": 342,
            "verified": True,
            "mint_authority_revoked": True,
            "freeze_authority_revoked": False,
            "liquidity_locked": False,
            "top_10_holders_percent": 45.8,
            "red_flags": [
                "Freeze authority still active",
                "Liquidity not fully locked",
            ],
        },
    }


# =============================================================================
# Temporary Keyring Fixture
# =============================================================================


@pytest.fixture
def temp_keyring() -> Generator[Path, None, None]:
    """Create temporary secure storage for wallet tests.

    Provides a temporary directory that simulates a secure keyring location.
    Automatically cleaned up after test completion.

    Yields:
        Path to temporary keyring directory

    Usage:
        def test_wallet_storage(temp_keyring):
            wallet_path = temp_keyring / "wallet.json"
            # Test operations...
            # Directory automatically cleaned up
    """
    keyring_path = Path(mkdtemp(prefix="test_keyring_"))

    try:
        yield keyring_path
    finally:
        # Cleanup: remove temporary keyring
        shutil.rmtree(keyring_path, ignore_errors=True)


# =============================================================================
# Additional Utility Fixtures
# =============================================================================


@pytest.fixture
def mock_transaction(mocker: Any) -> Any:
    """Mock Solana transaction for testing.

    Returns:
        Mocked transaction object with common methods
    """
    tx_mock = mocker.MagicMock()
    tx_mock.sign.return_value = None
    tx_mock.serialize.return_value = bytes([0x01, 0x02, 0x03])
    tx_mock.verify_and_sign.return_value = True
    return tx_mock


@pytest.fixture
def mock_rpc_client(mocker: Any) -> Any:
    """Mock Solana RPC client.

    Returns:
        Mocked RPC client with common method stubs
    """
    client_mock = mocker.MagicMock()

    # Common RPC method mocks
    client_mock.get_balance.return_value = mocker.MagicMock(value=1000000000)
    client_mock.get_account_info.return_value = mocker.MagicMock(
        value=mocker.MagicMock(data=bytes([0x00] * 100))
    )
    client_mock.send_transaction.return_value = mocker.MagicMock(
        value="5VERv8NMvB2dXRo5yN3qKvXGNyBzE9yFgN8sNvVqU7J3EXAMPLE"
    )
    client_mock.get_signature_statuses.return_value = mocker.MagicMock(
        value=[mocker.MagicMock(value=mocker.MagicMock(status="confirmed"))]
    )

    return client_mock
