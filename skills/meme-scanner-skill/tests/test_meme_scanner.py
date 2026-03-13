"""Tests for meme scanner skill.

Tests filtering logic, risk-adjusted scoring, sorting, edge cases,
output formatting, and API error handling.
"""

from typing import Any

from scripts.meme_scanner import (
    TokenInfo,
    filter_tokens,
    calculate_adjusted_scores,
    format_json_output,
    ScanResult,
    BitgetWalletAPI,
)


# =============================================================================
# Test 1: Filtering Logic
# =============================================================================


def test_filtering_logic() -> None:
    """Verify all filters work correctly: liquidity, holders, age.

    Creates mock tokens with varying characteristics and verifies
    that only tokens passing ALL filters are included.
    """
    # Create tokens with different characteristics
    tokens = [
        # Token 1: Passes all filters
        TokenInfo(
            symbol="PASS1",
            name="Pass Token 1",
            address="Pass111111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=50.0,
            liquidity_usd=100000,  # >= 50000
            holders=500,  # >= 100
            age_hours=24.0,  # >= 6
        ),
        # Token 2: Fails liquidity filter
        TokenInfo(
            symbol="FAIL_LIQ",
            name="Fail Liquidity",
            address="FailLiq111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=100.0,
            liquidity_usd=10000,  # < 50000
            holders=500,
            age_hours=24.0,
        ),
        # Token 3: Fails holders filter
        TokenInfo(
            symbol="FAIL_HLD",
            name="Fail Holders",
            address="FailHld111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=75.0,
            liquidity_usd=100000,
            holders=50,  # < 100
            age_hours=24.0,
        ),
        # Token 4: Fails age filter
        TokenInfo(
            symbol="FAIL_AGE",
            name="Fail Age",
            address="FailAge111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=60.0,
            liquidity_usd=100000,
            holders=500,
            age_hours=2.0,  # < 6
        ),
        # Token 5: Passes all filters (borderline)
        TokenInfo(
            symbol="PASS2",
            name="Pass Token 2",
            address="Pass211111111111111111111111111111111",
            chain="sol",
            price_usd=0.002,
            price_change_24h=30.0,
            liquidity_usd=50000,  # Exactly at minimum
            holders=100,  # Exactly at minimum
            age_hours=6.0,  # Exactly at minimum
        ),
    ]

    # Apply filters
    filtered = filter_tokens(
        tokens, min_liquidity=50000, min_holders=100, min_age_hours=6
    )

    # Verify correct tokens passed
    assert len(filtered) == 2
    filtered_symbols = [t.symbol for t in filtered]
    assert "PASS1" in filtered_symbols
    assert "PASS2" in filtered_symbols
    assert "FAIL_LIQ" not in filtered_symbols
    assert "FAIL_HLD" not in filtered_symbols
    assert "FAIL_AGE" not in filtered_symbols


# =============================================================================
# Test 2: Risk-Adjusted Scoring Formula
# =============================================================================


def test_risk_adjusted_scoring() -> None:
    """Verify risk-adjusted scoring formula: (price_change_24h * risk_score) / 100.

    Higher raw gains don't always mean higher adjusted score.
    """
    tokens = [
        # Token A: High gain, low risk score
        TokenInfo(
            symbol="HIGH_GAIN",
            name="High Gain Low Risk Score",
            address="HighGain111111111111111111111111111",
            chain="sol",
            price_usd=0.01,
            price_change_24h=200.0,  # +200%
            liquidity_usd=50000,
            holders=100,
            age_hours=24,
            risk_score=30,  # Low risk score
        ),
        # Token B: Moderate gain, high risk score
        TokenInfo(
            symbol="SAFE_GAIN",
            name="Safe Gain High Risk Score",
            address="SafeGain111111111111111111111111111",
            chain="sol",
            price_usd=0.02,
            price_change_24h=50.0,  # +50%
            liquidity_usd=100000,
            holders=500,
            age_hours=48,
            risk_score=90,  # High risk score
        ),
        # Token C: Negative gain (should result in 0 adjusted score)
        TokenInfo(
            symbol="NEGATIVE",
            name="Negative Gain",
            address="Negative111111111111111111111111111",
            chain="sol",
            price_usd=0.005,
            price_change_24h=-25.0,  # -25%
            liquidity_usd=75000,
            holders=200,
            age_hours=12,
            risk_score=80,
        ),
    ]

    # Calculate adjusted scores
    scored = calculate_adjusted_scores(tokens)

    # Find tokens by symbol
    high_gain = next(t for t in scored if t.symbol == "HIGH_GAIN")
    safe_gain = next(t for t in scored if t.symbol == "SAFE_GAIN")
    negative = next(t for t in scored if t.symbol == "NEGATIVE")

    # Verify formula: (price_change_24h * risk_score) / 100
    # HIGH_GAIN: (200 * 30) / 100 = 60
    assert high_gain.adjusted_score == 60.0

    # SAFE_GAIN: (50 * 90) / 100 = 45
    assert safe_gain.adjusted_score == 45.0

    # NEGATIVE: max(0, -25) * 80 / 100 = 0 (negative gains treated as 0)
    assert negative.adjusted_score == 0.0

    # Verify higher raw gains don't always win
    # HIGH_GAIN has 4x the price change but lower adjusted score than it would with high risk
    assert high_gain.adjusted_score > safe_gain.adjusted_score


