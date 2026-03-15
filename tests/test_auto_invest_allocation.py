"""Tests for score/liquidity-weighted auto-invest allocation."""

from agent.allocation import allocate_auto_invest_budget


class TestAutoInvestAllocation:
    def test_higher_score_and_liquidity_receive_more_budget(self):
        selected = [
            {"symbol": "A", "score": 90, "analysis": type("X", (), {"liquidity_usd": 300000})()},
            {"symbol": "B", "score": 80, "analysis": type("X", (), {"liquidity_usd": 150000})()},
            {"symbol": "C", "score": 70, "analysis": type("X", (), {"liquidity_usd": 50000})()},
        ]

        allocations = allocate_auto_invest_budget(selected, budget_usd=30)

        assert allocations["A"] > allocations["B"] > allocations["C"]
        assert round(sum(allocations.values()), 2) == 30.00

    def test_single_token_gets_full_budget(self):
        selected = [
            {"symbol": "BONK", "score": 88, "analysis": type("X", (), {"liquidity_usd": 200000})()},
        ]

        allocations = allocate_auto_invest_budget(selected, budget_usd=10)

        assert allocations == {"BONK": 10.0}
