"""
Comprehensive test suite for Token Risk Scorer.

Tests cover:
- Safe token scoring (score >= 70)
- Dangerous token scoring (score < 40)
- Edge case scoring (40 <= score < 70)
- Formula weight verification
- Invalid contract validation
- API timeout handling
- Output JSON structure
- Threshold boundary conditions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_scorer import (
    TokenRiskScorer,
    TokenRiskResult,
    ContractValidationError,
    APITimeoutError,
    RiskRating,
    quick_score_token,
)


class TestSafeTokenScoring:
    """Tests for tokens with safe ratings (score >= 70)."""

    def test_safe_token_scoring(
        self, mock_rugcheck_api, mock_bitget_api, sample_tokens
    ):
        """
        Test token with score >= 70 is rated as safe.

        Uses mock RugCheck returning score 92 and mock Bitget with good liquidity.
        Asserts final score >= 70 and rating is "safe".
        """
        # Setup: Configure mocks for safe token
        mock_rugcheck_api.default_score = 92
        mock_rugcheck_api.risks = []
        mock_bitget_api.liquidity_usd = 1000000  # High liquidity

        scorer = TokenRiskScorer(
            rugcheck_client=mock_rugcheck_api, bitget_client=mock_bitget_api
        )

        # Execute
        result = scorer.score_token(sample_tokens["safe_token"]["contract"])

        # Verify
        assert result.score >= 70, f"Expected score >= 70, got {result.score}"
        assert result.rating == "safe", f"Expected rating 'safe', got '{result.rating}'"
        assert len(result.risks) == 0, "Safe token should have no risks"


class TestDangerousTokenScoring:
    """Tests for tokens with dangerous ratings (score < 40)."""

    def test_dangerous_token_scoring(
        self, mock_rugcheck_api, mock_bitget_api, sample_tokens, dangerous_risks
    ):
        """
        Test token with score < 40 is rated as dangerous.

        Uses mock RugCheck with multiple dangerous risks.
        Asserts score < 40, rating is "dangerous", and risks array is populated.
        """
        # Setup: Configure mocks for dangerous token
        mock_rugcheck_api.default_score = 15  # Very low security score
        mock_rugcheck_api.risks = dangerous_risks
        mock_bitget_api.liquidity_usd = 5000  # Very low liquidity

        scorer = TokenRiskScorer(
            rugcheck_client=mock_rugcheck_api, bitget_client=mock_bitget_api
        )

        # Execute
        result = scorer.score_token(sample_tokens["dangerous_token"]["contract"])

        # Verify
        assert result.score < 40, f"Expected score < 40, got {result.score}"
        assert result.rating == "dangerous", (
            f"Expected rating 'dangerous', got '{result.rating}'"
        )
        assert len(result.risks) > 0, "Dangerous token should have risks populated"
        assert len(result.risks) >= 2, "Should have multiple risk factors"


class TestMediumRiskTokenScoring:
    """Tests for tokens with caution ratings (40 <= score < 70)."""

    def test_edge_case_token(
        self, mock_rugcheck_api, mock_bitget_api, sample_tokens, medium_risks
    ):
        """
        Test token with score 40-69 is rated as caution.

        Uses mock medium-risk data.
        Asserts rating is "caution".
        """
        # Setup: Configure mocks for medium risk token
        mock_rugcheck_api.default_score = 50  # Medium security score
        mock_rugcheck_api.risks = medium_risks
        mock_bitget_api.liquidity_usd = 100000  # Medium liquidity

        scorer = TokenRiskScorer(
            rugcheck_client=mock_rugcheck_api, bitget_client=mock_bitget_api
        )

        # Execute
        result = scorer.score_token(sample_tokens["medium_token"]["contract"])

        # Verify
        assert 40 <= result.score < 70, f"Expected score 40-69, got {result.score}"
        assert result.rating == "caution", (
            f"Expected rating 'caution', got '{result.rating}'"
        )


class TestScoringFormulaWeights:
    """Tests verifying the weighted scoring formula."""

    def test_scoring_formula_weights(self):
        """
        Test that scoring formula uses correct weights:
        - Security: 50%
        - Liquidity: 30%
        - Transaction: 20%

        Asserts correct weighted average calculation.
        """
        scorer = TokenRiskScorer()

        # Test with known values
        security = 80
        liquidity = 60
        transaction = 40

        # Expected: (80 * 0.50) + (60 * 0.30) + (40 * 0.20) = 40 + 18 + 8 = 66
        expected = 66

        result = scorer._calculate_weighted_score(security, liquidity, transaction)

        assert result == expected, f"Expected {expected}, got {result}"
        assert scorer.SECURITY_WEIGHT == 0.50, "Security weight should be 50%"
        assert scorer.LIQUIDITY_WEIGHT == 0.30, "Liquidity weight should be 30%"
        assert scorer.TRANSACTION_WEIGHT == 0.20, "Transaction weight should be 20%"

    @pytest.mark.parametrize(
        "security,liquidity,transaction,expected",
        [
            (100, 100, 100, 100),  # All max
            (0, 0, 0, 0),  # All min
            (50, 50, 50, 50),  # All medium
            (100, 0, 0, 50),  # Security only
            (0, 100, 0, 30),  # Liquidity only
            (0, 0, 100, 20),  # Transaction only
        ],
    )
    def test_weighted_score_parametrized(
        self, security, liquidity, transaction, expected
    ):
        """Parametrized test for various weight combinations."""
        scorer = TokenRiskScorer()
        result = scorer._calculate_weighted_score(security, liquidity, transaction)
        assert result == expected, (
            f"Expected {expected} for ({security}, {liquidity}, {transaction})"
        )


class TestInvalidContractValidation:
    """Tests for contract address validation error handling."""

    def test_invalid_contract_validation(self, risk_scorer, invalid_addresses):
        """
        Test invalid address format raises proper error.

        Asserts ContractValidationError with appropriate message.
        """
        for invalid_address in invalid_addresses:
            with pytest.raises(ContractValidationError) as exc_info:
                risk_scorer.validate_contract_address(invalid_address)

            assert "Invalid contract address" in str(
                exc_info.value
            ) or "non-empty string" in str(exc_info.value)

    def test_empty_string_validation(self, risk_scorer):
        """Test empty string raises validation error."""
        with pytest.raises(ContractValidationError) as exc_info:
            risk_scorer.validate_contract_address("")
        assert "non-empty string" in str(exc_info.value) or "Invalid" in str(
            exc_info.value
        )

    def test_valid_address_formats(self, risk_scorer, valid_solana_address):
        """Test valid Solana addresses pass validation."""
        result = risk_scorer.validate_contract_address(valid_solana_address)
        assert result is True


class TestAPITimeoutHandling:
    """Tests for API timeout and network error handling."""

    def test_api_timeout_handling_rugcheck(self, sample_tokens):
        """
        Test RugCheck API timeout is handled gracefully.

        Mocks timeout and asserts APITimeoutError is raised.
        """
        # Create mock that raises TimeoutError
        mock_rugcheck = Mock()
        mock_rugcheck.analyze.side_effect = TimeoutError("Connection timed out")

        mock_bitget = Mock()
        mock_bitget.get_liquidity.return_value = {"liquidity_usd": 100000}

        scorer = TokenRiskScorer(
            rugcheck_client=mock_rugcheck, bitget_client=mock_bitget
        )

        with pytest.raises(APITimeoutError) as exc_info:
            scorer.score_token(sample_tokens["safe_token"]["contract"])

        assert (
            "RugCheck" in str(exc_info.value)
            or "timeout" in str(exc_info.value).lower()
        )

    def test_api_timeout_handling_bitget(self, sample_tokens):
        """
        Test Bitget API timeout is handled gracefully.

        Mocks timeout and asserts APITimeoutError is raised.
        """
        # Create mock that returns good data
        mock_rugcheck = Mock()
        mock_rugcheck.analyze.return_value = {"score": 80, "risks": []}

        # Create mock that raises TimeoutError
        mock_bitget = Mock()
        mock_bitget.get_liquidity.side_effect = TimeoutError("Connection timed out")

        scorer = TokenRiskScorer(
            rugcheck_client=mock_rugcheck, bitget_client=mock_bitget
        )

        with pytest.raises(APITimeoutError) as exc_info:
            scorer.score_token(sample_tokens["safe_token"]["contract"])

        assert (
            "Bitget" in str(exc_info.value) or "timeout" in str(exc_info.value).lower()
        )


class TestOutputJSONStructure:
    """Tests for output format and JSON structure validation."""

    def test_output_json_structure(self, risk_scorer, sample_tokens):
        """
        Test output contains all required fields with correct types.

        Asserts:
        - All required fields present
        - score is int
        - rating is string
        - risks is list
        - metadata is dict
        """
        result = risk_scorer.score_token(sample_tokens["safe_token"]["contract"])

        # Check required fields exist
        required_fields = [
            "contract_address",
            "score",
            "rating",
            "security_score",
            "liquidity_score",
            "transaction_score",
            "risks",
            "metadata",
        ]

        for field in required_fields:
            assert hasattr(result, field), f"Missing required field: {field}"

        # Check types
        assert isinstance(result.score, int), (
            f"score should be int, got {type(result.score)}"
        )
        assert isinstance(result.rating, str), (
            f"rating should be str, got {type(result.rating)}"
        )
        assert isinstance(result.risks, list), (
            f"risks should be list, got {type(result.risks)}"
        )
        assert isinstance(result.metadata, dict), (
            f"metadata should be dict, got {type(result.metadata)}"
        )

    def test_to_dict_output(self, risk_scorer, sample_tokens):
        """Test to_dict() returns correct dictionary structure."""
        result = risk_scorer.score_token(sample_tokens["safe_token"]["contract"])
        data = risk_scorer.to_dict(result)

        assert isinstance(data, dict)
        assert data["contract_address"] == sample_tokens["safe_token"]["contract"]
        assert isinstance(data["score"], int)
        assert isinstance(data["rating"], str)

    def test_to_json_output(self, risk_scorer, sample_tokens):
        """Test to_json() returns valid JSON string."""
        result = risk_scorer.score_token(sample_tokens["safe_token"]["contract"])
        json_str = risk_scorer.to_json(result)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "score" in parsed
        assert "rating" in parsed


class TestThresholdBoundaries:
    """Tests for edge cases at rating threshold boundaries."""

    @pytest.mark.parametrize(
        "score,expected_rating",
        [
            (100, "safe"),
            (70, "safe"),  # Exactly at safe threshold
            (69, "caution"),
            (40, "caution"),  # Exactly at caution threshold
            (39, "dangerous"),
            (0, "dangerous"),
        ],
    )
    def test_threshold_boundaries(self, score, expected_rating):
        """
        Test rating at threshold boundaries.

        Verifies:
        - Score 70 -> safe
        - Score 40 -> caution
        - Score 39 -> dangerous
        """
        scorer = TokenRiskScorer()
        rating = scorer._get_rating(score)
        assert rating == expected_rating, (
            f"Score {score} should be '{expected_rating}', got '{rating}'"
        )

    def test_boundary_score_70(self):
        """Test score exactly 70 is safe."""
        scorer = TokenRiskScorer()
        result = scorer._get_rating(70)

        # Mock to get exact score of 70
        mock_rugcheck = Mock()
        mock_rugcheck.analyze.return_value = {"score": 100, "risks": []}
        mock_bitget = Mock()
        mock_bitget.get_liquidity.return_value = {
            "liquidity_usd": 166667
        }  # ~70 liquidity

        scorer_with_mocks = TokenRiskScorer(
            rugcheck_client=mock_rugcheck, bitget_client=mock_bitget
        )

        result = scorer_with_mocks.score_token(
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        )
        assert result.rating == "safe"

    def test_boundary_score_40(self):
        """Test score exactly 40 is caution."""
        rating = TokenRiskScorer()._get_rating(40)
        assert rating == "caution", f"Score 40 should be 'caution', got '{rating}'"

    def test_boundary_score_39(self):
        """Test score 39 is dangerous."""
        rating = TokenRiskScorer()._get_rating(39)
        assert rating == "dangerous", f"Score 39 should be 'dangerous', got '{rating}'"


class TestTokenRiskScorerIntegration:
    """Integration tests for TokenRiskScorer."""

    def test_scorer_without_clients(self, sample_tokens):
        """Test scorer works without API clients (uses defaults)."""
        scorer = TokenRiskScorer()
        result = scorer.score_token(sample_tokens["safe_token"]["contract"])

        assert result.score >= 0
        assert result.rating in ["safe", "caution", "dangerous"]

    def test_scorer_with_custom_timeout(self):
        """Test scorer respects custom timeout setting."""
        scorer = TokenRiskScorer(timeout=60)
        assert scorer.timeout == 60

    def test_quick_score_token_function(self, sample_tokens):
        """Test convenience function quick_score_token."""
        with patch("risk_scorer.TokenRiskScorer") as MockScorer:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.score = 75
            mock_result.rating = "safe"
            mock_instance.score_token.return_value = mock_result
            MockScorer.return_value = mock_instance

            result = quick_score_token(sample_tokens["safe_token"]["contract"])

            assert "contract" in result
            assert "score" in result
            assert "rating" in result
            assert result["score"] == 75
            assert result["rating"] == "safe"


class TestRiskFactorCalculation:
    """Tests for individual risk factor calculations."""

    def test_security_score_from_direct_score(self):
        """Test security score calculation with direct score."""
        scorer = TokenRiskScorer()
        data = {"score": 85}
        result = scorer._calculate_security_score(data)
        assert result == 85

    def test_security_score_from_risks(self):
        """Test security score calculation from risk factors."""
        scorer = TokenRiskScorer()
        data = {
            "risks": [
                {"severity": "critical"},  # -40
                {"severity": "high"},  # -25
                {"severity": "medium"},  # -10
            ]
        }
        result = scorer._calculate_security_score(data)
        expected = max(0, 100 - 40 - 25 - 10)  # = 15
        assert result == expected

    def test_liquidity_score_tiers(self):
        """Test liquidity score calculation across tiers."""
        scorer = TokenRiskScorer()

        test_cases = [
            (1000000, 100),  # >= $1M
            (500000, 85),  # >= $500k
            (100000, 70),  # >= $100k
            (50000, 50),  # >= $50k
            (10000, 30),  # >= $10k
            (1000, 10),  # < $10k
        ]

        for liquidity, expected in test_cases:
            data = {"liquidity_usd": liquidity}
            result = scorer._calculate_liquidity_score(data)
            assert result == expected, (
                f"Liquidity ${liquidity} should score {expected}, got {result}"
            )

    def test_transaction_score_holder_concentration(self):
        """Test transaction score with holder concentration penalties."""
        scorer = TokenRiskScorer()

        # High concentration (>80%)
        data = {"top_10_holders_percent": 85, "transaction_count_24h": 100}
        result = scorer._calculate_transaction_score(data)
        assert result == 60  # 100 - 40

        # Medium concentration (40-60%)
        data = {"top_10_holders_percent": 50, "transaction_count_24h": 100}
        result = scorer._calculate_transaction_score(data)
        assert result == 90  # 100 - 10

        # Low concentration
        data = {"top_10_holders_percent": 25, "transaction_count_24h": 100}
        result = scorer._calculate_transaction_score(data)
        assert result == 100


class TestMockClientBehavior:
    """Tests for mock client behavior in conftest."""

    def test_mock_rugcheck_tracks_calls(self, mock_rugcheck_api):
        """Test mock RugCheck client tracks call count."""
        mock_rugcheck_api.analyze("test_contract")
        assert mock_rugcheck_api.call_count == 1

        mock_rugcheck_api.analyze("another_contract")
        assert mock_rugcheck_api.call_count == 2

    def test_mock_bitget_tracks_calls(self, mock_bitget_api):
        """Test mock Bitget client tracks call count."""
        mock_bitget_api.get_liquidity("test_contract")
        assert mock_bitget_api.call_count == 1

    def test_mock_rugcheck_reset(self, mock_rugcheck_api):
        """Test mock RugCheck reset functionality."""
        mock_rugcheck_api.analyze("test")
        assert mock_rugcheck_api.call_count == 1

        mock_rugcheck_api.reset()
        assert mock_rugcheck_api.call_count == 0
