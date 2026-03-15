"""Tests for token symbol resolution before analysis."""

import json

from agent.decision import DecisionAnalyzer


class TestTokenResolution:
    """Test token symbol to contract resolution."""

    def test_contract_like_input_is_left_unchanged(self):
        """Mint-like inputs should bypass search resolution."""
        analyzer = DecisionAnalyzer()

        contract = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

        assert analyzer.resolve_token_contract(contract) == contract

    def test_symbol_input_resolves_to_exact_solana_match(self, monkeypatch):
        """Token symbols should resolve to an exact Solana search match."""
        analyzer = DecisionAnalyzer()

        def fake_run(cmd, capture_output, text, timeout):
            class Result:
                returncode = 0
                stdout = json.dumps(
                    {
                        "status": 0,
                        "data": {
                            "list": [
                                {
                                    "chain": "sol",
                                    "symbol": "BONK",
                                    "contract": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
                                },
                                {
                                    "chain": "eth",
                                    "symbol": "BONK",
                                    "contract": "0xdeadbeef",
                                },
                            ]
                        },
                    }
                )
                stderr = ""

            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)

        resolved = analyzer.resolve_token_contract("BONK")

        assert resolved == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

    def test_symbol_input_returns_none_when_no_exact_solana_match(self, monkeypatch):
        """Unknown symbols should fail cleanly instead of producing fake analysis."""
        analyzer = DecisionAnalyzer()

        def fake_run(cmd, capture_output, text, timeout):
            class Result:
                returncode = 0
                stdout = json.dumps(
                    {
                        "status": 0,
                        "data": {
                            "list": [{"chain": "sol", "symbol": "NOTBONK", "contract": "abc"}]
                        },
                    }
                )
                stderr = ""

            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)

        assert analyzer.resolve_token_contract("BONK") is None