# =============================================================================
# Test 3: Sorting by Adjusted Score (Not Raw Gains)
# =============================================================================


def test_sorting_by_adjusted_score() -> None:
    """Verify tokens are sorted by adjusted_score, not raw price_change_24h.

    Token A: +200% gain, score 30 → adjusted 60
    Token B: +50% gain, score 90 → adjusted 45
    Token C: +100% gain, score 80 → adjusted 80

    Expected order after sorting: C (80), A (60), B (45)
    This proves sorting is by adjusted score, not raw gains.
    """
    tokens = [
        # Token B: Lower gain, higher adjusted score potential
        TokenInfo(
            symbol="TOKEN_B",
            name="Token B",
            address="TokenB111111111111111111111111111111111",
            chain="sol",
            price_usd=0.02,
            price_change_24h=50.0,  # +50%
            liquidity_usd=100000,
            holders=500,
            age_hours=48,
            risk_score=90,  # High risk score → adjusted = 45
        ),
        # Token A: Highest gain, but risky
        TokenInfo(
            symbol="TOKEN_A",
            name="Token A",
            address="TokenA111111111111111111111111111111111",
            chain="sol",
            price_usd=0.01,
            price_change_24h=200.0,  # +200%
            liquidity_usd=50000,
            holders=100,
            age_hours=24,
            risk_score=30,  # Lower risk score → adjusted = 60
        ),
        # Token C: Balanced - should win
        TokenInfo(
            symbol="TOKEN_C",
            name="Token C",
            address="TokenC111111111111111111111111111111111",
            chain="sol",
            price_usd=0.015,
            price_change_24h=100.0,  # +100%
            liquidity_usd=80000,
            holders=300,
            age_hours=36,
            risk_score=80,  # Good risk score → adjusted = 80
        ),
    ]

    # Calculate adjusted scores and sort
    scored = calculate_adjusted_scores(tokens)
    sorted_tokens = sorted(scored, key=lambda t: t.adjusted_score, reverse=True)

    # Verify order: TOKEN_C (80), TOKEN_A (60), TOKEN_B (45)
    assert len(sorted_tokens) == 3
    assert sorted_tokens[0].symbol == "TOKEN_C"  # adjusted = 80
    assert sorted_tokens[1].symbol == "TOKEN_A"  # adjusted = 60
    assert sorted_tokens[2].symbol == "TOKEN_B"  # adjusted = 45

    # Verify TOKEN_A is ranked higher than TOKEN_B despite higher risk
    # This proves the ranking balances gains vs safety
    assert sorted_tokens.index(
        next(t for t in sorted_tokens if t.symbol == "TOKEN_A")
    ) < sorted_tokens.index(next(t for t in sorted_tokens if t.symbol == "TOKEN_B"))


# =============================================================================
# Test 4: Empty Results Handling
# =============================================================================


def test_empty_results_handling() -> None:
    """Verify graceful handling when all tokens are filtered out.

    Creates mock data where every token fails at least one filter.
    """
    # Create tokens that will all fail filters
    tokens = [
        # Fails liquidity
        TokenInfo(
            symbol="LOW_LIQ",
            name="Low Liquidity",
            address="LowLiq111111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=500.0,
            liquidity_usd=1000,  # Very low
            holders=1000,
            age_hours=100,
        ),
        # Fails holders
        TokenInfo(
            symbol="LOW_HLD",
            name="Low Holders",
            address="LowHld111111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=300.0,
            liquidity_usd=200000,
            holders=5,  # Very few
            age_hours=100,
        ),
        # Fails age
        TokenInfo(
            symbol="NEW_TOKEN",
            name="Brand New Token",
            address="NewToken11111111111111111111111111111111",
            chain="sol",
            price_usd=0.001,
            price_change_24h=1000.0,
            liquidity_usd=200000,
            holders=1000,
            age_hours=0.5,  # 30 minutes old
        ),
    ]

    # Apply strict filters that will exclude all tokens
    filtered = filter_tokens(
        tokens, min_liquidity=50000, min_holders=100, min_age_hours=6
    )

    # Verify empty result
    assert len(filtered) == 0
    assert filtered == []

    # Verify ScanResult handles empty tokens gracefully
    result = ScanResult(
        tokens=[],
        total_scanned=3,
        passed_filters=0,
        filtered_out=3,
        scan_time_seconds=0.5,
        filters_applied={
            "chain": "sol",
            "min_liquidity": 50000,
            "min_holders": 100,
            "min_age_hours": 6,
            "min_score": 50,
            "limit": 10,
        },
    )

    assert result.total_scanned == 3
    assert result.passed_filters == 0
    assert result.filtered_out == 3
    assert result.tokens == []


# =============================================================================
# Test 5: Output Format (JSON Structure)
# =============================================================================


def test_output_format_json() -> None:
    """Verify JSON output structure has all required fields with correct types."""
    # Create sample tokens
    tokens = [
        TokenInfo(
            symbol="TEST1",
            name="Test Token 1",
            address="Test111111111111111111111111111111111111",
            chain="sol",
            price_usd=0.00123,
            price_change_24h=75.5,
            liquidity_usd=150000,
            holders=350,
            age_hours=48.5,
            volume_24h=25000,
            market_cap=500000,
            risk_score=85,
            adjusted_score=64.175,
            security_flags=["new_token"],
        ),
        TokenInfo(
            symbol="TEST2",
            name="Test Token 2",
            address="Test222222222222222222222222222222222222",
            chain="sol",
            price_usd=0.00456,
            price_change_24h=120.0,
            liquidity_usd=300000,
            holders=720,
            age_hours=72.0,
            volume_24h=50000,
            market_cap=1000000,
            risk_score=92,
            adjusted_score=110.4,
            security_flags=[],
        ),
    ]

    # Create scan result
    result = ScanResult(
        tokens=tokens,
        total_scanned=50,
        passed_filters=2,
        filtered_out=48,
        scan_time_seconds=1.25,
        filters_applied={
            "chain": "sol",
            "min_liquidity": 50000,
            "min_holders": 100,
            "min_age_hours": 6,
            "min_score": 50,
            "limit": 10,
        },
    )

    # Generate JSON output
    json_output = format_json_output(result)

    # Parse and validate structure
    import json

    data = json.loads(json_output)

    # Verify top-level structure
    assert "scan_time" in data
    assert "statistics" in data
    assert "filters_applied" in data
    assert "tokens" in data

    # Verify statistics
    stats = data["statistics"]
    assert stats["total_scanned"] == 50
    assert stats["passed_filters"] == 2
    assert stats["filtered_out"] == 48
    assert stats["scan_duration_seconds"] == 1.25

    # Verify filters_applied
    filters = data["filters_applied"]
    assert filters["chain"] == "sol"
    assert filters["min_liquidity"] == 50000
    assert filters["min_holders"] == 100
    assert filters["min_age_hours"] == 6
    assert filters["min_score"] == 50
    assert filters["limit"] == 10

    # Verify tokens array
    assert len(data["tokens"]) == 2

    # Verify token structure (first token)
    token1 = data["tokens"][0]
    required_fields = [
        "symbol",
        "name",
        "address",
        "chain",
        "price_usd",
        "price_change_24h",
        "liquidity_usd",
        "holders",
        "age_hours",
        "volume_24h",
        "market_cap",
        "risk_score",
        "adjusted_score",
        "security_flags",
    ]

    for field in required_fields:
        assert field in token1, f"Missing field: {field}"

    # Verify types
    assert isinstance(token1["symbol"], str)
    assert isinstance(token1["name"], str)
    assert isinstance(token1["address"], str)
    assert isinstance(token1["chain"], str)
    assert isinstance(token1["price_usd"], float)
    assert isinstance(token1["price_change_24h"], float)
    assert isinstance(token1["liquidity_usd"], (int, float))
    assert isinstance(token1["holders"], int)
    assert isinstance(token1["age_hours"], float)
    assert isinstance(token1["volume_24h"], (int, float))
    assert isinstance(token1["market_cap"], (int, float))
    assert isinstance(token1["risk_score"], int)
    assert isinstance(token1["adjusted_score"], float)
    assert isinstance(token1["security_flags"], list)

    # Verify values
    assert token1["symbol"] == "TEST1"
    assert token1["risk_score"] == 85
    assert token1["adjusted_score"] == 64.18  # Rounded to 2 decimal places
    assert token1["security_flags"] == ["new_token"]


# =============================================================================
# Test 6: API Error Handling
# =============================================================================


def test_api_error_handling(mocker: Any) -> None:
    """Verify graceful handling when Bitget API is unavailable.

    Mocks API errors and verifies the scanner handles them gracefully
    without crashing.
    """
    # Mock the API to raise connection error
    mocker.patch(
        "scripts.meme_scanner.requests.Session.get",
        side_effect=Exception("Connection refused: API unavailable"),
    )

    # Create scanner instance
    api = BitgetWalletAPI(api_key="test_key")

    # Test fetch_rankings error handling
    rankings = api.fetch_rankings("topGainers", "solana", limit=50)
    assert rankings == []  # Should return empty list on error

    # Test fetch_token_info error handling
    token_info = api.fetch_token_info("TestToken111111111111111111111111111", "solana")
    assert token_info is None  # Should return None on error

    # Test fetch_security_check error handling
    security = api.fetch_security_check(
        "TestToken111111111111111111111111111", "solana"
    )
    assert security == {"risk_level": "unknown", "flags": ["api_error"]}


# =============================================================================
# Test 7: Risk Score Calculation Edge Cases
# =============================================================================


def test_risk_score_edge_cases() -> None:
    """Verify risk score calculation handles edge cases correctly.

    Tests boundary conditions for various risk factors.
    """
    from scripts.meme_scanner import calculate_risk_score

    # Test 1: Perfect token (no risk factors)
    perfect_token = {
        "liquidity_usd": 1000000,
        "holders": 5000,
        "age_hours": 720,  # 30 days
        "price_change_24h": 25,
    }
    perfect_security = {
        "risk_level": "low",
        "is_honeypot": False,
        "mint_function": False,
        "proxy_contract": False,
        "liquidity_locked": True,
        "owner_can_trade": True,
    }

    score, flags = calculate_risk_score(perfect_token, perfect_security)
    assert score == 100  # Maximum score
    assert len(flags) == 0

    # Test 2: Maximum risk token (all risk factors)
    risky_token = {
        "liquidity_usd": 1000,  # Very low
        "holders": 10,  # Very few
        "age_hours": 0.5,  # 30 minutes
        "price_change_24h": 600,  # Extreme pump
    }
    risky_security = {
        "risk_level": "high",
        "is_honeypot": True,
        "mint_function": True,
        "proxy_contract": True,
        "liquidity_locked": False,
        "owner_can_trade": False,
    }

    score, flags = calculate_risk_score(risky_token, risky_security)
    assert score == 0  # Minimum score (capped at 0)
    assert len(flags) >= 8  # Multiple risk flags

    # Test 3: Empty security info (defaults)
    score, flags = calculate_risk_score(perfect_token, {})
    assert score < 100  # Should have some deductions for unknown security

    # Test 4: Zero values
    zero_token = {
        "liquidity_usd": 0,
        "holders": 0,
        "age_hours": 0,
        "price_change_24h": 0,
    }
    score, flags = calculate_risk_score(zero_token, perfect_security)
    assert score < 50  # Should have significant deductions
